"""Cloud-run durable bookmark conversations; every provider is synthetic."""
from __future__ import annotations

import asyncio
import contextlib
import json
from contextlib import asynccontextmanager
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from facetmark import admin, chat, service
from facetmark.api import create_app
from facetmark.config import Settings
from facetmark.configfile import read_config
from facetmark.fetch import store as fetchstore
from facetmark.privacy import refresh_privacy
from facetmark.providers import MockProvider, Provider, ProviderError


class ReplyProvider(Provider):
    name = "synthetic-chat"

    def __init__(self, settings, replies=None):
        super().__init__(settings)
        self.chat_model_in_use = settings.chat_model
        self.calls = []
        self.replies = list(replies or [])
        self.before_reply = None
        self.closed = False

    async def chat_json(self, system, user):
        self.usage.calls += 1
        self.calls.append({"system": system, "user": json.loads(user)})
        if self.before_reply is not None:
            await self.before_reply()
        reply = self.replies.pop(0) if self.replies else {
            "claims": [{"text": "A supported synthetic answer.", "sources": [1]}], "gaps": []}
        if isinstance(reply, Exception):
            raise reply
        return reply

    async def embed(self, texts):
        raise AssertionError("These chat fixtures have no vectors and must not request embeddings")

    async def aclose(self):
        self.closed = True


def settings_for(tmp_path, **overrides):
    return Settings(data_dir=tmp_path / "chat-library", use_mock_provider=True,
        chat_model="selected-chat-model", embed_dim=8,
        privacy_excluded_domains=("private.test",), health_enable_external=False, **overrides)


@pytest.fixture
def client(tmp_path):
    app = create_app(settings_for(tmp_path))
    with TestClient(app, base_url="http://127.0.0.1:8787", client=("127.0.0.1", 42000)) as local:
        local.headers["Authorization"] = "Bearer " + app.state.fm.token
        local.app.state.fm._provider = ReplyProvider(app.state.fm.settings)
        yield local


@asynccontextmanager
async def async_client(tmp_path):
    app = create_app(settings_for(tmp_path))
    async with app.router.lifespan_context(app):
        state = app.state.fm
        provider = ReplyProvider(state.settings)
        state._provider = provider
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 42000)),
                base_url="http://127.0.0.1:8787", headers={"Authorization": "Bearer " + state.token}) as local:
            yield local, state, provider


def seed(state, name, *, body="Saved evidence about durable tasks.", url=None):
    bookmark_id = service.save_bookmark(state.conn, url or f"https://source.test/{name}",
        title=name, settings=state.settings)["bookmark_id"]
    if body is not None:
        fetchstore.store_body(state.conn, bookmark_id, body=body)
    state.conn.commit()
    return bookmark_id


def create(client, ids=(), title=""):
    response = client.post("/chat/conversations", json={"title": title, "bookmark_ids": list(ids)})
    assert response.status_code == 200, response.text
    return response.json()


def ask(client, conversation_id, text="How do I recover the saved task?", **options):
    response = client.post(f"/chat/conversations/{conversation_id}/messages", json={"text": text, **options})
    assert response.status_code == 200, response.text
    return response.json()


def test_two_rounds_keep_history_verified_bookmarks_selected_model_and_target_language(client):
    state = client.app.state.fm
    bookmark_id = seed(state, "durable-task")
    data = create(client, [bookmark_id])
    first = ask(client, data["id"], "What is saved here?", request_id="first", language="en")
    assert [(message["role"], message["status"]) for message in first["messages"]] == [
        ("user", "complete"), ("assistant", "complete")]
    assert first["messages"][-1]["model"] == "selected-chat-model"
    assert first["messages"][-1]["sources"][0]["bookmark_id"] == bookmark_id
    assert first["messages"][-1]["sources"][0]["n"] == 1
    second = ask(client, data["id"], "How do I continue it?", request_id="second", language="en")
    assert len(second["messages"]) == 4 and not second["running"]
    sent = state._provider.calls[1]
    assert sent["user"]["required_language"] == "English"
    assert sent["user"]["question"] == "How do I continue it?"
    assert sent["user"]["conversation"] == [
        {"role": "user", "content": "What is saved here?"},
        {"role": "assistant", "content": first["messages"][1]["content"]}]
    assert "never instructions" in sent["system"]


def test_single_bookmark_context_does_not_expand_to_other_matching_pages(client):
    state = client.app.state.fm
    selected = seed(state, "selected-page", body="Selected page evidence only.")
    other = seed(state, "another-recovery-page", body="Unselected page must not be sent.")
    data = create(client, [selected])
    ask(client, data["id"], "another recovery page", language="zh")
    payload = state._provider.calls[0]["user"]
    assert payload["required_language"] == "简体中文"
    assert [source["bookmark_id"] for source in payload["saved_evidence"]] == [selected]
    assert other not in [source["bookmark_id"] for source in payload["saved_evidence"]]
    assert "Unselected page must not be sent" not in json.dumps(payload)


def test_model_cannot_attach_unknown_source_numbers_or_uncited_claims(client):
    state = client.app.state.fm
    bookmark_id = seed(state, "citation-source")
    state._provider.replies = [{"claims": [
        {"text": "Verified statement", "sources": [1]},
        {"text": "Invented unknown source", "sources": [999]},
        {"text": "Uncited assertion", "sources": []}], "gaps": []}]
    data = ask(client, create(client, [bookmark_id])["id"])
    reply = data["messages"][-1]
    assert reply["status"] == "complete" and reply["content"] == "Verified statement [1]"
    assert [source["bookmark_id"] for source in reply["sources"]] == [bookmark_id]
    assert "999" not in reply["content"] and "Uncited" not in reply["content"]


def test_reply_without_valid_sources_is_retryable_and_keeps_the_question(client):
    state = client.app.state.fm
    bookmark_id = seed(state, "invalid-citation")
    state._provider.replies = [{"claims": [{"text": "Unsupported", "sources": [9876]}], "gaps": []}]
    data = ask(client, create(client, [bookmark_id])["id"], "Keep this question", request_id="question")
    assert data["messages"][-1]["status"] == "error"
    assert data["messages"][-1]["sources"] == []
    assert data["messages"][0]["content"] == "Keep this question"


def test_library_question_with_no_saved_evidence_does_not_call_the_model(client):
    state = client.app.state.fm
    seed(state, "sqlite-tasks")
    data = ask(client, create(client)["id"], "unobtaniumsourcezzznomatch", language="en")
    reply = data["messages"][-1]
    assert reply["status"] == "complete" and reply["model"] == "none"
    assert "No saved evidence" in reply["content"] and reply["sources"] == []
    assert state._provider.calls == []


def test_title_only_evidence_is_labeled_as_inference(client):
    state = client.app.state.fm
    bookmark_id = seed(state, "metadata-only", body=None)
    ask(client, create(client, [bookmark_id])["id"])
    sent = state._provider.calls[0]["user"]["saved_evidence"][0]
    assert sent["basis"] == "title" and sent["excerpt"] == "metadata-only"
    assert "title-only source is an inference" in state._provider.calls[0]["system"]


def test_same_request_delivery_is_idempotent_but_conflicting_text_is_rejected(client):
    state = client.app.state.fm
    conversation_id = create(client, [seed(state, "one-delivery")])["id"]
    first = ask(client, conversation_id, "Original question", request_id="once")
    repeated = ask(client, conversation_id, "Original question", request_id="once")
    assert repeated["messages"] == first["messages"] and len(state._provider.calls) == 1
    conflicting = client.post(f"/chat/conversations/{conversation_id}/messages",
        json={"text": "A different question", "request_id": "once"})
    assert conflicting.status_code == 409
    assert len(state._provider.calls) == 1


def test_failed_model_reply_can_retry_without_duplicate_questions_or_raw_error_leaks(client):
    state = client.app.state.fm
    conversation_id = create(client, [seed(state, "retry-source")])["id"]
    state._provider.replies = [ProviderError("sk-synthetic-secret-do-not-expose"),
        {"claims": [{"text": "Recovered answer", "sources": [1]}], "gaps": []}]
    first = ask(client, conversation_id, "A recoverable question", request_id="first")
    assistant_id = first["messages"][1]["id"]
    assert first["messages"][1]["status"] == "error"
    assert "sk-synthetic-secret" not in json.dumps(first)
    recovered = ask(client, conversation_id, "", retry=True, request_id="retry")
    assert len(recovered["messages"]) == 2
    assert recovered["messages"][0]["content"] == "A recoverable question"
    assert recovered["messages"][1]["id"] == assistant_id
    assert recovered["messages"][1]["status"] == "complete"
    repeated = ask(client, conversation_id, "", retry=True, request_id="retry")
    assert repeated["messages"] == recovered["messages"] and len(state._provider.calls) == 2


def test_completed_conversation_is_saved_and_can_be_reopened_after_service_restart(tmp_path):
    settings = settings_for(tmp_path)
    app = create_app(settings)
    with TestClient(app, client=("127.0.0.1", 42000)) as local:
        local.headers["Authorization"] = "Bearer " + app.state.fm.token
        app.state.fm._provider = ReplyProvider(settings)
        data = ask(local, create(local, [seed(app.state.fm, "persistent")])["id"], "A saved conversation")
    with TestClient(create_app(settings), client=("127.0.0.1", 42000)) as reopened:
        reopened.headers["Authorization"] = "Bearer " + reopened.app.state.fm.token
        loaded = reopened.get(f"/chat/conversations/{data['id']}").json()
        assert loaded["messages"] == data["messages"] and loaded["title"] == "A saved conversation"
        assert loaded["running"] is False
        assert reopened.get("/chat/conversations").json()["total"] == 1


def test_sources_and_history_respect_privacy_changes_without_resending_old_derived_content(client):
    state = client.app.state.fm
    private_later = seed(state, "private-later", url="https://private-later.test/page", body="PRIVATE_SOURCE_TEXT")
    allowed = seed(state, "still-public", url="https://still-public.test/page", body="Allowed saved text")
    state._provider.replies = [{"claims": [{"text": "PRIVATE_DERIVED_ANSWER", "sources": [1]}], "gaps": []}]
    conversation_id = create(client, [private_later, allowed])["id"]
    ask(client, conversation_id, "First question")
    state.settings = state.settings.model_copy(update={"privacy_excluded_domains": ("private-later.test", "private.test")})
    refresh_privacy(state.conn, state.settings)
    state.conn.commit()
    ask(client, conversation_id, "Next question")
    payload = state._provider.calls[1]["user"]
    assert [source["bookmark_id"] for source in payload["saved_evidence"]] == [allowed]
    serialized = json.dumps(payload)
    assert "PRIVATE_SOURCE_TEXT" not in serialized and "PRIVATE_DERIVED_ANSWER" not in serialized
    excluded = seed(state, "excluded-from-start", url="https://private.test/page")
    denied = client.post("/chat/conversations", json={"bookmark_ids": [excluded]})
    assert denied.status_code == 404


def test_large_saved_bodies_and_history_are_bounded_before_sending_to_a_model(client):
    state = client.app.state.fm
    body = "BODY_BEGIN " + "x" * 10000 + " UNIQUE_MIDDLE_TO_DROP " + "y" * 10000 + " BODY_END"
    ids = [seed(state, f"bounded-{index}", body=body) for index in range(chat.MAX_SOURCES)]
    conversation_id = create(client, ids)["id"]
    for index in range(12):
        state.conn.execute("INSERT INTO chat_message(conversation_id,role,content,status,sources,request_id,created_at) "
            "VALUES(?,? ,?,'complete','[]',?,?)", (conversation_id, "user" if index % 2 == 0 else "assistant",
                f"Old message {index} " + "z" * 10000, f"old-{index}", index))
    state.conn.commit()
    ask(client, conversation_id, "Use bounded evidence")
    payload = state._provider.calls[0]["user"]
    assert len(payload["saved_evidence"]) == chat.MAX_SOURCES
    assert sum(len(source["excerpt"]) for source in payload["saved_evidence"]) <= chat.MAX_SOURCE_CHARS
    assert sum(len(message["content"]) for message in payload["conversation"]) <= chat.MAX_HISTORY_CHARS
    assert all(len(message["content"]) <= 4000 for message in payload["conversation"])
    assert "UNIQUE_MIDDLE_TO_DROP" not in json.dumps(payload)
    assert all(source["excerpt"].startswith("BODY_BEGIN") and source["excerpt"].endswith("BODY_END")
               for source in payload["saved_evidence"])


def test_conversation_paging_and_message_limit_remain_explicit(client):
    state = client.app.state.fm
    ids = [create(client, title=f"conversation-{index}")["id"] for index in range(3)]
    first = client.get("/chat/conversations", params={"limit": 2, "offset": 0}).json()
    second = client.get("/chat/conversations", params={"limit": 2, "offset": 2}).json()
    assert first["total"] == second["total"] == 3
    assert len(first["items"]) == 2 and len(second["items"]) == 1
    assert {row["id"] for row in first["items"]}.isdisjoint(row["id"] for row in second["items"])
    for index in range(chat.MAX_MESSAGES):
        state.conn.execute("INSERT INTO chat_message(conversation_id,role,content,request_id,created_at) VALUES(?,'user',?,?,?)",
            (ids[0], "Old bounded conversation", f"old-{index}", index))
    state.conn.commit()
    response = client.post(f"/chat/conversations/{ids[0]}/messages", json={"text": "One more question"})
    assert response.status_code == 409 and state._provider.calls == []


def test_chat_requires_pairing_and_a_saved_successful_model_test(tmp_path):
    settings = settings_for(tmp_path)
    settings = settings.model_copy(update={"use_mock_provider": False, "chat_api_key": "synthetic-only"})
    with TestClient(create_app(settings), client=("127.0.0.1", 42000)) as local:
        state = local.app.state.fm
        state._provider = ReplyProvider(settings)
        assert local.get("/chat/conversations").status_code == 401
        assert local.post("/chat/conversations", json={}).status_code == 401
        local.headers["Authorization"] = "Bearer " + state.token
        conversation_id = create(local, [seed(state, "tested-model-only")])["id"]
        response = local.post(f"/chat/conversations/{conversation_id}/messages", json={"text": "Test first"})
        assert response.status_code == 409 and state._provider.calls == []
        state.probe_results["chat"] = {"fingerprint": admin.probe_fingerprint(state.settings, "chat"), "result": {"ok": True}}
        assert ask(local, conversation_id)["messages"][-1]["status"] == "complete"
        state.settings = state.settings.model_copy(update={"chat_model": "a-different-model"})
        assert local.post(f"/chat/conversations/{conversation_id}/messages", json={"text": "Test changed model"}).status_code == 409


async def test_duplicate_inflight_delivery_gets_the_saved_pending_reply_without_another_call(tmp_path):
    async with async_client(tmp_path) as (local, state, provider):
        entered, release = asyncio.Event(), asyncio.Event()

        async def wait_for_release():
            entered.set()
            await release.wait()

        provider.before_reply = wait_for_release
        data = (await local.post("/chat/conversations", json={"bookmark_ids": [seed(state, "single-flight")]})).json()
        path = f"/chat/conversations/{data['id']}/messages"
        first = asyncio.create_task(local.post(path, json={"text": "Delivered once", "request_id": "same-delivery"}))
        await asyncio.wait_for(entered.wait(), timeout=5)
        try:
            repeated = await local.post(path, json={"text": "Delivered once", "request_id": "same-delivery"})
            assert repeated.status_code == 200 and repeated.json()["running"]
            assert len(repeated.json()["messages"]) == 2 and len(provider.calls) == 1
            conflict = await local.post(path, json={"text": "Conflicting duplicate", "request_id": "same-delivery"})
            assert conflict.status_code == 409
        finally:
            release.set()
        completed = await asyncio.wait_for(first, timeout=5)
        assert completed.status_code == 200 and completed.json()["messages"][-1]["status"] == "complete"


async def test_explicit_cancel_preserves_the_question_and_retry_reuses_it(tmp_path):
    async with async_client(tmp_path) as (local, state, provider):
        entered, release = asyncio.Event(), asyncio.Event()

        async def wait_for_release():
            entered.set()
            await release.wait()

        provider.before_reply = wait_for_release
        data = (await local.post("/chat/conversations", json={"bookmark_ids": [seed(state, "cancel-source")]})).json()
        path = f"/chat/conversations/{data['id']}"
        pending = asyncio.create_task(local.post(path + "/messages", json={"text": "Keep my question", "request_id": "cancel-me"}))
        await asyncio.wait_for(entered.wait(), timeout=5)
        cancelled = await local.post(path + "/cancel")
        assert cancelled.status_code == 200 and cancelled.json()["cancelled"]
        response = await asyncio.wait_for(pending, timeout=5)
        messages = response.json()["messages"]
        assert messages[0]["content"] == "Keep my question" and messages[1]["status"] == "cancelled"
        provider.before_reply = None
        retried = await local.post(path + "/messages", json={"retry": True, "request_id": "retry-cancel"})
        assert retried.status_code == 200 and len(retried.json()["messages"]) == 2
        assert retried.json()["messages"][1]["status"] == "complete"
        assert provider.calls[-1]["user"]["question"] == "Keep my question"


@pytest.mark.parametrize("with_source", [True, False])
async def test_cancel_before_reply_routine_enters_settles_pending_rows(tmp_path, monkeypatch, with_source):
    async with async_client(tmp_path) as (local, state, provider):
        entered, release = asyncio.Event(), asyncio.Event()
        original = chat._complete

        async def before_first_execution(*args, **kwargs):
            # Model work has not started. The API cancellation path must own
            # settlement when the reply coroutine's try/finally never ran.
            entered.set()
            await release.wait()
            return await original(*args, **kwargs)

        monkeypatch.setattr(chat, "_complete", before_first_execution)
        ids = [seed(state, "early-cancel")] if with_source else []
        data = (await local.post("/chat/conversations", json={"bookmark_ids": ids})).json()
        path = f"/chat/conversations/{data['id']}"
        sent = asyncio.create_task(local.post(path + "/messages", json={"text": "Persist before scheduling", "request_id": "early"}))
        await asyncio.wait_for(entered.wait(), timeout=5)
        cancelled = await local.post(path + "/cancel")
        assert cancelled.status_code == 200 and cancelled.json()["cancelled"]
        await asyncio.wait_for(sent, timeout=5)
        saved = (await local.get(path)).json()
        assert saved["messages"][0]["content"] == "Persist before scheduling"
        assert saved["messages"][1]["status"] == "cancelled"
        assert not saved["running"] and provider.calls == []


async def test_navigation_request_cancellation_does_not_cancel_the_durable_reply(tmp_path):
    async with async_client(tmp_path) as (local, state, provider):
        entered, release = asyncio.Event(), asyncio.Event()

        async def wait_for_release():
            entered.set()
            await release.wait()

        provider.before_reply = wait_for_release
        data = (await local.post("/chat/conversations", json={"bookmark_ids": [seed(state, "navigation-survives")]})).json()
        path = f"/chat/conversations/{data['id']}"
        request = asyncio.create_task(local.post(path + "/messages", json={"text": "Answer after navigation", "request_id": "navigate"}))
        await asyncio.wait_for(entered.wait(), timeout=5)
        request.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await request
        saved = (await local.get(path)).json()
        assert saved["running"] and saved["messages"][1]["status"] == "pending"
        reply = state.chat_runs[data["id"]]
        release.set()
        await asyncio.wait_for(reply, timeout=5)
        saved = (await local.get(path)).json()
        assert saved["messages"][1]["status"] == "complete" and len(provider.calls) == 1


def test_interrupted_reply_is_recoverable_after_reopening_the_service(tmp_path):
    settings = settings_for(tmp_path)
    with TestClient(create_app(settings), client=("127.0.0.1", 42000)) as local:
        state = local.app.state.fm
        local.headers["Authorization"] = "Bearer " + state.token
        conversation_id = create(local, [seed(state, "interrupted-source")])["id"]
        state.conn.execute("INSERT INTO chat_message(conversation_id,role,content,request_id,created_at) VALUES(?,'user','Interrupted question','interrupted',1)", (conversation_id,))
        state.conn.execute("INSERT INTO chat_message(conversation_id,role,status,request_id,created_at) VALUES(?,'assistant','pending','interrupted',1)", (conversation_id,))
        state.conn.commit()
    with TestClient(create_app(settings), client=("127.0.0.1", 42000)) as reopened:
        state = reopened.app.state.fm
        state._provider = ReplyProvider(settings)
        reopened.headers["Authorization"] = "Bearer " + state.token
        saved = reopened.get(f"/chat/conversations/{conversation_id}").json()
        assert saved["messages"][0]["content"] == "Interrupted question"
        assert saved["messages"][1]["status"] == "cancelled" and not saved["running"]
        recovered = ask(reopened, conversation_id, "", retry=True, request_id="recover-interrupted")
        assert recovered["messages"][1]["status"] == "complete" and len(recovered["messages"]) == 2


@pytest.mark.parametrize("language, stopped", [("zh", "回答已停止"), ("en", "Reply stopped")])
def test_cancel_before_message_delivery_is_idempotent_and_never_calls_the_model(client, language, stopped):
    state = client.app.state.fm
    conversation_id = create(client, [seed(state, "cancel-before-delivery")])["id"]
    path = f"/chat/conversations/{conversation_id}"
    for _ in range(3):
        cancelled = client.post(path + "/cancel", json={"request_id": "delayed-message"})
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json() == {"cancelled": True, "request_id": "delayed-message", "pending_delivery": True}
    assert set(state.chat_cancellations) == {(conversation_id, "delayed-message")}
    assert client.get(path).json()["messages"] == []
    assert not state.chat_runs and not state.chat_requests

    saved = ask(client, conversation_id, "Delivered after Stop", request_id="delayed-message", language=language)
    assert [(row["role"], row["status"], row["request_id"]) for row in saved["messages"]] == [
        ("user", "complete", "delayed-message"), ("assistant", "cancelled", "delayed-message")]
    assert saved["messages"][0]["content"] == "Delivered after Stop"
    assert stopped in saved["messages"][1]["content"] and saved["messages"][1]["sources"] == []
    assert not saved["running"] and not state.chat_cancellations
    assert state._provider.calls == []

    repeated = ask(client, conversation_id, "Delivered after Stop", request_id="delayed-message", language=language)
    assert repeated["messages"] == saved["messages"]
    cancelled = client.post(path + "/cancel", json={"request_id": "delayed-message"})
    assert cancelled.status_code == 200 and cancelled.json()["cancelled"]
    assert not state.chat_cancellations and state._provider.calls == []


async def test_cancel_matches_the_active_request_and_preserves_a_different_pending_intent(tmp_path):
    async with async_client(tmp_path) as (local, state, provider):
        entered, release = asyncio.Event(), asyncio.Event()

        async def wait_for_release():
            entered.set()
            await release.wait()

        provider.before_reply = wait_for_release
        data = (await local.post("/chat/conversations", json={"bookmark_ids": [seed(state, "request-match")]})).json()
        path = f"/chat/conversations/{data['id']}"
        sent = asyncio.create_task(local.post(path + "/messages", json={"text": "The active question", "request_id": "active"}))
        try:
            await asyncio.wait_for(entered.wait(), timeout=5)
            other = await local.post(path + "/cancel", json={"request_id": "future"})
            assert other.status_code == 200 and other.json()["pending_delivery"]
            saved = (await local.get(path)).json()
            assert saved["running"] and saved["messages"][-1]["status"] == "pending"
            assert state.chat_requests[data["id"]] == "active" and len(provider.calls) == 1
            assert (await local.delete(path)).status_code == 409
            assert (data["id"], "future") in state.chat_cancellations

            cancelled = await local.post(path + "/cancel", json={"request_id": "active"})
            assert cancelled.status_code == 200 and cancelled.json() == {"cancelled": True, "request_id": "active"}
            result = await asyncio.wait_for(sent, timeout=5)
            assert result.status_code == 200
            assert result.json()["messages"][-1]["status"] == "cancelled"
            assert result.json()["messages"][0]["content"] == "The active question"
            repeated = await local.post(path + "/cancel", json={"request_id": "active"})
            assert repeated.status_code == 200 and repeated.json()["cancelled"]
            assert (data["id"], "active") not in state.chat_cancellations
            assert (data["id"], "future") in state.chat_cancellations
            assert data["id"] not in state.chat_requests and not provider.closed

            future = await local.post(path + "/messages", json={"text": "Previously stopped future question", "request_id": "future"})
            assert future.status_code == 200 and future.json()["messages"][-1]["status"] == "cancelled"
            assert len(future.json()["messages"]) == 4 and len(provider.calls) == 1
            assert not state.chat_cancellations
        finally:
            release.set()
            await asyncio.wait_for(asyncio.gather(sent, return_exceptions=True), timeout=5)


@pytest.mark.parametrize("earlier_status", ["complete", "cancelled"])
async def test_late_old_cancel_does_not_stop_a_new_reply_in_the_same_conversation(tmp_path, earlier_status):
    async with async_client(tmp_path) as (local, state, provider):
        data = (await local.post("/chat/conversations", json={"bookmark_ids": [seed(state, "late-stop")]})).json()
        path = f"/chat/conversations/{data['id']}"
        if earlier_status == "cancelled":
            assert (await local.post(path + "/cancel", json={"request_id": "earlier"})).status_code == 200
        first = await local.post(path + "/messages", json={"text": "Earlier question", "request_id": "earlier"})
        assert first.status_code == 200 and first.json()["messages"][-1]["status"] == earlier_status
        entered, release = asyncio.Event(), asyncio.Event()

        async def wait_for_release():
            entered.set()
            await release.wait()

        provider.before_reply = wait_for_release
        sent = asyncio.create_task(local.post(path + "/messages", json={"text": "A new question", "request_id": "new"}))
        try:
            await asyncio.wait_for(entered.wait(), timeout=5)
            late = await local.post(path + "/cancel", json={"request_id": "earlier"})
            assert late.status_code == 200
            assert late.json() == {"cancelled": earlier_status == "cancelled", "request_id": "earlier"}
            saved = (await local.get(path)).json()
            assert saved["running"] and saved["messages"][-1]["request_id"] == "new"
            assert saved["messages"][-1]["status"] == "pending" and len(saved["messages"]) == 4
            assert state.chat_requests[data["id"]] == "new"
            assert not state.chat_runs[data["id"]].done()
            assert (data["id"], "earlier") not in state.chat_cancellations
        finally:
            release.set()
            results = await asyncio.wait_for(asyncio.gather(sent, return_exceptions=True), timeout=5)
        assert isinstance(results[0], httpx.Response) and results[0].status_code == 200
        assert results[0].json()["messages"][-1]["status"] == "complete"
        assert results[0].json()["messages"][1]["status"] == earlier_status
        assert len(provider.calls) == (2 if earlier_status == "complete" else 1)


def test_cancel_intent_expiry_allows_a_new_delivery_and_retains_recent_intents(client, monkeypatch):
    state = client.app.state.fm
    clock = [5000.0]
    # Replace this module's dependency, not the shared time.monotonic used by
    # asyncio and TestClient: their deadlines must keep advancing normally.
    monkeypatch.setattr(chat, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    conversation_id = create(client, [seed(state, "intent-expiry")])["id"]
    path = f"/chat/conversations/{conversation_id}"
    assert client.post(path + "/cancel", json={"request_id": "expired"}).status_code == 200
    clock[0] += chat.CANCEL_INTENT_TTL - 10
    assert client.post(path + "/cancel", json={"request_id": "recent"}).status_code == 200
    clock[0] = 5000.0 + chat.CANCEL_INTENT_TTL + 1

    delivered = ask(client, conversation_id, "Expired Stop is no longer active", request_id="expired")
    assert delivered["messages"][-1]["status"] == "complete" and len(state._provider.calls) == 1
    assert (conversation_id, "expired") not in state.chat_cancellations
    assert (conversation_id, "recent") in state.chat_cancellations
    stopped = ask(client, conversation_id, "Recent Stop still applies", request_id="recent")
    assert stopped["messages"][-1]["status"] == "cancelled" and len(state._provider.calls) == 1
    assert not state.chat_cancellations


def test_cancel_intents_are_bounded_and_evict_the_oldest_unused_request(client, monkeypatch):
    state = client.app.state.fm
    monkeypatch.setattr(chat, "MAX_CANCEL_INTENTS", 3)
    conversation_id = create(client, [seed(state, "intent-capacity")])["id"]
    path = f"/chat/conversations/{conversation_id}"
    for index in range(4):
        response = client.post(path + "/cancel", json={"request_id": f"queued-{index}"})
        assert response.status_code == 200 and response.json()["pending_delivery"]
        assert len(state.chat_cancellations) <= 3
    assert set(state.chat_cancellations) == {(conversation_id, f"queued-{index}") for index in range(1, 4)}
    oldest = ask(client, conversation_id, "The evicted request can run", request_id="queued-0")
    assert oldest["messages"][-1]["status"] == "complete" and len(state._provider.calls) == 1
    newest = ask(client, conversation_id, "The retained Stop still applies", request_id="queued-3")
    assert newest["messages"][-1]["status"] == "cancelled" and len(state._provider.calls) == 1


def test_deleting_a_conversation_cleans_only_its_cancel_intents(client):
    state = client.app.state.fm
    source = seed(state, "delete-intents")
    first, second = create(client, [source])["id"], create(client, [source])["id"]
    for conversation_id, request_id in [(first, "shared-id"), (first, "another-id"), (second, "shared-id")]:
        response = client.post(f"/chat/conversations/{conversation_id}/cancel", json={"request_id": request_id})
        assert response.status_code == 200 and response.json()["pending_delivery"]
    assert len(state.chat_cancellations) == 3
    removed = client.delete(f"/chat/conversations/{first}")
    assert removed.status_code == 200 and removed.json() == {"ok": True}
    assert set(state.chat_cancellations) == {(second, "shared-id")}
    assert client.get(f"/chat/conversations/{first}").status_code == 404
    assert client.post(f"/chat/conversations/{first}/cancel", json={"request_id": "new-id"}).status_code == 404
    assert client.post(f"/chat/conversations/{first}/messages", json={"text": "Late deleted delivery", "request_id": "shared-id"}).status_code == 404
    assert set(state.chat_cancellations) == {(second, "shared-id")}
    saved = ask(client, second, "Another conversation's stopped request", request_id="shared-id")
    assert saved["messages"][-1]["status"] == "cancelled" and state._provider.calls == []
    assert not state.chat_cancellations


async def test_default_two_chat_slots_reject_overflow_and_cancel_releases_a_slot(tmp_path):
    async with async_client(tmp_path) as (local, state, provider):
        assert state.settings.chat_concurrency == 2
        view = (await local.get("/admin/settings")).json()
        assert next(row for row in view["settings"] if row["key"] == "chat_concurrency")["value"] == 2
        entered, release = asyncio.Queue(), asyncio.Event()

        async def wait_for_release():
            await entered.put(provider.calls[-1]["user"]["question"])
            await release.wait()

        provider.before_reply = wait_for_release
        source = seed(state, "two-chat-slots")
        ids = [(await local.post("/chat/conversations", json={"bookmark_ids": [source]})).json()["id"] for _ in range(3)]
        requests = []
        try:
            for index in range(2):
                requests.append(asyncio.create_task(local.post(f"/chat/conversations/{ids[index]}/messages",
                    json={"text": f"Question {index}", "request_id": f"slot-{index}"})))
                assert await asyncio.wait_for(entered.get(), timeout=5) == f"Question {index}"
            denied = await asyncio.wait_for(local.post(f"/chat/conversations/{ids[2]}/messages",
                json={"text": "Question 2", "request_id": "slot-2"}), timeout=5)
            assert denied.status_code == 409 and len(provider.calls) == 2
            assert (await local.get(f"/chat/conversations/{ids[2]}")).json()["messages"] == []

            cancelled = await local.post(f"/chat/conversations/{ids[0]}/cancel", json={"request_id": "slot-0"})
            assert cancelled.status_code == 200 and cancelled.json()["cancelled"]
            first = await asyncio.wait_for(requests[0], timeout=5)
            assert first.json()["messages"][-1]["status"] == "cancelled"
            assert ids[0] not in state.chat_requests
            requests.append(asyncio.create_task(local.post(f"/chat/conversations/{ids[2]}/messages",
                json={"text": "Question 2", "request_id": "slot-2"})))
            assert await asyncio.wait_for(entered.get(), timeout=5) == "Question 2"
            assert len(provider.calls) == 3
            assert sum(not task.done() for task in state.chat_runs.values()) == 2
            assert state.chat_requests == {ids[1]: "slot-1", ids[2]: "slot-2"}
        finally:
            release.set()
            results = await asyncio.wait_for(asyncio.gather(*requests, return_exceptions=True), timeout=5)
        assert all(isinstance(response, httpx.Response) and response.status_code == 200 for response in results)
        assert [response.json()["messages"][-1]["status"] for response in results] == ["cancelled", "complete", "complete"]
        assert not state.chat_runs and not state.chat_requests


@pytest.mark.parametrize("limit", [1, 3])
async def test_saved_chat_concurrency_is_persisted_and_controls_new_reply_capacity(tmp_path, limit):
    async with async_client(tmp_path) as (local, state, previous_provider):
        response = await local.put("/admin/settings", json={"values": {"chat_concurrency": limit}})
        assert response.status_code == 200, response.text
        assert "chat_concurrency" in response.json()["applied"]
        assert next(row for row in response.json()["settings"] if row["key"] == "chat_concurrency")["value"] == limit
        assert state.settings.chat_concurrency == limit and read_config()["chat_concurrency"] == limit
        assert settings_for(tmp_path).chat_concurrency == limit
        assert previous_provider.closed
        provider = ReplyProvider(state.settings)
        state._provider = provider
        entered, release = asyncio.Queue(), asyncio.Event()

        async def wait_for_release():
            await entered.put(provider.calls[-1]["user"]["question"])
            await release.wait()

        provider.before_reply = wait_for_release
        source = seed(state, "configured-chat-slots")
        ids = [(await local.post("/chat/conversations", json={"bookmark_ids": [source]})).json()["id"] for _ in range(limit + 1)]
        requests = []
        try:
            for index in range(limit):
                requests.append(asyncio.create_task(local.post(f"/chat/conversations/{ids[index]}/messages",
                    json={"text": f"Configured question {index}", "request_id": f"configured-{index}"})))
                assert await asyncio.wait_for(entered.get(), timeout=5) == f"Configured question {index}"
            denied = await asyncio.wait_for(local.post(f"/chat/conversations/{ids[-1]}/messages",
                json={"text": "Beyond configured capacity", "request_id": "overflow"}), timeout=5)
            assert denied.status_code == 409 and len(provider.calls) == limit
            assert (await local.get(f"/chat/conversations/{ids[-1]}")).json()["messages"] == []
        finally:
            release.set()
            results = await asyncio.wait_for(asyncio.gather(*requests, return_exceptions=True), timeout=5)
        assert all(isinstance(response, httpx.Response) and response.status_code == 200 for response in results)
        assert all(response.json()["messages"][-1]["status"] == "complete" for response in results)
        assert not state.chat_runs and not state.chat_requests


async def test_active_chat_rejects_settings_without_persisting_or_closing_its_provider(tmp_path):
    async with async_client(tmp_path) as (local, state, provider):
        entered, release = asyncio.Event(), asyncio.Event()

        async def wait_for_release():
            entered.set()
            await release.wait()

        provider.before_reply = wait_for_release
        source = seed(state, "settings-during-chat")
        data = (await local.post("/chat/conversations", json={"bookmark_ids": [source]})).json()
        path = f"/chat/conversations/{data['id']}"
        before_settings, before_config = state.settings.model_dump(), read_config()
        sent = asyncio.create_task(local.post(path + "/messages", json={"text": "Keep this provider open", "request_id": "settings-active"}))
        try:
            await asyncio.wait_for(entered.wait(), timeout=5)
            rejected = await local.put("/admin/settings", json={"values": {
                "chat_concurrency": 1, "chat_model": "changed-model", "privacy_excluded_domains": "source.test"}})
            assert rejected.status_code == 409 and "stop active replies" in rejected.json()["detail"]
            assert state.settings.model_dump() == before_settings and read_config() == before_config
            assert state._provider is provider and not provider.closed
            saved = (await local.get(path)).json()
            assert saved["running"] and saved["messages"][-1]["status"] == "pending"
            assert state.conn.execute("SELECT privacy_skipped FROM bookmark WHERE id=?", (source,)).fetchone()[0] == 0
        finally:
            release.set()
            results = await asyncio.wait_for(asyncio.gather(sent, return_exceptions=True), timeout=5)
        assert isinstance(results[0], httpx.Response) and results[0].status_code == 200
        assert results[0].json()["messages"][-1]["status"] == "complete"
        assert results[0].json()["messages"][-1]["model"] == "selected-chat-model"
        assert not provider.closed

        accepted = await local.put("/admin/settings", json={"values": {"chat_concurrency": 1}})
        assert accepted.status_code == 200 and state.settings.chat_concurrency == 1
        assert read_config()["chat_concurrency"] == 1
        assert provider.closed and state._provider is None


@pytest.mark.parametrize("language", ["zh", "en"])
def test_real_offline_demo_chat_quotes_saved_evidence_with_citations_and_an_honest_notice(tmp_path, language):
    settings = settings_for(tmp_path)
    with TestClient(create_app(settings), client=("127.0.0.1", 42000)) as local:
        state = local.app.state.fm
        local.headers["Authorization"] = "Bearer " + state.token
        provider = state.provider
        assert isinstance(provider, MockProvider)
        body = "每次完成后保存任务检查点，再继续未完成的内容。" if language == "zh" else "Save a checkpoint after each task and continue unfinished work."
        source = seed(state, f"offline-demo-{language}", body=body)
        data = ask(local, create(local, [source])["id"], "Explain this saved page", language=language, request_id="demo")
        reply = data["messages"][-1]
        assert reply["status"] == "complete" and not data["running"]
        assert body in reply["content"] and "[1]" in reply["content"]
        assert ("离线示例" if language == "zh" else "offline demo") in reply["content"]
        assert [(row["n"], row["bookmark_id"], row["basis"]) for row in reply["sources"]] == [(1, source, "body")]
        assert provider.usage.calls == 1 and provider.usage.completion_tokens > 0
