"""Bookmark timestamp unit detection.

This module exists because of a bug the design doc would have shipped. The doc
specified exactly one conversion, WebKit microseconds::

    unix = webkit_us / 1e6 - 11644473600

That is correct for Chrome's JSON ``Bookmarks`` file. It is wrong for the
Netscape HTML export every browser produces from "Export bookmarks", which
stores **plain Unix seconds**. Applying the WebKit formula to a real 1697-entry
export collapsed the entire library onto 1601-01-01, i.e. every episodic signal
would have been destroyed silently -- no exception, no empty result, just
uniformly garbage timestamps.

So the unit is detected, never assumed.
"""

from __future__ import annotations

import time
from collections.abc import Iterable, Sequence

#: Seconds between 1601-01-01 (WebKit/Windows FILETIME epoch) and 1970-01-01.
WEBKIT_EPOCH_OFFSET = 11_644_473_600

#: 1990-01-01. Nothing older than this is a plausible bookmark timestamp.
PLAUSIBLE_LO = 631_152_000

UNITS: tuple[tuple[str, float, float], ...] = (
    # (name, divisor, epoch offset in seconds)
    ("unix_s", 1.0, 0.0),
    ("unix_ms", 1e3, 0.0),
    ("unix_us", 1e6, 0.0),
    ("webkit_us", 1e6, float(WEBKIT_EPOCH_OFFSET)),
)


def _plausible_hi() -> float:
    # Allow a year of slack: exports carry "now", and clocks drift.
    return time.time() + 400 * 86400


def convert(raw: float, unit: str) -> int | None:
    for name, div, off in UNITS:
        if name == unit:
            return int(raw / div - off)
    raise ValueError(f"unknown timestamp unit {unit!r}")


def is_plausible(ts: float) -> bool:
    return PLAUSIBLE_LO <= ts <= _plausible_hi()


def classify_one(raw: float) -> str | None:
    """Return the first unit under which ``raw`` lands in a plausible window."""
    if raw <= 0:
        return None
    for name, div, off in UNITS:
        if is_plausible(raw / div - off):
            return name
    return None


def detect_unit(values: Iterable[float]) -> str | None:
    """Detect the unit for a whole file by majority vote.

    Voting across all values rather than deciding per value keeps one corrupt
    entry from flipping the interpretation of the entire library.
    """
    vals = [v for v in values if v and v > 0]
    if not vals:
        return None
    votes: dict[str, int] = {}
    for v in vals:
        u = classify_one(v)
        if u:
            votes[u] = votes.get(u, 0) + 1
    if not votes:
        return None
    return max(votes.items(), key=lambda kv: kv[1])[0]


def convert_all(values: Sequence[float | None]) -> tuple[list[int | None], str | None]:
    """Convert a whole column, using the majority unit with a per-value fallback.

    Returns ``(converted, unit)``. Values that are implausible under the majority
    unit get a second chance under their own best-fit unit; if that also fails
    they become ``None``, because a wrong date is worse than a missing one -- a
    missing date merely excludes the bookmark from the episodic facet, while a
    wrong one silently corrupts a session.
    """
    unit = detect_unit(v for v in values if v is not None)
    if unit is None:
        return [None] * len(values), None
    out: list[int | None] = []
    for v in values:
        if v is None or v <= 0:
            out.append(None)
            continue
        ts = convert(v, unit)
        if ts is not None and is_plausible(ts):
            out.append(ts)
            continue
        alt = classify_one(v)
        out.append(convert(v, alt) if alt else None)
    return out, unit
