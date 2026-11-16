"""A link check has one accepted run, independent of its browser response."""
from __future__ import annotations

import asyncio
import threading
import time
from contextlib import contextmanager, suppress
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from facetmark.api import create_app
from facetmark.config import Settings
from facetmark.health import CheckReport


@pytest.fixture
def local(tmp_path):
    with TestClient(create_app(Settings(data_dir=tmp_path / "health-runs", use_mock_provider=True)),
                    base_url="http://127.0.0.1:8787", client=("127.0.0.1", 41000)) as client:
        yield client


@pytest.fixture
def checker(monkeypatch):
    value = SimpleNamespace(calls=[], hold=False, started=threading.Event(), release=threading.Event(), fail=False, errors=[])

    async def probe(_conn, **kwargs):
        value.calls.append(kwargs)
        value.started.set()
        while value.hold and not value.release.is_set():
            await asyncio.sleep(0.005)
        if value.fail:
            raise OSError("synthetic link check failure")
        count = len(kwargs.get("ids") or [])
        return CheckReport(considered=count, probed=count, by_status={"alive": count}, errors=value.errors)

    monkeypatch.setattr("facetmark.api.healthmod.check_bookmarks", probe)
    try:
        yield value
    finally:
        value.release.set()


def headers(client):
    return {"Authorization": "Bearer " + client.app.state.fm.token}


def original(client, request_id="health-original", **values):
    current = client.get("/link-health/runs/current", headers=headers(client)).json()
    return {"request_id": request_id, "limit": 20, "expected_library": current["library_id"], **values}


def accepted(client, body):
    response = client.post("/link-health/check", headers=headers(client), json=body)
    assert response.status_code == 200, response.text
    return response.json()


def completed(client, request_id):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        response = client.get("/link-health/runs/" + request_id, headers=headers(client))
        assert response.status_code == 200
        value = response.json()
        if value["state"] not in {"running", "stopping"}:
            return value
        time.sleep(0.005)
    raise AssertionError("The controlled synthetic link check did not finish")


def test_an_original_link_check_has_a_readable_receipt_and_is_not_repeated(tmp_path, monkeypatch):
    calls = []

    async def probe(_conn, **kwargs):
        calls.append(kwargs)
        await asyncio.sleep(0.01)
        return CheckReport(considered=0)

    monkeypatch.setattr("facetmark.api.healthmod.check_bookmarks", probe)
    with TestClient(create_app(Settings(data_dir=tmp_path, use_mock_provider=True))) as client:
        headers = {"Authorization": "Bearer " + client.app.state.fm.token}
        original = {"request_id": "health-original", "limit": 20}
        accepted = client.post("/link-health/check", headers=headers, json=original)
        assert accepted.status_code == 200
        assert accepted.json().get("request_id") == "health-original"
        found = client.get("/link-health/runs/health-original", headers=headers)
        assert found.status_code == 200 and found.json()["request_id"] == "health-original"
        replay = client.post("/link-health/check", headers=headers, json=original)
        assert replay.status_code == 200 and replay.json()["request_id"] == "health-original"
        assert len(calls) == 1


def test_acceptance_freezes_the_due_scope_and_reads_do_not_hold_the_network_lock(local, checker):
    from facetmark.service import save_bookmark

    state = local.app.state.fm
    ids = [save_bookmark(state.conn, f"https://health.example/{index}", title=str(index), settings=state.settings)["bookmark_id"]
           for index in range(3)]
    state.conn.commit()
    checker.hold = True
    body = original(local, ids=[ids[2], ids[0]], limit=2)
    result = accepted(local, body)
    assert result["targets_count"] == 2
    assert checker.started.wait(timeout=2)
    save_bookmark(state.conn, "https://health.example/new", title="New unrelated page", settings=state.settings)
    state.conn.commit()
    assert set(checker.calls[0]["ids"]) == {ids[0], ids[2]}
    assert local.get("/admin/job", headers=headers(local)).json()["health_check_running"] is True
    assert local.get("/link-health/summary", headers=headers(local)).status_code == 200
    assert accepted(local, body)["request_id"] == body["request_id"] and len(checker.calls) == 1
    newer = local.post("/link-health/check", headers=headers(local), json=original(local, "new-check"))
    assert newer.status_code == 409
    assert local.get("/link-health/runs/new-check", headers=headers(local)).status_code == 404
    checker.release.set()
    assert completed(local, body["request_id"])["report"]["probed"] == 2


def test_an_accepted_replay_precedes_a_newer_running_check_and_does_not_stop_it(local, checker):
    body = original(local, "completed-first")
    accepted(local, body)
    done = completed(local, body["request_id"])
    checker.hold = True
    accepted(local, original(local, "running-later"))
    assert checker.started.wait(timeout=2)
    assert accepted(local, body) == done
    assert local.post("/link-health/runs/completed-first/stop", headers=headers(local)).json() == done
    assert local.app.state.fm.health_running
    checker.release.set()
    completed(local, "running-later")


def test_a_changed_original_request_is_rejected_without_a_second_visit(local, checker):
    body = original(local)
    accepted(local, body)
    completed(local, body["request_id"])
    response = local.post("/link-health/check", headers=headers(local), json={**body, "limit": 50})
    assert response.status_code == 409 and len(checker.calls) == 1


def test_closing_an_absent_original_fences_a_late_start_without_checking_any_url(local, checker):
    body = original(local, "closed-before-arrival")
    path = "/link-health/runs/closed-before-arrival/close"
    response = local.post(path, headers=headers(local), json=body)
    assert response.status_code == 200 and response.json()["state"] == "closed"
    assert local.post(path, headers=headers(local), json=body).json() == response.json()
    assert local.post("/link-health/check", headers=headers(local), json=body).status_code == 409
    assert checker.calls == [] and not local.app.state.fm.health_running


def test_acceptance_winning_close_keeps_the_same_running_check(local, checker):
    checker.hold = True
    body = original(local, "accepted-before-close")
    accepted(local, body)
    response = local.post("/link-health/runs/accepted-before-close/close", headers=headers(local), json=body)
    assert response.status_code == 200 and response.json()["state"] == "running"
    assert local.app.state.fm.health_running and len(checker.calls) == 1
    checker.release.set()
    completed(local, body["request_id"])


def test_stop_is_bound_to_the_accepted_run_and_the_next_check_can_start(local, checker):
    checker.hold = True
    body = original(local, "stop-original")
    accepted(local, body)
    assert checker.started.wait(timeout=2)
    response = local.post("/link-health/runs/stop-original/stop", headers=headers(local))
    assert response.status_code == 200
    done = completed(local, body["request_id"])
    assert done["state"] == "cancelled" and not local.app.state.fm.health_running
    assert local.post("/link-health/runs/stop-original/stop", headers=headers(local)).json() == done
    assert accepted(local, body) == done and len(checker.calls) == 1
    checker.release.set()
    accepted(local, original(local, "after-stop"))
    assert completed(local, "after-stop")["state"] == "done"


@pytest.mark.asyncio
async def test_a_duplicate_stop_does_not_cancel_the_original_final_result_cleanup(tmp_path, monkeypatch):
    from facetmark.api import AppState

    state = AppState(Settings(data_dir=tmp_path / "duplicate-stop", use_mock_provider=True))
    runner = state.health_runs
    entered = asyncio.Event()

    async def probe(_conn, **_kwargs):
        entered.set()
        await asyncio.Event().wait()

    monkeypatch.setattr("facetmark.health.check_bookmarks", probe)
    try:
        await runner.start(request_id="duplicate-stop", ids=None, limit=20)
        task = runner.task
        await asyncio.wait_for(entered.wait(), 1)
        await runner.stop("duplicate-stop")
        # A metadata reader holds the lock while the worker is cancelled.
        # Another window's Stop is queued before the worker's final write.
        await state.lock.acquire()
        second = asyncio.create_task(runner.stop("duplicate-stop"))
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        state.lock.release()
        await second
        with suppress(asyncio.CancelledError):
            await asyncio.wait_for(task, 1)
        assert not state.health_running
        assert runner.task is None and runner.active_id is None
        assert runner.read("duplicate-stop")["state"] == "cancelled"
    finally:
        if state.lock.locked():
            state.lock.release()
        await runner.shutdown()
        state.conn.close()


def test_a_failed_acceptance_stores_no_receipt_or_running_flag_and_the_original_can_retry(local, checker, monkeypatch):
    body = original(local)
    with monkeypatch.context() as patch:
        @contextmanager
        def fail(_conn):
            raise OSError("synthetic acceptance write failure")
            yield
        patch.setattr("facetmark.health_runs.transaction", fail)
        with pytest.raises(OSError, match="acceptance write failure"):
            local.post("/link-health/check", headers=headers(local), json=body)
    assert not local.app.state.fm.health_running and checker.calls == []
    assert local.get("/link-health/runs/health-original", headers=headers(local)).status_code == 404
    accepted(local, body)
    assert completed(local, body["request_id"])["state"] == "done"


def test_recording_the_finished_result_can_fail_without_showing_a_finished_worker_as_running(local, checker, monkeypatch):
    def fail(*_args, **_kwargs):
        raise OSError("synthetic final receipt write failure")
    monkeypatch.setattr("facetmark.health_runs.finish", fail)
    body = original(local)
    accepted(local, body)
    done = completed(local, body["request_id"])
    assert done["state"] == "failed" and "final receipt write failure" in done["error"]
    assert not local.app.state.fm.health_running
    assert accepted(local, body) == done and len(checker.calls) == 1


@pytest.mark.parametrize("failure,partial", [(True, False), (False, True)])
def test_check_failures_have_a_readable_original_result_and_no_automatic_retry(local, checker, failure, partial):
    checker.fail = failure
    checker.errors = ["synthetic one-host failure"] if partial else []
    body = original(local)
    accepted(local, body)
    result = completed(local, body["request_id"])
    assert result["state"] == ("failed" if failure else "partial")
    assert accepted(local, body) == result and len(checker.calls) == 1


def test_original_results_survive_restart_and_an_unfinished_record_does_not_visit_on_startup(local, checker):
    import json

    from facetmark.client_operations import fingerprint
    from facetmark.health_runs import parameters

    body = original(local, "before-restart")
    accepted(local, body)
    done = completed(local, body["request_id"])
    state = local.app.state.fm
    params = parameters(ids=None, limit=20, expected_library=body["expected_library"])
    state.conn.execute("INSERT INTO health_run(request_id,fingerprint,params,targets,state,started_at) VALUES(?,?,?,?,?,?)",
                       ("interrupted-before-start", fingerprint("link-health", params), json.dumps(params), "[]", "running", 100))
    state.conn.commit()
    calls = len(checker.calls)
    with TestClient(create_app(state.settings), base_url="http://127.0.0.1:8787", client=("127.0.0.1", 41000)) as restarted:
        assert restarted.get("/link-health/runs/before-restart", headers=headers(restarted)).json() == done
        interrupted = restarted.get("/link-health/runs/interrupted-before-start", headers=headers(restarted)).json()
        assert interrupted["state"] == "interrupted" and not restarted.app.state.fm.health_running
        assert accepted(restarted, {**body, "request_id": "interrupted-before-start"}) == interrupted
        assert len(checker.calls) == calls


def test_an_original_scope_from_a_different_data_directory_cannot_start_or_close_here(local, checker):
    body = original(local, "other-library", expected_library="0" * 64)
    assert local.post("/link-health/check", headers=headers(local), json=body).status_code == 409
    assert local.post("/link-health/runs/other-library/close", headers=headers(local), json=body).status_code == 409
    assert local.get("/link-health/runs/other-library", headers=headers(local)).status_code == 404
    assert checker.calls == []


def test_corrupt_original_data_is_not_treated_as_an_absent_request(local, checker):
    body = original(local)
    accepted(local, body)
    completed(local, body["request_id"])
    local.app.state.fm.conn.execute("UPDATE health_run SET targets='broken' WHERE request_id=?", (body["request_id"],))
    local.app.state.fm.conn.commit()
    assert local.get("/link-health/runs/health-original", headers=headers(local)).status_code == 409
    assert local.post("/link-health/check", headers=headers(local), json=body).status_code == 409 and len(checker.calls) == 1


def test_health_run_authority_and_legacy_report_contract(local, checker):
    for path in ("/link-health/runs/current", "/link-health/runs/missing"):
        assert local.get(path).status_code == 401
    for path in ("/link-health/runs/missing/stop", "/link-health/runs/missing/close"):
        assert local.post(path, json={}).status_code == 401
    response = local.post("/link-health/check", headers=headers(local), json={"limit": 20})
    assert response.status_code == 200 and "probed" in response.json() and "request_id" not in response.json()
    assert local.post("/link-health/check", headers=headers(local), json=original(local, "current")).status_code == 422
