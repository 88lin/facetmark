"""Storage layer: schema, connection handling and the sqlite-vec adapter.

Everything lives in one SQLite file. At the calibrated scale (1697 bookmarks ->
~8.5k vectors) sqlite-vec's exact brute-force scan answers in single-digit
milliseconds, so no ANN index is needed. The switch-over threshold is ~1e5
vectors (roughly 25k bookmarks).

sqlite-vec is pre-v1, so every vector read and write goes through the thin
adapter at the bottom of this module. Replacing the vector backend should not
require touching any other file.
"""

from __future__ import annotations

import json
import sqlite3
import struct
import time
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path
from typing import Any

import sqlite_vec

# SCHEMA_VERSION is derived from the migration list, not declared here, so the
# two cannot drift. Re-exported because callers have always imported it from db.
from .migrations import (  # noqa: F401  (re-export)
    SCHEMA_VERSION,
    SchemaTooNew,
    apply_pending,
    schema_status,
)

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- One row per bookmark. `url` is what we navigate to; `url_norm`/`url_hash`
-- are the identity key produced by normalize.normalize_url.
CREATE TABLE IF NOT EXISTS bookmark (
    id              INTEGER PRIMARY KEY,
    url             TEXT    NOT NULL,
    url_norm        TEXT    NOT NULL,
    url_hash        TEXT    NOT NULL UNIQUE,
    title           TEXT    NOT NULL DEFAULT '',
    folder          TEXT    NOT NULL DEFAULT '',   -- display path; DO NOT split on '/'
    folder_depth    INTEGER NOT NULL DEFAULT 0,    -- true nesting level (names may contain '/')
    host            TEXT    NOT NULL DEFAULT '',
    domain          TEXT    NOT NULL DEFAULT '',
    date_added      INTEGER,            -- unix seconds, UTC
    date_modified   INTEGER,
    source          TEXT,               -- netscape_html | chrome_json | api
    indexable       INTEGER NOT NULL DEFAULT 1,   -- http(s) only
    privacy_skipped INTEGER NOT NULL DEFAULT 0,
    import_artifact INTEGER NOT NULL DEFAULT 0,
    open_count      INTEGER NOT NULL DEFAULT 0,
    last_opened_at  INTEGER,
    created_at      INTEGER NOT NULL,
    updated_at      INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_bookmark_added  ON bookmark(date_added);
CREATE INDEX IF NOT EXISTS ix_bookmark_domain ON bookmark(domain);
CREATE INDEX IF NOT EXISTS ix_bookmark_folder ON bookmark(folder);

-- Fetched page body. Separated from `bookmark` so a re-fetch never rewrites
-- bookmark identity, and so the big TEXT column stays out of scan-heavy paths.
CREATE TABLE IF NOT EXISTS content (
    bookmark_id  INTEGER PRIMARY KEY REFERENCES bookmark(id) ON DELETE CASCADE,
    body_text    TEXT,
    body_seg     TEXT,        -- jieba-segmented copy, feeds the unicode61 index
    body_hash    TEXT,        -- hash of the canonicalised body; drives idempotency
    char_count   INTEGER NOT NULL DEFAULT 0,
    lang         TEXT,
    extractor    TEXT,        -- trafilatura | readability | meta | extension
    fetch_channel TEXT,       -- a | b | reader
    http_status  INTEGER,
    final_url    TEXT,
    fetched_at   INTEGER,
    error        TEXT
);

-- LLM output. One row per bookmark, regenerated only when source_hash drifts
-- from content.body_hash. `basis` says what the summary was written from --
-- 'body' (the page's extracted text), 'title' (never fetched; inferred from
-- title+url), 'karakeep' (bridge metadata, never a model call) -- because a
-- title-based summary is a guess about the page rather than a report from it,
-- and every surface that shows one is allowed to say so. Last, like every
-- column a migration adds, so a fresh file and a migrated one match.
CREATE TABLE IF NOT EXISTS enrichment (
    bookmark_id  INTEGER PRIMARY KEY REFERENCES bookmark(id) ON DELETE CASCADE,
    summary      TEXT,
    key_points   TEXT,        -- json array
    entities     TEXT,        -- json array
    topics       TEXT,        -- json array
    utility      TEXT,
    content_type TEXT,
    source_hash  TEXT,
    model        TEXT,
    created_at   INTEGER,
    basis        TEXT NOT NULL DEFAULT 'body'
);

-- Facet 2: hypothetical queries generated from the page (doc2query), then
-- filtered for self-consistency. `kept=1` rows are the ones that get embedded.
CREATE TABLE IF NOT EXISTS intent_query (
    id            INTEGER PRIMARY KEY,
    bookmark_id   INTEGER NOT NULL REFERENCES bookmark(id) ON DELETE CASCADE,
    text          TEXT    NOT NULL,
    kept          INTEGER NOT NULL DEFAULT 0,
    probe_rank    INTEGER,     -- rank of the source doc when probed with this query
    created_at    INTEGER,
    scored_at     INTEGER      -- NULL: never probed. `kept=0` alone cannot say.
);
CREATE INDEX IF NOT EXISTS ix_intent_bookmark ON intent_query(bookmark_id);
CREATE INDEX IF NOT EXISTS ix_intent_kept     ON intent_query(kept);
CREATE INDEX IF NOT EXISTS ix_intent_unscored ON intent_query(scored_at);

-- Provenance for facet 1. `vec_content` is a vec0 virtual table and holds
-- nothing but the vector, so what the vector was built from lives here. A row
-- whose hash no longer matches the text `content_text()` produces today is
-- stale and gets re-embedded; a vector with no row here has unknown
-- provenance and is treated the same way.
CREATE TABLE IF NOT EXISTS vec_content_meta (
    bookmark_id INTEGER PRIMARY KEY REFERENCES bookmark(id) ON DELETE CASCADE,
    text_hash   TEXT    NOT NULL,
    updated_at  INTEGER NOT NULL
);

-- Facet 4: reconstructed saving episodes.
CREATE TABLE IF NOT EXISTS session (
    id          INTEGER PRIMARY KEY,
    started_at  INTEGER NOT NULL,
    ended_at    INTEGER NOT NULL,
    size        INTEGER NOT NULL,
    label       TEXT,
    method      TEXT,       -- temporal | folder (folder = import-artifact fallback)
    eps_seconds INTEGER
);
CREATE INDEX IF NOT EXISTS ix_session_time ON session(started_at, ended_at);

CREATE TABLE IF NOT EXISTS bookmark_session (
    bookmark_id INTEGER NOT NULL REFERENCES bookmark(id) ON DELETE CASCADE,
    session_id  INTEGER NOT NULL REFERENCES session(id)  ON DELETE CASCADE,
    PRIMARY KEY (bookmark_id, session_id)
);
CREATE INDEX IF NOT EXISTS ix_bs_session ON bookmark_session(session_id);

-- Typed relations used for 1-hop expansion. Stored undirected-by-convention:
-- both directions are inserted so a single-direction query suffices.
CREATE TABLE IF NOT EXISTS edge (
    src    INTEGER NOT NULL REFERENCES bookmark(id) ON DELETE CASCADE,
    dst    INTEGER NOT NULL REFERENCES bookmark(id) ON DELETE CASCADE,
    kind   TEXT    NOT NULL,   -- session|semantic|supersession|same_domain|anchor_sibling
    weight REAL    NOT NULL DEFAULT 1.0,
    PRIMARY KEY (src, dst, kind)
);
CREATE INDEX IF NOT EXISTS ix_edge_src  ON edge(src, kind);
CREATE INDEX IF NOT EXISTS ix_edge_kind ON edge(kind);

-- Link health history. Append-only: a verdict is never overwritten, because
-- `gone` requires two high-confidence confirmations >= 7 days apart.
CREATE TABLE IF NOT EXISTS health (
    id                 INTEGER PRIMARY KEY,
    bookmark_id        INTEGER NOT NULL REFERENCES bookmark(id) ON DELETE CASCADE,
    checked_at         INTEGER NOT NULL,
    verdict            TEXT    NOT NULL,
    http_status        INTEGER,
    confidence         REAL    NOT NULL DEFAULT 0.0,
    local_evidence     TEXT,   -- json
    external_evidence  TEXT,   -- json
    archive_url        TEXT
);
CREATE INDEX IF NOT EXISTS ix_health_bookmark ON health(bookmark_id, checked_at DESC);

-- Channel B work queue. Channel A writes a row here whenever it hits a wall it
-- cannot honestly get past (403, bot check, client-rendered shell); the browser
-- extension leases rows and fetches them from a real tab with the user's own
-- session. Leases expire, because a browser tab can die mid-job and an
-- unreclaimable lease would strand the bookmark forever.
CREATE TABLE IF NOT EXISTS fetch_queue (
    bookmark_id INTEGER PRIMARY KEY REFERENCES bookmark(id) ON DELETE CASCADE,
    reason      TEXT    NOT NULL,                   -- channel-A verdict that deferred it
    state       TEXT    NOT NULL DEFAULT 'pending', -- pending | leased | done | failed
    attempts    INTEGER NOT NULL DEFAULT 0,
    queued_at   INTEGER NOT NULL,
    leased_at   INTEGER,
    last_error  TEXT,
    next_attempt_at INTEGER   -- NULL = ready now; else the backoff deadline
);
CREATE INDEX IF NOT EXISTS ix_fetch_queue_state ON fetch_queue(state, queued_at);
CREATE INDEX IF NOT EXISTS ix_fetch_queue_ready
    ON fetch_queue(state, next_attempt_at, queued_at);

CREATE TABLE IF NOT EXISTS interaction (
    id          INTEGER PRIMARY KEY,
    bookmark_id INTEGER REFERENCES bookmark(id) ON DELETE CASCADE,
    kind        TEXT    NOT NULL,   -- open | search_click | dismiss
    query       TEXT,
    at          INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_interaction_bookmark ON interaction(bookmark_id);

-- Facet 3, path A: trigram substring index. Handles CJK >= 3 chars, latin
-- substrings, and rescues terms that jieba mis-segments. Cannot match queries
-- shorter than 3 characters -- that is what fts_seg is for.
CREATE VIRTUAL TABLE IF NOT EXISTS fts_tri USING fts5(
    title, body, summary, extra, tokenize='trigram'
);

-- Facet 3, path B: word index over jieba-segmented text. This is the path that
-- answers two-character CJK queries such as 学习 / 工具 / 论文, which trigram
-- silently misses entirely.
CREATE VIRTUAL TABLE IF NOT EXISTS fts_seg USING fts5(
    title, body, summary, extra, tokenize='unicode61 remove_diacritics 2'
);
"""


class SchemaMismatch(RuntimeError):
    """Raised when the stored embedding model/dimension differs from settings."""


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


def connect(
    db_path: str | Path, *, read_only: bool = False, same_thread: bool = True
) -> sqlite3.Connection:
    """Open a connection with sqlite-vec loaded and sane pragmas.

    ``same_thread=False`` is for the long-lived service connection only. ASGI
    servers run synchronous handlers and dependencies on a worker threadpool, so
    a connection created during startup would otherwise be unusable from them.
    Python's sqlite3 is built in serialized threading mode, which makes the
    connection object itself mutex-protected; writes are additionally serialised
    by an asyncio lock in :class:`facetmark.api.AppState`.
    """
    p = Path(db_path)
    if str(p) != ":memory:":
        p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(p), timeout=30.0, isolation_level=None, check_same_thread=same_thread
    )
    conn.row_factory = sqlite3.Row
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA cache_size=-32000")  # ~32 MB
    if read_only:
        conn.execute("PRAGMA query_only=ON")
    return conn


def init_db(conn: sqlite3.Connection, *, migrate: bool = True, backup: bool = True) -> None:
    """Create what is missing, upgrade what is behind, stamp what is new.

    Order matters. Migrations run *before* ``SCHEMA_SQL``, because SCHEMA_SQL
    describes the current schema -- an index over a column that migration v2
    adds cannot be created on a v1 file. Running the upgrade first means the
    ``CREATE ... IF NOT EXISTS`` pass that follows is always a no-op on an
    existing database and a full build on a new one.
    """
    status = schema_status(conn)
    if status.too_new:
        raise SchemaTooNew(
            f"database is at schema v{status.found} but this facetmark only knows "
            f"v{status.expected}. Upgrade facetmark, or point at a different database."
        )
    if status.pending:
        if not migrate:
            versions = ", ".join(f"v{m.version}" for m in status.pending)
            raise RuntimeError(
                f"database is at schema v{status.found}, pending: {versions}. "
                "Run `facetmark migrate`."
            )
        apply_pending(conn, backup=backup)

    conn.executescript(SCHEMA_SQL)

    if status.fresh:
        set_meta(conn, "schema_version", str(SCHEMA_VERSION))
        set_meta(conn, "created_at", str(int(time.time())))


def open_db(
    db_path: str | Path, *, same_thread: bool = True, migrate: bool = True
) -> sqlite3.Connection:
    conn = connect(db_path, same_thread=same_thread)
    init_db(conn, migrate=migrate)
    return conn


# ---------------------------------------------------------------------------
# meta helpers
# ---------------------------------------------------------------------------


def get_meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


# ---------------------------------------------------------------------------
# Vector adapter -- the only place that knows about sqlite-vec internals
# ---------------------------------------------------------------------------


def _pack(vec: Sequence[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def unpack_vector(blob: bytes) -> list[float]:
    """Inverse of the storage packing. Part of the adapter, not of sqlite-vec."""
    return list(struct.unpack(f"{len(blob) // 4}f", blob))


def _l2_normalize(vec: Sequence[float]) -> list[float]:
    """Normalise to unit length.

    We store unit vectors and query with plain L2 distance. For unit vectors
    L2 distance is a monotonic function of cosine similarity, so ranking is
    identical to cosine without depending on a specific sqlite-vec build
    supporting ``distance_metric=cosine``.
    """
    s = sum(x * x for x in vec) ** 0.5
    if s == 0.0:
        return list(vec)
    return [x / s for x in vec]


def ensure_vec_tables(conn: sqlite3.Connection, dim: int, model: str) -> None:
    """Create the vector tables, pinning dimension and model in ``meta``.

    A dimension or model change invalidates every stored vector, so it is a hard
    error rather than a silent mix.
    """
    stored_dim = get_meta(conn, "embed_dim")
    stored_model = get_meta(conn, "embed_model")

    if stored_dim is not None and int(stored_dim) != dim:
        raise SchemaMismatch(
            f"database was built with embed_dim={stored_dim}, settings say {dim}. "
            f"Vectors are incompatible. Run 'facetmark reindex --vectors' to rebuild."
        )
    if stored_model is not None and stored_model != model:
        raise SchemaMismatch(
            f"database was built with embed_model={stored_model!r}, settings say {model!r}. "
            f"Run 'facetmark reindex --vectors' to rebuild."
        )

    conn.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_content USING vec0("
        f"  bookmark_id INTEGER PRIMARY KEY, embedding FLOAT[{dim}])"
    )
    conn.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_intent USING vec0("
        f"  intent_id INTEGER PRIMARY KEY, embedding FLOAT[{dim}])"
    )
    set_meta(conn, "embed_dim", str(dim))
    set_meta(conn, "embed_model", model)


def vec_tables_exist(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT count(*) AS n FROM sqlite_master WHERE name IN ('vec_content','vec_intent')"
    ).fetchone()
    return int(row["n"]) == 2


def upsert_content_vector(
    conn: sqlite3.Connection,
    bookmark_id: int,
    vec: Sequence[float],
    *,
    text_hash: str | None = None,
) -> None:
    """Write facet 1's vector, and say what text produced it.

    ``text_hash=None`` means the caller is not saying, which is not the same as
    saying nothing changed -- the provenance row is dropped so the vector reads
    as stale rather than as silently current.
    """
    blob = _pack(_l2_normalize(vec))
    conn.execute("DELETE FROM vec_content WHERE bookmark_id=?", (bookmark_id,))
    conn.execute(
        "INSERT INTO vec_content(bookmark_id, embedding) VALUES(?,?)", (bookmark_id, blob)
    )
    if text_hash is None:
        conn.execute("DELETE FROM vec_content_meta WHERE bookmark_id=?", (bookmark_id,))
    else:
        conn.execute(
            "INSERT INTO vec_content_meta(bookmark_id, text_hash, updated_at) VALUES(?,?,?) "
            "ON CONFLICT(bookmark_id) DO UPDATE SET "
            "  text_hash=excluded.text_hash, updated_at=excluded.updated_at",
            (bookmark_id, text_hash, now()),
        )


def content_vector_hashes(conn: sqlite3.Connection) -> dict[int, str]:
    """bookmark_id -> the hash of the text its stored vector was built from.

    Only bookmarks that still have a vector are included: a provenance row left
    behind by a hand-deleted ``vec_content`` would otherwise read as current.
    """
    rows = conn.execute(
        "SELECT m.bookmark_id AS id, m.text_hash AS h FROM vec_content_meta m "
        "WHERE m.bookmark_id IN (SELECT bookmark_id FROM vec_content)"
    ).fetchall()
    return {int(r["id"]): str(r["h"]) for r in rows}


def upsert_intent_vector(conn: sqlite3.Connection, intent_id: int, vec: Sequence[float]) -> None:
    blob = _pack(_l2_normalize(vec))
    conn.execute("DELETE FROM vec_intent WHERE intent_id=?", (intent_id,))
    conn.execute("INSERT INTO vec_intent(intent_id, embedding) VALUES(?,?)", (intent_id, blob))


def knn_content(
    conn: sqlite3.Connection, query_vec: Sequence[float], k: int
) -> list[tuple[int, float]]:
    """Nearest content vectors as ``(bookmark_id, distance)``, closest first."""
    blob = _pack(_l2_normalize(query_vec))
    rows = conn.execute(
        "SELECT bookmark_id, distance FROM vec_content "
        "WHERE embedding MATCH ? AND k=? ORDER BY distance",
        (blob, k),
    ).fetchall()
    return [(int(r["bookmark_id"]), float(r["distance"])) for r in rows]


def knn_intent(
    conn: sqlite3.Connection, query_vec: Sequence[float], k: int
) -> list[tuple[int, float]]:
    """Nearest intent vectors as ``(intent_id, distance)``, closest first."""
    blob = _pack(_l2_normalize(query_vec))
    rows = conn.execute(
        "SELECT intent_id, distance FROM vec_intent "
        "WHERE embedding MATCH ? AND k=? ORDER BY distance",
        (blob, k),
    ).fetchall()
    return [(int(r["intent_id"]), float(r["distance"])) for r in rows]


def count_vectors(conn: sqlite3.Connection) -> tuple[int, int]:
    if not vec_tables_exist(conn):
        return (0, 0)
    c = conn.execute("SELECT count(*) AS n FROM vec_content").fetchone()["n"]
    i = conn.execute("SELECT count(*) AS n FROM vec_intent").fetchone()["n"]
    return (int(c), int(i))


# ---------------------------------------------------------------------------
# small utilities
# ---------------------------------------------------------------------------


def jdump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def jload(s: str | None, default: Any = None) -> Any:
    if not s:
        return default if default is not None else []
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else []


def now() -> int:
    return int(time.time())


def executemany(conn: sqlite3.Connection, sql: str, rows: Iterable[tuple]) -> None:
    batch = list(rows)
    if batch:
        conn.executemany(sql, batch)


#: Ids per ``IN (...)`` batch. SQLite's ``SQLITE_MAX_VARIABLE_NUMBER`` is 32766
#: on anything built since 3.32, but the older default is **999** and it is a
#: compile-time constant, so the interpreter a user happens to have decides
#: whether a query raises. 900 leaves room for the handful of non-id parameters
#: the callers here also bind.
IN_CHUNK = 900


def in_chunks(ids: Sequence[int], size: int = IN_CHUNK) -> Iterator[list[int]]:
    """Split ``ids`` into batches small enough for a single ``IN (...)`` clause.

    Every query in this codebase that expands one placeholder per id used to be
    bounded by ``candidates_per_facet``, which is 50. Paging removed that bound:
    depth now follows ``limit + offset``, and the intent facet multiplies it by
    ``intent_keep_n`` again. Chunking is what makes "how deep can you page"
    a question about the configured ceiling rather than about which SQLite the
    host was compiled with.
    """
    seq = list(ids)
    for i in range(0, len(seq), size):
        yield seq[i:i + size]
