"""Persistence for link health. Append-only, and there is no delete path.

Every check is a new row. Nothing is overwritten, for two reasons that both
matter:

* ``gone`` needs **two** high-confidence confirmations at least
  ``health_gone_confirm_days`` apart, which is unanswerable if each check
  clobbers the last one;
* the history *is* the explanation. "Timed out on the 3rd, timed out on the
  10th, reader proxy got it on the 11th" is a story the user can read and
  overrule. A single mutable ``status`` column is a verdict with no appeal.

This module deliberately contains no ``DELETE`` statement, on ``health`` or on
``bookmark``. Demotion (``search.decay``) is the strongest action the system
takes against a dead link, and even that is reversible and multiplicative.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from typing import Any

from ..config import Settings, get_settings
from .synth import HealthCheck
from .verdicts import HIGH_CONFIDENCE, Status

#: Backoff schedule for `unreachable`: 1 day, doubling, capped at 30. A host
#: that has been down for a month does not become more informative by being
#: asked hourly.
BACKOFF_BASE_S = 86_400
BACKOFF_CAP_S = 30 * 86_400

#: Verdicts that mean "this check did not succeed", used to find the start of
#: the current failure run.
_FAILING = (
    Status.GONE.value, Status.SOFT_GONE.value,
    Status.RESTRICTED.value, Status.UNREACHABLE.value,
)


def record_check(conn: sqlite3.Connection, bookmark_id: int, check: HealthCheck) -> int:
    """Append one check. Returns the new ``health.id``."""
    local = json.dumps(check.local.as_dict(), ensure_ascii=False) if check.local else None
    ext = (json.dumps(check.external.as_dict(), ensure_ascii=False)
           if check.external else None)
    cur = conn.execute(
        "INSERT INTO health(bookmark_id, checked_at, verdict, http_status, "
        "confidence, local_evidence, external_evidence, archive_url) "
        "VALUES(?,?,?,?,?,?,?,?)",
        (int(bookmark_id), int(check.checked_at), check.status.value,
         check.http_status, float(check.confidence), local, ext,
         check.archive_url or None),
    )
    return int(cur.lastrowid or 0)


def latest(conn: sqlite3.Connection, bookmark_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM health WHERE bookmark_id=? ORDER BY checked_at DESC, id DESC LIMIT 1",
        (int(bookmark_id),),
    ).fetchone()


def history(conn: sqlite3.Connection, bookmark_id: int, *, limit: int = 20) -> list[sqlite3.Row]:
    return list(conn.execute(
        "SELECT * FROM health WHERE bookmark_id=? ORDER BY checked_at DESC, id DESC LIMIT ?",
        (int(bookmark_id), int(limit)),
    ))


def first_failed_at(conn: sqlite3.Connection, bookmark_id: int) -> int | None:
    """Start of the *current* run of failures.

    Walking back to the first-ever failure would be wrong: a page that broke in
    2023, was fixed, and broke again last week has been failing for a week, and
    the Wayback comparison ("was a snapshot taken after we started failing")
    depends on getting that boundary right.
    """
    rows = conn.execute(
        "SELECT checked_at, verdict FROM health WHERE bookmark_id=? "
        "ORDER BY checked_at DESC, id DESC",
        (int(bookmark_id),),
    ).fetchall()
    start: int | None = None
    for r in rows:
        if r["verdict"] not in _FAILING:
            break
        start = int(r["checked_at"])
    return start


def gone_confirmations(
    conn: sqlite3.Connection, bookmark_id: int, *, min_confidence: float = HIGH_CONFIDENCE
) -> list[int]:
    """Timestamps of high-confidence ``gone`` checks, oldest first."""
    return [
        int(r["checked_at"])
        for r in conn.execute(
            "SELECT checked_at FROM health WHERE bookmark_id=? AND verdict=? "
            "AND confidence >= ? ORDER BY checked_at ASC",
            (int(bookmark_id), Status.GONE.value, float(min_confidence)),
        )
    ]


def is_confirmed_gone(
    conn: sqlite3.Connection,
    bookmark_id: int,
    *,
    confirm_days: int = 7,
    min_confidence: float = HIGH_CONFIDENCE,
) -> bool:
    """Two high-confidence ``gone`` checks at least ``confirm_days`` apart.

    The gap is the point. Two checks five minutes apart during one outage are
    one observation with extra steps.
    """
    stamps = gone_confirmations(conn, bookmark_id, min_confidence=min_confidence)
    if len(stamps) < 2:
        return False
    return (stamps[-1] - stamps[0]) >= confirm_days * 86_400


def consecutive_failures(conn: sqlite3.Connection, bookmark_id: int) -> int:
    rows = conn.execute(
        "SELECT verdict FROM health WHERE bookmark_id=? ORDER BY checked_at DESC, id DESC",
        (int(bookmark_id),),
    ).fetchall()
    n = 0
    for r in rows:
        if r["verdict"] not in _FAILING:
            break
        n += 1
    return n


def retry_after_seconds(failures: int) -> int:
    if failures <= 0:
        return BACKOFF_BASE_S
    return min(BACKOFF_BASE_S * (2 ** (failures - 1)), BACKOFF_CAP_S)


@dataclass(slots=True)
class HealthState:
    """What the UI is allowed to show for one bookmark."""

    bookmark_id: int
    status: Status = Status.UNKNOWN
    confidence: float = 0.0
    checked_at: int | None = None
    http_status: int | None = None
    archive_url: str = ""
    confirmed_gone: bool = False
    consecutive_failures: int = 0
    next_check_after: int | None = None

    @property
    def show_in_graveyard(self) -> bool:
        """The only view that treats a link as dead -- and it still lists the
        bookmark everywhere else."""
        return self.status is Status.GONE and self.confirmed_gone

    @property
    def badge(self) -> str:
        return {
            Status.RESTRICTED: "may be region-restricted",
            Status.DRIFTED: "content changed",
            Status.SOFT_GONE: "page looks emptied",
            Status.GONE: "link appears dead",
            Status.UNREACHABLE: "",
            Status.ALIVE: "",
            Status.UNKNOWN: "",
        }[self.status]

    def as_dict(self) -> dict[str, Any]:
        return {
            "bookmark_id": self.bookmark_id,
            "status": self.status.value,
            "confidence": self.confidence,
            "checked_at": self.checked_at,
            "http_status": self.http_status,
            "archive_url": self.archive_url,
            "confirmed_gone": self.confirmed_gone,
            "badge": self.badge,
            "next_check_after": self.next_check_after,
        }


def state_of(
    conn: sqlite3.Connection, bookmark_id: int, *, settings: Settings | None = None
) -> HealthState:
    st = settings or get_settings()
    row = latest(conn, bookmark_id)
    if row is None:
        return HealthState(bookmark_id=bookmark_id)
    status = Status(row["verdict"]) if row["verdict"] in Status._value2member_map_ \
        else Status.UNKNOWN
    fails = consecutive_failures(conn, bookmark_id)
    return HealthState(
        bookmark_id=bookmark_id,
        status=status,
        confidence=float(row["confidence"] or 0.0),
        checked_at=int(row["checked_at"]),
        http_status=row["http_status"],
        archive_url=row["archive_url"] or "",
        confirmed_gone=is_confirmed_gone(
            conn, bookmark_id, confirm_days=st.health_gone_confirm_days),
        consecutive_failures=fails,
        next_check_after=(int(row["checked_at"]) + retry_after_seconds(fails)
                          if fails else None),
    )


def summary(conn: sqlite3.Connection) -> dict[str, int]:
    """Latest verdict per bookmark, counted. Bookmarks never checked are
    reported as ``unchecked`` rather than silently omitted."""
    rows = conn.execute(
        "SELECT h.verdict AS v, COUNT(*) AS n FROM health h "
        "JOIN (SELECT bookmark_id, MAX(checked_at) AS mx FROM health GROUP BY bookmark_id) m "
        "  ON m.bookmark_id = h.bookmark_id AND m.mx = h.checked_at "
        "GROUP BY h.verdict"
    ).fetchall()
    out = {r["v"]: int(r["n"]) for r in rows}
    total = conn.execute("SELECT COUNT(*) FROM bookmark WHERE indexable=1").fetchone()[0]
    checked = conn.execute("SELECT COUNT(DISTINCT bookmark_id) FROM health").fetchone()[0]
    out["unchecked"] = max(0, int(total) - int(checked))
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def due_for_check(
    conn: sqlite3.Connection,
    *,
    limit: int = 200,
    min_interval_days: int = 30,
    now_ts: int | None = None,
    ids: list[int] | None = None,
) -> list[sqlite3.Row]:
    """Bookmarks worth probing now: never checked, or past their backoff.

    Returns the columns the probe needs (url, title, indexed body stats) so the
    caller does not have to re-query per bookmark.
    """
    now = int(time.time()) if now_ts is None else int(now_ts)
    sql = [
        "SELECT b.id, b.url, b.title, b.privacy_skipped, "
        "       COALESCE(c.char_count, 0) AS known_chars, "
        "       COALESCE(c.body_text, '') AS known_body, "
        "       COALESCE(c.body_hash, '') AS known_hash, "
        "       h.checked_at AS last_checked, h.verdict AS last_verdict "
        "FROM bookmark b "
        "LEFT JOIN content c ON c.bookmark_id = b.id "
        "LEFT JOIN (SELECT bookmark_id, MAX(checked_at) AS checked_at, verdict FROM health "
        "           GROUP BY bookmark_id) h ON h.bookmark_id = b.id "
        "WHERE b.indexable = 1",
    ]
    params: list[Any] = []
    if ids:
        sql.append(f"AND b.id IN ({','.join('?' * len(ids))})")
        params.extend(int(i) for i in ids)
    sql.append("ORDER BY COALESCE(h.checked_at, 0) ASC, b.id ASC")
    rows = list(conn.execute(" ".join(sql), params))
    if ids:
        return rows[:limit]

    out: list[sqlite3.Row] = []
    for r in rows:
        if r["last_checked"] is None:
            out.append(r)
        else:
            fails = consecutive_failures(conn, int(r["id"]))
            wait = retry_after_seconds(fails) if fails else min_interval_days * 86_400
            if now - int(r["last_checked"]) >= wait:
                out.append(r)
        if len(out) >= limit:
            break
    return out
