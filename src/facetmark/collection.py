"""One server-side collection scope for browsing and bulk target snapshots."""
from __future__ import annotations

import json
import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .search.querylang import _field_sql, parse_query
from .text import build_fts_query


class CollectionScope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    folder: str | None = None
    tag: str | None = None
    domain: str | None = None
    session: int | None = None
    q: str = Field(default="", max_length=4096)
    status: Literal["all", "pending", "done", "failed"] = "all"
    exclude_ids: list[int] = Field(default_factory=list, max_length=10000)


def predicate(scope: CollectionScope, *, include_status: bool = True) -> tuple[str, list]:
    clauses, params = [], []
    for field in ("folder", "domain"):
        value = getattr(scope, field)
        if value is not None:
            clauses.append(f"b.{field}=?")
            params.append(value)
    if scope.tag is not None:
        clauses.append("EXISTS(SELECT 1 FROM json_each(b.tags) WHERE value=?)")
        params.append(scope.tag)
    if scope.session is not None:
        clauses.append("EXISTS(SELECT 1 FROM bookmark_session bs WHERE bs.bookmark_id=b.id AND bs.session_id=?)")
        params.append(scope.session)
    parsed = parse_query(scope.q)
    if parsed.ignored:
        raise ValueError("Invalid query filters: " + ", ".join(parsed.ignored))
    for field in parsed.filters:
        part = _field_sql(field, now=time.time())
        if part is None:
            raise ValueError("Unsupported collection filter")
        sql, values = part
        clauses.append(f"{'NOT ' if field.negate else ''}(COALESCE(({sql}),0))")
        params.extend(values)
    if parsed.text:
        selects = []
        for table, segmented in (("fts_seg", True), ("fts_tri", False)):
            match = build_fts_query(parsed.text, segmented=segmented)
            if match:
                selects.append(f"SELECT rowid FROM {table} WHERE {table} MATCH ?")
                params.append(match)
        clauses.append("b.id IN (" + " UNION ".join(selects) + ")" if selects else "0")
    for term in parsed.terms:
        if not term.negated:
            continue
        match = build_fts_query(term.raw, segmented=True)
        if match:
            clauses.append("b.id NOT IN(SELECT rowid FROM fts_seg WHERE fts_seg MATCH ?)")
            params.append(match)
    if include_status:
        done = "EXISTS(SELECT 1 FROM enrichment e WHERE e.bookmark_id=b.id AND COALESCE(e.summary,'')!='')"
        failed = "EXISTS(SELECT 1 FROM enrichment_failure ef WHERE ef.bookmark_id=b.id)"
        if scope.status == "done":
            clauses += [done, f"NOT {failed}"]
        elif scope.status == "failed":
            clauses.append(failed)
        elif scope.status == "pending":
            clauses += [f"NOT {done}", f"NOT {failed}"]
    if scope.exclude_ids:
        # A bounded exception list, never the entire 200k-record selection.
        clauses.append("b.id NOT IN(SELECT value FROM json_each(?))")
        params.append(json.dumps(scope.exclude_ids))
    return " AND ".join(clauses) or "1", params


def matching_ids(conn, scope: CollectionScope):
    where, params = predicate(scope)
    for row in conn.execute("SELECT b.id FROM bookmark b WHERE " + where + " ORDER BY b.id", params):
        yield row[0]
