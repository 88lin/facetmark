"""A numbered link check outlives its HTTP response without visiting twice.

The original scope and acceptance are stored before a network task is created.
Reads and accepted replays never create a task. Restart marks unfinished checks
interrupted; it does not automatically contact any saved URL.
"""
from __future__ import annotations

import asyncio
import contextlib
import json

from fastapi import HTTPException

from . import health
from .client_operations import fingerprint, transaction
from .db import now
from .desktop import database_identity


def parameters(*, ids: list[int] | None, limit: int, expected_library: str | None = None) -> dict:
    return {"ids": sorted(set(ids)) if ids is not None else None, "limit": limit, "expected_library": expected_library}


def _decode(row) -> dict:
    try:
        params, targets = json.loads(row["params"]), json.loads(row["targets"])
        report = json.loads(row["report"]) if row["report"] is not None else None
        if (not isinstance(params, dict) or not isinstance(params.get("limit"), int)
                or not isinstance(targets, list) or not all(isinstance(value, int) and value > 0 for value in targets)
                or report is not None and not isinstance(report, dict)
                or row["state"] not in {"running", "stopping", "done", "partial", "failed", "cancelled", "interrupted", "closed"}):
            raise ValueError
    except (TypeError, ValueError):
        raise HTTPException(409, "The original link check could not be read; keep its request for review") from None
    return {"request_id": row["request_id"], "state": row["state"], "params": params,
            "targets_count": len(targets), "started_at": row["started_at"], "finished_at": row["finished_at"],
            "report": report, "error": row["error"]}


def finish(conn, request_id: str, *, state: str, report: dict | None, error: str) -> None:
    with transaction(conn):
        conn.execute("UPDATE health_run SET state=?,finished_at=?,report=?,error=? WHERE request_id=? "
                     "AND state IN ('running','stopping')",
                     (state, now(), json.dumps(report, ensure_ascii=False) if report is not None else None, error, request_id))


class HealthRuns:
    def __init__(self, state):
        self.service = state
        self.task: asyncio.Task | None = None
        self.active_id: str | None = None
        self.stop_requested = False
        self.shutting_down = False
        # An I/O failure when recording the final result must not be displayed
        # as a still-running task. Its durable acceptance remains in the DB.
        self.unsaved_results: dict[str, dict] = {}
        state.conn.execute("UPDATE health_run SET state='interrupted',finished_at=?, "
                           "error='The previous link check was interrupted; saved link results remain available.' "
                           "WHERE state IN ('running','stopping')", (now(),))

    def read(self, request_id: str) -> dict | None:
        row = self.service.conn.execute("SELECT * FROM health_run WHERE request_id=?", (request_id,)).fetchone()
        if row is None:
            return None
        return {**_decode(row), **self.unsaved_results.get(request_id, {})}

    def current(self) -> dict:
        row = self.service.conn.execute("SELECT request_id FROM health_run WHERE state!='closed' "
                                        "ORDER BY started_at DESC,rowid DESC LIMIT 1").fetchone()
        return {"library_id": database_identity(self.service.settings.db_path),
                "running": self.service.health_running, "run": self.read(row["request_id"]) if row else None}

    async def start(self, *, request_id: str, ids: list[int] | None, limit: int, expected_library: str | None = None) -> dict:
        state = self.service
        params = parameters(ids=ids, limit=limit, expected_library=expected_library)
        digest = fingerprint("link-health", params)
        async with state.lock:
            row = state.conn.execute("SELECT fingerprint FROM health_run WHERE request_id=?", (request_id,)).fetchone()
            if row:
                if row["fingerprint"] != digest:
                    raise HTTPException(409, "This request ID belongs to a different original link check")
                original = self.read(request_id)
                if original["state"] == "closed":
                    raise HTTPException(409, "This original link check was closed; read saved results before a new check")
                return original
            if expected_library is not None and expected_library != database_identity(state.settings.db_path):
                raise HTTPException(409, "This original link check belongs to a different local library")
            if state.health_running or state.jobs.running or state.crawls.running:
                raise HTTPException(409, "Wait for the current link check or processing task")
            targets = [int(row["id"]) for row in health.due_for_check(state.conn, ids=ids, limit=limit)]
            settings = state.settings.model_copy(deep=True)
            with transaction(state.conn):
                state.conn.execute("INSERT INTO health_run(request_id,fingerprint,params,targets,state,started_at) "
                                   "VALUES(?,?,?,?,?,?)", (request_id, digest, json.dumps(params), json.dumps(targets), "running", now()))
            state.health_running = True
            self.active_id = request_id
            self.stop_requested = self.shutting_down = False
            self.task = asyncio.create_task(self._execute(request_id, targets, settings))
            return self.read(request_id)

    async def _execute(self, request_id: str, targets: list[int], settings) -> None:
        state = self.service
        report = None
        outcome, error = "failed", ""
        try:
            if self.stop_requested:
                raise asyncio.CancelledError
            result = await health.check_bookmarks(state.conn, ids=targets, limit=max(1, len(targets)),
                                                settings=settings, persist_lock=state.lock)
            report = result.as_dict()
            outcome = "partial" if result.errors else "done"
        except asyncio.CancelledError:
            outcome = "interrupted" if self.shutting_down else "cancelled"
            error = "The link check stopped; previously saved link results remain available."
        except Exception as failure:  # One failure belongs to this accepted run.
            from .admin import safe_error
            error = safe_error(failure, settings)
        finally:
            async with state.lock:
                try:
                    finish(state.conn, request_id, state=outcome, report=report, error=error)
                except Exception as failure:
                    from .admin import safe_error
                    self.unsaved_results[request_id] = {"state": "failed", "finished_at": now(), "report": report,
                        "error": "The check result could not be saved: " + safe_error(failure, settings)}
                finally:
                    if self.active_id == request_id:
                        state.health_running = False
                        self.active_id = None
                        self.task = None

    async def stop(self, request_id: str) -> dict:
        state = self.service
        async with state.lock:
            original = self.read(request_id)
            if original is None:
                raise HTTPException(404, "Original link check has not been accepted")
            if self.active_id == request_id and self.task and not self.task.done():
                with transaction(state.conn):
                    state.conn.execute("UPDATE health_run SET state='stopping' WHERE request_id=? AND state='running'", (request_id,))
                first_stop = not self.stop_requested
                self.stop_requested = True
                # Let the task enter its try/finally even if Stop follows the
                # accepting call before the task has received its first turn.
                if first_stop:
                    asyncio.get_running_loop().call_soon(self.task.cancel)
            return self.read(request_id)

    async def close(self, *, request_id: str, ids: list[int] | None, limit: int, expected_library: str | None = None) -> dict:
        state = self.service
        params = parameters(ids=ids, limit=limit, expected_library=expected_library)
        digest = fingerprint("link-health", params)
        async with state.lock:
            row = state.conn.execute("SELECT fingerprint FROM health_run WHERE request_id=?", (request_id,)).fetchone()
            if row:
                if row["fingerprint"] != digest:
                    raise HTTPException(409, "This request ID belongs to a different original link check")
                return self.read(request_id)
            if expected_library is not None and expected_library != database_identity(state.settings.db_path):
                raise HTTPException(409, "This original link check belongs to a different local library")
            with transaction(state.conn):
                state.conn.execute("INSERT INTO health_run(request_id,fingerprint,params,targets,state,started_at,finished_at) "
                                   "VALUES(?,?,?,?,?,?,?)", (request_id, digest, json.dumps(params), "[]", "closed", now(), now()))
            return self.read(request_id)

    async def shutdown(self) -> None:
        pending = self.task
        if pending and not pending.done():
            first_stop = not self.stop_requested
            self.stop_requested = self.shutting_down = True
            if first_stop:
                asyncio.get_running_loop().call_soon(pending.cancel)
            with contextlib.suppress(asyncio.CancelledError):
                await pending
