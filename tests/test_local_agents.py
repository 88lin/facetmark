from __future__ import annotations

import asyncio
import json
import sys

import pytest

from facetmark.config import Settings
from facetmark.local_agents import (
    AGENTS,
    LocalAgentProvider,
    available_agents,
    build_invocation,
    parse_agent_output,
    resolve_command,
    selected_agent,
)
from facetmark.providers import ProviderError


@pytest.fixture(autouse=True)
def isolated_agent_home(tmp_path, monkeypatch):
    monkeypatch.setattr("facetmark.local_agents.Path.home", lambda: tmp_path)
    monkeypatch.setattr("facetmark.local_agents._registry_directories", lambda: [])
    for key in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "OPENCODE_CONFIG", "OPENCODE_CONFIG_DIR",
                "OPENCODE_CONFIG_CONTENT", "OPENCODE_AUTH_CONTENT"):
        monkeypatch.delenv(key, raising=False)


def test_windows_npm_shim_is_resolved_to_node_without_a_shell(tmp_path, monkeypatch):
    shim = tmp_path / "codex.cmd"
    shim.write_text("npm generated wrapper", encoding="utf-8")
    entry = tmp_path / "node_modules/@openai/codex/bin/codex.js"
    entry.parent.mkdir(parents=True)
    entry.write_text("", encoding="utf-8")
    monkeypatch.setattr("facetmark.local_agents.shutil.which", lambda name: str(shim) if name == "codex" else "node.exe")
    assert resolve_command("codex") == ["node.exe", str(entry)]


def test_prompts_are_not_command_arguments_and_tools_are_disabled(tmp_path):
    for agent in AGENTS:
        args, env = build_invocation(agent, tmp_path, model="", environ={"CODEX_HOME": str(tmp_path)})
        assert not any("bypass" in value for value in args)
        if agent == "claude":
            assert args[args.index("--tools") + 1] == ""
            assert "--strict-mcp-config" in args
        elif agent == "codex":
            assert args[args.index("--sandbox") + 1] == "read-only"
            assert "features.shell_tool=false" in args
        else:
            assert json.loads(env["OPENCODE_CONFIG_CONTENT"])["permission"] == {"*": "deny"}


@pytest.mark.parametrize("agent,text", [
    ("codex", '{"type":"item.completed","item":{"type":"agent_message","text":"{\\"summary\\":\\"useful\\"}"}}\n{"type":"turn.completed"}'),
    ("claude", '{"type":"result","is_error":false,"result":"{\\"summary\\":\\"useful\\"}"}'),
    ("opencode", '{"type":"text","part":{"type":"text","text":"{\\"summary\\":\\"useful\\"}"}}\n{"type":"step_finish","part":{"reason":"stop"}}'),
])
def test_only_final_agent_text_is_decoded(agent, text):
    assert parse_agent_output(agent, text) == {"summary": "useful"}


def test_failed_agent_result_never_becomes_a_summary():
    with pytest.raises(ProviderError):
        parse_agent_output("claude", '{"type":"result","is_error":true,"result":"not logged in"}')


def test_opencode_native_npm_entry_does_not_need_node(tmp_path, monkeypatch):
    shim = tmp_path / "opencode.cmd"
    shim.touch()
    package = tmp_path / "node_modules/opencode-ai"
    (package / "bin").mkdir(parents=True)
    (package / "package.json").write_text('{"bin":{"opencode":"./bin/opencode.exe"}}')
    binary = package / "bin/opencode.exe"
    binary.touch()
    monkeypatch.setattr("facetmark.local_agents.shutil.which", lambda name: str(shim) if name == "opencode" else None)
    assert resolve_command("opencode") == [str(binary)]


def test_discovery_finds_user_installs_without_path(tmp_path, monkeypatch):
    monkeypatch.setattr("facetmark.local_agents.Path.home", lambda: tmp_path)
    monkeypatch.setattr("facetmark.local_agents.shutil.which", lambda _: None)
    monkeypatch.setattr("facetmark.local_agents.os.environ", {})
    binary = tmp_path / ".opencode/bin/opencode"
    binary.parent.mkdir(parents=True)
    binary.touch(mode=0o755)
    assert resolve_command("opencode") == [str(binary)]
    assert selected_agent("auto") == "opencode"
    assert next(item for item in available_agents() if item["id"] == "opencode")["installed"]
    assert selected_agent("claude") is None


def test_discovery_uses_refreshed_desktop_path_and_skips_broken_shims(tmp_path, monkeypatch):
    monkeypatch.setattr("facetmark.local_agents.os.environ", {})
    stale = tmp_path / "stale/opencode.cmd"
    stale.parent.mkdir()
    stale.touch()
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    binary = fresh / "opencode"
    binary.touch(mode=0o755)
    monkeypatch.setattr("facetmark.local_agents.shutil.which", lambda name: str(stale) if name == "opencode" else None)
    monkeypatch.setattr("facetmark.local_agents._registry_directories", lambda: [fresh])
    assert resolve_command("opencode") == [str(binary)]


@pytest.mark.parametrize("event", [
    {"type": "text", "part": None},
    {"type": "text", "part": {"text": {"summary": "invalid"}}},
    {"type": "error", "error": {"message": "private-credential"}},
])
def test_malformed_opencode_events_are_safe_provider_errors(event):
    with pytest.raises(ProviderError) as error:
        parse_agent_output("opencode", json.dumps(event))
    assert "private-credential" not in str(error.value)


def test_invalid_agent_json_does_not_echo_private_output():
    with pytest.raises(ProviderError) as error:
        parse_agent_output("opencode", json.dumps({"type": "text", "part": {"text": "private-credential"}}))
    assert "private-credential" not in str(error.value)
    assert "invalid JSON" in str(error.value)


def test_auto_probe_is_invalidated_when_the_resolved_cli_changes(tmp_path, monkeypatch):
    from facetmark.admin import probe_fingerprint

    settings = Settings(data_dir=tmp_path, chat_backend="agent")
    monkeypatch.setattr("facetmark.local_agents.resolve_command", lambda name: ["/bin/codex"] if name == "codex" else None)
    first = probe_fingerprint(settings, "chat")
    monkeypatch.setattr("facetmark.local_agents.resolve_command", lambda name: ["/bin/opencode"] if name == "opencode" else None)
    assert probe_fingerprint(settings, "chat") != first


def test_opencode_reuses_jsonc_models_without_inheriting_tools_or_plugins(tmp_path, monkeypatch):
    monkeypatch.setattr("facetmark.local_agents.Path.home", lambda: tmp_path)
    root = tmp_path / ".config/opencode"
    root.mkdir(parents=True)
    original = '''{
      // Existing model connection, including a URL containing double slashes.
      "model": "custom/bookmarks",
      "provider": {"custom": {"options": {"baseURL": "https://api.example/v1", "apiKey": "private-test-key",},},},
      "plugin": ["do-not-load"],
      "mcp": {"danger": {"command": ["do-not-run"]}},
      "permission": {"bash": "allow"},
      "instructions": ["do-not-read"],
    }'''
    (root / "opencode.jsonc").write_text(original, encoding="utf-8")
    args, env = build_invocation("opencode", tmp_path / "isolated", model="", environ={})
    config = json.loads(env["OPENCODE_CONFIG_CONTENT"])
    assert config["model"] == "custom/bookmarks"
    assert config["provider"]["custom"]["options"]["apiKey"] == "private-test-key"
    assert config["provider"]["custom"]["options"]["baseURL"] == "https://api.example/v1"
    assert config["permission"] == {"*": "deny"}
    assert config["plugin"] == [] and config["mcp"] == {} and config["instructions"] == []
    assert config["share"] == "disabled"
    assert "private-test-key" not in " ".join(args)
    assert "--pure" in args
    assert env["OPENCODE_DB"] == str(tmp_path / "isolated/sessions.db")
    assert (root / "opencode.jsonc").read_text(encoding="utf-8") == original


def test_opencode_model_override_and_custom_config(tmp_path, monkeypatch):
    monkeypatch.setattr("facetmark.local_agents.Path.home", lambda: tmp_path)
    custom = tmp_path / "custom.json"
    custom.write_text('{"model":"previous/model"}')
    args, env = build_invocation("opencode", tmp_path, model="chosen/model", environ={
        "OPENCODE_CONFIG": str(custom), "OPENCODE_PERMISSION": '{"bash":"allow"}',
    })
    assert args[args.index("--model") + 1] == "chosen/model"
    assert "OPENCODE_CONFIG" not in env
    assert json.loads(env["OPENCODE_PERMISSION"]) == {"*": "deny"}
    assert Settings(data_dir=tmp_path, chat_backend="agent", chat_agent="opencode").chat_agent == "opencode"


async def test_real_child_process_uses_stdin_unicode_and_existing_agent_config(tmp_path, monkeypatch):
    script = tmp_path / "fake_cli.py"
    script.write_text('''import json, sys
prompt = sys.stdin.buffer.read().decode("utf-8")
assert "摘要 $(do-not-execute)" in prompt
assert "摘要 $(do-not-execute)" not in " ".join(sys.argv)
event = {"type":"item.completed","item":{"type":"agent_message","text":json.dumps({"summary":"中文结果"}, ensure_ascii=False)}}
sys.stdout.buffer.write(json.dumps(event, ensure_ascii=False).encode("utf-8"))
''', encoding="utf-8")
    monkeypatch.setattr("facetmark.local_agents.selected_agent", lambda _: "codex")
    monkeypatch.setattr("facetmark.local_agents.resolve_command", lambda _: [sys.executable, str(script)])
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    provider = LocalAgentProvider(Settings(data_dir=tmp_path, chat_backend="agent"))
    assert await provider.chat_json("Return JSON", "摘要 $(do-not-execute)") == {"summary": "中文结果"}
    assert not provider._processes
    await provider.aclose()


@pytest.mark.parametrize("cancel", [False, True])
async def test_timeout_and_cancel_reap_the_child(tmp_path, monkeypatch, cancel):
    script = tmp_path / "waiting.py"
    ready = tmp_path / "ready"
    script.write_text(f'import pathlib,time\npathlib.Path({str(ready)!r}).touch()\ntime.sleep(60)', encoding="utf-8")
    monkeypatch.setattr("facetmark.local_agents.selected_agent", lambda _: "codex")
    monkeypatch.setattr("facetmark.local_agents.resolve_command", lambda _: [sys.executable, str(script)])
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    settings = Settings(data_dir=tmp_path, chat_backend="agent").model_copy(update={"chat_agent_timeout": 0.6})
    provider = LocalAgentProvider(settings)
    task = asyncio.create_task(provider.chat_json("json", "test"))
    for _ in range(100):
        if ready.exists():
            break
        await asyncio.sleep(0.01)
    assert ready.exists()
    processes = tuple(provider._processes)
    if cancel:
        task.cancel()
    with pytest.raises(asyncio.CancelledError if cancel else ProviderError):
        await task
    assert not provider._processes and all(p.poll() is not None for p in processes)
    await provider.aclose()


def test_codex_model_config_is_reused_without_inherited_mcp_and_hooks(tmp_path):
    (tmp_path / "config.toml").write_text('''model = "existing-model"
model_provider = "custom"
[model_providers.custom]
name = "Custom"
base_url = "https://model.example/v1"
env_key = "MY_MODEL_KEY"
[mcp_servers.danger]
command = "do-not-run"
[hooks]
command = "do-not-run-either"
''', encoding="utf-8")
    args, _ = build_invocation("codex", tmp_path, model="", environ={"CODEX_HOME": str(tmp_path)})
    assert "--ignore-user-config" in args and "--ignore-rules" in args
    assert 'model="existing-model"' in args
    assert "MY_MODEL_KEY" in " ".join(args)
    assert "do-not-run" not in " ".join(args)


def test_codex_literal_headers_are_reused_only_through_child_environment(tmp_path):
    (tmp_path / "config.toml").write_text('''model_provider = "custom"
[model_providers.custom]
name = "Custom"
base_url = "https://model.example/v1"
http_headers = {"X-API-Key"="synthetic-private-header"}
experimental_bearer_token = "synthetic-private-token"
''', encoding="utf-8")
    args, env = build_invocation("codex", tmp_path, model="", environ={"CODEX_HOME": str(tmp_path)})
    assert "synthetic-private" not in " ".join(args)
    assert "synthetic-private-header" in env.values()
    assert "synthetic-private-token" in env.values()
