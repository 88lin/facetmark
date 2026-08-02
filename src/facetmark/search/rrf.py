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

    @property
    def facets(self) -> list[str]:
        return sorted(self.ranks)


def rrf(
    ranked_lists: Mapping[str, Sequence[int]],
    *,
    k: int = DEFAULT_K,
    weights: Mapping[str, float] | None = None,
    limit: int | None = None,
) -> list[Fused]:
    """Fuse per-facet ranked id lists into one ordered list.

    ``weights`` scales a facet's contribution. It defaults to 1.0 everywhere;
    the search layer uses it only to damp facets that are structurally noisier,
    never to tune quality per query.
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
    out = sorted(acc.values(), key=lambda f: (-f.score, f.doc_id))
    return out[:limit] if limit else out


def rank_of(fused: Iterable[Fused], doc_id: int) -> int | None:
    """1-based position of ``doc_id``, or None. Used by the intent filter."""
    for i, f in enumerate(fused, start=1):
        if f.doc_id == doc_id:
            return i
    return None
