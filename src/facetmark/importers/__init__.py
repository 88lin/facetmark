"""Bookmark import: format detection, timestamp conversion, normalisation,
de-duplication and insertion.

Import is idempotent. Re-importing the same file updates titles and folders but
never duplicates rows, never moves ``date_added`` forward, and never touches
fetched content or enrichment. That matters because the file is the user's live
bookmark store and will be re-imported often.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from .. import text as textmod
from ..config import Settings, get_settings
from ..db import now
from ..normalize import host_excluded, normalize_url, registrable_domain
from . import chrome_json, netscape_html, timestamps
from .base import ImportResult, RawBookmark, folder_collisions

__all__ = [
    "ImportResult",
    "ImportStats",
    "RawBookmark",
    "chrome_json",
    "detect_and_parse",
    "import_bookmarks",
    "netscape_html",
    "read_text",
    "timestamps",
]


@dataclass(slots=True)
class ImportStats:
    total_parsed: int = 0
    inserted: int = 0
    updated: int = 0
    merged_duplicates: int = 0
    non_indexable: int = 0
    missing_dates: int = 0
    privacy_skipped: int = 0
    timestamp_unit: str | None = None
    source: str = ""
    folders: int = 0
    max_depth: int = 0
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "total_parsed": self.total_parsed,
            "inserted": self.inserted,
            "updated": self.updated,
            "merged_duplicates": self.merged_duplicates,
            "non_indexable": self.non_indexable,
            "missing_dates": self.missing_dates,
            "privacy_skipped": self.privacy_skipped,
            "timestamp_unit": self.timestamp_unit,
            "source": self.source,
            "folders": self.folders,
            "max_depth": self.max_depth,
            "warnings": self.warnings,
        }


#: Tried in order. Windows exports are frequently UTF-8 with BOM; some tools
#: emit GBK. ``cp1252`` is last because it decodes nearly any byte string, so
#: putting it earlier would hide a real GB18030 file behind mojibake.
ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "cp1252")


def decode_bookmark_bytes(raw: bytes) -> str:
    """Decode an export, tolerating BOMs and mislabelled encodings.

    Takes bytes rather than a path because the web upload has no path -- it
    holds the request body -- and both callers need the same ladder. Guessing
    wrong turns every CJK title into mojibake, which then poisons the lexical
    index, the summary and the LLM prompt alike; and because the parser only
    needs URLs and titles to *look* parseable, a wrong guess is silent.
    """
    for enc in ENCODINGS:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def read_text(path: str | Path) -> str:
    """Read a bookmark file, tolerating BOMs and mislabelled encodings."""
    return decode_bookmark_bytes(Path(path).read_bytes())


def detect_and_parse(content: str) -> ImportResult:
    """Dispatch on file shape, then fill in the detected timestamp unit."""
    stripped = content.lstrip()
    if stripped.startswith("{") and chrome_json.looks_like_chrome_json(content):
        result = chrome_json.parse(content)
    elif netscape_html.looks_like_netscape(content):
        result = netscape_html.parse(content)
    elif stripped.startswith("{"):
        result = chrome_json.parse(content)
    else:
        result = netscape_html.parse(content)

    converted, unit = timestamps.convert_all([b.date_added_raw for b in result.bookmarks])
    for b, ts in zip(result.bookmarks, converted, strict=True):
        b.date_added_raw = float(ts) if ts is not None else None
    mod_converted, _ = timestamps.convert_all([b.date_modified_raw for b in result.bookmarks])
    for b, ts in zip(result.bookmarks, mod_converted, strict=True):
        b.date_modified_raw = float(ts) if ts is not None else None
    result.timestamp_unit = unit
    if collisions := folder_collisions(result.bookmarks):
        result.warnings.append(
            f"{len(collisions)} folder display path(s) are ambiguous because a folder "
            f"name contains '/': {', '.join(collisions[:3])}"
            f"{' ...' if len(collisions) > 3 else ''}. Folder co-location may merge them."
        )
    return result


def _is_privacy_excluded(host: str, excluded: tuple[str, ...]) -> bool:
    return host_excluded(host, excluded)


def import_bookmarks(
    conn: sqlite3.Connection,
    path: str | Path | None = None,
    *,
    content: str | None = None,
    settings: Settings | None = None,
) -> ImportStats:
    """Import from a file path or from raw text."""
    st = settings or get_settings()
    if content is None:
        if path is None:
            raise ValueError("either path or content is required")
        content = read_text(path)

    parsed = detect_and_parse(content)
    stats = ImportStats(
        total_parsed=len(parsed.bookmarks),
        timestamp_unit=parsed.timestamp_unit,
        source=parsed.source,
        folders=parsed.folders,
        max_depth=parsed.max_depth,
        warnings=list(parsed.warnings),
    )
    if parsed.timestamp_unit is None and parsed.bookmarks:
        stats.warnings.append(
            "could not determine a timestamp unit; the episodic facet will be unavailable"
        )

    # ---- collapse duplicates in the source file itself -------------------
    # Keyed by normalised URL. On collision keep the earliest date_added (the
    # original save) and the richest title/folder.
    staged: dict[str, dict] = {}
    for b in parsed.bookmarks:
        nu = normalize_url(b.url)
        if not nu.indexable:
            stats.non_indexable += 1
        if b.date_added_raw is None:
            stats.missing_dates += 1

        row = staged.get(nu.hash)
        added = int(b.date_added_raw) if b.date_added_raw is not None else None
        if row is None:
            staged[nu.hash] = {
                "url": b.url,
                "url_norm": nu.normalized,
                "url_hash": nu.hash,
                "title": b.title,
                "folder": b.folder,
                "folder_depth": b.folder_depth,
                "host": nu.host,
                "domain": registrable_domain(nu.host),
                "date_added": added,
                "date_modified": int(b.date_modified_raw)
                if b.date_modified_raw is not None
                else None,
                "indexable": 1 if nu.indexable else 0,
                "note": b.note,
            }
        else:
            stats.merged_duplicates += 1
            if added is not None and (row["date_added"] is None or added < row["date_added"]):
                row["date_added"] = added
            if len(b.title) > len(row["title"]):
                row["title"] = b.title
            if not row["folder"] and b.folder:
                row["folder"] = b.folder
                row["folder_depth"] = b.folder_depth
            if b.note and not row["note"]:
                row["note"] = b.note

    # ---- upsert ----------------------------------------------------------
    ts = now()
    excluded = tuple(st.privacy_excluded_domains)
    for row in staged.values():
        privacy = 1 if (row["host"] and _is_privacy_excluded(row["host"], excluded)) else 0
        if privacy:
            stats.privacy_skipped += 1

        existing = conn.execute(
            "SELECT id, date_added, title, folder, folder_depth FROM bookmark"
            " WHERE url_hash=?",
            (row["url_hash"],),
        ).fetchone()

        if existing is None:
            cur = conn.execute(
                "INSERT INTO bookmark(url, url_norm, url_hash, title, folder, folder_depth,"
                " host, domain, date_added, date_modified, source, indexable,"
                " privacy_skipped, created_at, updated_at)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    row["url"],
                    row["url_norm"],
                    row["url_hash"],
                    row["title"],
                    row["folder"],
                    row["folder_depth"],
                    row["host"],
                    row["domain"],
                    row["date_added"],
                    row["date_modified"],
                    parsed.source,
                    row["indexable"],
                    privacy,
                    ts,
                    ts,
                ),
            )
            bid = int(cur.lastrowid or 0)
            stats.inserted += 1
        else:
            bid = int(existing["id"])
            # date_added only ever moves backwards: the earliest observation is
            # the true save time, and a later export must not overwrite it.
            keep_added = existing["date_added"]
            if row["date_added"] is not None and (
                keep_added is None or row["date_added"] < keep_added
            ):
                keep_added = row["date_added"]
            conn.execute(
                "UPDATE bookmark SET url=?, url_norm=?, title=?, folder=?, folder_depth=?,"
                " host=?, domain=?, date_added=?, date_modified=?, indexable=?,"
                " privacy_skipped=?, updated_at=? WHERE id=?",
                (
                    row["url"],
                    row["url_norm"],
                    row["title"] or existing["title"],
                    row["folder"] or existing["folder"],
                    row["folder_depth"] if row["folder"] else existing["folder_depth"],
                    row["host"],
                    row["domain"],
                    keep_added,
                    row["date_modified"],
                    row["indexable"],
                    privacy,
                    ts,
                    bid,
                ),
            )
            stats.updated += 1

        # Title-only lexical index so search works before any fetching happens.
        # The note (<DD>) is genuine user-authored text, so it goes into `extra`
        # where it gets the same weight as topics and entities.
        body_row = conn.execute(
            "SELECT body_text, body_seg FROM content WHERE bookmark_id=?", (bid,)
        ).fetchone()
        enr = conn.execute(
            "SELECT summary, topics, entities, key_points FROM enrichment WHERE bookmark_id=?",
            (bid,),
        ).fetchone()
        from ..db import jload

        textmod.sync_fts(
            conn,
            bid,
            title=row["title"],
            body=(body_row["body_text"] if body_row else "") or "",
            body_seg=(body_row["body_seg"] if body_row else None),
            summary=(enr["summary"] if enr else "") or "",
            topics=jload(enr["topics"]) if enr else [],
            entities=jload(enr["entities"]) if enr else [],
            key_points=([*jload(enr["key_points"]), row["note"]] if enr else [row["note"]]),
        )

    return stats
