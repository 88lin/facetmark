"""Metadata-only, conflict-aware synchronization through a user-owned folder.

The transport is an immutable commit DAG, not a last-writer-wins snapshot.
Cloud drives can deliver independent/offline writes in either order: both
versions survive, and missing parents or concurrent edits stop automatic sync.
Only URL, title, folder, tags and date_added cross the transport boundary.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import os
import re
import sqlite3
import stat
import time
import uuid
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from . import admin, library
from .config import Settings
from .normalize import normalize_url

DIRECTORY = ".facetmark-sync"
MARKER = "Facetmark metadata sync v1\n"
FORMAT = "facetmark-library-sync"
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_COMMITS = 2048
MAX_RECORDS = 100_000
PREVIEW_SECONDS = 600
COMMIT_NAME = re.compile(r"commit-([0-9a-f-]{36})\.json\Z")
ABSENT = object()
FIELDS = ("url", "title", "folder", "tags", "date_added")


class SyncConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    folder: str = Field(default="", max_length=4096)
    enabled: bool = False
    auto_sync: bool = False
    poll_seconds: int = Field(default=60, ge=30, le=3600, strict=True)


class ApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preview_id: str = Field(min_length=1, max_length=64)
    resolutions: dict[str, str] = Field(default_factory=dict)


def _fail(message: str, status: int = 400) -> None:
    raise HTTPException(status, message)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _uuid(value: Any) -> str:
    if not isinstance(value, str):
        _fail("Invalid synchronization identifier")
    try:
        if str(uuid.UUID(value)) != value:
            raise ValueError
    except ValueError:
        _fail("Invalid synchronization identifier")
    return value


def _linked(path: Path) -> bool:
    info = path.lstat()
    # Mount-point reparse tags are Windows junctions. Cloud placeholders use
    # other tags and are legitimate OneDrive files, so do not reject all tags.
    return stat.S_ISLNK(info.st_mode) or getattr(info, "st_reparse_tag", 0) == 0xA0000003


def _read(path: Path, limit: int) -> bytes:
    if _linked(path):
        _fail("Synchronization files must not be symbolic links or junctions")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0))
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit or info.st_nlink > 1:
            _fail("Synchronization file is oversized or is not an ordinary file")
        content = stream.read(limit + 1)
    if len(content) > limit:
        _fail("Synchronization file is oversized")
    return content


def _record(value: Any) -> dict | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != set(FIELDS):
        _fail("A sync record must contain only url, title, folder, tags and date_added")
    try:
        clean = library.CreateBookmark.model_validate({k: value[k] for k in FIELDS[:-1]})
    except ValidationError as exc:
        raise HTTPException(400, "Invalid bookmark metadata in synchronization file") from exc
    if urlsplit(clean.url).username is not None or urlsplit(clean.url).password is not None:
        _fail("URLs containing embedded credentials cannot be synchronized")
    date = value["date_added"]
    if date is not None and (type(date) is not int or not 0 <= date <= 32503680000):
        _fail("Invalid date_added in synchronization file")
    return {**clean.model_dump(), "tags": sorted(clean.tags), "date_added": date}


def _decode(content: bytes) -> dict:
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                _fail("Duplicate JSON keys in synchronization file")
            result[key] = value
        return result

    try:
        result = json.loads(content.decode("utf-8"), object_pairs_hook=pairs)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise HTTPException(400, "Malformed synchronization JSON") from exc
    if not isinstance(result, dict):
        _fail("Synchronization commit must be an object")
    return result


def _transport(folder: str, data_dir: Path, *, create: bool = False) -> Path:
    requested = Path(folder)
    if not folder or not requested.is_absolute() or not requested.is_dir():
        _fail("Choose an existing absolute shared-folder path")
    for part in (requested, *requested.parents):
        if _linked(part):
            _fail("Shared-folder paths must not traverse symbolic links or junctions")
    root = requested.resolve(strict=True)
    forbidden = {"user data", ".mozilla", ".chromium", ".google-chrome"}
    parts = [part.casefold() for part in root.parts]
    if (root == Path(root.anchor) or any(part in forbidden for part in parts)
            or ("mozilla" in parts and "firefox" in parts)
            or root == data_dir.resolve() or data_dir.resolve() in root.parents):
        _fail("Choose a shared documents folder outside browser profiles and Facetmark data")
    directory = root / DIRECTORY
    if create:
        directory.mkdir(exist_ok=True)
    if not directory.is_dir() or _linked(directory):
        _fail("The Facetmark synchronization directory is missing or unsafe", 409)
    marker = directory / "FORMAT"
    if create and not marker.exists():
        if any(directory.iterdir()):
            _fail("The synchronization directory contains unrecognized files")
        try:
            with marker.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(MARKER)
        except FileExistsError:
            pass
    if not marker.exists() or _read(marker, 128) != MARKER.encode("utf-8"):
        _fail("Unrecognized Facetmark synchronization directory")
    return directory


def _history(directory: Path) -> dict:
    commits: dict[str, dict] = {}
    fingerprints: list[tuple[str, str]] = []
    size = 0
    for path in sorted(directory.iterdir()):
        if path.name in {"FORMAT", ".DS_Store", "Thumbs.db", "desktop.ini"} or (path.name.startswith(".pending-") and path.suffix == ".tmp"):
            continue
        match = COMMIT_NAME.fullmatch(path.name)
        if not match:
            _fail("Unrecognized sync file; review any cloud-drive conflict copies before continuing", 409)
        cid = _uuid(match[1])
        content = _read(path, MAX_FILE_BYTES)
        size += len(content)
        if size > MAX_TOTAL_BYTES or len(commits) >= MAX_COMMITS:
            _fail("Synchronization history exceeds the supported size; keep it intact for recovery")
        commit = _decode(content)
        if set(commit) != {"format", "version", "id", "device", "parents", "changes"}:
            _fail("Invalid synchronization commit fields")
        if commit["format"] != FORMAT or type(commit["version"]) is not int or commit["version"] != 1:
            _fail("Unsupported synchronization format")
        if _uuid(commit["id"]) != cid:
            _fail("Synchronization filename and commit identifier disagree")
        _uuid(commit["device"])
        parents = commit["parents"]
        if (not isinstance(parents, list) or len(parents) > MAX_COMMITS
                or any(not isinstance(p, str) for p in parents) or len(set(parents)) != len(parents)):
            _fail("Invalid synchronization parent list")
        for parent in parents:
            _uuid(parent)
        changes = commit["changes"]
        if not isinstance(changes, dict) or len(changes) > MAX_RECORDS:
            _fail("Invalid synchronization change set")
        commit["changes"] = {_uuid(sid): _record(record) for sid, record in changes.items()}
        commits[cid] = commit
        fingerprints.append((path.name, hashlib.sha256(content).hexdigest()))
    ancestors: dict[str, set[str]] = {}
    remaining = dict(commits)
    while remaining:
        ready = [cid for cid, value in remaining.items() if all(p in ancestors for p in value["parents"])]
        if not ready:
            _fail("Sync history is incomplete or cyclic; wait for the shared folder to finish downloading", 409)
        for cid in ready:
            ancestor = set(commits[cid]["parents"])
            for parent in commits[cid]["parents"]:
                ancestor.update(ancestors[parent])
            ancestors[cid] = ancestor
            del remaining[cid]
    versions: dict[str, list[tuple[str, dict | None]]] = {}
    for cid in ancestors:  # topological order
        for sid, record in commits[cid]["changes"].items():
            previous = [(version, value) for version, value in versions.get(sid, [])
                        if version not in ancestors[cid]]
            versions[sid] = [*previous, (cid, record)]
    if len(versions) > MAX_RECORDS:
        _fail("Synchronization library exceeds the supported record limit")
    # Concurrent identical edits are equivalent, while distinct versions retain
    # their commit IDs as explicit choices for the conflict-resolution UI.
    for sid, values in versions.items():
        unique = {_json(value): (cid, value) for cid, value in sorted(values)}
        versions[sid] = list(unique.values())
    parents = {p for commit in commits.values() for p in commit["parents"]}
    return {"revision": _digest(fingerprints), "commits": set(commits), "size_bytes": size,
            "hashes": {COMMIT_NAME.fullmatch(name)[1]: digest for name, digest in fingerprints},
            "heads": sorted(set(commits) - parents), "versions": versions}


class SharedFolderSync:
    """One manager per app state; its caller holds the application's DB lock."""

    def __init__(self, conn: sqlite3.Connection, settings: Settings):
        self.conn, self.settings = conn, settings
        self.previews: dict[str, dict] = {}
        if conn.in_transaction:
            _fail("Finish the current database transaction before initializing sync", 409)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS library_sync_state(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS library_sync_identity(
                channel TEXT NOT NULL,sync_id TEXT NOT NULL,bookmark_id INTEGER,
                PRIMARY KEY(channel,sync_id),UNIQUE(channel,bookmark_id));
            CREATE TABLE IF NOT EXISTS library_sync_baseline(
                channel TEXT NOT NULL,sync_id TEXT NOT NULL,payload TEXT NOT NULL,
                PRIMARY KEY(channel,sync_id));
            CREATE TRIGGER IF NOT EXISTS library_sync_deleted AFTER DELETE ON bookmark BEGIN
                UPDATE library_sync_identity SET bookmark_id=NULL WHERE bookmark_id=OLD.id;
            END;
        """)
        if self._get("device_id") is None:
            with conn:
                self._set("device_id", str(uuid.uuid4()))

    def _get(self, key: str, default=None):
        row = self.conn.execute("SELECT value FROM library_sync_state WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def _set(self, key: str, value) -> None:
        self.conn.execute("INSERT INTO library_sync_state VALUES(?,?) "
                          "ON CONFLICT(key) DO UPDATE SET value=excluded.value "
                          "WHERE library_sync_state.value<>excluded.value", (key, _json(value)))

    def status(self) -> dict:
        config = self._get("config", SyncConfig().model_dump())
        return {**config, "configured": bool(config["folder"]), "device_id": self._get("device_id"),
                "last_sync_at": self._get("last_sync_at"), "last_error": self._get("last_error", ""),
                "pending_conflicts": self._get("pending_conflicts", 0),
                "needs_review": self._get("needs_review", True), "metadata_only": True,
                "transport_directory": DIRECTORY}

    def configure(self, body: SyncConfig) -> dict:
        old = self._get("config", {})
        values = body.model_dump()
        if body.folder and (body.enabled or body.folder != old.get("folder")):
            directory = _transport(body.folder, self.settings.data_dir, create=True)
            values["folder"] = str(directory.parent)
        elif body.enabled:
            _fail("A shared folder is required before enabling synchronization")
        with self.conn:
            self._set("config", values)
            self._set("last_error", "")
            if old.get("folder") != values["folder"]:
                self._set("needs_review", True)
                self._set("pending_conflicts", 0)
        self.previews.clear()
        return self.status()

    def _context(self) -> tuple[Path, str, dict]:
        config = self._get("config", {})
        if not config.get("enabled"):
            _fail("Shared-folder synchronization is disabled", 409)
        directory = _transport(config["folder"], self.settings.data_dir)
        channel = _digest(str(directory))
        remote = _history(directory)
        seen = self._get(f"seen:{channel}", {})
        if set(seen) - remote["commits"]:
            _fail("Previously synchronized history is missing; restore it or wait for the folder download", 409)
        if isinstance(seen, dict) and any(remote["hashes"][cid] != digest for cid, digest in seen.items()):
            _fail("Previously synchronized commits were modified; restore the immutable history", 409)
        return directory, channel, remote

    def _revision(self) -> str:
        rows = [dict(row) for row in self.conn.execute(
            "SELECT id,url,title,folder,tags,date_added,source,privacy_skipped FROM bookmark ORDER BY id")]
        protected = []
        if library._table_exists(self.conn, "karakeep_doc"):
            protected = [row[0] for row in self.conn.execute("SELECT bookmark_id FROM karakeep_doc ORDER BY bookmark_id")]
        return _digest([rows, protected])

    def _local(self, channel: str) -> tuple[dict, dict, set, set, int, int]:
        protected = set()
        if library._table_exists(self.conn, "karakeep_doc"):
            protected.update(row[0] for row in self.conn.execute("SELECT bookmark_id FROM karakeep_doc"))
        rows = list(self.conn.execute("SELECT * FROM bookmark ORDER BY id"))
        protected.update(row["id"] for row in rows if row["source"] == "karakeep")
        existing = {row["bookmark_id"]: row["sync_id"] for row in self.conn.execute(
            "SELECT * FROM library_sync_identity WHERE channel=? AND bookmark_id IS NOT NULL", (channel,))}
        values, ids, blocked, blocked_ids = {}, {}, set(), set()
        skipped = 0
        with self.conn:
            for row in rows:
                if row["id"] in protected:
                    blocked.add(row["url_hash"])
                    if row["id"] in existing:
                        blocked_ids.add(existing[row["id"]])
                    continue
                try:
                    value = _record({k: json.loads(row[k]) if k == "tags" else row[k] for k in FIELDS})
                except (HTTPException, ValueError, TypeError):
                    blocked.add(row["url_hash"])
                    if row["id"] in existing:
                        blocked_ids.add(existing[row["id"]])
                    skipped += 1
                    continue
                sid = existing.get(row["id"])
                if sid is None:
                    sid = str(uuid.uuid4())
                    self.conn.execute("INSERT INTO library_sync_identity VALUES(?,?,?)", (channel, sid, row["id"]))
                values[sid], ids[sid] = value, row["id"]
        for row in self.conn.execute("SELECT * FROM library_sync_identity WHERE channel=?", (channel,)):
            if row["bookmark_id"] is None:
                values[row["sync_id"]] = None
                ids[row["sync_id"]] = None
        return values, ids, blocked, blocked_ids, len(protected), skipped

    @staticmethod
    def _counts(entries: list[dict], choices: dict) -> dict:
        counts = dict.fromkeys(("upload_new", "upload_update", "upload_delete", "download_new",
                                "download_update", "download_delete", "unchanged", "conflicts"), 0)
        for entry in entries:
            sid, local, versions = entry["id"], entry["local"], entry["versions"]
            if sid not in choices:
                counts["conflicts"] += 1
                continue
            target = choices[sid]
            remote = versions[0][1] if len(versions) == 1 else ABSENT
            download = target is not ABSENT and target != local
            upload = (target is not ABSENT and (len(versions) > 1 or target != remote)
                      and not (target is None and not versions))
            if download and not (target is None and local is ABSENT):
                counts["download_" + ("delete" if target is None else "new" if local is ABSENT or local is None else "update")] += 1
            if upload:
                counts["upload_" + ("delete" if target is None else "new" if remote is ABSENT or remote is None else "update")] += 1
            if not download and not upload:
                counts["unchanged"] += 1
        return counts

    def preview(self) -> dict:
        directory, channel, remote = self._context()
        local, ids, blocked, blocked_ids, excluded, unsupported = self._local(channel)
        baseline = {row["sync_id"]: json.loads(row["payload"]) for row in self.conn.execute(
            "SELECT * FROM library_sync_baseline WHERE channel=?", (channel,))}
        aliases = {}
        # Independent initial imports share URL identity until the first sync.
        # Once attached, the stable sync ID owns identity, including URL edits.
        candidates = {normalize_url(value["url"]).hash: sid for sid, value in local.items()
                      if value and sid not in remote["versions"] and sid not in baseline}
        for sid, versions in sorted(remote["versions"].items()):
            if sid in local or len(versions) != 1 or versions[0][1] is None:
                continue
            old = candidates.pop(normalize_url(versions[0][1]["url"]).hash, None)
            if old:
                aliases[old] = sid
                local[sid], ids[sid] = local.pop(old), ids.pop(old)
        entries, choices, conflicts = [], {}, []
        for sid in sorted(local.keys() | baseline.keys() | remote["versions"].keys()):
            left, base = local.get(sid, ABSENT), baseline.get(sid, ABSENT)
            versions = remote["versions"].get(sid, [])
            right = versions[0][1] if len(versions) == 1 else ABSENT
            if sid in blocked_ids or any(value and normalize_url(value["url"]).hash in blocked for _, value in versions):
                continue
            entry = {"id": sid, "local": left, "versions": versions, "bookmark_id": ids.get(sid)}
            entries.append(entry)
            if len(versions) > 1:
                reason = "remote_concurrent_changes"
            elif left == right:
                choices[sid] = left
                continue
            elif left == base:
                choices[sid] = right
                continue
            elif right == base:
                choices[sid] = left
                continue
            else:
                reason = "local_and_remote_changed"
            conflicts.append({"id": sid, "reason": reason,
                              "local": None if left is ABSENT else left,
                              "remote": None if right is ABSENT else right,
                              "remote_versions": [{"choice": f"remote:{cid}", "record": value} for cid, value in versions]})
        # Independently created UUIDs can converge on one normalized URL. The
        # local database intentionally permits only one: make this resolvable in
        # preview, rather than discovering a uniqueness failure after approval.
        by_url: dict[str, set[str]] = {}
        for entry in entries:
            sid = entry["id"]
            possible = ([choices[sid]] if sid in choices else
                        [entry["local"], *(value for _, value in entry["versions"])])
            for target in possible:
                if target is not ABSENT and target is not None:
                    by_url.setdefault(normalize_url(target["url"]).hash, set()).add(sid)
        duplicates = {sid for group in by_url.values() if len(group) > 1 for sid in group}
        for conflict in conflicts:
            if conflict["id"] in duplicates:
                conflict["can_delete"] = True
        for entry in entries:
            if entry["id"] not in duplicates or entry["id"] not in choices:
                continue
            sid = entry["id"]
            del choices[sid]
            versions = entry["versions"]
            conflicts.append({"id": sid, "reason": "duplicate_url_keep_one", "can_delete": True,
                              "local": None if entry["local"] is ABSENT else entry["local"],
                              "remote": versions[0][1] if len(versions) == 1 else None,
                              "remote_versions": [{"choice": f"remote:{cid}", "record": value} for cid, value in versions]})
        changes = []
        for entry in entries:
            sid, left, versions = entry["id"], entry["local"], entry["versions"]
            if sid not in choices or choices[sid] is ABSENT:
                continue
            target = choices[sid]
            right = versions[0][1] if len(versions) == 1 else ABSENT
            directions = []
            if target != left and not (target is None and left is ABSENT):
                directions.append("download")
            if (len(versions) != 1 or target != right) and not (target is None and not versions):
                directions.append("upload")
            if directions:
                changes.append({"id": sid, "local": None if left is ABSENT else left,
                                "remote": None if right is ABSENT else right, "target": target,
                                "local_exists": left is not ABSENT, "remote_exists": bool(versions),
                                "directions": directions})
        token = str(uuid.uuid4())
        now = time.time()
        self.previews = {key: value for key, value in self.previews.items() if value["expires"] > now}
        if len(self.previews) >= 8:
            self.previews.pop(next(iter(self.previews)))
        self.previews[token] = {"expires": now + PREVIEW_SECONDS, "directory": directory,
                                "channel": channel, "remote": remote, "local_revision": self._revision(),
                                "entries": entries, "choices": choices, "conflicts": conflicts, "aliases": aliases}
        with self.conn:
            self._set("pending_conflicts", len(conflicts))
            self._set("last_error", "")
        return {"preview_id": token, "expires_at": int(now + PREVIEW_SECONDS),
                "counts": self._counts(entries, choices), "conflicts": conflicts, "changes": changes,
                "excluded_karakeep": excluded, "excluded_unsupported": unsupported, "metadata_only": True}

    def _backup(self) -> str:
        directory = self.settings.data_dir / "backups"
        directory.mkdir(exist_ok=True)
        if _linked(directory) or directory.resolve().parent != self.settings.data_dir.resolve():
            _fail("The local backup directory is unsafe")
        path = directory / f"library-sync-{time.time_ns()}-{uuid.uuid4().hex}.db"
        # SQLite backup includes bodies/indexes for local recovery. This file is
        # deliberately outside the shared folder and is never sent to it.
        with sqlite3.connect(path) as destination:
            self.conn.backup(destination)
        return str(path)

    def _publish(self, directory: Path, remote: dict, changes: dict) -> str | None:
        if not changes:
            return None
        cid = str(uuid.uuid4())
        content = (_json({"format": FORMAT, "version": 1, "id": cid, "device": self._get("device_id"),
                          "parents": remote["heads"], "changes": changes}) + "\n").encode("utf-8")
        if len(content) > MAX_FILE_BYTES:
            _fail("This synchronization batch exceeds the supported file size")
        # Never append a commit that the next preview would reject. Existing
        # history remains readable for recovery even when a limit is reached.
        if (len(remote.get("commits", ())) >= MAX_COMMITS
                or remote.get("size_bytes", 0) + len(content) > MAX_TOTAL_BYTES
                or len(set(remote.get("versions", ())) | changes.keys()) > MAX_RECORDS):
            _fail("Synchronization history has reached its supported size; keep it intact for recovery", 409)
        temporary, target = directory / f".pending-{cid}.tmp", directory / f"commit-{cid}.json"
        try:
            with temporary.open("xb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            if target.exists():
                _fail("A synchronization commit already exists; preview again", 409)
            os.replace(temporary, target)
        finally:
            with contextlib.suppress(FileNotFoundError):
                temporary.unlink()
        return cid

    def apply(self, body: ApplyRequest, *, automatic: bool = False) -> dict:
        plan = self.previews.get(body.preview_id)
        if not plan or plan["expires"] < time.time():
            _fail("Synchronization preview expired; preview again", 409)
        directory, channel, remote = self._context()
        if (channel != plan["channel"] or remote["revision"] != plan["remote"]["revision"]
                or self._revision() != plan["local_revision"]):
            _fail("The local library or shared folder changed; preview again", 409)
        if automatic and (self.status()["needs_review"] or plan["conflicts"]):
            _fail("Synchronization needs a manual review", 409)
        choices = dict(plan["choices"])
        conflict_ids = {conflict["id"] for conflict in plan["conflicts"]}
        deletable = {conflict["id"] for conflict in plan["conflicts"] if conflict.get("can_delete")}
        if set(body.resolutions) != conflict_ids:
            _fail("Choose a resolution for each conflict, and only those conflicts", 409)
        for entry in plan["entries"]:
            sid = entry["id"]
            if sid not in conflict_ids:
                continue
            resolution = body.resolutions[sid]
            if resolution == "local":
                choices[sid] = None if entry["local"] is ABSENT else entry["local"]
            elif resolution == "delete" and sid in deletable:
                choices[sid] = None
            elif resolution == "remote" and len(entry["versions"]) == 1:
                choices[sid] = entry["versions"][0][1]
            else:
                matches = [value for cid, value in entry["versions"] if resolution == f"remote:{cid}"]
                if len(matches) != 1:
                    _fail("Invalid conflict resolution", 409)
                choices[sid] = matches[0]
        alive = {}
        for sid, value in choices.items():
            if value is not ABSENT and value is not None:
                url_hash = normalize_url(value["url"]).hash
                if url_hash in alive:
                    _fail("Two synchronized records use the same URL; keep one version and delete the other", 409)
                alive[url_hash] = sid
        counts = self._counts(plan["entries"], choices)
        imports = sum(counts[key] for key in ("download_new", "download_update", "download_delete"))
        backup = self._backup() if imports else None
        published = None
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            if self._revision() != plan["local_revision"]:
                _fail("The library changed during synchronization; preview again", 409)
            for old, new in plan["aliases"].items():
                self.conn.execute("UPDATE library_sync_identity SET sync_id=? WHERE channel=? AND sync_id=?", (new, channel, old))
            # Delete first, allowing a resolved delete/new pair to reuse a URL.
            for entry in plan["entries"]:
                target = choices[entry["id"]]
                if target is None and entry["bookmark_id"] is not None:
                    library.delete_bookmarks(self.conn, [entry["bookmark_id"]])
            # Reserve identities inside this transaction so two approved URL
            # edits may swap addresses without transient UNIQUE collisions.
            for entry in plan["entries"]:
                target = choices[entry["id"]]
                if (target is not ABSENT and target is not None and entry["bookmark_id"] is not None
                        and entry["local"] and target["url"] != entry["local"]["url"]):
                    self.conn.execute("UPDATE bookmark SET url_hash=? WHERE id=?",
                                      (f"sync-reserved-{uuid.uuid4()}", entry["bookmark_id"]))
            changes = {}
            session_ids = set()
            for entry in plan["entries"]:
                sid, bid, target = entry["id"], entry["bookmark_id"], choices[entry["id"]]
                if target is ABSENT:
                    continue
                if target is not None and target != entry["local"]:
                    fields = {k: target[k] for k in FIELDS[:-1]}
                    if bid is None:
                        created = library.create_bookmark(self.conn, library.CreateBookmark(**fields), settings=self.settings)
                        bid = created["bookmark_id"]
                        self.conn.execute("INSERT INTO library_sync_identity VALUES(?,?,?) "
                                          "ON CONFLICT(channel,sync_id) DO UPDATE SET bookmark_id=excluded.bookmark_id", (channel, sid, bid))
                    else:
                        library.update_bookmark(self.conn, bid, library.EditBookmark(**fields), settings=self.settings)
                    session_ids.update(row[0] for row in self.conn.execute("SELECT session_id FROM bookmark_session WHERE bookmark_id=?", (bid,)))
                    now = int(time.time())
                    self.conn.execute("UPDATE bookmark SET date_added=?,date_modified=?,updated_at=? "
                                      "WHERE id=? AND date_added IS NOT ?",
                                      (target["date_added"], now, now, bid, target["date_added"]))
                if target is None:
                    self.conn.execute("INSERT OR IGNORE INTO library_sync_identity VALUES(?,?,NULL)", (channel, sid))
                versions = entry["versions"]
                if (len(versions) != 1 or versions[0][1] != target) and not (not versions and target is None):
                    changes[sid] = target
                self.conn.execute("INSERT OR REPLACE INTO library_sync_baseline VALUES(?,?,?)", (channel, sid, _json(target)))
            library._repair_sessions(self.conn, list(session_ids))
            # Detect ordinary preview/apply races. A cloud write arriving after
            # this check still becomes another immutable branch, never lost data.
            checked = _history(_transport(str(directory.parent), self.settings.data_dir))
            if checked["revision"] != remote["revision"]:
                _fail("The shared folder changed during synchronization; preview again", 409)
            published = self._publish(directory, remote, changes)
            seen = dict(remote["hashes"])
            if published:
                seen[published] = hashlib.sha256(_read(directory / f"commit-{published}.json", MAX_FILE_BYTES)).hexdigest()
            self._set(f"seen:{channel}", seen)
            self._set("last_sync_at", int(time.time()))
            self._set("last_error", "")
            self._set("pending_conflicts", 0)
            self._set("needs_review", False)
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            raise
        self.previews.clear()
        return {"counts": counts, "backup_path": backup, "published_commit": published, "status": self.status()}


def manager(state) -> SharedFolderSync:
    existing = getattr(state, "library_sync", None)
    if existing is None:
        existing = SharedFolderSync(state.conn, state.settings)
        state.library_sync = existing
    return existing


async def poll(state) -> None:
    """Root lifespan creates/cancels this task before closing the DB connection."""
    while True:
        delay = 60
        try:
            async with state.lock:
                sync = manager(state)
                status = sync.status()
                delay = status["poll_seconds"]
                if (status["enabled"] and status["auto_sync"] and not status["needs_review"]
                        and not status["pending_conflicts"] and not state.jobs.running):
                    plan = sync.preview()
                    if not plan["conflicts"] and plan["changes"]:
                        sync.apply(ApplyRequest(preview_id=plan["preview_id"]), automatic=True)
                    else:
                        sync.previews.pop(plan["preview_id"], None)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # an unavailable cloud folder must not stop the app
            async with state.lock:
                sync = manager(state)
                message = exc.detail if isinstance(exc, HTTPException) else str(exc)
                with state.conn:
                    sync._set("last_error", str(message))
        await asyncio.sleep(delay)


def register(app: FastAPI, auth: list) -> None:
    deps = [*auth, Depends(admin.admin_gate)]

    async def call(request: Request, action: Literal["status", "configure", "preview", "apply"], body=None):
        state = request.app.state.fm
        async with state.lock:
            if action != "status" and state.jobs.running:
                _fail("Stop the index job before synchronizing bookmarks", 409)
            sync = manager(state)
            try:
                return getattr(sync, action)(body) if body is not None else getattr(sync, action)()
            except HTTPException as exc:
                with state.conn:
                    sync._set("last_error", str(exc.detail))
                raise
            except OSError as exc:
                with state.conn:
                    sync._set("last_error", str(exc))
                raise HTTPException(409, f"Shared folder is unavailable: {exc}") from exc

    @app.get("/admin/library/sync/status", dependencies=deps)
    async def status(request: Request):
        return await call(request, "status")

    @app.post("/admin/library/sync/config", dependencies=deps)
    async def configure(body: SyncConfig, request: Request):
        return await call(request, "configure", body)

    @app.post("/admin/library/sync/preview", dependencies=deps)
    async def preview(request: Request):
        return await call(request, "preview")

    @app.post("/admin/library/sync/apply", dependencies=deps)
    async def apply(body: ApplyRequest, request: Request):
        return await call(request, "apply", body)
