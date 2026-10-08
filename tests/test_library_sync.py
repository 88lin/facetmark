"""Only synthetic SQLite databases and temporary shared directories are used."""

from __future__ import annotations

import asyncio
import json
import sqlite3
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from facetmark import library, library_sync
from facetmark.config import Settings
from facetmark.db import open_db
from facetmark.library_sync import ApplyRequest, SharedFolderSync, SyncConfig


@pytest.fixture()
def peers(tmp_path):
    shared = tmp_path / "shared-documents"
    shared.mkdir()
    instances = []
    for name in ("device-a", "device-b"):
        settings = Settings(data_dir=tmp_path / name, use_mock_provider=True,
                            api_key="SYNTHETIC_SECRET_NEVER_EXPORT")
        settings.ensure_dirs()
        conn = open_db(settings.db_path, same_thread=False)
        conn.commit()
        sync = SharedFolderSync(conn, settings)
        sync.configure(SyncConfig(folder=str(shared), enabled=True))
        instances.append(sync)
    yield (*instances, shared)
    for sync in instances:
        sync.conn.close()


def add(sync, *, url="https://example.test/read", title="A saved page", folder="Reading", tags=None):
    result = library.create_bookmark(sync.conn, library.CreateBookmark(
        url=url, title=title, folder=folder, tags=tags or ["research"]), settings=sync.settings)
    sync.conn.commit()
    return result["bookmark_id"]


def edit(sync, bid, **changes):
    library.update_bookmark(sync.conn, bid, library.EditBookmark(**changes), settings=sync.settings)
    sync.conn.commit()


def run(sync, resolutions=None):
    preview = sync.preview()
    return sync.apply(ApplyRequest(preview_id=preview["preview_id"], resolutions=resolutions or {}))


def row(sync):
    return sync.conn.execute("SELECT * FROM bookmark ORDER BY id").fetchone()


def converge(a, b):
    bid = add(a)
    run(a)
    run(b)
    return bid, row(b)["id"]


def test_metadata_roundtrip_stable_identity_url_edit_and_local_backup(peers):
    a, b, shared = peers
    bid = add(a, tags=["z", "a"])
    a.conn.execute("UPDATE bookmark SET date_added=1700000000 WHERE id=?", (bid,))
    a.conn.execute("INSERT INTO content(bookmark_id,body_text) VALUES(?,?)", (bid, "PRIVATE_SAVED_BODY"))
    a.conn.commit()
    first = run(a)
    assert first["counts"]["upload_new"] == 1
    assert first["backup_path"] is None
    imported = run(b)
    assert imported["counts"]["download_new"] == 1
    assert Path(imported["backup_path"]).is_file()
    assert not Path(imported["backup_path"]).is_relative_to(shared)
    assert row(b)["date_added"] == 1700000000
    assert json.loads(row(b)["tags"]) == ["a", "z"]
    assert b.conn.execute("SELECT count(*) FROM content").fetchone()[0] == 0
    sid = a.conn.execute("SELECT sync_id FROM library_sync_identity WHERE bookmark_id=?", (bid,)).fetchone()[0]
    edit(a, bid, url="https://example.test/new-address", title="Renamed")
    run(a)
    run(b)
    assert row(b)["url"] == "https://example.test/new-address"
    assert b.conn.execute("SELECT sync_id FROM library_sync_identity WHERE bookmark_id=?", (row(b)["id"],)).fetchone()[0] == sid
    assert b.conn.execute("SELECT count(*) FROM bookmark").fetchone()[0] == 1
    assert run(b)["counts"]["unchanged"] == 1
    text = "\n".join(path.read_text(encoding="utf-8") for path in (shared / library_sync.DIRECTORY).glob("*.json"))
    assert "SYNTHETIC_SECRET" not in text and "PRIVATE_SAVED_BODY" not in text
    for path in (shared / library_sync.DIRECTORY).glob("*.json"):
        for record in json.loads(path.read_text(encoding="utf-8"))["changes"].values():
            assert record is None or set(record) == set(library_sync.FIELDS)


def test_delete_tombstone_survives_sqlite_id_reuse_and_cannot_resurrect(peers):
    a, b, _ = peers
    old, _ = converge(a, b)
    old_sid = a.conn.execute("SELECT sync_id FROM library_sync_identity WHERE bookmark_id=?", (old,)).fetchone()[0]
    library.delete_bookmarks(a.conn, [old])
    new = add(a, url="https://example.test/new", title="New identity")
    assert new == old  # INTEGER PRIMARY KEY IDs may be reused after a deletion.
    preview = a.preview()
    assert preview["counts"]["upload_delete"] == 1
    a.apply(ApplyRequest(preview_id=preview["preview_id"]))
    result = run(b)
    assert result["counts"]["download_delete"] == 1
    assert row(b)["title"] == "New identity"
    identity = a.conn.execute("SELECT bookmark_id FROM library_sync_identity WHERE sync_id=?", (old_sid,)).fetchone()
    assert identity[0] is None
    run(b)
    run(a)
    assert a.conn.execute("SELECT count(*) FROM bookmark").fetchone()[0] == 1


def test_initial_same_url_is_adopted_and_differing_metadata_needs_a_choice(peers):
    a, b, _ = peers
    add(a, title="Remote title")
    run(a)
    bid = add(b, title="My existing title")
    preview = b.preview()
    assert preview["counts"]["conflicts"] == 1
    conflict = preview["conflicts"][0]
    with pytest.raises(HTTPException) as error:
        b.apply(ApplyRequest(preview_id=preview["preview_id"]))
    assert error.value.status_code == 409
    result = b.apply(ApplyRequest(preview_id=preview["preview_id"], resolutions={conflict["id"]: "remote"}))
    assert result["counts"]["download_update"] == 1
    assert row(b)["id"] == bid and row(b)["title"] == "Remote title"
    assert b.conn.execute("SELECT count(*) FROM bookmark").fetchone()[0] == 1


@pytest.mark.parametrize("resolution,expected", [("local", "B edit"), ("remote", "A edit")])
def test_concurrent_edits_are_not_silently_overwritten(peers, resolution, expected):
    a, b, _ = peers
    aid, bid = converge(a, b)
    edit(a, aid, title="A edit")
    edit(b, bid, title="B edit")
    run(a)
    preview = b.preview()
    assert preview["conflicts"][0]["local"]["title"] == "B edit"
    assert preview["conflicts"][0]["remote"]["title"] == "A edit"
    assert row(b)["title"] == "B edit"
    b.apply(ApplyRequest(preview_id=preview["preview_id"], resolutions={preview["conflicts"][0]["id"]: resolution}))
    run(a)
    assert row(a)["title"] == row(b)["title"] == expected


def test_remote_delete_and_local_edit_conflict_can_restore_the_edited_record(peers):
    a, b, _ = peers
    aid, bid = converge(a, b)
    library.delete_bookmarks(a.conn, [aid])
    edit(b, bid, title="Keep my changed page")
    run(a)
    preview = b.preview()
    conflict = preview["conflicts"][0]
    assert conflict["remote"] is None
    b.apply(ApplyRequest(preview_id=preview["preview_id"], resolutions={conflict["id"]: "local"}))
    run(a)
    assert row(a)["title"] == "Keep my changed page"


def test_offline_branches_preserve_both_remote_versions(peers):
    a, b, shared = peers
    aid, _ = converge(a, b)
    directory = shared / library_sync.DIRECTORY
    common = library_sync._history(directory)
    sid = next(iter(common["versions"]))
    original = common["versions"][sid][0][1]
    edit(a, aid, title="Online change")
    run(a)
    # Simulate an offline replica publishing against the last common parents.
    b._publish(directory, common, {sid: {**original, "title": "Offline change"}})
    preview = a.preview()
    conflict = preview["conflicts"][0]
    assert conflict["reason"] == "remote_concurrent_changes"
    assert {item["record"]["title"] for item in conflict["remote_versions"]} == {"Online change", "Offline change"}
    selected = next(item["choice"] for item in conflict["remote_versions"] if item["record"]["title"] == "Offline change")
    a.apply(ApplyRequest(preview_id=preview["preview_id"], resolutions={sid: selected}))
    run(b)
    assert row(a)["title"] == row(b)["title"] == "Offline change"
    assert len(list(directory.glob("*.json"))) == 4


@pytest.mark.parametrize("changed", ["local", "remote"])
def test_apply_rejects_changes_after_preview(peers, changed):
    a, b, _ = peers
    aid, bid = converge(a, b)
    preview = b.preview()
    if changed == "local":
        edit(b, bid, title="New local edit")
    else:
        edit(a, aid, title="New remote edit")
        run(a)
    with pytest.raises(HTTPException) as error:
        b.apply(ApplyRequest(preview_id=preview["preview_id"]))
    assert error.value.status_code == 409
    assert row(b)["title"] == ("New local edit" if changed == "local" else "A saved page")


def test_publish_failure_rolls_back_imports_and_keeps_local_backup(peers, monkeypatch):
    a, b, _ = peers
    add(a)
    run(a)
    preview = b.preview()
    def fail(*_args):
        raise OSError("Synthetic unavailable folder")
    monkeypatch.setattr(b, "_publish", fail)
    with pytest.raises(OSError):
        b.apply(ApplyRequest(preview_id=preview["preview_id"]))
    assert b.conn.execute("SELECT count(*) FROM bookmark").fetchone()[0] == 0
    backups = list((b.settings.data_dir / "backups").glob("library-sync-*.db"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as backup:
        assert backup.execute("SELECT count(*) FROM bookmark").fetchone()[0] == 0


def test_karakeep_owned_and_adopted_bookmarks_are_not_modified_or_exported(peers):
    a, b, _ = peers
    add(a)
    run(a)
    bid = add(b, title="Karakeep is authoritative")
    b.conn.execute("CREATE TABLE IF NOT EXISTS karakeep_doc (external_id TEXT PRIMARY KEY,bookmark_id INTEGER)")
    b.conn.execute("INSERT INTO karakeep_doc VALUES('synthetic-id',?)", (bid,))
    b.conn.commit()
    preview = b.preview()
    assert preview["excluded_karakeep"] == 1
    assert preview["counts"]["download_new"] == 0
    b.apply(ApplyRequest(preview_id=preview["preview_id"]))
    assert row(b)["title"] == "Karakeep is authoritative"


def test_sync_config_requires_explicit_first_review_and_allows_disabling_offline(peers):
    a, _, shared = peers
    a.configure(SyncConfig(folder=str(shared), enabled=True, auto_sync=True, poll_seconds=30))
    preview = a.preview()
    with pytest.raises(HTTPException):
        a.apply(ApplyRequest(preview_id=preview["preview_id"]), automatic=True)
    a.apply(ApplyRequest(preview_id=preview["preview_id"]))
    assert a.status()["needs_review"] is False
    (shared / library_sync.DIRECTORY).rename(shared / "temporarily-unavailable")
    a.configure(SyncConfig(folder=str(shared), enabled=False))
    assert a.status()["enabled"] is False


@pytest.mark.parametrize("damage", ["unknown_fields", "missing_parent", "conflict_copy", "oversized", "missing_history"])
def test_malformed_or_incomplete_transport_never_changes_the_library(peers, monkeypatch, damage):
    a, b, shared = peers
    aid, _ = converge(a, b)
    directory = shared / library_sync.DIRECTORY
    path = next(directory.glob("*.json"))
    commit = json.loads(path.read_text(encoding="utf-8"))
    if damage == "unknown_fields":
        next(iter(commit["changes"].values()))["body_text"] = "MUST_NOT_IMPORT"
        path.write_text(json.dumps(commit), encoding="utf-8")
    elif damage == "missing_parent":
        commit["parents"] = [str(uuid.uuid4())]
        path.write_text(json.dumps(commit), encoding="utf-8")
    elif damage == "conflict_copy":
        (directory / "commit-conflicted-copy.json").write_text("{}", encoding="utf-8")
    elif damage == "oversized":
        monkeypatch.setattr(library_sync, "MAX_FILE_BYTES", 8)
    else:
        path.unlink()
    with pytest.raises(HTTPException):
        b.preview()
    assert row(a)["id"] == aid and row(b)["title"] == "A saved page"


def test_profile_and_relative_paths_are_rejected_before_writing(peers, tmp_path):
    a, _, _ = peers
    profile = tmp_path / "Microsoft" / "Edge" / "User Data" / "Default"
    profile.mkdir(parents=True)
    for folder in (str(profile), "relative-folder", str(a.settings.data_dir)):
        with pytest.raises(HTTPException):
            a.configure(SyncConfig(folder=folder, enabled=True))
    assert not (profile / library_sync.DIRECTORY).exists()


def test_symlink_commit_is_rejected(peers, tmp_path):
    a, _, shared = peers
    target = tmp_path / "unrelated.json"
    target.write_text("{}", encoding="utf-8")
    link = shared / library_sync.DIRECTORY / f"commit-{uuid.uuid4()}.json"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("This platform does not permit test symlinks")
    with pytest.raises(HTTPException):
        a.preview()
    assert target.read_text(encoding="utf-8") == "{}"


def test_routes_require_token_loopback_and_pause_for_active_jobs(peers):
    a, _, _ = peers
    app = FastAPI()
    app.state.fm = SimpleNamespace(conn=a.conn, settings=a.settings, lock=asyncio.Lock(),
                                   jobs=SimpleNamespace(running=False), library_sync=a)
    def auth(request: Request):
        if request.headers.get("authorization") != "Bearer synthetic-token":
            raise HTTPException(401)
    library_sync.register(app, [Depends(auth)])
    with TestClient(app, client=("127.0.0.1", 1234)) as client:
        for suffix in ("status", "config", "preview", "apply"):
            response = client.get(f"/admin/library/sync/{suffix}") if suffix == "status" else client.post(f"/admin/library/sync/{suffix}", json={})
            assert response.status_code == 401
        headers = {"Authorization": "Bearer synthetic-token"}
        assert client.get("/admin/library/sync/status", headers=headers).json()["metadata_only"] is True
        app.state.fm.jobs.running = True
        assert client.post("/admin/library/sync/preview", json={}, headers=headers).status_code == 409
    with TestClient(app, client=("192.0.2.3", 1234)) as remote:
        assert remote.get("/admin/library/sync/status", headers=headers).status_code == 403


def test_preview_lists_actual_changes_and_distinguishes_new_from_deleted(peers):
    a, b, _ = peers
    bid = add(a)
    preview = a.preview()
    change = preview["changes"][0]
    assert change["directions"] == ["upload"]
    assert change["local_exists"] is True and change["remote_exists"] is False
    assert change["target"]["title"] == "A saved page"
    a.apply(ApplyRequest(preview_id=preview["preview_id"]))
    run(b)
    assert a.preview()["changes"] == []
    library.delete_bookmarks(a.conn, [bid])
    change = a.preview()["changes"][0]
    assert change["target"] is None and change["local_exists"] is True
    assert change["remote"]["title"] == "A saved page"


def test_duplicate_urls_from_offline_initial_imports_are_resolvable_in_preview(peers):
    a, b, shared = peers
    add(a)
    run(a)
    directory = shared / library_sync.DIRECTORY
    history = library_sync._history(directory)
    original = next(iter(history["versions"].values()))[0][1]
    other = str(uuid.uuid4())
    b._publish(directory, {"heads": []}, {other: {**original, "title": "Independent import"}})
    preview = a.preview()
    assert len(preview["conflicts"]) == 2
    conflict = next(item for item in preview["conflicts"] if item["id"] == other)
    assert conflict["local"] is None and conflict["reason"] == "duplicate_url_keep_one"
    a.apply(ApplyRequest(preview_id=preview["preview_id"], resolutions={item["id"]: "local" for item in preview["conflicts"]}))
    assert a.conn.execute("SELECT count(*) FROM bookmark").fetchone()[0] == 1
    assert library_sync._history(directory)["versions"][other][0][1] is None


def test_previously_attached_record_becoming_karakeep_owned_is_not_overwritten(peers):
    a, b, _ = peers
    aid, bid = converge(a, b)
    b.conn.execute("UPDATE bookmark SET source='karakeep' WHERE id=?", (bid,))
    b.conn.commit()
    edit(a, aid, url="https://example.test/remote-new-url", title="Changed elsewhere")
    run(a)
    preview = b.preview()
    assert not preview["conflicts"] and not preview["changes"]
    b.apply(ApplyRequest(preview_id=preview["preview_id"]))
    assert row(b)["title"] == "A saved page"
    assert b.conn.execute("SELECT count(*) FROM bookmark").fetchone()[0] == 1


def test_modifying_old_valid_commit_is_not_treated_as_a_new_remote_change(peers):
    a, b, shared = peers
    converge(a, b)
    path = next((shared / library_sync.DIRECTORY).glob("*.json"))
    commit = json.loads(path.read_text(encoding="utf-8"))
    next(iter(commit["changes"].values()))["title"] = "Rewritten history"
    path.write_text(json.dumps(commit), encoding="utf-8")
    with pytest.raises(HTTPException, match="immutable history"):
        b.preview()
    assert row(b)["title"] == "A saved page"


def test_atomic_publish_failure_leaves_no_commit_or_pending_file(peers, monkeypatch):
    a, _, shared = peers
    add(a)
    preview = a.preview()
    def fail(*_args):
        raise OSError("Synthetic atomic rename failure")
    monkeypatch.setattr(library_sync.os, "replace", fail)
    with pytest.raises(OSError):
        a.apply(ApplyRequest(preview_id=preview["preview_id"]))
    directory = shared / library_sync.DIRECTORY
    assert list(directory.glob("*.json")) == []
    assert list(directory.glob(".pending-*")) == []
    assert a.conn.execute("SELECT count(*) FROM library_sync_baseline").fetchone()[0] == 0


@pytest.mark.asyncio
async def test_automatic_poll_imports_only_after_approval_and_pauses_at_conflicts(peers, monkeypatch):
    a, b, shared = peers
    aid, bid = converge(a, b)
    b.configure(SyncConfig(folder=str(shared), enabled=True, auto_sync=True, poll_seconds=30))
    state = SimpleNamespace(conn=b.conn, settings=b.settings, lock=asyncio.Lock(),
                            jobs=SimpleNamespace(running=False), library_sync=b)
    async def stop_after_one_pass(_delay):
        raise asyncio.CancelledError
    monkeypatch.setattr(library_sync.asyncio, "sleep", stop_after_one_pass)
    edit(a, aid, title="Automatic update")
    run(a)
    with pytest.raises(asyncio.CancelledError):
        await library_sync.poll(state)
    assert row(b)["title"] == "Automatic update"
    edit(a, aid, title="Remote concurrent")
    edit(b, bid, title="Local concurrent")
    run(a)
    with pytest.raises(asyncio.CancelledError):
        await library_sync.poll(state)
    assert row(b)["title"] == "Local concurrent"
    assert b.status()["pending_conflicts"] == 1


def test_persisted_baseline_after_manager_restart_still_detects_concurrent_edits(peers):
    a, b, _ = peers
    aid, bid = converge(a, b)
    restarted = SharedFolderSync(b.conn, b.settings)
    assert restarted.status()["needs_review"] is False
    assert restarted.status()["device_id"] == b.status()["device_id"]
    edit(a, aid, title="Remote after restart")
    edit(restarted, bid, title="Local after restart")
    run(a)
    preview = restarted.preview()
    assert preview["counts"]["conflicts"] == 1
    assert preview["conflicts"][0]["local"]["title"] == "Local after restart"


def test_two_remote_url_edits_can_swap_without_a_transient_uniqueness_failure(peers):
    a, b, shared = peers
    add(a, url="https://example.test/one", title="First")
    add(a, url="https://example.test/two", title="Second")
    run(a)
    run(b)
    directory = shared / library_sync.DIRECTORY
    history = library_sync._history(directory)
    records = {sid: values[0][1] for sid, values in history["versions"].items()}
    changes = {}
    for sid, record in records.items():
        suffix = "two" if record["url"].endswith("/one") else "one"
        changes[sid] = {**record, "url": f"https://example.test/{suffix}"}
    a._publish(directory, history, changes)
    result = run(b)
    assert result["counts"]["download_update"] == 2
    assert {record["title"]: record["url"] for record in b.conn.execute("SELECT * FROM bookmark")} == {
        "First": "https://example.test/two", "Second": "https://example.test/one"}


@pytest.mark.parametrize("local_edit", [False, True])
def test_duplicate_url_conflicts_with_no_absent_version_offer_explicit_deletion(peers, local_edit):
    a, b, shared = peers
    add(a, url="https://example.test/one", title="Keep this page")
    add(a, url="https://example.test/two", title="Duplicate after edit")
    run(a)
    run(b)
    directory = shared / library_sync.DIRECTORY
    history = library_sync._history(directory)
    keep_sid = next(sid for sid, values in history["versions"].items() if values[0][1]["url"].endswith("/one"))
    delete_sid = next(sid for sid in history["versions"] if sid != keep_sid)
    second = history["versions"][delete_sid][0][1]
    if local_edit:
        second_id = b.conn.execute("SELECT id FROM bookmark WHERE url=?", (second["url"],)).fetchone()[0]
        edit(b, second_id, title="Also changed on this device")
    a._publish(directory, history, {delete_sid: {**second, "url": "https://example.test/one"}})

    preview = b.preview()
    assert len(preview["conflicts"]) == 2
    assert all(conflict["can_delete"] for conflict in preview["conflicts"])
    assert all(conflict["local"] and all(version["record"] for version in conflict["remote_versions"])
               for conflict in preview["conflicts"])
    result = b.apply(ApplyRequest(preview_id=preview["preview_id"],
                                 resolutions={keep_sid: "local", delete_sid: "delete"}))
    assert result["counts"]["download_delete"] == result["counts"]["upload_delete"] == 1
    with sqlite3.connect(result["backup_path"]) as backup:
        assert backup.execute("SELECT count(*) FROM bookmark").fetchone()[0] == 2
    run(a)
    assert a.conn.execute("SELECT count(*) FROM bookmark").fetchone()[0] == 1
    assert row(a)["title"] == row(b)["title"] == "Keep this page"
    assert library_sync._history(directory)["versions"][delete_sid][0][1] is None


@pytest.mark.parametrize("limit", ["commits", "bytes", "records"])
def test_publish_refuses_to_make_the_existing_history_unreadable(peers, monkeypatch, limit):
    a, b, shared = peers
    aid, _ = converge(a, b)
    directory = shared / library_sync.DIRECTORY
    original = {path.name: path.read_bytes() for path in directory.glob("*.json")}
    if limit == "records":
        monkeypatch.setattr(library_sync, "MAX_RECORDS", 1)
        add(a, url="https://example.test/another", title="Stays local")
    else:
        edit(a, aid, title="Stays local")
        if limit == "commits":
            monkeypatch.setattr(library_sync, "MAX_COMMITS", 1)
        else:
            monkeypatch.setattr(library_sync, "MAX_TOTAL_BYTES", sum(map(len, original.values())) + 1)
    preview = a.preview()
    with pytest.raises(HTTPException, match="supported size") as error:
        a.apply(ApplyRequest(preview_id=preview["preview_id"]))
    assert error.value.status_code == 409
    assert {path.name: path.read_bytes() for path in directory.glob("*.json")} == original
    assert len(library_sync._history(directory)["versions"]) == 1
    assert not b.preview()["changes"]


@pytest.mark.asyncio
async def test_idle_automatic_poll_preserves_a_manual_preview_and_does_not_write(peers, monkeypatch):
    a, b, shared = peers
    converge(a, b)
    b.configure(SyncConfig(folder=str(shared), enabled=True, auto_sync=True, poll_seconds=30))
    preview = b.preview()
    last_sync = b.status()["last_sync_at"]
    changes = b.conn.total_changes
    monkeypatch.setattr(library_sync.time, "time", lambda: last_sync + 60)
    state = SimpleNamespace(conn=b.conn, settings=b.settings, lock=asyncio.Lock(),
                            jobs=SimpleNamespace(running=False), library_sync=b)
    async def stop_after_one_pass(_delay):
        raise asyncio.CancelledError
    monkeypatch.setattr(library_sync.asyncio, "sleep", stop_after_one_pass)
    with pytest.raises(asyncio.CancelledError):
        await library_sync.poll(state)
    assert b.status()["last_sync_at"] == last_sync
    assert b.conn.total_changes == changes
    assert set(b.previews) == {preview["preview_id"]}


def test_embedded_url_credentials_are_excluded_before_publishing(peers):
    a, _, shared = peers
    add(a, url="https://synthetic-user:NEVER_SHARE_THIS@example.test/private")
    preview = a.preview()
    assert preview["excluded_unsupported"] == 1
    assert not preview["changes"] and not preview["conflicts"]
    a.apply(ApplyRequest(preview_id=preview["preview_id"]))
    assert list((shared / library_sync.DIRECTORY).glob("*.json")) == []
