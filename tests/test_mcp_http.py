"""Cloud-run HTTP protocol and desktop MCP authority regression."""
from __future__ import annotations

import asyncio
import json
import sqlite3
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from facetmark.api import create_app
from facetmark.config import Settings
from facetmark.configfile import config_path, read_config
from facetmark.mcp_http import PROTOCOL_VERSION
from facetmark.mcp_server import Ctx, create_server


@pytest.fixture
def client(tmp_path):
    settings = Settings(data_dir=tmp_path / "mcp-library", use_mock_provider=True)
    with TestClient(create_app(settings), base_url="http://127.0.0.1:8787",
                    client=("127.0.0.1", 42000)) as local:
        yield local


def pairing(client):
    return {"Authorization": "Bearer " + client.app.state.fm.token}


def configure(client, **values):
    response = client.post("/admin/mcp", headers=pairing(client), json=values)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    return response.json()


def rpc(client, token, method, params=None, request_id=1, extra_headers=None):
    return client.post("/mcp/", headers={"Authorization": "Bearer " + token,
        "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": PROTOCOL_VERSION,
        **(extra_headers or {})}, json={"jsonrpc": "2.0", "id": request_id,
        "method": method, "params": params or {}})


def result(response):
    assert response.status_code == 200, response.text
    data = response.json()
    assert "error" not in data, data
    return data["result"]


def structured(tool_result):
    return tool_result.get("structuredContent") or json.loads(tool_result["content"][0]["text"])


def test_disabled_mcp_and_the_admin_control_are_separate_authorities(client):
    assert client.get("/admin/mcp").status_code == 401
    info = client.get("/admin/mcp", headers=pairing(client)).json()
    assert info["enabled"] is False and info["running"] is False
    assert info["status"] == "disabled" and not info["configured"]
    assert info["transport_ready"] is True
    assert rpc(client, "", "initialize").status_code == 404
    info = configure(client, enabled=True)
    assert info["enabled"] and info["running"] and info["configured"]
    assert info["token"] and info["token"] != client.app.state.fm.token
    assert info["endpoint"] == "http://127.0.0.1:8787/mcp/"
    assert info["client_config"]["mcpServers"]["facetmark"]["headers"]["Authorization"] == "Bearer " + info["token"]
    ordinary = client.get("/admin/settings", headers=pairing(client)).json()
    assert "mcp_token" not in {row["key"] for row in ordinary["settings"]}
    assert info["token"] not in json.dumps(ordinary)
    assert rpc(client, "", "initialize").status_code == 401
    assert rpc(client, client.app.state.fm.token, "initialize").status_code == 401


def test_http_protocol_catalog_write_read_and_resource_match_stdio_capabilities(client):
    info = configure(client, enabled=True)
    token = info["token"]
    init = result(rpc(client, token, "initialize", {"protocolVersion": PROTOCOL_VERSION,
        "capabilities": {}, "clientInfo": {"name": "facetmark-http-test", "version": "1"}}))
    assert init["serverInfo"]["name"] == "facetmark"
    notified = client.post("/mcp/", headers={"Authorization": "Bearer " + token,
        "Accept": "application/json, text/event-stream"},
        json={"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert notified.status_code == 202
    tools = result(rpc(client, token, "tools/list"))["tools"]
    assert {row["name"] for row in tools} == {"search_bookmarks", "get_bookmark", "list_sessions",
        "get_session", "find_related", "synthesize", "suggest_from_context", "check_link_health", "save_bookmark"}
    resources = result(rpc(client, token, "resources/list"))["resources"]
    assert [row["uri"] for row in resources] == ["facetmark://stats"]
    templates = result(rpc(client, token, "resources/templates/list"))["resourceTemplates"]
    assert {row["uriTemplate"] for row in templates} == {"bookmark://{bookmark_id}", "session://{session_id}"}
    created = structured(result(rpc(client, token, "tools/call", {"name": "save_bookmark",
        "arguments": {"url": "https://synthetic.example/mcp-http", "title": "Synthetic protocol bookmark"}})))
    record = structured(result(rpc(client, token, "tools/call", {"name": "get_bookmark",
        "arguments": {"bookmark_id": created["bookmark_id"]}})))
    assert record["url"] == "https://synthetic.example/mcp-http"
    content = result(rpc(client, token, "resources/read", {"uri": "facetmark://stats"}))["contents"]
    assert json.loads(content[0]["text"])["bookmarks"] >= 1
    checked = configure(client, probe=True)
    assert checked["probe"] == {"ok": True, "server": "facetmark", "tools": 9,
        "resources": 1, "templates": 2, "transport": "streamable-http"}
    assert checked["last_request_at"] is not None


def test_disable_and_key_rotation_revoke_old_http_authority_and_keep_other_settings(client):
    first = configure(client, enabled=True)
    state = client.app.state.fm
    old_provider = state.provider
    state.probe_results["chat"] = {"fingerprint": "existing-test", "result": {"ok": True}}
    second = configure(client, rotate_token=True)
    assert second["token"] != first["token"]
    assert rpc(client, first["token"], "tools/list").status_code == 401
    assert result(rpc(client, second["token"], "tools/list"))["tools"]
    disabled = configure(client, enabled=False)
    assert disabled["status"] == "disabled" and not disabled["running"]
    assert rpc(client, second["token"], "tools/list").status_code == 404
    saved = read_config(config_path(state.settings.data_dir))
    assert saved["mcp_enabled"] is False and saved["mcp_token"] == second["token"]
    assert state.provider is old_provider
    assert state.probe_results["chat"]["fingerprint"] == "existing-test"


@pytest.mark.parametrize("headers", [{"Host": "evil.example:8787"},
    {"Origin": "https://evil.example"}, {"Origin": "null"},
    {"Origin": "http://127.0.0.1:9999"}])
def test_mcp_rejects_rebinding_and_cross_site_origins_even_with_a_token(client, headers):
    token = configure(client, enabled=True)["token"]
    assert rpc(client, token, "tools/list", extra_headers=headers).status_code == 403


def test_mcp_and_its_settings_are_loopback_only_even_with_valid_tokens(tmp_path):
    settings = Settings(data_dir=tmp_path / "remote-check", use_mock_provider=True,
                        mcp_enabled=True, mcp_token="synthetic-mcp-token")
    with TestClient(create_app(settings), base_url="http://127.0.0.1:8787",
                    client=("10.0.0.9", 42000)) as remote:
        assert rpc(remote, settings.mcp_token, "tools/list").status_code == 403
        assert remote.get("/admin/mcp", headers=pairing(remote)).status_code == 403


def test_mcp_transport_shuts_down_with_the_root_service_without_owning_its_connection(tmp_path):
    app = create_app(Settings(data_dir=tmp_path / "shutdown-check", use_mock_provider=True))
    with TestClient(app, base_url="http://127.0.0.1:8787",
                    client=("127.0.0.1", 42000)) as local:
        assert configure(local, enabled=True)["running"]
        bridge, conn = app.state.mcp_bridge, app.state.fm.conn
        assert not bridge.server.facetmark_ctx.owns_conn
    assert bridge.transport_ready is False
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")


def test_environment_mcp_settings_cannot_be_overwritten_and_probe_does_not_write_config(client, monkeypatch):
    configure(client, enabled=True)
    state = client.app.state.fm
    before = config_path(state.settings.data_dir).read_bytes()
    monkeypatch.setenv("FACETMARK_MCP_TOKEN", "externally-managed")
    response = client.post("/admin/mcp", headers=pairing(client), json={"rotate_token": True})
    assert response.status_code == 409
    assert configure(client, probe=True)["probe"]["ok"]
    assert config_path(state.settings.data_dir).read_bytes() == before


def test_mcp_mutations_wait_for_index_tasks_and_stored_health_reads_remain_available(client, monkeypatch):
    token = configure(client, enabled=True)["token"]
    state = client.app.state.fm
    with monkeypatch.context() as patch:
        patch.setattr(type(state.jobs), "running", property(lambda _self: True))
        denied = result(rpc(client, token, "tools/call", {"name": "save_bookmark",
            "arguments": {"url": "https://synthetic.example/must-not-be-added"}}))
        assert denied["isError"] and "running index task" in denied["content"][0]["text"]
        read = result(rpc(client, token, "tools/call", {"name": "check_link_health", "arguments": {"probe": False}}))
        assert not read.get("isError", False)
        denied_probe = result(rpc(client, token, "tools/call", {"name": "check_link_health", "arguments": {"probe": True}}))
        assert denied_probe["isError"]
    assert state.conn.execute("SELECT COUNT(*) FROM bookmark").fetchone()[0] == 0


async def test_shared_mcp_context_serializes_callbacks_and_uses_current_settings(conn, settings, monkeypatch):
    from facetmark import service

    state = SimpleNamespace(settings=settings, conn=conn, lock=asyncio.Lock(),
                            jobs=SimpleNamespace(running=False), provider=SimpleNamespace())
    active = 0
    maximum = 0
    seen = []

    async def search(_conn, _query, **values):
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        seen.append(values["settings"].chat_model)
        await asyncio.sleep(0)
        active -= 1
        return SimpleNamespace(as_dict=lambda: {"hits": [], "expanded": []})

    monkeypatch.setattr(service, "search", search)
    server = create_server(context=Ctx(None, None, state_getter=lambda: state))
    await asyncio.gather(server.call_tool("search_bookmarks", {"query": "one"}),
                         server.call_tool("search_bookmarks", {"query": "two"}))
    state.settings = settings.model_copy(update={"chat_model": "updated-model"})
    await server.call_tool("search_bookmarks", {"query": "three"})
    assert maximum == 1 and seen == [settings.chat_model, settings.chat_model, "updated-model"]
    await server.facetmark_ctx.aclose()
    assert conn.execute("SELECT 1").fetchone()[0] == 1
