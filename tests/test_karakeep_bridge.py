"""The karakeep bridge, tested against the contract in packages/shared/search.ts.

The four methods karakeep calls are addDocuments, deleteDocuments, search and
clearIndex. Everything here is offline: MockProvider embeds, so the assertions
are about the mapping and the response shape, not about ranking quality.
"""

from __future__ import annotations

import pytest

from facetmark.bridges import karakeep as kk
from facetmark.db import open_db
from facetmark.providers import MockProvider

DOCS = [
    {
        "id": "kk-1",
        "userId": "u1",
        "url": "https://example.com/postgres-indexes",
        "title": "Postgres index types explained",
        "content": "B-tree, hash, GiST and GIN indexes and when each one is the right choice.",
        "summary": "A tour of Postgres index types.",
        "tags": ["database", "postgres"],
        "createdAt": "2024-03-01T10:00:00Z",
    },
    {
        "id": "kk-2",
        "userId": "u1",
        "url": "https://example.com/sourdough",
        "linkTitle": "Sourdough starter maintenance",
        "note": "keep this, the hydration table is the useful part",
        "tags": ["cooking"],
        "createdAt": "2025-06-15T08:30:00Z",
    },
    {
        "id": "kk-3",
        "userId": "u2",
        "url": "https://example.com/rust-async",
        "title": "Async Rust without tears",
        "content": "Pinning, futures and why the borrow checker fights you in async code.",
        "tags": ["rust", "programming"],
        "createdAt": 1735689600,
    },
]


@pytest.fixture
async def bridged(mock_settings):
    conn = open_db(":memory:")
    provider = MockProvider(mock_settings)
    rep = await kk.add_documents(conn, DOCS, provider=provider, settings=mock_settings)
    return conn, provider, mock_settings, rep


class TestAddDocuments:
    async def test_a_batch_lands_as_bookmarks_content_and_vectors(self, bridged):
        conn, _, _, rep = bridged
        assert rep["received"] == 3
        assert rep["stored"] == 3
        assert rep["created"] == 3
        assert rep["updated"] == 0
        assert rep["embedded"] == 3
        assert rep["embed_error"] == ""
        assert conn.execute("SELECT COUNT(*) n FROM bookmark").fetchone()["n"] == 3
        assert conn.execute("SELECT COUNT(*) n FROM karakeep_doc").fetchone()["n"] == 3

    async def test_karakeep_crawled_text_becomes_body_text(self, bridged):
        """The point of the integration: karakeep already paid for the crawl."""
        conn, _, _, _ = bridged
        row = conn.execute(
            "SELECT c.char_count FROM karakeep_doc k JOIN content c"
            " ON c.bookmark_id = k.bookmark_id WHERE k.karakeep_id = 'kk-1'"
        ).fetchone()
        assert row["char_count"] > 50

    async def test_a_note_only_bookmark_still_gets_body_text(self, bridged):
        """Saved tweets and images have no article text; the note is the signal."""
        conn, _, _, _ = bridged
        row = conn.execute(
            "SELECT c.body_text FROM karakeep_doc k JOIN content c"
            " ON c.bookmark_id = k.bookmark_id WHERE k.karakeep_id = 'kk-2'"
        ).fetchone()
        assert "hydration table" in row["body_text"]

    async def test_tags_become_the_folder_string(self, bridged):
        conn, _, _, _ = bridged
        row = conn.execute(
            "SELECT b.folder, b.folder_depth FROM karakeep_doc k JOIN bookmark b"
            " ON b.id = k.bookmark_id WHERE k.karakeep_id = 'kk-1'"
        ).fetchone()
        assert row["folder"] == "database / postgres"
        assert row["folder_depth"] == 2

    async def test_link_title_is_the_fallback_when_title_is_absent(self, bridged):
        conn, _, _, _ = bridged
        row = conn.execute(
            "SELECT b.title FROM karakeep_doc k JOIN bookmark b ON b.id = k.bookmark_id"
            " WHERE k.karakeep_id = 'kk-2'"
        ).fetchone()
        assert row["title"] == "Sourdough starter maintenance"

    async def test_iso_and_epoch_timestamps_both_reach_date_added(self, bridged):
        conn, _, _, _ = bridged
        rows = dict(
            conn.execute(
                "SELECT k.karakeep_id, b.date_added FROM karakeep_doc k"
                " JOIN bookmark b ON b.id = k.bookmark_id"
            ).fetchall()
        )
        assert rows["kk-1"] == 1709287200  # 2024-03-01T10:00:00Z
        assert rows["kk-3"] == 1735689600

    async def test_a_missing_timestamp_is_counted_not_hidden(self, mock_settings):
        conn = open_db(":memory:")
        rep = await kk.add_documents(
            conn, [{"id": "x", "url": "https://e.com/a", "title": "a"}],
            provider=MockProvider(mock_settings), settings=mock_settings,
        )
        assert rep["created_at_missing"] == 1

    async def test_a_document_without_an_id_is_skipped_and_reported(self, mock_settings):
        conn = open_db(":memory:")
        rep = await kk.add_documents(
            conn, [{"url": "https://e.com/a"}, {"id": "ok", "url": "https://e.com/b"}],
            provider=MockProvider(mock_settings), settings=mock_settings,
        )
        assert (rep["stored"], rep["skipped_no_id"]) == (1, 1)

    async def test_pushing_the_same_id_twice_updates_in_place(self, bridged):
        conn, provider, st, _ = bridged
        again = await kk.add_documents(
            conn, [{**DOCS[0], "title": "Postgres index types, revised", "tags": ["db"]}],
            provider=provider, settings=st,
        )
        assert (again["created"], again["updated"]) == (0, 1)
        assert conn.execute("SELECT COUNT(*) n FROM bookmark").fetchone()["n"] == 3
        row = conn.execute("SELECT title, folder FROM bookmark WHERE id ="
                           " (SELECT bookmark_id FROM karakeep_doc WHERE karakeep_id='kk-1')"
                           ).fetchone()
        assert row["title"] == "Postgres index types, revised"
        assert row["folder"] == "db"

    async def test_an_existing_url_is_adopted_rather_than_duplicated(self, mock_settings):
        """A browser import and a karakeep push of one page are one bookmark."""
        conn = open_db(":memory:")
        conn.execute(
            "INSERT INTO bookmark(id,url,url_norm,url_hash,title,source,date_added,"
            "created_at,updated_at) VALUES(1,'https://example.com/x','https://example.com/x',"
            "?,'from browser','netscape_html',1,1,1)",
            ("h-x",),
        )
        conn.commit()
        from facetmark.normalize import normalize_url

        h = normalize_url("https://example.com/x").hash
        conn.execute("UPDATE bookmark SET url_hash=? WHERE id=1", (h,))
        conn.commit()
        rep = await kk.add_documents(
            conn, [{"id": "kk-x", "url": "https://example.com/x", "title": "from karakeep"}],
            provider=MockProvider(mock_settings), settings=mock_settings,
        )
        assert rep["created"] == 0
        assert conn.execute("SELECT COUNT(*) n FROM bookmark").fetchone()["n"] == 1
        assert conn.execute(
            "SELECT bookmark_id FROM karakeep_doc WHERE karakeep_id='kk-x'"
        ).fetchone()["bookmark_id"] == 1

    async def test_no_provider_stores_rows_and_reports_zero_vectors(self, mock_settings):
        """Degraded visibly: the rows are there, the report says embedded 0."""
        conn = open_db(":memory:")
        rep = await kk.add_documents(
            conn, DOCS, provider=None, settings=mock_settings, embed=False
        )
        assert rep["stored"] == 3
        assert rep["embedded"] == 0
        assert conn.execute("SELECT COUNT(*) n FROM karakeep_doc").fetchone()["n"] == 3


class TestSearch:
    async def test_hits_come_back_as_karakeep_ids_with_scores(self, bridged):
        conn, provider, st, _ = bridged
        out = await kk.search_documents(
            conn, {"query": "postgres index", "limit": 5}, provider=provider, settings=st
        )
        assert out["engine"] == "facetmark:full"
        assert out["hits"], "expected at least one hit"
        assert all(h["id"].startswith("kk-") for h in out["hits"])
        assert all(isinstance(h["score"], float) for h in out["hits"])
        assert out["processingTimeMs"] >= 0

    async def test_a_user_filter_removes_other_users_documents(self, bridged):
        conn, provider, st, _ = bridged
        out = await kk.search_documents(
            conn,
            {"query": "rust async pinning", "limit": 10,
             "filter": [{"type": "eq", "field": "userId", "value": "u1"}]},
            provider=provider, settings=st,
        )
        assert "kk-3" not in [h["id"] for h in out["hits"]]

    async def test_an_id_filter_restricts_to_the_listed_documents(self, bridged):
        conn, provider, st, _ = bridged
        out = await kk.search_documents(
            conn,
            {"query": "index", "limit": 10,
             "filter": [{"type": "in", "field": "id", "values": ["kk-2"]}]},
            provider=provider, settings=st,
        )
        assert [h["id"] for h in out["hits"]] in ([], ["kk-2"])

    async def test_an_empty_query_is_browsing_and_answers_chronologically(self, bridged):
        conn, provider, st, _ = bridged
        out = await kk.search_documents(
            conn, {"query": "", "limit": 10}, provider=provider, settings=st
        )
        assert out["engine"] == "chronological"
        assert [h["id"] for h in out["hits"]] == ["kk-2", "kk-3", "kk-1"]
        assert out["totalHits"] == 3

    async def test_ascending_sort_is_honoured_when_browsing(self, bridged):
        conn, provider, st, _ = bridged
        out = await kk.search_documents(
            conn,
            {"query": "", "limit": 10,
             "sort": [{"field": "createdAt", "order": "asc"}]},
            provider=provider, settings=st,
        )
        assert [h["id"] for h in out["hits"]] == ["kk-1", "kk-3", "kk-2"]

    async def test_offset_pages_without_losing_the_total(self, bridged):
        conn, provider, st, _ = bridged
        out = await kk.search_documents(
            conn, {"query": "", "limit": 1, "offset": 1}, provider=provider, settings=st
        )
        assert [h["id"] for h in out["hits"]] == ["kk-3"]
        assert out["totalHits"] == 3

    async def test_limit_is_clamped_not_trusted(self, bridged):
        conn, provider, st, _ = bridged
        out = await kk.search_documents(
            conn, {"query": "", "limit": 10_000}, provider=provider, settings=st
        )
        assert len(out["hits"]) == 3


class TestDeleteAndClear:
    async def test_delete_removes_the_document_and_its_rows(self, bridged):
        conn, _, _, _ = bridged
        rep = kk.delete_documents(conn, ["kk-2"])
        assert rep == {"requested": 1, "removed": 1, "kept_not_ours": 0}
        assert conn.execute("SELECT COUNT(*) n FROM bookmark").fetchone()["n"] == 2
        assert conn.execute("SELECT COUNT(*) n FROM karakeep_doc").fetchone()["n"] == 2

    async def test_deleting_an_unknown_id_is_not_an_error(self, bridged):
        conn, _, _, _ = bridged
        assert kk.delete_documents(conn, ["nope"])["removed"] == 0

    async def test_delete_never_removes_a_bookmark_it_did_not_create(self, mock_settings):
        conn = open_db(":memory:")
        from facetmark.normalize import normalize_url

        h = normalize_url("https://example.com/x").hash
        conn.execute(
            "INSERT INTO bookmark(id,url,url_norm,url_hash,title,source,date_added,"
            "created_at,updated_at) VALUES(1,'https://example.com/x','https://example.com/x',"
            "?,'from browser','netscape_html',1,1,1)", (h,),
        )
        conn.commit()
        await kk.add_documents(
            conn, [{"id": "kk-x", "url": "https://example.com/x", "title": "t"}],
            provider=MockProvider(mock_settings), settings=mock_settings,
        )
        rep = kk.delete_documents(conn, ["kk-x"])
        assert rep["kept_not_ours"] == 1
        assert conn.execute("SELECT COUNT(*) n FROM bookmark").fetchone()["n"] == 1

    async def test_clear_index_removes_only_karakeep_owned_rows(self, mock_settings):
        conn = open_db(":memory:")
        from facetmark.normalize import normalize_url

        h = normalize_url("https://example.com/keep").hash
        conn.execute(
            "INSERT INTO bookmark(id,url,url_norm,url_hash,title,source,date_added,"
            "created_at,updated_at) VALUES(99,'https://example.com/keep',"
            "'https://example.com/keep',?,'browser row','netscape_html',1,1,1)", (h,),
        )
        conn.commit()
        await kk.add_documents(conn, DOCS, provider=MockProvider(mock_settings),
                              settings=mock_settings)
        rep = kk.clear_index(conn)
        assert rep["purged_bookmarks"] == 3
        assert rep["cleared_mappings"] == 3
        left = conn.execute("SELECT title FROM bookmark").fetchall()
        assert [r["title"] for r in left] == ["browser row"]
        assert conn.execute("SELECT COUNT(*) n FROM karakeep_doc").fetchone()["n"] == 0


class TestPlumbing:
    def test_ensure_tables_is_idempotent(self, conn):
        kk.ensure_tables(conn)
        kk.ensure_tables(conn)
        assert conn.execute(
            "SELECT COUNT(*) n FROM sqlite_master WHERE name='karakeep_doc'"
        ).fetchone()["n"] == 1

    def test_a_library_that_never_talks_to_karakeep_has_no_bridge_table(self, conn):
        assert conn.execute(
            "SELECT COUNT(*) n FROM sqlite_master WHERE name='karakeep_doc'"
        ).fetchone()["n"] == 0

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("2024-03-01T10:00:00Z", 1709287200),
            ("2024-03-01T10:00:00+00:00", 1709287200),
            (1735689600, 1735689600),
            (1735689600000, 1735689600),
            ("", None),
            (None, None),
            ("not a date", None),
        ],
    )
    def test_timestamp_parsing(self, raw, expected):
        assert kk._parse_ts(raw) == expected

    def test_filters_are_split_into_user_and_ids(self):
        user, ids = kk._filters(
            {"filter": [
                {"type": "eq", "field": "userId", "value": "u9"},
                {"type": "in", "field": "id", "values": ["a", "b"]},
            ]}
        )
        assert (user, ids) == ("u9", ["a", "b"])

    def test_an_unknown_filter_field_is_ignored_rather_than_fatal(self):
        assert kk._filters({"filter": [{"type": "eq", "field": "nope", "value": "x"}]}) == ("", [])

    async def test_mapping_stats_report_body_coverage(self, bridged):
        conn, _, _, _ = bridged
        st = kk.mapping_stats(conn)
        assert st == {"documents": 3, "users": 2, "with_body": 3}
