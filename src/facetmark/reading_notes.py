"""Local reading notes; never part of a model prompt or shared-folder metadata."""
from __future__ import annotations

import sqlite3
import time

from fastapi import HTTPException

MAX_NOTE_CHARS = 60_000


def validate_note(value: str) -> str:
    if not isinstance(value, str) or len(value) > MAX_NOTE_CHARS or "\x00" in value:
        raise ValueError("A reading note must be text of at most 60000 characters without NUL characters")
    return value


def read_note(conn: sqlite3.Connection, bookmark_id: int) -> dict:
    if not conn.execute("SELECT 1 FROM bookmark WHERE id=?", (bookmark_id,)).fetchone():
        raise HTTPException(404, "This bookmark no longer exists; your note draft can still be copied")
    row = conn.execute("SELECT note,revision,updated_at,legacy_extra FROM bookmark_note WHERE bookmark_id=?",
                       (bookmark_id,)).fetchone()
    return {"bookmark_id": bookmark_id, "note": row["note"] if row else "",
            "revision": row["revision"] if row else 0, "updated_at": row["updated_at"] if row else 0,
            "legacy_text": row["legacy_extra"] if row else ""}


def save_note(conn: sqlite3.Connection, bookmark_id: int, note: str, base_revision: int) -> dict:
    note = validate_note(note)
    current = read_note(conn, bookmark_id)
    if current["revision"] != base_revision:
        raise HTTPException(409, {"code": "note_conflict", "message": "This note changed in another window. "
                                 "Review the saved version before saving your draft.", "current": current})
    conn.execute("INSERT INTO bookmark_note(bookmark_id,note,revision,updated_at) VALUES(?,?,?,?) "
                 "ON CONFLICT(bookmark_id) DO UPDATE SET note=excluded.note,revision=excluded.revision,"
                 "updated_at=excluded.updated_at", (bookmark_id, note, base_revision + 1, int(time.time())))
    from .text import sync_stored_fts
    sync_stored_fts(conn, bookmark_id)
    return read_note(conn, bookmark_id)


def import_note(conn: sqlite3.Connection, bookmark_id: int, note: str, *, legacy_text: str = "", saved: bool = False) -> None:
    """Fill only never-authored notes; a saved empty note is intentional."""
    validate_note(note)
    if not (note or saved or legacy_text):
        return
    conn.execute("INSERT INTO bookmark_note(bookmark_id,note,revision,updated_at,legacy_extra) VALUES(?,?,?,?,?) "
                 "ON CONFLICT(bookmark_id) DO UPDATE SET note=CASE WHEN bookmark_note.revision=0 "
                 "THEN excluded.note ELSE bookmark_note.note END,"
                 "revision=CASE WHEN bookmark_note.revision=0 THEN excluded.revision ELSE bookmark_note.revision END,"
                 "updated_at=CASE WHEN bookmark_note.revision=0 THEN excluded.updated_at ELSE bookmark_note.updated_at END,"
                 "legacy_extra=CASE WHEN bookmark_note.legacy_extra='' THEN excluded.legacy_extra ELSE bookmark_note.legacy_extra END",
                 (bookmark_id, note, 1 if note or saved else 0, int(time.time()) if note or saved else 0, legacy_text))
