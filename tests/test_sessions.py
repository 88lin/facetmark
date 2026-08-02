"""Facet 4 part one: temporal session reconstruction.

The load-bearing claims tested here are (a) the three-line numpy split really is
DBSCAN with min_samples=2, and (b) the eps calibrator recovers a planted
structure instead of just reporting whatever the objective's endpoints are.
"""

from __future__ import annotations

import numpy as np
import pytest

from facetmark.db import open_db
from facetmark.importers import import_bookmarks
from facetmark.sessions import (
    DEFAULT_EPS_GRID,
    FALLBACK_EPS,
    build_sessions,
    calibrate_eps,
    detect_import_artifacts,
    folder_purity,
    split_sessions,
)


def _reference_dbscan_1d(ts, eps):
    """Independent implementation: region query + expansion, as DBSCAN defines it.

    Deliberately written the slow, literal way so it shares no code with the
    thing it is checking.
    """
    ts = list(ts)
    n = len(ts)
    neigh = [[j for j in range(n) if abs(ts[i] - ts[j]) <= eps] for i in range(n)]
    labels = [None] * n
    cid = 0
    for i in range(n):
        if labels[i] is not None or len(neigh[i]) < 2:  # min_samples=2 incl. self
            continue
        labels[i] = cid
        queue = [x for x in neigh[i] if x != i]
        while queue:
            j = queue.pop(0)
            if labels[j] is not None:
                continue
            labels[j] = cid
            if len(neigh[j]) >= 2:
                queue.extend(x for x in neigh[j] if labels[x] is None)
        cid += 1
    return [-1 if x is None else x for x in labels]


def _canonical(labels):
    """Compare partitions, not label numbering."""
    groups = {}
    for i, lab in enumerate(labels):
        if lab != -1:
            groups.setdefault(lab, []).append(i)
    return sorted(tuple(v) for v in groups.values())


class TestSplitIsDbscanWithoutSklearn:
    @pytest.mark.parametrize("eps", [60, 300, 1800, 7200])
    def test_matches_reference_on_random_timelines(self, eps):
        rng = np.random.default_rng(7)
        for _ in range(25):
            n = int(rng.integers(2, 60))
            ts = np.cumsum(rng.exponential(900, n)).tolist()
            assert _canonical(split_sessions(ts, eps).labels) == _canonical(
                _reference_dbscan_1d(ts, eps)
            )

    def test_matches_reference_on_ties_and_duplicates(self):
        ts = [0, 0, 0, 5, 5, 10_000, 10_000, 10_001, 90_000]
        for eps in (0, 1, 10, 5000):
            assert _canonical(split_sessions(ts, eps).labels) == _canonical(
                _reference_dbscan_1d(ts, eps)
            )


class TestSplitBehaviour:
    def test_gap_larger_than_eps_cuts(self):
        sp = split_sessions([0, 10, 20, 5000, 5010], 100)
        assert sp.n_sessions == 2
        assert sp.labels.tolist() == [0, 0, 0, 1, 1]

    def test_lone_bookmark_is_not_an_episode(self):
        sp = split_sessions([0, 10, 99_999], 100)
        assert sp.labels.tolist() == [0, 0, -1]
        assert sp.n_sessions == 1
        assert sp.coverage == pytest.approx(2 / 3)

    def test_input_order_is_preserved_in_the_output(self):
        shuffled = [5000, 0, 5010, 10]
        labels = split_sessions(shuffled, 100).labels
        assert labels[0] == labels[2]  # the two late ones
        assert labels[1] == labels[3]  # the two early ones
        assert labels[0] != labels[1]

    def test_empty_input(self):
        sp = split_sessions([], 100)
        assert sp.n_sessions == 0 and sp.coverage == 0.0


class TestFolderPurity:
    def test_perfectly_aligned_sessions_score_one(self):
        labels = np.array([0, 0, 1, 1])
        folders = np.array([3, 3, 7, 7])
        assert folder_purity(labels, folders) == 1.0

    def test_singletons_contribute_no_pairs(self):
        assert folder_purity(np.array([-1, -1, -1]), np.array([1, 2, 3])) == 0.0

    def test_pair_counted_not_majority_voted(self):
        # 3 of 4 agree. Majority vote would call this pure; pair counting gives
        # 3 same-folder pairs out of 6.
        labels = np.array([0, 0, 0, 0])
        assert folder_purity(labels, np.array([1, 1, 1, 2])) == pytest.approx(0.5)


class TestEpsCalibration:
    @staticmethod
    def _planted(true_eps=600, n_bursts=40, per_burst=4, seed=1):
        """Bursts of same-folder saves, separated by long idle gaps."""
        rng = np.random.default_rng(seed)
        ts, folders, t = [], [], 0.0
        for b in range(n_bursts):
            t += rng.uniform(6 * 3600, 48 * 3600)  # idle gap, far above true_eps
            for _ in range(per_burst):
                ts.append(t)
                folders.append(f"topic-{b % 9}")
                t += rng.uniform(30, true_eps * 0.4)
        return ts, folders

    def test_recovers_a_planted_burst_structure(self):
        ts, folders = self._planted()
        cal = calibrate_eps(ts, folders)
        # The chosen eps must separate bursts (< the 6 h minimum idle gap) while
        # still joining within-burst saves (> the ~240 s intra-burst spacing).
        assert 300 <= cal.eps <= 10800
        sp = split_sessions(ts, cal.eps)
        assert sp.n_sessions == 40
        assert folder_purity(
            sp.labels, np.array([hash(f) % 1000 for f in folders])
        ) == pytest.approx(1.0)

    def test_objective_is_interior_not_an_endpoint(self):
        """Coverage alone would pick the largest eps, purity alone the smallest."""
        ts, folders = self._planted()
        cal = calibrate_eps(ts, folders)
        by_eps = {r.eps: r for r in cal.rows}
        assert by_eps[max(by_eps)].coverage >= by_eps[min(by_eps)].coverage
        assert by_eps[max(by_eps)].purity <= by_eps[min(by_eps)].purity
        assert cal.eps not in (min(by_eps), max(by_eps))

    def test_no_folder_signal_falls_back_instead_of_picking_noise(self):
        rng = np.random.default_rng(3)
        ts = np.cumsum(rng.exponential(900, 300)).tolist()
        folders = ["same"] * 300  # zero discriminative power: lift == 1 everywhere
        cal = calibrate_eps(ts, folders)
        assert cal.eps in DEFAULT_EPS_GRID or cal.eps == FALLBACK_EPS

    def test_tiny_library_falls_back(self):
        cal = calibrate_eps([1, 2], ["a", "b"])
        assert cal.eps == FALLBACK_EPS and "too few" in cal.reason

    def test_scan_is_deterministic(self):
        ts, folders = self._planted()
        a = calibrate_eps(ts, folders, seed=42)
        b = calibrate_eps(ts, folders, seed=42)
        assert a.eps == b.eps
        assert [r.objective for r in a.rows] == [r.objective for r in b.rows]


class TestImportArtifactDetection:
    def test_a_restore_burst_is_flagged_whole(self):
        ts = [1000.0] * 200 + [50_000.0, 60_000.0]
        mask = detect_import_artifacts(ts)
        assert mask[:200].all() and not mask[200:].any()

    def test_human_paced_saving_is_not_flagged(self):
        # Two saves in the same second is normal; the real calibration library
        # never exceeded that.
        ts = [float(i // 2) * 60 for i in range(400)]
        assert not detect_import_artifacts(ts).any()

    def test_burst_spread_over_a_second_still_counts(self):
        ts = list(np.linspace(0, 0.99, 120)) + [10_000.0]
        mask = detect_import_artifacts(ts)
        assert mask[:120].all() and not mask[120]


class TestPersistence:
    HTML = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<DL><p>
    <DT><H3>a</H3>
    <DL><p>
        <DT><A HREF="https://e.com/1" ADD_DATE="1700000000">one</A>
        <DT><A HREF="https://e.com/2" ADD_DATE="1700000120">two</A>
        <DT><A HREF="https://e.com/3" ADD_DATE="1700000240">three</A>
    </DL><p>
    <DT><H3>b</H3>
    <DL><p>
        <DT><A HREF="https://e.com/4" ADD_DATE="1700900000">four</A>
        <DT><A HREF="https://e.com/5" ADD_DATE="1700900100">five</A>
    </DL><p>
    <DT><A HREF="https://e.com/6" ADD_DATE="1800000000">loner</A>
</DL><p>
"""

    @pytest.fixture()
    def db(self):
        c = open_db(":memory:")
        import_bookmarks(c, content=self.HTML)
        yield c
        c.close()

    def test_two_episodes_and_one_loner(self, db):
        r = build_sessions(db, eps=1800)
        assert r.n_sessions == 2 and r.n_assigned == 5
        sizes = [x[0] for x in db.execute("SELECT size FROM session ORDER BY size").fetchall()]
        assert sizes == [2, 3]

    def test_rebuild_is_idempotent(self, db):
        build_sessions(db, eps=1800)
        first = db.execute("SELECT count(*) FROM bookmark_session").fetchone()[0]
        build_sessions(db, eps=1800)
        assert db.execute("SELECT count(*) FROM session").fetchone()[0] == 2
        assert db.execute("SELECT count(*) FROM bookmark_session").fetchone()[0] == first

    def test_deleting_a_session_cascades(self, db):
        build_sessions(db, eps=1800)
        db.execute("DELETE FROM session WHERE id=(SELECT min(id) FROM session)")
        assert db.execute("SELECT count(*) FROM bookmark_session").fetchone()[0] == 2

    def test_session_bounds_come_from_members(self, db):
        build_sessions(db, eps=1800)
        row = db.execute(
            "SELECT started_at, ended_at, method, eps_seconds FROM session ORDER BY started_at"
        ).fetchone()
        assert row["started_at"] == 1700000000
        assert row["ended_at"] == 1700000240
        assert row["method"] == "temporal" and row["eps_seconds"] == 1800

    def test_import_artifacts_fall_back_to_folder_grouping(self):
        c = open_db(":memory:")
        rows = "".join(
            f'<DT><A HREF="https://e.com/{i}" ADD_DATE="1700000000">t{i}</A>\n'
            for i in range(120)
        )
        import_bookmarks(
            c,
            content=f'<!DOCTYPE NETSCAPE-Bookmark-file-1>\n<DL><p>\n<DT><H3>bulk</H3>\n'
            f"<DL><p>\n{rows}</DL><p>\n</DL><p>\n",
        )
        r = build_sessions(c)
        assert r.n_import_artifact == 120
        assert c.execute("SELECT count(*) FROM bookmark WHERE import_artifact=1").fetchone()[0] == 120
        methods = {x[0] for x in c.execute("SELECT DISTINCT method FROM session").fetchall()}
        assert methods == {"folder"}
        c.close()

    def test_empty_library(self):
        c = open_db(":memory:")
        r = build_sessions(c)
        assert r.n_sessions == 0 and r.coverage == 0.0
        c.close()
