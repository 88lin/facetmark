"""Library browsing and the explicitly confirmed setup workflow."""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import sqlite3
import time
import uuid
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel

from . import admin, service
from .collection import CollectionScope, predicate
from .db import SchemaMismatch, vec_tables_exist
from .importers import decode_bookmark_bytes
from .importers.discovery import discover_bookmark_files
from .modelspace import space_id, validate_space


def browse(conn, *, limit=40, offset=0, folder=None, tag=None, domain=None, session=None,
           q="", status="all", sort="newest"):
    scope = CollectionScope(folder=folder, tag=tag, domain=domain, session=session, q=q, status=status)
    condition, params = predicate(scope)
    where = " WHERE " + condition
    total = conn.execute("SELECT count(*) FROM bookmark b" + where, params).fetchone()[0]
    orders = {"newest": "COALESCE(b.date_added,b.created_at) DESC,b.id DESC",
              "oldest": "COALESCE(b.date_added,b.created_at),b.id",
              "title": "COALESCE(NULLIF(e.ai_title,''),b.title) COLLATE NOCASE,b.id",
              "domain": "b.domain,b.title COLLATE NOCASE,b.id"}
    order = orders[sort]
    rows = conn.execute(
        "SELECT b.id AS bookmark_id, b.url, b.title, b.folder, b.tags, b.domain, b.date_added, "
        "COALESCE(e.ai_title,'') AS ai_title, e.language AS summary_language, "
        "COALESCE(e.summary,'') AS summary, substr(COALESCE(c.body_text,''),1,400) AS snippet, "
        "b.privacy_skipped, e.basis AS summary_basis, ef.error AS summary_error, "
        "CASE WHEN ef.bookmark_id IS NOT NULL THEN 'failed' "
        "WHEN COALESCE(e.summary,'')!='' THEN 'done' ELSE 'pending' END AS summary_status "
        "FROM bookmark b LEFT JOIN enrichment e ON e.bookmark_id=b.id "
        "LEFT JOIN content c ON c.bookmark_id=b.id LEFT JOIN enrichment_failure ef ON ef.bookmark_id=b.id"
        + where
        + f" ORDER BY {order} LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ).fetchall()
    items = [dict(r) for r in rows]
    for item in items:
        item["tags"] = json.loads(item["tags"])
    count_where, count_params = predicate(scope, include_status=False)
    # The status counts ignore the status filter by design, so an unfiltered
    # request already has the answer in `total`: one aggregate pass, not three.
    if not count_where.strip():
        done, failed = conn.execute(
            "SELECT sum(CASE WHEN COALESCE(e.summary,'')!='' AND ef.bookmark_id IS NULL THEN 1 ELSE 0 END), "
            "sum(CASE WHEN ef.bookmark_id IS NOT NULL THEN 1 ELSE 0 END) "
            "FROM bookmark b LEFT JOIN enrichment e ON e.bookmark_id=b.id "
            "LEFT JOIN enrichment_failure ef ON ef.bookmark_id=b.id").fetchone()
        counts = {"total": int(total), "done": int(done or 0), "failed": int(failed or 0)}
    else:
        counts = conn.execute(
            "SELECT count(*) AS total, "
            "sum(CASE WHEN COALESCE(e.summary,'')!='' AND ef.bookmark_id IS NULL THEN 1 ELSE 0 END) AS done, "
            "sum(CASE WHEN ef.bookmark_id IS NOT NULL THEN 1 ELSE 0 END) AS failed "
            "FROM bookmark b LEFT JOIN enrichment e ON e.bookmark_id=b.id "
            "LEFT JOIN enrichment_failure ef ON ef.bookmark_id=b.id WHERE " + count_where, count_params,
        ).fetchone()
        counts = {key: int(counts[key] or 0) for key in ("total", "done", "failed")}
    counts["pending"] = counts["total"] - counts["done"] - counts["failed"]
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(items) < total,
        "summary_counts": counts,
    }


def browse_facets(conn, group, *, q="", limit=50, offset=0):
    """Browse the complete taxonomy; the overview's top 200 is not a directory."""
    if group == "tags":
        grouped = (
            "SELECT j.value AS value,count(DISTINCT b.id) AS count "
            "FROM bookmark b,json_each(b.tags) j WHERE j.value!='' GROUP BY j.value"
        )
    else:
        column = {"folders": "folder", "domains": "domain"}[group]
        grouped = (
            f"SELECT {column} AS value,count(*) AS count FROM bookmark "
            f"WHERE {column}!='' GROUP BY {column}"
        )
    # instr treats %, _ and quotes as literal input, not LIKE wildcards.
    source = f" FROM ({grouped}) WHERE instr(lower(value),lower(?))>0"
    total = conn.execute("SELECT count(*)" + source, (q,)).fetchone()[0]
    # A full name must remain reachable on the first page even when hundreds
    # of parent paths contain the same text. Ties retain stable name ordering.
    items = [dict(row) for row in conn.execute(
        "SELECT value,count" + source + " ORDER BY CASE "
        "WHEN lower(value)=lower(?) THEN 0 "
        "WHEN instr(lower(value),lower(?))=1 THEN 1 ELSE 2 END,"
        "value COLLATE NOCASE,value LIMIT ? OFFSET ?",
        (q, q, q, limit, offset),
    )]
    return {"items": items, "total": total, "offset": offset, "limit": limit,
            "has_more": offset + len(items) < total}


def stored_folder_parts(folder, minimum_depth, maximum_depth):
    """Recover only the hierarchy established by the existing import metadata.

    Imports render ancestors with '/', while API-created folders remain literal
    names even when they contain slashes. Depth disagreements or slash-containing
    ancestor names cannot be reconstructed from the legacy display string alone.
    Preserve those exact identities as one readable entry rather than guessing.
    """
    if not folder:
        return []
    parts = folder.split("/")
    if minimum_depth == maximum_depth == len(parts) and all(parts):
        return parts
    return [folder]


def folder_path(conn, *, folder):
    depths = conn.execute(
        "SELECT min(folder_depth),max(folder_depth) FROM bookmark WHERE folder=?", (folder,),
    ).fetchone()
    return {"value": folder, "parts": stored_folder_parts(folder, *depths)}


def browse_folder_children(conn, *, parent="", limit=50, offset=0):
    """Page one recoverable directory level without widening exact selection."""
    prefix = f"{parent}/" if parent else ""
    rows = conn.execute(
        "SELECT folder,min(folder_depth),max(folder_depth),count(*) FROM bookmark "
        "WHERE folder != '' AND substr(folder,1,?)=? GROUP BY folder",
        (len(prefix), prefix),
    ).fetchall()
    counts = {row[0]: row[3] for row in rows}
    directory = {}
    for folder, minimum, maximum, _count in rows:
        parts = stored_folder_parts(folder, minimum, maximum)
        values = ["/".join(parts[:index + 1]) for index in range(len(parts))]
        if parent:
            if parent not in values[:-1]:
                continue
            index = values.index(parent) + 1
        else:
            index = 0
        value = values[index]
        child = directory.setdefault(value, {
            "value": value, "label": parts[index], "count": counts.get(value, 0),
            "has_children": False,
        })
        child["has_children"] |= index < len(parts) - 1
    ordered = sorted(directory.values(), key=lambda item: (
        not item["count"], item["label"].casefold(), item["label"],
    ))
    items = ordered[offset:offset + limit]
    return {"items": items, "total": len(ordered), "offset": offset, "limit": limit,
            "has_more": offset + len(items) < len(ordered)}


class SourceRequest(BaseModel):
    source_id: str


class ApplyRequest(BaseModel):
    confirm_rebuild: bool = False


def register(app: FastAPI, auth: list) -> None:
    deps = [*auth, Depends(admin.admin_gate)]

    @app.post('/admin/updates/check', dependencies=deps)
    async def check_updates():
        import httpx

        from . import __version__

        try:
            async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
                response = await client.get('https://api.github.com/repos/88lin/facetmark/releases/latest',
                    headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'Facetmark'})
            if response.status_code == 404:
                return {'current': __version__, 'latest': None, 'available': False,
                        'url': 'https://github.com/88lin/facetmark/actions/workflows/desktop.yml'}
            response.raise_for_status()
            version = str(response.json().get('tag_name', '')).removeprefix('v')
            def parts(value):
                # Pad to three components so "2.0" and "2.0.0" compare equal;
                # a pre-release tag compares as its numeric hull, which is the
                # conservative answer for an update prompt.
                numbers = [int(n) for n in value.split('-')[0].split('.') if n.isdecimal()]
                return tuple((numbers + [0, 0, 0])[:max(3, len(numbers))])
            return {'current': __version__, 'latest': version, 'available': parts(version) > parts(__version__),
                    'url': 'https://github.com/88lin/facetmark/releases/latest'}
        except (httpx.HTTPError, ValueError):
            raise HTTPException(502, 'Cannot check GitHub releases right now; retry or open the downloads page') from None

    @app.get('/admin/extension-status', dependencies=deps)
    async def extension_status(request: Request):
        last_seen = request.app.state.fm.extension_seen_at
        return {'last_seen_at': last_seen,
                'recently_connected': bool(last_seen and time.time() - last_seen < 180)}

    @app.get("/bookmarks", dependencies=auth)
    async def bookmarks(
        request: Request,
        limit: int = Query(40, ge=1, le=200),
        offset: int = Query(0, ge=0),
        folder: str | None = None,
        tag: str | None = None,
        domain: str | None = None,
        session: int | None = None,
        q: str = Query("", max_length=4096),
        status: Literal["all", "pending", "done", "failed"] = "all",
        sort: Literal["newest", "oldest", "title", "domain"] = "newest",
    ):
        try:
            predicate(CollectionScope(folder=folder, tag=tag, domain=domain, session=session, q=q, status=status))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        return browse(
            request.app.state.fm.conn,
            limit=limit,
            offset=offset,
            folder=folder,
            tag=tag,
            domain=domain,
            session=session,
            q=q, status=status, sort=sort,
        )

    @app.get("/bookmarks/facets", dependencies=auth)
    async def facets(request: Request):
        state = request.app.state.fm
        conn = state.conn
        # The workbench polls this every 4 s. The counts only move when the
        # library revision moves, so a revision-keyed memo removes three full
        # aggregate scans per poll on large collections.
        cached = getattr(facets, "cache", None)
        revision = admin.library_revision(conn)
        if cached and cached[0] == revision:
            return cached[1]
        result = {
            name: [
                dict(r)
                for r in conn.execute(
                    f"SELECT {col} AS value,count(*) AS count FROM bookmark WHERE {col}!='' "
                    f"GROUP BY {col} ORDER BY count DESC,{col} LIMIT 200"
                )
            ]
            for name, col in [("folders", "folder"), ("domains", "domain")]
        }
        result["tags"] = [
            dict(r)
            for r in conn.execute(
                "SELECT j.value,count(DISTINCT b.id) AS count FROM bookmark b,json_each(b.tags) j "
                "GROUP BY j.value ORDER BY count DESC,j.value LIMIT 200"
            )
        ]
        facets.cache = (revision, result)
        return result

    @app.get("/bookmarks/facets/{group}", dependencies=auth)
    async def facet_directory(
        request: Request,
        group: Literal["folders", "tags", "domains"],
        q: str = Query("", max_length=2048),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ):
        return browse_facets(request.app.state.fm.conn, group, q=q, limit=limit, offset=offset)

    @app.get("/bookmarks/folders/tree", dependencies=auth)
    async def folder_children(
        request: Request,
        parent: str = Query("", max_length=2048),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ):
        return browse_folder_children(request.app.state.fm.conn, parent=parent, limit=limit, offset=offset)

    @app.get("/bookmarks/folders/path", dependencies=auth)
    async def selected_folder_path(request: Request, folder: str = Query("", max_length=2048)):
        return folder_path(request.app.state.fm.conn, folder=folder)

    def sources(state):
        return [
            (
                hmac.new(
                    state.token.encode(), str(path.resolve()).encode(), hashlib.sha256
                ).hexdigest(),
                path,
                browser,
                profile,
            )
            for path, browser, profile in discover_bookmark_files()
        ]

    @app.get("/admin/import/sources", dependencies=deps)
    async def import_sources(request: Request):
        # Discovery lists names only. No bookmark content is read here.
        return {
            "sources": [
                {"id": sid, "browser": browser, "profile": profile}
                for sid, _, browser, profile in sources(request.app.state.fm)
            ]
        }

    @app.post("/admin/import/source", dependencies=deps)
    async def import_source(body: SourceRequest, request: Request):
        state = request.app.state.fm
        selected = next(
            (
                path
                for sid, path, _, _ in sources(state)
                if hmac.compare_digest(sid, body.source_id)
            ),
            None,
        )
        if selected is None:
            raise HTTPException(404, "Source is no longer available; discover sources again")
        try:
            with selected.open("rb") as stream:
                raw = stream.read(admin.MAX_UPLOAD_BYTES + 1)
        except OSError:
            raise HTTPException(
                409, "Cannot read the selected source; export HTML from the browser instead"
            ) from None
        if len(raw) > admin.MAX_UPLOAD_BYTES:
            raise HTTPException(413, "Source exceeds 64 MB; export a smaller library")
        async with state.lock:
            if state.jobs.running:
                raise HTTPException(409, "Stop the processing job before importing bookmarks")
            return service.import_content(
                state.conn, decode_bookmark_bytes(raw), settings=state.settings
            )

    @app.get("/admin/setup-status", dependencies=deps)
    async def setup_status(request: Request):
        state = request.app.state.fm
        candidate = admin.draft_settings(state.settings, state.pending_settings)
        compatible = True
        try:
            validate_space(state.conn, candidate)
        except SchemaMismatch:
            compatible = False
        stats = service.library_stats(state.conn)
        return {
            "bookmarks": stats["bookmarks"],
            # total_changes sees this connection; data_version also sees jobs
            # and CLI writes committed through a different connection.
            "library_revision": f"{state.conn.total_changes}:"
                                f"{state.conn.execute('PRAGMA data_version').fetchone()[0]}",
            "stats": stats,
            "demo": candidate.use_mock_provider,
            "summary_language": candidate.summary_language,
            "pending_apply": bool(state.pending_settings),
            "vector_compatible": compatible,
            "has_vectors": bool(stats["vectors"] and sum(stats["vectors"]) > 0),
            "channels": {
                c: {
                    "configured": candidate.channel_ready(c),
                    "tested": state.probe_results.get(c, {}).get("fingerprint")
                    == admin.probe_fingerprint(candidate, c),
                }
                for c in ("chat", "embed")
            },
        }

    @app.post("/admin/settings/apply", dependencies=deps)
    async def apply_settings(body: ApplyRequest, request: Request):
        state = request.app.state.fm
        async with state.lock:
            if state.jobs.running:
                raise HTTPException(409, "Stop the index job before applying settings")
            candidate = admin.draft_settings(state.settings, state.pending_settings)
            changed = space_id(candidate) != space_id(state.settings)
            try:
                validate_space(state.conn, candidate)
            except SchemaMismatch:
                changed = True
            rebuild = changed and vec_tables_exist(state.conn)
            if rebuild and not body.confirm_rebuild:
                raise HTTPException(
                    409,
                    "Confirm vector rebuild. A backup is made; bookmarks and page text are kept.",
                )
            if not candidate.use_mock_provider and state.probe_results.get("embed", {}).get(
                "fingerprint"
            ) != admin.probe_fingerprint(candidate, "embed"):
                raise HTTPException(409, "Test the saved embedding settings before applying")
            backup = None
            if rebuild:
                backup = f"vectors-{int(time.time())}-{uuid.uuid4().hex[:6]}.db"
                directory = state.settings.data_dir / "backups"
                directory.mkdir(parents=True, exist_ok=True)
                with contextlib.closing(sqlite3.connect(directory / backup)) as dest:
                    state.conn.backup(dest)
                state.conn.execute("BEGIN IMMEDIATE")
                try:
                    for table in ("vec_content", "vec_intent"):
                        state.conn.execute(f"DROP TABLE IF EXISTS {table}")
                    state.conn.execute("DELETE FROM vec_content_meta")
                    state.conn.execute(
                        "DELETE FROM meta WHERE key IN ('embed_model','embed_dim','embedding_space')"
                    )
                    state.conn.execute(
                        "UPDATE intent_query SET kept=0,probe_rank=NULL,scored_at=NULL"
                    )
                    state.conn.execute("DELETE FROM edge WHERE kind='semantic'")
                    state.conn.commit()
                except Exception:
                    state.conn.rollback()
                    raise
            state.settings = candidate
            state.pending_settings.clear()
            if state._provider is not None:
                await state._provider.aclose()
                state._provider = None
            return {"applied": True, "rebuild_required": rebuild, "backup": backup}
