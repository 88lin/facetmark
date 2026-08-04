"""What does the unreachable decay layer actually cost?

``tests/test_decay_reach.py`` proves the shipped rescue valve can never close in
a one-facet config: reciprocal rank fusion tops out at ``1/(k+1) = 0.0164`` for
a single unit-weight facet, the valve opens below ``decay_rescue_threshold =
0.02``, and :data:`~facetmark.search.pipeline.FULL` -- the default profile
whenever a real API key is configured -- has exactly one facet. So the demotion
the layer exists to perform never happens.

That is a proof about arithmetic. It says nothing about consequences, and
"there is a dead layer in the default profile" is a different claim from "the
default profile ranks worse because of it". This measures the second one.

The measurement is a **deterministic A/B against the same retriever**: identical
library, identical queries, identical embeddings, identical fusion, with one
setting changed. ``decay_rescue_threshold=0.02`` is what ships; ``0.0`` makes
the valve unreachable in the other direction, so the demotion always applies.
Every difference between the two runs is caused by the decay layer and nothing
else, which is why no statistical machinery is needed to attribute it -- the
bootstrap interval below is about generalising from *this* query set to another
one, not about whether the difference is real.

Read the cold-layer census first. If the demotion has nothing to demote, or if
what it demotes is never in a candidate list, then a zero difference is a fact
about this library rather than a fact about the layer, and the write-up has to
say which.

Usage::

    python scripts/decay_reach_probe.py --db library.db \\
        --queries eval/queries/w2w3-holdout.jsonl --json decay-reach.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from facetmark.config import Settings  # noqa: E402
from facetmark.db import connect  # noqa: E402
from facetmark.eval.corpus import load_query_file  # noqa: E402
from facetmark.providers import get_provider  # noqa: E402
from facetmark.search.decay import cold_bookmark_ids  # noqa: E402
from facetmark.search.pipeline import ALL_CONFIGS, search  # noqa: E402

SHIPPED = 0.02   # what the default profile uses; the valve is always open
REACHABLE = 0.0  # valve can never open, so the demotion always applies


def _settings(args, threshold: float) -> Settings:
    return Settings(
        data_dir=Path(args.db).resolve().parent,
        db_name=Path(args.db).name,
        embed_backend="local",
        embed_model=args.embed_model,
        embed_dim=args.embed_dim,
        local_embed_path=args.embed_path,
        local_embed_max_seq=args.max_seq,
        local_embed_batch=args.batch,
        api_key="placeholder-no-chat-needed",
        request_timeout=120.0,
        decay_rescue_threshold=threshold,
    )


def _census(conn: sqlite3.Connection, targets: set[int], age_days: int, now_ts: int) -> dict:
    """Who is cold, and does the cold layer overlap the answers?

    Condition 3 -- positive evidence of supersession -- is what keeps this from
    being an age filter, and it is also why the cold layer is usually tiny. A
    small cold layer bounds the effect before a single query runs.
    """
    cold = cold_bookmark_ids(conn, age_days=age_days, now_ts=now_ts)
    total = conn.execute("SELECT count(*) AS n FROM bookmark").fetchone()["n"]
    old_unopened = conn.execute(
        "SELECT count(*) AS n FROM bookmark WHERE open_count = 0 AND date_added IS NOT NULL "
        "AND date_added < ?",
        (now_ts - age_days * 86400,),
    ).fetchone()["n"]
    return {
        "bookmarks": int(total),
        "old_and_never_opened": int(old_unopened),
        "cold": len(cold),
        "cold_ids": sorted(cold),
        "targets": len(targets),
        "cold_targets": sorted(cold & targets),
        "note": (
            "old_and_never_opened is conditions 1+2 only; `cold` adds condition 3 "
            "(a supersession edge or a dead health verdict). The gap between them "
            "is how much work condition 3 is doing."
        ),
    }


async def _run(conn, queries, st, provider, *, limit: int, now_ts: int) -> list[dict]:
    out = []
    for q in queries:
        t0 = time.perf_counter()
        resp = await search(
            conn, q.text, limit=limit, config=ALL_CONFIGS["full"],
            provider=provider, settings=st, now_ts=now_ts,
        )
        ids = [h.bookmark_id for h in resp.hits]
        out.append({
            "text": q.text,
            "qtype": q.qtype,
            "target": q.target_id,
            "hits": ids,
            "rank": ids.index(q.target_id) + 1 if q.target_id in ids else 0,
            "ms": round((time.perf_counter() - t0) * 1000, 1),
            # `rescued` is the valve. Under the shipped threshold it is True
            # whenever the candidate pool contained a cold page at all, which
            # makes it the cheapest available count of how often the demotion
            # had something to demote and declined.
            "rescued": bool(resp.rescued),
            "cold_in_list": sum(1 for h in resp.hits if h.cold),
        })
    return out


def _recall(rows: list[dict], at: int) -> float:
    return sum(1 for r in rows if 0 < r["rank"] <= at) / len(rows)


def _boot(a: list[dict], b: list[dict], at: int, *, n: int, seed: int) -> dict:
    """Percentile CI for the paired Recall@`at` difference, b minus a."""
    rng = random.Random(seed)
    pairs = [
        (1.0 if 0 < x["rank"] <= at else 0.0, 1.0 if 0 < y["rank"] <= at else 0.0)
        for x, y in zip(a, b, strict=True)
    ]
    m = len(pairs)
    diffs = []
    for _ in range(n):
        s = [pairs[rng.randrange(m)] for _ in range(m)]
        diffs.append((sum(y for _, y in s) - sum(x for x, _ in s)) / m)
    diffs.sort()
    return {
        "delta_pp": round((_recall(b, at) - _recall(a, at)) * 100, 4),
        "ci95_pp": [
            round(diffs[int(0.025 * n)] * 100, 4),
            round(diffs[int(0.975 * n)] * 100, 4),
        ],
        "boots": n,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", required=True)
    p.add_argument("--queries", required=True)
    p.add_argument("--json", required=True)
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--embed-path", default="/workspace/models/bge-m3")
    p.add_argument("--embed-model", default="bge-m3")
    p.add_argument("--embed-dim", type=int, default=1024)
    p.add_argument("--max-seq", type=int, default=1024)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--age-days", type=int, default=365)
    p.add_argument("--boots", type=int, default=10_000)
    p.add_argument("--seed", type=int, default=20260805)
    p.add_argument("--now", type=int, default=0, help="freeze the clock; 0 means now")
    args = p.parse_args()

    now_ts = args.now or int(time.time())
    st_a = _settings(args, SHIPPED)
    st_b = _settings(args, REACHABLE)
    conn = connect(Path(args.db))
    corpus = load_query_file(conn, args.queries)
    queries = corpus.queries
    targets = {q.target_id for q in queries}

    census = _census(conn, targets, args.age_days, now_ts)
    print(
        f"cold layer: {census['cold']} of {census['bookmarks']} bookmarks "
        f"({census['old_and_never_opened']} pass age+unopened alone); "
        f"{len(census['cold_targets'])} of {census['targets']} targets are cold"
    )

    provider = get_provider(st_a)

    async def both():
        a = await _run(conn, queries, st_a, provider, limit=args.limit, now_ts=now_ts)
        print(f"shipped   (threshold={SHIPPED}): Recall@5 {_recall(a, 5):.4f}")
        b = await _run(conn, queries, st_b, provider, limit=args.limit, now_ts=now_ts)
        print(f"reachable (threshold={REACHABLE}): Recall@5 {_recall(b, 5):.4f}")
        return a, b

    a, b = asyncio.run(both())

    # Deterministic differences. These need no interval: the two runs differ by
    # one setting, so any change is attributable by construction.
    top5_changed = sum(1 for x, y in zip(a, b, strict=True) if x["hits"][:5] != y["hits"][:5])
    list_changed = sum(1 for x, y in zip(a, b, strict=True) if x["hits"] != y["hits"])
    rank_moved = [
        {"q": x["text"], "qtype": x["qtype"], "from": x["rank"], "to": y["rank"]}
        for x, y in zip(a, b, strict=True) if x["rank"] != y["rank"]
    ]
    cold = set(census["cold_ids"])
    with_cold_in_list = sum(1 for x in a if cold & set(x["hits"]))
    with_cold_in_top5 = sum(1 for x in a if cold & set(x["hits"][:5]))
    rescued_shipped = sum(1 for x in a if x["rescued"])
    rescued_reachable = sum(1 for y in b if y["rescued"])

    report = {
        "clock": now_ts,
        "db": str(Path(args.db).resolve()),
        "queries": len(queries),
        "qtypes": dict(Counter(q.qtype for q in queries)),
        "census": census,
        "shipped": {
            "threshold": SHIPPED,
            "recall5": round(_recall(a, 5), 4),
            "recall1": round(_recall(a, 1), 4),
            "rescued_queries": rescued_shipped,
        },
        "reachable": {
            "threshold": REACHABLE,
            "recall5": round(_recall(b, 5), 4),
            "recall1": round(_recall(b, 1), 4),
            # Should be 0: with the valve unreachable the demotion always
            # applies. Anything else means a run where the hot layer scored
            # nothing at all, and the write-up has to explain it.
            "rescued_queries": rescued_reachable,
        },
        "exposure": {
            "queries_with_a_cold_page_in_the_list": with_cold_in_list,
            "queries_with_a_cold_page_in_top5": with_cold_in_top5,
        },
        "difference": {
            "queries_whose_top5_changed": top5_changed,
            "queries_whose_list_changed": list_changed,
            "queries_whose_target_rank_moved": len(rank_moved),
            "moves": rank_moved[:50],
        },
        "recall5": _boot(a, b, 5, n=args.boots, seed=args.seed),
        "recall1": _boot(a, b, 1, n=args.boots, seed=args.seed),
        "by_qtype": {
            t: {
                "n": sum(1 for x in a if x["qtype"] == t),
                "shipped_recall5": round(
                    _recall([x for x in a if x["qtype"] == t], 5), 4
                ),
                "reachable_recall5": round(
                    _recall([y for y in b if y["qtype"] == t], 5), 4
                ),
            }
            for t in sorted({q.qtype for q in queries})
        },
    }
    Path(args.json).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    d = report["recall5"]
    print(
        f"delta Recall@5 {d['delta_pp']:+.4f}pp CI95 "
        f"[{d['ci95_pp'][0]:+.4f}, {d['ci95_pp'][1]:+.4f}]; "
        f"{top5_changed} of {len(queries)} top-5 lists changed; "
        f"valve opened on {rescued_shipped} shipped / {rescued_reachable} reachable"
    )
    print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
