"""Facet 4: the contextual facet -- a weight, not a ranker.

This is the deliberate asymmetry in the design. Facets 1-3 each produce a
ranked list and vote through RRF. Facet 4 does not, and cannot: "saved in the
same sitting" is not an ordering over the whole library, it is a property of a
*pair*. Asked to rank the library on its own it would return either everything
or nothing.

Worse, if it did vote, the vote would be circular. The contextual signal is
computed from the anchors, and the anchors come from facets 1 and 3. Feeding it
back into the fusion would let facet 1 vote twice under a different name and
quietly double the weight of whatever the content vector already liked.

So it is applied *after* fusion, as a bounded multiplier.

anchor-then-window
------------------
The hard case is ``配 Docker 那阵子存的东西``. There is no date in that query --
only a topic and the claim that a date exists. Two passes:

1. Retrieve on the topic alone. Those hits are the anchors.
2. Take the P10-P90 span of the anchors' ``date_added``. That is the window.

P10-P90 rather than min-max because one stray anchor from three years ago
would otherwise stretch the window across the whole library and make it
meaningless. Trimming 20% costs a little recall at the edges and buys a window
that is actually a window.

Session and folder co-membership are the same idea with an exact key instead of
a fuzzy one, so they need no trimming.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass, field

#: Contribution ceilings. The report fixes the time-window boost range at
#: 1.0-1.5; session and folder ride on top of it, and the total is clamped so
#: no amount of contextual agreement can outweigh being three facets' top hit.
W_WINDOW = 0.50
W_SESSION = 0.25
W_FOLDER = 0.15
MAX_BOOST = 1.60

#: How many fused hits are treated as anchors. Small on purpose: an anchor set
#: that reaches into the mediocre tail produces a window centred on noise.
DEFAULT_ANCHORS = 10

#: A folder holding more than this is a filing cabinet, not a context. On the
#: calibration library the median folder holds 8 bookmarks and the largest
#: holds well over a hundred; boosting everything in the latter says nothing.
MAX_FOLDER_FANOUT = 40


def percentile(sorted_values: Sequence[float], q: float) -> float:
    """Linear-interpolated percentile over an already-sorted sequence."""
    if not sorted_values:
        raise ValueError("empty sequence")
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    pos = (len(sorted_values) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = pos - lo
    return float(sorted_values[lo]) * (1 - frac) + float(sorted_values[hi]) * frac


def anchor_window(
    timestamps: Sequence[int], *, low: float = 0.10, high: float = 0.90
) -> tuple[int, int] | None:
    """P10-P90 span of the anchors' save times."""
    ts = sorted(int(t) for t in timestamps if t)
    if len(ts) < 2:
        return None
    a = int(percentile(ts, low))
    b = int(percentile(ts, high))
    if b < a:
        a, b = b, a
    if a == b:                      # every anchor saved in the same instant
        return (a - 1800, b + 1800)
    return (a, b)


def _anchor_strength(rank: int) -> float:
    """1.0 for the top anchor, decaying gently. rank is 1-based."""
    return 1.0 / (1.0 + 0.2 * max(rank - 1, 0))


@dataclass(slots=True)
class ContextSignals:
    window: tuple[int, int] | None = None
    #: ``query`` (a date was in the query) | ``anchor`` (derived from hits) | ``none``
    window_source: str = "none"
    anchor_ids: list[int] = field(default_factory=list)
    in_window: set[int] = field(default_factory=set)
    session_peers: dict[int, float] = field(default_factory=dict)
    folder_peers: dict[int, float] = field(default_factory=dict)
    episodic_confidence: float = 0.0

    def boost(self, bookmark_id: int) -> float:
        """Bounded multiplier applied to the fused score."""
        m = 1.0
        if bookmark_id in self.in_window:
            m += W_WINDOW * max(self.episodic_confidence, 0.0)
        s = self.session_peers.get(bookmark_id)
        if s:
            m += W_SESSION * s
        f = self.folder_peers.get(bookmark_id)
        if f:
            m += W_FOLDER * f
        return min(m, MAX_BOOST)

    def reasons(self, bookmark_id: int) -> list[str]:
        """Human-readable explanation of a boost, for the UI and for MCP."""
        out: list[str] = []
        if bookmark_id in self.in_window:
            out.append("saved in the same period")
        if self.session_peers.get(bookmark_id):
            out.append("saved in the same sitting")
        if self.folder_peers.get(bookmark_id):
            out.append("filed alongside a match")
        return out

    def as_dict(self) -> dict:
        return {
            "window": list(self.window) if self.window else None,
            "window_source": self.window_source,
            "anchors": list(self.anchor_ids),
            "in_window": len(self.in_window),
            "session_peers": len(self.session_peers),
            "folder_peers": len(self.folder_peers),
        }


def _fetch_dates(conn: sqlite3.Connection, ids: Sequence[int]) -> dict[int, int]:
    if not ids:
        return {}
    rows = conn.execute(
        f"SELECT id, date_added FROM bookmark WHERE id IN ({','.join('?' * len(ids))})",
        list(ids),
    ).fetchall()
    return {int(r["id"]): int(r["date_added"]) for r in rows if r["date_added"]}


def _session_peers(
    conn: sqlite3.Connection, anchors: Sequence[tuple[int, float]], candidates: set[int]
) -> dict[int, float]:
    if not anchors or not candidates:
        return {}
    ids = [a for a, _ in anchors]
    strength = dict(anchors)
    rows = conn.execute(
        "SELECT peer.bookmark_id AS peer_id, own.bookmark_id AS anchor_id "
        "FROM bookmark_session own "
        "JOIN bookmark_session peer ON peer.session_id = own.session_id "
        f"WHERE own.bookmark_id IN ({','.join('?' * len(ids))})",
        ids,
    ).fetchall()
    out: dict[int, float] = {}
    for r in rows:
        peer = int(r["peer_id"])
        if peer not in candidates:
            continue
        w = strength.get(int(r["anchor_id"]), 0.0)
        if w > out.get(peer, 0.0):
            out[peer] = w
    return out


def _folder_peers(
    conn: sqlite3.Connection, anchors: Sequence[tuple[int, float]], candidates: set[int]
) -> dict[int, float]:
    if not anchors or not candidates:
        return {}
    ids = [a for a, _ in anchors]
    strength = dict(anchors)
    rows = conn.execute(
        f"SELECT id, folder FROM bookmark WHERE id IN ({','.join('?' * len(ids))}) AND folder <> ''",
        ids,
    ).fetchall()
    if not rows:
        return {}
    # Folder is an opaque display path -- never split it on '/'. 6 folder names
    # in the calibration library contain a literal '/', and splitting them
    # merges 110 bookmarks into folders that do not exist.
    by_folder: dict[str, float] = {}
    for r in rows:
        f = str(r["folder"])
        w = strength.get(int(r["id"]), 0.0)
        if w > by_folder.get(f, 0.0):
            by_folder[f] = w
    folders = list(by_folder)
    sizes = {
        str(r["folder"]): int(r["n"])
        for r in conn.execute(
            "SELECT folder, count(*) AS n FROM bookmark "
            f"WHERE folder IN ({','.join('?' * len(folders))}) GROUP BY folder",
            folders,
        )
    }
    usable = [f for f in folders if sizes.get(f, 0) <= MAX_FOLDER_FANOUT]
    if not usable:
        return {}
    members = conn.execute(
        "SELECT id, folder FROM bookmark "
        f"WHERE folder IN ({','.join('?' * len(usable))})",
        usable,
    ).fetchall()
    out: dict[int, float] = {}
    for r in members:
        bid = int(r["id"])
        if bid not in candidates:
            continue
        w = by_folder.get(str(r["folder"]), 0.0)
        if w > out.get(bid, 0.0):
            out[bid] = w
    return out


def build_context(
    conn: sqlite3.Connection,
    *,
    anchors: Sequence[int],
    candidates: Sequence[int],
    query_window: tuple[int, int] | None = None,
    episodic_confidence: float = 0.0,
    max_anchors: int = DEFAULT_ANCHORS,
) -> ContextSignals:
    """Assemble the contextual weights for one query.

    ``anchors`` are the top fused hits, best first. ``candidates`` is the set
    the boost will actually be applied to -- scoring only those keeps this O(n
    of the result page) instead of O(library).
    """
    sig = ContextSignals(episodic_confidence=episodic_confidence)
    anchor_ids = [int(a) for a in anchors[:max_anchors]]
    sig.anchor_ids = anchor_ids
    cand = {int(c) for c in candidates}
    if not cand:
        return sig

    weighted = [(bid, _anchor_strength(i)) for i, bid in enumerate(anchor_ids, start=1)]

    if query_window is not None:
        sig.window = query_window
        sig.window_source = "query"
    elif episodic_confidence > 0.0 and anchor_ids:
        dates = _fetch_dates(conn, anchor_ids)
        win = anchor_window([dates[b] for b in anchor_ids if b in dates])
        if win is not None:
            sig.window = win
            sig.window_source = "anchor"

    if sig.window is not None:
        lo, hi = sig.window
        rows = conn.execute(
            f"SELECT id FROM bookmark WHERE id IN ({','.join('?' * len(cand))}) "
            "AND date_added IS NOT NULL AND date_added BETWEEN ? AND ?",
            [*cand, lo, hi],
        ).fetchall()
        sig.in_window = {int(r["id"]) for r in rows}

    sig.session_peers = _session_peers(conn, weighted, cand)
    sig.folder_peers = _folder_peers(conn, weighted, cand)
    return sig


def window_filter(conn: sqlite3.Connection, window: tuple[int, int]) -> list[int]:
    """Every bookmark saved inside a window, newest first.

    Used when the query is *only* episodic ("上个月存的") and there is no topic
    to anchor on -- then the window is the entire query.
    """
    lo, hi = window
    return [
        int(r["id"])
        for r in conn.execute(
            "SELECT id FROM bookmark WHERE date_added BETWEEN ? AND ? "
            "AND indexable=1 ORDER BY date_added DESC",
            (lo, hi),
        )
    ]
