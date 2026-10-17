"""Durable, bounded bookmark-processing snapshots; never 200k task objects."""
from __future__ import annotations

import json

from .collection import CollectionScope, predicate


def target_query(*, scope: CollectionScope | None, ids, mode: str, force: bool, limit=None):
    where, params = predicate(scope or CollectionScope())
    parts = [where, "b.indexable=1", "b.privacy_skipped=0"]
    if ids is not None:
        parts.append("b.id IN(SELECT value FROM json_each(?))")
        params.append(json.dumps(list(ids)))
    if not force:
        if mode == "summarize":
            parts.append("(COALESCE(e.summary,'')='' OR e.source_hash IS NULL OR COALESCE(c.body_hash,fm_title_hash(b.title,b.url))!=e.source_hash "
                         "OR EXISTS(SELECT 1 FROM enrichment_failure ef WHERE ef.bookmark_id=b.id))")
        else:
            parts.append("c.body_hash IS NULL")
    sql = ("SELECT b.id FROM bookmark b LEFT JOIN content c ON c.bookmark_id=b.id "
           "LEFT JOIN enrichment e ON e.bookmark_id=b.id WHERE " + " AND ".join(f"({p})" for p in parts)
           + " ORDER BY b.id")
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    return sql, params


def preview(conn, **kwargs):
    sql, params = target_query(**kwargs)
    return conn.execute("SELECT count(*) FROM (" + sql + ")", params).fetchone()[0]


def snapshot(conn, job, planned_ids=None):
    existing = conn.execute("SELECT count(*) FROM processing_item WHERE job_id=?", (job.id,)).fetchone()[0]
    if not existing and not job.snapshot_ready:
        selected = planned_ids if planned_ids is not None else job.bookmark_ids
        # `planned_ids` is the resolved list from the job's first run. Without
        # it a resume of a job whose rows were cleaned up would re-expand the
        # scope and pick up bookmarks added after the original task started.
        if planned_ids is not None and job.bookmark_ids is None:
            conn.execute("INSERT INTO processing_item(job_id,bookmark_id) "
                         "SELECT ?, value FROM json_each(?) WHERE value IN (SELECT id FROM bookmark)",
                         (job.id, json.dumps(planned_ids)))
        else:
            scope = CollectionScope(**job.scope) if job.scope is not None else None
            sql, params = target_query(scope=scope, ids=selected, mode=job.mode,
                                       force=job.force, limit=job.limit)
            conn.execute("INSERT INTO processing_item(job_id,bookmark_id) SELECT ?,id FROM (" + sql + ")",
                         [job.id, *params])
        conn.commit()
    job.snapshot_ready = True
    update_counts(conn, job)


def update_counts(conn, job):
    row = conn.execute("SELECT count(*),sum(state!='pending'),sum(state='failed') "
                       "FROM processing_item WHERE job_id=?", (job.id,)).fetchone()
    job.items_total, job.items_done, job.items_failed = (int(value or 0) for value in row)


def pending_batch(conn, job, size=64):
    return [row[0] for row in conn.execute(
        "SELECT bookmark_id FROM processing_item WHERE job_id=? AND state='pending' "
        "ORDER BY bookmark_id LIMIT ?", (job.id, size))]


def finished(conn, job, bookmark_id, error=None):
    conn.execute("UPDATE processing_item SET state=?,error=? WHERE job_id=? AND bookmark_id=?",
                 ("failed" if error else "done", error, job.id, bookmark_id))
    if not conn.in_transaction:
        conn.commit()
    job.items_done += 1
    job.items_failed += int(bool(error))
