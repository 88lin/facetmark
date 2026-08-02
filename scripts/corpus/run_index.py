"""Full index of the evaluation library against the real models, resumably.

Runs the stages in the only order that works -- enrich -> embed_content ->
filter_intents -> embed_intents -> sessions -> edges -- but enrich is chunked
so a crash, a timeout or a lost session costs at most one chunk. Enrichment is
idempotent on ``enrichment.source_hash``, so re-running this script picks up
exactly where it stopped without re-billing anything already done.

Snapshots the DB to the shared volume every ``--snap`` chunks, because the
local disk does not survive a machine lifecycle event and six hours of model
time is not something to redo.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import subprocess
import time
from pathlib import Path

from facetmark.config import get_settings
from facetmark.db import open_db

SNAP_DIR = Path("/mnt/shared-workspace/shared/facetmark_w1")


def pending_enrich(db: str) -> int:
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    n = c.execute(
        "SELECT count(*) FROM bookmark b LEFT JOIN enrichment e ON e.bookmark_id = b.id "
        "WHERE b.indexable = 1 AND e.bookmark_id IS NULL"
    ).fetchone()[0]
    c.close()
    return int(n)


def snapshot(db: str, tag: str) -> None:
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    local = Path("/workspace") / f"snap_{tag}.db"
    conn = open_db(db)
    conn.execute("VACUUM INTO ?", (str(local),))
    conn.close()
    # cp, not shutil, because the shared volume is S3-backed FUSE
    subprocess.run(["cp", str(local), str(SNAP_DIR / "library.db")], check=True)
    size = (SNAP_DIR / "library.db").stat().st_size
    local.unlink(missing_ok=True)
    print(f"    snapshot -> library.db ({size:,} B)", flush=True)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk", type=int, default=200)
    ap.add_argument("--snap", type=int, default=3, help="snapshot every N chunks")
    ap.add_argument("--stages", default="enrich,embed,intents,sessions,edges")
    args = ap.parse_args()
    stages = set(args.stages.split(","))

    st = get_settings()
    db = st.db_path
    t_all = time.monotonic()
    log: list[dict] = []

    if "enrich" in stages:
        from facetmark.enrich import enrich_all

        total0 = pending_enrich(db)
        print(f"enrich: {total0} pending, chunk={args.chunk}, "
              f"concurrency={st.enrich_concurrency}", flush=True)
        rnd = 0
        done = 0
        t0 = time.monotonic()
        while True:
            rnd += 1
            conn = open_db(db)
            try:
                rep = await enrich_all(conn, settings=st, limit=args.chunk)
            finally:
                conn.close()
            d = rep.as_dict()
            n = int(d["enriched"]) + int(d["failed"])
            if n == 0:
                break
            done += int(d["enriched"])
            el = time.monotonic() - t0
            left = max(total0 - done, 0)
            eta = left / max(done / max(el, 1e-9), 1e-9) / 60
            print(f"[enrich {rnd:>3}] +{d['enriched']:>3} fail={d['failed']:>3} "
                  f"done={done:>5}/{total0} {el / 60:6.1f}min "
                  f"{3600 * done / max(el, 1e-9):6.0f}/h eta={eta:6.1f}min "
                  f"q={d['queries_generated']}", flush=True)
            if d["errors"]:
                print(f"    errors: {d['errors'][:3]}", flush=True)
            if rnd % args.snap == 0:
                snapshot(db, "enrich")
        log.append({"stage": "enrich", "done": done,
                    "minutes": round((time.monotonic() - t0) / 60, 1)})
        snapshot(db, "enrich")

    from facetmark.edges import build_edges
    from facetmark.enrich import embed_content, embed_intents, filter_intents
    from facetmark.sessions import build_sessions

    def show(rep) -> dict:
        if hasattr(rep, "as_dict"):
            return rep.as_dict()
        if hasattr(rep, "__dict__"):
            return dict(rep.__dict__)
        return {k: getattr(rep, k) for k in getattr(rep, "__slots__", ())}

    async def stage(name: str, fn) -> None:
        t0 = time.monotonic()
        conn = open_db(db)
        try:
            rep = await fn(conn)
        finally:
            conn.commit()
            conn.close()
        d = show(rep)
        el = time.monotonic() - t0
        print(f"[{name}] {json.dumps(d, ensure_ascii=False, default=str)[:500]} "
              f"{el:.1f}s", flush=True)
        log.append({"stage": name, "report": d, "minutes": round(el / 60, 1)})

    def sync_stage(name: str, fn) -> None:
        t0 = time.monotonic()
        conn = open_db(db)
        try:
            rep = fn(conn)
        finally:
            conn.commit()
            conn.close()
        d = show(rep)
        el = time.monotonic() - t0
        print(f"[{name}] {json.dumps(d, ensure_ascii=False, default=str)[:500]} "
              f"{el:.1f}s", flush=True)
        log.append({"stage": name, "report": d, "minutes": round(el / 60, 1)})

    if "embed" in stages:
        await stage("embed_content", lambda c: embed_content(c, settings=st))
        snapshot(db, "embed")
    if "intents" in stages:
        await stage("filter_intents", lambda c: filter_intents(c, settings=st))
        await stage("embed_intents", lambda c: embed_intents(c, settings=st))
        snapshot(db, "intents")
    if "sessions" in stages:
        sync_stage("sessions", build_sessions)
    if "edges" in stages:
        sync_stage("edges", build_edges)
        snapshot(db, "final")

    print("\nINDEX_DONE " + json.dumps(
        {"minutes": round((time.monotonic() - t_all) / 60, 1), "log": log},
        ensure_ascii=False), flush=True)
    Path("/workspace/corpus/index_log.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")


asyncio.run(main())
