"""Settings changes must preserve privacy and the identity of a vector index."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from facetmark import service
from facetmark.api import create_app
from facetmark.config import Settings
from facetmark.configfile import read_config
from facetmark.db import ensure_vec_tables, get_meta, upsert_content_vector, upsert_intent_vector
from facetmark.enrich import embed_content, enrich_all, filter_intents
from facetmark.enrich.vectors import embed_intents
from facetmark.fetch.store import (
    enqueue_for_browser,
    lease_browser_batch,
    pending_targets,
    store_body,
)
from facetmark.providers import MockProvider
from facetmark.search.pipeline import Config, search
from facetmark.search.vectors import vector_lists, vector_lists_scored


class RecordingProvider(MockProvider):
    def __init__(self, settings):
        super().__init__(settings)
        self.sent = []

    async def chat_json(self, system, user):
        self.sent.append(user)
        return await super().chat_json(system, user)

    async def embed(self, texts):
        self.sent.extend(texts)
        return await super().embed(texts)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FACETMARK_DATA_DIR", str(tmp_path))
    settings = Settings(data_dir=tmp_path, use_mock_provider=True, embed_dim=8)
    with TestClient(create_app(settings), client=("127.0.0.1", 40404)) as c:
        c.headers["Authorization"] = f"Bearer {c.app.state.fm.token}"
        yield c


def save(client, path="private", host="bank.example"):
    r = client.post("/bookmark", json={"url": f"https://{host}/{path}", "title": path})
    assert r.status_code == 200
    return r.json()["bookmark_id"]


def rows(response):
    assert response.status_code == 200, response.text
    return {r["key"]: r for r in response.json()["settings"]}


async def test_excluding_existing_pages_stops_all_index_stages_and_browser_leases(client):
    state = client.app.state.fm
    conn = state.conn
    private = save(client, "PRIVATE_MARKER")
    public = save(client, "PUBLIC_MARKER", "public.example")
    ensure_vec_tables(conn, 8, state.settings.embed_model)
    upsert_content_vector(conn, private, [1.0] * 8)
    store_body(conn, private, body="PRIVATE_MARKER original body")
    conn.execute(
        "INSERT INTO intent_query(id,bookmark_id,text,kept,created_at) VALUES(501,?,?,1,1)",
        (private, "PRIVATE_MARKER old intent"),
    )
    upsert_intent_vector(conn, 501, [1.0] * 8)
    enqueue_for_browser(conn, private, reason="test")

    r = client.put("/admin/settings", json={"values": {"privacy_excluded_domains": ["bank.example"]}})
    assert r.status_code == 200
    assert conn.execute("SELECT privacy_skipped FROM bookmark WHERE id=?", (private,)).fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM vec_content").fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM vec_intent").fetchone()[0] == 0
    assert private not in [b[0] for b in pending_targets(conn, refetch=True)]
    assert lease_browser_batch(conn, 3) == []

    provider = RecordingProvider(state.settings)
    await enrich_all(conn, provider=provider, settings=state.settings, force=True)
    await embed_content(conn, provider=provider, settings=state.settings, force=True)
    await filter_intents(conn, provider=provider, settings=state.settings, force=True)
    await embed_intents(conn, provider=provider, settings=state.settings, force=True)
    assert provider.sent and all("PRIVATE_MARKER" not in text for text in provider.sent)
    assert conn.execute("SELECT count(*) FROM bookmark").fetchone()[0] == 2
    assert conn.execute("SELECT body_text FROM content WHERE bookmark_id=?", (private,)).fetchone()[0].startswith("PRIVATE_MARKER")
    assert conn.execute("SELECT count(*) FROM vec_content WHERE bookmark_id=?", (public,)).fetchone()[0] == 1

    assert client.put("/admin/settings", json={"values": {"privacy_excluded_domains": []}}).status_code == 200
    assert conn.execute("SELECT privacy_skipped FROM bookmark WHERE id=?", (private,)).fetchone()[0] == 0
    assert private in [b[0] for b in pending_targets(conn, refetch=True)]


def test_karakeep_excluded_page_never_reaches_embedding_provider(client):
    state = client.app.state.fm
    assert client.put("/admin/settings", json={"values": {"privacy_excluded_domains": ["bank.example"]}}).status_code == 200
    provider = RecordingProvider(state.settings)
    state._provider = provider
    for _ in range(2):  # Both insert and update obey the rule.
        r = client.post("/karakeep/documents", json={"documents": [
            {"id": "private", "url": "https://mail.bank.example/account", "title": "PRIVATE_MARKER", "content": "private body"},
            {"id": "public", "url": "https://public.example/page", "title": "public"},
        ]})
        assert r.status_code == 200
        assert r.json()["embedded"] == 1
    assert provider.sent and all("PRIVATE_MARKER" not in text for text in provider.sent)


async def test_private_lexical_hits_are_not_sent_to_synthesis_or_reranking(client):
    from facetmark.search.rerank import LLMReranker

    state = client.app.state.fm
    bid = save(client, "PRIVATE_MARKER")
    store_body(state.conn, bid, body="PRIVATE_MARKER secret body")
    client.put("/admin/settings", json={"values": {"privacy_excluded_domains": ["bank.example"]}})
    provider = RecordingProvider(state.settings)
    response = await search(
        state.conn, "PRIVATE_MARKER", settings=state.settings, provider=provider,
        config=Config("private-test", frozenset({"lex_seg", "lex_tri"}), rerank=True),
        reranker=LLMReranker(provider),
    )
    assert response.ids == [bid]
    result = await service.synthesize(state.conn, "PRIVATE_MARKER", settings=state.settings,
                                      provider=provider, response=response)
    assert result.sources == []
    assert provider.sent == []


def test_privacy_change_waits_for_existing_index_work(client, monkeypatch):
    import asyncio
    import threading

    release = threading.Event()

    async def held_index(*args, **kwargs):
        while not release.is_set():
            await asyncio.sleep(0.01)
        return service.IndexReport()

    monkeypatch.setattr(service, "index_all", held_index)
    assert client.post("/admin/index", json={"fetch": False}).status_code == 200
    try:
        r = client.put("/admin/settings", json={"values": {"privacy_excluded_domains": ["bank.example"]}})
        assert r.status_code == 409
        assert "stop the index job" in r.json()["detail"]
        assert "privacy_excluded_domains" not in read_config()
    finally:
        release.set()


async def test_index_job_keeps_the_model_settings_it_started_with(client, monkeypatch):
    from facetmark.admin import JobRunner

    captured = []

    async def capture(*args, settings, **kwargs):
        captured.append(settings.chat_model)
        return service.IndexReport()

    monkeypatch.setattr(service, "index_all", capture)
    settings = client.app.state.fm.settings
    original = settings.chat_model
    runner = JobRunner()
    runner.start(settings, fetch=False, limit=None, force=False)
    settings.chat_model = "changed-after-start"
    await runner._task
    assert captured == [original]


@pytest.mark.parametrize("function", [vector_lists, vector_lists_scored])
@pytest.mark.parametrize("change", [{"embed_model": "other-model"}, {"embed_dim": 4}])
async def test_mismatched_vectors_fail_before_any_model_call(client, function, change):
    from facetmark.db import SchemaMismatch

    state = client.app.state.fm
    ensure_vec_tables(state.conn, 8, state.settings.embed_model)
    altered = state.settings.model_copy(update=change)
    provider = RecordingProvider(altered)
    with pytest.raises(SchemaMismatch, match="reindex --vectors"):
        await function(state.conn, "query", provider=provider, settings=altered)
    assert provider.sent == []


def test_model_switch_returns_actionable_conflict_and_keeps_lexical_search(client):
    state = client.app.state.fm
    bid = save(client, "searchable")
    original = state.settings.embed_model
    ensure_vec_tables(state.conn, 8, original)
    upsert_content_vector(state.conn, bid, [1.0] * 8)
    assert client.put("/admin/settings", json={"values": {"embed_model": "other-model"}}).status_code == 200
    r = client.post("/search", json={"q": "searchable", "config": "A"})
    # Save keeps the active vector space intact until a confirmed apply.
    assert r.status_code == 200
    assert state.settings.embed_model == original
    assert state.pending_settings['embed_model'] == 'other-model'
    assert get_meta(state.conn, "embed_model") == original
    assert client.get("/quick", params={"q": "searchable"}).json()["total"] == 1


@pytest.mark.parametrize("mock", [True, False])
def test_mock_or_missing_credentials_never_claim_real_connection_success(client, mock):
    state = client.app.state.fm
    state.settings.use_mock_provider = mock
    state.settings.api_key = ""
    r = client.post("/admin/settings/test", json={"base_url": "https://nonexistent.invalid/v1"})
    assert r.status_code == 200
    assert not r.json()["ok"]
    for kind in ("chat", "embed"):
        assert not r.json()[kind]["ok"]
        assert r.json()[kind]["model"] == ('mock' if mock else getattr(state.settings, f'{kind}_model'))
        assert any(text in r.json()[kind]['error'] for text in ('not tested', 'no real model connection', 'not configured'))


def test_saved_restart_value_survives_reload_and_can_be_reverted(client):
    r = client.put("/admin/settings", json={"values": {"embed_dim": 16}})
    field = rows(r)["embed_dim"]
    assert (field["value"], field["active_value"], field["pending_restart"]) == (16, 8, True)
    assert rows(client.get("/admin/settings"))["embed_dim"] == field
    r = client.put("/admin/settings", json={"values": {"embed_dim": 8}})
    assert not rows(r)["embed_dim"]["pending_restart"]
    assert r.json()["restart_required"] == []
    assert read_config()["embed_dim"] == 8


def test_clearing_restart_value_tracks_default_without_recreating_file_key(client):
    r = client.put("/admin/settings", json={"values": {"embed_dim": None}})
    field = rows(r)["embed_dim"]
    assert field["value"] == Settings.model_fields["embed_dim"].default
    assert field["active_value"] == 8 and field["pending_restart"]
    assert "embed_dim" not in read_config()
    assert rows(client.get("/admin/settings"))["embed_dim"] == field


def test_invalid_local_provider_configuration_is_reported_instead_of_500(client):
    state = client.app.state.fm
    state.settings.embed_backend = "local"
    state.settings.local_embed_path = ""
    r = client.post("/admin/settings/test", json={})
    assert r.status_code == 200
    assert not r.json()["ok"]
    assert "LOCAL_EMBED_PATH" in r.json()["embed"]["error"]


async def test_database_open_failure_does_not_leave_an_index_job_running(client, monkeypatch):
    from facetmark.admin import JobRunner

    def broken(*args, **kwargs):
        raise OSError("test database unavailable")

    monkeypatch.setattr("facetmark.admin.open_db", broken)
    runner = JobRunner()
    job = runner.start(client.app.state.fm.settings, fetch=False, limit=None, force=False)
    await runner._task
    assert job.state == "failed"
    assert "test database unavailable" in job.error
    assert not runner.running


@pytest.mark.parametrize("fail", [False, True])
async def test_index_job_closes_its_provider_on_success_and_failure(client, monkeypatch, fail):
    from facetmark.admin import JobRunner

    closed = []
    provider = MockProvider(client.app.state.fm.settings)

    async def close():
        closed.append(True)

    async def index(*args, **kwargs):
        if fail:
            raise RuntimeError("test stage failed")
        return service.IndexReport()

    monkeypatch.setattr(provider, "aclose", close)
    monkeypatch.setattr("facetmark.admin.get_provider", lambda settings: provider)
    monkeypatch.setattr(service, "index_all", index)
    runner = JobRunner()
    job = runner.start(client.app.state.fm.settings, fetch=False, limit=None, force=False)
    await runner._task
    assert job.state == ("failed" if fail else "done")
    assert closed == [True]


async def test_empty_index_scope_does_not_embed_the_whole_library(client):
    state = client.app.state.fm
    bid = save(client, "scope-test")
    state.conn.execute(
        "INSERT INTO intent_query(bookmark_id,text,kept,created_at) VALUES(?,?,1,1)",
        (bid, "scope-test intent"),
    )
    provider = RecordingProvider(state.settings)
    content = await embed_content(state.conn, provider=provider, settings=state.settings, ids=[])
    intents = await filter_intents(state.conn, provider=provider, settings=state.settings, ids=[])
    assert content.content_written == 0
    assert intents.candidates == 0
    assert provider.sent == []
