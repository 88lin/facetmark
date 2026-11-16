"""Selected config files remain the source for saves, snapshots and MCP receipts."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from facetmark import admin, mcp_operations
from facetmark.api import create_app
from facetmark.config import Settings
from facetmark.configfile import read_config, write_config


def test_a_selected_source_survives_copies_without_becoming_an_exported_setting(tmp_path):
    selected = tmp_path / "selected"
    selected.mkdir()
    write_config({"chat_model": "selected-model"}, selected / "config.toml")
    settings = Settings(data_dir=selected)
    for snapshot in (settings, settings.model_copy(), settings.model_copy(deep=True)):
        assert snapshot.config_file_path == selected / "config.toml"
        assert set(snapshot.model_dump()) == set(Settings.model_fields)


def test_a_draft_validates_the_live_snapshot_without_reading_any_config_source(tmp_path, monkeypatch):
    settings = Settings(data_dir=tmp_path / "selected", chat_model="live-model")
    monkeypatch.setenv("FACETMARK_CHAT_MODEL", "new-environment-model")

    def no_source(_path=None):
        raise AssertionError("Editing a complete live snapshot must not reopen TOML")

    monkeypatch.setattr("facetmark.config.read_config", no_source)
    candidate = admin.draft_settings(settings, {"chat_concurrency": "3"})
    assert candidate.chat_concurrency == 3
    assert candidate.chat_model == "live-model"
    assert candidate.config_file_path == settings.config_file_path
    assert settings.chat_concurrency == 2
    with pytest.raises(ValueError):
        admin.draft_settings(settings, {"chat_concurrency": 0})


def test_saving_a_selected_library_never_reads_or_changes_a_broken_default(tmp_path, monkeypatch):
    default, selected = tmp_path / "broken-default", tmp_path / "selected"
    default.mkdir()
    selected.mkdir()
    broken = b'chat_model = "unfinished\n'
    (default / "config.toml").write_bytes(broken)
    monkeypatch.setenv("FACETMARK_DATA_DIR", str(default))
    settings = Settings(data_dir=selected, use_mock_provider=True)
    with TestClient(create_app(settings), client=("127.0.0.1", 40404)) as client:
        client.headers["Authorization"] = "Bearer " + client.app.state.fm.token
        response = client.put("/admin/settings", json={"values": {"chat_model": "saved-in-selected"}})
        assert response.status_code == 200, response.text
        assert response.json()["path"] == str(selected / "config.toml")
    assert (default / "config.toml").read_bytes() == broken
    assert Settings(data_dir=selected).chat_model == "saved-in-selected"


@pytest.fixture
def relocated(tmp_path, monkeypatch):
    source, database = tmp_path / "config-source", tmp_path / "database-location"
    source.mkdir()
    write_config({"data_dir": str(database), "chat_model": "saved-model"}, source / "config.toml")
    monkeypatch.setattr("facetmark.config.default_data_dir", lambda **_kw: source)
    return source, database


def test_a_toml_database_location_does_not_relocate_the_file_for_admin_saves(relocated):
    source, database = relocated
    settings = Settings(use_mock_provider=True)
    assert settings.data_dir == database
    with TestClient(create_app(settings), client=("127.0.0.1", 40404)) as client:
        client.headers["Authorization"] = "Bearer " + client.app.state.fm.token
        response = client.put("/admin/settings", json={"values": {"chat_model": "after-save"}})
        assert response.status_code == 200, response.text
        assert response.json()["path"] == str(source / "config.toml")
        assert client.app.state.fm.settings.config_file_path == source / "config.toml"
    assert not (database / "config.toml").exists()
    assert read_config(source / "config.toml")["chat_model"] == "after-save"
    assert Settings(use_mock_provider=True).chat_model == "after-save"


def test_mcp_acceptance_and_restart_confirmation_use_the_original_source(relocated):
    source, database = relocated
    settings = Settings()
    before = mcp_operations.configuration_revision(settings)
    changes, accepted = mcp_operations.accept_configuration(
        settings, enabled=True, rotate_token=True, request_id="original-local-change", expected_revision=before
    )
    assert accepted is not None and changes["mcp_token"]
    assert not (database / "config.toml").exists()
    saved = read_config(source / "config.toml")
    assert saved["mcp_enabled"] and saved["mcp_token"] == changes["mcp_token"]
    restarted = Settings()
    confirmed = mcp_operations.receipt(restarted, "original-local-change")
    assert confirmed == accepted
    assert not mcp_operations.public_receipt(confirmed, restarted)["superseded"]
    replayed, receipt = mcp_operations.accept_configuration(
        restarted, enabled=True, rotate_token=True, request_id="original-local-change", expected_revision=before
    )
    assert replayed == {} and receipt == accepted
    assert Settings().mcp_token == changes["mcp_token"]


def test_a_source_path_cannot_be_reassigned_by_reserved_file_metadata(tmp_path):
    selected = tmp_path / "selected"
    selected.mkdir()
    write_config({"_config_source_path": str(tmp_path / "another.toml")}, selected / "config.toml")
    assert Settings(data_dir=selected).config_file_path == Path(selected / "config.toml")
