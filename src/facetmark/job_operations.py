"""Atomic task acceptance and run snapshots, independent of the latest job file."""
from __future__ import annotations

import contextlib
import hashlib
import json
import time
from collections.abc import Iterator

from fastapi import HTTPException


@contextlib.contextmanager
def atomic(conn) -> Iterator[None]:
    conn.execute("SAVEPOINT task_acceptance")
    try:
        yield
    except BaseException:
        conn.execute("ROLLBACK TO task_acceptance")
        conn.execute("RELEASE task_acceptance")
        raise
    else:
        conn.execute("RELEASE task_acceptance")


def fingerprint(action: str, values: dict) -> str:
    content = json.dumps([action, values], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def receipt(conn, request_id: str | None, *, action: str | None = None, digest: str | None = None) -> dict | None:
    if request_id is None:
        return None
    row = conn.execute("SELECT * FROM processing_operation WHERE request_id=?", (request_id,)).fetchone()
    if row is None:
        return None
    if (action is not None and row["action"] != action) or (digest is not None and row["fingerprint"] != digest):
        raise HTTPException(409, "This task request ID belongs to a different operation")
    return {"request_id": request_id, "action": row["action"], "job_id": row["job_id"],
            "run_id": row["run_id"], "result": json.loads(row["result"])}


def accept(conn, request_id: str | None, *, action: str, digest: str, job, result: dict) -> None:
    if request_id is not None:
        conn.execute("INSERT INTO processing_operation(request_id,fingerprint,action,job_id,run_id,result,created_at) "
                     "VALUES(?,?,?,?,?,?,?)", (request_id, digest, action, job.id, job.run_id,
                                               json.dumps(result, ensure_ascii=False), int(time.time())))


def save_run(conn, job, *, create: bool = False) -> bool:
    snapshot = json.dumps(job.as_dict(), ensure_ascii=False)
    if create:
        conn.execute("INSERT INTO processing_run(run_id,job_id,snapshot,created_at,updated_at) VALUES(?,?,?,?,?)",
                     (job.run_id, job.id, snapshot, int(time.time()), int(time.time())))
        return True
    return bool(conn.execute("UPDATE processing_run SET snapshot=?,updated_at=? WHERE run_id=? AND job_id=?",
                             (snapshot, int(time.time()), job.run_id, job.id)).rowcount)


def saved_run(conn, *, job_id: str | None = None, run_id: str | None = None) -> dict | None:
    if run_id is not None:
        row = conn.execute("SELECT snapshot FROM processing_run WHERE run_id=?", (run_id,)).fetchone()
    elif job_id is not None:
        row = conn.execute("SELECT snapshot FROM processing_run WHERE job_id=? ORDER BY rowid DESC LIMIT 1",
                           (job_id,)).fetchone()
    else:
        row = conn.execute("SELECT snapshot FROM processing_run ORDER BY rowid DESC LIMIT 1").fetchone()
    return json.loads(row["snapshot"]) if row is not None else None


def recovered(snapshot: dict) -> dict:
    value = {**snapshot}
    if value.get("state") == "running":
        value.update(state="interrupted", current=None, pause_requested=False, cancel_requested=False)
    value["resumable"] = value.get("params", {}).get("mode") in {"fetch", "summarize"} and value.get("state") in {
        "paused", "interrupted", "cancelled", "failed", "partial",
    }
    return value


def resumable(conn) -> list[dict]:
    rows = conn.execute("""
        SELECT r.snapshot FROM processing_run r
        WHERE json_extract(r.snapshot,'$.params.mode') IN ('fetch','summarize')
          AND json_extract(r.snapshot,'$.state') IN ('paused','running','interrupted','cancelled','failed','partial')
          AND NOT EXISTS(SELECT 1 FROM processing_run n WHERE n.job_id=r.job_id AND n.rowid>r.rowid)
        ORDER BY r.rowid DESC LIMIT 50
    """)
    return [recovered(json.loads(row["snapshot"])) for row in rows]
