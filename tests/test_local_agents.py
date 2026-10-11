from __future__ import annotations

import asyncio
import json
import sys

import pytest

from facetmark.config import Settings
from facetmark.local_agents import (
    LocalAgentProvider,
    build_invocation,
    parse_agent_output,
    resolve_command,
)
from facetmark.providers import ProviderError


def test_windows_npm_shim_is_resolved_to_node_without_a_shell(tmp_path, monkeypatch):
    shim = tmp_path / "codex.cmd"
    shim.write_text("npm generated wrapper", encoding="utf-8")
    entry = tmp_path / "node_modules/@openai/codex/bin/codex.js"
    entry.parent.mkdir(parents=True)
    entry.write_text("", encoding="utf-8")
    monkeypatch.setattr("facetmark.local_agents.shutil.which", lambda name: str(shim) if name == "codex" else "node.exe")
    assert resolve_command("codex") == ["node.exe", str(entry)]


def test_prompts_are_not_command_arguments_and_tools_are_disabled(tmp_path):
    for agent in ("codex", "claude"):
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
])
def test_only_final_agent_text_is_decoded(agent, text):
    assert parse_agent_output(agent, text) == {"summary": "useful"}


def test_failed_agent_result_never_becomes_a_summary():
    with pytest.raises(ProviderError):
        parse_agent_output("claude", '{"type":"result","is_error":true,"result":"not logged in"}')


async def test_real_child_process_uses_stdin_unicode_and_existing_agent_config(tmp_path, monkeypatch):
    script = tmp_path / "fake_cli.py"
    script.write_text('''import json, sys
prompt = sys.stdin.read()
assert "摘要 $(do-not-execute)" in prompt
assert "摘要 $(do-not-execute)" not in " ".join(sys.argv)
print(json.dumps({"type":"item.completed","item":{"type":"agent_message","text":json.dumps({"summary":"中文结果"})}}))
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
