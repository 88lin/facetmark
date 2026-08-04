"""Tests for ``search.decay.cold_census``.

The census exists because of a measurement failure, and the tests are written
to make that failure impossible to repeat rather than to cover lines.

What happened: ``docs/decay-reach.md`` measured the cost of the demotion layer
on the 2,376-page evaluation library and reported exactly zero, CI95
``[0, 0]``. The measurement was correct. Its subject was not: the ``health``
table had zero rows, so condition 3 could only fire through supersession edges,
and ``open_count`` was 0 for every single bookmark, so condition 1 selected the
whole library. A three-condition detector was running on one condition. With
the health checker actually run, the cold layer went from 8 pages to 73 and the
same A/B came out at **-1.46pp, CI95 [-2.60, -0.49]** -- the layer costs recall.

So the properties under test are the ones that would have caught it:

* the decomposition reports each condition *separately*, not just the
  conjunction, because the conjunction is what hid the problem;
* ``degenerate_conditions`` names the two silent failures explicitly;
* ``servable_cold`` separates "the URL is dead" from "we cannot answer with
  it", which is the distinction the demotion gets wrong.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from facetmark.config import Settings
from facetmark.db import open_db
from facetmark.search import cold_census
from facetmark.search.decay import DEAD_VERDICTS, cold_bookmark_ids

NOW = 1785649110


def _library(path: Path, now: int = NOW) -> sqlite3.Connection:
    """Eight bookmarks covering every branch of the three conditions.

    ============  ===  =========  ==============  =====  ==================
    id            old  unopened   evidence        body   expected
    ============  ===  =========  ==============  =====  ==================
    1             yes  yes        supersession    500    cold, servable
    2             yes  yes        verdict 'gone'  500    cold, servable
    3             yes  yes        verdict 'gone'  0      cold, unservable
    4             yes  yes        'gone' -> 'ok'  500    not cold (healed)
    5             yes  yes        none            500    not cold
    6             yes  no         verdict 'gone'  500    not cold (opened)
    7             no   yes        verdict 'gone'  500    not cold (recent)
    8             yes  yes        verdict         500    cold, but body is
                                  'drifted'              under min_body_chars
    ============  ===  =========  ==============  =====  ==================
    """
    conn = open_db(path)
    old, recent = now - 400 * 86400, now - 10 * 86400
    rows = [
        (1, old, 0, 500),
        (2, old, 0, 500),
        (3, old, 0, 0),
        (4, old, 0, 500),
        (5, old, 0, 500),
        (6, old, 3, 500),
        (7, recent, 0, 500),
        (8, old, 0, 120),
    ]
    for bid, added, opens, chars in rows:
        conn.execute(
            "INSERT INTO bookmark(id, url, url_norm, url_hash, date_added, "
            "open_count, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?)",
            (bid, f"https://e/{bid}", f"https://e/{bid}", f"h{bid}", added, opens, now, now),
        )
        if chars:
            conn.execute(
                "INSERT INTO content(bookmark_id, body_text, char_count) VALUES(?,?,?)",
                (bid, "x" * chars, chars),
            )
    conn.execute("INSERT INTO edge(src, dst, kind) VALUES(1, 5, 'supersession')")
    for bid, verdict, when in [
        (2, "gone", now - 86400),
        (3, "gone", now - 86400),
        (4, "gone", now - 200 * 86400),
        (4, "alive", now - 86400),
        (6, "gone", now - 86400),
        (7, "gone", now - 86400),
        (8, "drifted", now - 86400),
    ]:
        conn.execute(
            "INSERT INTO health(bookmark_id, checked_at, verdict) VALUES(?,?,?)",
            (bid, when, verdict),
        )
    return conn


@pytest.fixture
def conn(tmp_path):
    c = _library(tmp_path / "lib.db")
    yield c
    c.close()


class TestTheConditionsAreReportedSeparately:
    """The conjunction is what hid the defect; the terms are what expose it."""

    def test_each_condition_gets_its_own_count(self, conn):
        got = cold_census(conn, age_days=365, now_ts=NOW)
        assert got["bookmarks"] == 8
        assert got["never_opened"] == 7          # everything except id 6
        assert got["older_than_cutoff"] == 7     # everything except id 7
        assert got["old_and_never_opened"] == 6  # ids 1-5, 8

    def test_condition_three_is_split_by_evidence_source(self, conn):
        got = cold_census(conn, age_days=365, now_ts=NOW)
        # This split is the whole point. On the evaluation library the edge term
        # gave 8 and the verdict term gave 0, and only reporting them apart
        # makes "the verdict term has never fired" visible.
        assert got["condition3_by_supersession"] == 1   # id 1
        assert got["condition3_by_dead_verdict"] == 3   # ids 2, 3, 8
        assert got["cold"] == 4

    def test_the_conjunction_agrees_with_the_function_that_ships(self, conn):
        # The census must not grow its own definition of cold. If it drifts from
        # cold_bookmark_ids the numbers in the write-up describe nothing.
        got = cold_census(conn, age_days=365, now_ts=NOW)
        assert got["cold"] == len(cold_bookmark_ids(conn, age_days=365, now_ts=NOW))

    def test_a_healed_page_is_not_cold(self, conn):
        # id 4 has 'gone' in its history and a later 'alive'. Only the newest
        # check counts, or the cold layer becomes a ratchet.
        assert 4 not in cold_bookmark_ids(conn, age_days=365, now_ts=NOW)
        assert cold_census(conn, age_days=365, now_ts=NOW)["cold"] == 4

    def test_every_dead_verdict_spelling_is_honoured(self, conn):
        # id 8 is cold on 'drifted', which is the weakest of the three
        # spellings and the one that supplied 28 of the 73 cold pages on the
        # evaluation library. If DEAD_VERDICTS and the census fall out of step
        # the decomposition under-reports the verdict term.
        assert set(DEAD_VERDICTS) == {"gone", "drifted", "soft_gone"}
        assert 8 in cold_bookmark_ids(conn, age_days=365, now_ts=NOW)


class TestTheSilentFailuresAreNamed:
    def test_an_unchecked_library_says_so(self, tmp_path):
        c = open_db(tmp_path / "empty.db")
        c.execute(
            "INSERT INTO bookmark(id, url, url_norm, url_hash, date_added, "
            "open_count, created_at, updated_at) "
            "VALUES(1,'https://e/1','https://e/1','h1',?,0,?,?)",
            (NOW - 400 * 86400, NOW, NOW),
        )
        got = cold_census(c, age_days=365, now_ts=NOW)
        assert got["health_checked"] == 0
        assert got["health_unchecked"] == 1
        assert "health_never_checked" in got["degenerate_conditions"]
        c.close()

    def test_a_checked_library_drops_the_warning(self, conn):
        got = cold_census(conn, age_days=365, now_ts=NOW)
        assert got["health_checked"] == 6
        assert "health_never_checked" not in got["degenerate_conditions"]

    def test_an_all_zero_open_count_is_flagged_as_degenerate(self, tmp_path):
        # Every browser export lands here: the Netscape HTML format carries no
        # usage telemetry, so condition 1 selects the entire library and the
        # detector is really a two-condition one. On the evaluation library this
        # was true of all 2,376 rows and nothing said so.
        c = open_db(tmp_path / "fresh.db")
        for bid in (1, 2, 3):
            c.execute(
                "INSERT INTO bookmark(id, url, url_norm, url_hash, date_added, "
                "open_count, created_at, updated_at) VALUES(?,?,?,?,?,0,?,?)",
                (bid, f"https://e/{bid}", f"https://e/{bid}", f"h{bid}", NOW, NOW, NOW),
            )
        got = cold_census(c, age_days=365, now_ts=NOW)
        assert got["never_opened"] == got["bookmarks"] == 3
        assert "never_opened_selects_everything" in got["degenerate_conditions"]
        c.close()

    def test_one_observed_open_clears_the_flag(self, conn):
        # id 6 has open_count = 3, so this library is not degenerate on
        # condition 1 even though six of eight rows are still at zero.
        got = cold_census(conn, age_days=365, now_ts=NOW)
        assert "never_opened_selects_everything" not in got["degenerate_conditions"]

    def test_an_empty_library_is_not_reported_as_degenerate(self, tmp_path):
        # 0 == 0 would satisfy "never_opened selects everything" arithmetically.
        # Saying a library with no bookmarks has a broken condition is noise.
        c = open_db(tmp_path / "void.db")
        got = cold_census(c, age_days=365, now_ts=NOW)
        assert got["bookmarks"] == 0
        assert got["cold"] == 0
        assert "never_opened_selects_everything" not in got["degenerate_conditions"]
        c.close()


class TestServableSeparatesDeadUrlFromDeadAnswer:
    """The distinction the demotion gets wrong, made countable."""

    def test_cold_pages_split_into_servable_and_not(self, conn):
        got = cold_census(conn, age_days=365, now_ts=NOW, min_body_chars=200)
        # ids 1, 2 have 500 chars; id 3 has none; id 8 has 120, under the floor.
        assert (got["servable_cold"], got["unservable_cold"]) == (2, 2)
        assert got["servable_cold"] + got["unservable_cold"] == got["cold"]

    def test_the_floor_is_the_configured_one(self, conn):
        # id 8's 120 chars cross a lower floor. The number has to follow
        # min_body_chars or "servable" means something different from what the
        # indexer considered worth indexing.
        assert cold_census(conn, age_days=365, now_ts=NOW, min_body_chars=100)[
            "servable_cold"
        ] == 3
        assert Settings().min_body_chars == 200

    def test_a_page_with_no_content_row_counts_as_unservable(self, conn):
        # id 3 has a dead verdict and no content row at all. A LEFT JOIN that
        # silently produced NULL >= 200 would have to be read as "servable".
        assert 3 in cold_bookmark_ids(conn, age_days=365, now_ts=NOW)
        got = cold_census(conn, age_days=365, now_ts=NOW)
        assert got["unservable_cold"] >= 1


class TestTheClockAndTheWindow:
    def test_the_census_uses_the_clock_it_is_given(self, conn):
        early = cold_census(conn, age_days=365, now_ts=NOW - 400 * 86400)
        assert (early["older_than_cutoff"], early["cold"]) == (0, 0)

    def test_the_cutoff_is_derived_from_age_days(self, conn):
        got = cold_census(conn, age_days=30, now_ts=NOW)
        assert got["age_days"] == 30
        assert got["cutoff_ts"] == NOW - 30 * 86400
        # A 30-day window makes id 7 (saved 10 days ago) still recent but pulls
        # nothing new in, so the cold set is unchanged.
        assert got["cold"] == 4

    def test_a_wide_enough_window_admits_the_recent_page(self, conn):
        got = cold_census(conn, age_days=1, now_ts=NOW)
        assert got["older_than_cutoff"] == 8
        assert got["cold"] == 5  # id 7 joins: recent, unopened, verdict 'gone'


class TestItIsReachableFromTheServiceSurfaces:
    def test_library_stats_carries_the_census(self, conn):
        from facetmark import service

        stats = service.library_stats(conn, Settings(use_mock_provider=True))
        assert "cold_layer" in stats
        assert stats["cold_layer"]["bookmarks"] == 8
        # health.summary already reported `unchecked`; nothing joined it to the
        # consequence. These two now sit in the same payload.
        assert stats["health"]["unchecked"] + stats["cold_layer"]["health_checked"] >= 6
