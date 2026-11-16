"""Lost chat responses and named connections never silently duplicate or switch work."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from facetmark import admin
from facetmark.api import create_app
from facetmark.config import Settings
from facetmark.providers import ProviderError
from tests.test_chat import ReplyProvider, ask, create, seed
from tests.test_chat import client as client


def test_creation_receipt_keeps_one_conversation_after_the_first_question_changes_its_title(client):
    body = {"id": "client-allocated-chat", "request_id": "create-once", "bookmark_ids": [seed(client.app.state.fm, "creation")]}
    first = client.post("/chat/conversations", json=body)
    assert first.status_code == 200, first.text
    assert first.json()["id"] == body["id"]
    ask(client, body["id"], request_id="first-question")
    repeated = client.post("/chat/conversations", json=body)
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["id"] == first.json()["id"]
    assert len(repeated.json()["messages"]) == 2
    assert client.get("/chat/conversations").json()["total"] == 1


def test_creation_receipt_rejects_a_different_scope_or_title_and_a_reused_client_id(client):
    first_id = seed(client.app.state.fm, "first-scope")
    second_id = seed(client.app.state.fm, "second-scope")
    body = {"id": "scoped-chat", "request_id": "scoped-creation", "title": "My question", "bookmark_ids": [first_id]}
    assert client.post("/chat/conversations", json=body).status_code == 200
    for changes in ({"bookmark_ids": [second_id]}, {"title": "Another question"}, {"request_id": "different-creation"}):
        assert client.post("/chat/conversations", json={**body, **changes}).status_code == 409
    assert client.get("/chat/conversations").json()["total"] == 1


def test_receipt_with_server_allocated_id_survives_restart_and_deleted_chat_is_not_recreated(client):
    state = client.app.state.fm
    body = {"request_id": "lost-creation", "title": "Persist this creation"}
    first = client.post("/chat/conversations", json=body).json()
    with TestClient(create_app(Settings(data_dir=state.settings.data_dir, use_mock_provider=True)),
                    client=("127.0.0.1", 40000)) as reopened:
        reopened.headers["Authorization"] = "Bearer " + reopened.app.state.fm.token
        repeated = reopened.post("/chat/conversations", json=body)
        assert repeated.status_code == 200, repeated.text
        assert repeated.json()["id"] == first["id"]
        assert reopened.delete("/chat/conversations/" + first["id"]).status_code == 200
        assert reopened.post("/chat/conversations", json=body).status_code == 410
        assert reopened.get("/chat/conversations").json()["total"] == 0


@pytest.mark.parametrize("change", [{"language": "zh"}, {"profile_id": "other"}, {"regenerate": True, "text": ""}])
def test_delivered_message_id_rejects_a_different_action_language_or_connection(client, change):
    cid = create(client, [seed(client.app.state.fm, "signature")])["id"]
    body = {"text": "Original question", "request_id": "message-once", "language": "en", "profile_id": ""}
    assert client.post(f"/chat/conversations/{cid}/messages", json=body).status_code == 200
    response = client.post(f"/chat/conversations/{cid}/messages", json={**body, **change})
    assert response.status_code == 409, response.text
    assert len(client.app.state.fm._provider.calls) == 1


def test_replaying_an_earlier_retry_after_a_later_retry_never_buys_an_extra_reply(client):
    state = client.app.state.fm
    state._provider.replies = [ProviderError("Synthetic failure") for _ in range(3)]
    cid = create(client, [seed(state, "retry-receipt")])["id"]
    ask(client, cid, request_id="question")
    path = f"/chat/conversations/{cid}/messages"
    for request_id in ("retry-one", "retry-two"):
        assert client.post(path, json={"retry": True, "request_id": request_id}).status_code == 200
    assert len(state._provider.calls) == 3
    repeated = client.post(path, json={"retry": True, "request_id": "retry-one"})
    assert repeated.status_code == 200, repeated.text
    assert len(state._provider.calls) == 3
    assert repeated.json()["messages"][-1]["request_id"] == "retry-two"
    assert repeated.json()["messages"][-1]["status"] == "error"


def saved_connection(client, monkeypatch, name="Detailed answers", model="chat-only-model", **overrides):
    async def probe(settings, channel=None):
        return {"chat": {"ok": True, "model": settings.chat_model, "ms": 1}}
    monkeypatch.setattr(admin, "probe", probe)
    values = {"chat_backend": "endpoint", "chat_model": model,
              "chat_base_url": "https://chat.synthetic.invalid/v1", "chat_api_key": "synthetic-chat-secret", **overrides}
    assert client.post("/admin/settings/test", json={"channel": "chat", **values}).status_code == 200
    response = client.post("/admin/model-profiles", json={"channel": "chat", "name": name, "values": values})
    assert response.status_code == 200, response.text
    return response.json()["profile"]


def test_named_chat_connection_is_pinned_per_conversation_without_changing_summary_settings(client, monkeypatch):
    state = client.app.state.fm
    profile = saved_connection(client, monkeypatch)
    providers = []
    def construct(settings):
        provider = ReplyProvider(settings)
        providers.append(provider)
        return provider
    monkeypatch.setattr(admin, "get_chat_provider", construct)
    global_values = state.settings.model_dump()
    original_provider = state._provider
    cid = create(client, [seed(state, "independent-connection")])["id"]
    first = ask(client, cid, request_id="named", profile_id=profile["id"])
    assert first["messages"][-1]["model"] == "chat-only-model"
    assert first["profile_id"] == profile["id"]
    assert providers[0].settings.chat_api_key == "synthetic-chat-secret"
    assert providers[0].closed and not original_provider.closed and not original_provider.calls
    assert state.settings.model_dump() == global_values
    assert "synthetic-chat-secret" not in json.dumps(first)
    follow_up = ask(client, cid, request_id="follow-up")
    assert follow_up["messages"][-1]["model"] == "chat-only-model"
    assert len(providers) == 2 and all(provider.closed for provider in providers)
    switched = ask(client, cid, request_id="use-summary", profile_id="")
    assert switched["profile_id"] == "" and switched["messages"][-1]["model"] == state.settings.chat_model
    assert state.settings.model_dump() == global_values


def test_removed_or_untested_connection_does_not_fall_back_to_the_summary_connection(client, monkeypatch):
    state = client.app.state.fm
    profile = saved_connection(client, monkeypatch)
    cid = create(client, [seed(state, "never-fallback")])["id"]
    assert client.delete("/admin/model-profiles/" + profile["id"]).status_code == 200
    path = f"/chat/conversations/{cid}/messages"
    assert client.post(path, json={"text": "Use removed connection", "profile_id": profile["id"]}).status_code == 404
    state.settings = state.settings.model_copy(update={"use_mock_provider": False})
    profile = client.post("/admin/model-profiles", json={"channel": "chat", "name": "Untested",
        "values": {"chat_base_url": "https://untested.synthetic.invalid/v1", "chat_api_key": "synthetic", "chat_model": "untested"}}).json()["profile"]
    assert client.post(path, json={"text": "Use untested connection", "profile_id": profile["id"]}).status_code == 409
    assert client.get("/chat/conversations/" + cid).json()["messages"] == []
    assert not state._provider.calls


def test_failed_named_test_revokes_chat_access_without_overwriting_the_previous_answer(client, monkeypatch):
    state = client.app.state.fm
    state.settings = state.settings.model_copy(update={"use_mock_provider": False})
    profile = saved_connection(client, monkeypatch)
    monkeypatch.setattr(admin, "get_chat_provider", lambda settings: ReplyProvider(settings))
    cid = create(client, [seed(state, "revoked-proof")])["id"]
    previous = ask(client, cid, request_id="valid", profile_id=profile["id"])
    async def failed(settings, channel=None):
        return {"chat": {"ok": False, "model": settings.chat_model}}
    monkeypatch.setattr(admin, "probe", failed)
    assert client.post("/admin/settings/test", json={"channel": "chat", "chat_backend": "endpoint", "chat_model": "chat-only-model",
        "chat_base_url": "https://chat.synthetic.invalid/v1", "chat_api_key": "synthetic-chat-secret"}).status_code == 200
    response = client.post(f"/chat/conversations/{cid}/messages", json={"text": "Follow-up", "request_id": "invalid"})
    assert response.status_code == 409, response.text
    assert client.get("/chat/conversations/" + cid).json()["messages"] == previous["messages"]


def test_named_chat_does_not_construct_an_unavailable_local_encoder(client, monkeypatch):
    state = client.app.state.fm
    state.settings = state.settings.model_copy(update={"embed_backend": "local", "local_embed_path": ""})
    profile = saved_connection(client, monkeypatch)
    monkeypatch.setattr(admin, "get_chat_provider", lambda settings: ReplyProvider(settings))
    cid = create(client, [seed(state, "chat-without-encoder")])["id"]
    answer = ask(client, cid, profile_id=profile["id"])
    assert answer["messages"][-1]["model"] == "chat-only-model"
