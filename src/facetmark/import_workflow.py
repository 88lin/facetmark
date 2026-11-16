"""Local import previews, atomic receipts and a persistent import history.

No URL is fetched during preview or apply. Repeating a request ID returns its
saved receipt, so retrying after a lost response cannot import the batch twice.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from urllib.parse import unquote

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import admin, library, service
from .config import Settings
from .importers import decode_bookmark_bytes, import_bookmarks
from .importers.netscape_html import looks_like_netscape
from .normalize import normalize_url

MAX_URLS = 500
ID_PATTERN = r"^[a-zA-Z0-9_-]{12,64}$"


class UrlDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=2_000_000)
    folder: str = Field(default="", max_length=2048)
    _folder = field_validator("folder")(library._clean_text)


class UrlApply(UrlDraft):
    revision: str = Field(max_length=128)
    request_id: str = Field(pattern=ID_PATTERN)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _identifier(value: str | None) -> str:
    if value is None:
        return uuid.uuid4().hex
    if not re.fullmatch(ID_PATTERN, value):
        raise HTTPException(422, "Invalid import request ID")
    return value


def ensure_idle(state) -> None:
    if (state.jobs.running or state.crawls.running or state.health_running or state.model_users
            or any(not task.done() for task in state.chat_runs.values())):
        raise HTTPException(409, "Wait for active processing, replies or link checks before importing")


def receipt(conn, request_id: str, fingerprint: str) -> dict | None:
    row = conn.execute("SELECT request_hash,state,result FROM import_run WHERE id=?", (request_id,)).fetchone()
    if row is None:
        return None
    if row["request_hash"] != fingerprint:
        raise HTTPException(409, "This import request ID belongs to different content")
    return json.loads(row["result"]) if row["state"] in {"done", "partial"} else None


def record(conn, *, source: str, label: str, result: dict, request_id: str | None = None,
           fingerprint: str = "", state: str | None = None, error: str = "") -> str:
    identity = _identifier(request_id)
    if state is None:
        state = "partial" if result.get("skipped") or result.get("errors") or result.get("warnings") else "done"
    conn.execute(
        "INSERT INTO import_run(id,source,label,created_at,state,request_hash,result,error) VALUES(?,?,?,?,?,?,?,?) "
        "ON CONFLICT(id) DO UPDATE SET state=excluded.state,result=excluded.result,error=excluded.error",
        (identity, source, label[:2048], int(time.time()), state, fingerprint,
         json.dumps(result, ensure_ascii=False), error[:2048]),
    )
    return identity


def _valid_export(content: str) -> None:
    text = content.lstrip("\ufeff \t\r\n")
    if text.startswith(("{", "[")):
        doc = json.loads(text)
        if not isinstance(doc, dict):
            raise ValueError("Expected a browser or Facetmark bookmark export")
        if "facetmark" in doc:
            if not isinstance(doc.get("bookmarks"), list):
                raise ValueError("Bookmarks must be an array")
        elif not isinstance(doc.get("roots"), dict):
            raise ValueError("Expected Chromium roots or a Facetmark export")
    elif not looks_like_netscape(text) and not re.search(r"<DT>\s*<A\s", text, re.I):
        raise ValueError("Expected a browser HTML bookmark export")


def import_bytes(conn, raw: bytes, *, settings: Settings, source: str, label: str,
                 request_id: str | None = None) -> dict:
    identity = _identifier(request_id)
    fingerprint = _digest(source + ":" + hashlib.sha256(raw).hexdigest())
    saved = receipt(conn, identity, fingerprint)
    if saved is not None:
        return saved
    try:
        content = decode_bookmark_bytes(raw)
        _valid_export(content)
        with library.transaction(conn):
            stats = import_bookmarks(conn, content=content, settings=settings)
            result = {**service._import_stats(stats), "import_id": identity}
            record(conn, source=source, label=label, result=result,
                   request_id=identity, fingerprint=fingerprint)
        return result
    except (ValueError, TypeError, AttributeError, OverflowError, RecursionError):
        message = "Invalid bookmark export; no changes were applied"
        with library.transaction(conn):
            record(conn, source=source, label=label, result={}, request_id=identity,
                   fingerprint=fingerprint, state="failed", error=message)
        raise HTTPException(400, message) from None


def preview(conn, draft: UrlDraft) -> dict:
    lines = [(number, line.strip()) for number, line in enumerate(draft.text.splitlines(), 1) if line.strip()]
    if len(lines) > MAX_URLS:
        raise HTTPException(422, "Paste up to 500 URLs at a time")
    if not lines:
        raise HTTPException(422, "Paste at least one URL")
    seen = set()
    items = []
    for number, line in lines:
        url, _, title = line.partition("\t")
        item = {"line": number, "url": url[:8192], "title": title.strip()[:2048], "status": "invalid"}
        try:
            values = library.CreateBookmark(url=url, title=title.strip(), folder=draft.folder)
        except ValueError:
            item["reason"] = "Use one complete HTTP(S) URL per line without credentials"
        else:
            normalized = normalize_url(values.url)
            item["url"] = values.url
            if normalized.hash in seen:
                item["status"] = "duplicate"
            else:
                existing = conn.execute("SELECT id FROM bookmark WHERE url_hash=?", (normalized.hash,)).fetchone()
                item["status"] = "existing" if existing else "new"
                if existing:
                    item["bookmark_id"] = existing[0]
            seen.add(normalized.hash)
        items.append(item)
    counts = {status: sum(item["status"] == status for item in items) for status in ("new", "existing", "duplicate", "invalid")}
    return {"items": items, "counts": counts, "revision": admin.library_revision(conn)}


def apply(conn, body: UrlApply, settings: Settings) -> dict:
    fingerprint = _digest("urls:" + json.dumps({"text": body.text, "folder": body.folder}, ensure_ascii=False, sort_keys=True))
    saved = receipt(conn, body.request_id, fingerprint)
    if saved is not None:
        return saved
    if body.revision != admin.library_revision(conn):
        raise HTTPException(409, "The library changed. Preview the URLs again before importing")
    with library.transaction(conn):
        candidate = preview(conn, body)
        if not candidate["counts"]["new"]:
            raise HTTPException(422, "There are no new valid URLs to import")
        items = candidate["items"]
        for item in items:
            if item["status"] != "new":
                continue
            created = library.create_bookmark(conn, library.CreateBookmark(
                url=item["url"], title=item["title"], folder=body.folder), settings=settings)
            item.update(status="imported", bookmark_id=created["bookmark_id"])
        result = {"parsed": len(items), "inserted": candidate["counts"]["new"], "updated": 0,
                  "merged_duplicates": candidate["counts"]["existing"] + candidate["counts"]["duplicate"],
                  "skipped": candidate["counts"]["invalid"], "items": items, "import_id": body.request_id}
        record(conn, source="urls", label="Pasted URLs", result=result,
               request_id=body.request_id, fingerprint=fingerprint)
    return result


def register(app: FastAPI, auth: list) -> None:
    deps = [*auth, Depends(admin.admin_gate)]

    @app.post("/admin/import/urls/preview", dependencies=deps)
    async def url_preview(body: UrlDraft, request: Request):
        state = request.app.state.fm
        async with state.lock:
            return preview(state.conn, body)

    @app.post("/admin/import/urls", dependencies=deps)
    async def url_apply(body: UrlApply, request: Request):
        state = request.app.state.fm
        async with state.lock:
            ensure_idle(state)
            return apply(state.conn, body, state.settings)

    @app.get("/admin/import/history", dependencies=deps)
    async def history(request: Request, limit: int = Query(default=20, ge=1, le=50), offset: int = Query(default=0, ge=0)):
        state = request.app.state.fm
        async with state.lock:
            rows = state.conn.execute(
                "SELECT id,source,label,created_at,state,error,json_remove(result,'$.items') AS result "
                "FROM import_run ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?", (limit + 1, offset),
            ).fetchall()
            return {"items": [{**dict(row), "result": json.loads(row["result"])} for row in rows[:limit]],
                    "offset": offset, "limit": limit, "has_more": len(rows) > limit}

    @app.get("/admin/import/history/{identity}", dependencies=deps)
    async def history_detail(identity: str, request: Request):
        _identifier(identity)
        state = request.app.state.fm
        async with state.lock:
            row = state.conn.execute(
                "SELECT id,source,label,created_at,state,error,result FROM import_run WHERE id=?", (identity,),
            ).fetchone()
        if row is None:
            raise HTTPException(404, "Import receipt is no longer available")
        return {**dict(row), "result": json.loads(row["result"])}


def filename_label(value: str) -> str:
    return unquote(value).replace("\\", "/").rsplit("/", 1)[-1] or "Bookmark export"
