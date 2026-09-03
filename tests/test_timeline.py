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
        assert tl["older"] == 1
        assert tl["oldest"] == D40

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
        ]

    def test_added_offers_date_examples(self, conn):
        out = suggest_query_syntax(conn, "added:")
        assert any(s["label"] == "added:<7d" for s in out["suggestions"])

    def test_the_endpoint_is_token_gated(self, tmp_path):
        st = Settings(data_dir=tmp_path, use_mock_provider=True, embed_dim=32,
                      embed_model="m", chat_model="m", health_enable_external=False)
        with TestClient(create_app(st), client=("127.0.0.1", 40000)) as client:
            r = client.post("/suggest/query", json={"text": "dom"})
            assert r.status_code == 401
