"""Link health: three layers, one conclusion, no deletions.

    local probe  ->  public cross-validation  ->  optional user proxy
       (layer 1)          (layer 2)                   (layer 3)
                              |
                        synthesis + append-only history

The layer split exists because the local machine cannot answer the question the
user actually cares about. "Is this link dead?" and "can I reach this link?"
have identical symptoms from one socket -- timeout, reset, 403 -- and only one
of them justifies telling the user their bookmark rotted. So layer 1 reports
observations, layer 2 asks other observers, and only the synthesis step is
allowed to use the word ``gone``.

Two guarantees hold across the whole package:

* **Nothing is ever deleted or hidden.** The strongest consequence of a ``gone``
  verdict is a graveyard view and a Wayback link; the bookmark stays in the
  index and stays searchable.
* **``gone`` needs two high-confidence confirmations at least a week apart.**
  With the external layer disabled, confidence is capped below that bar, so a
  privacy-conscious local-only setup can never confirm a death at all -- it
  just says "unreachable" forever, which is the honest answer.

A side effect worth knowing about: the reader proxy in layer 2 returns the page
body when it succeeds. Pages that channel A could never reach get their text
recovered here as a by-product of being health-checked.
"""

from __future__ import annotations

import asyncio
import sqlite3
import time
from dataclasses import dataclass, field

import httpx

from ..config import Settings, get_settings
from ..fetch.client import FetchPolicy
from ..fetch.store import policy_from_settings, store_body
from .external import ExternalReport, gather_external
from .local import LocalProbe, probe_many, probe_one
from .store import (
    HealthState,
    due_for_check,
    first_failed_at,
    history,
    is_confirmed_gone,
    latest,
    record_check,
    retry_after_seconds,
    state_of,
    summary,
)
from .synth import HealthCheck, synthesize
from .verdicts import Evidence, LocalVerdict, Status

__all__ = [
    "CheckReport",
    "Evidence",
    "ExternalReport",
    "HealthCheck",
    "HealthState",
    "LocalProbe",
    "LocalVerdict",
    "Status",
    "check_bookmarks",
    "due_for_check",
    "first_failed_at",
    "gather_external",
    "history",
    "is_confirmed_gone",
    "latest",
    "probe_many",
    "probe_one",
    "record_check",
    "retry_after_seconds",
    "state_of",
    "summary",
    "synthesize",
]

#: How many layer-2 investigations run at once. Lower than the fetch
#: concurrency on purpose: each one fans out to three third parties, and
#: hammering archive.org on behalf of one person's bookmark file is rude.
EXTERNAL_CONCURRENCY = 6


@dataclass(slots=True)
class CheckReport:
    considered: int = 0
    probed: int = 0
    escalated: int = 0
    recovered_bodies: int = 0
    by_status: dict[str, int] = field(default_factory=dict)
    confirmed_gone: list[int] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "considered": self.considered,
            "probed": self.probed,
            "escalated": self.escalated,
            "recovered_bodies": self.recovered_bodies,
            "by_status": self.by_status,
            "confirmed_gone": self.confirmed_gone,
            "errors": self.errors,
        }


async def check_bookmarks(
    conn: sqlite3.Connection,
    *,
    ids: list[int] | None = None,
    limit: int = 200,
    settings: Settings | None = None,
    policy: FetchPolicy | None = None,
    client: httpx.AsyncClient | None = None,
    now_ts: int | None = None,
    save_recovered: bool = True,
) -> CheckReport:
    """Probe a batch of bookmarks and append one health row for each.

    ``save_recovered`` files reader-proxy text into ``content`` for bookmarks
    that have none. It is on by default because the alternative -- throwing
    away a body somebody already paid a round trip for -- is silly, but it is a
    write, so it is switchable.
    """
    st = settings or get_settings()
    pol = policy or policy_from_settings(st)
    now = int(time.time()) if now_ts is None else int(now_ts)
    rep = CheckReport()

    rows = due_for_check(conn, limit=limit, ids=ids, now_ts=now)
    rep.considered = len(rows)
    if not rows:
        return rep

    targets = [
        {
            "url": r["url"],
            "known_chars": int(r["known_chars"] or 0),
            "known_body": r["known_body"] or "",
            "known_hash": r["known_hash"] or "",
            "title_hint": r["title"] or "",
        }
        for r in rows
    ]

    owned = client is None
    cl = client or httpx.AsyncClient(
        timeout=pol.timeout_s, follow_redirects=True, max_redirects=pol.max_redirects
    )
    try:
        probes = await probe_many(
            targets, policy=pol, client=cl,
            soft_gone_ratio=st.health_soft_gone_length_ratio,
        )
        rep.probed = len(probes)

        gate = asyncio.Semaphore(EXTERNAL_CONCURRENCY)
        externals: list[ExternalReport | None] = [None] * len(probes)

        async def escalate(i: int, bookmark_id: int, probe: LocalProbe) -> None:
            async with gate:
                try:
                    externals[i] = await gather_external(
                        cl, probe.url, settings=st,
                        first_failed_ts=first_failed_at(conn, bookmark_id) or now,
                        now_ts=now,
                    )
                except Exception as exc:  # noqa: BLE001 - one bad host must not
                    # abort the batch; the check degrades to local-only.
                    rep.errors.append(f"{probe.url}: {type(exc).__name__}: {exc}"[:200])

        pending = [
            escalate(i, int(rows[i]["id"]), p)
            for i, p in enumerate(probes)
            if p.needs_external
        ]
        rep.escalated = len(pending)
        if pending:
            await asyncio.gather(*pending)
    finally:
        if owned:
            await cl.aclose()

    for i, probe in enumerate(probes):
        bid = int(rows[i]["id"])
        check = synthesize(probe, externals[i], now_ts=now)
        record_check(conn, bid, check)
        rep.by_status[check.status.value] = rep.by_status.get(check.status.value, 0) + 1
        if check.status is Status.GONE and is_confirmed_gone(
            conn, bid, confirm_days=st.health_gone_confirm_days
        ):
            rep.confirmed_gone.append(bid)
        if save_recovered and check.recovered_body and not (rows[i]["known_chars"] or 0):
            store_body(
                conn, bid, body=check.recovered_body,
                title=check.recovered_title, extractor="reader-proxy",
                channel="reader", final_url=probe.final_url or probe.url,
            )
            rep.recovered_bodies += 1

    rep.by_status = dict(sorted(rep.by_status.items(), key=lambda kv: -kv[1]))
    return rep
