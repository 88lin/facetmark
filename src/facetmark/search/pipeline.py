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

from ..config import Settings, get_settings
from ..db import jload
from ..providers import MockProvider, Provider, get_provider
from . import abstain
from .context import ContextSignals, build_context, window_filter
from .decay import cold_bookmark_ids, decay_hits
from .graph import Expansion, expand
from .lexical import lexical_lists, lexical_lists_scored
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
    #: Only set on rows in the expansion group.
    via: int | None = None
    via_kind: str = ""

    def as_dict(self) -> dict:
        d = {
            "bookmark_id": self.bookmark_id, "url": self.url, "title": self.title,
            "score": round(self.score, 6), "base_score": round(self.base_score, 6),
            "facets": self.facets, "ranks": self.ranks,
            "context_boost": round(self.context_boost, 4),
            "context_reasons": self.context_reasons, "cold": self.cold,
            "folder": self.folder, "domain": self.domain, "date_added": self.date_added,
            "snippet": self.snippet, "utility": self.utility,
            "content_type": self.content_type, "topics": self.topics,
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

    def as_dict(self) -> dict:
        return {
            "query": self.query,
            "hits": [h.as_dict() for h in self.hits],
            "expanded": [h.as_dict() for h in self.expanded],
            "understanding": self.understanding.as_dict() if self.understanding else None,
            "config": self.config,
            "facet_sizes": self.facet_sizes,
            "facet_confidence": self.facet_confidence,
            "context": self.context,
            "rescued": self.rescued,
            "reranker": self.reranker,
            "took_ms": {k: round(v, 2) for k, v in self.took_ms.items()},
        }

    @property
    def ids(self) -> list[int]:
        return [h.bookmark_id for h in self.hits]


# ---------------------------------------------------------------------------
# hydration
# ---------------------------------------------------------------------------

_ROW_SQL = """
SELECT b.id, b.url, b.title, b.folder, b.domain, b.date_added,
       e.summary, e.utility, e.content_type, e.topics,
       substr(c.body_text, 1, 400) AS body_head
FROM bookmark b
LEFT JOIN enrichment e ON e.bookmark_id = b.id
LEFT JOIN content    c ON c.bookmark_id = b.id
WHERE b.id IN ({marks})
"""


def _snippet(summary: str | None, body_head: str | None) -> str:
    text = (summary or "").strip() or (body_head or "").strip()
    text = " ".join(text.split())
    return text[:SNIPPET_CHARS]


def hydrate(conn: sqlite3.Connection, ids: Sequence[int]) -> dict[int, dict]:
    if not ids:
        return {}
    marks = ",".join("?" * len(ids))
    rows = conn.execute(_ROW_SQL.format(marks=marks), list(ids)).fetchall()
    return {int(r["id"]): dict(r) for r in rows}


def _to_hit(row: Mapping, fused: Fused | None = None) -> SearchHit:
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
        snippet=_snippet(row["summary"], row["body_head"]),
        utility=str(row["utility"] or ""),
        content_type=str(row["content_type"] or ""),
        topics=jload(row["topics"], []),
    )


# ---------------------------------------------------------------------------
# fast path
# ---------------------------------------------------------------------------


def quick_search(
    conn: sqlite3.Connection, query: str, *, limit: int = 20, k: int = DEFAULT_K
) -> SearchResponse:
    """Lexical-only first paint. Synchronous, no model call, no network."""
    t0 = time.perf_counter()
    u = classify(query)
    lists = lexical_lists(conn, query, limit=max(limit * 3, 30))
    fused = rrf(lists, k=k, weights=DEFAULT_FACET_WEIGHTS, limit=limit)
    rows = hydrate(conn, [f.doc_id for f in fused])
    hits = [_to_hit(rows[f.doc_id], f) for f in fused if f.doc_id in rows]
    return SearchResponse(
        query=query, hits=hits, understanding=u, config="quick",
        facet_sizes={k2: len(v) for k2, v in lists.items()},
        took_ms={"total": (time.perf_counter() - t0) * 1000},
    )


# ---------------------------------------------------------------------------
# full path
# ---------------------------------------------------------------------------


async def search(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 20,
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

    per_facet = max(s.candidates_per_facet, limit)

    # --- 2. facets --------------------------------------------------------
    # Two paths. The default one takes ranked ids and throws the scores away,
    # because RRF is deliberately rank-only. The abstention path keeps them,
    # because deciding whether a facet has an opinion requires looking at the
    # shape of its score distribution -- see `facetmark.search.abstain`.
    lists: dict[str, list[int]] = {}
    facet_confidence: dict[str, float] = {}
    if config.abstain_margin > 0.0:
        t0 = time.perf_counter()
        scored: dict[str, list[tuple[int, float]]] = {}
        if config.facets & LEXICAL_FACETS:
            for name, rows in lexical_lists_scored(conn, query, limit=per_facet).items():
                if name in config.facets:
                    scored[name] = rows
        mark("lexical", t0)

        t0 = time.perf_counter()
        if config.facets & VECTOR_FACETS:
            vrows, _vec = await vector_lists_scored(
                conn, query, provider=prov, settings=s, limit=per_facet,
                want_content="content" in config.facets,
                want_intent="intent" in config.facets,
            )
            scored.update(vrows)
        mark("vectors", t0)

        t0 = time.perf_counter()
        lists, facet_confidence = abstain.apply(scored, config.abstain_margin)
        mark("abstain", t0)
    else:
        t0 = time.perf_counter()
        if config.facets & LEXICAL_FACETS:
            for name, ids in lexical_lists(conn, query, limit=per_facet).items():
                if name in config.facets:
                    lists[name] = ids
        mark("lexical", t0)

        t0 = time.perf_counter()
        if config.facets & VECTOR_FACETS:
            vlists, _vec = await vector_lists(
                conn, query, provider=prov, settings=s, limit=per_facet,
                want_content="content" in config.facets,
                want_intent="intent" in config.facets,
            )
            lists.update(vlists)
        mark("vectors", t0)

    # --- 3. fusion --------------------------------------------------------
    t0 = time.perf_counter()
    fused = rrf(lists, k=s.rrf_k, weights=config.facet_weights, max_bonus=config.max_bonus)
    mark("fuse", t0)

    # A purely episodic query ("上个月存的那些") has no topic for any facet to
    # match. The window *is* the query, so it becomes the candidate set.
    if not fused and understanding.time_window is not None:
        ids = window_filter(conn, understanding.time_window)[: per_facet]
        fused = rrf({"episodic_window": ids}, k=s.rrf_k)
        lists["episodic_window"] = ids

    ctx: ContextSignals | None = None
    if fused and config.wants_context(understanding):
        t0 = time.perf_counter()
        head = [f.doc_id for f in fused[:200]]
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
    rescued = False
    cold: set[int] = set()
    if config.decay and fused:
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

    page = fused[:limit]
    rows = hydrate(conn, [f.doc_id for f in page])
    hits: list[SearchHit] = []
    for f in page:
        row = rows.get(f.doc_id)
        if row is None:
            continue
        hit = _to_hit(row, f)
        hit.cold = f.doc_id in cold
        if ctx is not None:
            hit.context_boost = ctx.boost(f.doc_id)
            hit.context_reasons = ctx.reasons(f.doc_id)
            hit.base_score = f.score / hit.context_boost if hit.context_boost else f.score
        hits.append(hit)

    # --- 5. rerank --------------------------------------------------------
    rr_name = ""
    if config.rerank and hits:
        t0 = time.perf_counter()
        rr = reranker or get_reranker(s, prov)
        rr_name = rr.name
        docs = [RerankDoc(h.bookmark_id, h.title, h.snippet) for h in hits]
        scores = await rr.score(query, docs)
        if len(scores) == len(hits):
            hits = reorder(hits, scores, depth=len(hits))
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
    expansions: list[Expansion] = []
    if config.graph and hits:
        t0 = time.perf_counter()
        expansions = expand(
            conn,
            [(h.bookmark_id, h.score) for h in hits],
            factor=s.graph_expand_factor,
            limit=expand_limit,
            exclude=[h.bookmark_id for h in hits],
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
    return SearchResponse(
        query=query, hits=hits, expanded=expanded, understanding=understanding,
        config=config.name, facet_sizes={k: len(v) for k, v in lists.items()},
        facet_confidence=facet_confidence,
        context=ctx.as_dict() if ctx else None, rescued=rescued,
        reranker=rr_name, took_ms=timings,
    )
