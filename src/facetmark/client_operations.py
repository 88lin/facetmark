"""Atomic receipts for extension saves and browser text deliveries."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from .db import now


class ClientOperationConflict(ValueError):
    pass


def fingerprint(action: str, values: dict) -> str:
    raw = json.dumps([action, values], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def receipt(conn: sqlite3.Connection, request_id: str | None, *, digest: str | None = None) -> dict | None:
    if request_id is None:
        return None
    row = conn.execute("SELECT action,fingerprint,result FROM client_operation WHERE request_id=?", (request_id,)).fetchone()
    if row is None:
        return None
    if digest is not None and row["fingerprint"] != digest:
        raise ClientOperationConflict("This request ID belongs to a different browser operation")
    return {"request_id": request_id, "action": row["action"], "result": json.loads(row["result"])}


def accept(conn: sqlite3.Connection, request_id: str | None, *, action: str, digest: str, result: dict) -> None:
    if request_id is not None:
        conn.execute("INSERT INTO client_operation(request_id,action,fingerprint,result,created_at) VALUES(?,?,?,?,?)",
                     (request_id, action, digest, json.dumps(result, ensure_ascii=False), now()))


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[None]:
    conn.execute("SAVEPOINT client_delivery")
    try:
        yield
    except BaseException:
        conn.execute("ROLLBACK TO client_delivery")
        conn.execute("RELEASE client_delivery")
        raise
    else:
        conn.execute("RELEASE client_delivery")
