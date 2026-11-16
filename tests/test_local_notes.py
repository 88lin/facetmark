"""Personal reading notes remain local, persistent and independently editable."""
from __future__ import annotations

import json

import pytest

from facetmark import service
from facetmark.db import open_db, set_meta
from facetmark.fetch.store import store_body
from facetmark.importers import import_bookmarks
from tests.test_library import BASE, create
from tests.test_library import client as client

NOTE = "cormorantnotebook\n我保存这篇文章的原因。\n  缩进与换行应完整保留。"
URL = "https://local-notes.example/read"


def import_note(conn, settings, note=NOTE):
    payload = {"facetmark": {"version": 2}, "bookmarks": [{"url": URL, "title": "A saved reading page", "note": note}]}
    result = import_bookmarks(conn, content=json.dumps(payload, ensure_ascii=False), settings=settings)
    assert result.inserted + result.updated == 1
    return conn.execute("SELECT id FROM bookmark WHERE url=?", (URL,)).fetchone()[0]


@pytest.mark.parametrize("refresh", ["body", "index", "reimport"])
def test_imported_notes_remain_searchable_after_body_index_and_empty_reimport(conn, settings, refresh):
    bid = import_note(conn, settings)
    assert [hit.bookmark_id for hit in service.quick_search(conn, "cormorantnotebook", settings=settings).hits] == [bid]
    if refresh == "body":
        store_body(conn, bid, body="A newly saved page body", channel="extension")
        conn.commit()
    elif refresh == "index":
        service.sync_fts_tag_refresh(conn, bid)
    else:
        assert import_note(conn, settings, "") == bid
    assert [hit.bookmark_id for hit in service.quick_search(conn, "cormorantnotebook", settings=settings).hits] == [bid]


def test_full_reading_returns_the_complete_personal_note(conn, settings):
    bid = import_note(conn, settings)
    assert service.bookmark_record(conn, bid, settings=settings, include_body=True).get("note") == NOTE


def test_portable_full_export_retains_notes_for_a_real_roundtrip(conn, settings, tmp_path):
    import_note(conn, settings)
    result = service.export_bookmarks(conn, full=True)
    assert result["bookmarks"][0].get("note") == NOTE
    restored = open_db(tmp_path / "restored.db")
    try:
        report = import_bookmarks(restored, content=json.dumps(result, ensure_ascii=False), settings=settings)
        assert report.inserted == 1
        bid = restored.execute("SELECT id FROM bookmark").fetchone()[0]
        assert service.bookmark_record(restored, bid, include_body=True, settings=settings)["note"] == NOTE
        assert [hit.bookmark_id for hit in service.quick_search(restored, "cormorantnotebook", settings=settings).hits] == [bid]
    finally:
        restored.close()


def note_path(bid):
    return f"{BASE}/bookmarks/{bid}/note"


def write(client, bid, note=NOTE, revision=0, request_id="save-note"):
    return client.patch(note_path(bid), json={"note": note, "base_revision": revision, "request_id": request_id})


def test_saved_note_preserves_whitespace_is_independent_and_has_a_receipt(client):
    bid = create(client)
    first = write(client, bid, "  " + NOTE + "\n  ")
    assert first.status_code == 200, first.text
    assert first.json()["note"] == "  " + NOTE + "\n  "
    assert first.json()["revision"] == 1
    assert client.get(f"{BASE}/operations/save-note").json()["result"] == first.json()
    assert client.get(f"/bookmark/{bid}?body=true").json()["note"] == first.json()["note"]
    assert "note" not in client.get(f"/bookmark/{bid}").json()
    conn = client.app.state.fm.conn
    assert conn.execute("SELECT count(*) FROM enrichment").fetchone()[0] == 0
    assert conn.execute("SELECT title FROM bookmark WHERE id=?", (bid,)).fetchone()[0] == "page"


def test_note_replay_does_not_overwrite_a_newer_note_or_a_different_page(client):
    bid = create(client)
    first = write(client, bid)
    assert first.status_code == 200, first.text
    later = write(client, bid, "A later note", 1, "later-note")
    assert later.status_code == 200, later.text
    assert write(client, bid).json() == first.json()
    assert client.get(note_path(bid)).json()["note"] == "A later note"
    assert write(client, create(client, "other")).status_code == 409
    assert write(client, bid, "different same ID").status_code == 409


def test_note_conflict_retains_the_saved_version_and_never_silently_overwrites(client):
    bid = create(client)
    assert write(client, bid).status_code == 200
    second = write(client, bid, "Another window's draft", 0, "conflicting-note")
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "note_conflict"
    assert second.json()["detail"]["current"]["note"] == NOTE
    assert client.get(f"{BASE}/operations/conflicting-note").status_code == 404
    assert write(client, bid, "Another window's draft", 1, "reviewed-note").status_code == 200


def test_note_clear_survives_reimports_and_a_full_backup(client, settings, tmp_path):
    bid = create(client)
    assert write(client, bid).status_code == 200
    assert write(client, bid, "", 1, "clear-note").status_code == 200
    conn = client.app.state.fm.conn
    payload = {"facetmark": {"version": 2}, "bookmarks": [{"url": "https://example.org/page", "note": NOTE}]}
    import_bookmarks(conn, content=json.dumps(payload), settings=settings)
    assert client.get(note_path(bid)).json()["note"] == ""
    exported = service.export_bookmarks(conn, full=True)
    assert exported["bookmarks"][0]["note_saved"] is True
    restored = open_db(tmp_path / "cleared.db")
    try:
        import_bookmarks(restored, content=json.dumps(exported), settings=settings)
        import_bookmarks(restored, content=json.dumps(payload), settings=settings)
        assert service.bookmark_record(restored, 1, include_body=True, settings=settings)["note"] == ""
    finally:
        restored.close()


def test_note_and_fts_roll_back_if_the_receipt_fails(client):
    bid = create(client)
    conn = client.app.state.fm.conn
    conn.execute("CREATE TRIGGER fail_note_receipt BEFORE INSERT ON library_operation "
                 "BEGIN SELECT RAISE(ABORT,'synthetic receipt failure'); END")
    result = write(client, bid)
    assert result.status_code == 500, result.text
    assert client.get(note_path(bid)).json()["note"] == ""
    assert client.get(f"{BASE}/operations/save-note").status_code == 404
    assert not service.quick_search(conn, "cormorantnotebook", settings=client.app.state.fm.settings).hits


def test_notes_remain_editable_during_processing_and_for_external_pages(client):
    bid = create(client)
    state = client.app.state.fm
    state.conn.execute("UPDATE bookmark SET source='karakeep',privacy_skipped=1 WHERE id=?", (bid,))
    state.model_users += 1
    try:
        result = write(client, bid)
        assert result.status_code == 200, result.text
        assert result.json()["note"] == NOTE
        assert client.patch(f"{BASE}/bookmarks/{bid}", json={"title": "Blocked metadata change"}).status_code == 409
    finally:
        state.model_users -= 1


@pytest.mark.parametrize("fields", [{"note": None}, {"note": "x" * 60_001}, {"note": "a\x00b"},
                                   {"base_revision": True}, {"base_revision": -1}, {"request_id": None}])
def test_invalid_note_writes_leave_saved_content_untouched(client, fields):
    bid = create(client)
    result = client.patch(note_path(bid), json={"note": NOTE, "base_revision": 0, "request_id": "invalid-note", **fields})
    assert result.status_code == 422, result.text
    assert client.get(note_path(bid)).json()["revision"] == 0


def test_late_note_retry_after_deletion_never_recreates_a_page(client):
    bid = create(client)
    first = write(client, bid)
    assert first.status_code == 200
    assert client.delete(f"{BASE}/bookmarks/{bid}").status_code == 200
    assert write(client, bid).json() == first.json()
    assert client.get(note_path(bid)).status_code == 404
    assert client.app.state.fm.conn.execute("SELECT count(*) FROM bookmark_note").fetchone()[0] == 0


def test_upgrade_preserves_unmatched_old_import_text_without_inventing_a_note(tmp_path, settings):
    path = tmp_path / "old-notes.db"
    previous = open_db(path)
    bid = import_note(previous, settings)
    previous.execute("DROP TABLE bookmark_note")
    previous.execute("UPDATE fts_tri SET extra=? WHERE rowid=?", ("Folder " + NOTE + " old-tag", bid))
    set_meta(previous, "schema_version", "14")
    previous.commit()
    previous.close()
    upgraded = open_db(path)
    try:
        value = service.bookmark_record(upgraded, bid, settings=settings, include_body=True)
        assert value["note"] == ""
        assert value["legacy_note_text"] == "Folder " + NOTE + " old-tag"
        service.sync_fts_tag_refresh(upgraded, bid)
        assert service.quick_search(upgraded, "cormorantnotebook", settings=settings).hits[0].bookmark_id == bid
        assert service.export_bookmarks(upgraded, full=True)["bookmarks"][0]["legacy_note_text"] == value["legacy_note_text"]
    finally:
        upgraded.close()


def test_a_metadata_export_does_not_silently_include_personal_notes(conn, settings):
    import_note(conn, settings)
    assert "note" not in service.export_bookmarks(conn)["bookmarks"][0]
