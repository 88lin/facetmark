"""Round-trip fidelity: does a library backfilled through the karakeep bridge
rank the same as one facetmark built itself?

Protocol frozen before any retrieval ran: ``docs/karakeep-roundtrip-protocol.md``.
Report appended afterwards to ``docs/karakeep-roundtrip.md``.

Four phases, each resumable, because the push phase embeds 2,376 documents on a
CPU and that is the better part of an hour:

    python scripts/karakeep_roundtrip.py build   --src ... --out ...
    python scripts/karakeep_roundtrip.py push    --docs ... --db ...
    python scripts/karakeep_roundtrip.py query   --src ... --db ... --queries ...
    python scripts/karakeep_roundtrip.py verdict --runs ... --out ...

The push phase talks to a running ``facetmark serve`` over real HTTP rather than
calling the bridge in-process, so the route layer, the auth dependency and the
service lock are all in the path.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import statistics
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from facetmark.config import get_settings  # noqa: E402
from facetmark.db import connect  # noqa: E402
from facetmark.providers import get_provider  # noqa: E402
from facetmark.search.pipeline import ALL_CONFIGS, search  # noqa: E402

#: Frozen in the protocol so decay and any time window resolve identically to
#: ``docs/gate-w2w3.md``.
CLOCK = 1785649110
BOOTSTRAP_N = 10000
BOOTSTRAP_SEED = 20260803
USER_ID = "roundtrip"


# ---------------------------------------------------------------------------
# phase 1: build karakeep documents from a facetmark library
# ---------------------------------------------------------------------------


def phase_build(args: argparse.Namespace) -> None:
    conn = connect(Path(args.src))
    rows = conn.execute(
        """
        SELECT b.id, b.url, b.title, b.folder, b.date_added,
               COALESCE(c.body_text, '') AS body,
               COALESCE(e.summary, '')   AS summary,
               COALESCE(e.topics, '')    AS topics
        FROM bookmark b
        LEFT JOIN content c    ON c.bookmark_id = b.id
        LEFT JOIN enrichment e ON e.bookmark_id = b.id
        ORDER BY b.id
        """
    ).fetchall()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    n_body = 0
    with out.open("w", encoding="utf-8") as fh:
        for r in rows:
            body = r["body"] or ""
            n_body += int(bool(body.strip()))
            tags = [t for t in (r["folder"] or "").split("/") if t.strip()]
            ts = int(r["date_added"] or 0)
            doc = {
                "id": f"w1-{int(r['id'])}",
                "userId": USER_ID,
                "url": r["url"],
                "title": r["title"] or "",
                "linkTitle": "",
                # Left empty on purpose: the bridge concatenates
                # description + note + content, so empty ones make the stored
                # body byte-identical to the source. See protocol section 4.
                "description": "",
                "note": "",
                "content": body,
                "summary": r["summary"] or "",
                "tags": tags,
                "createdAt": datetime.fromtimestamp(ts, UTC).isoformat().replace("+00:00", "Z"),
            }
            fh.write(json.dumps(doc, ensure_ascii=False) + "\n")
    print(json.dumps({
        "phase": "build", "documents": len(rows), "with_body": n_body,
        "out": str(out),
    }, ensure_ascii=False))


# ---------------------------------------------------------------------------
# phase 2: push them through POST /karakeep/documents over real HTTP
# ---------------------------------------------------------------------------


def phase_push(args: argparse.Namespace) -> None:
    docs = [json.loads(ln) for ln in Path(args.docs).read_text(encoding="utf-8").splitlines() if ln.strip()]
    token = Path(args.token).read_text(encoding="utf-8").strip()
    headers = {"Authorization": f"Bearer {token}"}
    base = args.url.rstrip("/")

    totals: Counter[str] = Counter()
    t_start = time.time()
    with httpx.Client(timeout=args.timeout) as cl:
        for i in range(0, len(docs), args.batch):
            batch = docs[i:i + args.batch]
            t0 = time.time()
            rp = cl.post(f"{base}/karakeep/documents",
                         json={"documents": batch, "embed": not args.no_embed},
                         headers=headers)
            rp.raise_for_status()
            body = rp.json()
            for k, v in body.items():
                if isinstance(v, int):
                    totals[k] += v
            if body.get("embed_error"):
                print(f"  embed_error: {body['embed_error']}", flush=True)
            dt = time.time() - t0
            done = i + len(batch)
            rate = done / max(time.time() - t_start, 1e-9)
            eta = (len(docs) - done) / max(rate, 1e-9)
            print(f"  {done}/{len(docs)}  {dt:.1f}s  {rate:.2f} doc/s  eta {eta/60:.1f} min",
                  flush=True)
        stats = cl.get(f"{base}/karakeep/stats", headers=headers).json()

    print(json.dumps({
        "phase": "push", "elapsed_s": round(time.time() - t_start, 1),
        "totals": dict(totals), "stats": stats,
    }, ensure_ascii=False))


# ---------------------------------------------------------------------------
# phase 3: run the query set three ways
# ---------------------------------------------------------------------------


def _load_queries(path: Path) -> list[dict]:
    out = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("//"):
            continue
        out.append(json.loads(ln))
    return out


async def _native(conn, provider, settings, queries: list[dict], cfg: str,
                  *, now_ts: int | None, limit: int) -> list[list[str]]:
    """URLs of the top ``limit`` hits, one list per query."""
    out = []
    for i, q in enumerate(queries):
        resp = await search(conn, q["text"], limit=limit, config=ALL_CONFIGS[cfg],
                            provider=provider, settings=settings, now_ts=now_ts)
        out.append([h.url for h in resp.hits[:limit]])
        if (i + 1) % 100 == 0:
            print(f"  native/{cfg} {i+1}/{len(queries)}", flush=True)
    return out


def phase_query(args: argparse.Namespace) -> None:
    settings = get_settings()
    provider = get_provider(settings)
    queries = _load_queries(Path(args.queries))
    configs = [c.strip() for c in args.configs.split(",") if c.strip()]
    limit = args.limit

    src = connect(Path(args.src))
    brg = connect(Path(args.db))

    # karakeep_id -> url on the bridged side, so HTTP hits can be compared by URL
    kid2url = {
        r["karakeep_id"]: r["url"]
        for r in brg.execute(
            "SELECT k.karakeep_id, b.url FROM karakeep_doc k"
            " JOIN bookmark b ON b.id = k.bookmark_id"
        )
    }

    runs: dict[str, dict] = {"clock": CLOCK, "n_queries": len(queries), "configs": configs,
                             "limit": limit, "runs": {}}

    token = Path(args.token).read_text(encoding="utf-8").strip()
    headers = {"Authorization": f"Bearer {token}"}
    base = args.url.rstrip("/")

    for cfg in configs:
        print(f"[{cfg}] source library, native, clock={CLOCK}", flush=True)
        a = asyncio.run(_native(src, provider, settings, queries, cfg, now_ts=CLOCK, limit=limit))
        print(f"[{cfg}] bridged library, native, clock={CLOCK}", flush=True)
        b = asyncio.run(_native(brg, provider, settings, queries, cfg, now_ts=CLOCK, limit=limit))
        # read path: the route uses the real clock, so the native side it is
        # compared against must too.
        print(f"[{cfg}] bridged library, native, real clock", flush=True)
        b_now = asyncio.run(_native(brg, provider, settings, queries, cfg, now_ts=None, limit=limit))
        print(f"[{cfg}] bridged library, POST /karakeep/search", flush=True)
        http: list[list[str]] = []
        with httpx.Client(timeout=args.timeout) as cl:
            for i, q in enumerate(queries):
                rp = cl.post(f"{base}/karakeep/search",
                             json={"query": q["text"], "limit": limit, "config": cfg},
                             headers=headers)
                rp.raise_for_status()
                http.append([kid2url.get(h["id"], "") for h in rp.json()["hits"]])
                if (i + 1) % 100 == 0:
                    print(f"  http/{cfg} {i+1}/{len(queries)}", flush=True)
        runs["runs"][cfg] = {"source": a, "bridged": b, "bridged_now": b_now, "http": http}

    runs["queries"] = [{"text": q["text"], "qtype": q.get("qtype", ""),
                        "target_url": q["target_url"]} for q in queries]
    Path(args.out).write_text(json.dumps(runs, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"phase": "query", "out": args.out, "configs": configs}, ensure_ascii=False))


# ---------------------------------------------------------------------------
# phase 4: verdict
# ---------------------------------------------------------------------------


def _mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact binomial test on the discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    from math import comb
    k = min(b, c)
    tail = sum(comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def _boot_ci(pairs: list[tuple[int, int]], n: int, seed: int) -> tuple[float, float]:
    rng = random.Random(seed)
    m = len(pairs)
    if m == 0:
        return (0.0, 0.0)
    deltas = []
    idx = range(m)
    for _ in range(n):
        s = [pairs[rng.choice(idx)] for _ in idx]
        deltas.append(sum(y - x for x, y in s) / m * 100.0)
    deltas.sort()
    return (deltas[int(0.025 * n)], deltas[int(0.975 * n)])


def phase_verdict(args: argparse.Namespace) -> None:
    data = json.loads(Path(args.runs).read_text(encoding="utf-8"))
    queries = data["queries"]
    out: dict = {"clock": data["clock"], "n_queries": data["n_queries"],
                 "bootstrap_n": BOOTSTRAP_N, "bootstrap_seed": BOOTSTRAP_SEED,
                 "configs": {}}

    for cfg, run in data["runs"].items():
        src, brg, brg_now, http = run["source"], run["bridged"], run["bridged_now"], run["http"]
        pairs5, pairs1 = [], []
        overlaps, top1_same = [], 0
        by_type: dict[str, list[tuple[int, int]]] = {}
        for q, a, b in zip(queries, src, brg, strict=True):
            t = q["target_url"]
            h5a, h5b = int(t in a[:5]), int(t in b[:5])
            pairs5.append((h5a, h5b))
            pairs1.append((int(bool(a[:1]) and a[0] == t), int(bool(b[:1]) and b[0] == t)))
            overlaps.append(len(set(a[:5]) & set(b[:5])))
            top1_same += int(bool(a) and bool(b) and a[0] == b[0])
            by_type.setdefault(q["qtype"], []).append((h5a, h5b))

        n = len(pairs5)
        r5a = sum(x for x, _ in pairs5) / n
        r5b = sum(y for _, y in pairs5) / n
        r1a = sum(x for x, _ in pairs1) / n
        r1b = sum(y for _, y in pairs1) / n
        won = sum(1 for x, y in pairs5 if y > x)
        lost = sum(1 for x, y in pairs5 if y < x)
        lo, hi = _boot_ci(pairs5, BOOTSTRAP_N, BOOTSTRAP_SEED)

        # read path: exact list equality, http vs native-with-real-clock
        mismatch, tie_reorder = 0, 0
        for a, b in zip(brg_now, http, strict=True):
            if a[:5] == b[:5]:
                continue
            if set(a[:5]) == set(b[:5]):
                tie_reorder += 1
            else:
                mismatch += 1

        strata = {}
        for t, ps in sorted(by_type.items()):
            m = len(ps)
            strata[t] = {
                "n": m,
                "source_r5": round(sum(x for x, _ in ps) / m, 4),
                "bridged_r5": round(sum(y for _, y in ps) / m, 4),
                "delta_pp": round((sum(y - x for x, y in ps) / m) * 100, 2),
            }

        out["configs"][cfg] = {
            "source_recall5": round(r5a, 4), "bridged_recall5": round(r5b, 4),
            "delta_recall5_pp": round((r5b - r5a) * 100, 2),
            "ci95_pp": [round(lo, 2), round(hi, 2)],
            "won": won, "lost": lost, "discordant": won + lost,
            "mcnemar_p": round(_mcnemar_exact(lost, won), 6),
            "source_recall1": round(r1a, 4), "bridged_recall1": round(r1b, 4),
            "overlap5_median": statistics.median(overlaps),
            "overlap5_mean": round(statistics.mean(overlaps), 3),
            "overlap5_hist": dict(sorted(Counter(overlaps).items())),
            "top1_same": round(top1_same / n, 4),
            "http_vs_native_mismatch": mismatch,
            "http_vs_native_tie_reorder": tie_reorder,
            "strata": strata,
        }

    # pre-registered rules, applied only to the rungs they were written for
    a_cfg = out["configs"].get("A")
    checks = {}
    if a_cfg:
        d = abs(a_cfg["delta_recall5_pp"])
        lo, hi = a_cfg["ci95_pp"]
        checks["a_metric_fidelity"] = bool(d <= 3.00 and lo >= -5.0 and hi <= 5.0)
        checks["b_list_fidelity"] = bool(
            a_cfg["overlap5_median"] >= 4 and a_cfg["top1_same"] >= 0.80
        )
    checks["c_read_path_identical"] = all(
        c["http_vs_native_mismatch"] == 0 for c in out["configs"].values()
    )
    out["checks"] = checks
    out["verdict"] = "roundtrip_faithful" if all(checks.values()) else "roundtrip_unfaithful"

    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build")
    b.add_argument("--src", required=True)
    b.add_argument("--out", required=True)
    b.set_defaults(fn=phase_build)

    u = sub.add_parser("push")
    u.add_argument("--docs", required=True)
    u.add_argument("--token", required=True)
    u.add_argument("--url", default="http://127.0.0.1:8787")
    u.add_argument("--batch", type=int, default=32)
    u.add_argument("--timeout", type=float, default=1800.0)
    u.add_argument("--no-embed", action="store_true")
    u.set_defaults(fn=phase_push)

    q = sub.add_parser("query")
    q.add_argument("--src", required=True)
    q.add_argument("--db", required=True)
    q.add_argument("--queries", required=True)
    q.add_argument("--token", required=True)
    q.add_argument("--url", default="http://127.0.0.1:8787")
    q.add_argument("--configs", default="A,full")
    q.add_argument("--limit", type=int, default=10)
    q.add_argument("--timeout", type=float, default=600.0)
    q.add_argument("--out", required=True)
    q.set_defaults(fn=phase_query)

    v = sub.add_parser("verdict")
    v.add_argument("--runs", required=True)
    v.add_argument("--out", required=True)
    v.set_defaults(fn=phase_verdict)

    args = p.parse_args(argv)
    args.fn(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
