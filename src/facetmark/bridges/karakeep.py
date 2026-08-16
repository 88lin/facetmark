"""A karakeep search provider, so facetmark stops growing its own front end.

karakeep (https://github.com/karakeep-app/karakeep) already solves everything
around retrieval that this project was slowly and badly reimplementing: a
browser extension, a mobile app, a headless-Chrome crawler with readability
extraction, asset archiving, multi-user accounts, tag automation, a web UI, and
Docker/Helm deployment. Its ranking, on the other hand, is a plugin -- it ships
MeiliSearch behind a four-method interface and nothing else in the codebase
assumes which implementation is behind it.

That interface is the whole integration surface (``packages/shared/search.ts``)::

    addDocuments(documents, options?)   -> void
    deleteDocuments(ids, options?)      -> void
    search(options)                     -> {hits: [{id, score?}], totalHits, processingTimeMs}
    clearIndex()                        -> void

This module implements those four operations against a facetmark library, and
``facetmark.api`` exposes them under ``/karakeep/*`` so the TypeScript side can
be a thin HTTP forwarder (``integrations/karakeep/``).

What the mapping does and does not preserve
-------------------------------------------

* ``content`` is karakeep's crawled article text. It goes straight into
  facetmark's ``content`` table, which is the single biggest thing this bridge
  buys: facetmark's own crawler is the slowest part of a first index, and
  karakeep has already paid that cost.
* ``tags`` become the ``folder`` string, joined with ``" / "``. karakeep has no
  folder tree, and tags are the closest thing to the co-filing signal that
  facetmark's folder-peer context feature reads. It is a real approximation, not
  an identity: a page with five tags looks like a deeply nested folder path.
* ``summary`` and ``tags`` are written to ``enrichment`` so both the lexical
  index and the content vector see them -- but only on pages this bridge owns.
  A page that already carries an enrichment written by a real model keeps it,
  and the batch reports that as ``kept_enrichment``. Substituting a tag list
  for a model summary changes the text facet 1 embeds, and the round-trip
  experiment measured what that costs: it changed 100% of embedded texts and
  flipped 20.9% of top-1 results. facetmark's own intent facet -- the "why did
  I save this" queries -- is *not* populated by this bridge. Run ``facetmark
  index`` afterwards if you want it; it will reuse karakeep's body text, will
  not re-request pages karakeep already gave bodies for, and only pays for the
  LLM calls.
* ``createdAt`` becomes ``date_added``, which is what time decay and session
  reconstruction read. karakeep sends ISO 8601; anything unparseable falls back
  to now, and the count of those fallbacks is reported rather than swallowed.
* ``userId`` is kept in the mapping table and applied as a filter *after*
  ranking, because facetmark's index has no user partition. On a multi-user
  instance that biases recall toward whoever has more bookmarks: the over-fetch
  factor below compensates but cannot guarantee. One facetmark database per
  karakeep user is the honest configuration for real multi-tenancy.

Nothing here writes back to karakeep. The mapping table is created on demand, so
a library that never talks to karakeep never grows it, and dropping the
integration is ``DROP TABLE karakeep_doc``.
"""

from __future__ import annotations

import contextlib
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..config import Settings, get_settings
from ..db import jdump, jload, now
from ..enrich.vectors import embed_content
from ..fetch.store import store_body
from ..normalize import normalize_url, registrable_domain
from ..providers import Provider
from ..search.pipeline import ALL_CONFIGS, search
from ..text import sync_fts

#: How many facetmark hits to ask for per requested karakeep hit when a userId
#: filter is present. Ranking happens over the whole library, so a user with a
#: small share of the rows needs headroom before the filter cuts in. The
#: headroom is bounded by ``max_candidate_depth``, not by a constant here.
OVERFETCH = 5
#: Ceiling on one karakeep page, kept separate from ``max_page_size`` because
#: it is part of karakeep's own contract rather than a facetmark setting.
MAX_LIMIT = 200


def ensure_tables(conn: sqlite3.Connection) -> None:
    """Create the karakeep id mapping. Idempotent, and never called implicitly."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS karakeep_doc(
            karakeep_id TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL DEFAULT '',
            bookmark_id INTEGER NOT NULL,
            updated_at  INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_karakeep_doc_bookmark ON karakeep_doc(bookmark_id);
        CREATE INDEX IF NOT EXISTS idx_karakeep_doc_user ON karakeep_doc(user_id);
        """
    )
    conn.commit()


def _parse_ts(raw: Any) -> int | None:
    """karakeep sends ISO 8601 strings; accept epoch numbers too."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, int | float):
        v = float(raw)
        # Anything past ~2286 in seconds is really milliseconds.
        return int(v / 1000) if v > 1e11 else int(v)
    text = str(raw).strip().replace("Z", "+00:00")
    with contextlib.suppress(ValueError):
        return int(datetime.fromisoformat(text).timestamp())
    return None


@dataclass(slots=True)
class KarakeepDoc:
    """One row of ``zBookmarkSearchDocument``, only the fields that carry signal."""

    id: str
    user_id: str = ""
    url: str = ""
    title: str = ""
    link_title: str = ""
    description: str = ""
    content: str = ""
    note: str = ""
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    publisher: str = ""
    author: str = ""
    created_at: int | None = None
    created_at_missing: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> KarakeepDoc:
        def s(key: str) -> str:
            v = d.get(key)
            return "" if v is None else str(v)

        ts = _parse_ts(d.get("createdAt", d.get("created_at")))
        tags = d.get("tags") or []
        return cls(
            id=str(d.get("id", "")),
            user_id=s("userId") or s("user_id"),
            url=s("url"),
            title=s("title"),
            link_title=s("linkTitle") or s("link_title"),
            description=s("description"),
            content=s("content"),
            note=s("note"),
            summary=s("summary"),
            tags=[str(t) for t in tags if str(t).strip()],
            publisher=s("publisher"),
            author=s("author"),
            created_at=ts,
            created_at_missing=ts is None,
        )

    @property
    def display_title(self) -> str:
        return self.title or self.link_title or self.url

    @property
    def folder(self) -> str:
        return " / ".join(self.tags)

    @property
    def body(self) -> str:
        """Everything karakeep already extracted, in one block.

        The note and description are included because in karakeep they are
        frequently the only text a bookmark has -- a saved tweet or an image has
        no article body, and the note is the user's own reason for keeping it,
        which is precisely the signal this project exists to index.
        """
        parts = [self.description, self.note, self.content]
        return "\n\n".join(p for p in parts if p.strip())


def _upsert_one(
    conn: sqlite3.Connection, doc: KarakeepDoc, *, settings: Settings
) -> tuple[int, bool, bool]:
    """Insert or update one document.

    Returns ``(bookmark_id, created, kept_enrichment)``, where the last flag
    means the page already carried an enrichment this bridge did not write and
    that enrichment was left alone.
    """
    nu = normalize_url(doc.url or f"karakeep://{doc.id}")
    ts = doc.created_at if doc.created_at is not None else now()
    row = conn.execute(
        "SELECT bookmark_id FROM karakeep_doc WHERE karakeep_id = ?", (doc.id,)
    ).fetchone()
    bid = int(row["bookmark_id"]) if row is not None else 0
    created = False

    if bid == 0:
        # A URL already in the library (a browser import, say) is adopted rather
        # than duplicated: karakeep becomes another source for the same page.
        prior = conn.execute("SELECT id FROM bookmark WHERE url_hash = ?", (nu.hash,)).fetchone()
        if prior is not None:
            bid = int(prior["id"])
        else:
            cur = conn.execute(
                "INSERT INTO bookmark(url, url_norm, url_hash, title, folder, folder_depth,"
                " host, domain, date_added, source, indexable, privacy_skipped,"
                " created_at, updated_at)"
                " VALUES(?,?,?,?,?,?,?,?,?,'karakeep',?,0,?,?)",
                (nu.original, nu.normalized, nu.hash, doc.display_title, doc.folder,
                 len(doc.tags), nu.host, registrable_domain(nu.host), ts,
                 1 if nu.indexable else 0, now(), now()),
            )
            bid = int(cur.lastrowid)
            created = True

    if not created:
        # ``source`` is deliberately left alone. It is the only record of who
        # created the row, and ``delete_documents`` refuses to remove anything
        # it did not create -- overwriting it here would quietly turn this
        # bridge into something that can delete a browser import.
        conn.execute(
            "UPDATE bookmark SET title=?, folder=?, folder_depth=?, date_added=?,"
            " updated_at=? WHERE id=?",
            (doc.display_title, doc.folder, len(doc.tags), ts, now(), bid),
        )

    body = doc.body
    if body:
        store_body(conn, bid, body=body, title=doc.display_title,
                   extractor="karakeep", channel="k")

    # Enrichment is claimed, never clobbered -- the same rule ``source`` and
    # ``delete_documents`` already follow, and for a sharper reason here.
    # karakeep's tag list is a coarser signal than a model-written enrichment,
    # and overwriting with it is a downgrade that ``facetmark index`` cannot
    # undo: the old UPDATE left ``source_hash`` matching the body hash, so
    # re-enrichment saw the row as current and skipped it forever. Meanwhile
    # the content vector *was* rebuilt, from the worse text. A page could
    # therefore lose its summary permanently and get a quietly worse vector,
    # from a sync that reported nothing unusual.
    #
    # The round-trip experiment measured what that substitution costs even in
    # the benign direction (bridge-written topics displacing model topics
    # changed 100% of embedded texts and flipped 20.9% of top-1 results);
    # doing it to a library the user already enriched is the malignant one.
    existing = conn.execute(
        "SELECT source_hash, summary, topics, entities, key_points"
        " FROM enrichment WHERE bookmark_id=?", (bid,)
    ).fetchone()
    kept_enrichment = existing is not None and existing["source_hash"] != "karakeep"
    if not kept_enrichment and (doc.summary or doc.tags):
        conn.execute(
            "INSERT INTO enrichment(bookmark_id, summary, key_points, entities, topics,"
            " utility, content_type, basis, source_hash, model, created_at)"
            " VALUES(?,?,'[]','[]',?,'', '', 'karakeep', 'karakeep', 'karakeep', ?)"
            " ON CONFLICT(bookmark_id) DO UPDATE SET summary=excluded.summary,"
            " topics=excluded.topics, source_hash='karakeep', model='karakeep',"
            " basis='karakeep', created_at=excluded.created_at",
            (bid, doc.summary, jdump(doc.tags), now()),
        )
        existing = None

    # The lexical rows mirror whatever the enrichment table actually holds, so
    # a kept enrichment stays searchable by its own words rather than by
    # karakeep's.
    if kept_enrichment:
        sync_fts(conn, bid, title=doc.display_title, body=body,
                 summary=existing["summary"] or "",
                 topics=jload(existing["topics"], []),
                 entities=jload(existing["entities"], []),
                 key_points=jload(existing["key_points"], []))
    else:
        sync_fts(conn, bid, title=doc.display_title, body=body,
                 summary=doc.summary, topics=doc.tags,
                 entities=[e for e in (doc.author, doc.publisher) if e])
    conn.execute(
        "INSERT INTO karakeep_doc(karakeep_id, user_id, bookmark_id, updated_at)"
        " VALUES(?,?,?,?) ON CONFLICT(karakeep_id) DO UPDATE SET"
        " user_id=excluded.user_id, bookmark_id=excluded.bookmark_id,"
        " updated_at=excluded.updated_at",
        (doc.id, doc.user_id, bid, now()),
    )
    return bid, created, kept_enrichment


async def add_documents(
    conn: sqlite3.Connection,
    documents: list[dict],
    *,
    provider: Provider | None = None,
    settings: Settings | None = None,
    embed: bool = True,
) -> dict:
    """``addDocuments``: store a batch and embed exactly that batch.

    Embedding happens inside the call because karakeep expects a document to be
    searchable once the promise resolves, and it already batches pushes through
    ``batchingDocumentQueue``. With no embedding provider configured the rows are
    still stored and ``embedded`` comes back 0 -- visibly degraded rather than
    silently empty.
    """
    st = settings or get_settings()
    ensure_tables(conn)
    docs = [KarakeepDoc.from_dict(d) for d in documents if str(d.get("id", "")).strip()]
    ids: list[int] = []
    created = 0
    kept_enrichment = 0
    for doc in docs:
        bid, was_new, kept = _upsert_one(conn, doc, settings=st)
        ids.append(bid)
        created += int(was_new)
        kept_enrichment += int(kept)
    conn.commit()

    embedded = 0
    error = ""
    if embed and ids:
        try:
            rep = await embed_content(conn, provider=provider, settings=st, ids=ids, force=True)
            embedded = rep.content_written
        except Exception as exc:  # pragma: no cover - provider/network dependent
            error = f"{type(exc).__name__}: {exc}"
    return {
        "received": len(documents),
        "stored": len(docs),
        "skipped_no_id": len(documents) - len(docs),
        "created": created,
        "updated": len(docs) - created,
        "embedded": embedded,
        #: Pages whose existing, model-written enrichment was left in place.
        #: A number that climbs means karakeep is syncing over a library
        #: facetmark already understands, which is the good case, not an error.
        "kept_enrichment": kept_enrichment,
        "created_at_missing": sum(1 for d in docs if d.created_at_missing),
        "embed_error": error,
    }


def delete_documents(conn: sqlite3.Connection, ids: list[str]) -> dict:
    """``deleteDocuments``: drop the mapping and the rows it owns.

    A bookmark that predates the bridge (same URL, imported from a browser) is
    unmapped but kept. Deleting it because karakeep forgot it would make this
    integration destructive to data it does not own.
    """
    ensure_tables(conn)
    removed = 0
    kept_foreign = 0
    for kid in ids:
        row = conn.execute(
            "SELECT bookmark_id FROM karakeep_doc WHERE karakeep_id = ?", (str(kid),)
        ).fetchone()
        if row is None:
            continue
        bid = int(row["bookmark_id"])
        conn.execute("DELETE FROM karakeep_doc WHERE karakeep_id = ?", (str(kid),))
        src = conn.execute("SELECT source FROM bookmark WHERE id = ?", (bid,)).fetchone()
        if src is not None and src["source"] == "karakeep":
            _purge_bookmark(conn, bid)
            removed += 1
        else:
            kept_foreign += 1
    conn.commit()
    return {"requested": len(ids), "removed": removed, "kept_not_ours": kept_foreign}


def _purge_bookmark(conn: sqlite3.Connection, bid: int) -> None:
    for sql in (
        "DELETE FROM content WHERE bookmark_id=?",
        "DELETE FROM enrichment WHERE bookmark_id=?",
        "DELETE FROM intent_query WHERE bookmark_id=?",
        "DELETE FROM bookmark_session WHERE bookmark_id=?",
        "DELETE FROM edge WHERE src=? OR dst=?",
        "DELETE FROM health WHERE bookmark_id=?",
        "DELETE FROM fetch_queue WHERE bookmark_id=?",
        "DELETE FROM bookmark WHERE id=?",
    ):
        conn.execute(sql, (bid, bid) if "dst" in sql else (bid,))
    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("DELETE FROM vec_content WHERE rowid=?", (bid,))
    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("DELETE FROM fts_tri WHERE rowid=?", (bid,))
        conn.execute("DELETE FROM fts_seg WHERE rowid=?", (bid,))


def clear_index(conn: sqlite3.Connection) -> dict:
    """``clearIndex``: remove only what karakeep put here."""
    ensure_tables(conn)
    rows = conn.execute(
        "SELECT k.karakeep_id, k.bookmark_id FROM karakeep_doc k"
        " JOIN bookmark b ON b.id = k.bookmark_id WHERE b.source = 'karakeep'"
    ).fetchall()
    for r in rows:
        _purge_bookmark(conn, int(r["bookmark_id"]))
    n_map = conn.execute("SELECT COUNT(*) AS n FROM karakeep_doc").fetchone()["n"]
    conn.execute("DELETE FROM karakeep_doc")
    conn.commit()
    return {"purged_bookmarks": len(rows), "cleared_mappings": int(n_map)}


def _filters(options: dict) -> tuple[str, list[str]]:
    """Split karakeep's ``FilterQuery[]`` into (user_id, explicit ids)."""
    user_id = ""
    ids: list[str] = []
    for f in options.get("filter") or []:
        field_ = f.get("field")
        if field_ == "userId":
            if f.get("type") == "eq":
                user_id = str(f.get("value", ""))
            elif f.get("type") == "in":
                vals = [str(v) for v in f.get("values") or []]
                user_id = vals[0] if len(vals) == 1 else user_id
        elif field_ == "id":
            if f.get("type") == "eq":
                ids.append(str(f.get("value", "")))
            else:
                ids.extend(str(v) for v in f.get("values") or [])
    return user_id, ids


def _chronological(conn: sqlite3.Connection, user_id: str, ids: list[str],
                   *, limit: int, offset: int, desc: bool) -> dict:
    sql = ("SELECT k.karakeep_id AS kid FROM karakeep_doc k"
           " JOIN bookmark b ON b.id = k.bookmark_id")
    where, params = [], []
    if user_id:
        where.append("k.user_id = ?")
        params.append(user_id)
    if ids:
        where.append(f"k.karakeep_id IN ({','.join('?' * len(ids))})")
        params.extend(ids)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY b.date_added {'DESC' if desc else 'ASC'}, k.karakeep_id"
    rows = conn.execute(sql, params).fetchall()
    page = rows[offset:offset + limit]
    return {"hits": [{"id": r["kid"]} for r in page], "totalHits": len(rows)}


async def search_documents(
    conn: sqlite3.Connection,
    options: dict,
    *,
    provider: Provider | None = None,
    settings: Settings | None = None,
    config: str = "full",
) -> dict:
    """``search``: rank with facetmark, answer in karakeep's shape.

    An empty query is karakeep browsing rather than searching, and is answered
    chronologically instead of by running a retrieval pass over an empty string.
    """
    st = settings or get_settings()
    ensure_tables(conn)
    t0 = time.perf_counter()
    query = str(options.get("query") or "").strip()
    limit = max(1, min(int(options.get("limit") or 20), MAX_LIMIT))
    offset = max(0, int(options.get("offset") or 0))
    user_id, only_ids = _filters(options)
    sort = options.get("sort") or []
    desc = not (sort and str(sort[0].get("order", "desc")).lower() == "asc")

    if not query:
        out = _chronological(conn, user_id, only_ids, limit=limit, offset=offset, desc=desc)
        out["processingTimeMs"] = round((time.perf_counter() - t0) * 1000, 2)
        out["engine"] = "chronological"
        return out

    # Both the karakeep-id mapping and the userId filter are applied *after*
    # ranking, and neither is a bijection: a bookmark can carry several
    # karakeep ids, and a library can hold bookmarks karakeep never sent. So
    # the window retrieved is not the window returned, and `offset` stays a
    # slice of the mapped list rather than being pushed into the pipeline.
    #
    # What did change: the ceiling on that window is `max_candidate_depth`
    # rather than a literal 500, the depth is pinned so the window is one
    # coherent ranking, and the floor is `candidates_per_facet` -- the pipeline
    # retrieves that much regardless, so reading it costs nothing and makes
    # `totalHits` a real count instead of the size of the page.
    need = limit + offset
    over = OVERFETCH if (user_id or only_ids) else 1
    window = min(max(need * over, st.candidates_per_facet), max(1, st.max_candidate_depth))
    resp = await search(
        conn, query, limit=window, offset=0, depth=window,
        config=ALL_CONFIGS.get(config, ALL_CONFIGS["full"]),
        provider=provider,
        # `max_page_size` bounds what a *caller* is handed. This window is
        # internal -- filtered and re-sliced before anything leaves -- so the
        # bound that applies to it is the depth ceiling.
        settings=st if window <= st.max_page_size else st.model_copy(
            update={"max_page_size": window}
        ),
    )
    by_bid: dict[int, list[tuple[str, str]]] = {}
    for r in conn.execute("SELECT karakeep_id, user_id, bookmark_id FROM karakeep_doc"):
        by_bid.setdefault(int(r["bookmark_id"]), []).append((r["karakeep_id"], r["user_id"]))

    hits: list[dict] = []
    seen: set[str] = set()
    for h in resp.hits:
        for kid, uid in by_bid.get(int(h.bookmark_id), ()):
            if user_id and uid != user_id:
                continue
            if only_ids and kid not in only_ids:
                continue
            if kid in seen:
                continue
            seen.add(kid)
            hits.append({"id": kid, "score": float(getattr(h, "score", 0.0) or 0.0)})
    page = hits[offset:offset + limit]
    return {
        "hits": page,
        "totalHits": len(hits),
        "processingTimeMs": round((time.perf_counter() - t0) * 1000, 2),
        "engine": f"facetmark:{config}",
        # The pipeline knows whether it stopped early; asking it beats
        # inferring truncation from the length of what came back, which said
        # "truncated" for any library whose match count landed exactly on the
        # window.
        "truncated": resp.has_more,
    }


def mapping_stats(conn: sqlite3.Connection) -> dict:
    ensure_tables(conn)
    n = conn.execute("SELECT COUNT(*) AS n FROM karakeep_doc").fetchone()["n"]
    users = conn.execute("SELECT COUNT(DISTINCT user_id) AS n FROM karakeep_doc").fetchone()["n"]
    bodies = conn.execute(
        "SELECT COUNT(*) AS n FROM karakeep_doc k JOIN content c ON c.bookmark_id = k.bookmark_id"
        " WHERE COALESCE(c.char_count, 0) > 0"
    ).fetchone()["n"]
    return {"documents": int(n), "users": int(users), "with_body": int(bodies)}
