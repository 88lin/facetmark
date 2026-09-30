"""The timeline endpoint and the query-syntax completer.

Both are ports of hister features, and both are deliberately *read-only views
over columns that already exist*: ``timeline`` buckets ``bookmark.date_added``
and the completer reads distinct values out of ``bookmark``/``enrichment``.
Neither may touch the write path, and both must answer usefully on an empty
library -- the library view fetches them on every visit, including the first.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from facetmark.api import create_app
from facetmark.config import Settings
from facetmark.service import suggest_query_syntax, timeline

# 2026-08-04T00:13:20Z, and three days earlier, forty days earlier.
NOW = 1785792800
D3 = 1785792800 - 3 * 86400
D40 = 1785792800 - 40 * 86400


@pytest.fixture()
def conn():
    from facetmark.db import open_db

    c = open_db(":memory:")
    for i, (url, title, ts) in enumerate(
        [
            ("https://github.com/a", "today one", NOW - 3600),
            ("https://github.com/b", "today two", NOW - 7200),
            ("https://gitlab.com/c", "three days ago", D3),
            ("https://example.com/d", "forty days ago", D40),
        ],
        start=1,
    ):
        c.execute(
            "INSERT INTO bookmark(id, url, url_norm, url_hash, title, host, domain,"
            " date_added, source, indexable, created_at, updated_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (i, url, url, f"h{i}", title, "x", "x", ts, "api", 1, NOW, NOW),
        )
    c.commit()
    yield c
    c.close()


class TestTimeline:
    def test_seven_day_buckets_newest_first(self, conn):
        tl = timeline(conn, now=NOW)
        assert len(tl["days"]) == 7
        assert tl["days"][0]["count"] == 2      # today
        assert tl["days"][3]["count"] == 1      # three days ago
        assert sum(d["count"] for d in tl["days"]) == 3

    def test_months_bucket_the_rest(self, conn):
        tl = timeline(conn, now=NOW)
        assert tl["months"][0]["count"] == 1
        # Not 1. The one bookmark outside the week *is* that month bucket, and
        # the strip's label reads "N older than the months shown". This line
        # asserted 1 and was counting the same bookmark twice -- the bug the
        # page was printing, written down as an expectation.
        assert tl["older"] == 0
        assert tl["oldest"] == D40


def _month_start(now_ts: int, back: int) -> int:
    """Midnight UTC on the first of the month ``back`` months before ``now``."""
    import datetime as dt

    d = dt.datetime.fromtimestamp(now_ts, tz=dt.timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    for _ in range(back):
        d = (d - dt.timedelta(days=1)).replace(day=1)
    return int(d.timestamp())


def _add(conn, i: int, ts: int) -> None:
    conn.execute(
        "INSERT INTO bookmark(id, url, url_norm, url_hash, title, host, domain,"
        " date_added, source, indexable, created_at, updated_at)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (i, f"https://e.test/{i}", f"https://e.test/{i}", f"hh{i}",
         f"page {i}", "e.test", "e.test", ts, "api", 1, ts, ts),
    )


class TestTheOlderCount:
    """The strip says "N older than the months shown", so N is the tail the
    month list did not reach.

    It was counting everything outside the seven-day window, which is the set
    the month buckets are drawn *from*. The demo library showed three months
    summing to 40 and then claimed 40 more below them; a real 1,857-bookmark
    library claimed 1,832 under twelve months that held almost all of them.
    """

    @pytest.fixture()
    def empty(self):
        from facetmark.db import open_db

        c = open_db(":memory:")
        yield c
        c.close()

    def test_a_library_the_months_reach_has_no_tail(self, empty):
        for i in range(1, 6):
            _add(empty, i, _month_start(NOW, i) + 10 * 86400)
        empty.commit()
        tl = timeline(empty, now=NOW)
        assert len(tl["months"]) == 5
        assert tl["older"] == 0

    def test_only_what_the_month_list_did_not_reach_is_counted(self, empty):
        for i in range(1, 16):
            _add(empty, i, _month_start(NOW, i) + 10 * 86400)
        empty.commit()
        tl = timeline(empty, now=NOW, months=12)
        assert len(tl["months"]) == 12
        assert tl["older"] == 3

    @pytest.mark.parametrize("seeded,months", [(5, 12), (15, 12), (15, 6), (1, 1)])
    def test_the_three_pieces_add_up_to_the_library(self, empty, seeded, months):
        """The invariant that makes the label true: a bookmark is in the week,
        or in a month shown, or in the tail -- and in exactly one of them."""
        for i in range(1, seeded + 1):
            _add(empty, i, _month_start(NOW, i) + 10 * 86400)
        empty.commit()
        tl = timeline(empty, now=NOW, months=months)
        counted = (
            sum(d["count"] for d in tl["days"])
            + sum(m["count"] for m in tl["months"])
            + tl["older"]
        )
        assert counted == seeded

    def test_the_month_boundary_is_the_one_the_buckets_used(self, empty):
        """A save in the first second of the oldest month shown belongs to that
        bucket, not to the tail. The count and the bucketing read the same
        ``strftime`` expression so they cannot disagree about where a month
        starts -- this is the assertion that keeps them reading it."""
        for i in range(1, 13):
            _add(empty, i, _month_start(NOW, i) + 10 * 86400)
        _add(empty, 99, _month_start(NOW, 12))
        empty.commit()
        tl = timeline(empty, now=NOW, months=12)
        assert tl["months"][-1]["count"] == 2
        assert tl["older"] == 0

    def test_an_empty_library_answers_zeroes_not_an_error(self, conn):
        conn.execute("DELETE FROM bookmark")
        conn.commit()
        tl = timeline(conn, now=NOW)
        assert tl == {"days": [], "months": [], "older": 0, "oldest": None}

    def test_the_endpoint_serves_it(self, conn, tmp_path):
        st = Settings(data_dir=tmp_path, use_mock_provider=True, embed_dim=32,
                      embed_model="m", chat_model="m", health_enable_external=False)
        # Point the service at the fixture's connection through a fresh file:
        # TestClient owns its own AppState, so the rows are re-inserted there.
        with TestClient(create_app(st), client=("127.0.0.1", 40000)) as client:
            auth = {"Authorization": f"Bearer {client.app.state.fm.token}"}
            r = client.get("/timeline", headers=auth)
        assert r.status_code == 200
        body = r.json()
        assert body["days"] == [] and body["oldest"] is None


class TestQuerySyntaxSuggest:
    def test_a_fragment_offers_the_fields(self, conn):
        out = suggest_query_syntax(conn, "dom")
        labels = [s["label"] for s in out["suggestions"]]
        assert "domain:" in labels
        assert all(s["kind"] == "field" for s in out["suggestions"])

    def test_domain_values_come_from_the_library(self, conn):
        conn.execute("UPDATE bookmark SET domain='github.com' WHERE id IN (1,2)")
        conn.execute("UPDATE bookmark SET domain='gitlab.com' WHERE id=3")
        conn.commit()
        out = suggest_query_syntax(conn, "domain:git")
        got = [(s["label"], s["detail"]) for s in out["suggestions"]]
        assert ("github.com", "2 saved") in got
        assert ("gitlab.com", "1 saved") in got

    def test_negation_keeps_the_minus_sign(self, conn):
        conn.execute("UPDATE bookmark SET domain='github.com' WHERE id=1")
        conn.commit()
        out = suggest_query_syntax(conn, "-domain:git")
        assert out["suggestions"][0]["insert"] == "-domain:github.com"

    def test_sort_completes_its_values(self, conn):
        out = suggest_query_syntax(conn, "sort:")
        assert [s["label"] for s in out["suggestions"]] == [
            "sort:date", "sort:-date", "sort:domain", "sort:title", "sort:url",
            "sort:opened",
        ]

    def test_site_completes_like_the_field_it_aliases(self, conn):
        """`site:` is a documented alias of `domain:` and completed nothing:
        the branches compared the name the user typed, not the canonical one."""
        conn.execute("UPDATE bookmark SET domain='github.com' WHERE id=1")
        conn.commit()
        out = suggest_query_syntax(conn, "site:git")
        assert out["suggestions"][0]["insert"] == "site:github.com"

    def test_host_completes_from_the_hostnames_in_the_library(self, conn):
        conn.execute("UPDATE bookmark SET host='news.ycombinator.com' WHERE id=1")
        conn.commit()
        out = suggest_query_syntax(conn, "host:ycomb")
        assert out["suggestions"][0]["insert"] == "host:news.ycombinator.com"

    def test_added_offers_date_examples(self, conn):
        out = suggest_query_syntax(conn, "added:")
        assert any(s["label"] == "added:<7d" for s in out["suggestions"])

    def test_the_endpoint_is_token_gated(self, tmp_path):
        st = Settings(data_dir=tmp_path, use_mock_provider=True, embed_dim=32,
                      embed_model="m", chat_model="m", health_enable_external=False)
        with TestClient(create_app(st), client=("127.0.0.1", 40000)) as client:
            r = client.post("/suggest/query", json={"text": "dom"})
            assert r.status_code == 401
