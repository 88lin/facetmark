"""Desktop pre-upgrade snapshots are complete pairs and never replace old recovery files."""
from __future__ import annotations

import json
import os
import sqlite3
import stat
from pathlib import Path

import pytest

from facetmark import desktop
from facetmark.config import Settings
from facetmark.configfile import write_config


@pytest.fixture
def local_library(tmp_path, monkeypatch):
    settings = Settings(data_dir=tmp_path / "isolated 资料库 #100%")
    settings.ensure_dirs()
    write_config({"chat_model": "keep-this-saved-model"}, settings.config_file_path)
    stamp = settings.data_dir / "desktop-version.json"
    stamp.write_text(json.dumps({"version": "0.0.0"}), encoding="utf-8")
    monkeypatch.setattr(desktop.time, "strftime", lambda _format: "20300101-010203")
    conn = sqlite3.connect(settings.db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE saved_text(body TEXT)")
    conn.execute("INSERT INTO saved_text VALUES('first committed WAL text')")
    conn.commit()
    try:
        yield settings, conn
    finally:
        conn.close()


def rows(path):
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        return conn.execute("SELECT body FROM saved_text ORDER BY rowid").fetchall()


def backup_bytes(settings):
    directory = settings.data_dir / "backups"
    return {file.name: file.read_bytes() for file in directory.iterdir() if file.is_file()}


@pytest.mark.skipif(os.name != "nt", reason="Windows desktop uses verbatim paths")
def test_upgrade_reads_the_original_wal_through_the_native_windows_path(local_library):
    settings, conn = local_library
    canonical = Path("\\\\?\\" + str(settings.data_dir))
    settings = settings.model_copy(update={"data_dir": canonical})
    conn.execute("INSERT INTO saved_text VALUES('committed before restart')")
    conn.commit()
    assert settings.db_path.with_name("facetmark.db-wal").stat().st_size > 0

    desktop.backup_on_upgrade(settings)

    saved = next((canonical / "backups").glob("*.db"))
    assert rows(saved) == [("first committed WAL text",), ("committed before restart",)]
    assert saved.with_suffix(".toml").read_bytes() == settings.config_file_path.read_bytes()
    assert rows(settings.db_path) == rows(saved)


def test_repeated_desktop_upgrade_attempts_with_the_same_timestamp_retain_both_complete_pairs(local_library):
    settings, conn = local_library
    stamp = (settings.data_dir / "desktop-version.json").read_bytes()
    desktop.backup_on_upgrade(settings)
    directory = settings.data_dir / "backups"
    first_db = next(directory.glob("*.db"))
    first_bytes = backup_bytes(settings)
    conn.execute("INSERT INTO saved_text VALUES('second committed WAL text')")
    conn.commit()
    write_config({"chat_model": "later-saved-model"}, settings.config_file_path)
    desktop.backup_on_upgrade(settings)
    later = backup_bytes(settings)
    assert len(later) == 4
    assert all(later[name] == value for name, value in first_bytes.items())
    assert rows(first_db) == [("first committed WAL text",)]
    second_db = next(file for file in directory.glob("*.db") if file != first_db)
    assert rows(second_db) == [("first committed WAL text",), ("second committed WAL text",)]
    assert second_db.with_suffix(".toml").read_bytes() == settings.config_file_path.read_bytes()
    assert (settings.data_dir / "desktop-version.json").read_bytes() == stamp
    assert not any(file.is_dir() for file in directory.iterdir())


def test_desktop_upgrade_copies_the_config_source_even_if_toml_moves_the_database(tmp_path, monkeypatch):
    source, data = tmp_path / "config-source", tmp_path / "database-location"
    source.mkdir()
    write_config({"data_dir": str(data), "chat_model": "original-config-source"}, source / "config.toml")
    monkeypatch.setattr("facetmark.config.default_data_dir", lambda **_kw: source)
    settings = Settings()
    settings.ensure_dirs()
    with sqlite3.connect(settings.db_path) as conn:
        conn.execute("CREATE TABLE saved_text(body TEXT)")
        conn.execute("INSERT INTO saved_text VALUES('original local text')")
    desktop.backup_on_upgrade(settings)
    directory = data / "backups"
    saved_db = next(directory.glob("*.db"))
    assert rows(saved_db) == [("original local text",)]
    assert saved_db.with_suffix(".toml").read_bytes() == (source / "config.toml").read_bytes()
    assert not (data / "config.toml").exists()


def test_a_partial_desktop_sqlite_snapshot_is_not_published_and_preserves_the_prior_pair(local_library, monkeypatch):
    settings, _ = local_library
    desktop.backup_on_upgrade(settings)
    original = backup_bytes(settings)
    real_connect = sqlite3.connect

    class FailedSource:
        def __init__(self, conn):
            self.conn = conn

        def close(self):
            self.conn.close()

        def backup(self, destination):
            destination.execute("CREATE TABLE synthetic_partial(body TEXT)")
            destination.commit()
            raise sqlite3.OperationalError("synthetic partial desktop backup failure")

    def connect(database, *args, **kwargs):
        conn = real_connect(database, *args, **kwargs)
        is_source = kwargs.get("uri") or Path(database) == settings.db_path
        return FailedSource(conn) if is_source else conn

    with monkeypatch.context() as patch:
        patch.setattr(desktop.sqlite3, "connect", connect)
        with pytest.raises(sqlite3.OperationalError, match="partial desktop"):
            desktop.backup_on_upgrade(settings)
    assert backup_bytes(settings) == original
    assert not any(file.is_dir() for file in (settings.data_dir / "backups").iterdir())


def test_a_config_copy_failure_does_not_publish_half_a_pair(local_library, monkeypatch):
    import shutil

    settings, _ = local_library
    desktop.backup_on_upgrade(settings)
    original = backup_bytes(settings)

    def interrupted(_source, destination, **_kwargs):
        Path(destination).write_bytes(b"synthetic partial config copy")
        raise OSError("synthetic config copy failure")

    monkeypatch.setattr(shutil, "copy2", interrupted)
    with pytest.raises(OSError, match="config copy failure"):
        desktop.backup_on_upgrade(settings)
    assert backup_bytes(settings) == original
    assert not any(file.is_dir() for file in (settings.data_dir / "backups").iterdir())


def test_desktop_snapshot_flush_failure_keeps_all_existing_recovery_files(local_library, monkeypatch):
    settings, _ = local_library
    desktop.backup_on_upgrade(settings)
    original = backup_bytes(settings)

    def interrupted(_descriptor):
        raise OSError("synthetic desktop flush failure")

    monkeypatch.setattr(os, "fsync", interrupted)
    with pytest.raises(OSError, match="desktop flush failure"):
        desktop.backup_on_upgrade(settings)
    assert backup_bytes(settings) == original


def test_a_config_publication_race_keeps_the_other_file_and_removes_only_our_new_database(local_library, monkeypatch):
    settings, _ = local_library
    desktop.backup_on_upgrade(settings)
    original = backup_bytes(settings)
    occupied = []

    def occupy(target):
        target = Path(target)
        if target.suffix == ".toml":
            target.write_bytes(b"another complete recovery config")
            occupied.append(target)

    if os.name == "nt":
        real_publish = Path.rename

        def raced(source, target):
            occupy(target)
            return real_publish(source, target)

        monkeypatch.setattr(Path, "rename", raced)
    else:
        real_publish = os.link

        def raced(source, target):
            occupy(target)
            return real_publish(source, target)

        monkeypatch.setattr(os, "link", raced)

    with pytest.raises(FileExistsError):
        desktop.backup_on_upgrade(settings)
    assert len(occupied) == 1 and occupied[0].read_bytes() == b"another complete recovery config"
    assert not occupied[0].with_suffix(".db").exists()
    assert backup_bytes(settings) == {**original, occupied[0].name: b"another complete recovery config"}


def test_a_read_only_source_config_remains_read_only_in_its_complete_snapshot(local_library):
    settings, _ = local_library
    original = settings.config_file_path.read_bytes()
    mode = settings.config_file_path.stat().st_mode
    settings.config_file_path.chmod(mode & ~stat.S_IWUSR)
    try:
        desktop.backup_on_upgrade(settings)
        saved = next((settings.data_dir / "backups").glob("*.toml"))
        assert saved.read_bytes() == original
        assert not saved.stat().st_mode & stat.S_IWUSR
        assert not settings.config_file_path.stat().st_mode & stat.S_IWUSR
    finally:
        settings.config_file_path.chmod(mode)
        for file in (settings.data_dir / "backups").glob("*.toml"):
            file.chmod(file.stat().st_mode | stat.S_IWUSR)


def test_a_source_that_disappears_after_the_file_check_is_not_recreated_as_an_empty_library(tmp_path, monkeypatch):
    settings = Settings(data_dir=tmp_path / "disappearing-library")
    settings.ensure_dirs()
    conn = sqlite3.connect(settings.db_path)
    conn.execute("CREATE TABLE saved_text(body TEXT)")
    conn.commit()
    conn.close()
    real_is_file = Path.is_file

    def disappear(path):
        exists = real_is_file(path)
        if path == settings.db_path and exists:
            path.unlink()
        return exists

    monkeypatch.setattr(Path, "is_file", disappear)
    with pytest.raises(sqlite3.OperationalError):
        desktop.backup_on_upgrade(settings)
    assert not settings.db_path.exists()
    assert not list((settings.data_dir / "backups").iterdir())
