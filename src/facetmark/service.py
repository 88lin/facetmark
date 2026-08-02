"""The read model, shared by all three entry points.

There are three ways into facetmark -- the HTTP API the extension talks to, the
MCP server an agent talks to, and the CLI a person talks to -- and they must
agree on what a bookmark *is*. Putting the shaping here rather than in each
entry point is the only way to guarantee that; the alternative is three slowly
diverging dictionaries.

Two contracts are enforced in this module and nowhere else:

* ``summary`` is truncated to 200 characters and ``snippet`` to 300. An agent
  pulling 20 results should not receive 20 full page bodies, and a popup
  rendering them should not have to decide where to cut.
* A bookmark is never hidden or deleted because of its health verdict. The
  record carries ``health`` and ``badge`` and lets the caller decide. See the
  UI contract in the design document: even a confirmed-``gone`` link stays in
  the library and stays searchable, it just gains a graveyard flag and an
  archive link.
"""

from __future__ import annotations

import contextlib
import json
import re
import secrets
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any

from . import db as dbmod
from . import edges as edgemod
from . import health as healthmod
from . import sessions as sessmod
from .config import Settings, get_settings
from .enrich import embed_content, embed_intents, enrich_all, filter_intents
from .fetch import store as fetchstore
from .importers import import_bookmarks
from .normalize import host_excluded, normalize_url, registrable_domain
from .providers import Provider, get_provider
from .search import graph as graphmod
from .search.pipeline import FULL, Config, SearchResponse, quick_search, search
from .text import sync_fts

SUMMARY_CHARS = 200
SNIPPET_CHARS = 300

TOKEN_BYTES = 24


# ---------------------------------------------------------------------------
# pairing token
# ---------------------------------------------------------------------------


def pairing_token(settings: Settings | None = None, *, create: bool = True) -> str:
    """Read the extension pairing token, minting one on first use.

    The service binds to 127.0.0.1, but "localhost only" is not an
    authorisation model: any other process on the machine, including a web page
    via a local network request, can reach the same port. The token is written
    to a file the user can read and paste into the extension once.
    """
    st = settings or get_settings()
    path = st.token_path
    if path.exists():
        tok = path.read_text(encoding="utf-8").strip()
        if tok:
            return tok
    if not create:
        return ""
    st.ensure_dirs()
    tok = secrets.token_urlsafe(TOKEN_BYTES)
    path.write_text(tok, encoding="utf-8")
    # best effort; Windows ignores POSIX modes
    with contextlib.suppress(OSError):  # pragma: no cover - platform dependent
        path.chmod(0o600)
    return tok


def rotate_token(settings: Settings | None = None) -> str:
    st = settings or get_settings()
    if st.token_path.exists():
        st.token_path.unlink()
    return pairing_token(st)


# ---------------------------------------------------------------------------
# record shaping
# ---------------------------------------------------------------------------


def _jlist(raw: Any) -> list:
    if not raw:
        return []
    try:
        out = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return out if isinstance(out, list) else []


def _clip(text: str | None, n: int) -> str:
    t = (text or "").strip()
    return t if len(t) <= n else t[: n - 1].rstrip() + "\u2026"


_BOOKMARK_SQL = """
SELECT b.id, b.url, b.title, b.folder, b.folder_depth, b.domain, b.host,
       b.date_added, b.date_modified, b.source, b.indexable, b.privacy_skipped,
       b.import_artifact, b.open_count, b.last_opened_at,
       e.summary, e.topics, e.entities, e.key_points, e.utility, e.content_type,
       e.model AS enrich_model,
       c.char_count, c.lang, c.extractor, c.fetch_channel, c.http_status,
       c.fetched_at, c.final_url, c.error AS fetch_error,
       substr(COALESCE(c.body_text, ''), 1, 400) AS body_head
FROM bookmark b
LEFT JOIN enrichment e ON e.bookmark_id = b.id
LEFT JOIN content    c ON c.bookmark_id = b.id
WHERE b.id = ?
"""


def bookmark_record(
    conn: sqlite3.Connection,
    bookmark_id: int,
    *,
    settings: Settings | None = None,
    include_body: bool = False,
) -> dict | None:
    """One bookmark, fully joined. ``None`` when the id does not exist."""
    row = conn.execute(_BOOKMARK_SQL, (bookmark_id,)).fetchone()
    if row is None:
        return None
    st = settings or get_settings()

    state = healthmod.state_of(conn, bookmark_id, settings=st)
    sessions = [
        {"session_id": r["session_id"], "started_at": r["started_at"],
         "size": r["size"], "label": r["label"] or ""}
        for r in conn.execute(
            "SELECT bs.session_id, s.started_at, s.size, s.label "
            "FROM bookmark_session bs JOIN session s ON s.id = bs.session_id "
            "WHERE bs.bookmark_id = ? ORDER BY s.started_at",
            (bookmark_id,),
        ).fetchall()
    ]
    intents = [
        r["text"]
        for r in conn.execute(
            "SELECT text FROM intent_query WHERE bookmark_id=? AND kept=1 ORDER BY probe_rank",
            (bookmark_id,),
        ).fetchall()
    ]

    rec: dict[str, Any] = {
        "bookmark_id": row["id"],
        "url": row["url"],
        "title": row["title"],
        "folder": row["folder"],
        "folder_depth": row["folder_depth"],
        "domain": row["domain"],
        "date_added": row["date_added"],
        "open_count": row["open_count"],
        "last_opened_at": row["last_opened_at"],
        "summary": _clip(row["summary"], SUMMARY_CHARS),
        "topics": _jlist(row["topics"]),
        "entities": _jlist(row["entities"]),
        "key_points": _jlist(row["key_points"]),
        "utility": row["utility"] or "",
        "content_type": row["content_type"] or "",
        "intent_queries": intents,
        "sessions": sessions,
        "indexed": {
            "chars": row["char_count"] or 0,
            "lang": row["lang"] or "",
            "extractor": row["extractor"] or "",
            "channel": row["fetch_channel"] or "",
            "http_status": row["http_status"],
            "fetched_at": row["fetched_at"],
            "error": row["fetch_error"] or "",
            "enriched_by": row["enrich_model"] or "",
        },
        "privacy_skipped": bool(row["privacy_skipped"]),
        "health": state.as_dict(),
        "badge": state.badge,
        "in_graveyard": state.show_in_graveyard,
    }
    if not rec["summary"]:
        rec["summary"] = _clip(row["body_head"], SUMMARY_CHARS)
    if include_body:
        body = conn.execute(
            "SELECT body_text FROM content WHERE bookmark_id=?", (bookmark_id,)
        ).fetchone()
        rec["body_text"] = (body["body_text"] if body else "") or ""
    return rec


def session_list(
    conn: sqlite3.Connection, *, limit: int = 50, offset: int = 0, min_size: int = 2
) -> list[dict]:
    rows = conn.execute(
        "SELECT id, started_at, ended_at, size, label, method, eps_seconds "
        "FROM session WHERE size >= ? ORDER BY started_at DESC LIMIT ? OFFSET ?",
        (min_size, limit, offset),
    ).fetchall()
    return [
        {
            "session_id": r["id"],
            "started_at": r["started_at"],
            "ended_at": r["ended_at"],
            "span_seconds": max(0, r["ended_at"] - r["started_at"]),
            "size": r["size"],
            "label": r["label"] or "",
            "method": r["method"] or "",
            "eps_seconds": r["eps_seconds"],
        }
        for r in rows
    ]


def session_record(conn: sqlite3.Connection, session_id: int) -> dict | None:
    row = conn.execute(
        "SELECT id, started_at, ended_at, size, label, method, eps_seconds "
        "FROM session WHERE id = ?",
        (session_id,),
    ).fetchone()
    if row is None:
        return None
    members = conn.execute(
        "SELECT b.id, b.url, b.title, b.folder, b.domain, b.date_added, "
        f"       substr(COALESCE(e.summary,''),1,{SUMMARY_CHARS}) AS summary "
        "FROM bookmark_session bs JOIN bookmark b ON b.id = bs.bookmark_id "
        "LEFT JOIN enrichment e ON e.bookmark_id = b.id "
        "WHERE bs.session_id = ? ORDER BY b.date_added",
        (session_id,),
    ).fetchall()
    return {
        "session_id": row["id"],
        "started_at": row["started_at"],
        "ended_at": row["ended_at"],
        "span_seconds": max(0, row["ended_at"] - row["started_at"]),
        "size": row["size"],
        "label": row["label"] or "",
        "method": row["method"] or "",
        "eps_seconds": row["eps_seconds"],
        "bookmarks": [
            {"bookmark_id": m["id"], "url": m["url"], "title": m["title"],
             "folder": m["folder"], "domain": m["domain"],
             "date_added": m["date_added"], "summary": m["summary"] or ""}
            for m in members
        ],
    }


def related_records(
    conn: sqlite3.Connection, bookmark_id: int, *, kind: str | None = None, limit: int = 20
) -> list[dict]:
    """Typed neighbours of one bookmark.

    ``supersession`` is directional on purpose: an outgoing edge means *this was
    replaced by that*, which is a different statement from *that was replaced by
    this*, and collapsing it would make the newest-version answer unreliable.
    """
    if kind is not None and kind not in edgemod.WEIGHTS:
        raise ValueError(f"unknown edge kind {kind!r}; expected one of {sorted(edgemod.WEIGHTS)}")
    exps = graphmod.related(conn, bookmark_id, kind=kind, limit=limit)
    if not exps:
        return []
    ids = [e.doc_id for e in exps]
    rows = {
        r["id"]: r
        for r in conn.execute(
            "SELECT b.id, b.url, b.title, b.folder, b.domain, b.date_added, "
            f"       substr(COALESCE(e.summary,''),1,{SUMMARY_CHARS}) AS summary "
            "FROM bookmark b LEFT JOIN enrichment e ON e.bookmark_id = b.id "
            f"WHERE b.id IN ({','.join('?' * len(ids))})",
            ids,
        ).fetchall()
    }
    out = []
    for e in exps:
        r = rows.get(e.doc_id)
        if r is None:
            continue
        out.append({
            "bookmark_id": r["id"], "url": r["url"], "title": r["title"],
            "folder": r["folder"], "domain": r["domain"], "date_added": r["date_added"],
            "summary": r["summary"] or "", "kind": e.kind, "score": round(e.score, 6),
        })
    return out


# ---------------------------------------------------------------------------
# suggest from context
# ---------------------------------------------------------------------------

_SENT_SPLIT = re.compile(r"[\n\r]+|(?<=[.!?\u3002\uff01\uff1f])\s+")
MAX_CONTEXT_CHARS = 4000


def suggest_from_context(
    conn: sqlite3.Connection, text: str, *, limit: int = 8
) -> dict:
    """What in the library is relevant to a block of text the user is writing.

    Deliberately lexical-only and synchronous. This is called from an editor or
    an agent's working context, possibly on every pause, so it must not cost a
    model call. The text is truncated rather than embedded: sending a user's
    draft to an embedding endpoint on every keystroke is a privacy cost they did
    not agree to when they installed a bookmark manager.
    """
    body = (text or "").strip()[:MAX_CONTEXT_CHARS]
    if not body:
        return {"query": "", "hits": [], "probes": []}

    probes = [s.strip() for s in _SENT_SPLIT.split(body) if len(s.strip()) >= 4][:5]
    if not probes:
        probes = [body]

    pooled: dict[int, dict] = {}
    for p in probes:
        resp = quick_search(conn, p, limit=limit)
        for rank, hit in enumerate(resp.hits, start=1):
            slot = pooled.setdefault(
                hit.bookmark_id,
                {"bookmark_id": hit.bookmark_id, "url": hit.url, "title": hit.title,
                 "folder": hit.folder, "domain": hit.domain,
                 "snippet": _clip(hit.snippet, SNIPPET_CHARS),
                 "score": 0.0, "matched": []},
            )
            slot["score"] += 1.0 / (60 + rank)
            slot["matched"].append(_clip(p, 80))
    ranked = sorted(pooled.values(), key=lambda d: (-d["score"], d["bookmark_id"]))[:limit]
    for d in ranked:
        d["score"] = round(d["score"], 6)
    return {"query": _clip(body, 200), "probes": probes, "hits": ranked}


# ---------------------------------------------------------------------------
# synthesis
# ---------------------------------------------------------------------------

_SYNTH_SYSTEM = (
    "You answer strictly from the numbered bookmark excerpts given to you. "
    "Return JSON only, shaped as "
    '{"claims":[{"text":"...","sources":[1,2]}],"gaps":["..."]}. '
    "Every claim must cite at least one source number. If the excerpts do not "
    "support an answer, return an empty claims list and say why in gaps. "
    "Never use knowledge that is not in the excerpts."
)


@dataclass(slots=True)
class Synthesis:
    query: str
    claims: list[dict] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    #: True when the model did not return a usable shape and the claims below
    #: are extractive fallbacks rather than a synthesis.
    degraded: bool = False
    model: str = ""

    def as_dict(self) -> dict:
        return {
            "query": self.query, "claims": self.claims, "sources": self.sources,
            "gaps": self.gaps, "degraded": self.degraded, "model": self.model,
        }


def _source_block(sources: list[dict]) -> str:
    parts = []
    for s in sources:
        parts.append(
            f"[{s['n']}] {s['title']}\n"
            f"    url: {s['url']}\n"
            f"    excerpt: {s['excerpt']}"
        )
    return "\n".join(parts)


async def synthesize(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 8,
    provider: Provider | None = None,
    settings: Settings | None = None,
    response: SearchResponse | None = None,
) -> Synthesis:
    """Answer a question over the library, with per-claim provenance.

    The sources and the gap list are computed from the retrieval result and do
    not depend on the model. Only the claims do. When the model returns
    something unusable the result degrades to one extractive claim per source
    and says so, rather than inventing a synthesis or raising.
    """
    st = settings or get_settings()
    resp = response
    if resp is None:
        resp = await search(conn, query, limit=limit, settings=st, provider=provider)

    sources: list[dict] = []
    for n, hit in enumerate(resp.hits[:limit], start=1):
        rec = bookmark_record(conn, hit.bookmark_id, settings=st)
        excerpt = ""
        if rec:
            excerpt = rec["summary"] or _clip(hit.snippet, SNIPPET_CHARS)
        sources.append({
            "n": n, "bookmark_id": hit.bookmark_id, "url": hit.url,
            "title": hit.title, "excerpt": excerpt or _clip(hit.snippet, SNIPPET_CHARS),
            "health": (rec or {}).get("health", {}).get("status", "unknown"),
            "badge": (rec or {}).get("badge", ""),
        })

    gaps = _deterministic_gaps(resp, sources)
    if not sources:
        return Synthesis(query=query, gaps=gaps or ["nothing in the library matched"],
                         model="none")

    prov = provider or get_provider(st)
    user = f"Question: {query}\n\nExcerpts:\n{_source_block(sources)}"
    try:
        raw = await prov.chat_json(_SYNTH_SYSTEM, user)
    except Exception as exc:  # provider down, no key, rate limited
        return Synthesis(query=query, claims=_extractive(sources), sources=sources,
                         gaps=[*gaps, f"model unavailable: {exc}"], degraded=True,
                         model=prov.name)

    claims = _coerce_claims(raw, len(sources))
    if not claims:
        fallback = _extractive(sources)
        why = ("model returned no usable claims; showing indexed excerpts"
               if fallback else
               "model returned no usable claims and the sources have no indexed text")
        return Synthesis(query=query, claims=fallback, sources=sources,
                         gaps=[*gaps, why], degraded=True, model=prov.name)
    model_gaps = [str(g) for g in (raw.get("gaps") or []) if str(g).strip()][:5]
    return Synthesis(query=query, claims=claims, sources=sources,
                     gaps=[*gaps, *model_gaps], model=prov.name)


def _coerce_claims(raw: dict, n_sources: int) -> list[dict]:
    items = raw.get("claims")
    if not isinstance(items, list):
        return []
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        text = str(it.get("text") or "").strip()
        if not text:
            continue
        cites = it.get("sources") or []
        nums = []
        for c in cites if isinstance(cites, list) else []:
            try:
                v = int(c)
            except (TypeError, ValueError):
                continue
            if 1 <= v <= n_sources:
                nums.append(v)
        if not nums:
            continue  # an uncited claim is exactly what this tool exists to prevent
        out.append({"text": text[:600], "sources": sorted(set(nums))})
    return out[:12]


def _extractive(sources: list[dict]) -> list[dict]:
    return [
        {"text": s["excerpt"], "sources": [s["n"]]}
        for s in sources if s["excerpt"]
    ]


def _deterministic_gaps(resp: SearchResponse, sources: list[dict]) -> list[str]:
    """Gaps that are true regardless of what the model says."""
    gaps: list[str] = []
    empty = [f for f, size in (resp.facet_sizes or {}).items() if size == 0]
    if empty:
        gaps.append("no candidates from facet(s): " + ", ".join(sorted(empty)))
    dead = [s["bookmark_id"] for s in sources if s["health"] in {"gone", "soft_gone"}]
    if dead:
        gaps.append(f"{len(dead)} cited bookmark(s) look dead; excerpts are from the index")
    thin = [s["n"] for s in sources if len(s["excerpt"]) < 40]
    if thin:
        gaps.append(f"{len(thin)} source(s) have little or no indexed text")
    return gaps


# ---------------------------------------------------------------------------
# writes
# ---------------------------------------------------------------------------


def save_bookmark(
    conn: sqlite3.Connection,
    url: str,
    *,
    title: str = "",
    folder: str = "",
    date_added: int | None = None,
    settings: Settings | None = None,
) -> dict:
    """Insert one bookmark, or return the existing row for the same URL.

    This writes to facetmark's index only. The browser's own bookmark store is
    never touched -- that is a deliberate boundary, not an omission: a tool that
    rewrites your bookmarks is a tool you cannot safely uninstall.
    """
    st = settings or get_settings()
    nu = normalize_url(url)
    row = conn.execute("SELECT id FROM bookmark WHERE url_hash = ?", (nu.hash,)).fetchone()
    if row is not None:
        rec = bookmark_record(conn, row["id"], settings=st)
        assert rec is not None
        rec["created"] = False
        return rec

    host = nu.host
    domain = registrable_domain(host)
    privacy = 1 if host_excluded(host, st.privacy_excluded_domains) else 0
    ts = int(time.time())
    # folder_depth counts real nesting, and a folder created through the API is
    # a single level. It is emphatically not folder.count("/"): folder names
    # legitimately contain slashes, which is why the display path is never split.
    cur = conn.execute(
        "INSERT INTO bookmark(url, url_norm, url_hash, title, folder, folder_depth, "
        "  host, domain, date_added, source, indexable, privacy_skipped, "
        "  created_at, updated_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,'api',?,?,?,?)",
        (nu.original, nu.normalized, nu.hash, title, folder,
         1 if folder else 0, host, domain,
         date_added if date_added is not None else ts,
         1 if nu.indexable else 0, privacy, ts, ts),
    )
    bid = int(cur.lastrowid)
    sync_fts(conn, bid, title=title, body="", summary="", topics=([folder] if folder else ()))
    conn.commit()
    rec = bookmark_record(conn, bid, settings=st)
    assert rec is not None
    rec["created"] = True
    return rec


def record_open(conn: sqlite3.Connection, bookmark_id: int, *, query: str = "") -> None:
    """Log that the user actually opened a result. Feeds nothing yet by design.

    The metabolism layer needs an honest usage signal, and the only honest
    signal is one collected before anyone decides how to score it.
    """
    conn.execute(
        "UPDATE bookmark SET open_count = open_count + 1, last_opened_at = ? WHERE id = ?",
        (int(time.time()), bookmark_id),
    )
    conn.execute(
        "INSERT INTO interaction(bookmark_id, kind, query, at) VALUES(?,?,?,?)",
        (bookmark_id, "open", query or None, int(time.time())),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------


def library_stats(conn: sqlite3.Connection) -> dict:
    def one(sql: str, *p) -> int:
        r = conn.execute(sql, p).fetchone()
        return int(r[0]) if r and r[0] is not None else 0

    stats = {
        "bookmarks": one("SELECT COUNT(*) FROM bookmark"),
        "indexable": one("SELECT COUNT(*) FROM bookmark WHERE indexable=1"),
        "privacy_skipped": one("SELECT COUNT(*) FROM bookmark WHERE privacy_skipped=1"),
        "with_body": one("SELECT COUNT(*) FROM content WHERE COALESCE(char_count,0) > 0"),
        "enriched": one("SELECT COUNT(*) FROM enrichment"),
        "intent_kept": one("SELECT COUNT(*) FROM intent_query WHERE kept=1"),
        "sessions": one("SELECT COUNT(*) FROM session"),
        "edges": one("SELECT COUNT(*) FROM edge"),
        "domains": one("SELECT COUNT(DISTINCT domain) FROM bookmark WHERE domain <> ''"),
        "queue": fetchstore.queue_stats(conn),
        "health": healthmod.summary(conn),
    }
    stats["vectors"] = dbmod.count_vectors(conn) if dbmod.vec_tables_exist(conn) else {}
    stats["edges_by_kind"] = {
        r["kind"]: r["n"]
        for r in conn.execute("SELECT kind, COUNT(*) n FROM edge GROUP BY kind").fetchall()
    }
    return stats


# ---------------------------------------------------------------------------
# indexing orchestration
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class IndexReport:
    steps: dict[str, Any] = field(default_factory=dict)
    seconds: dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"steps": self.steps, "seconds": {k: round(v, 2) for k, v in self.seconds.items()}}


async def index_all(
    conn: sqlite3.Connection,
    *,
    provider: Provider | None = None,
    settings: Settings | None = None,
    fetch: bool = True,
    limit: int | None = None,
    force: bool = False,
    progress=None,
) -> IndexReport:
    """Everything after import, in the one order that works.

    The order is not cosmetic. Content vectors must exist before intent
    filtering runs, because the filter probes the live index with each candidate
    query and asks whether the page it came from comes back. Filtering before
    the vectors exist means probing an index with one facet missing, which
    rejects good queries for the wrong reason.
    """
    st = settings or get_settings()
    prov = provider or get_provider(st)
    rep = IndexReport()

    def note(name: str, value: Any, t0: float) -> None:
        rep.steps[name] = value
        rep.seconds[name] = time.perf_counter() - t0
        if progress:
            progress(name, value)

    if fetch:
        t = time.perf_counter()
        cr = await fetchstore.crawl(conn, limit=limit, refetch=force, settings=st)
        note("fetch", cr.as_dict(), t)

    t = time.perf_counter()
    er = await enrich_all(conn, provider=prov, settings=st, limit=limit, force=force)
    note("enrich", {"enriched": er.enriched, "skipped": er.skipped_unchanged,
                    "failed": er.failed, "queries": er.queries_generated}, t)

    t = time.perf_counter()
    vc = await embed_content(conn, provider=prov, settings=st, force=force)
    note("embed_content", {"embedded": vc.content_written, "skipped": vc.content_skipped,
                           "dim": vc.dim, "model": vc.model}, t)

    t = time.perf_counter()
    ir = await filter_intents(conn, provider=prov, settings=st)
    note("filter_intents", {"candidates": ir.candidates, "kept": ir.kept,
                            "dropped": ir.dropped, "keep_rate": round(ir.keep_rate, 4),
                            "rank_histogram": ir.rank_histogram}, t)

    t = time.perf_counter()
    vi = await embed_intents(conn, provider=prov, settings=st, force=force)
    note("embed_intents", {"embedded": vi.intent_written}, t)

    t = time.perf_counter()
    sr = sessmod.build_sessions(conn)
    note("sessions", {"eps": sr.eps, "reason": sr.reason, "sessions": sr.n_sessions,
                      "assigned": sr.n_assigned, "coverage": round(sr.coverage, 4)}, t)

    t = time.perf_counter()
    es = edgemod.build_edges(conn)
    note("edges", {"counts": es.counts, "total": es.total, "skipped": es.skipped}, t)

    conn.commit()
    return rep


def import_file(
    conn: sqlite3.Connection, path: str, *, settings: Settings | None = None
) -> dict:
    stats = import_bookmarks(conn, path, settings=settings)
    conn.commit()
    return {
        "parsed": stats.total_parsed, "inserted": stats.inserted, "updated": stats.updated,
        "merged_duplicates": stats.merged_duplicates,
        "non_indexable": stats.non_indexable, "missing_dates": stats.missing_dates,
        "privacy_skipped": stats.privacy_skipped, "folders": stats.folders,
        "max_depth": stats.max_depth, "timestamp_unit": stats.timestamp_unit,
        "source": stats.source, "warnings": stats.warnings,
    }


__all__ = [
    "SNIPPET_CHARS",
    "SUMMARY_CHARS",
    "Config",
    "FULL",
    "IndexReport",
    "Synthesis",
    "bookmark_record",
    "import_file",
    "index_all",
    "library_stats",
    "pairing_token",
    "quick_search",
    "record_open",
    "related_records",
    "rotate_token",
    "save_bookmark",
    "search",
    "session_list",
    "session_record",
    "suggest_from_context",
    "synthesize",
]
