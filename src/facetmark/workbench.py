"""Library browsing and the explicitly confirmed setup workflow."""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import sqlite3
import time
import uuid

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel

from . import admin, service
from .db import SchemaMismatch, vec_tables_exist
from .importers import decode_bookmark_bytes
from .importers.discovery import discover_bookmark_files
from .modelspace import space_id, validate_space


def browse(conn, *, limit=40, offset=0, folder=None, tag=None, domain=None, session=None):
    clauses, params = [], []
    for name, value in [("folder", folder), ("domain", domain)]:
        if value is not None:
            clauses.append(f"b.{name} = ?")
            params.append(value)
    if tag is not None:
        clauses.append("EXISTS (SELECT 1 FROM json_each(b.tags) WHERE value = ?)")
        params.append(tag)
    if session is not None:
        clauses.append(
            "EXISTS (SELECT 1 FROM bookmark_session bs WHERE bs.bookmark_id=b.id AND bs.session_id=?)"
        )
        params.append(session)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    total = conn.execute("SELECT count(*) FROM bookmark b" + where, params).fetchone()[0]
    rows = conn.execute(
        "SELECT b.id AS bookmark_id, b.url, b.title, b.folder, b.tags, b.domain, b.date_added, "
        "substr(COALESCE(e.summary,c.body_text,''),1,400) AS summary, "
        "b.privacy_skipped, e.basis AS summary_basis FROM bookmark b "
        "LEFT JOIN enrichment e ON e.bookmark_id=b.id LEFT JOIN content c ON c.bookmark_id=b.id"
        + where
        + " ORDER BY COALESCE(b.date_added,b.created_at) DESC,b.id DESC LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ).fetchall()
    items = [dict(r) for r in rows]
    for item in items:
        item["tags"] = json.loads(item["tags"])
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(items) < total,
    }


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
                return tuple(int(n) for n in value.split('.') if n.isdecimal())
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
    ):
        return browse(
            request.app.state.fm.conn,
            limit=limit,
            offset=offset,
            folder=folder,
            tag=tag,
            domain=domain,
            session=session,
        )

    @app.get("/bookmarks/facets", dependencies=auth)
    async def facets(request: Request):
        conn = request.app.state.fm.conn
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
        return result

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
            "stats": stats,
            "demo": candidate.use_mock_provider,
            "pending_apply": bool(state.pending_settings),
            "vector_compatible": compatible,
            "has_vectors": vec_tables_exist(state.conn),
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
