#!/usr/bin/env python3
"""Take Facet 3 apart: what is each of the two word indexes actually worth?

``facetmark.text`` justifies keeping two FTS5 tables with a measured table --
``trigram`` cannot match a sub-3-character query, ``unicode61`` cannot match
inside an unsegmented CJK run -- but that table used 2-4 character *lookups* as
ground truth on a calibration library. The two indexes have been fused as one
block ever since, and neither half has ever been scored against a real query.

Three rungs, none of which touches a vector, so all three run without a model:

    seg_only   lex_seg  (jieba + unicode61)
    tri_only   lex_tri  (trigram)
    lex_only   both, fused by RRF -- what the product actually ships inside B/C/D

This is exploratory, in the sense of ``docs/gate-w1.md`` §9: it uses the same
479 queries that produced the hypotheses, so it describes structure and does not
decide anything. It does not change a weight and does not remove a facet.

    python scripts/lex_facet_split.py --db library.db --eval eval_loo.json \
        --out eval/lex-facet-split.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import random
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

from facetmark.config import Settings
from facetmark.search.pipeline import EXPLORATORY, search
from facetmark.text import _FTS_STRIP_RE, _WS_RE, build_fts_query, has_cjk

RUNGS = ("seg_only", "tri_only", "lex_only")
#: Same constants as scripts/intent_strata.py, so the two reports are comparable.
BOOTSTRAP_N = 10000
BOOTSTRAP_SEED = 20260803


def hit(rank: int, k: int) -> bool:
    return 1 <= rank <= k


def paired(idx: list[int], a: dict[int, int], b: dict[int, int],
           rng: random.Random) -> dict:
    """Paired hit@5 comparison of rung ``b`` against rung ``a``.

    Exact two-sided McNemar on the discordant pairs (they are small here, which
    is where the chi-square approximation is known to be wrong) plus a paired
    percentile bootstrap, resampling query indices so the pairing survives.
    """
    diffs = [hit(b.get(i, 0), 5) - hit(a.get(i, 0), 5) for i in idx]
    gained = sum(1 for d in diffs if d > 0)
    lost = sum(1 for d in diffs if d < 0)
    disc = gained + lost
    k = min(gained, lost)
    p = (min(1.0, 2 * sum(math.comb(disc, i) for i in range(k + 1)) / (2**disc))
         if disc else 1.0)
    n = len(diffs)
    draws = sorted(
        sum(diffs[rng.randrange(n)] for _ in range(n)) / n * 100 for _ in range(BOOTSTRAP_N)
    ) if n else []
    return {
        "delta_pp": round(sum(diffs) / n * 100, 2) if n else 0.0,
        "ci95_pp": [round(draws[int(0.025 * BOOTSTRAP_N)], 2),
                    round(draws[int(0.975 * BOOTSTRAP_N)], 2)] if draws else [0.0, 0.0],
        "gained": gained, "lost": lost, "p": round(p, 5),
    }


async def rank_all(db: str, queries: list[dict], rung: str, settings: Settings,
                   limit: int) -> dict[int, int]:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    config = EXPLORATORY[rung]
    out: dict[int, int] = {}
    try:
        for i, q in enumerate(queries):
            resp = await search(conn, q["text"], limit=limit, config=config, settings=settings)
            ids = [h.bookmark_id for h in resp.hits]
            target = int(q["target_id"])
            out[i] = ids.index(target) + 1 if target in ids else 0
    finally:
        conn.close()
    return out


def trigram_coverage(db: str, queries: list[dict]) -> dict:
    """How often does each word index return anything at all, before and after.

    The pre-repair trigram expression is reconstructed here rather than
    described, so the defect stays reproducible from the repository after the
    code that caused it is gone: whitespace-split, quote each piece whole, drop
    pieces under three characters. For a Chinese sentence that is one quoted
    12-character phrase, and the index is being asked for the user's whole
    sentence verbatim.
    """
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    counts: Counter = Counter()
    try:
        for q in queries:
            scope = "cjk" if has_cjk(q["text"]) else "latin"
            counts[f"{scope}:n"] += 1
            now = build_fts_query(q["text"], segmented=False)
            before = " OR ".join(
                f'"{p}"' for p in dict.fromkeys(
                    x for x in _WS_RE.split(_FTS_STRIP_RE.sub(" ", q["text"]).strip())
                    if len(x) >= 3
                )
            )
            for label, expr in (("after", now), ("before", before)):
                if not expr:
                    continue
                rows = conn.execute(
                    "SELECT count(*) c FROM fts_tri WHERE fts_tri MATCH ?", (expr,)
                ).fetchone()["c"]
                if rows:
                    counts[f"{scope}:{label}"] += 1
    finally:
        conn.close()
    out = {}
    for scope in ("cjk", "latin"):
        n = counts[f"{scope}:n"]
        out[scope] = {
            "n": n,
            "lex_tri_non_empty_before_repair": counts[f"{scope}:before"],
            "lex_tri_non_empty_after_repair": counts[f"{scope}:after"],
            "share_before": round(counts[f"{scope}:before"] / n, 4) if n else 0.0,
            "share_after": round(counts[f"{scope}:after"] / n, 4) if n else 0.0,
        }
    return out


async def run(args) -> None:
    settings = Settings(db_path=args.db, use_mock_provider=True)
    rep = json.loads(Path(args.eval).read_text(encoding="utf-8"))
    queries = rep["queries"]

    ranks: dict[str, dict[int, int]] = {}
    for rung in RUNGS:
        print(f"running {rung} over {len(queries)} queries ...", flush=True)
        ranks[rung] = await rank_all(args.db, queries, rung, settings, args.limit)

    groups: dict[str, list[int]] = defaultdict(list)
    for i, q in enumerate(queries):
        groups["all"].append(i)
        groups[q["qtype"]].append(i)
        groups["cjk" if has_cjk(q["text"]) else "latin"].append(i)

    def recall(idx: list[int], rank: dict[int, int], k: int) -> float:
        return round(sum(hit(rank.get(i, 0), k) for i in idx) / len(idx), 4) if idx else 0.0

    out: dict = {
        "n_queries": len(queries),
        "rungs": {r: EXPLORATORY[r].as_dict() for r in RUNGS},
        "recall": {
            g: {"n": len(idx),
                **{f"{r}_r{k}": recall(idx, ranks[r], k) for r in RUNGS for k in (1, 5)}}
            for g, idx in sorted(groups.items())
        },
        "bootstrap": {"resamples": BOOTSTRAP_N, "seed": BOOTSTRAP_SEED},
        "trigram_coverage": trigram_coverage(args.db, queries),
        "deltas": {},
        "complement": {},
        "tri_unique": [],
    }

    # Does fusing the two indexes beat the better one on its own?
    rng = random.Random(BOOTSTRAP_SEED)
    for g, idx in sorted(groups.items()):
        out["deltas"][g] = {
            "seg_only->lex_only": paired(idx, ranks["seg_only"], ranks["lex_only"], rng),
            "tri_only->lex_only": paired(idx, ranks["tri_only"], ranks["lex_only"], rng),
        }

    # What does the trigram index find that the word index does not, and does
    # fusing the two keep it? Same four-way table as the lexical audit, one
    # level down.
    for g, idx in sorted(groups.items()):
        cell: Counter = Counter()
        kept = 0
        for i in idx:
            s, t = hit(ranks["seg_only"].get(i, 0), 5), hit(ranks["tri_only"].get(i, 0), 5)
            cell["both" if s and t else "seg_only" if s
                 else "tri_only" if t else "neither"] += 1
            if t and not s and hit(ranks["lex_only"].get(i, 0), 5):
                kept += 1
        out["complement"][g] = {
            "n": len(idx), **dict(cell),
            "tri_only_share": round(cell["tri_only"] / len(idx), 4) if idx else 0.0,
            # of the queries only trigram solves, how many survive the fusion
            "tri_only_kept_by_fusion": kept,
        }

    out["tri_unique"] = [
        {"qtype": queries[i]["qtype"], "text": queries[i]["text"],
         "tri_rank": ranks["tri_only"][i], "seg_rank": ranks["seg_only"][i],
         "fused_rank": ranks["lex_only"][i]}
        for i in groups["all"]
        if hit(ranks["tri_only"].get(i, 0), 5) and not hit(ranks["seg_only"].get(i, 0), 5)
    ][:20]

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"recall": out["recall"], "complement": out["complement"]},
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
