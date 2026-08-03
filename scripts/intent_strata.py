#!/usr/bin/env python3
"""Does the intent facet only pay off on pages whose own text is thin?

W4 read 50 extracted intents by hand and said no overall. It also left a
hypothesis behind: 11 of the 19 usable intents sat on pages whose title carried
no information, so maybe intent extraction is a title-repair trick rather than a
retrieval facet. This script tests that hypothesis on data that already exists.

Three strata analyses, none of which need a new query set or a live model:

S1  Retrieval. Split the 479 W1 queries by how many content words the gold
    page's title has, then compare A (content facet only) against C_nolex
    (content + intent) inside each stratum. If the hypothesis holds, the intent
    facet should stop losing -- or start winning -- where titles are degenerate.

S2  Neighbourhoods. Split all 2,376 probes from the facet-overlap run the same
    way and by body length, and look at how much the intent facet's top-k
    differs from the content facet's. This is the mechanism the hypothesis
    assumes: intent has to carry information content does not.

S3  Grounding. For every kept intent string, measure what fraction of its
    content words appear nowhere on the page. Lexical only, so it is an upper
    bound on invention, not a measurement of it -- a paraphrase counts as
    ungrounded. Split by the same strata. If thin pages produce more ungrounded
    intent, the hypothesis is in trouble from the other side.

Thresholds are fixed here before the numbers are read; see docs/w4-intent-strata.md.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

# --- pre-registered thresholds -------------------------------------------------
# A title with three content words or fewer cannot pick a document out of a
# 2,376-page library on its own. Chosen for power, not for outcome: the split
# lands 213/266 across the query set, which is the only body-or-title cut that
# leaves both strata usable.
TITLE_DEGENERATE_MAX_TOKENS = 3
# A page with under 500 characters of extracted body gives the content facet
# almost nothing to embed. Reported for the library, unusable for retrieval:
# zero W1 queries point at such a page.
BODY_THIN_MAX_CHARS = 500
BOOTSTRAP_N = 10000
BOOTSTRAP_SEED = 20260803

WORD_RE = re.compile(r"[0-9A-Za-z\u4e00-\u9fff]")


def content_words(text: str) -> list[str]:
    """Segment and drop punctuation-only tokens. jieba for CJK, whitespace else."""
    from facetmark.text import segment_query

    return [w.lower() for w in segment_query(text or "").split() if WORD_RE.search(w)]


def hit5(rank: int) -> int:
    return 1 if 0 < rank <= 5 else 0


def mcnemar_p(gained: int, lost: int) -> float:
    """Exact two-sided binomial test on the discordant pairs."""
    n = gained + lost
    if n == 0:
        return 1.0
    k = min(gained, lost)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2**n)
    return min(1.0, 2 * tail)


def boot_ci(pairs: list[tuple[int, int]], rng: random.Random) -> tuple[float, float]:
    """Percentile CI for the paired mean difference, in percentage points."""
    if not pairs:
        return (float("nan"), float("nan"))
    diffs = [b - a for a, b in pairs]
    n = len(diffs)
    draws = sorted(
        sum(diffs[rng.randrange(n)] for _ in range(n)) / n * 100 for _ in range(BOOTSTRAP_N)
    )
    return (round(draws[int(0.025 * BOOTSTRAP_N)], 2), round(draws[int(0.975 * BOOTSTRAP_N)], 2))


def boot_interaction(
    deg: list[tuple[int, int]], norm: list[tuple[int, int]], rng: random.Random
) -> tuple[float, float]:
    """CI for (delta in degenerate stratum) - (delta in normal stratum)."""
    dd = [b - a for a, b in deg]
    dn = [b - a for a, b in norm]
    if not dd or not dn:
        return (float("nan"), float("nan"))
    nd, nn = len(dd), len(dn)
    draws = []
    for _ in range(BOOTSTRAP_N):
        md = sum(dd[rng.randrange(nd)] for _ in range(nd)) / nd
        mn = sum(dn[rng.randrange(nn)] for _ in range(nn)) / nn
        draws.append((md - mn) * 100)
    draws.sort()
    return (round(draws[int(0.025 * BOOTSTRAP_N)], 2), round(draws[int(0.975 * BOOTSTRAP_N)], 2))


def load_page_stats(db: Path) -> dict[int, dict]:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = conn.execute(
        "select b.id, b.title, coalesce(c.char_count, 0), coalesce(c.body_seg, '') "
        "from bookmark b left join content c on c.bookmark_id = b.id"
    ).fetchall()
    stats = {}
    for bid, title, chars, body_seg in rows:
        tw = content_words(title)
        stats[bid] = {
            "title": title,
            "title_tokens": len(tw),
            "title_set": set(tw),
            "chars": chars,
            "body_set": {w.lower() for w in body_seg.split() if WORD_RE.search(w)},
            "degenerate_title": len(tw) <= TITLE_DEGENERATE_MAX_TOKENS,
            "thin_body": chars < BODY_THIN_MAX_CHARS,
        }
    conn.close()
    return stats


def s1_retrieval(evalp: Path, stats: dict[int, dict], rng: random.Random) -> dict:
    rep = json.loads(evalp.read_text())
    queries = rep["queries"]
    a = rep["outcomes"]["A"]
    c = rep["outcomes"]["C_nolex"]
    strata: dict[str, list] = {"degenerate": [], "normal": []}
    qtypes: dict[str, Counter] = {"degenerate": Counter(), "normal": Counter()}
    gold_chars = []
    for i, q in enumerate(queries):
        st = stats[q["target_id"]]
        gold_chars.append(st["chars"])
        key = "degenerate" if st["degenerate_title"] else "normal"
        strata[key].append((hit5(a[i]["rank"]), hit5(c[i]["rank"]), q["qtype"]))
        qtypes[key][q["qtype"]] += 1

    out: dict = {
        "gold_body_chars": {
            "min": min(gold_chars),
            "p05": sorted(gold_chars)[len(gold_chars) // 20],
            "median": sorted(gold_chars)[len(gold_chars) // 2],
            "under_thin_threshold": sum(1 for x in gold_chars if x < BODY_THIN_MAX_CHARS),
        },
        "strata": {},
    }
    for key, rows in strata.items():
        pairs = [(x[0], x[1]) for x in rows]
        gained = sum(1 for x, y in pairs if y and not x)
        lost = sum(1 for x, y in pairs if x and not y)
        out["strata"][key] = {
            "n": len(pairs),
            "qtypes": dict(qtypes[key]),
            "A_recall@5": round(sum(x for x, _ in pairs) / len(pairs), 4),
            "C_nolex_recall@5": round(sum(y for _, y in pairs) / len(pairs), 4),
            "delta_pp": round((sum(y - x for x, y in pairs) / len(pairs)) * 100, 2),
            "ci95_pp": boot_ci(pairs, rng),
            "mcnemar": {"gained": gained, "lost": lost, "p": round(mcnemar_p(gained, lost), 5)},
        }
    out["interaction_pp"] = round(
        out["strata"]["degenerate"]["delta_pp"] - out["strata"]["normal"]["delta_pp"], 2
    )
    out["interaction_ci95_pp"] = boot_interaction(
        [(x[0], x[1]) for x in strata["degenerate"]],
        [(x[0], x[1]) for x in strata["normal"]],
        rng,
    )
    # qtype is the obvious confounder: the intent facet behaves very differently
    # on content vs episodic queries, and the strata need not share a mix.
    per_type = {}
    for qt in sorted({x[2] for rows in strata.values() for x in rows}):
        per_type[qt] = {}
        for key, rows in strata.items():
            sub = [(x[0], x[1]) for x in rows if x[2] == qt]
            per_type[qt][key] = {
                "n": len(sub),
                "delta_pp": round(sum(y - x for x, y in sub) / len(sub) * 100, 2) if sub else None,
            }
    out["by_qtype"] = per_type
    return out


def s2_neighbourhoods(overlapp: Path, stats: dict[int, dict]) -> dict:
    raw = json.loads(overlapp.read_text())
    buckets: dict[str, list[dict]] = {}
    for row in raw["rows"]:
        st = stats.get(row["id"])
        if st is None:
            continue
        for key in (
            "degenerate_title" if st["degenerate_title"] else "normal_title",
            "thin_body" if st["thin_body"] else "normal_body",
            "all",
        ):
            buckets.setdefault(key, []).append(row)
    out = {}
    for key, rows in sorted(buckets.items()):
        lex = [r["overlap_k_lex"] for r in rows if r.get("n_lex")]
        out[key] = {
            "n": len(rows),
            "mean_overlap_k_intent": round(sum(r["overlap_k"] for r in rows) / len(rows), 4),
            "mean_overlap_k_lex": round(sum(lex) / len(lex), 4) if lex else None,
            "self_found_in_intent_topk": sum(1 for r in rows if 0 < r["self_rank_intent"] <= 10),
            "self_rank_intent_is_1": sum(1 for r in rows if r["self_rank_intent"] == 1),
        }
    return out


def s3_grounding(db: Path, stats: dict[int, dict]) -> dict:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = conn.execute(
        "select bookmark_id, text from intent_query where kept = 1 order by bookmark_id, id"
    ).fetchall()
    conn.close()
    buckets: dict[str, list[tuple[float, float]]] = {}
    for bid, text in rows:
        st = stats.get(bid)
        if st is None:
            continue
        words = set(content_words(text))
        if not words:
            continue
        page = st["title_set"] | st["body_set"]
        ungrounded = len(words - page) / len(words)
        novel_vs_title = len(words - st["title_set"]) / len(words)
        for key in (
            "degenerate_title" if st["degenerate_title"] else "normal_title",
            "thin_body" if st["thin_body"] else "normal_body",
            "all",
        ):
            buckets.setdefault(key, []).append((ungrounded, novel_vs_title))
    return {
        k: {
            "n": len(v),
            "mean_ungrounded": round(sum(x for x, _ in v) / len(v), 4),
            "mean_novel_vs_title": round(sum(y for _, y in v) / len(v), 4),
        }
        for k, v in sorted(buckets.items())
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, required=True, help="indexed W1 library snapshot")
    ap.add_argument("--eval", type=Path, required=True, help="eval_loo.json (needs A + C_nolex)")
    ap.add_argument("--overlap", type=Path, help="facet_overlap.json from scripts/facet_overlap.py")
    ap.add_argument("--out", type=Path, help="write the full result as JSON")
    args = ap.parse_args()

    rng = random.Random(BOOTSTRAP_SEED)
    stats = load_page_stats(args.db)
    result = {
        "thresholds": {
            "title_degenerate_max_tokens": TITLE_DEGENERATE_MAX_TOKENS,
            "body_thin_max_chars": BODY_THIN_MAX_CHARS,
            "bootstrap_n": BOOTSTRAP_N,
            "bootstrap_seed": BOOTSTRAP_SEED,
        },
        "library": {
            "pages": len(stats),
            "degenerate_title": sum(1 for s in stats.values() if s["degenerate_title"]),
            "thin_body": sum(1 for s in stats.values() if s["thin_body"]),
        },
        "s1_retrieval": s1_retrieval(args.eval, stats, rng),
        "s3_grounding": s3_grounding(args.db, stats),
    }
    if args.overlap:
        result["s2_neighbourhoods"] = s2_neighbourhoods(args.overlap, stats)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.out:
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
