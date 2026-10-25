"""Configuration diagnostics must redact every credential and name real commands."""
from __future__ import annotations

import contextlib
import json
import re
import shlex
import sqlite3
from pathlib import Path

import pytest
from typer.main import get_command
from typer.testing import CliRunner

from facetmark import db, diagnose, local_agents, service
from facetmark.cli import _mask, app
from facetmark.config import Settings, reset_settings
from facetmark.configfile import config_path, update_config
from facetmark.migrations import SCHEMA_VERSION

SECRET_KEYS = ("api_key", "chat_api_key", "embed_api_key", "mcp_token")
SHORT_SECRET = "Z8qP6rT3"
LONG_SECRET = "sk-CLI-SYNTHETIC-SECRET-91827364"


@pytest.fixture
def isolated_cli(tmp_path, monkeypatch):
    directory = tmp_path / "cli-library"
    monkeypatch.setenv("FACETMARK_DATA_DIR", str(directory))
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    try:
        yield CliRunner(), directory
    finally:
        reset_settings()


@pytest.mark.parametrize("secret", ["", "A", "b2", SHORT_SECRET, "123456789", LONG_SECRET])
def test_mask_never_returns_a_nonempty_credential_in_full(secret):
    masked = _mask(secret)
    if not secret:
        assert masked == ""
    else:
        assert masked and secret not in masked
        if len(secret) <= 8:
            assert masked == "***"


@pytest.mark.parametrize("key", SECRET_KEYS)
@pytest.mark.parametrize("secret", [SHORT_SECRET, LONG_SECRET], ids=["eight-characters", "long-key"])
@pytest.mark.parametrize("json_mode", [False, True], ids=["table", "json"])
def test_config_show_redacts_all_environment_credentials_and_preserves_their_source(isolated_cli, monkeypatch, key, secret, json_mode):
    runner, _ = isolated_cli
    monkeypatch.setenv("FACETMARK_" + key.upper(), secret)
    monkeypatch.setenv("FACETMARK_ENRICH_CONCURRENCY", "5")
    result = runner.invoke(app, ["config", "show", *(["--json"] if json_mode else [])])
    assert result.exit_code == 0, result.output
    assert secret not in result.output
    assert key in result.stdout
    if json_mode:
        rows = {row["key"]: row for row in json.loads(result.stdout)["settings"]}
        assert rows[key] == {"key": key, "value": _mask(secret), "source": "env"}
        assert rows["enrich_concurrency"] == {"key": "enrich_concurrency", "value": 5, "source": "env"}
    else:
        line = next(line for line in result.stdout.splitlines() if re.match(rf"\s*{key}\s", line))
        assert _mask(secret) in line and "env" in line


@pytest.mark.parametrize("source", ["file", "dotenv"])
@pytest.mark.parametrize("json_mode", [False, True], ids=["table", "json"])
def test_config_show_redacts_file_and_dotenv_credentials_without_hiding_settings(isolated_cli, source, json_mode):
    runner, directory = isolated_cli
    secrets = {key: f"sk-{key}-SYNTHETIC-LOCAL-92837465" for key in SECRET_KEYS}
    if source == "file":
        update_config({**secrets, "enrich_concurrency": 6})
    else:
        Path(".env").write_text("\n".join(f"FACETMARK_{key.upper()}={value}" for key, value in secrets.items()) +
            "\nFACETMARK_ENRICH_CONCURRENCY=6\n", encoding="utf-8")
    result = runner.invoke(app, ["config", "show", *(["--json"] if json_mode else [])])
    assert result.exit_code == 0, result.output
    assert all(secret not in result.output for secret in secrets.values())
    assert all(key in result.stdout for key in SECRET_KEYS)
    if json_mode:
        data = json.loads(result.stdout)
        assert data["path"] == str(config_path(directory))
        rows = {row["key"]: row for row in data["settings"]}
        for key, secret in secrets.items():
            assert rows[key] == {"key": key, "value": _mask(secret), "source": "file" if source == "file" else "env"}
        assert rows["enrich_concurrency"]["value"] == 6
    else:
        for key, secret in secrets.items():
            line = next(line for line in result.stdout.splitlines() if re.match(rf"\s*{key}\s", line))
            assert _mask(secret) in line and ("file" if source == "file" else "env") in line


def test_doctor_uses_independent_chat_and_embedding_credentials_and_does_not_echo_them(isolated_cli, monkeypatch):
    runner, directory = isolated_cli
    secrets = {"chat_api_key": "CHAT_DIAGNOSTIC_SECRET_93847566", "embed_api_key": "EMBED_DIAGNOSTIC_SECRET_94857667"}
    update_config(secrets)

    def forbid_provider(*args, **kwargs):
        pytest.fail("doctor must report configuration without making a model request")

    monkeypatch.setattr("facetmark.providers.get_provider", forbid_provider)
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0, result.output
    checks = {check["name"]: check for check in json.loads(result.stdout)["checks"]}
    assert checks["provider.chat"]["status"] == "ok" and checks["provider.embed"]["status"] == "ok"
    assert "not tested" in checks["provider.chat"]["message"]
    assert "not tested" in checks["provider.embed"]["message"]
    assert all(secret not in result.output for secret in secrets.values())
    assert not (directory / "facetmark.db").exists()


@pytest.mark.parametrize("configuration,chat_status,embed_status", [
    ({"embed_api_key": "EMBED_ONLY_SYNTHETIC_SECRET"}, "warn", "ok"),
    ({"chat_api_key": "CHAT_ONLY_SYNTHETIC_SECRET"}, "ok", "warn"),
    ({"chat_backend": "agent", "chat_agent": "codex", "embed_api_key": "AGENT_EMBED_SYNTHETIC_SECRET"}, "ok", "ok"),
    ({"chat_base_url": "http://127.0.0.1:1234/v1", "embed_base_url": "http://127.0.0.1:1234/v1",
      "chat_allow_no_key": True, "embed_allow_no_key": True}, "ok", "ok"),
], ids=["embedding-only", "chat-only", "chat-agent", "explicit-local-no-key"])
def test_provider_diagnostics_report_channel_configuration_without_legacy_key_assumptions(tmp_path, monkeypatch, configuration, chat_status, embed_status):
    monkeypatch.setattr(local_agents, "selected_agent", lambda requested: "codex")
    settings = Settings(data_dir=tmp_path / "diagnostic-config", api_key="", use_mock_provider=False, **configuration)
    checks = {check.name: check for check in diagnose.check_provider(settings)}
    assert checks["provider.chat"].status == chat_status
    assert checks["provider.embed"].status == embed_status
    serialized = json.dumps([check.as_dict() for check in checks.values()])
    assert all(value not in serialized for key, value in configuration.items() if key.endswith("api_key"))
    if settings.chat_backend == "agent":
        assert "Login and model execution were not tested" in checks["provider.chat"].message
    else:
        assert "not tested" in checks["provider.chat"].message


@pytest.mark.parametrize("broken,expected_command", [
    ("empty-library", "import"), ("missing-seg", "reindex"), ("empty-seg", "reindex"),
    ("missing-tri", "reindex"), ("empty-tri", "reindex"), ("old-schema", "migrate"),
    ("vector-space", "index"),
])
def test_doctor_recommendations_are_registered_commands_with_valid_options_and_do_not_repair_the_database(isolated_cli, monkeypatch, broken, expected_command):
    runner, directory = isolated_cli
    settings = Settings(data_dir=directory, use_mock_provider=True, embed_dim=16, embed_model="diagnostic-current-model")
    settings.ensure_dirs()
    monkeypatch.setenv("FACETMARK_USE_MOCK_PROVIDER", "true")
    monkeypatch.setenv("FACETMARK_EMBED_DIM", "16")
    monkeypatch.setenv("FACETMARK_EMBED_MODEL", "diagnostic-current-model")
    conn = db.open_db(settings.db_path)
    try:
        if broken != "empty-library":
            service.save_bookmark(conn, "https://diagnostic.test/synthetic", title="Diagnostic source", settings=settings)
        if broken in {"missing-seg", "empty-seg", "missing-tri", "empty-tri"}:
            table = "fts_seg" if broken.endswith("seg") else "fts_tri"
            if broken.startswith("missing"):
                conn.execute(f"DROP TABLE {table}")
            else:
                conn.execute(f"DELETE FROM {table}")
        elif broken == "old-schema":
            db.set_meta(conn, "schema_version", str(SCHEMA_VERSION - 1))
        elif broken == "vector-space":
            db.ensure_vec_tables(conn, 8, "diagnostic-previous-model")
        conn.commit()
    finally:
        conn.close()
    before = settings.db_path.read_bytes()
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code in {0, 1}, result.output
    data = json.loads(result.stdout)
    assert settings.db_path.read_bytes() == before
    recommendations = []
    for check in data["checks"]:
        match = re.search(r"\brun:\s*(facetmark[^\n]*)", check["message"], re.IGNORECASE)
        if match:
            recommendations.append(shlex.split(match.group(1).rstrip(" .")))
    assert expected_command in {recommendation[1] for recommendation in recommendations}, data
    registered = get_command(app).commands
    for recommendation in recommendations:
        assert recommendation[0] == "facetmark"
        assert recommendation[1] in registered
        command = registered[recommendation[1]]
        valid_options = {option for parameter in command.params
            for option in [*getattr(parameter, "opts", []), *getattr(parameter, "secondary_opts", [])]}
        for argument in recommendation[2:]:
            if argument.startswith("--"):
                assert argument.split("=", 1)[0] in valid_options, recommendation
        # --help is eager; no recommended repair is executed by this suite.
        help_result = runner.invoke(app, [*recommendation[1:], "--help"])
        assert help_result.exit_code == 0, (recommendation, help_result.output)
        assert "Usage:" in help_result.stdout
        assert settings.db_path.read_bytes() == before
    if broken == "old-schema":
        with contextlib.closing(sqlite3.connect(settings.db_path)) as inspected:
            assert inspected.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] == str(SCHEMA_VERSION - 1)
