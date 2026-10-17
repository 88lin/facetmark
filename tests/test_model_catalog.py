import json
import os
import sys
from pathlib import Path

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from facetmark import local_agents, model_catalog
from facetmark.api import create_app
from facetmark.config import Settings
from facetmark.providers import ProviderError


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    for key in ("CODEX_HOME", "CLAUDE_CONFIG_DIR", "ANTHROPIC_MODEL", "XDG_CONFIG_HOME",
                "XDG_DATA_HOME", "OPENCODE_CONFIG", "OPENCODE_CONFIG_DIR",
                "OPENCODE_CONFIG_CONTENT", "OPENCODE_AUTH_CONTENT"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(local_agents, "selected_agent", lambda value: value)


async def test_codex_uses_cached_choices_and_default_when_cli_cannot_list(tmp_path, monkeypatch):
    root = tmp_path / ".codex"
    root.mkdir()
    (root / "config.toml").write_text('model = "configured-model"\n', encoding="utf-8")
    (root / "models_cache.json").write_text(json.dumps({"models": [
        {"slug": "first", "display_name": "First"}, {"slug": "hidden", "visibility": "hidden"},
        {"slug": "first"}, {"slug": None}, {"other": "ignored"},
    ]}), encoding="utf-8")

    async def unavailable(*args):
        raise ProviderError("older CLI")

    monkeypatch.setattr(model_catalog, "_cli_catalog", unavailable)
    data = await model_catalog.agent_catalog("codex")
    assert data["default_model"] == "configured-model"
    assert [item["id"] for item in data["models"]] == ["configured-model", "first"]
    assert data["warning"] == "cached_catalog"


async def test_claude_lists_aliases_and_custom_models_without_exposing_credentials(tmp_path):
    root = tmp_path / ".claude"
    root.mkdir()
    content = json.dumps({"model": "custom/summary", "env": {
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "routed/sonnet", "ANTHROPIC_API_KEY": "private-test-secret",
    }})
    config = root / "settings.json"
    config.write_text(content, encoding="utf-8")
    data = await model_catalog.agent_catalog("claude")
    assert {item["id"] for item in data["models"]} == {"custom/summary", "sonnet", "opus", "haiku", "routed/sonnet"}
    assert "private-test-secret" not in json.dumps(data)
    assert config.read_text(encoding="utf-8") == content


async def test_codex_refresh_recovers_from_corrupt_cache(tmp_path, monkeypatch):
    root = tmp_path / ".codex"
    root.mkdir()
    (root / "models_cache.json").write_text("{broken", encoding="utf-8")

    async def live(*args):
        return '{"models":[{"slug":"fresh-model"}]}'

    monkeypatch.setattr(model_catalog, "_cli_catalog", live)
    data = await model_catalog.agent_catalog("codex")
    assert [item["id"] for item in data["models"]] == ["fresh-model"]
    assert data["warning"] == ""


async def test_opencode_lists_live_catalog_and_preserves_source_config(tmp_path, monkeypatch):
    root = tmp_path / ".config/opencode"
    root.mkdir(parents=True)
    config = root / "opencode.jsonc"
    original = '{"model":"local/first", "provider":{"local":{"models":{"first":{}}}},}'
    config.write_text(original, encoding="utf-8")

    async def live(*args):
        return "startup log\nlocal/first\nlocal/second\nlocal/second\n{not a model}\n"

    monkeypatch.setattr(model_catalog, "_cli_catalog", live)
    data = await model_catalog.agent_catalog("opencode")
    assert [item["id"] for item in data["models"]] == ["local/first", "local/second"]
    assert data["default_model"] == "local/first"
    assert config.read_text(encoding="utf-8") == original


async def test_catalog_child_uses_no_shell_and_returns_utf8(tmp_path, monkeypatch):
    script = tmp_path / "model fixture.py"
    script.write_text('import json\nprint(json.dumps({"models":[{"slug":"fixture","name":"中文"}]}, ensure_ascii=False))', encoding="utf-8")
    monkeypatch.setattr(local_agents, "resolve_command", lambda agent: [sys.executable, str(script)])
    output = await model_catalog._cli_catalog("codex", tmp_path, {**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert json.loads(output)["models"][0]["name"] == "中文"


@respx.mock
async def test_endpoint_models_use_channel_key_and_deduplicate_choices():
    route = respx.get("https://models.example/v1/models").respond(200, json={"data": [
        {"id": "summary"}, {"id": "summary"}, {"id": "embedding"}, {"bad": "ignored"},
    ]})
    data = await model_catalog.endpoint_catalog(Settings(
        chat_base_url="https://models.example/v1", chat_api_key="chat-secret", embed_api_key="embed-secret"), "chat")
    assert route.calls.last.request.headers["Authorization"] == "Bearer chat-secret"
    assert [item["id"] for item in data["models"]] == ["summary", "embedding"]
    assert "secret" not in json.dumps(data)


@pytest.mark.parametrize("status", [401, 403, 404, 302, 500])
@respx.mock
async def test_catalog_errors_never_echo_service_credentials(status):
    respx.get("https://models.example/v1/models").respond(status, text="private-test-secret", headers={"Location": "https://elsewhere.example/models"})
    with pytest.raises(ProviderError) as exc:
        await model_catalog.endpoint_catalog(Settings(chat_base_url="https://models.example/v1", chat_api_key="private-test-secret"), "chat")
    assert "private-test-secret" not in str(exc.value)


@respx.mock
def test_model_discovery_uses_draft_without_saving_or_marking_tested(tmp_path, monkeypatch):
    monkeypatch.setenv("FACETMARK_DATA_DIR", str(tmp_path))
    route = respx.get("https://draft.example/v1/models").respond(200, json={"data": [{"id": "chosen"}]})
    with TestClient(create_app(Settings(data_dir=tmp_path, embed_dim=8)), client=("127.0.0.1", 40000)) as client:
        client.headers["Authorization"] = f"Bearer {client.app.state.fm.token}"
        before = client.get("/admin/settings").json()
        response = client.post("/admin/settings/models", json={"channel": "chat", "chat_base_url": "https://draft.example/v1", "chat_api_key": "draft-secret"})
        assert response.status_code == 200
        assert response.json()["models"][0]["id"] == "chosen"
        assert route.calls.last.request.headers["Authorization"] == "Bearer draft-secret"
        assert client.get("/admin/settings").json() == before
        assert not client.app.state.fm.probe_results
        client.headers.clear()
        assert client.post("/admin/settings/models", json={"channel": "chat"}).status_code == 401


@respx.mock
async def test_unavailable_endpoint_has_a_retryable_sanitized_error():
    respx.get("https://models.example/v1/models").mock(side_effect=httpx.ConnectError("private URL"))
    with pytest.raises(ProviderError, match="Check the connection"):
        await model_catalog.endpoint_catalog(Settings(chat_base_url="https://models.example/v1", chat_api_key="secret"), "chat")
