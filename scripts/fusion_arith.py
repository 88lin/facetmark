#!/usr/bin/env python3
"""Audit the fusion operator itself: what RRF does to a hit only one facet knows.

The lexical-solvability audit (``docs/query-set-lexical-audit.md``) found 29 of
479 queries where the lexical facet finds the target and the content facet does
not, and A->B is -5.43pp anyway. That points the finger at the fusion step. This
script asks whether the finger is pointing at the right place, in two parts that
need neither a model nor a new query set:

1. **Arithmetic.** With the shipped constants (``rrf_k``, ``candidates_per_facet``,
   ``DEFAULT_FACET_WEIGHTS``), how mediocre can a document be in every facet and
   still outscore a document that one facet ranks first? This is a closed-form
   property of the operator; it makes no claim about quality.

2. **Occurrence, on real data.** The two lexical facets need no vectors, so the
   real 479-query set can be replayed through ``lex_seg`` + ``lex_tri`` and the
   burial counted. Two facets is the *mildest* case -- the shipped C and D fuse
   four -- so whatever shows up here is a lower bound.

   The replay must be run *after* the trigram repair in ``facetmark.text``.
   Before it, ``lex_tri`` came back empty for 186 of the 479 queries, so 39% of
   the set never reached the fusion step at all and the burial count was taken
   on a biased, latin-heavy remainder.

Neither part reports a win or a loss for any configuration. The verdict on any
fusion change belongs to the query set that has not been generated yet.

    python scripts/fusion_arith.py --db library.db --eval eval_loo.json \
        --out eval/fusion-arith.json
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path

from facetmark.config import Settings
from facetmark.search.lexical import lexical_lists
from facetmark.search.pipeline import CONFIGS, DEFAULT_FACET_WEIGHTS
from facetmark.search.rrf import guarantee_bonus, rrf


def arithmetic(k: int, depth: int, weights: dict[str, float]) -> dict:
    """Closed-form: the crossover between one confident facet and many bored ones."""
    w_top = max(weights.values())
    sole_first = w_top / (k + 1)  # the most a sole-facet hit can ever score

    rows = []
    for name in ("B", "C", "D"):
        cfg = CONFIGS[name]
        ws = {f: weights.get(f, 1.0) for f in sorted(cfg.facets)}
        total = sum(ws.values())
        # every facet ranks the distractor dead last within the candidate depth
        worst_case = total / (k + depth)
        # the rank at which a full-house document finally drops below a sole #1
        crossover = total * (k + 1) / w_top - k
        rows.append(
            {
                "config": name,
                "facets": ws,
                "total_weight": round(total, 3),
                "score_if_every_facet_ranks_it_last": round(worst_case, 6),
                "beats_sole_facet_first": worst_case > sole_first,
                "ratio_to_sole_facet_first": round(worst_case / sole_first, 3),
                # a document present in every facet outranks a sole-facet #1
                # while its (shared) rank is below this; compare with `depth`
                "crossover_rank": round(crossover, 1),
                "crossover_beyond_candidate_depth": crossover > depth,
            }
        )

    # the cheapest coalition that buries a sole-facet #1: two 1.0-weight facets
    two_flat = 2.0 * (k + 1) / w_top - k
    return {
        "rrf_k": k,
        "candidates_per_facet": depth,
        "facet_weights": dict(weights),
        "sole_facet_rank1_score": round(sole_first, 6),
        "two_flat_facets_crossover_rank": round(two_flat, 1),
        "per_config": rows,
    }


def max_term_lambda(k: int, depth: int, weights: dict[str, float], config: str) -> dict:
    """How large a CombMAX term would have to be to restore the guarantee.

    Principle: a document some facet ranks first must outscore a document that
    no facet ranks better than last. The closed form lives in
    :func:`facetmark.search.rrf.guarantee_bonus` -- this script calls it rather
    than restating it, because the number here and the number the ``C_max`` rung
    is built from have to be the same number.
    """
    ws = {f: weights.get(f, 1.0) for f in sorted(CONFIGS[config].facets)}
    lam = guarantee_bonus(k, depth, ws)
    return {
        "config": config,
        "lambda_required": round(lam, 3),
        "note": "score = sum_f w_f/(k+r_f) + lambda * max_f w_f/(k+r_f)",
        "implemented_as": "search.rrf.rrf(max_bonus=...); rung C_max, off by default",
    }


def _sole_facet_heads(lists: dict[str, list[int]]) -> dict[int, str]:
    """Docs that exactly one facet ranks first and no other facet lists at all."""
    membership: dict[int, set[str]] = {}
    for facet, ids in lists.items():
        for doc in ids:
            membership.setdefault(doc, set()).add(facet)
    out = {}
    for facet, ids in lists.items():
        if not ids:
            continue
        head = ids[0]
        if membership[head] == {facet}:
            out[head] = facet
    return out


def replay(db: Path, eval_path: Path, settings: Settings) -> dict:
    """Count the burial on the real query set, using the two model-free facets."""
    rep = json.loads(eval_path.read_text())
    queries = rep["queries"]
    depth = settings.candidates_per_facet
    k = settings.rrf_k
    weights = {f: DEFAULT_FACET_WEIGHTS.get(f, 1.0) for f in ("lex_seg", "lex_tri")}

    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row  # lexical_lists reads rows by column name
    try:
        buried = Counter()
        fused_ranks: list[int] = []
        by_type: dict[str, Counter] = {}
        examples = []
        disagree = 0
        skipped: Counter = Counter()
        gold = Counter()
        gold_examples = []
        for q in queries:
            lists = lexical_lists(conn, q["text"], limit=depth)
            lists = {f: ids for f, ids in lists.items() if ids}
            if len(lists) < 2:
                # Nothing to fuse. What survives the repair is the legitimate
                # case: a query whose every piece is under three characters, so
                # the trigram index has no term it could possibly match.
                skipped[",".join(sorted(lists)) or "none"] += 1
                continue
            heads = {f: ids[0] for f, ids in lists.items()}
            if len(set(heads.values())) > 1:
                disagree += 1
            fused = rrf(lists, k=k, weights=weights)
            position = {f.doc_id: i for i, f in enumerate(fused, start=1)}

            # --- (a) a document exactly one facet ranks first ------------------
            for doc, facet in _sole_facet_heads(lists).items():
                pos = position[doc]
                fused_ranks.append(pos)
                bucket = by_type.setdefault(q["qtype"], Counter())
                bucket["sole"] += 1
                for cut in (5, 10):
                    if pos > cut:
                        buried[cut] += 1
                        bucket[f"out_of_top{cut}"] += 1
                if pos > 10 and len(examples) < 15:
                    # who overtook it, and how well did their own facets rate them?
                    above = [f for f in fused[: pos - 1] if len(f.ranks) > 1]
                    tops = [min(f.ranks.values()) for f in above]
                    examples.append(
                        {
                            "qtype": q["qtype"],
                            "text": q["text"][:90],
                            "facet": facet,
                            "doc_id": doc,
                            "fused_rank": pos,
                            "overtaken_by_multi_facet_docs": len(above),
                            # the *strongest* overtaker: its best rank in any facet
                            "strongest_overtaker_best_facet_rank": min(tops, default=0),
                        }
                    )

            # --- (b) the gold target, which is what recall actually counts -----
            target = q["target_id"]
            in_facets = {f: ids.index(target) + 1 for f, ids in lists.items() if target in ids}
            if not in_facets:
                gold["target_in_no_lexical_list"] += 1
                continue
            best_facet_rank = min(in_facets.values())
            pos = position[target]
            sole = len(in_facets) == 1
            gold["sole_facet" if sole else "both_facets"] += 1
            if best_facet_rank <= 5:
                gold["facet_top5"] += 1
                if pos > 5:
                    gold["facet_top5_but_fused_out_of_top5"] += 1
                    if sole:
                        gold["sole_facet_top5_lost_by_fusion"] += 1
                        if len(gold_examples) < 12:
                            gold_examples.append(
                                {
                                    "qtype": q["qtype"],
                                    "text": q["text"][:90],
                                    "facet": next(iter(in_facets)),
                                    "facet_rank": best_facet_rank,
                                    "fused_rank": pos,
                                }
                            )
                elif sole:
                    gold["sole_facet_top5_survived_fusion"] += 1
    finally:
        conn.close()

    n = len(fused_ranks)
    return {
        "queries_replayed": len(queries),
        "queries_with_only_one_non_empty_facet": dict(skipped),
        "queries_fused": len(queries) - sum(skipped.values()),
        "queries_where_the_two_facets_disagree_on_first": disagree,
        "sole_facet_first_hits": n,
        "median_fused_rank": sorted(fused_ranks)[n // 2] if n else None,
        "pushed_out_of_top5": buried[5],
        "pushed_out_of_top10": buried[10],
        "share_pushed_out_of_top5": round(buried[5] / n, 4) if n else None,
        "share_pushed_out_of_top10": round(buried[10] / n, 4) if n else None,
        "by_type": {t: dict(c) for t, c in sorted(by_type.items())},
        "examples": examples,
        "gold_target": dict(gold),
        "gold_examples": gold_examples,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, required=True)
    ap.add_argument("--eval", type=Path, required=True, help="eval_loo.json, for its queries")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    settings = Settings(db_path=args.db, use_mock_provider=True)
    weights = dict(DEFAULT_FACET_WEIGHTS)
    result = {
        "arithmetic": arithmetic(settings.rrf_k, settings.candidates_per_facet, weights),
        "max_term_cost": [
            max_term_lambda(settings.rrf_k, settings.candidates_per_facet, weights, c)
            for c in ("B", "C")
        ],
        "replay_two_lexical_facets": replay(args.db, args.eval, settings),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result["arithmetic"], ensure_ascii=False, indent=2))
    print(json.dumps(result["max_term_cost"], ensure_ascii=False, indent=2))
    r = result["replay_two_lexical_facets"]
    print(json.dumps({kk: vv for kk, vv in r.items() if kk != "examples"},
                     ensure_ascii=False, indent=2))
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
