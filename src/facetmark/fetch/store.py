"""Persist fetch results, and run the channel-A -> channel-B handoff.

Two things happen here that are easy to get wrong elsewhere:

1. **Idempotency is decided by the body hash, not by the fetch.** Re-fetching a
   page that has not changed must not invalidate its enrichment, because
   enrichment costs money. ``content.body_hash`` is compared against the newly
   canonicalised body; when they match, the row's timestamps are refreshed and
   nothing downstream is touched.

2. **A failed fetch is a result, not an absence.** A 403 is recorded, and the
   bookmark is queued for the browser channel. Writing nothing would make the
   next run retry it identically and fail identically.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import httpx

from ..config import Settings, get_settings
from ..db import now
from ..normalize import body_hash
from ..text import detect_lang, segment, sync_fts
from .client import DEFER_TO_BROWSER, BatchResult, FetchPolicy, FetchResult, Verdict, fetch_many

#: A leased queue item is reclaimed after this long. Long enough for a slow page
#: plus the extension's own settle delay, short enough that a crashed tab does
#: not park a bookmark for a whole session.
LEASE_TTL_S = 300

#: After this many browser attempts the item is parked as ``failed`` rather than
#: cycling forever. It stays in the table as evidence.
MAX_BROWSER_ATTEMPTS = 3

#: How long a failed item waits before it is offered again, by attempt number.
#: The queue is polled by an extension that will happily ask every few seconds,
#: so without this an item that failed because the host was rate-limiting burns
#: all three of its attempts inside a minute and gets parked for a reason that
#: would have gone away on its own. Growing 5m -> 30m -> 2h spans a browsing
#: session, which is the timescale the transient failures actually live on.
BROWSER_RETRY_BACKOFF_S: tuple[int, ...] = (300, 1_800, 7_200)


def retry_delay_s(attempts: int) -> int:
    """Seconds to wait after ``attempts`` failed tries (1-based)."""
    if attempts < 1:
        return BROWSER_RETRY_BACKOFF_S[0]
    return BROWSER_RETRY_BACKOFF_S[min(attempts, len(BROWSER_RETRY_BACKOFF_S)) - 1]


# ---------------------------------------------------------------------------
# content rows
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class SaveOutcome:
    bookmark_id: int
    stored: bool
    """False when the fetch produced no usable body."""
    changed: bool
    """True when the body hash differs from what was already stored -- the only
    condition under which enrichment must be redone."""
    body_hash: str = ""
    queued_for_browser: bool = False


def _existing_hash(conn: sqlite3.Connection, bookmark_id: int) -> str | None:
    row = conn.execute(
        "SELECT body_hash FROM content WHERE bookmark_id=?", (bookmark_id,)
    ).fetchone()
    return row["body_hash"] if row else None


def store_body(
    conn: sqlite3.Connection,
    bookmark_id: int,
    *,
    body: str,
    title: str = "",
    extractor: str = "",
    channel: str = "a",
    http_status: int | None = None,
    final_url: str = "",
    error: str = "",
) -> SaveOutcome:
    """Write a body into ``content`` and rebuild both lexical index rows."""
    bh = body_hash(body)
    prior = _existing_hash(conn, bookmark_id)
    changed = bh != prior
    seg = segment(body)
    conn.execute(
        """
        INSERT INTO content(bookmark_id, body_text, body_seg, body_hash, char_count,
                            lang, extractor, fetch_channel, http_status, final_url,
                            fetched_at, error)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(bookmark_id) DO UPDATE SET
            body_text=excluded.body_text, body_seg=excluded.body_seg,
            body_hash=excluded.body_hash, char_count=excluded.char_count,
            lang=excluded.lang, extractor=excluded.extractor,
            fetch_channel=excluded.fetch_channel, http_status=excluded.http_status,
            final_url=excluded.final_url, fetched_at=excluded.fetched_at,
            error=excluded.error
        """,
        (bookmark_id, body, seg, bh, len(body), detect_lang(body), extractor,
         channel, http_status, final_url, now(), error),
    )
    row = conn.execute("SELECT title FROM bookmark WHERE id=?", (bookmark_id,)).fetchone()
    sync_fts(conn, bookmark_id, title=(row["title"] if row else title) or title,
             body=body, body_seg=seg)
    return SaveOutcome(bookmark_id, stored=True, changed=changed, body_hash=bh)


def record_failure(
    conn: sqlite3.Connection,
    bookmark_id: int,
    *,
    verdict: Verdict,
    http_status: int | None = None,
    final_url: str = "",
    error: str = "",
    channel: str = "a",
) -> None:
    """Remember that a fetch failed, without destroying a body we already have.

    A page that was readable last month and 403s today keeps its stored text:
    losing the index because the site added a paywall would punish the user for
    the site's decision.
    """
    conn.execute(
        """
        INSERT INTO content(bookmark_id, body_text, body_seg, body_hash, char_count,
                            extractor, fetch_channel, http_status, final_url,
                            fetched_at, error)
        VALUES(?, NULL, NULL, NULL, 0, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(bookmark_id) DO UPDATE SET
            fetch_channel=excluded.fetch_channel, http_status=excluded.http_status,
            final_url=excluded.final_url, fetched_at=excluded.fetched_at,
            error=excluded.error
        """,
        (bookmark_id, verdict.value, channel, http_status, final_url, now(), error or verdict.value),
    )


def save_result(
    conn: sqlite3.Connection,
    bookmark_id: int,
    result: FetchResult,
    *,
    channel: str = "a",
    queue_deferred: bool = True,
) -> SaveOutcome:
    if result.verdict is Verdict.OK and result.body:
        out = store_body(
            conn, bookmark_id, body=result.body, title=result.title,
            extractor=result.extractor, channel=channel,
            http_status=result.http_status, final_url=result.final_url,
        )
        clear_queue_item(conn, bookmark_id, state="done")
        return out

    record_failure(conn, bookmark_id, verdict=result.verdict,
                   http_status=result.http_status, final_url=result.final_url,
                   error=result.error, channel=channel)
    queued = False
    if queue_deferred and result.should_defer_to_browser:
        queued = enqueue_for_browser(conn, bookmark_id, reason=result.verdict.value)
    return SaveOutcome(bookmark_id, stored=False, changed=False, queued_for_browser=queued)


# ---------------------------------------------------------------------------
# channel B queue
# ---------------------------------------------------------------------------


def enqueue_for_browser(conn: sqlite3.Connection, bookmark_id: int, *, reason: str) -> bool:
    """Queue one bookmark for the extension. Returns False if it is parked."""
    row = conn.execute(
        "SELECT state, attempts FROM fetch_queue WHERE bookmark_id=?", (bookmark_id,)
    ).fetchone()
    if row is not None and row["state"] == "failed":
        return False
    conn.execute(
        """
        INSERT INTO fetch_queue(bookmark_id, reason, state, attempts, queued_at)
        VALUES(?,?, 'pending', 0, ?)
        ON CONFLICT(bookmark_id) DO UPDATE SET
            reason=excluded.reason, state='pending', leased_at=NULL,
            next_attempt_at=NULL
        """,
        (bookmark_id, reason, now()),
    )
    return True


def lease_browser_batch(
    conn: sqlite3.Connection, n: int = 3, *, ttl_s: int = LEASE_TTL_S
) -> list[dict]:
    """Hand the extension up to ``n`` URLs and mark them leased.

    Expired leases are reclaimed first, so a tab that died mid-fetch does not
    strand its bookmark. A reclaimed lease is offered again immediately: a tab
    that never reported back says nothing about whether the host is healthy,
    which is the only thing the backoff deadline is about.
    """
    ts = now()
    cutoff = ts - ttl_s
    conn.execute(
        "UPDATE fetch_queue SET state='pending', leased_at=NULL "
        "WHERE state='leased' AND (leased_at IS NULL OR leased_at < ?)",
        (cutoff,),
    )
    rows = conn.execute(
        """
        SELECT q.bookmark_id, q.reason, q.attempts, b.url, b.title
        FROM fetch_queue q JOIN bookmark b ON b.id = q.bookmark_id
        WHERE q.state='pending' AND b.indexable=1 AND b.privacy_skipped=0
          AND (q.next_attempt_at IS NULL OR q.next_attempt_at <= ?)
        ORDER BY q.queued_at LIMIT ?
        """,
        (ts, n),
    ).fetchall()
    ids = [r["bookmark_id"] for r in rows]
    if ids:
        conn.executemany(
            "UPDATE fetch_queue SET state='leased', leased_at=?, attempts=attempts+1 "
            "WHERE bookmark_id=?",
            [(now(), i) for i in ids],
        )
    return [
        {"bookmark_id": r["bookmark_id"], "url": r["url"], "title": r["title"],
         "reason": r["reason"], "attempt": r["attempts"] + 1}
        for r in rows
    ]


def complete_browser_item(
    conn: sqlite3.Connection,
    bookmark_id: int,
    *,
    body: str = "",
    title: str = "",
    final_url: str = "",
    error: str = "",
) -> SaveOutcome:
    """Accept a body the extension read out of a real tab."""
    if body and len(body.strip()) >= 1:
        out = store_body(conn, bookmark_id, body=body, title=title,
                         extractor="extension", channel="b", final_url=final_url)
        clear_queue_item(conn, bookmark_id, state="done")
        return out

    row = conn.execute(
        "SELECT attempts FROM fetch_queue WHERE bookmark_id=?", (bookmark_id,)
    ).fetchone()
    attempts = row["attempts"] if row else MAX_BROWSER_ATTEMPTS
    state = "failed" if attempts >= MAX_BROWSER_ATTEMPTS else "pending"
    retry_at = None if state == "failed" else now() + retry_delay_s(attempts)
    conn.execute(
        "UPDATE fetch_queue SET state=?, leased_at=NULL, last_error=?, next_attempt_at=? "
        "WHERE bookmark_id=?",
        (state, error or "empty body from extension", retry_at, bookmark_id),
    )
    record_failure(conn, bookmark_id, verdict=Verdict.EMPTY, final_url=final_url,
                   error=error or "empty body from extension", channel="b")
    return SaveOutcome(bookmark_id, stored=False, changed=False)


def clear_queue_item(conn: sqlite3.Connection, bookmark_id: int, *, state: str = "done") -> None:
    conn.execute(
        "UPDATE fetch_queue SET state=?, leased_at=NULL, next_attempt_at=NULL "
        "WHERE bookmark_id=?",
        (state, bookmark_id),
    )


def queue_stats(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute("SELECT state, COUNT(*) n FROM fetch_queue GROUP BY state").fetchall()
    return {r["state"]: r["n"] for r in rows}


def queue_waiting(conn: sqlite3.Connection, *, at: int | None = None) -> int:
    """How many pending items are serving a backoff rather than ready to lease.

    Reported separately from :func:`queue_stats` so ``pending: 40`` and an empty
    lease response stop looking like a bug.
    """
    ts = now() if at is None else at
    row = conn.execute(
        "SELECT COUNT(*) FROM fetch_queue "
        "WHERE state='pending' AND next_attempt_at IS NOT NULL AND next_attempt_at > ?",
        (ts,),
    ).fetchone()
    return int(row[0])


# ---------------------------------------------------------------------------
# selection + orchestration
# ---------------------------------------------------------------------------


def pending_targets(
    conn: sqlite3.Connection,
    *,
    limit: int | None = None,
    refetch: bool = False,
    ids: Sequence[int] | None = None,
) -> list[tuple[int, str, str]]:
    """Bookmarks that channel A should try, as ``(id, url, title)``.

    Excludes non-indexable rows and anything the privacy filter has claimed:
    a domain on the exclusion list should never see a request from us at all,
    which means no fetch either -- not merely no LLM call.
    """
    where = ["b.indexable=1", "b.privacy_skipped=0"]
    params: list[object] = []
    if ids is not None:
        if not ids:
            return []
        where.append(f"b.id IN ({','.join('?' * len(ids))})")
        params.extend(ids)
    if not refetch:
        where.append("(c.bookmark_id IS NULL OR c.body_hash IS NULL)")
    sql = (
        "SELECT b.id, b.url, b.title FROM bookmark b "
        "LEFT JOIN content c ON c.bookmark_id = b.id "
        f"WHERE {' AND '.join(where)} ORDER BY b.id"
    )
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    return [(r["id"], r["url"], r["title"]) for r in conn.execute(sql, params).fetchall()]


def policy_from_settings(settings: Settings | None = None) -> FetchPolicy:
    s = settings or get_settings()
    return FetchPolicy(
        concurrency=s.fetch_concurrency,
        per_host_concurrency=s.fetch_per_host_concurrency,
        per_host_min_interval_s=s.fetch_per_host_min_interval,
        timeout_s=s.fetch_timeout,
        user_agent=s.user_agent,
        respect_robots=s.respect_robots,
        robots_on_error=s.robots_on_error,
        max_crawl_delay_s=s.robots_max_crawl_delay,
    )


@dataclass(slots=True)
class CrawlReport:
    attempted: int = 0
    stored: int = 0
    changed: int = 0
    queued: int = 0
    by_verdict: dict[str, int] | None = None

    def as_dict(self) -> dict:
        return {
            "attempted": self.attempted, "stored": self.stored, "changed": self.changed,
            "queued_for_browser": self.queued, "by_verdict": self.by_verdict or {},
        }


async def crawl(
    conn: sqlite3.Connection,
    *,
    limit: int | None = None,
    refetch: bool = False,
    ids: Sequence[int] | None = None,
    settings: Settings | None = None,
    policy: FetchPolicy | None = None,
    client: httpx.AsyncClient | None = None,
    progress=None,
) -> CrawlReport:
    """Run channel A over the pending set and persist everything it learns."""
    targets = pending_targets(conn, limit=limit, refetch=refetch, ids=ids)
    if not targets:
        return CrawlReport(by_verdict={})

    pol = policy or policy_from_settings(settings)
    batch: BatchResult = await fetch_many(
        [t[1] for t in targets], policy=pol, client=client, on_result=progress
    )

    rep = CrawlReport(attempted=len(targets), by_verdict=batch.by_verdict())
    for (bid, _url, _title), res in zip(targets, batch.results, strict=True):
        out = save_result(conn, bid, res)
        rep.stored += int(out.stored)
        rep.changed += int(out.changed)
        rep.queued += int(out.queued_for_browser)
    conn.commit()
    return rep


def deferred_verdicts() -> Iterable[str]:
    return sorted(v.value for v in DEFER_TO_BROWSER)
