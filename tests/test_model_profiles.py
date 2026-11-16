"""Named connections keep credentials, validation and channel boundaries local."""
from __future__ import annotations

import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from facetmark import admin
from facetmark.api import create_app
from facetmark.config import Settings
from facetmark.configfile import read_config


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FACETMARK_DATA_DIR", str(tmp_path))

    async def probe(settings, channel=None):
        channels = [channel] if channel else ["chat", "embed"]
        return {name: {"ok": getattr(settings, f"{name}_model") != "broken",
                       "model": getattr(settings, f"{name}_model"), "ms": 1,
                       **({"dim": settings.embed_dim, "dim_matches": True} if name == "embed" else {})}
                for name in channels}

    monkeypatch.setattr(admin, "probe", probe)
    with TestClient(create_app(Settings(data_dir=tmp_path, embed_dim=8)),
                    client=("127.0.0.1", 40000)) as value:
        value.headers["Authorization"] = "Bearer " + value.app.state.fm.token
        yield value


def save(client, name="日常摘要", channel="chat", **overrides):
    values = {f"{channel}_base_url": "https://synthetic.invalid/v1",
              f"{channel}_api_key": "SYNTHETIC_SECRET_DO_NOT_RETURN",
              f"{channel}_model": "summary-model", **overrides}
    assert client.post("/admin/settings/test", json={"channel": channel, **values}).status_code == 200
    response = client.post("/admin/model-profiles", json={"name": name, "channel": channel, "values": values})
    assert response.status_code == 200, response.text
    return response.json()["profile"]


def test_saved_profile_reopens_and_applies_without_a_new_test(client, tmp_path, monkeypatch):
    profile = save(client)
    for index in range(20):
        client.post("/admin/settings/test", json={"channel": "chat", "chat_model": f"draft-{index}"})
    with TestClient(create_app(Settings(data_dir=tmp_path, embed_dim=8)),
                    client=("127.0.0.1", 40000)) as reopened:
        reopened.headers["Authorization"] = "Bearer " + reopened.app.state.fm.token
        async def unexpected(*args, **kwargs):
            raise AssertionError("Applying a tested connection must not call the model")
        monkeypatch.setattr(admin, "probe", unexpected)
        response = reopened.post(f"/admin/model-profiles/{profile['id']}/apply")
        assert response.status_code == 200, response.text
        assert reopened.app.state.fm.settings.chat_model == "summary-model"
        assert reopened.app.state.fm.settings.chat_api_key == "SYNTHETIC_SECRET_DO_NOT_RETURN"
        assert reopened.get("/admin/setup-status").json()["channels"]["chat"]["tested"]
        assert "SYNTHETIC_SECRET_DO_NOT_RETURN" not in response.text
        assert read_config()["chat_model"] == "summary-model"


def test_profile_views_never_return_keys_and_do_not_activate_on_save(client, tmp_path):
    profile = save(client)
    assert profile["tested"] and profile["key_set"]
    assert client.app.state.fm.settings.chat_model != "summary-model"
    listing = client.get("/admin/model-profiles").json()
    assert listing["profiles"][0]["name"] == "日常摘要"
    assert "SYNTHETIC_SECRET_DO_NOT_RETURN" not in json.dumps(listing)
    assert "chat_api_key" not in json.dumps(listing)
    assert "SYNTHETIC_SECRET_DO_NOT_RETURN" in (tmp_path / "model-profiles.json").read_text(encoding="utf-8")


def test_switching_chat_keeps_embedding_settings_and_clears_inherited_keys(client):
    state = client.app.state.fm
    profile = save(client, chat_base_url="https://other.synthetic.invalid/v1", chat_api_key="")
    response = client.post(f"/admin/model-profiles/{profile['id']}/apply")
    assert response.status_code == 200, response.text
    assert state.settings.chat_base_url == "https://other.synthetic.invalid/v1"
    assert state.settings.chat_api_key == ""
    assert state.settings.embed_dim == 8
    assert state.settings.embed_model == "text-embedding-3-small"


def test_changed_embedding_profile_remains_pending_until_the_safe_apply_flow(client):
    profile = save(client, channel="embed", embed_dim=16)
    response = client.post(f"/admin/model-profiles/{profile['id']}/apply")
    assert response.status_code == 200, response.text
    assert client.app.state.fm.settings.embed_dim == 8
    assert client.app.state.fm.pending_settings["embed_dim"] == 16
    assert "embed_dim" in response.json()["restart_required"]
    assert response.json()["profile"]["tested"]


def test_retry_with_the_same_id_keeps_one_profile_and_rename_preserves_validation(client):
    profile = save(client)
    response = client.put(f"/admin/model-profiles/{profile['id']}", json={"name": "长文本的命名连接"})
    assert response.status_code == 200, response.text
    assert response.json()["profile"]["tested"]
    for _ in range(2):
        response = client.post("/admin/model-profiles", json={"id": "retry-once", "name": "可重试连接", "channel": "chat"})
        assert response.status_code == 200, response.text
    assert len(client.get("/admin/model-profiles").json()["profiles"]) == 2


def test_retry_keeps_the_original_snapshot_even_if_current_settings_have_changed(client):
    body = {"id": "lost-response", "name": "初始连接", "channel": "chat"}
    first = client.post("/admin/model-profiles", json=body)
    assert first.status_code == 200
    assert client.put("/admin/settings", json={"values": {"chat_model": "new-current-model"}}).status_code == 200
    retry = client.post("/admin/model-profiles", json=body)
    assert retry.status_code == 200
    assert retry.json()["profile"]["model"] == first.json()["profile"]["model"]
    assert client.post("/admin/model-profiles", json={**body, "name": "different"}).status_code == 409


@pytest.mark.parametrize("result", [{}, {"ok": False}, {"ok": True, "dim_matches": False}])
def test_failed_or_incomplete_probe_files_never_show_a_ready_connection(tmp_path, result):
    settings = Settings(data_dir=tmp_path, chat_api_key="synthetic-key")
    probes = {"chat": {"fingerprint": admin.probe_fingerprint(settings, "chat"), "result": result}}
    assert not admin.connection_status(settings, "chat", probes)["tested"]


def test_unknown_or_cross_channel_values_and_duplicate_names_are_rejected(client):
    for values in ({"privacy_excluded_domains": ["example.com"]}, {"embed_model": "wrong-channel"}):
        response = client.post("/admin/model-profiles", json={"name": "Invalid", "channel": "chat", "values": values})
        assert response.status_code == 400, response.text
    save(client, name="My connection")
    response = client.post("/admin/model-profiles", json={"name": "  my CONNECTION  ", "channel": "chat"})
    assert response.status_code == 409, response.text
    assert client.post("/admin/model-profiles", json={"name": "   ", "channel": "chat"}).status_code == 422


def test_environment_locks_and_active_work_prevent_application(client, monkeypatch):
    profile = save(client)
    monkeypatch.setenv("FACETMARK_CHAT_MODEL", "locked-model")
    assert client.post(f"/admin/model-profiles/{profile['id']}/apply").status_code == 409
    monkeypatch.delenv("FACETMARK_CHAT_MODEL")
    state = client.app.state.fm
    state.model_users += 1
    try:
        assert client.post(f"/admin/model-profiles/{profile['id']}/apply").status_code == 409
    finally:
        state.model_users -= 1
    assert state.settings.chat_model != "summary-model"


def test_new_failed_test_revokes_the_profile_proof_instead_of_resurrecting_it(client, monkeypatch):
    profile = save(client)
    async def failure(settings, channel=None):
        return {"chat": {"ok": False, "model": "summary-model", "error": "Synthetic quota error"}}
    monkeypatch.setattr(admin, "probe", failure)
    result = client.post("/admin/settings/test", json={"channel": "chat", "chat_base_url": "https://synthetic.invalid/v1",
                         "chat_api_key": "SYNTHETIC_SECRET_DO_NOT_RETURN", "chat_model": "summary-model"})
    assert not result.json()["chat"]["ok"]
    assert not client.get("/admin/model-profiles").json()["profiles"][0]["tested"]
    assert client.post(f"/admin/model-profiles/{profile['id']}/apply").status_code == 200
    assert not client.get("/admin/setup-status").json()["channels"]["chat"]["tested"]


def test_broken_profile_file_is_reported_and_never_overwritten(client, tmp_path):
    path = tmp_path / "model-profiles.json"
    path.write_text('{"broken": "SYNTHETIC_SECRET_DO_NOT_RETURN"}', encoding="utf-8")
    before = path.read_bytes()
    response = client.get("/admin/model-profiles")
    assert response.status_code == 500
    assert "SYNTHETIC_SECRET_DO_NOT_RETURN" not in response.text
    assert client.post("/admin/model-profiles", json={"name": "新连接", "channel": "chat"}).status_code == 500
    assert path.read_bytes() == before


def test_removal_keeps_the_current_connection_and_bookmarks(client):
    profile = save(client)
    bookmark = client.post("/bookmark", json={"url": "https://synthetic.invalid/kept-bookmark", "title": "Kept locally"})
    assert bookmark.status_code == 200
    bookmark_id = bookmark.json()["bookmark_id"]
    assert client.post(f"/admin/model-profiles/{profile['id']}/apply").status_code == 200
    assert client.delete(f"/admin/model-profiles/{profile['id']}").status_code == 200
    assert client.app.state.fm.settings.chat_model == "summary-model"
    assert client.get("/admin/model-profiles").json()["profiles"] == []
    assert client.get(f"/bookmark/{bookmark_id}").status_code == 200
    assert client.delete(f"/admin/model-profiles/{profile['id']}").status_code == 404


def test_profile_routes_require_pairing_and_loopback(client):
    token = client.headers.pop("Authorization")
    assert client.get("/admin/model-profiles").status_code == 401
    client.headers["Authorization"] = token
    client.app.state.fm.settings = client.app.state.fm.settings.model_copy(update={"admin_api": False})
    assert client.get("/admin/model-profiles").status_code == 403


def test_an_inflight_connection_test_blocks_setting_writes_and_releases_its_reservation(client, monkeypatch):
    started = threading.Event()
    release = asyncio.Event()

    async def waiting(settings, channel=None):
        started.set()
        await release.wait()
        return {"chat": {"ok": True, "model": settings.chat_model}}

    monkeypatch.setattr(admin, "probe", waiting)
    with ThreadPoolExecutor(max_workers=1) as executor:
        pending = executor.submit(client.post, "/admin/settings/test", json={"channel": "chat"})
        try:
            assert started.wait(timeout=5)
            assert client.put("/admin/settings", json={"values": {"chat_model": "do-not-apply"}}).status_code == 409
        finally:
            client.portal.call(release.set)
        assert pending.result(timeout=5).status_code == 200
    assert client.app.state.fm.model_users == 0
    assert client.put("/admin/settings", json={"values": {"chat_model": "apply-after-test"}}).status_code == 200
