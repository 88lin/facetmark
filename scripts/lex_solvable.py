"""How much of the query set is solvable by word matching alone?

Protocol, written before any of this was run: ``docs/query-set-lexical-audit.md``.

Runs the shipped ``lex_only`` rung -- ``lex_seg`` + ``lex_tri``, no vectors, no
context, no graph, no rerank -- over the same 479 queries and the same library
snapshot as ``eval_loo.json``, then crosses the result against the A rung's
per-query ranks taken from that file.

No embedding model is needed: ``pipeline.search()`` guards the whole vector
branch behind ``config.facets & VECTOR_FACETS``, and this config has neither.

    python scripts/lex_solvable.py --db /workspace/w1/library-w1-indexed.db \
        --eval /workspace/w1/eval_loo.json --out /workspace/w1/lex_solvable.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

from facetmark.config import Settings
from facetmark.search.pipeline import EXPLORATORY, search

#: Pre-registered in the protocol, restated here so a reader of the numbers does
#: not have to trust that they were fixed in advance.
THRESHOLDS = {
    "q_content_r5_substantially_lexical": 0.60,
    "q_vague_r5_gate_failed": 0.30,
    "lex_only_wins_share_worth_fixing_fusion": 0.05,
}


def load_eval(path: str) -> tuple[list[dict], dict[str, dict[int, int]]]:
    """Queries plus ``{rung: {query index: rank}}`` from an eval report.

    ``outcomes`` is a per-rung list positionally aligned with ``queries``; the
    harness writes it that way and ``intent_strata.py`` reads it the same way.
    A length mismatch would silently shift every rank onto the wrong query, so
    it is an error rather than a zip.
    """
    rep = json.loads(Path(path).read_text(encoding="utf-8"))
    queries = rep["queries"]
    ranks: dict[str, dict[int, int]] = {}
    for name, rows in rep["outcomes"].items():
        if len(rows) != len(queries):
            raise SystemExit(f"{path}: rung {name} has {len(rows)} outcomes "
                             f"for {len(queries)} queries")
        ranks[name] = {i: int(r.get("rank") or 0) for i, r in enumerate(rows)}
    return queries, ranks


def hit(rank: int, k: int) -> bool:
    """Ranks are 1-based in the reports; 0 means the target never appeared."""
    return 1 <= rank <= k


async def run(args) -> None:
    settings = Settings(db_path=args.db, use_mock_provider=True)
    queries, ranks = load_eval(args.eval)
    if "A" not in ranks:
        raise SystemExit(f"{args.eval}: no A rung to compare against")
    print(f"{len(queries)} queries; rungs in eval file: {sorted(ranks)}", flush=True)

    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    config = EXPLORATORY["lex_only"]
    lex_rank: dict[int, int] = {}
    for i, q in enumerate(queries):
        resp = await search(conn, q["text"], limit=args.limit, config=config,
                           settings=settings)
        ids = [h.bookmark_id for h in resp.hits]
        target = int(q["target_id"])
        lex_rank[i] = ids.index(target) + 1 if target in ids else 0
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(queries)}", flush=True)
    conn.close()

    by_type: dict[str, list[int]] = defaultdict(list)
    for i, q in enumerate(queries):
        by_type[q["qtype"]].append(i)

    def recall(idx: list[int], rank: dict[int, int], k: int) -> float:
        return sum(hit(rank.get(i, 0), k) for i in idx) / len(idx) if idx else 0.0

    out: dict = {
        "thresholds": THRESHOLDS,
        "config": config.as_dict(),
        "n_queries": len(queries),
        "overall": {
            "lex_only": {"r1": recall(list(lex_rank), lex_rank, 1),
                         "r5": recall(list(lex_rank), lex_rank, 5)},
            "A": {"r1": recall(list(lex_rank), ranks["A"], 1),
                  "r5": recall(list(lex_rank), ranks["A"], 5)},
        },
        "by_type": {},
        "complement": {},
    }
    for qtype, idx in sorted(by_type.items()):
        out["by_type"][qtype] = {
            "n": len(idx),
            "lex_only_r1": recall(idx, lex_rank, 1),
            "lex_only_r5": recall(idx, lex_rank, 5),
            "A_r1": recall(idx, ranks["A"], 1),
            "A_r5": recall(idx, ranks["A"], 5),
        }

    # The four-way table the protocol pre-registered. "lex only" is the money
    # fusion should have made; A->B says it lost money instead.
    for scope, idx in [("all", list(lex_rank)), *sorted(by_type.items())]:
        cell: Counter = Counter()
        for i in idx:
            lx, a = hit(lex_rank.get(i, 0), 5), hit(ranks["A"].get(i, 0), 5)
            cell["both" if lx and a else "lex_only" if lx
                 else "vector_only" if a else "neither"] += 1
        out["complement"][scope] = {
            "n": len(idx), **dict(cell),
            "lex_only_share": round(cell["lex_only"] / len(idx), 4) if idx else 0.0,
        }

    # Queries only the lexical facets solve, for reading rather than counting.
    out["examples_lex_only"] = [
        {"i": i, "qtype": queries[i]["qtype"], "text": queries[i]["text"],
         "lex_rank": lex_rank[i]}
        for i in sorted(lex_rank)
        if hit(lex_rank[i], 5) and not hit(ranks["A"].get(i, 0), 5)
    ][:20]

    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("overall", "by_type", "complement")},
                     ensure_ascii=False, indent=2), flush=True)
    print(f"\nwrote {args.out}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--eval", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=20)
    asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    main()
