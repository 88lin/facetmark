"""Collection writes and exports retain the user's original operation and scope."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from facetmark.api import create_app
from facetmark.config import Settings
from tests.test_library import BASE, create
from tests.test_library import client as client


def test_creation_replay_returns_its_original_result_without_overwriting_a_later_edit(client):
    body = {"url": "https://example.org/created-once", "title": "Original title", "request_id": "create-once"}
    first = client.post(f"{BASE}/bookmarks", json=body)
    assert first.status_code == 200, first.text
    bid = first.json()["bookmark_id"]
    assert client.patch(f"{BASE}/bookmarks/{bid}", json={"title": "A later edit"}).status_code == 200
    repeated = client.post(f"{BASE}/bookmarks", json=body)
    assert repeated.status_code == 200, repeated.text
    assert repeated.json() == first.json()
    assert client.get(f"/bookmark/{bid}").json()["title"] == "A later edit"
    assert client.app.state.fm.conn.execute("SELECT count(*) FROM bookmark").fetchone()[0] == 1
    conflict = client.post(f"{BASE}/bookmarks", json={**body, "url": "https://example.org/different"})
    assert conflict.status_code == 409


def test_edit_receipt_preserves_a_later_change_and_cannot_be_reused_for_another_record(client):
    bid = create(client, "edit-once")
    other = create(client, "another-record")
    body = {"title": "First saved edit", "request_id": "edit-once"}
    path = f"{BASE}/bookmarks/{bid}"
    first = client.patch(path, json=body)
    assert first.status_code == 200, first.text
    assert client.patch(path, json={"title": "Newer saved edit"}).status_code == 200
    assert client.patch(path, json=body).json() == first.json()
    assert client.get(f"/bookmark/{bid}").json()["title"] == "Newer saved edit"
    assert client.patch(f"{BASE}/bookmarks/{other}", json=body).status_code == 409
    assert client.get(f"/bookmark/{other}").json()["title"] == "another-record"
    assert client.patch(path, json={"request_id": "empty-edit"}).status_code == 422


def test_bulk_delete_receipt_survives_removed_records_and_never_applies_to_new_ids(client):
    ids = [create(client, "delete-one"), create(client, "delete-two")]
    keep = create(client, "keep")
    body = {"ids": ids, "action": "delete", "request_id": "delete-once"}
    first = client.post(f"{BASE}/bulk", json=body)
    assert first.status_code == 200, first.text
    assert client.post(f"{BASE}/bulk", json=body).json() == first.json()
    assert client.post(f"{BASE}/bulk", json={**body, "ids": [keep]}).status_code == 409
    assert client.get(f"/bookmark/{keep}").status_code == 200
    assert client.app.state.fm.conn.execute("SELECT count(*) FROM bookmark").fetchone()[0] == 1


def test_taxonomy_receipt_does_not_rename_a_new_category_with_the_old_name(client):
    bid = create(client, "original-category", folder="Old")
    body = {"kind": "folder", "action": "rename", "name": "Old", "new_name": "New", "request_id": "rename-once"}
    first = client.post(f"{BASE}/taxonomy", json=body)
    assert first.status_code == 200, first.text
    later = create(client, "new-old-category", folder="Old")
    assert client.post(f"{BASE}/taxonomy", json=body).json() == first.json()
    assert client.get(f"/bookmark/{bid}").json()["folder"] == "New"
    assert client.get(f"/bookmark/{later}").json()["folder"] == "Old"


def test_delete_endpoint_accepts_an_optional_delivery_id(client):
    bid = create(client, "single-delete")
    path = f"{BASE}/bookmarks/{bid}?request_id=single-delete-once"
    first = client.delete(path)
    assert first.status_code == 200, first.text
    assert client.delete(path).json() == first.json()


def test_deleting_the_last_bookmark_does_not_reassign_its_identity_to_new_content(client):
    old = create(client, "old-reference")
    conversation = client.post("/chat/conversations", json={"bookmark_ids": [old]}).json()
    assert client.delete(f"{BASE}/bookmarks/{old}").status_code == 200
    replacement = create(client, "different-content")
    assert replacement > old
    assert client.get(f"/bookmark/{old}").status_code == 404
    assert client.get(f"/chat/conversations/{conversation['id']}").json()["bookmark_ids"] == [old]


def test_mutation_and_receipt_commit_together(client):
    conn = client.app.state.fm.conn
    conn.execute("CREATE TRIGGER fail_library_receipt BEFORE INSERT ON library_operation "
                 "BEGIN SELECT RAISE(ABORT,'synthetic receipt failure'); END")
    # The application deliberately translates sqlite failures into an HTTP
    # error; the saved data and FTS must still roll back with the failed receipt.
    result = client.post(f"{BASE}/bookmarks", json={"url": "https://example.org/rollback", "request_id": "rollback-once"})
    assert result.status_code == 500, result.text
    assert "synthetic receipt failure" in result.json()["detail"]
    assert conn.execute("SELECT count(*) FROM bookmark").fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM library_operation").fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM fts_seg").fetchone()[0] == 0


def test_receipt_reads_and_replays_survive_restart_and_an_active_job(client):
    body = {"url": "https://example.org/reopened-receipt", "request_id": "reopened-once"}
    first = client.post(f"{BASE}/bookmarks", json=body)
    assert first.status_code == 200, first.text
    settings = Settings(data_dir=client.app.state.fm.settings.data_dir, use_mock_provider=True)
    with TestClient(create_app(settings), client=("127.0.0.1", 40405)) as reopened:
        reopened.headers["Authorization"] = "Bearer " + reopened.app.state.fm.token
        state = reopened.app.state.fm
        original_jobs = state.jobs
        class Busy:
            running = True
        state.jobs = Busy()
        try:
            receipt = reopened.get(f"{BASE}/operations/reopened-once")
            assert receipt.status_code == 200, receipt.text
            assert receipt.json()["result"] == first.json()
            assert reopened.post(f"{BASE}/bookmarks", json=body).json() == first.json()
            assert reopened.post(f"{BASE}/bookmarks", json={"url": "https://example.org/new-write"}).status_code == 409
            assert reopened.get(f"{BASE}/operations/never-written").status_code == 404
        finally:
            state.jobs = original_jobs


def test_export_matches_the_keyword_status_selection_and_exclusions_without_browser_ids(client):
    done = create(client, "SCOPETOKEN-done", folder="Chosen")
    failed = create(client, "SCOPETOKEN-failed", folder="Chosen")
    excluded = create(client, "SCOPETOKEN-excluded", folder="Chosen")
    unrelated = create(client, "Other-title", folder="Chosen")
    create(client, "SCOPETOKEN-outside", folder="Outside")
    conn = client.app.state.fm.conn
    conn.execute("INSERT INTO enrichment(bookmark_id,summary) VALUES(?,?)", (done, "Saved overview"))
    for bid in (failed, excluded, unrelated):
        conn.execute("INSERT INTO enrichment_failure(bookmark_id,error,updated_at) VALUES(?,'Synthetic failure',1)", (bid,))
    scope = {"folder": "Chosen", "q": "SCOPETOKEN", "status": "failed", "exclude_ids": [excluded]}
    result = client.post(f"{BASE}/export", json={"format": "json", "scope": scope})
    assert result.status_code == 200, result.text
    assert [row["url"] for row in result.json()["bookmarks"]] == ["https://example.org/SCOPETOKEN-failed"]
    assert "library_operation" not in result.text and "request_id" not in result.text


@pytest.mark.parametrize("extra", [{"ids": [1]}, {"query": "tag:work"}, {"filters": {"folder": "Other"}}])
def test_export_rejects_ambiguous_legacy_arguments_with_a_saved_collection_scope(client, extra):
    response = client.post(f"{BASE}/export", json={"scope": {}, **extra})
    assert response.status_code == 422


def test_exported_conversations_obey_the_same_selected_scope(client):
    included = create(client, "CHATSCOPETOKEN")
    outside = create(client, "outside-chat-scope")
    for title, ids in (("Included conversation", [included]), ("Mixed conversation", [included, outside]), ("Whole library conversation", [])):
        assert client.post("/chat/conversations", json={"title": title, "bookmark_ids": ids}).status_code == 200
    selected = client.post(f"{BASE}/export", json={"scope": {"q": "CHATSCOPETOKEN"}})
    assert selected.status_code == 200, selected.text
    assert [row["title"] for row in selected.json()["conversations"]] == ["Included conversation"]
    whole = client.post(f"{BASE}/export", json={"scope": {}})
    assert whole.status_code == 200, whole.text
    assert len(whole.json()["conversations"]) == 3
    invalid = client.post(f"{BASE}/export", json={"scope": {"q": "added:not-a-date"}})
    assert invalid.status_code == 422
