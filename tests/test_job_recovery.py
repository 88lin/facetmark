"""Task requests keep their accepted run and cannot target a newer attempt."""
from __future__ import annotations

import asyncio
import json
import threading

import pytest

from facetmark import admin, job_operations, service
from facetmark.db import open_db, set_meta
from facetmark.fetch import store as fetchstore
from tests.test_reading_jobs import client as client
from tests.test_reading_jobs import configure_chat, fake_fetch, save, wait_job


def test_start_replay_after_completion_does_not_fetch_twice(client, monkeypatch):
    bid = save(client, "start-once")
    contacted = fake_fetch(monkeypatch)
    body = {"mode": "fetch", "bookmark_ids": [bid], "force": True, "request_id": "start-once-request"}
    first = client.post("/admin/jobs/start", json=body)
    assert first.status_code == 200, first.text
    final = wait_job(client)
    repeated = client.post("/admin/jobs/start", json=body)
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["id"] == first.json()["id"]
    assert repeated.json()["run_id"] == first.json()["run_id"]
    assert client.get("/admin/job").json()["run_id"] == final["run_id"]
    assert contacted == ["https://reading.test/start-once"]
    receipt = client.get("/admin/jobs/operations/start-once-request")
    assert receipt.status_code == 200, receipt.text
    assert receipt.json()["result"]["id"] == first.json()["id"]


def test_start_id_cannot_be_reused_for_a_different_selection_or_action(client, monkeypatch):
    ids = [save(client, "first-selection"), save(client, "second-selection")]
    fake_fetch(monkeypatch)
    body = {"mode": "fetch", "bookmark_ids": [ids[0]], "request_id": "fixed-start-request"}
    first = client.post("/admin/jobs/start", json=body)
    assert first.status_code == 200
    wait_job(client)
    conflict = client.post("/admin/jobs/start", json={**body, "bookmark_ids": [ids[1]]})
    assert conflict.status_code == 409, conflict.text
    wrong_action = client.post("/admin/jobs/cancel", json={"request_id": body["request_id"],
        "job_id": first.json()["id"], "run_id": first.json().get("run_id", "old-run")})
    assert wrong_action.status_code == 409, wrong_action.text


def hold_fetch(monkeypatch):
    fake_fetch(monkeypatch)
    original = fetchstore.fetch_many
    entered, release = threading.Event(), threading.Event()

    async def hold(*args, **kwargs):
        entered.set()
        while not release.is_set():
            await asyncio.sleep(0.01)
        return await original(*args, **kwargs)

    monkeypatch.setattr(fetchstore, "fetch_many", hold)
    return entered, release


@pytest.mark.parametrize("action", ["pause", "cancel"])
def test_late_control_does_not_stop_a_different_task(client, monkeypatch, action):
    bid = save(client, "control-target")
    fake_fetch(monkeypatch)
    previous = client.post("/admin/jobs/start", json={"mode": "fetch", "bookmark_ids": [bid]}).json()
    wait_job(client)
    entered, release = hold_fetch(monkeypatch)
    current = client.post("/admin/jobs/start", json={"mode": "fetch", "bookmark_ids": [bid], "force": True}).json()
    assert entered.wait(2)
    try:
        response = client.post(f"/admin/jobs/{action}", json={"job_id": previous["id"],
            "run_id": previous.get("run_id", "old-run"), "request_id": f"late-{action}-request"})
        assert response.status_code == 409, response.text
        job = client.get("/admin/job").json()
        assert job["id"] == current["id"] and job["state"] == "running"
        assert not job["pause_requested"] and not job["cancel_requested"]
    finally:
        release.set()
        wait_job(client)


@pytest.mark.parametrize("action", ["pause", "cancel"])
def test_control_replay_after_a_new_task_returns_the_original_receipt(client, monkeypatch, action):
    bid = save(client, "accepted-control")
    entered, release = hold_fetch(monkeypatch)
    original = client.post("/admin/jobs/start", json={"mode": "fetch", "bookmark_ids": [bid]}).json()
    assert entered.wait(2)
    body = {"job_id": original["id"], "run_id": original.get("run_id", "old-run"),
            "request_id": f"accepted-{action}-request"}
    try:
        accepted = client.post(f"/admin/jobs/{action}", json=body)
        assert accepted.status_code == 200, accepted.text
    finally:
        release.set()
        wait_job(client)
    entered, release = hold_fetch(monkeypatch)
    current = client.post("/admin/jobs/start", json={"mode": "fetch", "bookmark_ids": [bid], "force": True}).json()
    assert entered.wait(2)
    try:
        repeated = client.post(f"/admin/jobs/{action}", json=body)
        assert repeated.status_code == 200, repeated.text
        assert repeated.json() == accepted.json()
        actual = client.get("/admin/job").json()
        assert actual["id"] == current["id"] and actual["state"] == "running"
        assert not actual["pause_requested"] and not actual["cancel_requested"]
    finally:
        release.set()
        wait_job(client)


def test_receipt_failure_rolls_back_the_snapshot_before_any_task_is_scheduled(client, monkeypatch):
    bid = save(client, "atomic-start")
    contacted = fake_fetch(monkeypatch)
    conn = client.app.state.fm.conn
    conn.execute("CREATE TRIGGER fail_task_receipt BEFORE INSERT ON processing_operation "
                 "BEGIN SELECT RAISE(ABORT,'synthetic task receipt failure'); END")
    result = client.post("/admin/jobs/start", json={"mode": "fetch", "bookmark_ids": [bid],
        "request_id": "rollback-task-request"})
    assert result.status_code == 500, result.text
    assert client.get("/admin/job").json()["state"] == "idle"
    assert conn.execute("SELECT count(*) FROM processing_item").fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM processing_run").fetchone()[0] == 0
    assert contacted == []


def test_saved_terminal_state_does_not_depend_on_the_last_job_file(client, monkeypatch):
    bid = save(client, "durable-state")
    fake_fetch(monkeypatch)
    created = client.post("/admin/jobs/start", json={"mode": "fetch", "bookmark_ids": [bid],
        "request_id": "durable-state-request"}).json()
    final = wait_job(client)
    runner = admin.JobRunner(client.app.state.fm.settings.data_dir)
    runner.path.write_text("not-json", encoding="utf-8")
    (runner.path.parent / "jobs" / f"{created['id']}.json").write_text("not-json", encoding="utf-8")
    restarted = admin.JobRunner(client.app.state.fm.settings.data_dir)
    saved = restarted.saved(created["id"], conn=client.app.state.fm.conn)
    assert saved["state"] == final["state"] == "done"
    assert saved["run_id"] == final["run_id"]
    assert saved["items"] == final["items"]


def test_active_model_work_blocks_a_new_task_but_not_a_saved_receipt(client, monkeypatch):
    bid = save(client, "model-busy")
    fake_fetch(monkeypatch)
    body = {"mode": "fetch", "bookmark_ids": [bid], "request_id": "before-model-work"}
    accepted = client.post("/admin/jobs/start", json=body)
    assert accepted.status_code == 200
    wait_job(client)
    state = client.app.state.fm
    state.model_users = 1
    try:
        assert client.post("/admin/jobs/start", json=body).status_code == 200
        refused = client.post("/admin/jobs/start", json={**body, "request_id": "while-model-work"})
        assert refused.status_code == 409, refused.text
    finally:
        state.model_users = 0


@pytest.mark.parametrize("action", ["pause", "cancel"])
def test_control_for_an_older_run_cannot_stop_a_resume_of_the_same_job(client, monkeypatch, action):
    bid = save(client, "same-job-new-run")
    fake_fetch(monkeypatch, failures=("https://reading.test/same-job-new-run",))
    original = client.post("/admin/jobs/start", json={"mode": "fetch", "bookmark_ids": [bid]}).json()
    assert wait_job(client)["state"] == "partial"
    entered, release = hold_fetch(monkeypatch)
    body = {"resume_id": original["id"], "resume_run_id": original["run_id"],
            "request_id": "same-job-resume-request", "confirmed": True}
    current = client.post("/admin/jobs/resume", json=body)
    assert current.status_code == 200, current.text
    assert entered.wait(2)
    try:
        assert current.json()["id"] == original["id"]
        assert current.json()["run_id"] != original["run_id"]
        late = client.post(f"/admin/jobs/{action}", json={"job_id": original["id"],
            "run_id": original["run_id"], "request_id": f"same-job-late-{action}"})
        assert late.status_code == 409, late.text
        actual = client.get("/admin/job").json()
        assert actual["run_id"] == current.json()["run_id"]
        assert not actual["pause_requested"] and not actual["cancel_requested"]
        repeated = client.post("/admin/jobs/resume", json=body)
        assert repeated.status_code == 200 and repeated.json() == current.json()
    finally:
        release.set()
        assert wait_job(client)["state"] == "done"
    repeated = client.post("/admin/jobs/resume", json=body)
    assert repeated.status_code == 200 and repeated.json() == current.json()
    receipt = client.get("/admin/jobs/operations/same-job-resume-request").json()
    assert receipt["result"] == current.json()
    assert receipt["job"]["run_id"] == current.json()["run_id"] and receipt["job"]["state"] == "done"


@pytest.mark.parametrize("action", ["pause", "cancel"])
def test_failed_control_receipt_rolls_back_flags_log_and_durable_run(client, monkeypatch, action):
    bid = save(client, "atomic-control")
    entered, release = hold_fetch(monkeypatch)
    created = client.post("/admin/jobs/start", json={"mode": "fetch", "bookmark_ids": [bid]}).json()
    assert entered.wait(2)
    state = client.app.state.fm
    before = client.get("/admin/job").json()
    stored = job_operations.saved_run(state.conn, run_id=created["run_id"])
    state.conn.execute("CREATE TRIGGER fail_control_receipt BEFORE INSERT ON processing_operation "
                       "BEGIN SELECT RAISE(ABORT,'synthetic control receipt failure'); END")
    try:
        response = client.post(f"/admin/jobs/{action}", json={"job_id": created["id"],
            "run_id": created["run_id"], "request_id": f"atomic-{action}-request"})
        assert response.status_code == 500, response.text
        actual = client.get("/admin/job").json()
        assert actual["pause_requested"] == before["pause_requested"]
        assert actual["cancel_requested"] == before["cancel_requested"]
        assert actual["log"] == before["log"] and actual["state"] == "running"
        assert job_operations.saved_run(state.conn, run_id=created["run_id"]) == stored
        assert client.get(f"/admin/jobs/operations/atomic-{action}-request").status_code == 404
    finally:
        release.set()
        wait_job(client)


def test_restart_before_provider_work_recovers_acceptance_without_scheduling_again(client, monkeypatch):
    bid = save(client, "accepted-before-work")
    contacted = fake_fetch(monkeypatch)
    entered = threading.Event()

    async def before_work(self, job, settings):
        entered.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(admin.JobRunner, "_run", before_work)
    body = {"mode": "fetch", "bookmark_ids": [bid], "request_id": "accepted-before-work-request"}
    response = client.post("/admin/jobs/start", json=body)
    assert response.status_code == 200 and entered.wait(2)
    state = client.app.state.fm
    original = state.jobs
    client.portal.call(original.shutdown)
    state.jobs = admin.JobRunner(state.settings.data_dir)
    recovered = client.get("/admin/jobs/operations/accepted-before-work-request").json()
    assert recovered["result"] == response.json()
    assert recovered["job"]["state"] == "interrupted" and recovered["job"]["resumable"]
    assert recovered["job"]["items"] == {"total": 1, "done": 0, "failed": 0}
    assert client.get("/admin/job").json()["state"] == "interrupted"
    repeated = client.post("/admin/jobs/start", json=body)
    assert repeated.status_code == 200 and repeated.json() == response.json()
    assert state.jobs._task is None and contacted == []
    assert state.conn.execute("SELECT count(*) FROM processing_run").fetchone()[0] == 1


def test_terminal_persistence_failure_keeps_results_and_closes_provider_and_connection(client, monkeypatch):
    bid = save(client, "terminal-save-failure", body="Saved source text")
    instances = configure_chat(client, monkeypatch)
    connections = []
    original_open = admin.open_db

    class TrackedConnection:
        def __init__(self, connection):
            self.connection, self.closed = connection, False

        def __getattr__(self, name):
            return getattr(self.connection, name)

        def close(self):
            self.connection.close()
            self.closed = True

    def tracked_open(*args, **kwargs):
        result = TrackedConnection(original_open(*args, **kwargs))
        connections.append(result)
        return result

    monkeypatch.setattr(admin, "open_db", tracked_open)
    conn = client.app.state.fm.conn
    conn.execute("CREATE TRIGGER fail_terminal_snapshot BEFORE UPDATE OF snapshot ON processing_run "
                 "WHEN json_extract(NEW.snapshot,'$.state')='done' "
                 "BEGIN SELECT RAISE(ABORT,'synthetic terminal save failure'); END")
    accepted = client.post("/admin/jobs/start", json={"mode": "summarize", "bookmark_ids": [bid],
        "confirmed": True, "request_id": "terminal-save-request"})
    assert accepted.status_code == 200, accepted.text
    final = wait_job(client)
    assert final["state"] == "failed" and "Could not save task status" in final["error"]
    assert instances[0].closed and len(connections) == 1 and connections[0].closed
    record = client.get(f"/bookmark/{bid}?body=true").json()
    assert record["summary"] == "A fresh reading summary." and record["body_text"] == "Saved source text"
    assert conn.execute("SELECT count(*) FROM processing_item WHERE job_id=?", (accepted.json()["id"],)).fetchone()[0] == 1
    assert job_operations.saved_run(conn, run_id=accepted.json()["run_id"])["state"] == "failed"


def test_cancel_takes_priority_over_pause_and_replaying_pause_cannot_restore_its_flag(client, monkeypatch):
    bid = save(client, "cancel-after-pause")
    entered, release = hold_fetch(monkeypatch)
    created = client.post("/admin/jobs/start", json={"mode": "fetch", "bookmark_ids": [bid]}).json()
    assert entered.wait(2)
    target = {"job_id": created["id"], "run_id": created["run_id"]}
    pause = {**target, "request_id": "pause-before-cancel"}
    cancel = {**target, "request_id": "cancel-after-pause"}
    try:
        assert client.post("/admin/jobs/pause", json=pause).status_code == 200
        assert client.post("/admin/jobs/cancel", json=cancel).status_code == 200
        actual = client.get("/admin/job").json()
        assert actual["cancel_requested"] and not actual["pause_requested"]
        assert client.post("/admin/jobs/pause", json=pause).status_code == 200
        assert client.post("/admin/jobs/pause", json={**target, "request_id": "late-pause-after-cancel"}).status_code == 409
        assert client.post("/admin/jobs/cancel", json={**target, "request_id": "second-cancel-request"}).status_code == 200
        actual = client.get("/admin/job").json()
        assert actual["cancel_requested"] and not actual["pause_requested"]
        assert sum("cancel requested" in line for line in actual["log"]) == 1
    finally:
        release.set()
        assert wait_job(client)["state"] == "cancelled"


def test_v13_upgrade_preserves_the_highest_number_across_all_legacy_files_and_retains_corruption(tmp_path):
    path = tmp_path / "facetmark.db"
    conn = open_db(path)
    conn.execute("DROP TABLE processing_operation")
    conn.execute("DROP TABLE processing_run")
    set_meta(conn, "schema_version", "12")
    conn.close()
    history = tmp_path / "jobs"
    history.mkdir()
    files = {
        tmp_path / "last-index-job.json": json.dumps({"params": {"bookmark_ids": [4000]}}),
        tmp_path / "last-index-job.ids.json": json.dumps({"ids": [7000]}),
        history / "aaaaaaaaaaaa.json": json.dumps({"params": {"bookmark_ids": [9000]}}),
        history / "bbbbbbbbbbbb.json": json.dumps({"params": {"bookmark_ids": [2, True, -1]}}),
        history / "cccccccccccc.json": "not-json",
    }
    for source, content in files.items():
        source.write_text(content, encoding="utf-8")
    upgraded = open_db(path)
    try:
        assert upgraded.execute("SELECT value FROM meta WHERE key='bookmark_id_highwater'").fetchone()[0] == "9000"
        assert upgraded.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] == "13"
        result = service.save_bookmark(upgraded, "https://reading.test/after-legacy-upgrade", title="new")
        assert result["bookmark_id"] == 9001
        for source, content in files.items():
            assert source.read_text(encoding="utf-8") == content
    finally:
        upgraded.close()
