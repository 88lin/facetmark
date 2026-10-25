"""Regeneration preserves earlier answers and scopes never silently broaden."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from facetmark.api import create_app
from facetmark.config import Settings
from facetmark.fetch.store import store_body
from facetmark.providers import MockProvider, ProviderError
from facetmark.service import save_bookmark


class Reply(MockProvider):
    def __init__(self, settings):
        super().__init__(settings)
        self.sent = []
        self.fail = False

    async def chat_json(self, system, user):
        self.sent.append(json.loads(user))
        if self.fail:
            raise ProviderError("Synthetic failure")
        return {"claims": [{"text": f"Saved answer {len(self.sent)}", "sources": [1]}], "gaps": []}


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(Settings(data_dir=tmp_path, use_mock_provider=True,
                    privacy_excluded_domains=("private.test",))), client=("127.0.0.1", 40000)) as local:
        state = local.app.state.fm
        state._provider = Reply(state.settings)
        local.headers["Authorization"] = "Bearer " + state.token
        for index in range(14):
            bid = save_bookmark(state.conn, f"https://source.test/{index}", title=f"Source {index}",
                                folder="small" if index < 2 else "big", settings=state.settings)["bookmark_id"]
            store_body(state.conn, bid, body="Synthetic saved evidence about recovery.")
        state.conn.commit()
        yield local


def test_regenerate_keeps_old_answer_and_retries_the_saved_question_after_failure(client):
    state = client.app.state.fm
    bid = state.conn.execute("SELECT MIN(id) FROM bookmark").fetchone()[0]
    cid = client.post("/chat/conversations", json={"bookmark_ids": [bid]}).json()["id"]
    path = f"/chat/conversations/{cid}/messages"
    original = client.post(path, json={"text": "How can I recover?", "request_id": "first"}).json()
    assert len(original["messages"]) == 2 and original["messages"][-1]["status"] == "complete"
    answer = original["messages"][-1]["content"]
    renewed = client.post(path, json={"regenerate": True, "request_id": "second"})
    assert renewed.status_code == 200, renewed.text
    data = renewed.json()
    assert [message["role"] for message in data["messages"]] == ["user", "assistant", "assistant"]
    assert data["messages"][1]["content"] == answer
    assert state._provider.sent[-1]["question"] == "How can I recover?"
    assert state._provider.sent[-1]["conversation"] == []
    assert client.post(path, json={"regenerate": True, "request_id": "second"}).json() == data
    assert len(state._provider.sent) == 2
    state._provider.fail = True
    failed = client.post(path, json={"regenerate": True, "request_id": "third"}).json()
    assert failed["messages"][-1]["status"] == "error"
    assert failed["messages"][1]["content"] == answer
    assert client.post(path, json={"regenerate": True}).status_code == 409
    state._provider.fail = False
    retried = client.post(path, json={"retry": True, "request_id": "fourth"}).json()
    assert len(retried["messages"]) == 4 and retried["messages"][-1]["status"] == "complete"
    assert state._provider.sent[-1]["question"] == "How can I recover?"
    assert retried["messages"][1]["content"] == answer


def test_scoped_chat_resolves_exact_folders_exclusions_and_a_hard_source_bound(client):
    state = client.app.state.fm
    ids = [row[0] for row in state.conn.execute("SELECT id FROM bookmark WHERE folder='small' ORDER BY id")]
    assert client.post("/chat/scopes/resolve", json={"scope": {}}).status_code == 422
    result = client.post("/chat/scopes/resolve", json={"scope": {"folder": "small", "exclude_ids": [ids[0]]}})
    assert result.status_code == 200 and result.json()["bookmark_ids"] == ids[1:]
    assert client.post("/chat/scopes/resolve", json={"scope": {"folder": "missing"}}).status_code == 404
    state.conn.execute("UPDATE bookmark SET privacy_skipped=1 WHERE id=?", (ids[1],))
    state.conn.commit()
    assert client.post("/chat/scopes/resolve", json={"scope": {"folder": "small"}}).status_code == 404


def test_invalid_regeneration_actions_do_not_append_messages(client):
    cid = client.post("/chat/conversations", json={}).json()["id"]
    path = f"/chat/conversations/{cid}/messages"
    assert client.post(path, json={"regenerate": True}).status_code == 409
    assert client.post(path, json={"retry": True, "regenerate": True}).status_code == 422
    assert client.post(path, json={"text": "Different question", "regenerate": True}).status_code == 422
    assert client.get(f"/chat/conversations/{cid}").json()["messages"] == []


def test_changed_saved_content_is_fresh_evidence_and_old_answer_is_not_resent_as_history(client):
    state = client.app.state.fm
    bid = state.conn.execute("SELECT MIN(id) FROM bookmark").fetchone()[0]
    cid = client.post("/chat/conversations", json={"bookmark_ids": [bid]}).json()["id"]
    path = f"/chat/conversations/{cid}/messages"
    original = client.post(path, json={"text": "How can I recover?"}).json()
    old_hash = original["messages"][-1]["sources"][0]["source_hash"]
    store_body(state.conn, bid, body="A different, newly saved explanation of recovery.")
    state.conn.commit()
    assert client.post(path, json={"text": "What changed?"}).status_code == 200
    sent = state._provider.sent[-1]
    assert sent["saved_evidence"][0]["source_hash"] != old_hash
    assert all(message["role"] != "assistant" for message in sent["conversation"])
