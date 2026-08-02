"""Facet 2: hypothetical queries, filtered by whether they actually work.

A language model asked for eight ways someone might search for a page will
happily produce eight. Some are good. Some restate the title. Some are about a
different page entirely, because the model drifted. Indexing all eight puts the
bad ones in the same vector space as the good ones, where they pull unrelated
searches toward this bookmark -- the failure mode that makes query expansion a
net loss in several published evaluations.

The filter is a round trip. Embed the candidate, search the library with the
facets that already exist (content and lexical -- *never* the intent facet
itself, which would be circular), and ask: did this query find the page it was
written for? A query that cannot retrieve its own source document will not
retrieve it for the user either. Keep the best ``intent_keep_n``, discard the
rest, and record every candidate's probe rank so the evaluation can show what
was thrown away and why.

This is Doc2Query-minus applied to a personal library: the reported gain there
comes precisely from dropping the expansions that do not survive this check.

**Known degeneracy.** The probe asks for ``top_k * PROBE_MULTIPLIER`` candidates.
When the library holds fewer bookmarks than that, every document is in the
result set by default and the filter accepts everything -- a vector index has no
distance floor, so "nearest" says nothing about "near". It becomes a real filter
once the library is larger than the probe depth (30 by default), which any
library worth building this for already is. Small libraries lose the filter, not
the facet.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass, field

from ..config import Settings, get_settings
from ..db import ensure_vec_tables, knn_content, upsert_intent_vector
from ..providers import Provider, get_provider
from ..search.lexical import lexical_lists
from ..search.rrf import rrf

#: How deep the probe looks before calling a candidate a failure. Wider than
#: the number of results a user sees, because the point is "can this query find
#: the page at all", not "does it win".
PROBE_MULTIPLIER = 3


@dataclass(slots=True)
class IntentReport:
    bookmarks: int = 0
    candidates: int = 0
    kept: int = 0
    dropped: int = 0
    bookmarks_with_none_kept: int = 0
    probe_top_k: int = 0
    keep_n: int = 0
    #: Vectors stored straight from the probe, so `embed_intents` finds nothing
    #: left to pay for.
    vectors_written: int = 0
    rank_histogram: dict[str, int] = field(default_factory=dict)

    @property
    def keep_rate(self) -> float:
        return self.kept / self.candidates if self.candidates else 0.0

    def as_dict(self) -> dict:
        return {
            "bookmarks": self.bookmarks, "candidates": self.candidates,
            "kept": self.kept, "dropped": self.dropped,
            "keep_rate": round(self.keep_rate, 4),
            "bookmarks_with_none_kept": self.bookmarks_with_none_kept,
            "probe_top_k": self.probe_top_k, "keep_n": self.keep_n,
            "vectors_written": self.vectors_written,
            "rank_histogram": self.rank_histogram,
        }


def probe(
    conn: sqlite3.Connection,
    query_text: str,
    query_vec: Sequence[float],
    *,
    top_k: int,
) -> list[int]:
    """Search with content + lexical only, and return the fused id ranking."""
    depth = top_k * PROBE_MULTIPLIER
    lists: dict[str, list[int]] = {}
    hits = knn_content(conn, query_vec, depth)
    if hits:
        lists["content"] = [bid for bid, _ in hits]
    lists.update(lexical_lists(conn, query_text, limit=depth))
    if not lists:
        return []
    return [f.doc_id for f in rrf(lists, limit=depth)]


def _bucket(rank: int | None, top_k: int) -> str:
    if rank is None:
        return "not_found"
    if rank == 1:
        return "1"
    if rank <= 3:
        return "2-3"
    if rank <= top_k:
        return f"4-{top_k}"
    return f">{top_k}"


async def filter_intents(
    conn: sqlite3.Connection,
    *,
    provider: Provider | None = None,
    settings: Settings | None = None,
    ids: Sequence[int] | None = None,
    keep_n: int | None = None,
    progress=None,
) -> IntentReport:
    """Score every candidate query, keep the ones that find their own page."""
    s = settings or get_settings()
    prov = provider or get_provider(s)
    ensure_vec_tables(conn, s.embed_dim, s.embed_model)
    k_keep = s.intent_keep_n if keep_n is None else keep_n
    top_k = s.intent_probe_top_k
    rep = IntentReport(probe_top_k=top_k, keep_n=k_keep)

    where = ""
    params: list[object] = []
    if ids:
        where = f" WHERE bookmark_id IN ({','.join('?' * len(ids))})"
        params = list(ids)
    rows = conn.execute(
        f"SELECT id, bookmark_id, text FROM intent_query{where} ORDER BY bookmark_id, id",
        params,
    ).fetchall()
    if not rows:
        return rep

    rep.candidates = len(rows)
    rep.bookmarks = len({r["bookmark_id"] for r in rows})

    from .vectors import BATCH

    ranks: dict[int, int | None] = {}
    # The vector computed to probe with is the same vector the intent facet will
    # later search against -- same text, same model. Letting it fall out of
    # scope means `embed_intents` pays for every kept query a second time: on a
    # 2,376-page library that is ~9,500 redundant embedding calls, half again on
    # top of what the filter itself costs. Only candidates that could still be
    # kept are held, so the peak is bounded by the passing set, not by the
    # candidate set.
    passing_vecs: dict[int, Sequence[float]] = {}
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        vecs = await prov.embed([r["text"] for r in chunk])
        for r, vec in zip(chunk, vecs, strict=True):
            ordering = probe(conn, r["text"], vec, top_k=top_k)
            rank = (
                ordering.index(r["bookmark_id"]) + 1 if r["bookmark_id"] in ordering else None
            )
            ranks[r["id"]] = rank
            if rank is not None and rank <= top_k:
                passing_vecs[r["id"]] = vec
        if progress is not None:
            progress(min(i + BATCH, len(rows)), len(rows))

    by_bookmark: dict[int, list[sqlite3.Row]] = {}
    for r in rows:
        by_bookmark.setdefault(r["bookmark_id"], []).append(r)

    hist: dict[str, int] = {}
    updates: list[tuple[int, int | None, int]] = []
    for cands in by_bookmark.values():
        scored = [(ranks.get(c["id"]), c["id"]) for c in cands]
        for rank, _ in scored:
            key = _bucket(rank, top_k)
            hist[key] = hist.get(key, 0) + 1
        passing = sorted(
            [(rk, cid) for rk, cid in scored if rk is not None and rk <= top_k]
        )[:k_keep]
        keep_ids = {cid for _, cid in passing}
        if not keep_ids:
            rep.bookmarks_with_none_kept += 1
        for rank, cid in scored:
            updates.append((1 if cid in keep_ids else 0, rank, cid))

    conn.executemany(
        "UPDATE intent_query SET kept=?, probe_rank=? WHERE id=?", updates
    )
    for kept_flag, _rank, cid in updates:
        if kept_flag and cid in passing_vecs:
            upsert_intent_vector(conn, cid, passing_vecs[cid])
            rep.vectors_written += 1
    # Anything that just lost its `kept` flag must lose its vector too, or the
    # intent facet keeps answering with a query the filter rejected.
    conn.execute(
        "DELETE FROM vec_intent WHERE intent_id IN (SELECT id FROM intent_query WHERE kept=0)"
    )
    conn.commit()

    rep.kept = sum(1 for k, _, _ in updates if k == 1)
    rep.dropped = rep.candidates - rep.kept
    rep.rank_histogram = dict(sorted(hist.items()))
    return rep
