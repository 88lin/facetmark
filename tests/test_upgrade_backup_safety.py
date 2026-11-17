"""Isolated SQLite upgrade snapshots must retain every previous recovery file."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

from facetmark.migrations import backup_database


@pytest.fixture
def local_database(tmp_path):
    directory = tmp_path / "isolated-library"
    directory.mkdir()
    path = directory / "personal-library.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE saved_text (id INTEGER PRIMARY KEY, body TEXT)")
    conn.execute("INSERT INTO saved_text VALUES(1, 'original saved text')")
    conn.commit()
    try:
        yield conn, path
    finally:
        conn.close()


def stored_text(path):
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        return conn.execute("SELECT body FROM saved_text ORDER BY id").fetchall()


def test_repeated_upgrade_snapshots_preserve_the_original_and_return_the_new_file(local_database):
    conn, path = local_database
    original = backup_database(conn, suffix="bak-v1")
    original_bytes = original.read_bytes()
    conn.execute("INSERT INTO saved_text VALUES(2, 'later local text')")
    conn.commit()
    later = backup_database(conn, suffix="bak-v1")
    assert original.read_bytes() == original_bytes
    assert original == path.with_name(path.name + ".bak-v1")
    assert later != original and later.parent == path.parent
    assert stored_text(original) == [("original saved text",)]
    assert stored_text(later) == [("original saved text",), ("later local text",)]
    assert not list(path.parent.glob("*.tmp"))


def test_a_rejected_snapshot_inside_a_transaction_keeps_the_complete_old_backup(local_database):
    conn, path = local_database
    original = backup_database(conn, suffix="bak-v1")
    original_bytes = original.read_bytes()
    conn.execute("INSERT INTO saved_text VALUES(2, 'uncommitted text')")
    with pytest.raises(sqlite3.OperationalError):
        backup_database(conn, suffix="bak-v1")
    assert original.read_bytes() == original_bytes
    assert set(path.parent.iterdir()) == {path, original, path.with_name(path.name + "-journal")}
    conn.rollback()
    assert stored_text(original) == [("original saved text",)]


def test_partial_snapshot_failure_never_publishes_or_removes_a_recovery_file(local_database):
    conn, path = local_database
    original = backup_database(conn, suffix="bak-v1")
    original_bytes = original.read_bytes()

    class FailedSnapshot:
        def execute(self, sql, args=()):
            if sql.startswith("VACUUM INTO"):
                Path(args[0]).write_bytes(b"synthetic partial SQLite output")
                raise sqlite3.OperationalError("synthetic interrupted snapshot write")
            return conn.execute(sql, args)

    with pytest.raises(sqlite3.OperationalError, match="interrupted snapshot"):
        backup_database(FailedSnapshot(), suffix="bak-v1")
    assert original.read_bytes() == original_bytes
    assert set(path.parent.iterdir()) == {path, original}
    assert stored_text(path) == stored_text(original)


def test_flush_failure_retains_prior_snapshots_and_does_not_publish_a_new_one(local_database, monkeypatch):
    conn, path = local_database
    original = backup_database(conn, suffix="bak-v1")
    original_bytes = original.read_bytes()

    def rejected_flush(_):
        raise OSError("synthetic backup flush failed")

    monkeypatch.setattr(os, "fsync", rejected_flush)
    with pytest.raises(OSError, match="backup flush"):
        backup_database(conn, suffix="bak-v1")
    assert original.read_bytes() == original_bytes
    assert set(path.parent.iterdir()) == {path, original}


def test_a_publication_collision_preserves_the_other_snapshot_and_chooses_a_new_name(local_database, monkeypatch):
    conn, path = local_database
    original = backup_database(conn, suffix="bak-v1")
    original_bytes = original.read_bytes()
    conn.execute("INSERT INTO saved_text VALUES(2, 'current local text')")
    conn.commit()
    collision = []

    def occupy(target):
        target = Path(target)
        if target != original and not collision:
            target.write_bytes(original_bytes)
            collision.append(target)

    if os.name == "nt":
        publish = Path.rename

        def raced_rename(source, target):
            occupy(target)
            return publish(source, target)

        monkeypatch.setattr(Path, "rename", raced_rename)
    else:
        publish = os.link

        def raced_link(source, target):
            occupy(target)
            return publish(source, target)

        monkeypatch.setattr(os, "link", raced_link)

    saved = backup_database(conn, suffix="bak-v1")
    assert len(collision) == 1 and saved not in {original, collision[0]}
    assert original.read_bytes() == collision[0].read_bytes() == original_bytes
    assert stored_text(saved) == [("original saved text",), ("current local text",)]
    assert set(path.parent.iterdir()) == {path, original, collision[0], saved}
