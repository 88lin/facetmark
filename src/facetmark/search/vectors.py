"""Facets 1 and 2: the two vector rankings.

Facet 1 (``content``) is one vector per bookmark and needs no explanation --
it is what every existing tool does.

Facet 2 (``intent``) is the one that is not obvious. The vectors are not
documents; they are *hypothetical questions the page answers*, generated at
index time and filtered for self-consistency. A KNN over that space is
therefore a question-to-question match, which is a much shorter semantic jump
than question-to-document when the user's phrasing shares no vocabulary with
the page. That is exactly the ``q_vague`` case: "那个能把网页转成 markdown 的
东西" against a page that only ever says "HTML to Markdown converter".

Two mechanical details matter here:

*Over-fetch.* Several intent vectors belong to the same bookmark (up to
``intent_keep_n``), so a KNN of k=50 over intent space can collapse to far
fewer than 50 distinct bookmarks. We ask for ``k * keep_n`` and truncate after
deduplication.

*Best-rank dedup.* When a bookmark is hit by three of its own intent queries,
it takes the position of its *best* one. Counting all three would let a
verbose page outvote a precise one purely by having generated more queries.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence

from ..config import Settings, get_settings
from ..db import knn_content, knn_intent, vec_tables_exist
from ..providers import Provider, get_provider


def content_list(
    conn: sqlite3.Connection, query_vec: Sequence[float], *, limit: int = 50
) -> list[int]:
    """Facet 1: nearest content vectors, best first."""
    return [bid for bid, _ in content_list_scored(conn, query_vec, limit=limit)]


def content_list_scored(
    conn: sqlite3.Connection, query_vec: Sequence[float], *, limit: int = 50
) -> list[tuple[int, float]]:
    """:func:`content_list` with a similarity attached, higher being better.

    sqlite-vec reports L2 distance between unit vectors; negating it gives the
    same convention the lexical facets use. The abstention margin only ever
    looks at differences between a facet's own scores, so the affine offset
    between this and bm25 does not matter -- which is the point of measuring
    confidence within a facet rather than across facets.
    """
    if not vec_tables_exist(conn):
        return []
    return [(bid, -dist) for bid, dist in knn_content(conn, query_vec, limit)]


def intent_list(
    conn: sqlite3.Connection,
    query_vec: Sequence[float],
    *,
    limit: int = 50,
    over_fetch: int = 4,
) -> list[int]:
    """Facet 2: nearest intent vectors, mapped to bookmarks, best rank wins."""
    return [
        bid
        for bid, _ in intent_list_scored(
            conn, query_vec, limit=limit, over_fetch=over_fetch
        )
    ]


def intent_list_scored(
    conn: sqlite3.Connection,
    query_vec: Sequence[float],
    *,
    limit: int = 50,
    over_fetch: int = 4,
) -> list[tuple[int, float]]:
    """:func:`intent_list` with a similarity attached, higher being better."""
    if not vec_tables_exist(conn):
        return []
    k = max(limit * max(over_fetch, 1), limit)
    hits = knn_intent(conn, query_vec, k)
    if not hits:
        return []
    ids = [i for i, _ in hits]
    rows = conn.execute(
        f"SELECT id, bookmark_id FROM intent_query WHERE id IN ({','.join('?' * len(ids))})",
        ids,
    ).fetchall()
    owner = {int(r["id"]): int(r["bookmark_id"]) for r in rows}

    out: list[tuple[int, float]] = []
    seen: set[int] = set()
    for intent_id, dist in hits:           # already ordered by distance
        bid = owner.get(intent_id)
        if bid is None or bid in seen:
            continue
        seen.add(bid)
        # A bookmark inherits the score of its best-matching intent query,
        # which is the first one seen because `hits` is distance-ordered.
        out.append((bid, -dist))
        if len(out) >= limit:
            break
    return out


def vector_lists_from_vec(
    conn: sqlite3.Connection,
    query_vec: Sequence[float],
    *,
    limit: int = 50,
    want_content: bool = True,
    want_intent: bool = True,
) -> dict[str, list[int]]:
    return {
        k: [i for i, _ in v]
        for k, v in vector_lists_from_vec_scored(
            conn, query_vec, limit=limit, want_content=want_content, want_intent=want_intent
        ).items()
    }


def vector_lists_from_vec_scored(
    conn: sqlite3.Connection,
    query_vec: Sequence[float],
    *,
    limit: int = 50,
    want_content: bool = True,
    want_intent: bool = True,
) -> dict[str, list[tuple[int, float]]]:
    out: dict[str, list[tuple[int, float]]] = {}
    if want_content:
        c = content_list_scored(conn, query_vec, limit=limit)
        if c:
            out["content"] = c
    if want_intent:
        i = intent_list_scored(conn, query_vec, limit=limit)
        if i:
            out["intent"] = i
    return out


async def vector_lists(
    conn: sqlite3.Connection,
    query: str,
    *,
    provider: Provider | None = None,
    settings: Settings | None = None,
    limit: int = 50,
    want_content: bool = True,
    want_intent: bool = True,
) -> tuple[dict[str, list[int]], list[float] | None]:
    """Embed the query once, then run both vector facets against it.

    Returns the lists plus the query vector, because the caller (graph
    expansion, ``find_related``) frequently needs the vector again and a second
    embedding call would be a second billable request for the same string.
    """
    if not (want_content or want_intent) or not vec_tables_exist(conn):
        return {}, None
    s = settings or get_settings()
    prov = provider or get_provider(s)
    vec = (await prov.embed([query]))[0]
    return vector_lists_from_vec(
        conn, vec, limit=limit, want_content=want_content, want_intent=want_intent
    ), vec


async def vector_lists_scored(
    conn: sqlite3.Connection,
    query: str,
    *,
    provider: Provider | None = None,
    settings: Settings | None = None,
    limit: int = 50,
    want_content: bool = True,
    want_intent: bool = True,
) -> tuple[dict[str, list[tuple[int, float]]], list[float] | None]:
    """:func:`vector_lists` with similarities kept, for the abstention path."""
    if not (want_content or want_intent) or not vec_tables_exist(conn):
        return {}, None
    s = settings or get_settings()
    prov = provider or get_provider(s)
    vec = (await prov.embed([query]))[0]
    return vector_lists_from_vec_scored(
        conn, vec, limit=limit, want_content=want_content, want_intent=want_intent
    ), vec
