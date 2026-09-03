"""The query path, end to end.

    understand -> four facets -> RRF -> contextual weight -> metabolism
                -> rerank -> 1-hop expansion (separate group)

Two entry points, because the interface needs two speeds:

``quick_search``  synchronous, lexical only, no model call. This is the first
                  paint: the user has typed three characters and stopped, and
                  something has to be on screen in under 20 ms.
``search``        the full pipeline. One embedding call, optionally one chat
                  call for reranking. Replaces the first paint when it lands.

Progressive rendering is not a performance trick here, it is a correctness
concession: the lexical facet is the only one that is *always* right about
exact strings, and the only one that costs nothing. Showing it first means a
user searching for a remembered phrase gets their answer before the vector
facets have finished having an opinion.
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import TypeVar

from ..config import Settings, get_settings
from ..db import in_chunks, jload
from ..providers import MockProvider, Provider, get_provider
from . import abstain
from .context import ContextSignals, build_context, window_filter
from .decay import cold_bookmark_ids, decay_hits
from .graph import Expansion, expand
from .lexical import lexical_lists, lexical_lists_scored
from .querylang import (
    ParsedQuery,
    apply_filters,
    parse_query,
    pool_from_filters,
    sort_pool,
)
from .rerank import RerankDoc, Reranker, get_reranker, reorder
from .rrf import DEFAULT_K, Fused, guarantee_bonus, rrf
from .understand import (
    QueryUnderstanding,
    classify,
    classify_assisted,
    episodic_beyond_a_bare_year,
)
from .vectors import vector_lists, vector_lists_scored

#: Per-facet fusion weights. Three of the four are 1.0 -- RRF's whole appeal is
#: that it does not need tuning, and weighting facets is the first step back
#: towards the score-normalisation swamp it was chosen to avoid. ``lex_tri`` is
#: the one exception: trigram matching fires on substrings inside unrelated
#: words, so it is damped rather than trusted equally with the word index.
DEFAULT_FACET_WEIGHTS: dict[str, float] = {
    "content": 1.0,
    "intent": 1.0,
    "lex_seg": 1.0,
    "lex_tri": 0.7,
}

VECTOR_FACETS = frozenset({"content", "intent"})
LEXICAL_FACETS = frozenset({"lex_seg", "lex_tri"})
ALL_FACETS = VECTOR_FACETS | LEXICAL_FACETS

def vector_facets_present(conn: sqlite3.Connection) -> frozenset[str]:
    """Which vector facets this library can actually run right now.

    A facet counts as present only when its table exists *and* holds at least
    one row: an empty ``vec_content`` ranks nothing, however honourable the
    intent behind it. ``default_config`` cannot make this call -- it sees the
    settings and the provider, not the database -- and the settings are exactly
    what a chat-only deployment lies about. A key that answers
    ``/chat/completions`` and 404s on ``/embeddings`` has ``api_key`` set, so
    the gate's answer is ``FULL``, and ``FULL`` over an empty vector store
    returns an empty page for every query. That is not a degraded answer, it
    is no answer, and the library usually holds pages the lexical index can
    find. Whether it can is decided here, per query, from the database.
    """
    out: set[str] = set()
    for table, facet in (("vec_content", "content"), ("vec_intent", "intent")):
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if exists is None:
            continue
        if conn.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone():
            out.add(facet)
    return frozenset(out)


def degrade_for_vector_store(
    conn: sqlite3.Connection, config: Config
) -> tuple[Config, str]:
    """Swap in lexical facets when the config's vector facets cannot run.

    Only the total-loss case is repaired: a config that keeps at least one
    runnable facet runs as named, and the empty facet is visible in
    ``facet_sizes`` as the honest report of a facet with no candidates. What is
    not honest is a config left with *zero* runnable facets -- the shipped
    ``full`` profile over a library with no vectors -- because that answers
    every question with an empty page while the words the reader typed are
    sitting in the lexical index.

    The lexical facets inherit the config's other flags (context, graph,
    decay, rerank) unchanged. Nothing about the *ranking* of those facets is
    being claimed here: this is the same pre-gate behaviour ``FUSED`` ships
    for the mock provider, deployed as a runtime fallback rather than a
    default, and the response says it happened via ``degraded_from``.
    """
    missing = config.facets & VECTOR_FACETS - vector_facets_present(conn)
    if not missing or (config.facets - missing):
        return config, ""
    return (
        Config(
            name=f"{config.name}/lex",
            facets=LEXICAL_FACETS,
            context=config.context,
            graph=config.graph,
            rerank=config.rerank,
            decay=config.decay,
        ),
        config.name,
    )


#: Candidate depth assumed when sizing the CombMAX coefficient for ``C_max``.
#: Mirrors :attr:`Settings.candidates_per_facet`, which is a runtime setting and
#: therefore not importable as a constant here; the two are checked against each
#: other in the tests.
#:
#: The dependence runs the *unintuitive* way: shallow lists are what make the
#: bonus necessary. "Last" means rank ``depth``, so a deeper list pushes the
#: all-last document further down, and past depth 166 it loses to a sole #1
#: unaided -- the coefficient falls to zero. Raising ``candidates_per_facet``
#: without re-deriving this would leave ``C_max`` paying for a guarantee it
#: already has.
_GUARANTEE_DEPTH = 50

SNIPPET_CHARS = 300

#: Facet lists come through as bare ids on the default path and as
#: ``(id, score)`` pairs on the abstention path. Trimming is the same operation
#: on both, and doing it in one place is what keeps the two paths agreeing
#: about how deep the pool was.
_T = TypeVar("_T")


# ---------------------------------------------------------------------------
# paging
# ---------------------------------------------------------------------------
#
# What makes a page-2 request honest is that it continues page 1 rather than
# holding a second opinion about the same query, and whether that holds is a
# property of the fusion rather than of the slicing.
#
# **One facet: exact.** A single ranked list scores ``w / (k + rank)``, which is
# strictly decreasing in rank, so the fused order *is* the facet's order. Asking
# for 500 candidates instead of 50 appends and never reorders. The shipped
# ``FULL`` config has one facet, so its paging is exact for free.
#
# **Several facets: only at a fixed depth.** A document's RRF score is a sum
# over the facets that ranked it *within the depth asked for*, so raising the
# depth can hand a document a term it did not previously have -- and that term
# can be worth more than a rival's whole score. Ranks 40 and 40 in two facets
# beat rank 1 in one facet (0.0200 against 0.0164) but contribute nothing at
# depth 30. So a deeper pool genuinely reorders, and paging by growing the depth
# would let page 2 disagree with page 1 about page 1.
#
# The fix is not to grow the depth. ``depth`` is a request parameter, echoed on
# every response: a client that wants an exactly consistent multi-page session
# sends back the depth it was given, and every page is then a slice of one
# ranking. Left unset it defaults to whatever the requested window needs, which
# is the cheap thing to do for the overwhelmingly common single-page request.
# ``tests/test_search.py::TestPaging`` pins both halves of this -- exactness
# under a pinned depth, and the reordering that motivates the parameter.


@dataclass(frozen=True, slots=True)
class Page:
    """The resolved window for one request, after clamping."""

    limit: int
    offset: int
    #: Per-facet candidate depth. Either the caller's, or derived from the
    #: window; clamped to ``max_candidate_depth`` either way.
    depth: int
    #: :attr:`depth` was cut by ``max_candidate_depth``. On its own this says
    #: nothing about whether results were lost -- the facets may not have had
    #: that many candidates anyway -- so it is combined with the observed facet
    #: sizes before being reported. See :func:`page_signals`.
    ceiling_hit: bool

    @property
    def stop(self) -> int:
        return self.offset + self.limit

    @property
    def fetch(self) -> int:
        """How many rows to ask each facet for: :attr:`depth`, plus a probe.

        The probe row is the difference between "the facet had more to give"
        and "the facet happened to hold exactly this many", which are the same
        observation if you only ask for ``depth``. It is cut off again by
        :func:`trim_pool` before fusion, so it never reaches a score, a hydrate
        or a page -- it exists to be counted.
        """
        return self.depth + 1


def resolve_page(
    settings: Settings,
    *,
    limit: int,
    offset: int,
    depth: int | None = None,
    over_fetch: int = 1,
) -> Page:
    """Clamp a requested window and settle the retrieval depth it runs at.

    ``limit`` and ``offset`` are clamped rather than rejected, and the clamped
    values are echoed back on the response, because a caller that asks for
    10,000 rows wants results, not a 422 -- but it also must not be told "here
    are your 10,000 rows" and handed 200.

    ``depth`` pins the per-facet candidate depth; see the module note above for
    why a paging client should pin it. Unset, it is derived from the window.

    ``over_fetch`` widens that derived depth for callers whose facets return
    heavily overlapping lists, where fusion dedupes a large fraction of the pool
    and asking for exactly the window size yields a short page that looks like
    the end of the results.
    """
    limit = max(1, min(int(limit), max(1, settings.max_page_size)))
    ceiling = max(1, settings.max_candidate_depth)
    offset = max(0, min(int(offset), ceiling - 1))
    if depth is None:
        want = max(settings.candidates_per_facet, (limit + offset) * max(1, over_fetch))
    else:
        want = max(1, int(depth))
    settled = min(want, ceiling)
    return Page(limit=limit, offset=offset, depth=settled, ceiling_hit=settled < want)


def trim_pool(
    page: Page, lists: Mapping[str, Sequence[_T]]
) -> tuple[dict[str, list[_T]], bool]:
    """Cut every facet back to ``depth`` and report whether any overflowed.

    Facets are read at :attr:`Page.fetch`, one row deeper than the pool is
    allowed to be. Trimming here rather than at each call site keeps the fusion
    input exactly ``depth`` rows per facet -- which is what makes a pinned depth
    reproduce the same ranking on every page -- while the row that was thrown
    away still gets to answer "was there more?".
    """
    over = any(len(ids) > page.depth for ids in lists.values())
    return {name: list(ids)[: page.depth] for name, ids in lists.items()}, over


def page_signals(page: Page, total: int, *, truncated: bool) -> tuple[bool, bool]:
    """``(has_more, depth_capped)`` for a finished request.

    ``truncated`` comes from :func:`trim_pool`: some facet had a row past the
    depth we fused at, so the library has more to say even when the served
    window ran to the end of the pool. Without it a request whose window lands
    exactly on the depth ceiling would report itself as the last page, which is
    the one lie a paging UI cannot recover from.

    ``depth_capped`` narrows that to the case worth acting on -- more results
    exist *and* the reason we stopped is our own ceiling rather than the
    caller's window -- so a client can tell "press next" apart from "raise
    ``depth`` or narrow the query".

    In a multi-facet config the overflow row may turn out to be a document the
    pool already holds, so ``has_more`` is an upper bound there: it can say
    "more" and deliver a short final page. It is never wrong in the other
    direction, and the shipped single-facet config is exact.
    """
    return (page.stop < total or truncated), (truncated and page.ceiling_hit)


@dataclass(frozen=True, slots=True)
class Config:
    """One rung of the ablation ladder (and the shipped default)."""

    name: str
    facets: frozenset[str]
    context: bool = False
    graph: bool = False
    rerank: bool = False
    decay: bool = False
    #: Per-facet fusion weights layered over :data:`DEFAULT_FACET_WEIGHTS`. A
    #: tuple of pairs rather than a dict because the dataclass is frozen and
    #: therefore hashable, and a dict field would make hashing raise.
    #:
    #: The W1 leave-one-out result says flat-weight RRF is what costs 5-6pp of
    #: Recall@5: a coincidence on a weak facet (1/61 + 0.7/61 = 0.0279) outvotes
    #: confidence on a strong one (1/61 = 0.0164). Down-weighting the weak
    #: facets is the obvious repair, but "obvious" is not "measured" -- the
    #: numbers that suggested it came from the 479 queries in
    #: ``eval/queries/w1-real-library.jsonl``, so fitting weights on those and
    #: reporting the gain would be fitting to the test set. This knob exists so
    #: W2 can fit it on a *new* query set. Nothing ships with it set.
    weight_overrides: tuple[tuple[str, float], ...] = ()
    #: Silence a facet whose own score distribution says it has no opinion.
    #: 0.0 disables it entirely, which is the shipped state. See
    #: :mod:`facetmark.search.abstain` for why the threshold is measured
    #: within a facet rather than across facets, and why no value for it has
    #: been fitted.
    abstain_margin: float = 0.0
    #: Apply the contextual multiplier only when the query looks episodic.
    #:
    #: A vs A_ctx: +8.14pp on episodic queries, -9.94pp on content queries, both
    #: p<0.001. That is not a weak mechanism, it is a strong one pointed at the
    #: wrong queries. Requires ``context=True`` to do anything. Also unshipped
    #: and unvalidated for the same reason as ``weight_overrides``.
    context_gate: bool = False
    #: Which gate predicate ``context_gate`` means.
    #:
    #: 1 -- ``is_episodic``: any resolvable time expression opens the gate. This
    #: is what 1.2.0 shipped, on evidence that only ever measured what the gate
    #: does when it *should* fire.
    #:
    #: 2 -- :func:`~facetmark.search.understand.episodic_beyond_a_bare_year`: a
    #: lone year no longer counts. Pre-registered in
    #: ``docs/gate-precision-protocol.md`` §6 as the remedy if v1 failed its
    #: precision test, which it did: -18.83pp Recall@5 on 361 probes whose year
    #: belonged to the subject matter rather than to the filing date.
    context_gate_version: int = 1
    #: CombMAX coefficient handed to :func:`~facetmark.search.rrf.rrf`. 0.0 --
    #: the shipped state -- leaves fusion bit-identical to plain RRF.
    #:
    #: The sum has no floor for a confident single facet: two full-weight facets
    #: that merely recall a document beat a sole-facet #1 at every rank inside
    #: the candidate depth (``docs/w2-fusion-anatomy.md`` §3), and 81 of the 102
    #: sole-facet #1s in the W1 replay left the top 5. A max term is the
    #: standard repair. :func:`~facetmark.search.rrf.guarantee_bonus` says the
    #: coefficient needed to fully restore the guarantee is >1, i.e. the bonus
    #: has to outweigh the entire sum -- so this is a knob to *measure*, not a
    #: default to flip. Same discipline as ``weight_overrides``: the evidence
    #: for it came from the 479 queries in
    #: ``eval/queries/w1-real-library.jsonl``, so it has to be fitted and judged
    #: on a query set those queries did not generate.
    max_bonus: float = 0.0

    @property
    def facet_weights(self) -> dict[str, float]:
        """Fusion weights for this configuration, defaults plus overrides."""
        w = dict(DEFAULT_FACET_WEIGHTS)
        w.update(self.weight_overrides)
        return w

    def wants_context(self, understanding) -> bool:
        """Whether the contextual multiplier should run for this query."""
        if not self.context:
            return False
        if not self.context_gate:
            return True
        if self.context_gate_version >= 2:
            return episodic_beyond_a_bare_year(understanding)
        return understanding.is_episodic

    def as_dict(self) -> dict:
        return {
            "name": self.name, "facets": sorted(self.facets), "context": self.context,
            "graph": self.graph, "rerank": self.rerank, "decay": self.decay,
            "weight_overrides": dict(self.weight_overrides),
            "context_gate": self.context_gate,
            "context_gate_version": self.context_gate_version,
            "abstain_margin": self.abstain_margin,
            "max_bonus": self.max_bonus,
        }


#: The ablation ladder from the design document. A is what every existing tool
#: does; each rung adds exactly one mechanism so the delta is attributable.
CONFIGS: dict[str, Config] = {
    "A": Config("A", frozenset({"content"})),
    "B": Config("B", frozenset({"content", "lex_seg", "lex_tri"})),
    "C": Config("C", ALL_FACETS),
    "D": Config("D", ALL_FACETS, context=True, graph=True),
    "E": Config("E", ALL_FACETS, context=True, graph=True, rerank=True),
}

#: Rungs the design document never asked for, added after the W1 gate came back
#: negative in an unexpected direction: A beat every rung above it on the primary
#: metric, and the single largest regression in the whole table was A->B, the
#: step that introduces the lexical facets. The ladder is additive by
#: construction, so it can isolate "what does adding X do on top of everything
#: below it" but never "what does *removing* X do". These are the leave-one-out
#: complements needed to answer the second question, kept in a separate dict so
#: the pre-registered ladder above stays exactly as it was pre-registered.
EXPLORATORY: dict[str, Config] = {
    # C minus the lexical facets: does the intent facet stand on its own?
    "C_nolex": Config("C_nolex", VECTOR_FACETS),
    # D minus the lexical facets: keeps D's context/graph, drops the suspect.
    "D_nolex": Config("D_nolex", VECTOR_FACETS, context=True, graph=True),
    # A plus context/graph only: the cheapest thing that could still work.
    "A_ctx": Config("A_ctx", frozenset({"content"}), context=True, graph=True),
    # A plus the expansion group and nothing else. Graph expansion never touches
    # `hits`, only the second group -- so this separates "the related group pays
    # for itself" from "the context multiplier reorders the page", which A_ctx
    # bundles together and therefore cannot attribute.
    "A_graph": Config("A_graph", frozenset({"content"}), graph=True),
    # The lexical facets with nothing to hide behind. Not a candidate for
    # anything -- it is the diagnostic the query set never had: how much of it
    # is solvable by word matching alone, which is exactly what the generator's
    # anti-leak gates exist to prevent and never measured. Because the vector
    # branch is guarded by `config.facets & VECTOR_FACETS`, this rung runs
    # without an embedding model at all. Protocol: docs/query-set-lexical-audit.md.
    "lex_only": Config("lex_only", LEXICAL_FACETS),
    # Facet 3 taken apart. The two indexes were justified against each other on
    # a calibration library using two-to-four character lookups as ground truth
    # (see facetmark.text), and have been fused as one block ever since; nobody
    # measured either half against a real query. Taking them apart is what
    # exposed the trigram defect -- lex_tri returned nothing for 88% of Chinese
    # queries. Same reason as lex_only: no vectors, so both run without a model.
    # Results: docs/w2-fusion-anatomy.md.
    "seg_only": Config("seg_only", frozenset({"lex_seg"})),
    "tri_only": Config("tri_only", frozenset({"lex_tri"})),
    # --- W2 candidates ---------------------------------------------------
    # The three rungs below exist so the two W1 repairs are *runnable* before
    # they are believed. They are not defaults and they carry no claim: the
    # evidence that motivated each one comes from the same 479 queries any
    # A/B against them would use, so a win here measures nothing but the
    # circularity. They ship so W2 can point them at a query set that has not
    # seen them.
    #
    # A_ctx, but the multiplier only fires when the query looks episodic.
    # A_ctx is +8.14pp episodic / -9.94pp content; if the gate works the
    # second number should go to roughly zero and the first should survive.
    "A_gatedctx": Config(
        "A_gatedctx", frozenset({"content"}), context=True, graph=True, context_gate=True
    ),
    # A_gatedctx with the year clause narrowed. The remedy pre-registered in
    # docs/gate-precision-protocol.md before the probe set existed: a bare year
    # stops counting as a filing-date signal. Two tests to pass, both frozen in
    # advance -- the -18.83pp probe-set cost has to go, and the +3.09pp W2/W3
    # win has to survive.
    "A_gatedctx_v2": Config(
        "A_gatedctx_v2", frozenset({"content"}), context=True, graph=True,
        context_gate=True, context_gate_version=2,
    ),
    # D with the same gate: the full fusion stack, contextual multiplier
    # restricted to the queries it helped.
    "D_gated": Config(
        "D_gated", ALL_FACETS, context=True, graph=True, decay=False, context_gate=True
    ),
    # C with the lexical facets damped instead of removed. C_nolex showed that
    # *deleting* a weak facet does not recover the loss (-5.43pp either way);
    # this asks whether *quieting* it does. 0.3/0.2 is a guess, not a fit.
    "C_lowlex": Config(
        "C_lowlex", ALL_FACETS, weight_overrides=(("lex_seg", 0.3), ("lex_tri", 0.2))
    ),
    # C with abstention instead of damping. Damping says "this facet is always
    # worth less"; abstention says "this facet is worth nothing on the queries
    # where it cannot tell its own results apart". They are different claims
    # and the ladder should be able to separate them, so they get one rung
    # each. 0.25 is a placeholder -- a facet has to clear a quarter of its own
    # score range to be heard -- and it has not been fitted on anything.
    "C_abstain": Config("C_abstain", ALL_FACETS, abstain_margin=0.25),
    # C with the trigram half of Facet 3 removed rather than damped. Separating
    # the two lexical indexes for the first time (docs/w2-fusion-anatomy.md)
    # found that adding lex_tri to lex_seg is worth -0.42pp, CI95 [-2.09, +1.25]
    # -- a facet that has never been shown to pay for its vote. Deleting it is
    # a different claim from damping it (C_lowlex damps both halves), so it gets
    # its own rung. Like the others: implemented, off, unjudged.
    "C_notri": Config("C_notri", ALL_FACETS - frozenset({"lex_tri"})),
    # C with a CombMAX term sized to restore the sole-facet guarantee. The
    # coefficient is computed, not chosen: `guarantee_bonus` solves for the
    # crossover between a document some facet ranks #1 and a document no facet
    # ranks better than last, which for C's weights is 2.361. Sitting *at* the
    # crossover rather than a hair above it is deliberate -- the worst case
    # ties, everything short of it wins, and inventing an epsilon would dress a
    # boundary up as a fitted value. It is
    # above 1.0, meaning the bonus outweighs the sum it is correcting -- which
    # is the honest reading of the arithmetic, not an endorsement. Whether a
    # coefficient that large helps or wrecks the ranking is exactly the question
    # a fresh query set has to answer. Implemented, off, unjudged.
    "C_max": Config(
        "C_max", ALL_FACETS,
        max_bonus=guarantee_bonus(DEFAULT_K, _GUARANTEE_DEPTH, DEFAULT_FACET_WEIGHTS),
    ),
}

#: What shipped before the W1 gate: stage E plus metabolism. Kept reachable by
#: name so anyone comparing against the pre-gate behaviour can still ask for it.
FUSED = Config("fused", ALL_FACETS, context=True, graph=True, rerank=True, decay=True)

#: What ``facetmark search``, the API and the MCP server actually run now.
#:
#: This used to be ``FUSED``. The W1 ablation on a 2,376-document library of real
#: pages says that was wrong on every mechanism it turned on, so each flag below
#: is set by a measurement rather than by the design document:
#:
#: * ``facets={"content"}`` -- fusing anything into the content vector cost
#:   5-6pp of Recall@5, and it cost the same whether the companion was the two
#:   lexical facets (A->B, -5.43pp, p=0.0067) or the intent facet on its own
#:   (A->C_nolex, -5.43pp, p=0.0016). Flat-weight RRF over facets of unequal
#:   quality lets a coincidence on a weak facet outvote confidence on a strong
#:   one. Weighting is fixable, but it has to be fitted on queries that did not
#:   suggest the fix, so it is W2 work.
#: * ``context=False`` -- the contextual multiplier is not a small effect in
#:   either direction: +8.14pp on episodic queries and -9.94pp on content
#:   queries (both p<0.001, A vs A_ctx on W1). Unconditionally on it loses, so
#:   W1 shipped it off and left "gate it on the query looking episodic" as a
#:   hypothesis. W2 judged that hypothesis on 616 queries that played no part in
#:   forming it (``docs/gate-w2w3.md``) and it won: gated, +3.09pp over plain A,
#:   CI95 [+1.79, +4.55], 19 won / 0 lost. 1.2.0 made it the default on that
#:   evidence.
#:
#:   1.3.0 takes it back out, because that evidence only ever measured the gate
#:   on queries where it *should* fire. Its 0.55% false-positive rate was
#:   measured on 181 content queries a generator had been instructed not to put
#:   dates into. Asked instead for 361 topical queries whose time expression
#:   belongs to the subject matter -- "2015年国际空间站咖啡机为什么那么贵" of a
#:   page filed in 2026 -- the gate fires on **361 of 361** and costs
#:   **-18.83pp of Recall@5, CI95 [-23.27, -14.68], 3 better / 71 worse**, with
#:   Recall@1 falling from 0.801 to 0.363 (``docs/gate-precision.md``). On the
#:   304 probes whose resolved window cannot contain the answer it is -22.37pp;
#:   on the 57 where the window happens to be right it is +0.00pp, which is the
#:   control that says this is the window being wrong and not the multiplier
#:   being heavy.
#:
#:   The remedy for that was written down before the probe set existed and is
#:   implemented as ``A_gatedctx_v2`` (``context_gate_version=2``): a bare year
#:   stops counting as a filing-date signal. It does what it says -- the 197
#:   probes it silences move 0.00pp with zero discordant pairs, and it keeps
#:   +1.79pp CI95 [+0.81, +2.92] on the 616 -- but the residual -10.52pp from
#:   ``time:relative``, a clause the pre-registered remedy deliberately did not
#:   touch, fails the first of its two frozen bars. The protocol required both,
#:   so the default reverts here rather than moving to v2.
#: * ``graph=True`` -- the only mechanism in the study that is free. Expansion
#:   never touches the ranked page, so every ranked metric is bit-identical to
#:   plain A, and the second group finds the target in 2.09pp more queries
#:   (10 won / 0 lost, p=0.0019) for 9 milliseconds.
#: * ``rerank=False`` -- 45.4 s per query at p50 on a local 3B model, to recover
#:   45% of the Recall@1 that fusion destroyed. With fusion off there is nothing
#:   left for it to repair. Still available as ``--config E``.
#: * ``decay=True`` -- metabolism is deliberately outside the ladder; it is a
#:   library-hygiene feature, and leaving it on during ablation would let a
#:   cold-start corpus move the numbers for reasons unrelated to retrieval.
FULL = Config("full", frozenset({"content"}), graph=True, decay=True)

#: Named configurations that are neither ladder rungs nor complements: the thing
#: that ships, and the thing that used to ship.
PROFILES: dict[str, Config] = {"full": FULL, "fused": FUSED}

def default_config(settings=None, provider: Provider | None = None) -> Config:
    """The configuration this deployment should actually run.

    ``FULL`` is what the W1 ablation selected, and every flag in it is set by a
    measurement taken on a library of 2,376 real pages embedded by a real model.
    None of those measurements transfer to a deployment with no embeddings: the
    mock provider hashes text into a vector, so the content facet -- the one
    that wins outright on a real library -- is the one that returns noise on a
    mock one, and dropping the lexical facets would leave such a deployment with
    nothing that works. ``get_reranker`` already makes exactly this call for
    exactly this reason.

    So: real embeddings get the gate's answer, everyone else gets the pre-gate
    behaviour, which at least retrieves by words. The provider instance decides
    when it is known, because a caller can inject a mock over settings that say
    otherwise -- which is exactly what the test suite does.
    """
    if isinstance(provider, MockProvider):
        return FUSED
    if settings is not None and (
        getattr(settings, "use_mock_provider", False) or not getattr(settings, "api_key", "")
    ):
        return FUSED
    return FULL


#: Every config the harness or the API can be asked to run, pre-registered or
#: not. Callers that report results must say which dict a rung came from; an
#: exploratory rung measured on the same queries that motivated it is a
#: hypothesis, not a result.
ALL_CONFIGS: dict[str, Config] = {**CONFIGS, **EXPLORATORY, **PROFILES}


@dataclass(slots=True)
class SearchHit:
    bookmark_id: int
    url: str
    title: str
    score: float
    #: Score before the contextual multiplier and metabolism, i.e. raw RRF.
    base_score: float = 0.0
    facets: list[str] = field(default_factory=list)
    ranks: dict[str, int] = field(default_factory=dict)
    contributions: dict[str, float] = field(default_factory=dict)
    context_boost: float = 1.0
    context_reasons: list[str] = field(default_factory=list)
    cold: bool = False
    folder: str = ""
    domain: str = ""
    date_added: int | None = None
    snippet: str = ""
    utility: str = ""
    content_type: str = ""
    topics: list[str] = field(default_factory=list)
    #: User-authored tags (imports, save API). Echoed so every client can
    #: render the filing vocabulary the way it renders the folder.
    tags: list[str] = field(default_factory=list)
    #: Only set on rows in the expansion group.
    via: int | None = None
    via_kind: str = ""

    def as_dict(self) -> dict:
        d = {
            "bookmark_id": self.bookmark_id, "url": self.url, "title": self.title,
            "score": round(self.score, 6), "base_score": round(self.base_score, 6),
            "facets": self.facets, "ranks": self.ranks,
            # Already computed by `rrf()`; sending it is what lets a reader see
            # *how much* each path put into a row rather than only that it
            # voted. Reconstructing it in the browser would mean shipping `k`
            # and the per-config facet weights as well, and then keeping two
            # copies of the formula honest.
            "contributions": {f: round(v, 6) for f, v in self.contributions.items()},
            "context_boost": round(self.context_boost, 4),
            "context_reasons": self.context_reasons, "cold": self.cold,
            "folder": self.folder, "domain": self.domain, "date_added": self.date_added,
            "snippet": self.snippet, "utility": self.utility,
            "content_type": self.content_type, "topics": self.topics,
            "tags": self.tags,
        }
        if self.via is not None:
            d["via"] = self.via
            d["via_kind"] = self.via_kind
        return d


@dataclass(slots=True)
class SearchResponse:
    query: str
    hits: list[SearchHit] = field(default_factory=list)
    #: 1-hop neighbours of the top hits. Rendered as its own group, never
    #: interleaved with ``hits``.
    expanded: list[SearchHit] = field(default_factory=list)
    understanding: QueryUnderstanding | None = None
    config: str = "full"
    facet_sizes: dict[str, int] = field(default_factory=dict)
    #: Per-facet self-confidence, populated only when abstention is enabled.
    #: A facet that was silenced still appears here, with the score that
    #: silenced it -- otherwise fitting a threshold would mean guessing at the
    #: distribution of the thing you are thresholding.
    facet_confidence: dict[str, float] = field(default_factory=dict)
    context: dict | None = None
    #: True when the cold-layer demotion was lifted because nothing hot scored.
    rescued: bool = False
    reranker: str = ""
    took_ms: dict[str, float] = field(default_factory=dict)
    #: The window actually served. Not an echo of the request: both are clamped
    #: against ``max_page_size`` / ``max_candidate_depth``, and a caller that
    #: pages by incrementing its own counter needs to know which one was used.
    limit: int = 0
    offset: int = 0
    #: The per-facet candidate depth this ranking was produced at. Send it back
    #: on the next page: fusion is only order-stable across pages at a fixed
    #: depth once more than one facet is in play (see the paging note above).
    depth: int = 0
    #: Documents ranked for this query, i.e. the size of the fused pool. It is
    #: a count of what fusion *considered*, which at the depth ceiling is a
    #: lower bound on the library's true match count rather than the whole of
    #: it -- ``depth_capped`` says which of the two this is.
    total: int = 0
    #: Whether another page exists. Derived from the pool, except at the depth
    #: ceiling where the pool itself is truncated and the honest answer is
    #: "probably, and you have reached the configured limit".
    has_more: bool = False
    #: The pool was cut by ``max_candidate_depth``, not by the library running
    #: out. Distinguishing these is the whole reason both fields exist: a short
    #: page at the ceiling is not the end of the results.
    depth_capped: bool = False
    #: Set when the config that actually ran is not the one that was asked
    #: for: it named vector facets the library cannot run (no vector store),
    #: so the lexical facets stood in. Holds the *requested* config's name --
    #: ``config`` above holds the name of what ran. Empty when nothing moved.
    degraded_from: str = ""
    #: The query-language filters this query carried (``domain:``, ``added:``,
    #: negations, ``sort:``), echoed so a caller can see what was applied.
    #: ``None`` -- the default -- means the query had no syntax at all and the
    #: ranking ran exactly as it did before the language existed.
    filters: dict | None = None
    #: The sort directive the query asked for, "" when it asked for none.
    sort: str = ""

    def as_dict(self) -> dict:
        return {
            "query": self.query,
            "hits": [h.as_dict() for h in self.hits],
            "expanded": [h.as_dict() for h in self.expanded],
            "understanding": self.understanding.as_dict() if self.understanding else None,
            "config": self.config,
            "degraded_from": self.degraded_from,
            "facet_sizes": self.facet_sizes,
            "facet_confidence": self.facet_confidence,
            "context": self.context,
            "rescued": self.rescued,
            "reranker": self.reranker,
            "took_ms": {k: round(v, 2) for k, v in self.took_ms.items()},
            "limit": self.limit,
            "offset": self.offset,
            "depth": self.depth,
            "total": self.total,
            "has_more": self.has_more,
            "depth_capped": self.depth_capped,
            "filters": self.filters,
            "sort": self.sort,
        }

    @property
    def ids(self) -> list[int]:
        return [h.bookmark_id for h in self.hits]


# ---------------------------------------------------------------------------
# hydration
# ---------------------------------------------------------------------------

_ROW_SQL = """
SELECT b.id, b.url, b.title, b.folder, b.domain, b.date_added, b.tags,
       e.summary, e.utility, e.content_type, e.topics,
       substr(c.body_text, 1, 400) AS body_head
FROM bookmark b
LEFT JOIN enrichment e ON e.bookmark_id = b.id
LEFT JOIN content    c ON c.bookmark_id = b.id
WHERE b.id IN ({marks})
"""


def _snippet(summary: str | None, body_head: str | None, terms: Sequence[str] = ()) -> str:
    """One line of context, centred on the first query term it contains.

    Before the query language existed the snippet was the first 300 characters
    of whatever was longest, summary or body head. That is the right default
    when there is nothing to aim at. When the caller knows the query terms,
    though, a snippet that starts at the top of the page and stops before the
    paragraph the user actually matched is a missed explanation: the term is in
    the hit, and the snippet is where a reader looks to see *why* it is a hit.

    So: find the first occurrence of the longest term (the longest match is the
    most specific one, and the one worth showing), and window around it within
    :data:`SNIPPET_CHARS`. Terms that appear nowhere leave the old behaviour
    untouched. CJK needs no special case -- ``str.find`` is position agnostic
    and the terms arrive already split by the parser.
    """
    text = (summary or "").strip() or (body_head or "").strip()
    text = " ".join(text.split())
    if not text:
        return ""
    if terms:
        low = text.lower()
        for term in sorted({t for t in terms if t}, key=len, reverse=True):
            pos = low.find(term.lower())
            if pos >= 0:
                return _window_around(text, pos, len(term))
    return text[:SNIPPET_CHARS]


def _window_around(text: str, pos: int, hit_len: int) -> str:
    """A ~SNIPPET_CHARS window centred on a hit, with honest ellipses."""
    half_before = (SNIPPET_CHARS - hit_len) // 2
    start = max(0, pos - half_before)
    end = min(len(text), start + SNIPPET_CHARS)
    # Re-widen the head if the tail clipped short (short text near the end).
    start = max(0, end - SNIPPET_CHARS)
    out = text[start:end]
    if start > 0:
        out = "…" + out
    if end < len(text):
        out = out + "…"
    return out


def _snippet_terms(parsed: ParsedQuery, u: QueryUnderstanding | None) -> list[str]:
    """Every word worth centreing a snippet on, longest first.

    The parser's positive words and phrase words, plus any phrases the
    understanding layer pulled out of CJK quotes -- the two extractions agree
    on double-quoted input and the union is cheap. Negated terms are left out
    on purpose: a snippet centred on the word the user excluded would explain
    the wrong thing.
    """
    terms: list[str] = []
    for t in parsed.terms:
        if t.negated:
            continue
        terms.extend(t.plain.split())
    if u is not None:
        for p in u.phrases:
            terms.extend(p.split())
    return sorted({t for t in terms if t}, key=len, reverse=True)


def hydrate(conn: sqlite3.Connection, ids: Sequence[int]) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for batch in in_chunks(ids):
        marks = ",".join("?" * len(batch))
        for r in conn.execute(_ROW_SQL.format(marks=marks), batch):
            out[int(r["id"])] = dict(r)
    return out


def _to_hit(
    row: Mapping, fused: Fused | None = None, terms: Sequence[str] = ()
) -> SearchHit:
    return SearchHit(
        bookmark_id=int(row["id"]),
        url=str(row["url"]),
        title=str(row["title"] or ""),
        score=fused.score if fused else 0.0,
        base_score=fused.score if fused else 0.0,
        facets=fused.facets if fused else [],
        ranks=dict(fused.ranks) if fused else {},
        contributions=dict(fused.contributions) if fused else {},
        folder=str(row["folder"] or ""),
        domain=str(row["domain"] or ""),
        date_added=int(row["date_added"]) if row["date_added"] else None,
        snippet=_snippet(row["summary"], row["body_head"], terms),
        utility=str(row["utility"] or ""),
        content_type=str(row["content_type"] or ""),
        topics=jload(row["topics"], []),
        tags=jload(row["tags"], []),
    )


# ---------------------------------------------------------------------------
# fast path
# ---------------------------------------------------------------------------


def quick_search(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 20,
    offset: int = 0,
    depth: int | None = None,
    k: int = DEFAULT_K,
    settings: Settings | None = None,
) -> SearchResponse:
    """Lexical-only first paint. Synchronous, no model call, no network.

    Query-language filters are honoured here too, at no cost: the first paint
    is where a reader pastes ``domain:github.com sort:date``, and answering it
    with unfiltered results only to have the full pipeline correct them a
    second later is a visible flash of the wrong answer.
    """
    t0 = time.perf_counter()
    s = settings or get_settings()
    parsed = parse_query(query)
    # 3x the window, as before: the two lexical lists overlap heavily -- that is
    # the point of running both -- so fusion dedupes a large fraction of what
    # they return, and asking for exactly the window size would hand back a
    # short page that looks like the end of the results.
    page = resolve_page(s, limit=limit, offset=offset, depth=depth, over_fetch=3)
    u = classify(query)

    if parsed.is_browse:
        # A query with nothing to rank (``domain:github.com``, ``-python``,
        # or a bare ``sort:date``) is a browse, and the filters *are* the
        # retrieval. RRF over one list preserves the order they chose
        # (date-descending by default).
        ids = pool_from_filters(conn, parsed, limit=page.fetch)
        lists = {"filter": ids}
        fused = rrf(lists, k=k)
        truncated = len(ids) >= page.fetch
    else:
        lists, truncated = trim_pool(page, lexical_lists(conn, parsed.text, limit=page.fetch))
        fused = rrf(lists, k=k, weights=DEFAULT_FACET_WEIGHTS)

    if parsed.has_filters:
        keep = set(apply_filters(conn, parsed, [f.doc_id for f in fused]))
        fused = [f for f in fused if f.doc_id in keep]
    if parsed.sort:
        by_id = {f.doc_id: f for f in fused}
        fused = [by_id[i] for i in sort_pool(conn, [f.doc_id for f in fused], parsed.sort)]

    window = fused[page.offset:page.stop]
    rows = hydrate(conn, [f.doc_id for f in window])
    terms = _snippet_terms(parsed, u)
    hits = [_to_hit(rows[f.doc_id], f, terms) for f in window if f.doc_id in rows]
    has_more, capped = page_signals(page, len(fused), truncated=truncated)
    return SearchResponse(
        query=query, hits=hits, understanding=u, config="quick",
        facet_sizes={k2: len(v) for k2, v in lists.items()},
        took_ms={"total": (time.perf_counter() - t0) * 1000},
        limit=page.limit, offset=page.offset, depth=page.depth, total=len(fused),
        has_more=has_more, depth_capped=capped,
        # `None` means the query carried no syntax at all -- the compatibility
        # guarantee. An ignored token is syntax the user typed, so `echo()`
        # being non-empty is the condition, not `has_syntax`: a query whose
        # only syntax failed to parse reported nothing and looked plain.
        filters=parsed.echo() or None,
        sort=parsed.sort,
    )


# ---------------------------------------------------------------------------
# full path
# ---------------------------------------------------------------------------


async def search(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 20,
    offset: int = 0,
    depth: int | None = None,
    config: Config | None = None,
    provider: Provider | None = None,
    settings: Settings | None = None,
    reranker: Reranker | None = None,
    understanding: QueryUnderstanding | None = None,
    assist: bool = False,
    now_ts: int | None = None,
    expand_limit: int = 8,
) -> SearchResponse:
    """Run the full retrieval pipeline for one query."""
    s = settings or get_settings()
    prov = provider or get_provider(s)
    if config is None:
        config = default_config(s, prov)
    config, degraded_from = degrade_for_vector_store(conn, config)
    # The query language splits "what to match" from "what to require": the
    # facets see the free text (phrases intact for the lexical paths, syntax
    # stripped for the embedding), and the filters cut the fused pool after
    # ranking. A query with no syntax parses to itself and nothing below
    # takes a different branch.
    parsed = parse_query(query)
    facet_query = parsed.text
    embed_query = parsed.plain_text or parsed.text
    timings: dict[str, float] = {}
    t_start = time.perf_counter()

    def mark(name: str, t0: float) -> None:
        timings[name] = (time.perf_counter() - t0) * 1000

    # --- 1. understanding -------------------------------------------------
    t0 = time.perf_counter()
    if understanding is None:
        understanding = (
            await classify_assisted(query, provider=prov, now_ts=now_ts)
            if assist
            else classify(query, now_ts=now_ts)
        )
    mark("understand", t0)

    # Retrieval depth used to be a side effect of the page size
    # (`max(candidates_per_facet, limit)`), which meant asking for more rows
    # quietly changed what was retrieved. It is now resolved up front, bounded,
    # and reported back.
    page = resolve_page(s, limit=limit, offset=offset, depth=depth)
    # One row deeper than the pool is allowed to be; `trim_pool` takes it back
    # off before anything is fused. See `Page.fetch`.
    per_facet = page.fetch

    # --- 2. facets --------------------------------------------------------
    # Two paths. The default one takes ranked ids and throws the scores away,
    # because RRF is deliberately rank-only. The abstention path keeps them,
    # because deciding whether a facet has an opinion requires looking at the
    # shape of its score distribution -- see `facetmark.search.abstain`.
    #
    # A query whose filters left no free text never reaches the facets at
    # all: the filters *are* the candidate list, and pretending otherwise
    # would burn an embedding call to rank documents the user has already
    # enumerated. That pool also skips the context multiplier, the decay
    # layer and the reranker -- a browse is an explicit enumeration, and
    # demoting "old, never opened" pages on a query that *asked* for old
    # pages would be the filters and the metabolism layer contradicting each
    # other with the metabolism layer winning.
    lists: dict[str, list[int]] = {}
    facet_confidence: dict[str, float] = {}
    truncated = False
    # ``-python`` with no positive text is also a browse: the whole library
    # minus one thing. So is a bare ``sort:date``. ``is_browse`` is the one
    # predicate both entry points read, because they disagreed: this path used
    # to require a filter, so ``sort:date`` answered nothing here while the
    # first paint answered the whole library.
    browse = parsed.is_browse
    if browse:
        t0 = time.perf_counter()
        ids = pool_from_filters(conn, parsed, limit=page.fetch)
        lists = {"filter": ids}
        mark("filter", t0)
    elif config.abstain_margin > 0.0:
        t0 = time.perf_counter()
        scored: dict[str, list[tuple[int, float]]] = {}
        if config.facets & LEXICAL_FACETS and facet_query:
            for name, rows in lexical_lists_scored(conn, facet_query, limit=per_facet).items():
                if name in config.facets:
                    scored[name] = rows
        mark("lexical", t0)

        t0 = time.perf_counter()
        if config.facets & VECTOR_FACETS and embed_query:
            vrows, _vec = await vector_lists_scored(
                conn, embed_query, provider=prov, settings=s, limit=per_facet,
                want_content="content" in config.facets,
                want_intent="intent" in config.facets,
            )
            scored.update(vrows)
        mark("vectors", t0)

        # Trim before abstention, not after: the margin is read off the shape
        # of a facet's score distribution, and the probe row is not part of the
        # pool it is being asked about.
        scored, truncated = trim_pool(page, scored)

        t0 = time.perf_counter()
        lists, facet_confidence = abstain.apply(scored, config.abstain_margin)
        mark("abstain", t0)
    else:
        t0 = time.perf_counter()
        if config.facets & LEXICAL_FACETS and facet_query:
            for name, ids in lexical_lists(conn, facet_query, limit=per_facet).items():
                if name in config.facets:
                    lists[name] = ids
        mark("lexical", t0)

        t0 = time.perf_counter()
        if config.facets & VECTOR_FACETS and embed_query:
            vlists, _vec = await vector_lists(
                conn, embed_query, provider=prov, settings=s, limit=per_facet,
                want_content="content" in config.facets,
                want_intent="intent" in config.facets,
            )
            lists.update(vlists)
        mark("vectors", t0)

        lists, truncated = trim_pool(page, lists)

    # --- 3. fusion --------------------------------------------------------
    t0 = time.perf_counter()
    fused = rrf(lists, k=s.rrf_k, weights=config.facet_weights, max_bonus=config.max_bonus)
    mark("fuse", t0)

    # A purely episodic query ("上个月存的那些") has no topic for any facet to
    # match. The window *is* the query, so it becomes the candidate set.
    if not fused and understanding.time_window is not None:
        ids = window_filter(conn, understanding.time_window)[: per_facet]
        truncated = truncated or len(ids) > page.depth
        ids = ids[: page.depth]
        fused = rrf({"episodic_window": ids}, k=s.rrf_k)
        lists["episodic_window"] = ids

    # --- 3b. the query language's filters cut the pool after ranking --------
    #
    # Post-fusion on purpose: a filter is a constraint on *which* documents may
    # answer, not an opinion about their order, so it never touches a score.
    # Cutting before fusion would also change the depth the facets fused at.
    if fused and parsed.has_filters:
        t0 = time.perf_counter()
        keep = set(apply_filters(conn, parsed, [f.doc_id for f in fused], now=now_ts))
        fused = [f for f in fused if f.doc_id in keep]
        mark("filter", t0)

    ctx: ContextSignals | None = None
    if fused and not browse and config.wants_context(understanding):
        t0 = time.perf_counter()
        # The 200-row cap keeps the context queries off the tail of the pool,
        # where a boost cannot change anything anyway. It has to cover the
        # served window though: a row past the cap gets a boost of 1.0 and
        # would be judged against neighbours that were boosted, which is not a
        # cheaper answer, just a wrong one.
        head = [f.doc_id for f in fused[: max(200, page.stop)]]
        ctx = build_context(
            conn,
            anchors=[f.doc_id for f in fused],
            candidates=head,
            query_window=understanding.time_window,
            episodic_confidence=understanding.episodic_confidence,
        )
        for f in fused:
            f.score *= ctx.boost(f.doc_id)
        fused = sorted(fused, key=lambda f: (-f.score, f.doc_id))
        mark("context", t0)

    # --- 4. metabolism ----------------------------------------------------
    # A browse has no ranking for metabolism to have an opinion about, and a
    # cold demotion on a query that *asked* for old pages (``added:>1y``) is
    # the two layers contradicting each other.
    rescued = False
    cold: set[int] = set()
    if config.decay and fused and not browse:
        t0 = time.perf_counter()
        cold = cold_bookmark_ids(
            conn, age_days=s.decay_age_days,
            ids=[f.doc_id for f in fused], now_ts=now_ts,
        )
        fused, outcome = decay_hits(
            fused, cold, factor=s.decay_factor, rescue_threshold=s.decay_rescue_threshold
        )
        rescued = outcome.rescued
        mark("decay", t0)

    # --- 4b. the requested sort -------------------------------------------
    #
    # After every scoring stage and before the window, so a sorted page is a
    # slice of the sorted pool -- exactly the guarantee paging needs. Sorting
    # after the window would let page 2 disagree with page 1 about page 1.
    # A reranker enabled on the same query still reorders the served head,
    # which is the two directives arguing and the last one winning; every
    # shipped config has rerank off, so this is documented rather than fixed.
    if parsed.sort and fused:
        t0 = time.perf_counter()
        by_id = {f.doc_id: f for f in fused}
        ordered = sort_pool(conn, [f.doc_id for f in fused], parsed.sort)
        fused = [by_id[i] for i in ordered if i in by_id]
        mark("sort", t0)

    window = fused[page.offset : page.stop]
    rows = hydrate(conn, [f.doc_id for f in window])
    terms = _snippet_terms(parsed, understanding)
    hits: list[SearchHit] = []
    for f in window:
        row = rows.get(f.doc_id)
        if row is None:
            continue
        hit = _to_hit(row, f, terms)
        hit.cold = f.doc_id in cold
        if ctx is not None:
            hit.context_boost = ctx.boost(f.doc_id)
            hit.context_reasons = ctx.reasons(f.doc_id)
            hit.base_score = f.score / hit.context_boost if hit.context_boost else f.score
        hits.append(hit)

    # --- 5. rerank --------------------------------------------------------
    rr_name = ""
    if config.rerank and hits and not browse:
        t0 = time.perf_counter()
        rr = reranker or get_reranker(s, prov)
        rr_name = rr.name
        # Bound the *scoring*, not just the reorder. `depth=len(hits)` scored
        # the whole page. The reranker is listwise -- one call, a line per
        # candidate, one score demanded back per id -- so the page size sets
        # both the prompt length and the required output length, and a large
        # enough page stops fitting the context window at all. `rerank_depth`
        # is the depth `search.rerank` already documents; rows past it keep
        # their fused order, which is a tradeoff nothing here has measured.
        rr_depth = max(1, s.rerank_depth)
        head = hits[:rr_depth]
        docs = [RerankDoc(h.bookmark_id, h.title, h.snippet) for h in head]
        scores = await rr.score(facet_query or query, docs)
        if len(scores) == len(head):
            hits = reorder(hits, scores, depth=rr_depth)
        mark("rerank", t0)

    # --- 6. one hop out, as its own group ---------------------------------
    #
    # What must be excluded is what the user is *shown*, not what the retriever
    # *considered*. Those are wildly different sets: every vector facet returns
    # `candidates_per_facet` neighbours whether or not they are any good, so the
    # fused pool is ~50-150 documents while `hits` is ~10. Excluding the pool
    # deletes the expansion group outright on a small library and guts it on a
    # large one, because a graph neighbour of a hit is *by construction* the
    # kind of document a vector facet also drags in. Expansion answers a
    # different question from retrieval; a document that lost on topical
    # similarity can still be the right answer to "what came with this?".
    #
    # With paging, "shown" means every page up to this one, not just this page:
    # `fused[:page.stop]`. At `offset=0` that is exactly `hits`, so the shipped
    # behaviour is unchanged.
    expansions: list[Expansion] = []
    if config.graph and hits:
        t0 = time.perf_counter()
        expansions = expand(
            conn,
            [(h.bookmark_id, h.score) for h in hits],
            factor=s.graph_expand_factor,
            limit=expand_limit,
            exclude=[f.doc_id for f in fused[: page.stop]],
        )
        mark("expand", t0)

    exp_rows = hydrate(conn, [e.doc_id for e in expansions])
    expanded: list[SearchHit] = []
    for e in expansions:
        row = exp_rows.get(e.doc_id)
        if row is None:
            continue
        h = _to_hit(row)
        h.score = e.score
        h.base_score = e.score
        h.via = e.via
        h.via_kind = e.kind
        expanded.append(h)

    timings["total"] = (time.perf_counter() - t_start) * 1000
    has_more, capped = page_signals(page, len(fused), truncated=truncated)
    return SearchResponse(
        query=query, hits=hits, expanded=expanded, understanding=understanding,
        config=config.name, facet_sizes={k: len(v) for k, v in lists.items()},
        facet_confidence=facet_confidence,
        context=ctx.as_dict() if ctx else None, rescued=rescued,
        reranker=rr_name, took_ms=timings,
        limit=page.limit, offset=page.offset, depth=page.depth, total=len(fused),
        has_more=has_more, depth_capped=capped, degraded_from=degraded_from,
        # `None` means the query carried no syntax at all -- the compatibility
        # guarantee. An ignored token is syntax the user typed, so `echo()`
        # being non-empty is the condition, not `has_syntax`: a query whose
        # only syntax failed to parse reported nothing and looked plain.
        filters=parsed.echo() or None,
        sort=parsed.sort,
    )
