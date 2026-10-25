import json

import pytest
from fastapi.testclient import TestClient

from facetmark import admin, local_agents, model_catalog
from facetmark.api import create_app
from facetmark.config import Settings
from facetmark.providers import ProviderError


@pytest.fixture(autouse=True)
def isolated_agent_configuration(tmp_path, monkeypatch):
    monkeypatch.setattr(local_agents.Path, "home", lambda: tmp_path)
    for key in ("CODEX_HOME", "CLAUDE_CONFIG_DIR", "ANTHROPIC_MODEL", "CLAUDE_CODE_EFFORT_LEVEL",
                "OPENCODE_CONFIG", "OPENCODE_CONFIG_DIR", "OPENCODE_CONFIG_CONTENT",
                "OPENCODE_AUTH_CONTENT", "XDG_CONFIG_HOME"):
        monkeypatch.delenv(key, raising=False)


@pytest.mark.parametrize("agent,effort,flag", [
    ("codex", "xhigh", "-c"),
    ("claude", "high", "--effort"),
    ("opencode", "careful-summary", "--variant"),
])
def test_explicit_thinking_setting_reaches_each_cli_without_changing_parent_environment(tmp_path, agent, effort, flag):
    original = {"CODEX_HOME": str(tmp_path), "CLAUDE_CODE_EFFORT_LEVEL": "low"}
    args, env = local_agents.build_invocation(agent, tmp_path, model="chosen/model",
                                             reasoning_effort=effort, environ=original)
    if agent == "codex":
        assert 'model_reasoning_effort="xhigh"' in args
        assert 'model_reasoning_summary="none"' in args
    else:
        assert args[args.index(flag) + 1] == effort
    assert args[args.index("--model") + 1] == "chosen/model"
    assert original["CLAUDE_CODE_EFFORT_LEVEL"] == "low"
    if agent == "claude":
        assert env["CLAUDE_CODE_EFFORT_LEVEL"] == "high"


def test_claude_effort_cannot_turn_on_workflow_or_invent_an_off_mode(tmp_path):
    for effort in ("none", "ultracode"):
        with pytest.raises(ProviderError, match="Claude Code effort"):
            local_agents.build_invocation("claude", tmp_path, model="", reasoning_effort=effort, environ={})


def test_codex_profile_defaults_are_reused_and_explicit_effort_wins(tmp_path):
    path = tmp_path / "config.toml"
    original = '''profile = "bookmarks"
model = "base-model"
model_reasoning_effort = "low"
[profiles.bookmarks]
model = "profile-model"
model_reasoning_effort = "high"
'''
    path.write_text(original, encoding="utf-8-sig")
    args, _ = local_agents.build_invocation("codex", tmp_path, model="", environ={"CODEX_HOME": str(tmp_path)})
    assert 'model="profile-model"' in args and 'model_reasoning_effort="high"' in args
    explicit, _ = local_agents.build_invocation("codex", tmp_path, model="chosen",
        reasoning_effort="low", environ={"CODEX_HOME": str(tmp_path)})
    assert explicit[-3:] == ["-c", 'model_reasoning_effort="low"', "-"]
    assert path.read_text(encoding="utf-8-sig") == original


def test_codex_managed_model_and_effort_defaults_yield_together_to_explicit_selection(tmp_path):
    (tmp_path / "config.toml").write_text('''[models.new_thread]
model = "managed-model"
model_reasoning_effort = "medium"
''', encoding="utf-8")
    env = {"CODEX_HOME": str(tmp_path)}
    inherited = local_agents._codex_configuration(env)
    assert inherited["model"] == "managed-model" and inherited["model_reasoning_effort"] == "medium"
    assert "model_reasoning_effort" not in local_agents._codex_configuration(env, model="selected-model")
    assert "model" not in local_agents._codex_configuration(env, reasoning_effort="high")


def test_inherited_effort_change_invalidates_same_installation_test(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    monkeypatch.setattr(local_agents, "resolve_command", lambda agent: ["/synthetic/codex"] if agent == "codex" else None)
    path = tmp_path / "config.toml"
    path.write_text('model_reasoning_effort="low"', encoding="utf-8")
    settings = Settings(data_dir=tmp_path, chat_backend="agent", chat_agent="codex")
    first = admin.probe_fingerprint(settings, "chat")
    path.write_text('model_reasoning_effort="high"', encoding="utf-8")
    assert admin.probe_fingerprint(settings, "chat") != first
    explicit = settings.model_copy(update={"chat_agent_reasoning_effort": "xhigh"})
    assert admin.probe_fingerprint(explicit, "chat") != admin.probe_fingerprint(settings, "chat")
    assert admin.probe_fingerprint(explicit, "embed") == admin.probe_fingerprint(settings, "embed")


async def test_codex_catalog_retains_supported_levels_and_model_default_without_exposing_extra_data(tmp_path, monkeypatch):
    root = tmp_path / ".codex"
    root.mkdir()
    (root / "config.toml").write_text('model="summary-model"', encoding="utf-8")
    (root / "models_cache.json").write_text(json.dumps({"models": [{
        "slug": "summary-model", "default_reasoning_level": "medium",
        "supported_reasoning_levels": [{"effort": "low"}, {"effort": "medium"}, {"effort": "xhigh"}, {"bad": "ignored"}],
        "private": "synthetic-private-value",
    }]}), encoding="utf-8")

    async def unavailable(*args):
        raise ProviderError("Synthetic old CLI")

    monkeypatch.setattr(local_agents, "selected_agent", lambda _: "codex")
    monkeypatch.setattr(model_catalog, "_cli_catalog", unavailable)
    data = await model_catalog.agent_catalog("auto")
    assert data["default_reasoning_effort"] == "medium"
    assert data["models"][0]["reasoning_levels"] == [{"id": "low"}, {"id": "medium"}, {"id": "xhigh"}]
    assert "synthetic-private-value" not in json.dumps(data)


async def test_opencode_verbose_catalog_preserves_model_variants_and_excludes_disabled_variants(tmp_path, monkeypatch):
    root = tmp_path / ".config/opencode"
    root.mkdir(parents=True)
    original = '{"model":"custom/summary","provider":{"custom":{"models":{"summary":{"variants":{"careful":{"reasoningEffort":"high"}}}}}}}'
    config = root / "opencode.json"
    config.write_text(original, encoding="utf-8")

    async def catalog(*args):
        return 'custom/summary\n' + json.dumps({
            "id": "summary", "providerID": "custom", "name": "Summary",
            "options": {"reasoningEffort": "medium", "apiKey": "synthetic-private-key"},
            "variants": {"low": {}, "careful": {}, "hidden": {"disabled": True}},
        }, indent=2) + "\ncustom/second\n"

    monkeypatch.setattr(local_agents, "selected_agent", lambda _: "opencode")
    monkeypatch.setattr(model_catalog, "_cli_catalog", catalog)
    data = await model_catalog.agent_catalog("opencode")
    selected = next(model for model in data["models"] if model["id"] == "custom/summary")
    assert selected["reasoning_levels"] == [{"id": "low"}, {"id": "careful"}]
    assert selected["default_reasoning_effort"] == "medium"
    assert "synthetic-private-key" not in json.dumps(data)
    assert config.read_text(encoding="utf-8") == original


async def test_claude_model_saved_effort_and_environment_override_are_visible(tmp_path, monkeypatch):
    root = tmp_path / ".claude"
    root.mkdir()
    (root / "settings.json").write_text(json.dumps({
        "model": "custom-model", "effortLevel": "low",
        "modelSettings": {"custom-model": {"effortLevel": "high"}},
    }), encoding="utf-8")
    monkeypatch.setattr(local_agents, "selected_agent", lambda _: "claude")
    data = await model_catalog.agent_catalog("claude")
    assert data["default_reasoning_effort"] == "high"
    assert data["configured_reasoning_effort"] == "low"
    assert next(model for model in data["models"] if model["id"] == "custom-model")["default_reasoning_effort"] == "high"
    monkeypatch.setenv("CLAUDE_CODE_EFFORT_LEVEL", "medium")
    data = await model_catalog.agent_catalog("claude")
    assert data["default_reasoning_effort"] == "medium"


def test_agent_thinking_is_tested_saved_and_invalidated_as_part_of_the_chat_configuration(tmp_path, monkeypatch):
    captured = []
    monkeypatch.setattr(local_agents, "resolve_command", lambda _: ["/synthetic/agent"])

    async def probe(settings, channel=None):
        captured.append(settings.chat_agent_reasoning_effort)
        return {"chat": {"ok": True, "model": "codex/chosen", "ms": 1}}

    monkeypatch.setattr(admin, "probe", probe)
    with TestClient(create_app(Settings(data_dir=tmp_path)), client=("127.0.0.1", 40000)) as client:
        client.headers["Authorization"] = "Bearer " + client.app.state.fm.token
        values = {"chat_backend": "agent", "chat_agent": "codex", "chat_agent_model": "chosen",
                  "chat_agent_reasoning_effort": "high"}
        assert client.post("/admin/settings/test", json={**values, "channel": "chat"}).json()["chat"]["ok"]
        assert captured == ["high"]
        assert client.put("/admin/settings", json={"values": values}).status_code == 200
        state = client.app.state.fm
        assert state.settings.chat_agent_reasoning_effort == "high"
        assert state.probe_results["chat"]["fingerprint"] == admin.probe_fingerprint(state.settings, "chat")
        assert client.put("/admin/settings", json={"values": {"chat_agent_reasoning_effort": "low"}}).status_code == 200
        assert state.probe_results["chat"]["fingerprint"] != admin.probe_fingerprint(state.settings, "chat")


def test_configuration_change_during_probe_cannot_be_recorded_as_a_success(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    monkeypatch.setattr(local_agents, "resolve_command", lambda _: ["/synthetic/codex"])
    path = tmp_path / "config.toml"
    path.write_text('model_reasoning_effort="low"', encoding="utf-8")

    async def probe(settings, channel=None):
        path.write_text('model_reasoning_effort="high"', encoding="utf-8")
        return {"chat": {"ok": True, "model": "codex/chosen", "ms": 1}}

    monkeypatch.setattr(admin, "probe", probe)
    with TestClient(create_app(Settings(data_dir=tmp_path, chat_backend="agent", chat_agent="codex")),
                    client=("127.0.0.1", 40000)) as client:
        client.headers["Authorization"] = "Bearer " + client.app.state.fm.token
        result = client.post("/admin/settings/test", json={"channel": "chat"}).json()["chat"]
        assert not result["ok"] and "changed during the test" in result["error"]
        assert not client.app.state.fm.probe_results
