"""Apply domain exclusions to existing records without deleting bookmarks."""

from __future__ import annotations

import sqlite3

from .config import Settings
from .db import vec_tables_exist
from .normalize import host_excluded


def refresh_privacy(conn: sqlite3.Connection, settings: Settings) -> None:
    """Refresh persisted flags and retire vectors for newly excluded pages.

    Bodies and enrichments stay local. Removing only derived vectors prevents
    semantic retrieval of excluded pages and makes unexcluded pages eligible
    for the next indexing run again.
    """
    changes = []
    excluded = []
    for row in conn.execute("SELECT id, host, privacy_skipped FROM bookmark"):
        private = int(host_excluded(row["host"], settings.privacy_excluded_domains))
        if private != row["privacy_skipped"]:
            changes.append((private, row["id"]))
        if private:
            excluded.append((row["id"],))
    conn.executemany("UPDATE bookmark SET privacy_skipped=? WHERE id=?", changes)
    if excluded and vec_tables_exist(conn):
        conn.executemany("DELETE FROM vec_content WHERE bookmark_id=?", excluded)
        conn.executemany("DELETE FROM vec_content_meta WHERE bookmark_id=?", excluded)
        conn.executemany(
            "DELETE FROM vec_intent WHERE intent_id IN "
            "(SELECT id FROM intent_query WHERE bookmark_id=?)", excluded,
        )
