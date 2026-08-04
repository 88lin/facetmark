"""Tests for the decay-reach probe's measuring apparatus.

``scripts/`` is not a package, so the module is loaded by path, the same way
``test_boost_medium.py`` does it.

The probe's replay loop needs an indexed library and an embedding model, so the
616-query run is not reproduced here. What is tested is everything that decides
whether the reported zero is *believable*: that the two arms differ by exactly
one setting and read the same database, that ``SHIPPED`` is still what ships,
that the census counts the condition doing the work rather than the age filter,
that the interval is paired, and that the replay loop records ranks the way the
write-up reads them.

The load-bearing one is
``TestTheIntervalIsPairedAndDeterministic.test_cancelling_differences_do_not_
collapse_the_interval``. ``docs/decay-reach.md`` §5 argues the ``[0, 0]``
interval means "nothing changed", not "changes cancelled". That is a claim
about ``_boot``, and it is only true if the bootstrap resamples pairs.
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import sqlite3
from pathlib import Path

import pytest

from facetmark.config import Settings
from facetmark.db import open_db
from facetmark.search import apply_decay
from facetmark.search.pipeline import ALL_CONFIGS

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "decay_reach_probe.py"


def _load():
    spec = importlib.util.spec_from_file_location("decay_reach_probe_under_test", _PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def dr():
    return _load()


def _rows(*ranks: int, qtype: str = "q_content") -> list[dict]:
    return [{"rank": r, "qtype": qtype} for r in ranks]


class TestTheTwoArmsDifferByExactlyOneSetting:
    """The whole attribution argument rests on this and nothing else."""

    def _args(self, db: str) -> argparse.Namespace:
        return argparse.Namespace(
            db=db, embed_model="bge-m3", embed_dim=1024,
            embed_path="/nonexistent/bge-m3", max_seq=1024, batch=16,
        )

    def test_only_the_rescue_threshold_differs(self, dr, tmp_path):
        args = self._args(str(tmp_path / "lib.db"))
        a = dr._settings(args, dr.SHIPPED).model_dump()
        b = dr._settings(args, dr.REACHABLE).model_dump()
        differing = {k for k in a if a[k] != b[k]}
        assert differing == {"decay_rescue_threshold"}
        assert (a["decay_rescue_threshold"], b["decay_rescue_threshold"]) == (0.02, 0.0)

    def test_both_arms_read_the_same_database_file(self, dr, tmp_path):
        args = self._args(str(tmp_path / "sub" / "lib.db"))
        a, b = dr._settings(args, dr.SHIPPED), dr._settings(args, dr.REACHABLE)
        assert a.data_dir == b.data_dir == (tmp_path / "sub")
        assert a.db_name == b.db_name == "lib.db"

    def test_shipped_is_still_what_ships(self, dr):
        # If the default ever moves, the "shipped" arm silently stops being the
        # shipped arm and every number in docs/decay-reach.md is mislabelled.
        assert Settings().decay_rescue_threshold == dr.SHIPPED

    def test_reachable_makes_the_valve_unreachable_in_the_other_direction(self, dr):
        # RRF scores are non-negative, so `hot_top_score < 0.0` can never hold
        # and the demotion always applies. That is what makes the B arm the
        # decay layer as designed rather than a second copy of the A arm.
        out, info = apply_decay([(1, 0.0164), (2, 0.0161)], {2},
                                factor=0.5, rescue_threshold=dr.REACHABLE)
        assert info.rescued is False
        assert info.demoted == 1
        assert out[1] == (2, pytest.approx(0.00805))

        _, shipped = apply_decay([(1, 0.0164), (2, 0.0161)], {2},
                                 factor=0.5, rescue_threshold=dr.SHIPPED)
        assert (shipped.rescued, shipped.demoted) == (True, 0)


class TestRecallCountsWhatTheWriteUpSaysItCounts:
    def test_rank_zero_is_a_miss_not_a_first_place(self, dr):
        # `_run` encodes "target absent from the list" as 0, which sorts before
        # 1 under any naive `rank <= at`.
        assert dr._recall(_rows(0, 0), 5) == 0.0
        assert dr._recall(_rows(1, 0), 1) == 0.5

    def test_the_cutoff_is_inclusive(self, dr):
        assert dr._recall(_rows(5), 5) == 1.0
        assert dr._recall(_rows(6), 5) == 0.0

    def test_ranks_beyond_the_cutoff_still_count_at_a_wider_one(self, dr):
        rows = _rows(1, 3, 9, 0)
        assert (dr._recall(rows, 1), dr._recall(rows, 5), dr._recall(rows, 20)) == (
            0.25, 0.5, 0.75,
        )


class TestTheIntervalIsPairedAndDeterministic:
    def test_identical_arms_give_a_degenerate_interval(self, dr):
        rows = _rows(1, 3, 0, 7, 2)
        got = dr._boot(rows, list(rows), 5, n=200, seed=1)
        assert got["delta_pp"] == 0.0
        assert got["ci95_pp"] == [0.0, 0.0]
        assert got["boots"] == 200

    def test_cancelling_differences_do_not_collapse_the_interval(self, dr):
        # Twenty queries, ten gained and ten lost: the point estimate is the
        # same 0.0 as above, but the interval must not be. This is the property
        # docs/decay-reach.md §5 leans on when it says the shipped [0, 0] means
        # "nothing changed" rather than "changes cancelled".
        a = _rows(*([1] * 10 + [0] * 10))
        b = _rows(*([0] * 10 + [1] * 10))
        got = dr._boot(a, b, 5, n=2000, seed=7)
        assert got["delta_pp"] == 0.0
        lo, hi = got["ci95_pp"]
        assert lo < 0.0 < hi

    def test_the_seed_is_reproducible_and_never_touches_the_estimate(self, dr):
        a = _rows(*([1] * 20 + [0] * 20))
        b = _rows(*([1] * 26 + [0] * 14))
        first = dr._boot(a, b, 5, n=1000, seed=20260805)
        assert first == dr._boot(a, b, 5, n=1000, seed=20260805)
        # Only the interval is a draw. If a reseed moved delta_pp the reported
        # effect would be an artefact of the resampling.
        assert dr._boot(a, b, 5, n=1000, seed=1)["delta_pp"] == first["delta_pp"] == 15.0
        lo, hi = first["ci95_pp"]
        assert lo <= first["delta_pp"] <= hi

    def test_the_point_estimate_matches_the_recalls_it_is_an_interval_around(self, dr):
        a, b = _rows(9, 9, 9, 9), _rows(1, 9, 9, 9)
        got = dr._boot(a, b, 5, n=500, seed=3)
        assert got["delta_pp"] == pytest.approx(
            (dr._recall(b, 5) - dr._recall(a, 5)) * 100, abs=1e-9
        )
        assert got["delta_pp"] == 25.0

    def test_unequal_arms_are_an_error_rather_than_a_truncation(self, dr):
        # A dropped query would quietly re-pair every query after it with the
        # wrong partner, which is exactly the failure a paired design cannot
        # survive.
        with pytest.raises(ValueError):
            dr._boot(_rows(1, 2, 3), _rows(1, 2), 5, n=10, seed=0)


class TestTheCensusMeasuresTheConditionDoingTheWork:
    def _library(self, path: Path, now: int) -> sqlite3.Connection:
        conn = open_db(path)
        old, recent = now - 400 * 86400, now - 10 * 86400
        rows = [
            (1, old, 0),   # superseded by an edge
            (2, old, 0),   # latest health verdict is dead
            (3, old, 0),   # was dead, latest check says otherwise
            (4, old, 0),   # old and untouched, but no evidence at all
            (5, old, 1),   # evidence, but it has been opened
            (6, recent, 0),  # evidence, but not old enough
        ]
        for bid, added, opens in rows:
            conn.execute(
                "INSERT INTO bookmark(id, url, url_norm, url_hash, date_added, "
                "open_count, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?)",
                (bid, f"https://e/{bid}", f"https://e/{bid}", f"h{bid}", added,
                 opens, now, now),
            )
        for src in (1, 5, 6):
            conn.execute(
                "INSERT INTO edge(src, dst, kind) VALUES(?, 4, 'supersession')", (src,)
            )
        conn.execute(
            "INSERT INTO health(bookmark_id, checked_at, verdict) VALUES(2, ?, 'gone')",
            (now - 86400,),
        )
        conn.execute(
            "INSERT INTO health(bookmark_id, checked_at, verdict) VALUES(3, ?, 'gone')",
            (now - 200 * 86400,),
        )
        conn.execute(
            "INSERT INTO health(bookmark_id, checked_at, verdict) VALUES(3, ?, 'ok')",
            (now - 86400,),
        )
        return conn

    def test_condition_three_is_what_separates_cold_from_merely_old(self, dr, tmp_path):
        now = 1785649110
        conn = self._library(tmp_path / "lib.db", now)
        got = dr._census(conn, set(), age_days=365, now_ts=now)
        assert got["bookmarks"] == 6
        assert got["old_and_never_opened"] == 4      # ids 1-4
        assert got["cold_ids"] == [1, 2]             # only those with evidence
        assert got["cold"] == 2
        conn.close()

    def test_a_healed_page_is_not_cold(self, dr, tmp_path):
        # Bookmark 3 has a 'gone' verdict in its history and a later 'ok'. Only
        # the newest check counts; the opposite reading would make the cold
        # layer a ratchet.
        now = 1785649110
        conn = self._library(tmp_path / "lib.db", now)
        assert 3 not in dr._census(conn, set(), age_days=365, now_ts=now)["cold_ids"]
        conn.close()

    def test_the_overlap_with_the_answers_is_reported_not_inferred(self, dr, tmp_path):
        now = 1785649110
        conn = self._library(tmp_path / "lib.db", now)
        got = dr._census(conn, {2, 6, 99}, age_days=365, now_ts=now)
        assert got["targets"] == 3
        assert got["cold_targets"] == [2]
        conn.close()

    def test_the_clock_is_the_frozen_one_not_todays(self, dr, tmp_path):
        # Same library, a clock four hundred days earlier: nothing is old yet,
        # so nothing can be cold. If the census silently used time.time() the
        # census and the retrieval runs would disagree about the cold set.
        now = 1785649110
        conn = self._library(tmp_path / "lib.db", now)
        early = dr._census(conn, set(), age_days=365, now_ts=now - 400 * 86400)
        assert (early["old_and_never_opened"], early["cold"]) == (0, 0)
        conn.close()


class TestWhatTheReplayLoopRecords:
    class _Hit:
        def __init__(self, bookmark_id: int, cold: bool = False):
            self.bookmark_id = bookmark_id
            self.cold = cold

    class _Resp:
        def __init__(self, hits, rescued=False):
            self.hits = hits
            self.rescued = rescued

    class _Q:
        def __init__(self, text, qtype, target_id):
            self.text, self.qtype, self.target_id = text, qtype, target_id

    def _run_with(self, dr, monkeypatch, responses, queries):
        seen: list[dict] = []

        async def fake_search(conn, text, **kw):
            seen.append({"text": text, **kw})
            return responses[text]

        monkeypatch.setattr(dr, "search", fake_search)
        rows = asyncio.run(
            dr._run(None, queries, Settings(use_mock_provider=True), None,
                    limit=20, now_ts=1785649110)
        )
        return rows, seen

    def test_rank_is_one_indexed_and_absence_is_zero(self, dr, monkeypatch):
        queries = [self._Q("found", "q_content", 7), self._Q("missing", "q_vague", 99)]
        responses = {
            "found": self._Resp([self._Hit(3), self._Hit(7)]),
            "missing": self._Resp([self._Hit(3)]),
        }
        rows, _ = self._run_with(dr, monkeypatch, responses, queries)
        assert [r["rank"] for r in rows] == [2, 0]
        assert [r["qtype"] for r in rows] == ["q_content", "q_vague"]

    def test_the_valve_and_the_cold_pages_are_counted_separately(self, dr, monkeypatch):
        # `rescued` says the demotion declined to fire; `cold_in_list` says it
        # had something to fire at. The write-up needs both -- 113 rescues over
        # 46 lists containing a cold page is not a contradiction.
        queries = [self._Q("q", "q_vague", 1)]
        responses = {
            "q": self._Resp([self._Hit(1), self._Hit(2, cold=True),
                             self._Hit(3, cold=True)], rescued=True)
        }
        rows, _ = self._run_with(dr, monkeypatch, responses, queries)
        assert rows[0]["rescued"] is True
        assert rows[0]["cold_in_list"] == 2
        assert rows[0]["hits"] == [1, 2, 3]

    def test_it_measures_the_default_profile_at_the_frozen_clock(self, dr, monkeypatch):
        queries = [self._Q("q", "q_content", 1)]
        _, seen = self._run_with(dr, monkeypatch, {"q": self._Resp([self._Hit(1)])},
                                 queries)
        assert seen[0]["config"] is ALL_CONFIGS["full"]
        assert seen[0]["now_ts"] == 1785649110
        assert seen[0]["limit"] == 20
