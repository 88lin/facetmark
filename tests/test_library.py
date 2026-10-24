"""Bookmark edits keep the saved record and its searchable state consistent."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from facetmark import library, service
from facetmark.api import create_app
from facetmark.bridges.karakeep import ensure_tables
from facetmark.config import Settings
from facetmark.db import ensure_vec_tables, open_db, upsert_content_vector, upsert_intent_vector
from facetmark.fetch.store import enqueue_for_browser, store_body
from facetmark.importers import detect_and_parse
from facetmark.search.lexical import lexical_search

BASE = "/admin/library"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FACETMARK_DATA_DIR", str(tmp_path))
    settings = Settings(data_dir=tmp_path, use_mock_provider=True, embed_dim=8,
                        privacy_excluded_domains=("private.example",))
    with TestClient(create_app(settings), client=("127.0.0.1", 40404)) as c:
        c.headers["Authorization"] = f"Bearer {c.app.state.fm.token}"
        yield c


def create(client, name="page", **fields):
    response = client.post(f"{BASE}/bookmarks", json={
        "url": f"https://example.org/{name}", "title": name, **fields,
    })
    assert response.status_code == 200, response.text
    return response.json()["bookmark_id"]


def add_derived(client, bid):
    state = client.app.state.fm
    conn = state.conn
    store_body(conn, bid, body="Old body marker BODYTOKEN")
    conn.execute("INSERT INTO enrichment(bookmark_id,summary,topics,source_hash) VALUES(?,?,?,?)",
                 (bid, "STALESUMMARY", '["STALETOPIC"]', "old"))
    intent = conn.execute("INSERT INTO intent_query(bookmark_id,text,kept) VALUES(?,?,1)",
                          (bid, "STALEINTENT")).lastrowid
    ensure_vec_tables(conn, 8, state.settings.embed_model)
    upsert_content_vector(conn, bid, [1.0] * 8, text_hash="old")
    upsert_intent_vector(conn, intent, [1.0] * 8)
    enqueue_for_browser(conn, bid, reason="test")
    conn.execute("INSERT INTO health(bookmark_id,checked_at,verdict) VALUES(?,1,'ok')", (bid,))
    service.record_open(conn, bid)
    service.sync_fts_tag_refresh(conn, bid)
    return intent


def test_edit_refreshes_search_and_retires_derived_without_losing_body(client):
    bid = create(client, "OLDTITLE", folder="read/write", tags=["OLDTAG"])
    intent = add_derived(client, bid)
    conn = client.app.state.fm.conn
    assert bid in lexical_search(conn, "STALESUMMARY")
    response = client.patch(f"{BASE}/bookmarks/{bid}", json={
        "title": "NEWTITLE", "tags": [" NEWTAG ", "NEWTAG"], "folder": "new/folder",
    })
    assert response.status_code == 200, response.text
    assert response.json()["tags"] == ["NEWTAG"]
    assert response.json()["folder_depth"] == 1
    for word in ("OLDTITLE", "OLDTAG", "STALESUMMARY", "STALETOPIC"):
        assert bid not in lexical_search(conn, word)
    for word in ("NEWTITLE", "NEWTAG", "BODYTOKEN"):
        assert bid in lexical_search(conn, word)
    assert conn.execute("SELECT 1 FROM vec_intent WHERE intent_id=?", (intent,)).fetchone() is None
    for table in ("vec_content", "vec_content_meta", "intent_query", "enrichment"):
        assert conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
    assert conn.execute("SELECT body_text FROM content WHERE bookmark_id=?", (bid,)).fetchone()[0]
    assert response.json()["open_count"] == 1


def test_url_change_clears_previous_page_data_and_rechecks_privacy(client):
    bid = create(client)
    add_derived(client, bid)
    other = create(client, "neighbor")
    conn = client.app.state.fm.conn
    conn.execute("INSERT INTO edge(src,dst,kind) VALUES(?,?,'same_domain')", (bid, other))
    response = client.patch(f"{BASE}/bookmarks/{bid}", json={
        "url": "https://mail.private.example/new?utm_source=edited",
    })
    assert response.status_code == 200, response.text
    got = response.json()
    assert got["privacy_skipped"] is True
    assert got["open_count"] == 0 and got["last_opened_at"] is None
    assert got["summary"] == ""
    stored = conn.execute("SELECT host,domain,url_norm FROM bookmark WHERE id=?", (bid,)).fetchone()
    assert tuple(stored) == ("mail.private.example", "private.example", "https://mail.private.example/new")
    for table in ("content", "health", "fetch_queue", "interaction", "edge"):
        assert conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
    assert bid not in lexical_search(conn, "BODYTOKEN")


def test_tag_only_or_noop_edit_keeps_current_ai_work(client):
    bid = create(client, tags=["OLDTAG"])
    add_derived(client, bid)
    response = client.patch(f"{BASE}/bookmarks/{bid}", json={"tags": ["NEWTAG"]})
    assert response.status_code == 200
    assert response.json()["summary"] == "STALESUMMARY"
    conn = client.app.state.fm.conn
    assert conn.execute("SELECT count(*) FROM vec_content").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM vec_intent").fetchone()[0] == 1
    assert bid not in lexical_search(conn, "OLDTAG")
    assert bid in lexical_search(conn, "NEWTAG")
    response = client.patch(f"{BASE}/bookmarks/{bid}", json={"title": "page", "tags": ["NEWTAG"]})
    assert response.json()["updated"] is False
    assert conn.execute("SELECT count(*) FROM enrichment").fetchone()[0] == 1


def test_duplicate_create_and_url_edit_are_conflicts_without_tag_merge(client):
    first = create(client, "duplicate", tags=["keep"])
    other = create(client, "other", tags=["unchanged"])
    duplicate = client.post(f"{BASE}/bookmarks", json={
        "url": "http://www.example.org/duplicate/?utm_source=test", "tags": ["bad"],
    })
    assert duplicate.status_code == 409
    response = client.patch(f"{BASE}/bookmarks/{other}", json={
        "url": "https://example.org/duplicate", "title": "should not change",
    })
    assert response.status_code == 409
    assert response.json()["detail"]["bookmark_id"] == first
    conn = client.app.state.fm.conn
    assert service.bookmark_record(conn, first)["tags"] == ["keep"]
    assert service.bookmark_record(conn, other)["title"] == "other"


@pytest.mark.parametrize("payload", [
    {"url": ""}, {"url": "not-an-address"}, {"url": "javascript:alert(1)"},
    {"url": "https://example.org:999999/"}, {"url": "https://exa mple.org/"},
    {"url": "https://name:secret@example.org/"}, {"url": "https://name@example.org/"},
    {"url": "https://@example.org/"},
    {"url": "https://example.org/", "tags": [" "]},
    {"url": "https://example.org/", "tags": ["x"] * 101},
    {"url": "https://example.org/", "source": "karakeep"},
])
def test_create_rejects_invalid_payloads(client, payload):
    assert client.post(f"{BASE}/bookmarks", json=payload).status_code == 422
    assert client.app.state.fm.conn.execute("SELECT count(*) FROM bookmark").fetchone()[0] == 0


def test_request_constraints_and_missing_ids_do_not_partially_mutate(client):
    bid = create(client, tags=["keep"])
    for payload in ({}, {"title": None}, {"folder": None}, {"url": None}, {"tags": None}):
        assert client.patch(f"{BASE}/bookmarks/{bid}", json=payload).status_code == 422
    for ids in ([], [0], [-1], [True], ["1"], [2**63], [bid] * 1001):
        assert client.post(f"{BASE}/bulk", json={"ids": ids, "action": "delete"}).status_code == 422
    response = client.post(f"{BASE}/bulk", json={"ids": [bid, 999], "action": "delete"})
    assert response.status_code == 404
    assert client.app.state.fm.conn.execute("SELECT count(*) FROM bookmark").fetchone()[0] == 1


def test_url_edit_rejects_credentials_without_replacing_cached_page(client):
    bid = create(client)
    add_derived(client, bid)
    response = client.patch(f"{BASE}/bookmarks/{bid}", json={
        "url": "https://name:secret@example.org/new", "title": "must not replace",
    })
    assert response.status_code == 422
    record = service.bookmark_record(client.app.state.fm.conn, bid, include_body=True)
    assert record["title"] == "page"
    assert record["url"] == "https://example.org/page"
    assert record["body_text"] == "Old body marker BODYTOKEN"
    assert record["summary"] == "STALESUMMARY"


def test_bulk_moves_tags_merges_and_rolls_back_if_any_row_exceeds_limit(client):
    first = create(client, "first", tags=["old"])
    full = create(client, "full", tags=[f"t{i}" for i in range(100)])
    response = client.post(f"{BASE}/bulk", json={
        "ids": [first, full], "action": "tag-add", "tags": ["overflow"],
    })
    assert response.status_code == 422
    conn = client.app.state.fm.conn
    assert service.bookmark_record(conn, first)["tags"] == ["old"]
    response = client.post(f"{BASE}/bulk", json={
        "ids": [first, first, full], "action": "move", "folder": "literal/path",
    })
    assert response.json() == {"updated": 2, "deleted": 0, "ids": [first, full]}
    response = client.post(f"{BASE}/bulk", json={
        "ids": [first], "action": "tag-add", "tags": ["old", "new"],
    })
    assert response.status_code == 200
    assert service.bookmark_record(conn, first)["tags"] == ["old", "new"]
    client.post(f"{BASE}/bulk", json={"ids": [first], "action": "tag-remove", "tags": ["old"]})
    assert first not in lexical_search(conn, "old")


@pytest.mark.parametrize("ownership", ["source", "adopted"])
def test_karakeep_owned_or_adopted_rows_block_entire_mutation(client, ownership):
    ordinary = create(client, "ordinary", folder="shared")
    owned = create(client, "owned", folder="shared")
    conn = client.app.state.fm.conn
    if ownership == "source":
        conn.execute("UPDATE bookmark SET source='karakeep' WHERE id=?", (owned,))
    else:
        ensure_tables(conn)
        conn.execute("INSERT INTO karakeep_doc VALUES('remote','user',?,1)", (owned,))
    for route, payload in (("bulk", {"action": "delete", "ids": [ordinary, owned]}),
                           ("taxonomy", {"kind": "folder", "action": "rename",
                                         "name": "shared", "new_name": "changed"})):
        assert client.post(f"{BASE}/{route}", json=payload).status_code == 409
    assert client.patch(f"{BASE}/bookmarks/{owned}", json={"title": "changed"}).status_code == 409
    record = client.get(f"/bookmark/{owned}").json()
    assert record["managed_externally"] is True
    assert record["source"] == ("karakeep" if ownership == "source" else "api")
    assert client.get(f"/bookmark/{ordinary}").json()["managed_externally"] is False
    assert conn.execute("SELECT count(*) FROM bookmark WHERE folder='shared'").fetchone()[0] == 2
    assert client.post(f"{BASE}/export", json={"ids": [owned]}).status_code == 200


def test_delete_removes_virtual_indexes_dependents_and_repairs_sessions(client):
    bid = create(client, "delete")
    other = create(client, "survivor")
    add_derived(client, bid)
    conn = client.app.state.fm.conn
    conn.execute("INSERT INTO session VALUES(10,1,2,2,'pair','temporal',600)")
    conn.execute("INSERT INTO session VALUES(11,1,1,1,'single','folder',NULL)")
    conn.executemany("INSERT INTO bookmark_session VALUES(?,?)", [(bid, 10), (other, 10), (bid, 11)])
    conn.executemany("INSERT INTO edge VALUES(?,?,'session',1)", [(bid, other), (other, bid)])
    response = client.delete(f"{BASE}/bookmarks/{bid}")
    assert response.json() == {"deleted": 1, "ids": [bid]}
    for table in ("content", "enrichment", "intent_query", "vec_content", "vec_content_meta",
                  "vec_intent", "fetch_queue", "health", "interaction", "edge"):
        assert conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0, table
    for table in ("fts_tri", "fts_seg"):
        assert conn.execute(f"SELECT count(*) FROM {table} WHERE rowid=?", (bid,)).fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM session").fetchone()[0] == 1
    session = conn.execute("SELECT * FROM session WHERE id=10").fetchone()
    date = conn.execute("SELECT date_added FROM bookmark WHERE id=?", (other,)).fetchone()[0]
    assert (session["size"], session["started_at"], session["ended_at"]) == (1, date, date)
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_taxonomy_exact_folder_names_and_tag_merge_preserve_bookmarks(client):
    exact = create(client, "exact", folder="read/write", tags=["old", "new"])
    child_like = create(client, "similar", folder="read/write/deeper", tags=["old"])
    response = client.post(f"{BASE}/taxonomy", json={
        "kind": "folder", "action": "delete", "name": "read/write",
    })
    assert response.json()["ids"] == [exact]
    conn = client.app.state.fm.conn
    assert service.bookmark_record(conn, child_like)["folder"] == "read/write/deeper"
    client.post(f"{BASE}/taxonomy", json={
        "kind": "tag", "action": "rename", "name": "old", "new_name": "new",
    })
    assert service.bookmark_record(conn, exact)["tags"] == ["new"]
    assert service.bookmark_record(conn, child_like)["tags"] == ["new"]
    client.post(f"{BASE}/taxonomy", json={"kind": "tag", "action": "delete", "name": "new"})
    assert service.bookmark_record(conn, exact)["tags"] == []
    assert conn.execute("SELECT count(*) FROM bookmark").fetchone()[0] == 2


def test_move_repairs_folder_sessions_and_uses_known_destination_depth(client):
    bid = create(client, "move", folder="old")
    peer = create(client, "peer", folder="old")
    destination = create(client, "destination", folder="Imported/Nested")
    conn = client.app.state.fm.conn
    conn.execute("UPDATE bookmark SET folder_depth=2 WHERE id=?", (destination,))
    conn.execute("INSERT INTO session VALUES(10,1,2,2,'folder','folder',NULL)")
    conn.executemany("INSERT INTO bookmark_session VALUES(?,10)", [(bid,), (peer,)])
    conn.executemany("INSERT INTO edge VALUES(?,?,'session',1)", [(bid, peer), (peer, bid)])
    response = client.post(f"{BASE}/bulk", json={
        "ids": [bid], "action": "move", "folder": "Imported/Nested",
    })
    assert response.status_code == 200
    assert service.bookmark_record(conn, bid)["folder_depth"] == 2
    assert service.bookmark_record(conn, bid)["sessions"] == []
    assert conn.execute("SELECT size FROM session WHERE id=10").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM edge WHERE kind='session'").fetchone()[0] == 0


def test_mutations_block_running_jobs_and_require_local_authenticated_admin(client, monkeypatch, tmp_path):
    bid = create(client)
    state = client.app.state.fm
    monkeypatch.setattr(type(state.jobs), "running", property(lambda self: True))
    for method, route, payload in (
        ("post", "/bookmarks", {"url": "https://other.example/"}),
        ("patch", f"/bookmarks/{bid}", {"title": "new"}),
        ("delete", f"/bookmarks/{bid}", None),
        ("post", "/bulk", {"ids": [bid], "action": "delete"}),
        ("post", "/taxonomy", {"kind": "tag", "action": "delete", "name": "tag"}),
    ):
        response = client.request(method, BASE + route, json=payload)
        assert response.status_code == 409
    # Read-only exports stay available while a job is running.
    assert client.post(f"{BASE}/export", json={}).status_code == 200
    client.headers.pop("Authorization")
    assert client.post(f"{BASE}/export", json={}).status_code == 401
    with TestClient(create_app(Settings(data_dir=tmp_path / "remote", use_mock_provider=True)),
                    client=("192.0.2.1", 40404)) as remote:
        remote.headers["Authorization"] = f"Bearer {remote.app.state.fm.token}"
        assert remote.post(f"{BASE}/bookmarks", json={"url": "https://example.org/"}).status_code == 403


def test_json_export_keeps_reading_copy_and_roundtrips_scoped_metadata(client):
    first = create(client, "first", title="中文 <title>", folder="read/write", tags=["tool", "a,b"])
    second = create(client, "second", folder="read/write", tags=["other"])
    create(client, "outside", folder="elsewhere", tags=["tool"])
    add_derived(client, first)
    response = client.post(f"{BASE}/export", json={
        "format": "json", "ids": [first, second], "filters": {"folder": "read/write"}, "query": "tag:tool",
    })
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert 'attachment; filename="facetmark-' in response.headers["content-disposition"]
    assert response.headers["cache-control"] == "no-store"
    payload = response.json()
    assert payload["facetmark"]["count"] == 1
    assert payload["facetmark"]["full"] is True
    assert payload["bookmarks"][0]["content"]["body_text"] == "Old body marker BODYTOKEN"
    assert payload["bookmarks"][0]["derived"]["summary"] == "STALESUMMARY"
    assert payload["bookmarks"][0]["derived"]["topics"] == ["STALETOPIC"]
    assert "STALEINTENT" not in response.text
    assert client.app.state.fm.token not in response.text
    fresh = open_db(":memory:")
    try:
        stats = service.import_content(fresh, response.text, settings=client.app.state.fm.settings)
        assert stats["inserted"] == 1
        record = fresh.execute("SELECT title,folder,folder_depth,tags FROM bookmark").fetchone()
        assert tuple(record) == ("中文 <title>", "read/write", 1, '["tool", "a,b"]')
        # Full exports keep text for portable reading. Import deliberately
        # rebuilds cached bodies and AI data rather than restoring old indexes.
        assert fresh.execute("SELECT count(*) FROM content").fetchone()[0] == 0
        assert fresh.execute("SELECT count(*) FROM enrichment").fetchone()[0] == 0
    finally:
        fresh.close()


def test_full_export_includes_cached_text_without_summary_and_local_private_pages(client):
    bid = create(client, "private", url="https://private.example/", tags=["local"])
    state = client.app.state.fm
    body = "A private saved page\n\n" + "Entire page content. " * 300
    store_body(state.conn, bid, body=body, extractor="extension", channel="b")
    state.conn.execute("UPDATE content SET error='sensitive diagnostic' WHERE bookmark_id=?", (bid,))
    exported = client.post(f"{BASE}/export", json={"ids": [bid]}).json()["bookmarks"][0]
    assert exported["content"]["body_text"] == body
    assert exported["content"]["char_count"] == len(body)
    assert exported["derived"]["summary"] == ""
    assert exported["derived"]["chars"] == len(body)
    assert "error" not in exported["content"]
    # The shared CLI full export and UI use the same complete reading schema.
    cli = service.export_bookmarks(state.conn, full=True)["bookmarks"][0]
    assert cli["content"] == exported["content"]
    assert cli["derived"] == exported["derived"]


def test_export_with_long_filter_header_is_still_recognized_for_reimport(client):
    bid = create(client, "long-filter", folder="A" * 1800)
    response = client.post(f"{BASE}/export", json={
        "ids": [bid], "filters": {"folder": "A" * 1800}, "query": " " * 400,
    })
    assert response.status_code == 200
    assert '"bookmarks"' not in response.text[:2048]
    parsed = detect_and_parse(response.text)
    assert parsed.source == "facetmark_json"
    assert len(parsed.bookmarks) == 1
    assert parsed.bookmarks[0].folder == "A" * 1800


def test_html_export_escapes_content_preserves_regular_tags_and_can_be_reimported(client):
    bid = create(client, title='中文 <script> & "quote"', folder="read/write", tags=["tool", "工具", 'a&b "tag"'])
    add_derived(client, bid)
    response = client.post(f"{BASE}/export", json={"format": "html", "ids": [bid]})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<script>" not in response.text
    assert "BODYTOKEN" not in response.text and "STALESUMMARY" not in response.text
    parsed = detect_and_parse(response.text)
    assert not parsed.warnings
    assert len(parsed.bookmarks) == 1
    record = parsed.bookmarks[0]
    assert record.title == '中文 <script> & "quote"'
    assert record.tags == ["tool", "工具", 'a&b "tag"']
    assert record.folder_path == ["read/write"]


def test_export_refuses_ambiguous_or_stale_selections(client):
    create(client)
    for payload in ({"query": "some ranked search"}, {"query": "added:not-a-date"},
                    {"ids": []}, {"ids": [999999]}, {"format": "csv"}):
        assert client.post(f"{BASE}/export", json=payload).status_code in {404, 422}
    response = client.post(f"{BASE}/export", json={"filters": {"folder": "no matches"}})
    assert response.status_code == 200
    assert response.json()["bookmarks"] == []


def test_helpers_participate_in_callers_transaction_without_implicit_commit(conn, settings):
    conn.execute("BEGIN")
    record = library.create_bookmark(conn, library.CreateBookmark(url="https://example.org/transaction"),
                                     settings=settings)
    library.update_bookmark(conn, record["bookmark_id"], library.EditBookmark(title="changed"),
                            settings=settings)
    assert conn.in_transaction
    conn.rollback()
    assert conn.execute("SELECT count(*) FROM bookmark").fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM fts_tri").fetchone()[0] == 0
