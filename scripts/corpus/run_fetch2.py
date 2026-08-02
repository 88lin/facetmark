"""Crawl the corpus once, driving by an explicit id list.

``pending_targets`` selects on ``content.body_hash IS NULL``, which means a row
that failed is offered again on the next call. That is right for ``facetmark
index`` -- a transient 429 should be retried tomorrow -- but it makes a
"loop until nothing is pending" driver never terminate: each batch refills with
the same dead links and starves the URLs nobody has tried yet.

So the sweep is planned up front: take the ids that have no content row at all,
walk them in batches, then make exactly one retry pass over the subset whose
failure looks transient. Anything still failing is a fact about the web, not
about the crawler, and gets reported rather than retried.
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
import time
from collections import Counter

from facetmark.config import get_settings
from facetmark.db import open_db
from facetmark.fetch import crawl

BATCH = int(sys.argv[1]) if len(sys.argv) > 1 else 200

#: Substrings of ``content.error`` worth one more attempt. Everything else --
#: 403, 404, paywall, robots, client-side rendering -- will not change.
TRANSIENT = ("timeout", "Server disconnected", "HTTP 429", "HTTP 5",
             "Temporary failure in name resolution", "unreachable")


def untried(db: str) -> list[int]:
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = c.execute(
        "SELECT b.id FROM bookmark b LEFT JOIN content c ON c.bookmark_id = b.id "
        "WHERE b.indexable = 1 AND b.privacy_skipped = 0 AND c.bookmark_id IS NULL "
        "ORDER BY b.id"
    ).fetchall()
    c.close()
    return [r[0] for r in rows]


def transient_failures(db: str) -> list[int]:
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = c.execute(
        "SELECT bookmark_id, coalesce(error,'') FROM content WHERE body_hash IS NULL"
    ).fetchall()
    c.close()
    return [i for i, e in rows if any(t in e for t in TRANSIENT)]


async def sweep(st, db: str, ids: list[int], label: str) -> dict:
    totals: Counter[str] = Counter()
    stored = attempted = 0
    t0 = time.monotonic()
    for k in range(0, len(ids), BATCH):
        chunk = ids[k:k + BATCH]
        conn = open_db(db)
        try:
            rep = await crawl(conn, settings=st, ids=chunk, refetch=(label == "retry"))
        finally:
            conn.commit()
            conn.close()
        d = rep.as_dict() if hasattr(rep, "as_dict") else dict(rep.__dict__)
        attempted += int(d.get("attempted") or 0)
        stored += int(d.get("stored") or 0)
        totals.update(d.get("by_verdict") or {})
        el = time.monotonic() - t0
        print(f"[{label} {k // BATCH + 1:>3}] attempted={attempted:>5} stored={stored:>5} "
              f"{el / 60:6.1f}min {attempted / max(el, 1):5.2f}url/s "
              f"eta={((len(ids) - attempted) / max(attempted / max(el, 1), 1e-9)) / 60:5.1f}min "
              f"{json.dumps(dict(totals.most_common(8)))}", flush=True)
    return {"label": label, "planned": len(ids), "attempted": attempted, "stored": stored,
            "minutes": round((time.monotonic() - t0) / 60, 1),
            "by_verdict": dict(totals.most_common())}


async def main() -> None:
    st = get_settings()
    db = st.db_path
    out = []

    ids = untried(db)
    print(f"plan: {len(ids)} never-tried bookmarks, batch={BATCH}", flush=True)
    if ids:
        out.append(await sweep(st, db, ids, "fresh"))

    retry = transient_failures(db)
    print(f"\nplan: {len(retry)} transient failures worth one retry", flush=True)
    if retry:
        out.append(await sweep(st, db, retry, "retry"))

    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    final = {
        "bookmarks": c.execute("SELECT count(*) FROM bookmark").fetchone()[0],
        "with_body": c.execute(
            "SELECT count(*) FROM content WHERE body_hash IS NOT NULL").fetchone()[0],
        "failed": c.execute(
            "SELECT count(*) FROM content WHERE body_hash IS NULL").fetchone()[0],
        "queued_for_browser": c.execute("SELECT count(*) FROM fetch_queue").fetchone()[0],
        "errors": dict(c.execute(
            "SELECT coalesce(error,'?'), count(*) FROM content WHERE body_hash IS NULL "
            "GROUP BY 1 ORDER BY 2 DESC LIMIT 25").fetchall()),
    }
    c.close()
    final["survival"] = round(final["with_body"] / max(final["bookmarks"], 1), 4)
    print("\nFETCH_DONE " + json.dumps({"sweeps": out, "final": final},
                                       ensure_ascii=False), flush=True)


asyncio.run(main())
