"""Regression tests for independent credentials, browsing and safe setup."""

from __future__ import annotations

import asyncio
import json
import time

import pytest
import respx
from fastapi.testclient import TestClient

from facetmark import admin, service
from facetmark.api import create_app
from facetmark.config import Settings
from facetmark.configfile import read_config, write_config
from facetmark.db import ensure_vec_tables, get_meta, upsert_content_vector
from facetmark.providers import ProviderError, get_provider


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FACETMARK_DATA_DIR", str(tmp_path))
    with TestClient(
        create_app(Settings(data_dir=tmp_path, embed_dim=8)), client=("127.0.0.1", 40404)
    ) as c:
        c.headers["Authorization"] = f"Bearer {c.app.state.fm.token}"
        yield c


def test_legacy_environment_outranks_channel_file_without_crossing_keys(monkeypatch):
    write_config(
        {
            "chat_base_url": "https://chat.example/v1",
            "chat_api_key": "chat-secret",
            "embed_base_url": "https://embed.example/v1",
            "embed_api_key": "embed-secret",
        }
    )
    monkeypatch.setenv("FACETMARK_BASE_URL", "https://env.example/v1")
    settings = Settings()
    for channel in ("chat", "embed"):
        assert settings.channel_settings(channel).base_url == "https://env.example/v1"
        assert settings.channel_settings(channel).api_key == ""
    monkeypatch.setenv("FACETMARK_API_KEY", "env-secret")
    assert Settings().channel_settings("embed").api_key == "env-secret"
    assert (
        Settings(chat_base_url="https://override.example/v1").channel_settings("chat").api_key == ""
    )


def test_channel_override_does_not_inherit_lower_source_key(monkeypatch):
    write_config({"chat_base_url": "https://a.example/v1", "chat_api_key": "a-secret"})
    monkeypatch.setenv("FACETMARK_CHAT_BASE_URL", "https://b.example/v1")
    settings = Settings()
    assert not settings.channel_ready("chat")
    assert settings.channel_settings("chat").api_key == ""
    assert Settings(**settings.model_dump()).model_dump() == settings.model_dump()


def test_saved_pending_endpoint_never_receives_the_other_key(client):
    state = client.app.state.fm
    state.settings = Settings(
        data_dir=state.settings.data_dir,
        embed_dim=8,
        chat_base_url="https://chat.example/v1",
        chat_api_key="chat-secret",
        embed_base_url="https://old.example/v1",
        embed_api_key="old-secret",
    )
    r = client.put(
        "/admin/settings",
        json={
            "values": {"embed_base_url": "https://new.example/v1", "embed_api_key": "new-secret"}
        },
    )
    assert r.status_code == 200, r.text
    assert state.settings.channel_settings("embed").base_url == "https://old.example/v1"
    assert state.settings.channel_settings("embed").api_key == "old-secret"
    assert (
        admin.draft_settings(state.settings, state.pending_settings)
        .channel_settings("embed")
        .api_key
        == "new-secret"
    )
    assert (
        client.put(
            "/admin/settings", json={"values": {"chat_base_url": "https://other.example/v1"}}
        ).status_code
        == 200
    )
    assert state.settings.channel_settings("chat").api_key == ""
    assert read_config()["chat_api_key"] == ""


async def test_unconfigured_provider_never_returns_mock_vectors():
    provider = get_provider(Settings())
    with pytest.raises(ProviderError, match="not configured"):
        await provider.embed(["test"])
    await provider.aclose()


def test_probes_are_independent_and_discover_dimension_without_saving(client):
    with respx.mock as router:
        chat = router.post("https://chat.example/v1/chat/completions").respond(
            200, json={"choices": [{"message": {"content": '{"ok":true}'}}]}
        )
        embed = router.post("http://127.0.0.1:11434/v1/embeddings").respond(
            200, json={"data": [{"index": 0, "embedding": [0.2] * 12}]}
        )
        result = client.post(
            "/admin/settings/test",
            json={
                "channel": "embed",
                "embed_base_url": "http://127.0.0.1:11434/v1",
                "embed_allow_no_key": True,
                "embed_model": "small",
            },
        ).json()
        assert result["embed"]["dim"] == 12 and not result["ok"]
        assert not chat.called
        assert "authorization" not in embed.calls.last.request.headers
        result = client.post(
            "/admin/settings/test",
            json={
                "channel": "chat",
                "chat_base_url": "https://chat.example/v1",
                "chat_api_key": "chat-secret",
            },
        ).json()
        assert result["ok"]
        assert chat.calls.last.request.headers["authorization"] == "Bearer chat-secret"
    assert read_config() == {}


@pytest.mark.parametrize("url", ["https://public.example/v1", "http://localhost.evil.example/v1"])
def test_keyless_remote_endpoint_is_rejected(client, url):
    assert (
        client.post(
            "/admin/settings/test", json={"embed_base_url": url, "embed_allow_no_key": True}
        ).status_code
        == 400
    )


def test_probe_errors_redact_secret_and_untrusted_validation_inputs(client, monkeypatch):
    async def fail(self, system, user):
        raise RuntimeError("upstream echoed super-secret-key")

    monkeypatch.setattr("facetmark.providers.OpenAICompatibleProvider.chat_json", fail)
    result = client.post(
        "/admin/settings/test", json={"channel": "chat", "chat_api_key": "super-secret-key"}
    )
    assert "super-secret-key" not in result.text
    assert not result.json()["ok"]
    result = client.put(
        "/admin/settings", json={"values": {"chat_api_key": "super-secret-key", "embed_dim": "bad"}}
    )
    assert result.status_code == 400 and "super-secret-key" not in result.text


def test_browse_filters_paging_ties_and_auth(client):
    state = client.app.state.fm
    for i in range(67):
        service.save_bookmark(
            state.conn,
            f"https://example.test/{i}",
            title=f"Title {i}",
            folder="folder' OR 1=1 --" if i == 0 else "Notes",
            tags=["one"] if i % 2 else ["two"],
            date_added=1700000000,
            settings=state.settings,
        )
    first = client.get("/bookmarks?limit=30").json()
    second = client.get("/bookmarks?limit=30&offset=30").json()
    assert first["total"] == 67 and first["has_more"]
    assert not {b["bookmark_id"] for b in first["items"]} & {
        b["bookmark_id"] for b in second["items"]
    }
    assert client.get("/bookmarks", params={"folder": "folder' OR 1=1 --"}).json()["total"] == 1
    assert client.get("/bookmarks?tag=one").json()["total"] == 33
    assert client.get("/bookmarks/facets").json()["domains"] == [
        {"value": "example.test", "count": 67}
    ]
    client.headers.pop("Authorization")
    assert client.get("/bookmarks").status_code == 401
    assert client.get("/bookmarks/facets").status_code == 401


def test_discovery_requires_selection_and_rejects_arbitrary_path(client, monkeypatch, tmp_path):
    source = tmp_path / "Bookmarks"
    raw = json.dumps(
        {
            "roots": {
                "bookmark_bar": {
                    "type": "folder",
                    "children": [
                        {"type": "url", "name": "Synthetic", "url": "https://synthetic.test"}
                    ],
                }
            }
        }
    )
    source.write_text(raw)
    monkeypatch.setattr(
        "facetmark.workbench.discover_bookmark_files",
        lambda: [(source, "Test browser", "Test profile")],
    )
    listed = client.get("/admin/import/sources").json()["sources"]
    assert str(source) not in json.dumps(listed)
    assert client.post("/admin/import/source", json={"source_id": str(source)}).status_code == 404
    assert (
        client.post("/admin/import/source", json={"source_id": listed[0]["id"]}).status_code == 200
    )
    assert source.read_text() == raw
    assert client.get("/bookmarks").json()["total"] == 1


def test_rebuild_requires_confirmation_and_keeps_original_records(client):
    state = client.app.state.fm
    state.settings.use_mock_provider = True
    bid = service.save_bookmark(
        state.conn, "https://example.test", title="Retained", settings=state.settings
    )["bookmark_id"]
    ensure_vec_tables(state.conn, 8, state.settings.embed_model)
    upsert_content_vector(state.conn, bid, [0.1] * 8)
    assert client.put("/admin/settings", json={"values": {"embed_dim": 16}}).status_code == 200
    assert client.post("/admin/settings/apply", json={}).status_code == 409
    assert client.get("/bookmarks").json()["total"] == 1
    result = client.post("/admin/settings/apply", json={"confirm_rebuild": True})
    assert result.status_code == 200, result.text
    assert (
        result.json()["backup"]
        and (state.settings.data_dir / "backups" / result.json()["backup"]).is_file()
    )
    assert state.settings.embed_dim == 16 and not state.pending_settings
    assert get_meta(state.conn, "embed_dim") is None
    assert client.get("/quick?q=Retained").json()["total"] == 1


async def test_job_completion_and_shutdown_are_persisted(tmp_path, monkeypatch):
    async def complete(*args, **kwargs):
        return service.IndexReport()

    monkeypatch.setattr(service, "index_all", complete)
    runner = admin.JobRunner(tmp_path)
    runner.start(
        Settings(data_dir=tmp_path, use_mock_provider=True), fetch=False, limit=None, force=False
    )
    await runner._task
    assert admin.JobRunner(tmp_path).previous["state"] == "done"

    async def wait(*args, **kwargs):
        await asyncio.sleep(30)

    monkeypatch.setattr(service, "index_all", wait)
    runner.start(
        Settings(data_dir=tmp_path, use_mock_provider=True), fetch=False, limit=None, force=False
    )
    await asyncio.sleep(0.01)
    await runner.shutdown()
    assert admin.JobRunner(tmp_path).previous["state"] == "interrupted"


def test_index_requires_real_config_test_and_explicit_consent(client):
    assert client.post("/admin/index", json={"confirmed": True}).status_code == 409
    state = client.app.state.fm
    state.settings = Settings(data_dir=state.settings.data_dir, api_key="test", embed_dim=8)
    assert client.post("/admin/index", json={}).status_code == 400
    assert client.post("/admin/index", json={"confirmed": True}).status_code == 409


async def test_vector_stages_reject_same_dimension_different_endpoint(client):
    from facetmark.db import SchemaMismatch, set_meta
    from facetmark.enrich.vectors import embed_content
    from facetmark.modelspace import space_id
    from facetmark.search.vectors import vector_lists

    state = client.app.state.fm
    original = Settings(data_dir=state.settings.data_dir, embed_dim=8, api_key="test")
    ensure_vec_tables(state.conn, 8, original.embed_model)
    set_meta(state.conn, "embedding_space", space_id(original))
    changed = original.model_copy(update={"embed_base_url": "https://different.example/v1"})
    with pytest.raises(SchemaMismatch, match="endpoint or model changed"):
        await vector_lists(state.conn, "question", settings=changed)
    with pytest.raises(SchemaMismatch, match="endpoint or model changed"):
        await embed_content(state.conn, settings=changed)


def test_session_filter_is_shared_by_browse_and_query(client):
    state = client.app.state.fm
    bids = [service.save_bookmark(state.conn, f"https://session.example/{i}", title=f"session target {i}", settings=state.settings)["bookmark_id"] for i in range(3)]
    sid = state.conn.execute("INSERT INTO session(started_at,ended_at,size,method) VALUES(1,2,2,'temporal')").lastrowid
    state.conn.executemany("INSERT INTO bookmark_session(bookmark_id,session_id) VALUES(?,?)", [(bid, sid) for bid in bids[:2]])
    state.conn.commit()
    browse = client.get(f"/bookmarks?session={sid}").json()
    search = client.get("/quick", params={"q": f"target session:{sid}"}).json()
    assert {row["bookmark_id"] for row in browse["items"]} == set(bids[:2])
    assert {row["bookmark_id"] for row in search["hits"]} == set(bids[:2])


def test_update_check_and_extension_connection_are_observed(client):
    assert not client.get("/admin/extension-status").json()["recently_connected"]
    client.get("/stats", headers={"X-Facetmark-Client": "extension"})
    assert client.get("/admin/extension-status").json()["recently_connected"]
    with respx.mock as router:
        route = router.get("https://api.github.com/repos/88lin/facetmark/releases/latest")
        route.respond(404)
        assert client.post("/admin/updates/check").json()["latest"] is None
        route.respond(200, json={"tag_name": "v999.0.0"})
        assert client.post("/admin/updates/check").json()["available"]
        route.respond(503)
        assert client.post("/admin/updates/check").status_code == 502


def test_real_provider_setup_apply_index_and_search(client):
    """Exercise the HTTP provider contract without contacting a real model."""
    import httpx

    state = client.app.state.fm
    bid = service.save_bookmark(state.conn, "https://guide.example/sqlite", title="SQLite retrieval guide", settings=state.settings)["bookmark_id"]
    values = {
        "chat_base_url": "https://chat.example/v1", "chat_api_key": "chat-only",
        "chat_model": "chat-test", "embed_base_url": "https://embed.example/v1",
        "embed_api_key": "embed-only", "embed_model": "embed-test", "embed_dim": 8,
    }
    assert not state.settings.use_mock_provider
    with respx.mock as router:
        chat = router.post("https://chat.example/v1/chat/completions").respond(200, json={"choices": [{"message": {"content": json.dumps({"summary": "SQLite provides a reliable local retrieval store.", "key_points": ["Keep the source"], "entities": ["SQLite"], "topics": ["databases"], "utility": "reference", "content_type": "article", "intent_queries": ["How does SQLite store local data?"]})}}]})

        def embeddings(request):
            payload = json.loads(request.content)
            assert request.headers["authorization"] == "Bearer embed-only"
            return httpx.Response(200, json={"data": [{"index": i, "embedding": [1.0] + [0.0] * 7} for i, _ in enumerate(payload["input"])]})

        router.post("https://embed.example/v1/embeddings").mock(side_effect=embeddings)
        assert client.put("/admin/settings", json={"values": values}).status_code == 200
        assert client.post("/admin/settings/apply", json={}).status_code == 409
        for channel in ("chat", "embed"):
            probe = client.post("/admin/settings/test", json={"channel": channel})
            assert probe.status_code == 200 and probe.json()["ok"], probe.text
        assert client.post("/admin/settings/apply", json={}).status_code == 200
        assert client.post("/admin/index", json={"confirmed": True, "fetch": False}).status_code == 200
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            job = client.get("/admin/job").json()
            if job["state"] not in ("running", "cancelling"):
                break
            time.sleep(.02)
        assert job["state"] == "done", job
        assert all(call.request.headers["authorization"] == "Bearer chat-only" for call in chat.calls)
        result = client.post("/search", json={"q": "SQLite"})
        assert result.status_code == 200 and bid in [row["bookmark_id"] for row in result.json()["hits"]]
        assert client.get("/admin/setup-status").json()["has_vectors"]
