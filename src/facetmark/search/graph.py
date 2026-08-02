"""One-hop graph expansion, kept in its own lane.

Expansion answers a different question from search. Search answers "what
matches?"; expansion answers "what came with the things that matched?". Mixing
the two into one list is how a related-items feature turns into a relevance
bug: the user reads a ranked list top-down assuming every row is an answer, and
row 4 is suddenly a thing that merely sat next to an answer.

So the expansion is returned as a **separate group** and the UI renders it
under its own heading. That is also why the score carries ``via`` and ``kind``:
an expanded row is only defensible if it can say *"because it was saved in the
same sitting as <the thing you found>"*.

One hop, never two. Two hops through ``same_domain`` walks github.com to
everything; two hops through ``session`` chains episodes days apart into one
blob. The 1-hop restriction is not a performance compromise, it is what keeps
the edge semantics true.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

#: An expanded item's score is this fraction of its seed's, times the edge
#: weight. It is < 1 by construction so a 1-hop neighbour can never outrank the
#: seed that produced it.
DEFAULT_FACTOR = 0.6

#: Seeds are taken from the top of the fused list only.
DEFAULT_SEEDS = 10


@dataclass(slots=True)
class Expansion:
    doc_id: int
    score: float
    via: int
    kind: str
    edge_weight: float

    def as_dict(self) -> dict:
        return {
            "bookmark_id": self.doc_id, "score": round(self.score, 6),
            "via": self.via, "kind": self.kind, "edge_weight": self.edge_weight,
        }


def expand(
    conn: sqlite3.Connection,
    seeds: Sequence[tuple[int, float]],
    *,
    factor: float = DEFAULT_FACTOR,
    limit: int = 10,
    exclude: Iterable[int] = (),
    kinds: Sequence[str] | None = None,
    max_seeds: int = DEFAULT_SEEDS,
    per_seed: int = 20,
) -> list[Expansion]:
    """Walk one hop out from ``seeds`` (``(bookmark_id, score)``, best first)."""
    seeds = list(seeds)[:max_seeds]
    if not seeds or limit <= 0:
        return []
    blocked = set(exclude) | {s for s, _ in seeds}

    sql = "SELECT dst, kind, weight FROM edge WHERE src = ?"
    params_tail: list[object] = []
    if kinds:
        sql += f" AND kind IN ({','.join('?' * len(kinds))})"
        params_tail += list(kinds)
    sql += " ORDER BY weight DESC, dst LIMIT ?"

    best: dict[int, Expansion] = {}
    for seed_id, seed_score in seeds:
        rows = conn.execute(sql, [seed_id, *params_tail, per_seed]).fetchall()
        for r in rows:
            dst = int(r["dst"])
            if dst in blocked:
                continue
            score = factor * float(seed_score) * float(r["weight"])
            cur = best.get(dst)
            if cur is None or score > cur.score:
                best[dst] = Expansion(dst, score, seed_id, str(r["kind"]), float(r["weight"]))
    out = sorted(best.values(), key=lambda e: (-e.score, e.doc_id))
    return out[:limit]


def related(
    conn: sqlite3.Connection, bookmark_id: int, *, kind: str | None = None, limit: int = 20
) -> list[Expansion]:
    """Neighbours of a single bookmark. Backs the ``find_related`` MCP tool.

    ``supersession`` is the one directed kind: an outgoing edge means *this
    bookmark was replaced by* ``dst``, so the direction must not be collapsed.
    """
    kinds = [kind] if kind else None
    return expand(
        conn, [(bookmark_id, 1.0)], factor=1.0, limit=limit, kinds=kinds, per_seed=limit
    )
