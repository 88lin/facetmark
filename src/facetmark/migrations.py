"""Ordered schema migrations, and the version check that makes them mandatory.

``db.SCHEMA_SQL`` is written entirely in ``CREATE TABLE IF NOT EXISTS``. That is
the right shape for creating a database and the wrong shape for upgrading one:
a file written by an older release opens cleanly, reports no error, and then
fails at the first query that touches a column added later. The failure lands
far from its cause, usually on a user's machine, and the only evidence is a
stack trace about a column nobody remembers removing.

So every schema change after v1 ships as an entry here, and the version the file
was written with is checked on every open.

The rules that keep this honest:

* **One entry per version, in order.** Entry *n* takes a database from ``n-1``
  to ``n``. There is no way to skip one and no way to reorder them.
* **Each entry is its own transaction**, and writing ``meta.schema_version`` is
  its last statement. An interrupted upgrade leaves the file at the last
  version that fully applied, never halfway through one.
* **A file newer than the code is an error.** Downgrading data is not something
  this project can promise to do without losing rows, so it refuses instead of
  guessing.
* **The file is copied before the first entry runs.** A migration bug is the
  one class of bug with no recovery path, and a snapshot costs seconds.
* **Entries are written to be re-runnable.** They should not be re-run -- the
  version guard prevents it -- but a migration that checks before it acts is a
  migration that can be repaired by hand without corrupting the file.

Adding a migration means: append a ``Migration`` here, *and* make the same
change in ``SCHEMA_SQL`` so a fresh database is born at the new version.
``tests/test_db.py`` compares a fresh database against a migrated one column by
column, which is what stops those two from drifting apart.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "MIGRATIONS",
    "SCHEMA_VERSION",
    "Migration",
    "SchemaStatus",
    "SchemaTooNew",
    "apply_pending",
    "backup_database",
    "database_path",
    "schema_status",
]


class SchemaTooNew(RuntimeError):
    """The database was written by a newer facetmark than the one running."""


@dataclass(frozen=True)
class Migration:
    """One step. ``version`` is what the database is at once ``fn`` returns."""

    version: int
    note: str
    fn: Callable[[sqlite3.Connection], None]


# ---------------------------------------------------------------------------
# the migrations
# ---------------------------------------------------------------------------


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    # Positional indexing: PRAGMA results do not depend on the caller's
    # row_factory, and a migration may run on a connection that has none.
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _v2_browser_queue_backoff(conn: sqlite3.Connection) -> None:
    """Give the browser queue somewhere to record *when* a retry is allowed.

    Without this the queue only knows how many attempts an item has had, so a
    page that fails because the site is rate-limiting gets handed straight back
    to the extension on the next poll -- three attempts burned in as many
    seconds against a host that needed a minute.
    """
    if "next_attempt_at" not in _columns(conn, "fetch_queue"):
        conn.execute("ALTER TABLE fetch_queue ADD COLUMN next_attempt_at INTEGER")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_fetch_queue_ready "
        "ON fetch_queue(state, next_attempt_at, queued_at)"
    )


def _v3_content_vector_provenance(conn: sqlite3.Connection) -> None:
    """Record *what text* each content vector was built from.

    ``embed_content`` used to decide what needed embedding by asking whether a
    bookmark had a vector at all. A library indexed before its pages were
    fetched therefore kept its title-only vectors forever: the body arrived, the
    summary arrived, and the vector -- the thing search actually ranks on --
    never moved. Only ``facetmark reindex`` rebuilt it, and nothing told the
    user it was out of date.

    Vectors already in the file have unknown provenance, so this deliberately
    backfills nothing. They land as stale and get rebuilt by the next
    ``facetmark index``, which is the honest answer: this build cannot know what
    text produced them.
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS vec_content_meta ("
        "  bookmark_id INTEGER PRIMARY KEY REFERENCES bookmark(id) ON DELETE CASCADE,"
        "  text_hash   TEXT NOT NULL,"
        "  updated_at  INTEGER NOT NULL"
        ")"
    )


MIGRATIONS: tuple[Migration, ...] = (
    Migration(2, "browser queue remembers when a retry is allowed", _v2_browser_queue_backoff),
    Migration(3, "content vectors remember what they were built from",
              _v3_content_vector_provenance),
)

#: What this build writes into a new database. Derived from the migration list
#: rather than declared next to it, because the two drifting apart is exactly
#: the bug this module exists to prevent.
SCHEMA_VERSION: int = MIGRATIONS[-1].version if MIGRATIONS else 1


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SchemaStatus:
    """What the file says, what the code wants, and what stands between them."""

    found: int | None  # None: the file has no tables yet
    expected: int
    pending: tuple[Migration, ...]

    @property
    def fresh(self) -> bool:
        return self.found is None

    @property
    def too_new(self) -> bool:
        return self.found is not None and self.found > self.expected

    @property
    def current(self) -> bool:
        return not self.pending and not self.too_new

    def as_dict(self) -> dict:
        return {
            "found": self.found,
            "expected": self.expected,
            "fresh": self.fresh,
            "current": self.current,
            "too_new": self.too_new,
            "pending": [{"version": m.version, "note": m.note} for m in self.pending],
        }


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def _recorded_version(conn: sqlite3.Connection) -> int | None:
    if not _table_exists(conn, "meta"):
        return None
    row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    if row is not None:
        try:
            return int(row[0])
        except (TypeError, ValueError):
            return 1
    # A meta table with no version marker is either a database this code just
    # created and has not stamped yet, or one from before versioning existed.
    # Rows decide which: an empty file is new, a populated one is old.
    if _table_exists(conn, "bookmark"):
        n = conn.execute("SELECT COUNT(*) FROM bookmark").fetchone()[0]
        if n:
            return 1
    return None


def schema_status(conn: sqlite3.Connection) -> SchemaStatus:
    found = _recorded_version(conn)
    pending: tuple[Migration, ...] = ()
    if found is not None and found < SCHEMA_VERSION:
        pending = tuple(m for m in MIGRATIONS if m.version > found)
    return SchemaStatus(found=found, expected=SCHEMA_VERSION, pending=pending)


# ---------------------------------------------------------------------------
# applying
# ---------------------------------------------------------------------------


def database_path(conn: sqlite3.Connection) -> Path | None:
    """The file behind ``main``, or None for an in-memory database."""
    for row in conn.execute("PRAGMA database_list"):
        if row[1] == "main":
            return Path(row[2]) if row[2] else None
    return None


def backup_database(conn: sqlite3.Connection, *, suffix: str) -> Path | None:
    """Snapshot the file next to itself. Returns None for in-memory databases.

    ``VACUUM INTO`` is used rather than a file copy because it takes a
    transactionally consistent snapshot -- a plain copy of a WAL database can
    catch it mid-checkpoint.
    """
    src = database_path(conn)
    if src is None:
        return None
    dest = src.with_name(f"{src.name}.{suffix}")
    dest.unlink(missing_ok=True)
    conn.execute("VACUUM INTO ?", (str(dest),))
    return dest


def apply_pending(
    conn: sqlite3.Connection, *, backup: bool = True
) -> tuple[list[Migration], Path | None]:
    """Run every migration the file has not seen. Returns what ran, and the backup."""
    status = schema_status(conn)
    if status.too_new:
        raise SchemaTooNew(
            f"database is at schema v{status.found} but this facetmark only knows "
            f"v{status.expected}. Upgrade facetmark, or point at a different database."
        )
    if not status.pending:
        return [], None

    saved = backup_database(conn, suffix=f"bak-v{status.found}") if backup else None

    done: list[Migration] = []
    for m in status.pending:
        conn.execute("BEGIN IMMEDIATE")
        try:
            m.fn(conn)
            conn.execute(
                "INSERT INTO meta(key, value) VALUES('schema_version', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(m.version),),
            )
        except Exception:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")
        done.append(m)
    return done, saved
