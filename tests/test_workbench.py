"""Regression tests for independent credentials, browsing and safe setup."""

from __future__ import annotations

import asyncio
import json

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
