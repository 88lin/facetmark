"""Vocabulary for link health: what one observation point saw, versus what the
system is willing to tell the user.

Two enums, deliberately. ``LocalVerdict`` records what *this machine* observed
on one probe. ``Status`` is the synthesised, user-facing conclusion. Collapsing
them into a single enum is exactly the mistake this whole layer exists to
prevent: a page that is merely unreachable *from here* getting filed as dead.
From the local socket, a page blocked by geography and a page deleted last year
are indistinguishable -- same timeout, same reset, same 403. Only a second
observation point can tell them apart, and only the synthesis step (which has
seen both) is allowed to name the outcome.

Confidence
----------
Every stored check carries a confidence, because the asymmetry matters: a
wrongly-declared ``gone`` costs the user a bookmark they will never know they
lost, while a wrongly-declared ``alive`` costs one line of noise. So the
numbers below are a floor-and-additive scheme, not a probability estimate, and
they are biased toward inaction:

* an explicit server statement (404/410) starts high, because the server is the
  authority on its own URL space;
* a local network failure starts low, because the local network is the least
  trustworthy observer in the system;
* external corroboration only ever *adds*;
* with the external layer switched off, confidence is capped at
  ``LOCAL_ONLY_CAP`` -- a local-only check can never reach the bar that
  confirming ``gone`` requires. That is the graceful degradation promised in
  the design: the probe still runs, it just cannot conclude anything final.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class LocalVerdict(str, Enum):
    """Layer-1 observation. Provisional by construction."""

    ALIVE = "alive"
    GONE = "gone"                            # 404 / 410: the server says so
    SOFT_GONE = "soft_gone"                  # 200 + placeholder + length collapse
    DRIFTED = "drifted"                      # 200 but the content moved on
    BLOCKED = "blocked_or_forbidden"         # 401 / 403 / 429 / 451
    DNS_FAIL = "dns_fail"                    # NXDOMAIN / SERVFAIL
    UNREACHABLE_LOCAL = "unreachable_local"  # timeout, reset, TLS, 5xx
    SKIPPED = "skipped"                      # not an http(s) URL


class Status(str, Enum):
    """Synthesised conclusion. These strings are the UI contract and are also
    what lands in ``health.verdict``; ``search.decay.DEAD_VERDICTS`` reads
    them, so the spellings are load-bearing."""

    ALIVE = "alive"
    GONE = "gone"
    SOFT_GONE = "soft_gone"
    DRIFTED = "drifted"
    RESTRICTED = "restricted"
    UNREACHABLE = "unreachable"
    UNKNOWN = "unknown"


#: Local verdicts worth escalating to the cross-validation layer. Anything that
#: came back 200 is not here: the page answered, so a second observation point
#: has nothing to add about whether it exists.
NEEDS_EXTERNAL: frozenset[LocalVerdict] = frozenset({
    LocalVerdict.GONE,
    LocalVerdict.BLOCKED,
    LocalVerdict.DNS_FAIL,
    LocalVerdict.UNREACHABLE_LOCAL,
})

BASE_CONFIDENCE: dict[Status, float] = {
    Status.ALIVE: 0.95,
    Status.GONE: 0.80,
    Status.SOFT_GONE: 0.60,
    Status.DRIFTED: 0.70,
    Status.RESTRICTED: 0.50,
    Status.UNREACHABLE: 0.40,
    Status.UNKNOWN: 0.10,
}

#: Corroboration bonuses. Reader-proxy success is the strongest because it is a
#: direct positive: something, somewhere, rendered the page today.
BONUS_READER_OK = 0.30
BONUS_PROXY_OK = 0.25
BONUS_RESOLVER_DIVERGENCE = 0.25
BONUS_SNAPSHOT_AFTER_FAILURE = 0.15
BONUS_RESOLVERS_AGREE_NXDOMAIN = 0.10

#: Bar a ``gone`` check must clear to count as one of the two confirmations.
HIGH_CONFIDENCE = 0.75

#: Ceiling when the external layer did not run (disabled, or the host is on the
#: privacy exclusion list). Deliberately below HIGH_CONFIDENCE.
LOCAL_ONLY_CAP = 0.60

#: Below this vocabulary overlap, a 200 counts as ``drifted``. Set low on
#: purpose: ``drifted`` feeds the metabolism layer, so a false positive
#: demotes a live page, while a false negative costs nothing but a stale
#: summary the user can refresh.
DRIFT_SIMILARITY = 0.60

#: Placeholder phrasing for soft-404 detection. Never sufficient alone -- a
#: page legitimately about HTTP 404 would match. Requires the length collapse
#: as well.
SOFT_404_PATTERNS: tuple[str, ...] = (
    "404",
    "not found",
    "no longer available",
    "no longer exists",
    "page doesn't exist",
    "page does not exist",
    "has been removed",
    "content unavailable",
    "this page isn't available",
    "页面不存在",
    "页面已删除",
    "内容不存在",
    "内容已删除",
    "文章不存在",
    "笔记不存在",
    "已被删除",
    "找不到该页面",
    "无法访问",
    "ページが見つかりません",
)


def placeholder_hit(title: str, body: str, *, scan_chars: int = 500) -> str:
    """Return the first soft-404 pattern found in the title or the head of the
    body, or ``""``. Only the head is scanned: a real article can mention "not
    found" three screens down, a placeholder page says it immediately."""
    hay = f"{title or ''}\n{(body or '')[:scan_chars]}".lower()
    for pat in SOFT_404_PATTERNS:
        if pat in hay:
            return pat
    return ""


@dataclass(frozen=True, slots=True)
class Evidence:
    """One observation, from one layer. Stored verbatim so a user can see why
    the system said what it said."""

    layer: str            # local | doh | wayback | reader | proxy | policy
    signal: str
    detail: str = ""
    at: int = field(default_factory=lambda: int(time.time()))

    def as_dict(self) -> dict:
        return {"layer": self.layer, "signal": self.signal,
                "detail": self.detail, "at": self.at}


def clamp(x: float) -> float:
    return max(0.0, min(1.0, round(x, 3)))
