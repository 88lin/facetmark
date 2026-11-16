"""Original MCP configuration acceptance and read-only recovery."""
from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from facetmark.api import create_app
from facetmark.config import Settings
from facetmark.configfile import config_path, read_config, update_config


@pytest.fixture
def local(tmp_path):
    settings = Settings(data_dir=tmp_path / "mcp-operations", use_mock_provider=True)
    with TestClient(create_app(settings), base_url="http://127.0.0.1:8787", client=("127.0.0.1", 42000)) as client:
        yield client


def headers(client):
    return {"Authorization": "Bearer " + client.app.state.fm.token}


def status(client):
    return client.get("/admin/mcp", headers=headers(client)).json()


def change(client, request_id, **values):
    body = {"request_id": request_id, "expected_revision": status(client).get("revision", "0" * 64), **values}
    response = client.post("/admin/mcp", headers=headers(client), json=body)
    assert response.status_code == 200, response.text
    return body, response.json()


def test_replaying_an_original_rotation_does_not_rotate_again_or_reenable_later_disabled_service(local):
    change(local, "enable-first", enabled=True)
    original, accepted = change(local, "rotate-original", rotate_token=True)
    _, later = change(local, "rotate-later", rotate_token=True)
    change(local, "disable-later", enabled=False)
    replay = local.post("/admin/mcp", headers=headers(local), json=original)
    assert replay.status_code == 200
    view = replay.json()
    assert view["token"] == later["token"] != accepted["token"]
    assert not view["enabled"] and view["operation"]["superseded"]
    assert view["operation"]["request_id"] == "rotate-original"
    assert view["operation"]["accepted_revision"] == accepted["operation"]["accepted_revision"]
    changed = local.post("/admin/mcp", headers=headers(local), json={**original, "rotate_token": False, "enabled": True})
    assert changed.status_code == 409
    assert status(local)["token"] == later["token"] and not status(local)["enabled"]


def test_original_receipt_survives_restart_and_discloses_only_the_current_configuration(local):
    change(local, "enable-original", enabled=True)
    _, accepted = change(local, "rotate-before-restart", rotate_token=True)
    change(local, "disabled-before-restart", enabled=False)
    path = config_path(local.app.state.fm.settings.data_dir)
    history = read_config(path)["_mcp_operations"]
    assert accepted["token"] not in history and "rotate-before-restart" in history
    settings = Settings(data_dir=local.app.state.fm.settings.data_dir, use_mock_provider=True,
                        **{key: value for key, value in read_config(path).items() if key in {"mcp_enabled", "mcp_token"}})
    with TestClient(create_app(settings), base_url="http://127.0.0.1:8787", client=("127.0.0.1", 42000)) as restarted:
        before = path.read_bytes()
        found = restarted.get("/admin/mcp/operations/rotate-before-restart", headers=headers(restarted))
        assert found.status_code == 200 and found.headers["cache-control"] == "no-store"
        assert found.json()["status"]["token"] == accepted["token"]
        assert not found.json()["status"]["enabled"]
        assert path.read_bytes() == before
        assert restarted.get("/admin/mcp/operations/not-accepted", headers=headers(restarted)).status_code == 404
        assert restarted.get("/admin/mcp/operations/rotate-before-restart").status_code == 401


def test_stale_configuration_cannot_rotate_or_reenable_a_newer_configuration(local):
    baseline = status(local)["revision"]
    change(local, "another-window", enabled=True)
    token = status(local)["token"]
    rejected = local.post("/admin/mcp", headers=headers(local), json={
        "request_id": "stale-window", "expected_revision": baseline, "rotate_token": True})
    assert rejected.status_code == 409
    assert status(local)["token"] == token
    assert local.get("/admin/mcp/operations/stale-window", headers=headers(local)).status_code == 404
    baseline = status(local)["revision"]
    update_config({"mcp_enabled": False}, config_path(local.app.state.fm.settings.data_dir))
    rejected = local.post("/admin/mcp", headers=headers(local), json={
        "request_id": "stale-file", "expected_revision": baseline, "enabled": True})
    assert rejected.status_code == 409


def test_config_replace_failure_accepts_neither_token_nor_operation_and_original_retry_is_possible(local, monkeypatch):
    change(local, "enable-before-error", enabled=True)
    path = config_path(local.app.state.fm.settings.data_dir)
    before, token = path.read_bytes(), status(local)["token"]
    body = {"request_id": "failed-rotation", "expected_revision": status(local)["revision"], "rotate_token": True}
    with monkeypatch.context() as patch:
        def fail_replace(*_args):
            raise OSError("synthetic config replacement failure")
        patch.setattr("facetmark.configfile.os.replace", fail_replace)
        with pytest.raises(OSError, match="replacement failure"):
            local.post("/admin/mcp", headers=headers(local), json=body)
    assert path.read_bytes() == before and status(local)["token"] == token
    assert local.get("/admin/mcp/operations/failed-rotation", headers=headers(local)).status_code == 404
    accepted = local.post("/admin/mcp", headers=headers(local), json=body)
    assert accepted.status_code == 200 and accepted.json()["token"] != token


def test_original_replay_is_read_only_even_after_environment_settings_become_locked(local, monkeypatch):
    original, accepted = change(local, "accepted-enabled", enabled=True)
    path = config_path(local.app.state.fm.settings.data_dir)
    before = path.read_bytes()
    monkeypatch.setenv("FACETMARK_MCP_TOKEN", "externally-managed")
    replay = local.post("/admin/mcp", headers=headers(local), json=original)
    assert replay.status_code == 200 and replay.json()["token"] == accepted["token"]
    assert path.read_bytes() == before


def test_corrupt_recovery_history_is_not_treated_as_an_absent_original_operation(local):
    change(local, "retained-original", enabled=True)
    update_config({"_mcp_operations": json.dumps({"retained-original": {"fingerprint": None}})},
                  config_path(local.app.state.fm.settings.data_dir))
    found = local.get("/admin/mcp/operations/retained-original", headers=headers(local))
    assert found.status_code == 409 and "history" in found.json()["detail"]


def test_closing_an_unaccepted_change_fences_its_late_rotation_and_is_idempotent(local):
    change(local, "enabled-before-close", enabled=True)
    body = {"request_id": "not-arrived-yet", "expected_revision": status(local)["revision"], "rotate_token": True}
    token = status(local)["token"]
    closed = local.post("/admin/mcp/operations/not-arrived-yet/close", headers=headers(local), json=body)
    assert closed.status_code == 200 and closed.json()["state"] == "closed"
    replay = local.post("/admin/mcp", headers=headers(local), json=body)
    assert replay.status_code == 409 and status(local)["token"] == token
    assert local.post("/admin/mcp/operations/not-arrived-yet/close", headers=headers(local), json=body).json() == closed.json()
    different = local.post("/admin/mcp/operations/not-arrived-yet/close", headers=headers(local),
                           json={**body, "enabled": False})
    assert different.status_code == 409 and status(local)["token"] == token


def test_acceptance_winning_the_close_race_keeps_its_receipt_and_current_configuration(local):
    body, accepted = change(local, "accepted-before-close", enabled=True)
    change(local, "disabled-after-acceptance", enabled=False)
    closed = local.post("/admin/mcp/operations/accepted-before-close/close", headers=headers(local), json=body)
    assert closed.status_code == 200 and closed.json()["state"] == "accepted"
    assert closed.json()["status"]["token"] == accepted["token"] and not closed.json()["status"]["enabled"]


async def test_late_protocol_check_cannot_publish_a_result_for_a_replaced_configuration(local, monkeypatch):
    change(local, "enable-probe", enabled=True)
    started, release = asyncio.Event(), asyncio.Event()
    bridge = local.app.state.mcp_bridge

    async def probe(_request):
        started.set()
        await release.wait()
        return {"ok": True, "tools": 9}

    monkeypatch.setattr(bridge, "probe", probe)
    import httpx
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=local.app, client=("127.0.0.1", 0)),
                                 base_url="http://127.0.0.1:8787") as client:
        pending = asyncio.create_task(client.post("/admin/mcp", headers=headers(local), json={"probe": True}))
        await started.wait()
        body = {"request_id": "rotate-during-probe", "expected_revision": status(local)["revision"], "rotate_token": True}
        rotated = await client.post("/admin/mcp", headers=headers(local), json=body)
        assert rotated.status_code == 200
        release.set()
        completed = await pending
        assert completed.status_code == 200 and completed.json()["probe"] is None
        assert bridge.last_probe is None
