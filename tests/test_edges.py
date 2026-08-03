"""The typed relation graph.

The properties worth defending: hub domains must not explode into thousands of
meaningless edges, supersession must stay directed and must not fire on
same-sitting duplicates, and semantic edges must be mutual so dense regions do
not become attractors.
"""

from __future__ import annotations

import numpy as np
import pytest

from facetmark.db import ensure_vec_tables, open_db, upsert_content_vector
from facetmark.edges import (
    MAX_DOMAIN_FANOUT,
    WEIGHTS,
    build_anchor_sibling_edges,
    build_edges,
    build_same_domain_edges,
    build_semantic_edges,
    build_session_edges,
    build_supersession_edges,
    neighbours,
)
from facetmark.importers import import_bookmarks
from facetmark.sessions import build_sessions


def _html(entries: str) -> str:
    return f"<!DOCTYPE NETSCAPE-Bookmark-file-1>\n<DL><p>\n{entries}</DL><p>\n"


def _a(url: str, title: str, date: int) -> str:
    return f'    <DT><A HREF="{url}" ADD_DATE="{date}">{title}</A>\n'


@pytest.fixture()
def db():
    c = open_db(":memory:")
    yield c
    c.close()


def _load(conn, entries: str):
    import_bookmarks(conn, content=_html(entries))
    return {r["url"]: int(r["id"]) for r in conn.execute("SELECT id, url FROM bookmark")}


class TestSessionEdges:
    def test_members_of_one_episode_are_connected_both_ways(self, db):
        ids = _load(db, _a("https://a.com/1", "x", 1700000000)
                       + _a("https://b.com/2", "y", 1700000060)
                       + _a("https://c.com/3", "z", 1700000120))
        build_sessions(db, eps=1800)
        build_session_edges(db)
        a, b = ids["https://a.com/1"], ids["https://b.com/2"]
        assert db.execute(
            "SELECT count(*) FROM edge WHERE kind='session' AND src=? AND dst=?", (a, b)
        ).fetchone()[0] == 1
        assert db.execute(
            "SELECT count(*) FROM edge WHERE kind='session' AND src=? AND dst=?", (b, a)
        ).fetchone()[0] == 1

    def test_smaller_episodes_weigh_more(self, db):
        small = _a("https://a.com/1", "x", 1700000000) + _a("https://b.com/2", "y", 1700000060)
        big = "".join(_a(f"https://h{i}.com/", f"t{i}", 1800000000 + i * 60) for i in range(10))
        _load(db, small + big)
        build_sessions(db, eps=1800)
        build_session_edges(db)
        weights = sorted({r[0] for r in db.execute(
            "SELECT DISTINCT weight FROM edge WHERE kind='session'")})
        assert len(weights) == 2 and weights[0] < weights[1]
        assert weights[1] == pytest.approx(WEIGHTS["session"])

    def test_oversized_episode_is_skipped_entirely(self, db):
        # 40 saves one minute apart: a binge, not a sitting. 780 pairs of noise.
        _load(db, "".join(_a(f"https://h{i}.com/", f"t{i}", 1700000000 + i * 60)
                          for i in range(40)))
        build_sessions(db, eps=1800)
        assert build_session_edges(db) == 0

    def test_no_self_edges(self, db):
        _load(db, _a("https://a.com/1", "x", 1700000000) + _a("https://b.com/2", "y", 1700000060))
        build_sessions(db, eps=1800)
        build_session_edges(db)
        assert db.execute("SELECT count(*) FROM edge WHERE src = dst").fetchone()[0] == 0


class TestSameDomainEdges:
    def test_two_pages_on_one_small_domain_connect(self, db):
        _load(db, _a("https://blog.example.org/a", "a", 1700000000)
                  + _a("https://blog.example.org/b", "b", 1800000000))
        assert build_same_domain_edges(db) == 2  # one pair, both directions

    def test_a_hub_domain_produces_nothing(self, db):
        """Measured: 78 github.com bookmarks would mean 3003 uninformative edges."""
        n = MAX_DOMAIN_FANOUT + 5
        _load(db, "".join(_a(f"https://github.com/o/r{i}", f"r{i}", 1700000000 + i)
                          for i in range(n)))
        assert build_same_domain_edges(db) == 0

    def test_weight_is_the_lowest_of_all_kinds(self):
        assert WEIGHTS["same_domain"] == min(WEIGHTS.values())

    def test_subdomains_of_one_site_share_a_domain(self, db):
        _load(db, _a("https://a.example.org/x", "x", 1700000000)
                  + _a("https://b.example.org/y", "y", 1800000000))
        assert build_same_domain_edges(db) == 2


class TestAnchorSiblingEdges:
    def test_two_fragments_of_one_page_connect(self, db):
        # Only on hosts where the fragment is known to address real content.
        _load(db, _a("https://docs.python.org/3/library/asyncio.html#task", "task", 1700000000)
                  + _a("https://docs.python.org/3/library/asyncio.html#queue", "queue", 1800000000))
        assert build_anchor_sibling_edges(db) == 2

    def test_elsewhere_the_fragments_never_reach_the_graph(self, db):
        """On an ordinary host the fragment is dropped, so the two URLs are one
        bookmark by the time the graph is built. Normalisation already answered
        the question; there is nothing left to relate."""
        ids = _load(db, _a("https://blog.example.org/guide#install", "install", 1700000000)
                        + _a("https://blog.example.org/guide#config", "config", 1800000000))
        assert len(ids) == 1
        assert build_anchor_sibling_edges(db) == 0

    def test_two_files_in_one_repo_connect(self, db):
        _load(db, _a("https://github.com/o/r/blob/main/a.py", "a", 1700000000)
                  + _a("https://github.com/o/r/issues/12", "issue", 1800000000))
        assert build_anchor_sibling_edges(db) == 2

    def test_different_repos_on_the_same_forge_do_not(self, db):
        _load(db, _a("https://github.com/o/r1", "r1", 1700000000)
                  + _a("https://github.com/o/r2", "r2", 1800000000))
        assert build_anchor_sibling_edges(db) == 0

    def test_fragmentless_pages_on_one_site_do_not(self, db):
        _load(db, _a("https://docs.example.org/a", "a", 1700000000)
                  + _a("https://docs.example.org/b", "b", 1800000000))
        assert build_anchor_sibling_edges(db) == 0


class TestSupersessionEdges:
    OLD, NEW = 1700000000, 1700000000 + 400 * 86400

    def test_direction_is_older_to_newer(self, db):
        ids = _load(db, _a("https://d.example/v1", "Rust 异步编程 完全指南", self.OLD)
                        + _a("https://d.example/v2", "Rust 异步编程 完全指南", self.NEW))
        rows = db.execute("SELECT src, dst FROM edge WHERE kind='supersession'").fetchall()
        build_supersession_edges(db)
        rows = db.execute("SELECT src, dst FROM edge WHERE kind='supersession'").fetchall()
        assert len(rows) == 1
        assert (int(rows[0][0]), int(rows[0][1])) == (ids["https://d.example/v1"],
                                                      ids["https://d.example/v2"])

    def test_what_replaced_this_is_one_lookup(self, db):
        ids = _load(db, _a("https://d.example/v1", "Rust 异步编程 完全指南", self.OLD)
                        + _a("https://d.example/v2", "Rust 异步编程 完全指南", self.NEW))
        build_supersession_edges(db)
        assert neighbours(db, ids["https://d.example/v1"], kinds=["supersession"])
        assert neighbours(db, ids["https://d.example/v2"], kinds=["supersession"]) == []

    def test_same_sitting_duplicates_are_not_supersession(self, db):
        _load(db, _a("https://d.example/v1", "Rust 异步编程 完全指南", self.OLD)
                  + _a("https://d.example/v2", "Rust 异步编程 完全指南", self.OLD + 120))
        assert build_supersession_edges(db) == 0

    def test_unrelated_titles_on_one_domain_are_not_supersession(self, db):
        _load(db, _a("https://d.example/a", "Rust 异步编程 完全指南", self.OLD)
                  + _a("https://d.example/b", "咖啡 冲煮 水温 曲线", self.NEW))
        assert build_supersession_edges(db) == 0

    def test_cross_domain_lookalikes_are_left_alone(self, db):
        """A false supersession demotes a live bookmark; the bar stays high."""
        _load(db, _a("https://one.example/x", "Rust 异步编程 完全指南", self.OLD)
                  + _a("https://two.example/y", "Rust 异步编程 完全指南", self.NEW))
        assert build_supersession_edges(db) == 0


class TestSemanticEdges:
    def _seed(self, conn, vectors):
        ids = _load(conn, "".join(_a(f"https://h{i}.example/", f"t{i}", 1700000000 + i * 100000)
                                  for i in range(len(vectors))))
        ordered = [ids[f"https://h{i}.example/"] for i in range(len(vectors))]
        ensure_vec_tables(conn, dim=4, model="mock")
        for bid, v in zip(ordered, vectors, strict=True):
            upsert_content_vector(conn, bid, np.asarray(v, dtype=np.float32))
        return ordered

    def test_absent_vectors_are_a_skip_not_a_crash(self, db):
        _load(db, _a("https://a.com/1", "x", 1700000000))
        assert build_semantic_edges(db) == 0
        stats = build_edges(db)
        assert stats.counts["semantic"] == 0 and stats.skipped

    def test_near_duplicates_connect_and_opposites_do_not(self, db):
        ids = self._seed(db, [[1, 0, 0, 0], [0.99, 0.14, 0, 0], [0, 0, 0, 1]])
        build_semantic_edges(db)
        got = {(int(a), int(b)) for a, b in
               db.execute("SELECT src, dst FROM edge WHERE kind='semantic'")}
        assert (ids[0], ids[1]) in got and (ids[1], ids[0]) in got
        assert (ids[0], ids[2]) not in got

    def test_edges_are_mutual_only(self, db):
        """A vector in a dense cluster must not become an attractor."""
        rng = np.random.default_rng(0)
        cluster = [(rng.normal(0, 0.02, 4) + np.array([1, 0, 0, 0])) for _ in range(9)]
        outlier = np.array([0.0, 1.0, 0.0, 0.0])
        ids = self._seed(db, [*cluster, outlier])
        build_semantic_edges(db)
        deg = dict(db.execute(
            "SELECT src, count(*) FROM edge WHERE kind='semantic' GROUP BY src").fetchall())
        assert deg.get(ids[-1], 0) == 0
        assert max(deg.values()) <= 9

    def test_weight_falls_with_distance(self, db):
        ids = self._seed(db, [[1, 0, 0, 0], [0.999, 0.045, 0, 0], [0.9, 0.436, 0, 0]])
        build_semantic_edges(db)
        w = {int(d): float(x) for d, x in db.execute(
            "SELECT dst, weight FROM edge WHERE kind='semantic' AND src=?", (ids[0],))}
        assert w[ids[1]] > w[ids[2]]


class TestOrchestration:
    def test_rebuild_is_idempotent(self, db):
        _load(db, _a("https://github.com/o/r/a", "one", 1700000000)
                  + _a("https://github.com/o/r/b", "two", 1700000060))
        build_sessions(db, eps=1800)
        first = build_edges(db).total
        assert build_edges(db).total == first

    def test_selective_rebuild_leaves_other_kinds_alone(self, db):
        _load(db, _a("https://github.com/o/r/a", "one", 1700000000)
                  + _a("https://github.com/o/r/b", "two", 1700000060))
        build_sessions(db, eps=1800)
        build_edges(db)
        before = db.execute(
            "SELECT count(*) FROM edge WHERE kind='session'").fetchone()[0]
        build_edges(db, kinds=["same_domain"])
        assert db.execute(
            "SELECT count(*) FROM edge WHERE kind='session'").fetchone()[0] == before

    def test_deleting_a_bookmark_cascades_out_of_the_graph(self, db):
        ids = _load(db, _a("https://github.com/o/r/a", "one", 1700000000)
                        + _a("https://github.com/o/r/b", "two", 1700000060))
        build_edges(db)
        db.execute("DELETE FROM bookmark WHERE id=?", (ids["https://github.com/o/r/a"],))
        assert db.execute("SELECT count(*) FROM edge").fetchone()[0] == 0

    def test_one_hop_only(self, db):
        ids = _load(db, _a("https://github.com/o/r1/a", "a", 1700000000)
                        + _a("https://github.com/o/r1/b", "b", 1700000060)
                        + _a("https://github.com/o/r2/a", "c", 1900000000)
                        + _a("https://github.com/o/r2/b", "d", 1900000060))
        build_edges(db, kinds=["anchor_sibling"])
        out = neighbours(db, ids["https://github.com/o/r1/a"])
        assert [x[0] for x in out] == [ids["https://github.com/o/r1/b"]]


class TestTheStatsMustDescribeTheTableAndNotTheIntention:
    """``EdgeStats`` used to report rows *offered*, which is not a measurement.

    The W1 index log said 19,763 edges; the library snapshot published with the
    report holds 19,648. Rebuilding the graph on that same snapshot reproduces
    19,763, so the graph definition was right and the *count* was the thing that
    could not be checked -- it was ``len(pairs)``, not a query. A count that
    cannot disagree with the writer is not evidence that the write happened.
    """

    def test_the_reported_total_equals_what_the_table_holds(self, db):
        _load(db, _a("https://github.com/o/r/a", "one", 1700000000)
                  + _a("https://github.com/o/r/b", "two", 1700000060)
                  + _a("https://github.com/o/r/c", "three", 1700000120))
        build_sessions(db, eps=1800)
        stats = build_edges(db)
        assert stats.total == db.execute("SELECT count(*) FROM edge").fetchone()[0]
        for kind, n in stats.counts.items():
            assert n == db.execute(
                "SELECT count(*) FROM edge WHERE kind=?", (kind,)
            ).fetchone()[0], kind

    def test_a_pair_offered_twice_is_counted_once(self, db):
        from facetmark.edges import _insert

        ids = _load(db, _a("https://a.com/1", "x", 1700000000)
                        + _a("https://b.com/2", "y", 1700000060))
        a, b = ids["https://a.com/1"], ids["https://b.com/2"]
        pairs = [(a, b, 1.0), (a, b, 0.5), (b, a, 1.0)]
        assert _insert(db, "session", pairs) == 2, "three offered, two rows"
        assert db.execute("SELECT count(*) FROM edge").fetchone()[0] == 2
        assert db.execute(
            "SELECT weight FROM edge WHERE src=? AND dst=?", (a, b)
        ).fetchone()[0] == 0.5, "last write still wins"


class TestTheSemanticFloorIsTheOneThatWasEvaluated:
    """The shipped default must be the value the W1 report measured.

    It was not. The report recalibrated the floor under a rule fixed before
    seeing the outcome (1st percentile of random document-pair distance, two
    decimals -> 0.93) and rebuilt the graph, taking semantic coverage from 1.4%
    to 79.4%; every number in §5 and §9.1 was measured on that graph. The
    constant in the source stayed at 0.60, so a fresh install reproduced the
    report's prose and not its configuration.
    """

    def test_the_default_is_the_preregistered_value(self):
        from facetmark.edges import SEMANTIC_MAX_DISTANCE

        assert SEMANTIC_MAX_DISTANCE == 0.93, (
            "0.93 is p1 of the random-pair distance distribution on bge-m3 "
            "(post_index.json). Changing it means re-deriving it under the "
            "same rule on the new embedding model, not picking a nicer number."
        )

    def test_the_module_level_knob_can_actually_be_turned(self, db, monkeypatch):
        # It could not: max_distance was a default argument, bound at import,
        # so setting the constant did nothing and said nothing.
        import facetmark.edges as E

        ids = TestSemanticEdges._seed(
            TestSemanticEdges(), db, [[1, 0, 0, 0], [0.9, 0.436, 0, 0]]
        )
        monkeypatch.setattr(E, "SEMANTIC_MAX_DISTANCE", 0.01)
        assert E.build_semantic_edges(db) == 0, "a tight floor must exclude"
        monkeypatch.setattr(E, "SEMANTIC_MAX_DISTANCE", 1.5)
        assert E.build_semantic_edges(db) == 2, "a loose floor must include"
        assert db.execute(
            "SELECT count(*) FROM edge WHERE kind='semantic' AND src=?", (ids[0],)
        ).fetchone()[0] == 1
