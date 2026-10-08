"""Local bookmark editing and portable exports.

Mutations are transactions, including the derived indexes they retire. The HTTP
routes additionally hold the service lock and refuse to race an indexing job.
The helpers never commit a caller's transaction, so a synchronization adapter
can use the same editing semantics inside its own atomic operation.
"""

from __future__ import annotations

import contextlib
import html
import json
import sqlite3
import time
from collections.abc import Iterator, Sequence
from typing import Annotated, Literal
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Path, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from . import admin, service
from .config import Settings
from .db import in_chunks, jload
from .normalize import host_excluded, normalize_url, registrable_domain

MAX_IDS = 1000
BookmarkId = Annotated[int, Field(strict=True, gt=0, le=2**63 - 1)]
Tag = Annotated[str, Field(strict=True, min_length=1, max_length=128)]
Text = Annotated[str, Field(strict=True, max_length=2048)]
Url = Annotated[str, Field(strict=True, min_length=1, max_length=8192)]
Ids = Annotated[list[BookmarkId], Field(min_length=1, max_length=MAX_IDS)]
Tags = Annotated[list[Tag], Field(max_length=100)]


def _clean_text(value: str) -> str:
    if "\x00" in value:
        raise ValueError("text cannot contain a NUL character")
    return value.strip()


def _clean_url(value: str) -> str:
    value = value.strip()
    try:
        parts = urlsplit(value)
        if (parts.scheme.lower() not in {"http", "https"} or not parts.hostname
                or parts.username is not None or parts.password is not None
                or any(c.isspace() or ord(c) < 32 for c in value)):
            raise ValueError
        # Accessing .port validates numeric ports and their range.
        _ = parts.port
        normalize_url(value)
    except (ValueError, UnicodeError):
        raise ValueError("URL must be an absolute http:// or https:// address without credentials") from None
    return value


def _clean_tags(values: list[str]) -> list[str]:
    clean = [_clean_text(v) for v in values]
    if any(not v for v in clean):
        raise ValueError("tags cannot be empty")
    return list(dict.fromkeys(clean))


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateBookmark(RequestModel):
    url: Url
    title: Text = ""
    folder: Text = ""
    tags: Tags = Field(default_factory=list)

    _url = field_validator("url")(_clean_url)
    _text = field_validator("title", "folder")(_clean_text)
    _tags = field_validator("tags")(_clean_tags)


class EditBookmark(RequestModel):
    url: Url | None = None
    title: Text | None = None
    folder: Text | None = None
    tags: Tags | None = None

    @field_validator("url", "title", "folder", "tags", mode="before")
    @classmethod
    def supplied_values_cannot_be_null(cls, value):
        if value is None:
            raise ValueError("omit unchanged fields; use an empty string or list to clear")
        return value

    _url = field_validator("url")(_clean_url)
    _text = field_validator("title", "folder")(_clean_text)
    _tags = field_validator("tags")(_clean_tags)

    @model_validator(mode="after")
    def nonempty(self):
        if not self.model_fields_set:
            raise ValueError("provide at least one field to edit")
        return self


class BulkRequest(RequestModel):
    ids: Ids
    action: Literal["move", "tag-add", "tag-remove", "delete"]
    folder: Text | None = None
    tags: Tags | None = None

    @field_validator("tags")
    @classmethod
    def tags_clean(cls, value):
        return _clean_tags(value) if value is not None else None

    @field_validator("folder")
    @classmethod
    def folder_clean(cls, value):
        return _clean_text(value) if value is not None else None

    @model_validator(mode="after")
    def action_fields(self):
        if self.action == "move":
            if self.folder is None or self.tags is not None:
                raise ValueError("move requires folder and does not take tags")
        elif self.action in {"tag-add", "tag-remove"}:
            if not self.tags or self.folder is not None:
                raise ValueError("tag changes require nonempty tags and do not take folder")
        elif self.folder is not None or self.tags is not None:
            raise ValueError("delete only takes ids")
        self.ids = list(dict.fromkeys(self.ids))
        return self


class TaxonomyRequest(RequestModel):
    kind: Literal["folder", "tag"]
    action: Literal["rename", "delete"]
    name: Text
    new_name: Text | None = None

    @model_validator(mode="after")
    def names(self):
        self.name = _clean_text(self.name)
        if not self.name:
            raise ValueError("name cannot be empty")
        if self.action == "rename":
            if self.new_name is None or not _clean_text(self.new_name):
                raise ValueError("rename requires a nonempty new_name")
            self.new_name = _clean_text(self.new_name)
        elif self.new_name is not None:
            raise ValueError("delete does not take new_name")
        if self.kind == "tag" and any(len(v) > 128 for v in (self.name, self.new_name or "")):
            raise ValueError("tags must be at most 128 characters")
        return self


class ExportFilters(RequestModel):
    folder: Text | None = None
    tag: Tag | None = None
    domain: Annotated[str, Field(strict=True, max_length=253)] | None = None
    session: BookmarkId | None = None


class ExportRequest(RequestModel):
    format: Literal["json", "html"] = "json"
    ids: Ids | None = None
    filters: ExportFilters = Field(default_factory=ExportFilters)
    query: Annotated[str, Field(strict=True, max_length=4096)] = ""


@contextlib.contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[None]:
    """A savepoint also works when a caller already owns the transaction."""
    conn.execute("SAVEPOINT library_edit")
    try:
        yield
    except BaseException:
        conn.execute("ROLLBACK TO library_edit")
        conn.execute("RELEASE library_edit")
        raise
    else:
        conn.execute("RELEASE library_edit")


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE name=?", (name,)).fetchone() is not None


def _rows(conn: sqlite3.Connection, ids: Sequence[int], *, editable: bool = True) -> list[sqlite3.Row]:
    found: dict[int, sqlite3.Row] = {}
    for chunk in in_chunks(ids):
        marks = ",".join("?" * len(chunk))
        for row in conn.execute(f"SELECT * FROM bookmark WHERE id IN ({marks})", chunk):
            found[row["id"]] = row
    missing = sorted(set(ids) - found.keys())
    if missing:
        raise HTTPException(404, {"message": "Bookmarks no longer exist", "ids": missing})
    if editable:
        protected = {bid for bid, row in found.items() if row["source"] == "karakeep"}
        if _table_exists(conn, "karakeep_doc"):
            for chunk in in_chunks(ids):
                marks = ",".join("?" * len(chunk))
                protected.update(r[0] for r in conn.execute(
                    f"SELECT bookmark_id FROM karakeep_doc WHERE bookmark_id IN ({marks})", chunk
                ))
        if protected:
            raise HTTPException(409, {"message": "Edit Karakeep-linked bookmarks in Karakeep",
                                      "ids": sorted(protected)})
    return [found[bid] for bid in dict.fromkeys(ids)]


def retire_derived(conn: sqlite3.Connection, bookmark_id: int, *, discard_content: bool = False) -> None:
    """Retire stale AI results before deleting the intent IDs that own vectors."""
    if _table_exists(conn, "vec_content"):
        conn.execute("DELETE FROM vec_content WHERE bookmark_id=?", (bookmark_id,))
    if _table_exists(conn, "vec_intent"):
        conn.execute("DELETE FROM vec_intent WHERE intent_id IN "
                     "(SELECT id FROM intent_query WHERE bookmark_id=?)", (bookmark_id,))
    for table in ("vec_content_meta", "intent_query", "enrichment"):
        conn.execute(f"DELETE FROM {table} WHERE bookmark_id=?", (bookmark_id,))
    kinds = "kind!='session'" if discard_content else "kind IN ('semantic','supersession')"
    conn.execute(f"DELETE FROM edge WHERE (src=? OR dst=?) AND {kinds}",
                 (bookmark_id, bookmark_id))
    if discard_content:
        for table in ("content", "fetch_queue", "health", "interaction"):
            conn.execute(f"DELETE FROM {table} WHERE bookmark_id=?", (bookmark_id,))


def _repair_sessions(conn: sqlite3.Connection, session_ids: Sequence[int]) -> None:
    if not session_ids:
        return
    for sid in set(session_ids):
        row = conn.execute(
            "SELECT count(*) AS n,min(COALESCE(b.date_added,b.created_at)) AS start,"
            "max(COALESCE(b.date_added,b.created_at)) AS end FROM bookmark_session bs "
            "JOIN bookmark b ON b.id=bs.bookmark_id WHERE bs.session_id=?", (sid,),
        ).fetchone()
        if row["n"]:
            conn.execute("UPDATE session SET size=?,started_at=?,ended_at=? WHERE id=?",
                         (row["n"], row["start"], row["end"], sid))
        else:
            conn.execute("DELETE FROM session WHERE id=?", (sid,))
    # Session edge weights depend on episode size. Rebuild only this cheap,
    # deterministic relation; semantic/domain relations remain untouched.
    from .edges import build_session_edges

    conn.execute("DELETE FROM edge WHERE kind='session'")
    build_session_edges(conn)


def _folder_sessions(conn: sqlite3.Connection, ids: Sequence[int]) -> list[int]:
    session_ids = []
    for chunk in in_chunks(ids):
        marks = ",".join("?" * len(chunk))
        session_ids.extend(r[0] for r in conn.execute(
            "SELECT DISTINCT bs.session_id FROM bookmark_session bs JOIN session s ON s.id=bs.session_id "
            f"WHERE s.method='folder' AND bs.bookmark_id IN ({marks})", chunk))
    return session_ids


def _destination_depth(conn: sqlite3.Connection, folder: str) -> int:
    if not folder:
        return 0
    depths = [r[0] for r in conn.execute(
        "SELECT DISTINCT folder_depth FROM bookmark WHERE folder=? AND folder_depth>0", (folder,))]
    # A known folder carries actual import structure; a newly typed name is
    # one literal folder even when that name contains slashes.
    return depths[0] if len(depths) == 1 else 1


def create_bookmark(conn: sqlite3.Connection, values: CreateBookmark, *, settings: Settings) -> dict:
    nu = normalize_url(values.url)
    now = int(time.time())
    with transaction(conn):
        duplicate = conn.execute("SELECT id FROM bookmark WHERE url_hash=?", (nu.hash,)).fetchone()
        if duplicate:
            raise HTTPException(409, {"message": "This URL is already saved", "bookmark_id": duplicate[0]})
        cursor = conn.execute(
            "INSERT INTO bookmark(url,url_norm,url_hash,title,folder,folder_depth,host,domain,"
            "date_added,date_modified,source,indexable,privacy_skipped,tags,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,'api',?,?,?,?,?)",
            (nu.original, nu.normalized, nu.hash, values.title, values.folder,
             _destination_depth(conn, values.folder), nu.host, registrable_domain(nu.host), now, now,
             int(nu.indexable), int(host_excluded(nu.host, settings.privacy_excluded_domains)),
             json.dumps(values.tags, ensure_ascii=False), now, now),
        )
        bid = int(cursor.lastrowid)
        service.sync_fts_tag_refresh(conn, bid)
        record = service.bookmark_record(conn, bid, settings=settings)
    return {**record, "created": True}


def update_bookmark(conn: sqlite3.Connection, bookmark_id: int, values: EditBookmark,
                    *, settings: Settings, _repair: bool = True) -> dict:
    with transaction(conn):
        old = _rows(conn, [bookmark_id])[0]
        changes = values.model_dump(exclude_unset=True)
        changed = {key for key, value in changes.items()
                   if value != (jload(old[key], []) if key == "tags" else old[key])}
        if not changed:
            return {**service.bookmark_record(conn, bookmark_id, settings=settings), "updated": False}
        if "tags" in changes:
            changes["tags"] = json.dumps(changes["tags"], ensure_ascii=False)
        if "url" in changed:
            nu = normalize_url(changes["url"])
            duplicate = conn.execute("SELECT id FROM bookmark WHERE url_hash=? AND id!=?",
                                     (nu.hash, bookmark_id)).fetchone()
            if duplicate:
                raise HTTPException(409, {"message": "This URL is already saved", "bookmark_id": duplicate[0]})
            changes.update(url_norm=nu.normalized, url_hash=nu.hash, host=nu.host,
                           domain=registrable_domain(nu.host), indexable=int(nu.indexable),
                           privacy_skipped=int(host_excluded(nu.host, settings.privacy_excluded_domains)),
                           open_count=0, last_opened_at=None)
        session_ids = []
        if "folder" in changed:
            # This API names one exact folder. A slash in its display name is
            # a literal character, not enough evidence to invent nesting.
            changes["folder_depth"] = _destination_depth(conn, changes["folder"])
            session_ids = _folder_sessions(conn, [bookmark_id]) if _repair else []
            conn.execute("DELETE FROM bookmark_session WHERE bookmark_id=? AND session_id IN "
                         "(SELECT id FROM session WHERE method='folder')", (bookmark_id,))
        changes.update(date_modified=int(time.time()), updated_at=int(time.time()))
        conn.execute("UPDATE bookmark SET " + ",".join(f"{k}=?" for k in changes) + " WHERE id=?",
                     [*changes.values(), bookmark_id])
        # Tags are not part of the enrichment prompt or embedding recipe.
        # Refiling or changing title/URL is; its previous summary is stale.
        if changed.intersection({"url", "title", "folder"}):
            retire_derived(conn, bookmark_id, discard_content="url" in changed)
        service.sync_fts_tag_refresh(conn, bookmark_id)
        _repair_sessions(conn, session_ids)
        record = service.bookmark_record(conn, bookmark_id, settings=settings)
    return {**record, "updated": True}


def delete_bookmarks(conn: sqlite3.Connection, ids: Sequence[int]) -> dict:
    ids = list(dict.fromkeys(ids))
    with transaction(conn):
        _rows(conn, ids)
        session_ids = []
        for bid in ids:
            session_ids.extend(r[0] for r in conn.execute(
                "SELECT session_id FROM bookmark_session WHERE bookmark_id=?", (bid,)))
            retire_derived(conn, bid, discard_content=True)
            for table in ("fts_tri", "fts_seg"):
                conn.execute(f"DELETE FROM {table} WHERE rowid=?", (bid,))
            # Foreign keys remove content, sessions, relations and interactions;
            # virtual FTS/vec tables above have no cascade support.
            conn.execute("DELETE FROM bookmark WHERE id=?", (bid,))
        _repair_sessions(conn, session_ids)
    return {"deleted": len(ids), "ids": ids}


def bulk_edit(conn: sqlite3.Connection, body: BulkRequest, *, settings: Settings) -> dict:
    with transaction(conn):
        rows = _rows(conn, body.ids)
        if body.action == "delete":
            return {"updated": 0, **delete_bookmarks(conn, body.ids)}
        sessions = _folder_sessions(conn, body.ids) if body.action == "move" else []
        updated = 0
        for row in rows:
            if body.action == "move":
                values = EditBookmark(folder=body.folder)
            else:
                tags = jload(row["tags"], [])
                replacement = (list(dict.fromkeys([*tags, *body.tags])) if body.action == "tag-add"
                               else [tag for tag in tags if tag not in body.tags])
                if len(replacement) > 100:
                    raise HTTPException(422, "A bookmark cannot have more than 100 tags")
                values = EditBookmark(tags=replacement)
            updated += int(update_bookmark(conn, row["id"], values, settings=settings, _repair=False)["updated"])
        _repair_sessions(conn, sessions)
    return {"updated": updated, "deleted": 0, "ids": body.ids}


def edit_taxonomy(conn: sqlite3.Connection, body: TaxonomyRequest, *, settings: Settings) -> dict:
    with transaction(conn):
        if body.kind == "folder":
            ids = [r[0] for r in conn.execute("SELECT id FROM bookmark WHERE folder=? ORDER BY id", (body.name,))]
        else:
            ids = [r[0] for r in conn.execute(
                "SELECT b.id FROM bookmark b WHERE EXISTS "
                "(SELECT 1 FROM json_each(b.tags) WHERE value=?) ORDER BY b.id", (body.name,))]
        if not ids:
            raise HTTPException(404, "Folder or tag no longer exists")
        rows = _rows(conn, ids)
        sessions = _folder_sessions(conn, ids) if body.kind == "folder" else []
        updated = 0
        for row in rows:
            if body.kind == "folder":
                values = EditBookmark(folder=body.new_name if body.action == "rename" else "")
            else:
                tags = jload(row["tags"], [])
                replacement = ([body.new_name if tag == body.name else tag for tag in tags]
                               if body.action == "rename" else [tag for tag in tags if tag != body.name])
                values = EditBookmark(tags=list(dict.fromkeys(replacement)))
            updated += int(update_bookmark(conn, row["id"], values, settings=settings, _repair=False)["updated"])
        _repair_sessions(conn, sessions)
    return {"updated": updated, "deleted": 0, "ids": ids}


def export_library(conn: sqlite3.Connection, body: ExportRequest) -> dict:
    from . import __version__
    from .importers.facetmark_json import FORMAT_VERSION, MARKER
    from .search.querylang import filter_sets, parse_query

    parsed = parse_query(body.query)
    if parsed.text:
        raise HTTPException(422, "Export query must contain filters only; export selected results for a text search")
    include, exclude, ignored = filter_sets(conn, parsed)
    if parsed.ignored or ignored:
        raise HTTPException(422, {"message": "Invalid export filters", "filters": [*parsed.ignored, *ignored]})
    if body.ids is not None:
        _rows(conn, body.ids, editable=False)
        include = set(body.ids) if include is None else include.intersection(body.ids)
    clauses, params = [], []
    for key in ("folder", "domain"):
        value = getattr(body.filters, key)
        if value is not None:
            clauses.append(f"b.{key}=?")
            params.append(value)
    if body.filters.tag is not None:
        clauses.append("EXISTS (SELECT 1 FROM json_each(b.tags) WHERE value=?)")
        params.append(body.filters.tag)
    if body.filters.session is not None:
        clauses.append("EXISTS (SELECT 1 FROM bookmark_session bs WHERE bs.bookmark_id=b.id AND bs.session_id=?)")
        params.append(body.filters.session)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    records = []
    record_ids = []
    for row in conn.execute("SELECT b.* FROM bookmark b" + where + " ORDER BY b.id", params):
        if row["id"] in exclude or (include is not None and row["id"] not in include):
            continue
        record = {key: row[key] for key in ("url", "title", "folder", "folder_depth", "date_added")}
        record["tags"] = jload(row["tags"], [])
        if row["date_modified"] is not None:
            record["date_modified"] = row["date_modified"]
        records.append(record)
        record_ids.append(row["id"])
    if body.format == "json":
        reading_data = service.export_reading_data(conn, record_ids)
        for bid, record in zip(record_ids, records, strict=True):
            record.update(reading_data[bid])
    return {MARKER: {"version": FORMAT_VERSION, "app_version": __version__,
                     "exported_at": int(time.time()), "count": len(records), "query": body.query,
                     "full": body.format == "json", "filters": body.filters.model_dump(exclude_none=True)},
            "bookmarks": records}


def netscape_html(payload: dict) -> str:
    """Standard Netscape HTML, with literal folder names kept intact."""
    lines = ['<!DOCTYPE NETSCAPE-Bookmark-file-1>',
             '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
             '<TITLE>Facetmark bookmarks</TITLE>', '<H1>Facetmark bookmarks</H1>', '<DL><p>']
    groups: dict[tuple[str, int], list[dict]] = {}
    for record in payload["bookmarks"]:
        groups.setdefault((record["folder"], record["folder_depth"]), []).append(record)
    for (folder, depth), records in groups.items():
        parts = folder.split("/") if depth > 1 and len(folder.split("/")) == depth else [folder]
        parts = [part for part in parts if part]
        for part in parts:
            lines.extend([f'<DT><H3>{html.escape(part)}</H3>', '<DL><p>'])
        for record in records:
            attrs = [f'HREF="{html.escape(record["url"], quote=True)}"']
            for key, attr in (("date_added", "ADD_DATE"), ("date_modified", "LAST_MODIFIED")):
                if record.get(key) is not None:
                    attrs.append(f'{attr}="{int(record[key])}"')
            if record["tags"]:
                attrs.append(f'TAGS="{html.escape(",".join(record["tags"]), quote=True)}"')
            lines.append(f'<DT><A {" ".join(attrs)}>{html.escape(record["title"])}</A>')
        lines.extend('</DL><p>' for _ in parts)
    lines.append('</DL><p>')
    return "\n".join(lines) + "\n"


def register(app: FastAPI, auth: list) -> None:
    deps = [*auth, Depends(admin.admin_gate)]

    def writable(state):
        if state.jobs.running:
            raise HTTPException(409, "Stop the index job before changing bookmarks")

    @app.post("/admin/library/bookmarks", dependencies=deps)
    async def create(body: CreateBookmark, request: Request):
        state = request.app.state.fm
        async with state.lock:
            writable(state)
            return create_bookmark(state.conn, body, settings=state.settings)

    @app.patch("/admin/library/bookmarks/{bookmark_id}", dependencies=deps)
    async def edit(body: EditBookmark, request: Request, bookmark_id: int = Path(gt=0, le=2**63 - 1)):
        state = request.app.state.fm
        async with state.lock:
            writable(state)
            return update_bookmark(state.conn, bookmark_id, body, settings=state.settings)

    @app.delete("/admin/library/bookmarks/{bookmark_id}", dependencies=deps)
    async def delete(request: Request, bookmark_id: int = Path(gt=0, le=2**63 - 1)):
        state = request.app.state.fm
        async with state.lock:
            writable(state)
            return delete_bookmarks(state.conn, [bookmark_id])

    @app.post("/admin/library/bulk", dependencies=deps)
    async def bulk(body: BulkRequest, request: Request):
        state = request.app.state.fm
        async with state.lock:
            writable(state)
            return bulk_edit(state.conn, body, settings=state.settings)

    @app.post("/admin/library/taxonomy", dependencies=deps)
    async def taxonomy(body: TaxonomyRequest, request: Request):
        state = request.app.state.fm
        async with state.lock:
            writable(state)
            return edit_taxonomy(state.conn, body, settings=state.settings)

    @app.post("/admin/library/export", dependencies=deps)
    async def export(body: ExportRequest, request: Request):
        state = request.app.state.fm
        async with state.lock:
            payload = export_library(state.conn, body)
        data = (netscape_html(payload) if body.format == "html"
                else json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
        return Response(data, media_type="text/html" if body.format == "html" else "application/json",
                        headers={"Content-Disposition": f'attachment; filename="facetmark-{stamp}.{body.format}"',
                                 "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
