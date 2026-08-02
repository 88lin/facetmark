"""Turn enriched rows into vectors.

Two vector spaces, both written through :mod:`facetmark.db` so nothing else has
to know about sqlite-vec:

``vec_content``  one vector per bookmark, over title + summary + topics +
                 body head. This is facet 1.
``vec_intent``   one vector per *kept* intent query. This is facet 2, and it is
                 the reason the same embedding model must be used for both:
                 a query embedding is compared against both spaces.

Vectors are L2-normalised on write (in ``db.upsert_*``), so plain L2 distance
ranks identically to cosine and the sqlite-vec distance metric never has to be
configured.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass

from ..config import Settings, get_settings
from ..db import (
    ensure_vec_tables,
    jload,
    upsert_content_vector,
    upsert_intent_vector,
)
from ..providers import Provider, get_provider
from ..text import truncate_head_tail

#: Embedding APIs charge per token and rate-limit per request. 64 is small
#: enough to keep a failed batch cheap to redo and large enough that a
#: 1,700-bookmark library is ~27 requests, not 1,700.
BATCH = 64

#: Body text contributes this many characters to the content vector. Beyond
#: roughly this length the vector drifts toward the page's boilerplate.
CONTENT_BODY_CHARS = 2000


@dataclass(slots=True)
class VectorReport:
    content_written: int = 0
    intent_written: int = 0
    content_skipped: int = 0
    dim: int = 0
    model: str = ""

    def as_dict(self) -> dict:
        return {
            "content_written": self.content_written,
            "intent_written": self.intent_written,
            "content_skipped": self.content_skipped,
            "dim": self.dim, "model": self.model,
        }


def content_text(
    *, title: str, summary: str, topics: Sequence[str], entities: Sequence[str], body: str
) -> str:
    """What actually gets embedded for facet 1.

    Title first because it is short and high-signal; summary next; topics and
    entities as a compact keyword line; then a bounded slice of the body.
    """
    parts = [title.strip()]
    if summary:
        parts.append(summary.strip())
    kw = " · ".join([*topics, *entities][:12])
    if kw:
        parts.append(kw)
    if body:
        parts.append(truncate_head_tail(body, CONTENT_BODY_CHARS))
    return "\n".join(p for p in parts if p)


def _content_rows(conn: sqlite3.Connection, force: bool, ids: Sequence[int] | None):
    where = ["b.indexable=1", "b.privacy_skipped=0"]
    params: list[object] = []
    if ids:
        where.append(f"b.id IN ({','.join('?' * len(ids))})")
        params.extend(ids)
    if not force:
        where.append("b.id NOT IN (SELECT bookmark_id FROM vec_content)")
    sql = (
        "SELECT b.id, b.title, c.body_text, e.summary, e.topics, e.entities "
        "FROM bookmark b "
        "LEFT JOIN content c    ON c.bookmark_id = b.id "
        "LEFT JOIN enrichment e ON e.bookmark_id = b.id "
        f"WHERE {' AND '.join(where)} ORDER BY b.id"
    )
    return conn.execute(sql, params).fetchall()


async def embed_content(
    conn: sqlite3.Connection,
    *,
    provider: Provider | None = None,
    settings: Settings | None = None,
    force: bool = False,
    ids: Sequence[int] | None = None,
    progress=None,
) -> VectorReport:
    s = settings or get_settings()
    prov = provider or get_provider(s)
    ensure_vec_tables(conn, s.embed_dim, s.embed_model)
    rep = VectorReport(dim=s.embed_dim, model=s.embed_model)

    rows = _content_rows(conn, force, ids)
    pending: list[tuple[int, str]] = []
    for r in rows:
        text = content_text(
            title=r["title"] or "", summary=r["summary"] or "",
            topics=jload(r["topics"], []), entities=jload(r["entities"], []),
            body=r["body_text"] or "",
        )
        if text.strip():
            pending.append((r["id"], text))
        else:
            rep.content_skipped += 1

    for i in range(0, len(pending), BATCH):
        chunk = pending[i:i + BATCH]
        vecs = await prov.embed([t for _, t in chunk])
        for (bid, _), vec in zip(chunk, vecs, strict=True):
            upsert_content_vector(conn, bid, vec)
        rep.content_written += len(chunk)
        if progress is not None:
            progress("content", rep.content_written, len(pending))
    conn.commit()
    return rep


async def embed_intents(
    conn: sqlite3.Connection,
    *,
    provider: Provider | None = None,
    settings: Settings | None = None,
    force: bool = False,
    progress=None,
) -> VectorReport:
    """Embed the queries that survived the self-consistency filter."""
    s = settings or get_settings()
    prov = provider or get_provider(s)
    ensure_vec_tables(conn, s.embed_dim, s.embed_model)
    rep = VectorReport(dim=s.embed_dim, model=s.embed_model)

    sql = "SELECT id, text FROM intent_query WHERE kept=1"
    if not force:
        sql += " AND id NOT IN (SELECT intent_id FROM vec_intent)"
    rows = conn.execute(sql + " ORDER BY id").fetchall()
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        vecs = await prov.embed([r["text"] for r in chunk])
        for r, vec in zip(chunk, vecs, strict=True):
            upsert_intent_vector(conn, r["id"], vec)
        rep.intent_written += len(chunk)
        if progress is not None:
            progress("intent", rep.intent_written, len(rows))
    conn.commit()
    return rep


async def embed_query(
    query: str, *, provider: Provider | None = None, settings: Settings | None = None
) -> list[float]:
    prov = provider or get_provider(settings)
    return (await prov.embed([query]))[0]
