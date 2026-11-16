"""Saved reading and recall vocabulary survive refresh and reimport.

Only an in-memory synthetic library is used. These exercise the shared paths
used by HTTP, CLI, MCP and the extension's body completion.
"""
from __future__ import annotations

import json

import pytest

from facetmark import service
from facetmark.fetch.store import store_body
from facetmark.importers import import_bookmarks


def enriched(conn, settings):
    bid = service.save_bookmark(conn, "https://contracts.test/page", title="originalneedle",
                                folder="researchcabinet", tags=["specialtag"], settings=settings)["bookmark_id"]
    conn.execute(
        "INSERT INTO enrichment(bookmark_id,ai_title,summary,topics,entities,key_points,basis,model) "
        "VALUES(?,?,?,?,?,?,?,?)",
        (bid, "magnesium", "astrophysics " * 80, '["optics"]', '["photometry"]',
         '["spectroscopy"]', "body", "synthetic"),
    )
    conn.commit()
    service.sync_fts_tag_refresh(conn, bid)
    return bid


@pytest.mark.parametrize("word", ["magnesium", "astrophysics", "optics", "specialtag"])
def test_body_refresh_preserves_saved_recall_vocabulary(conn, settings, word):
    bid = enriched(conn, settings)
    assert service.quick_search(conn, word, settings=settings).hits
    store_body(conn, bid, body="New saved source text", channel="extension")
    conn.commit()
    assert [hit.bookmark_id for hit in service.quick_search(conn, word, settings=settings).hits] == [bid]


def test_reading_request_contains_the_complete_saved_summary(conn, settings):
    bid = enriched(conn, settings)
    compact = service.bookmark_record(conn, bid, settings=settings)
    reading = service.bookmark_record(conn, bid, settings=settings, include_body=True)
    assert len(compact["summary"]) <= service.SUMMARY_CHARS
    assert reading["summary"] == ("astrophysics " * 80).strip()


def test_reimport_without_a_title_preserves_the_searchable_local_title(conn, settings):
    bid = enriched(conn, settings)
    payload = {"facetmark": {"version": 1}, "bookmarks": [{"url": "https://contracts.test/page", "title": ""}]}
    import_bookmarks(conn, content=json.dumps(payload), settings=settings)
    assert conn.execute("SELECT title FROM bookmark WHERE id=?", (bid,)).fetchone()[0] == "originalneedle"
    assert [hit.bookmark_id for hit in service.quick_search(conn, "originalneedle", settings=settings).hits] == [bid]
