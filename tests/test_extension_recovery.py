"""Browser deliveries retain their original page, lease and accepted result."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from facetmark import client_operations, service
from facetmark.api import create_app
from facetmark.config import Settings
from facetmark.fetch import store


@pytest.fixture
def client(tmp_path):
    app = create_app(Settings(data_dir=tmp_path / "extension", use_mock_provider=True))
    with TestClient(app) as client:
        yield client


@pytest.fixture
def auth(client):
    return {"Authorization": f"Bearer {client.app.state.fm.token}"}


def lease(client, auth):
    state = client.app.state.fm
    bid = service.save_bookmark(state.conn, "https://extension.test/original", title="Original", settings=state.settings)["bookmark_id"]
    store.store_body(state.conn, bid, body="saved text before the browser request")
    store.enqueue_for_browser(state.conn, bid, reason="wall")
    state.conn.commit()
    item = client.get("/queue/next", headers=auth).json()["items"][0]
    return bid, item


def payload(bid, item, **changes):
    return {"bookmark_id": bid, "lease_id": item.get("lease_id", "missing-lease"),
            "source_url": item["url"], "body": "body from the original browser page",
            "request_id": "extension-original", **changes}


def text(client, bid):
    return client.app.state.fm.conn.execute("SELECT body_text FROM content WHERE bookmark_id=?", (bid,)).fetchone()[0]


def test_lease_has_a_distinct_identity(client, auth):
    bid, item = lease(client, auth)
    assert isinstance(item.get("lease_id"), str) and len(item["lease_id"]) >= 16
    conn = client.app.state.fm.conn
    conn.execute("UPDATE fetch_queue SET leased_at=0 WHERE bookmark_id=?", (bid,))
    conn.commit()
    newer = client.get("/queue/next", headers=auth).json()["items"][0]
    assert newer["lease_id"] != item["lease_id"]


def test_result_for_an_edited_url_preserves_the_current_body(client, auth):
    bid, item = lease(client, auth)
    conn = client.app.state.fm.conn
    conn.execute("UPDATE bookmark SET url='https://extension.test/edited' WHERE id=?", (bid,))
    conn.commit()
    before = text(client, bid)
    response = client.post("/queue/complete", headers=auth, json=payload(bid, item))
    assert response.status_code == 409
    assert text(client, bid) == before


def test_previous_lease_cannot_complete_a_new_attempt(client, auth):
    bid, item = lease(client, auth)
    conn = client.app.state.fm.conn
    conn.execute("UPDATE fetch_queue SET leased_at=0 WHERE bookmark_id=?", (bid,))
    conn.commit()
    client.get("/queue/next", headers=auth)
    response = client.post("/queue/complete", headers=auth, json=payload(bid, item))
    assert response.status_code == 409
    assert text(client, bid) == "saved text before the browser request"


def test_accepted_result_is_replayed_without_overwriting_a_later_body(client, auth):
    bid, item = lease(client, auth)
    original = payload(bid, item)
    first = client.post("/queue/complete", headers=auth, json=original)
    assert first.status_code == 200 and first.json()["stored"] is True
    store.store_body(client.app.state.fm.conn, bid, body="later saved source text")
    client.app.state.fm.conn.commit()
    second = client.post("/queue/complete", headers=auth, json=original)
    assert second.status_code == 200
    assert second.json()["changed"] == first.json()["changed"]
    assert text(client, bid) == "later saved source text"
    receipt = client.get("/client/operations/extension-original", headers=auth)
    assert receipt.status_code == 200
    assert receipt.json()["result"]["bookmark_id"] == bid


def test_reused_request_id_cannot_change_an_accepted_body(client, auth):
    bid, item = lease(client, auth)
    client.post("/queue/complete", headers=auth, json=payload(bid, item))
    response = client.post("/queue/complete", headers=auth, json=payload(bid, item, body="different content"))
    assert response.status_code == 409
    assert text(client, bid) == "body from the original browser page"


def test_paused_unprocessed_lease_is_released_once_without_spending_an_attempt(client, auth):
    bid, item = lease(client, auth)
    release = {"items": [{"bookmark_id": bid, "lease_id": item.get("lease_id", "missing-lease")}]}
    first = client.post("/queue/release", headers=auth, json=release)
    assert first.status_code == 200 and first.json()["released"] == 1
    second = client.post("/queue/release", headers=auth, json=release)
    assert second.status_code == 200 and second.json()["released"] == 0
    row = client.app.state.fm.conn.execute("SELECT state,attempts FROM fetch_queue WHERE bookmark_id=?", (bid,)).fetchone()
    assert tuple(row) == ("pending", 0)


def test_old_release_does_not_release_a_new_lease(client, auth):
    bid, item = lease(client, auth)
    conn = client.app.state.fm.conn
    conn.execute("UPDATE fetch_queue SET leased_at=0 WHERE bookmark_id=?", (bid,))
    conn.commit()
    client.get("/queue/next", headers=auth)
    response = client.post("/queue/release", headers=auth, json={"items": [{"bookmark_id": bid, "lease_id": item.get("lease_id", "missing-lease")}]})
    assert response.status_code == 200 and response.json()["released"] == 0
    assert conn.execute("SELECT state FROM fetch_queue WHERE bookmark_id=?", (bid,)).fetchone()[0] == "leased"


def test_retry_of_an_accepted_save_does_not_recreate_a_deleted_bookmark(client, auth):
    original = {"url": "https://extension.test/save", "title": "Saved", "request_id": "extension-save"}
    first = client.post("/bookmark", headers=auth, json=original)
    assert first.status_code == 200
    bid = first.json()["bookmark_id"]
    conn = client.app.state.fm.conn
    conn.execute("DELETE FROM bookmark WHERE id=?", (bid,))
    conn.commit()
    retry = client.post("/bookmark", headers=auth, json=original)
    assert retry.status_code == 200 and retry.json()["bookmark_id"] == bid
    assert conn.execute("SELECT COUNT(*) FROM bookmark").fetchone()[0] == 0


def test_save_and_receipt_rollback_together_when_acceptance_cannot_be_saved(client, auth, monkeypatch):
    conn = client.app.state.fm.conn
    before = conn.execute("SELECT COUNT(*) FROM bookmark").fetchone()[0]
    original = {"url": "https://extension.test/atomic-save", "title": "Atomic original", "request_id": "atomic-save"}

    def fail(*args, **kwargs):
        raise OSError("Synthetic receipt storage failed")

    with monkeypatch.context() as patch:
        patch.setattr(client_operations, "accept", fail)
        with pytest.raises(OSError, match="receipt storage"):
            client.post("/bookmark", headers=auth, json=original)
    assert conn.execute("SELECT COUNT(*) FROM bookmark").fetchone()[0] == before
    assert client.get("/client/operations/atomic-save", headers=auth).status_code == 404
    retry = client.post("/bookmark", headers=auth, json=original)
    assert retry.status_code == 200 and retry.json()["created"] is True


def test_body_queue_state_and_receipt_rollback_together_on_acceptance_failure(client, auth, monkeypatch):
    bid, item = lease(client, auth)
    before = text(client, bid)

    def fail(*args, **kwargs):
        raise OSError("Synthetic receipt storage failed")

    with monkeypatch.context() as patch:
        patch.setattr(client_operations, "accept", fail)
        with pytest.raises(OSError, match="receipt storage"):
            client.post("/queue/complete", headers=auth, json=payload(bid, item))
    assert text(client, bid) == before
    row = client.app.state.fm.conn.execute("SELECT state,lease_id FROM fetch_queue WHERE bookmark_id=?", (bid,)).fetchone()
    assert tuple(row) == ("leased", item["lease_id"])
    assert client.get("/client/operations/extension-original", headers=auth).status_code == 404
    retry = client.post("/queue/complete", headers=auth, json=payload(bid, item))
    assert retry.status_code == 200 and retry.json()["stored"] is True


def test_reading_eligibility_change_rejects_original_delivery_and_preserves_text(client, auth):
    bid, item = lease(client, auth)
    conn = client.app.state.fm.conn
    conn.execute("UPDATE bookmark SET indexable=0,privacy_skipped=1 WHERE id=?", (bid,))
    conn.commit()
    before = text(client, bid)
    response = client.post("/queue/complete", headers=auth, json=payload(bid, item))
    assert response.status_code == 409
    assert text(client, bid) == before
    assert client.get("/client/operations/extension-original", headers=auth).status_code == 404
