"""Connection proofs belong to a configuration, not the last settings visit."""

from fastapi.testclient import TestClient

from facetmark import admin, local_agents
from facetmark.api import create_app
from facetmark.config import Settings


def test_unsaved_model_test_does_not_replace_saved_connection_after_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("FACETMARK_DATA_DIR", str(tmp_path))

    async def probe(settings, channel=None):
        return {"chat": {"ok": settings.chat_model != "broken", "model": settings.chat_model, "ms": 1}}

    monkeypatch.setattr(admin, "probe", probe)
    with TestClient(create_app(Settings(data_dir=tmp_path)), client=("127.0.0.1", 40000)) as client:
        client.headers["Authorization"] = "Bearer " + client.app.state.fm.token
        saved = {"chat_base_url": "https://synthetic.invalid/v1", "chat_api_key": "synthetic-key",
                 "chat_model": "saved-model"}
        assert client.post("/admin/settings/test", json={**saved, "channel": "chat"}).json()["chat"]["ok"]
        assert client.put("/admin/settings", json={"values": saved}).status_code == 200
        for model in ("another-model", "broken"):
            client.post("/admin/settings/test", json={"chat_model": model, "channel": "chat"})
            assert client.get("/admin/setup-status").json()["channels"]["chat"]["tested"]
    with TestClient(create_app(Settings(data_dir=tmp_path)), client=("127.0.0.1", 40000)) as client:
        client.headers["Authorization"] = "Bearer " + client.app.state.fm.token
        assert client.app.state.fm.settings.chat_model == "saved-model"
        assert client.get("/admin/setup-status").json()["channels"]["chat"]["tested"]
        client.put("/admin/settings", json={"values": {"chat_model": "never-tested"}})
        assert not client.get("/admin/setup-status").json()["channels"]["chat"]["tested"]


def test_explicit_codex_choice_ignores_unused_client_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    monkeypatch.setattr(local_agents, "resolve_command", lambda _: ["/synthetic/codex"])
    config = tmp_path / "config.toml"
    config.write_text('model="daily-model"\nmodel_reasoning_effort="low"', encoding="utf-8")
    settings = Settings(data_dir=tmp_path / "app", chat_backend="agent", chat_agent="codex",
                        chat_agent_model="summary-model", chat_agent_reasoning_effort="xhigh")
    fingerprint = admin.probe_fingerprint(settings, "chat")
    config.write_text('model="other-daily-model"\nmodel_reasoning_effort="high"', encoding="utf-8")
    assert admin.probe_fingerprint(settings, "chat") == fingerprint
    assert admin.probe_fingerprint(settings.model_copy(update={"chat_agent_reasoning_effort": "max"}), "chat") != fingerprint


def test_endpoint_proof_ignores_inactive_agent_and_json_formatting(tmp_path):
    settings = Settings(data_dir=tmp_path, chat_backend="endpoint", chat_api_key="synthetic-key",
                        chat_extra_body='{"reasoning_effort":"high","max_tokens":2048}')
    fingerprint = admin.probe_fingerprint(settings, "chat")
    equivalent = settings.model_copy(update={"chat_agent_model": "unused", "chat_agent_timeout": 999,
        "chat_extra_body": '{ "max_tokens": 2048, "reasoning_effort": "high" }'})
    assert admin.probe_fingerprint(equivalent, "chat") == fingerprint
    assert admin.probe_fingerprint(settings.model_copy(update={"chat_api_key": "changed-key"}), "chat") != fingerprint


def test_existing_installation_proof_remains_valid_when_upgrading(tmp_path):
    settings = Settings(data_dir=tmp_path, chat_api_key="synthetic-key", chat_model="existing")
    proof = {"fingerprint": admin._legacy_probe_fingerprint(settings, "chat"),
             "result": {"ok": True, "model": "existing"}}
    admin.persist_probes(tmp_path, {"chat": proof})
    restored = admin.load_probes(tmp_path)
    assert admin.matching_probe(settings, "chat", restored) == proof
    assert not admin.matching_probe(settings.model_copy(update={"chat_model": "changed"}), "chat", restored)


def test_trying_many_drafts_keeps_the_saved_connection_and_bounded_history(tmp_path):
    settings = Settings(data_dir=tmp_path, chat_api_key="synthetic-key", chat_model="saved")
    results = {}
    admin.remember_probe(results, "chat", admin.probe_fingerprint(settings, "chat"), {"ok": True}, settings)
    for index in range(20):
        draft = settings.model_copy(update={"chat_model": f"draft-{index}"})
        admin.remember_probe(results, "chat", admin.probe_fingerprint(draft, "chat"), {"ok": True}, settings)
    assert admin.matching_probe(settings, "chat", results)
    assert len(results["chat"]["history"]) <= 8
    assert all("history" not in record for record in results["chat"]["history"])
    assert "synthetic-key" not in str(results)


def test_choosing_effort_keeps_the_detected_codex_default_model(tmp_path):
    (tmp_path / "config.toml").write_text(
        '[models.new_thread]\nmodel="managed-summary"\nmodel_reasoning_effort="medium"', encoding="utf-8")
    args, _ = local_agents.build_invocation("codex", tmp_path / "isolated", model="",
        reasoning_effort="max", environ={"CODEX_HOME": str(tmp_path)})
    assert 'model="managed-summary"' in args
    assert args[args.index('model_reasoning_effort="max"') - 1] == "-c"
