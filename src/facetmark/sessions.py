"""Facet 4, part one: reconstruct saving episodes from ``date_added``.

Why this facet exists
---------------------
What survives in a person's memory about a bookmark is often not its contents
but its *circumstances*: "that thing I found the evening I was picking a CRDT
library". Content-only indexes cannot answer that, because the circumstance is
not written on the page. The timestamp is the only trace of it we have.

Clustering, without a clustering library
----------------------------------------
With ``min_samples = 2`` and one dimension, DBSCAN degenerates to "cut wherever
the gap to the next point exceeds eps". That is three lines of ``numpy.diff``,
and it is exactly equivalent -- verified numerically against a reference
implementation. Pulling in scikit-learn for this would be dead weight.

Choosing eps
------------
The design document proposed reading eps off the valley of a log-histogram of
inter-arrival gaps, expecting 20-60 minutes. Measured on a real 1697-entry
library, there is no clean valley: the raw histogram minimum lands at 164
minutes, the same histogram smoothed with a width-5 window lands at 231, and
neither agrees with the other or with the design estimate. The method is not
robust, so this module does not use it.

Instead eps is chosen against an external label. Folder membership is the only
label a bookmark file gives away for free: if the episodes we cut really are
topical collection bursts, bookmarks inside one episode should land in the same
folder far more often than chance. Scanning eps and maximising
``coverage x purity_lift`` puts the optimum at 10-20 minutes on the calibration
library, with purity running 6-8x above a shuffled baseline.

That label is circular and this module says so out loud: bookmarks saved in one
sitting are *also* more likely to be filed together by hand, so some of the lift
is definitional. It is a heuristic calibration, not causal evidence. The lift
over shuffling is large enough (8.5x at 5 minutes) that the cut is finding
something real, and ``--eps`` always overrides.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

import numpy as np

#: eps values scanned by the calibrator, in seconds (5 min .. 4 h).
DEFAULT_EPS_GRID: tuple[int, ...] = (
    300, 600, 900, 1200, 1800, 2700, 3600, 5400, 7200, 10800, 14400,
)

#: Fallback when a library is too small or too label-poor to calibrate on.
FALLBACK_EPS = 1200  # 20 minutes: the calibration optimum.

#: A burst denser than this many saves inside one second is a file import,
#: not a person browsing. Measured: a real library peaks at 2 saves/second.
IMPORT_BURST_PER_SECOND = 50

#: Shuffles used to estimate the chance level of folder purity.
PURITY_SHUFFLES = 20


@dataclass(slots=True)
class SessionSplit:
    """One eps applied to one timeline."""

    eps: int
    #: For each input index, its session id, or ``-1`` for a singleton.
    labels: np.ndarray
    n_sessions: int
    coverage: float          # fraction of bookmarks in a session of size >= 2
    median_size: float


@dataclass(slots=True)
class EpsScanRow:
    eps: int
    n_sessions: int
    coverage: float
    median_size: float
    purity: float
    baseline: float
    lift: float
    objective: float


@dataclass(slots=True)
class Calibration:
    eps: int
    reason: str
    rows: list[EpsScanRow] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core split
# ---------------------------------------------------------------------------
def split_sessions(timestamps: Sequence[float], eps: float) -> SessionSplit:
    """Cut the timeline wherever the gap to the next save exceeds ``eps``.

    ``timestamps`` need not be sorted; labels come back aligned to the input
    order. Runs of length 1 get label ``-1``: a single bookmark is not an
    episode, and treating it as one would inflate every downstream statistic.
    """
    n = len(timestamps)
    if n == 0:
        return SessionSplit(int(eps), np.empty(0, dtype=np.int64), 0, 0.0, 0.0)

    ts = np.asarray(timestamps, dtype=np.float64)
    order = np.argsort(ts, kind="stable")
    gaps = np.diff(ts[order])
    # Cumulative count of "gap too big" is the run id, directly.
    run = np.concatenate(([0], np.cumsum(gaps > eps))).astype(np.int64)

    sizes = np.bincount(run)
    keep = sizes >= 2
    # Renumber surviving runs to a dense 0..k-1, singletons to -1.
    remap = np.full(sizes.shape, -1, dtype=np.int64)
    remap[keep] = np.arange(int(keep.sum()), dtype=np.int64)

    labels_sorted = remap[run]
    labels = np.empty(n, dtype=np.int64)
    labels[order] = labels_sorted

    k = int(keep.sum())
    covered = int((labels >= 0).sum())
    med = float(np.median(sizes[keep])) if k else 0.0
    return SessionSplit(int(eps), labels, k, covered / n, med)


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------
def folder_purity(labels: np.ndarray, folder_ids: np.ndarray) -> float:
    """Share of same-session pairs that also share a folder.

    Pair-counted rather than majority-voted so that one large mixed session
    cannot be scored as pure just because a plurality of it agrees.
    """
    same = tot = 0
    for lab in np.unique(labels[labels >= 0]):
        f = folder_ids[labels == lab]
        m = len(f)
        if m < 2:
            continue
        tot += m * (m - 1) // 2
        counts = np.bincount(f)
        same += int((counts * (counts - 1) // 2).sum())
    return same / tot if tot else 0.0


def _baseline_purity(labels: np.ndarray, folder_ids: np.ndarray, *, rng: np.random.Generator) -> float:
    """Purity when folder assignment is shuffled: the chance level."""
    vals = [
        folder_purity(labels, rng.permutation(folder_ids))
        for _ in range(PURITY_SHUFFLES)
    ]
    return float(np.mean(vals))


def calibrate_eps(
    timestamps: Sequence[float],
    folders: Sequence[str],
    *,
    grid: Iterable[int] = DEFAULT_EPS_GRID,
    seed: int = 0,
) -> Calibration:
    """Pick eps by maximising ``coverage x purity_lift`` over a grid.

    Neither factor works alone. Purity falls monotonically as eps grows, so
    optimising it drives eps to zero and nothing gets grouped. Coverage rises
    monotonically, so optimising it drives eps to infinity and everything is one
    session. The product is the trade-off, and ``lift`` rather than raw purity
    keeps a library whose folders happen to be lopsided from scoring well by
    accident.
    """
    n = len(timestamps)
    if n < 4:
        return Calibration(FALLBACK_EPS, "too few dated bookmarks to calibrate")

    codes = {f: i for i, f in enumerate(sorted(set(folders)))}
    folder_ids = np.array([codes[f] for f in folders], dtype=np.int64)
    rng = np.random.default_rng(seed)

    rows: list[EpsScanRow] = []
    for eps in grid:
        sp = split_sessions(timestamps, eps)
        if sp.n_sessions == 0:
            continue
        pur = folder_purity(sp.labels, folder_ids)
        base = _baseline_purity(sp.labels, folder_ids, rng=rng)
        lift = pur / base if base > 0 else 0.0
        rows.append(
            EpsScanRow(eps, sp.n_sessions, sp.coverage, sp.median_size,
                       pur, base, lift, sp.coverage * lift)
        )

    if not rows or all(r.objective <= 0 for r in rows):
        return Calibration(FALLBACK_EPS, "no usable folder signal; using default eps", rows)

    best = max(rows, key=lambda r: r.objective)
    return Calibration(
        best.eps,
        f"coverage {best.coverage:.1%} x purity lift {best.lift:.1f}x "
        f"(purity {best.purity:.1%} vs {best.baseline:.1%} shuffled)",
        rows,
    )


# ---------------------------------------------------------------------------
# Import artefacts
# ---------------------------------------------------------------------------
def detect_import_artifacts(
    timestamps: Sequence[float], *, per_second: int = IMPORT_BURST_PER_SECOND
) -> np.ndarray:
    """Flag bookmarks that arrived faster than a human can browse.

    Restoring a backup or migrating browsers stamps hundreds of bookmarks with
    the same second. Those timestamps record a file operation, not an episode,
    and feeding them to the splitter produces one enormous meaningless session
    that would dominate every context-facet result.

    Returns a boolean mask aligned to the input.
    """
    n = len(timestamps)
    if n == 0:
        return np.zeros(0, dtype=bool)
    ts = np.asarray(timestamps, dtype=np.float64)
    order = np.argsort(ts, kind="stable")
    s = ts[order]
    # For each i, how many saves fall in [t_i, t_i + 1)?
    right = np.searchsorted(s, s + 1.0, side="left")
    dense = (right - np.arange(n)) > per_second
    # Mark the whole burst, not just its leading edge.
    mask_sorted = np.zeros(n, dtype=bool)
    for i in np.flatnonzero(dense):
        mask_sorted[i : right[i]] = True
    out = np.zeros(n, dtype=bool)
    out[order] = mask_sorted
    return out


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class SessionBuildResult:
    eps: int
    reason: str
    n_sessions: int
    n_assigned: int
    n_import_artifact: int
    coverage: float
    scan: list[EpsScanRow] = field(default_factory=list)


def build_sessions(
    conn: sqlite3.Connection,
    *,
    eps: int | None = None,
    grid: Iterable[int] = DEFAULT_EPS_GRID,
    seed: int = 0,
) -> SessionBuildResult:
    """Recompute every session from scratch and persist it.

    Rebuild rather than incremental update: sessions are cheap to recompute
    (one sort over a few thousand integers) and a partial update after an import
    would leave stale boundaries in the middle of the timeline.
    """
    rows = conn.execute(
        "SELECT id, date_added, folder FROM bookmark"
        " WHERE date_added IS NOT NULL AND indexable = 1"
        " ORDER BY date_added, id"
    ).fetchall()
    if not rows:
        conn.execute("DELETE FROM session")
        conn.commit()
        return SessionBuildResult(FALLBACK_EPS, "no dated bookmarks", 0, 0, 0, 0.0)

    ids = [int(r["id"]) for r in rows]
    ts = [float(r["date_added"]) for r in rows]
    folders = [r["folder"] or "" for r in rows]

    artifact = detect_import_artifacts(ts)
    conn.execute("UPDATE bookmark SET import_artifact = 0")
    if artifact.any():
        conn.executemany(
            "UPDATE bookmark SET import_artifact = 1 WHERE id = ?",
            [(ids[i],) for i in np.flatnonzero(artifact)],
        )

    # Calibrate on the human-paced subset only; a burst would flatten the scan.
    live = ~artifact
    if eps is None:
        cal = calibrate_eps(
            [t for t, k in zip(ts, live, strict=True) if k],
            [f for f, k in zip(folders, live, strict=True) if k],
            grid=grid, seed=seed,
        )
        eps_used, reason, scan = cal.eps, cal.reason, cal.rows
    else:
        eps_used, reason, scan = int(eps), "eps supplied by caller", []

    sp = split_sessions([t for t, k in zip(ts, live, strict=True) if k], eps_used)
    live_ids = [i for i, k in zip(ids, live, strict=True) if k]
    live_ts = [t for t, k in zip(ts, live, strict=True) if k]

    # Import artefacts fall back to folder grouping: the file operation destroyed
    # the temporal signal, but whatever structure the file had is still there.
    groups: dict[tuple[str, int], list[tuple[int, float]]] = {}
    for bid, t, lab in zip(live_ids, live_ts, sp.labels, strict=True):
        if lab >= 0:
            groups.setdefault(("temporal", int(lab)), []).append((bid, t))
    art_idx = np.flatnonzero(artifact)
    if len(art_idx):
        by_folder: dict[str, list[tuple[int, float]]] = {}
        for i in art_idx:
            by_folder.setdefault(folders[i], []).append((ids[i], ts[i]))
        for j, (fol, members) in enumerate(sorted(by_folder.items())):
            if fol and len(members) >= 2:
                groups[("folder", j)] = members

    conn.execute("DELETE FROM session")  # cascades to bookmark_session
    assigned = 0
    for (method, _), members in sorted(groups.items(), key=lambda kv: min(m[1] for m in kv[1])):
        times = [t for _, t in members]
        cur = conn.execute(
            "INSERT INTO session(started_at, ended_at, size, method, eps_seconds)"
            " VALUES(?,?,?,?,?)",
            (int(min(times)), int(max(times)), len(members), method,
             eps_used if method == "temporal" else None),
        )
        sid = int(cur.lastrowid or 0)
        conn.executemany(
            "INSERT OR IGNORE INTO bookmark_session(bookmark_id, session_id) VALUES(?,?)",
            [(bid, sid) for bid, _ in members],
        )
        assigned += len(members)
    conn.commit()

    return SessionBuildResult(
        eps=eps_used,
        reason=reason,
        n_sessions=len(groups),
        n_assigned=assigned,
        n_import_artifact=int(artifact.sum()),
        coverage=assigned / len(ids),
        scan=scan,
    )
