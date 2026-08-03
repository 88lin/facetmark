"""Reciprocal rank fusion.

``score(d) = sum_r 1 / (k + rank_r(d))``, k = 60.

Rank fusion rather than score fusion, because the four facets do not produce
comparable numbers: BM25 is unbounded and corpus-dependent, cosine distance is
bounded, and the contextual facet produces a hand-built weight. Normalising
those onto a common scale means inventing a mapping and then tuning it. Ranks
need no mapping.

k = 60 is the value from the original TREC work and is deliberately not tuned.
It is large enough that the top few ranks of a list do not dominate the sum, and
a facet that ranks a document 1st contributes 1/61 while one that ranks it 50th
contributes 1/110 -- present, but outvoted.

**What the sum cannot do.** Being outvoted is the point right up until the
voters are mediocre. With the shipped constants, a document every facet ranks
dead last within the candidate depth scores 1.50x (config B) or 2.05x (C/D) what
a document a single facet ranks *first* scores, and two full-weight facets that
both merely recall a document beat a sole-facet #1 at every rank inside the
candidate depth. That is arithmetic, not tuning -- see
``docs/w2-fusion-anatomy.md`` §3. ``max_bonus`` below is the optional CombMAX
term that can restore the guarantee; :func:`guarantee_bonus` computes how large
it has to be. It ships off.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

DEFAULT_K = 60


@dataclass(slots=True)
class Fused:
    doc_id: int
    score: float
    #: facet name -> rank (1-based) in that facet's list
    ranks: dict[str, int] = field(default_factory=dict)
    #: facet name -> that facet's contribution to the score
    contributions: dict[str, float] = field(default_factory=dict)
    #: the CombMAX term, if ``max_bonus`` was non-zero. Kept separate from
    #: ``contributions`` because it is not a facet's vote: it is a bonus paid to
    #: whichever facet was most confident, and folding it into that facet's
    #: entry would misreport how much the sum contributed.
    max_term: float = 0.0

    @property
    def facets(self) -> list[str]:
        return sorted(self.ranks)


def guarantee_bonus(k: int, depth: int, weights: Mapping[str, float]) -> float:
    """Crossover ``max_bonus`` between a sole-facet #1 and an all-last document.

    The guarantee at stake is the weakest one available: *a document some facet
    ranks first must outscore a document no facet ranks better than last*. Pure
    RRF does not provide it. Solving the boundary case

        (1 + L) * w_top / (k + 1)  ==  (W + L * w_top) / (k + depth)

    for L, where ``w_top`` is the largest facet weight and ``W`` their sum,
    gives the value below. It is a crossover, not a strict minimum: exactly at
    it the two documents score the same and the order falls to the id
    tiebreak, and every rival short of the worst case -- one that misses a
    facet, or that any facet ranks above last -- loses outright. Values above it
    win the worst case too.

    With the shipped constants it is 1.116 for config B and 2.361 for C/D --
    **greater than one**, i.e. the max term has to outweigh the entire sum it is
    correcting. That is the finding, not a recommendation: an additive fusion
    cannot protect a confident single facet cheaply. Any value actually shipped
    has to be justified on a query set that was not used to generate the
    hypothesis.

    Returns 0.0 when the guarantee already holds. That happens when ``depth``
    is large: last place at rank 200 is worth much less than last place at rank
    50, so a deeper candidate list dilutes the all-last document until it loses
    unaided. For these weights the bonus vanishes at depth 166. The shallow
    list is the cause, not the deep one.
    """
    if not weights:
        return 0.0
    w_top = max(weights.values())
    total = sum(weights.values())
    lo, hi = k + 1, k + depth
    den = w_top * (hi - lo)
    if den <= 0 or w_top <= 0:
        return 0.0
    return max(0.0, (lo * total - hi * w_top) / den)


def rrf(
    ranked_lists: Mapping[str, Sequence[int]],
    *,
    k: int = DEFAULT_K,
    weights: Mapping[str, float] | None = None,
    limit: int | None = None,
    max_bonus: float = 0.0,
) -> list[Fused]:
    """Fuse per-facet ranked id lists into one ordered list.

    ``weights`` scales a facet's contribution. It defaults to 1.0 everywhere;
    the search layer uses it only to damp facets that are structurally noisier,
    never to tune quality per query.

    ``max_bonus`` adds a CombMAX term::

        score(d) = sum_f w_f / (k + r_f)  +  max_bonus * max_f w_f / (k + r_f)

    At 0.0 -- the shipped value -- this function is bit-identical to plain RRF.
    Above 0.0 it buys back some of the single-facet confidence the sum throws
    away; :func:`guarantee_bonus` says how much is needed to buy back all of it.
    """
    acc: dict[int, Fused] = {}
    for facet, ids in ranked_lists.items():
        w = 1.0 if weights is None else float(weights.get(facet, 1.0))
        if w == 0.0:
            continue
        seen: set[int] = set()
        rank = 0
        for doc_id in ids:
            if doc_id in seen:      # a facet may legitimately emit duplicates
                continue
            seen.add(doc_id)
            rank += 1
            contrib = w / (k + rank)
            entry = acc.get(doc_id)
            if entry is None:
                entry = acc[doc_id] = Fused(doc_id, 0.0)
            entry.score += contrib
            entry.ranks[facet] = rank
            entry.contributions[facet] = contrib
    if max_bonus:
        # Second pass rather than tracking a running max in the loop above: the
        # loop is per-facet, so a running max would be correct but the branch
        # would sit in the hot path of the shipped (max_bonus == 0) config.
        for entry in acc.values():
            entry.max_term = max_bonus * max(entry.contributions.values())
            entry.score += entry.max_term
    out = sorted(acc.values(), key=lambda f: (-f.score, f.doc_id))
    return out[:limit] if limit else out


def rank_of(fused: Iterable[Fused], doc_id: int) -> int | None:
    """1-based position of ``doc_id``, or None. Used by the intent filter."""
    for i, f in enumerate(fused, start=1):
        if f.doc_id == doc_id:
            return i
    return None
