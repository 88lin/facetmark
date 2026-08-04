"""Judge the episodic gate's precision against ``docs/gate-precision-protocol.md``.

The protocol is the contract; this file only applies it. Every threshold below
is a quotation from a document committed before the probe set existed, and the
git history is the audit trail.

What is being priced: the probe set is 400 *content* queries, every one of which
carries a time expression belonging to its subject matter. The gate reads that
expression as a save-time window, and the window is wrong by construction. The
question is what that costs in Recall@5 -- **not** how often such queries occur,
which no measurement here can answer.

The self-check that makes the rest of the numbers trustworthy is the last one
printed: on queries where the gate does **not** fire, the two rungs are the same
code path, so their ΔR@5 must be exactly 0.00pp with zero discordant pairs. If
it is not, the harness or the gate is not doing what this script assumes and the
verdict is void.

Usage::

    python gate_precision.py --report eval/gate-precision-eval.json \
        --queries eval/queries/gate-precision.jsonl \
        --db library.db --out eval/gate-precision.json
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
from collections import Counter
from pathlib import Path

from facetmark.eval.harness import Outcome, bootstrap_ci, mcnemar, summarise
from facetmark.search.understand import classify

BASE = "A"
SWITCH = "A_gatedctx"

#: From the protocol's verdict table. Not tunable here on purpose.
FAIL_POINT_PP = -2.0
ALPHA = 0.05

#: Buckets over |content_year - save_year|, so "how wrong was the window" can be
#: read off the result. Descriptive: the protocol attaches no verdict to these.
DISTANCE_BUCKETS = ((1, 2, "1-2y"), (3, 7, "3-7y"), (8, 99, "8y+"))


def load_queries(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("//"):
            rows.append(json.loads(line))
    return rows


def index_clock(db: str) -> int | None:
    """``meta.created_at``: "recently" has to mean the same thing tomorrow."""
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        row = conn.execute("SELECT value FROM meta WHERE key = 'created_at'").fetchone()
    except sqlite3.Error:  # pragma: no cover - operator tool
        return None
    finally:
        conn.close()
    return int(row[0]) if row and str(row[0]).isdigit() else None


def outcomes(report: dict, key: str) -> list[Outcome]:
    if key not in report.get("outcomes", {}):
        raise SystemExit(f"rung {key!r} is not in this report; it has "
                         f"{', '.join(sorted(report.get('outcomes', {})))}")
    qs = report["queries"]
    rows = report["outcomes"][key]
    if len(rows) != len(qs):
        raise SystemExit(f"rung {key}: {len(rows)} outcomes for {len(qs)} queries")
    return [
        Outcome(qtype=q["qtype"], rank=int(r["rank"]), ms=float(r.get("ms", 0.0)),
                expanded=bool(r.get("expanded", False)))
        for q, r in zip(qs, rows, strict=True)
    ]


def detectable_pp(discordant: int, n: int) -> float:
    """The same formula the W2/W3 verdicts used, so the two are comparable."""
    if discordant <= 0 or n <= 0:
        return float("nan")
    z = 1.959963985 + 0.841621234
    return round(z * math.sqrt(discordant) / n * 100, 2)


def slice_delta(a: list[Outcome], b: list[Outcome], idx: list[int], *,
                resamples: int) -> dict:
    """ΔR@5 over a subset of query positions, with the same paired machinery."""
    if not idx:
        return {"n": 0}
    ia = [a[i] for i in idx]
    ib = [b[i] for i in idx]
    mc = mcnemar(ia, ib)
    disc = int(mc["gained"] + mc["lost"])
    return {
        "n": len(idx),
        "recall@5": {BASE: summarise(ia)["recall@5"], SWITCH: summarise(ib)["recall@5"]},
        "recall@5_pp": round((summarise(ib)["recall@5"] - summarise(ia)["recall@5"]) * 100, 2),
        "ci95_pp": list(bootstrap_ci(ia, ib, resamples=resamples)),
        "mcnemar": mc,
        "discordant": disc,
        "detectable_pp_at_80pct_power": detectable_pp(disc, len(idx)),
    }


def verdict_for(point: float, lo: float, hi: float) -> dict:
    """The protocol's three-row table, plus the row it does not have.

    A point estimate of -1.0pp with a CI entirely below zero is a real cost that
    is smaller than the threshold the protocol set for triggering ``gate_v2``.
    That case is neither "unqualified" nor "no cost found", and reporting it as
    either would be a lie about the interval. It gets its own label and triggers
    no disposition, which is what the pre-registered threshold implies.
    """
    if point <= FAIL_POINT_PP and hi < 0:
        return {"label": "gate_precision_unqualified",
                "zh": "门控精确率不合格",
                "triggers_disposition": True,
                "why": f"point {point:+.2f}pp <= {FAIL_POINT_PP}pp and CI95 upper "
                       f"bound {hi:+.2f}pp < 0"}
    if lo <= 0 <= hi:
        return {"label": "no_cost_detected", "zh": "未发现代价",
                "triggers_disposition": False,
                "why": f"CI95 [{lo:+.2f}, {hi:+.2f}] contains zero"}
    if lo > 0:
        return {"label": "beneficial", "zh": "反而有益",
                "triggers_disposition": False,
                "why": f"CI95 lower bound {lo:+.2f}pp > 0"}
    return {"label": "cost_below_threshold", "zh": "有代价，但小于预注册门槛",
            "triggers_disposition": False,
            "why": f"CI95 [{lo:+.2f}, {hi:+.2f}] excludes zero on the losing side, "
                   f"but the point estimate {point:+.2f}pp is above the "
                   f"{FAIL_POINT_PP}pp threshold the protocol set"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--queries", required=True,
                    help="the probe jsonl, for subtype and year-distance metadata")
    ap.add_argument("--db")
    ap.add_argument("--now", type=int)
    ap.add_argument("--out", required=True)
    ap.add_argument("--bootstrap", type=int, default=10000)
    args = ap.parse_args()

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    probes = load_queries(Path(args.queries))
    qs = report["queries"]
    if len(probes) != len(qs):
        raise SystemExit(f"{len(probes)} probe lines but {len(qs)} scored queries")
    for p, q in zip(probes, qs, strict=True):
        if p["text"] != q["text"]:
            raise SystemExit("probe file and report are not in the same order; "
                             f"{p['text']!r} != {q['text']!r}")

    now_ts = args.now or (index_clock(args.db) if args.db else None)
    a, b = outcomes(report, BASE), outcomes(report, SWITCH)

    fired, rules = [], []
    for p in probes:
        u = classify(p["text"], now_ts=now_ts)
        fired.append(bool(u.is_episodic))
        rules.append(tuple(u.rule_hits or ("(none)",)) if u.is_episodic else ())

    n = len(probes)
    primary = slice_delta(a, b, list(range(n)), resamples=args.bootstrap)
    lo, hi = primary["ci95_pp"]
    v = verdict_for(primary["recall@5_pp"], lo, hi)

    idx_fired = [i for i in range(n) if fired[i]]
    idx_quiet = [i for i in range(n) if not fired[i]]
    quiet = slice_delta(a, b, idx_quiet, resamples=args.bootstrap)
    selfcheck_ok = (not idx_quiet) or (quiet["recall@5_pp"] == 0.0
                                       and quiet["discordant"] == 0)

    by_subtype = {}
    for s in sorted({p["subtype"] for p in probes}):
        idx = [i for i in range(n) if probes[i]["subtype"] == s]
        by_subtype[s] = slice_delta(a, b, idx, resamples=args.bootstrap)
        by_subtype[s]["fired"] = sum(fired[i] for i in idx)

    by_distance = {}
    for lo_d, hi_d, name in DISTANCE_BUCKETS:
        idx = [i for i in range(n)
               if probes[i].get("year_distance") is not None
               and lo_d <= probes[i]["year_distance"] <= hi_d]
        if idx:
            by_distance[name] = slice_delta(a, b, idx, resamples=args.bootstrap)

    out = {
        "protocol": "docs/gate-precision-protocol.md",
        "source": args.report,
        "queries": args.queries,
        "clock": now_ts,
        "n": n,
        "bootstrap": args.bootstrap,
        "alpha": ALPHA,
        "primary": {**primary, "verdict": v},
        "firing": {
            "overall": {"n": n, "fired": len(idx_fired),
                        "share": round(len(idx_fired) / n, 4) if n else 0.0},
            "by_subtype": {s: {"n": by_subtype[s]["n"], "fired": by_subtype[s]["fired"],
                               "share": round(by_subtype[s]["fired"] / by_subtype[s]["n"], 4)}
                           for s in by_subtype},
            "by_rule": dict(Counter("+".join(r) for r in rules if r).most_common()),
        },
        "secondary": {
            "fired_subset": slice_delta(a, b, idx_fired, resamples=args.bootstrap),
            "not_fired_subset": quiet,
            "by_subtype": by_subtype,
            "by_year_distance": by_distance,
        },
        "self_check": {
            "rule": "the two rungs differ only by the gate, so ΔR@5 on queries "
                    "where it never fires must be exactly 0.00pp",
            "passed": bool(selfcheck_ok),
            "not_fired_n": len(idx_quiet),
        },
    }
    if not selfcheck_ok:
        out["primary"]["verdict"] = {
            "label": "void", "zh": "结论作废",
            "triggers_disposition": False,
            "why": "the not-fired subset moved; the measurement is not measuring "
                   "the gate",
        }

    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")

    p = out["primary"]
    print(f"n={n}  fired {len(idx_fired)}/{n} "
          f"({out['firing']['overall']['share'] * 100:.1f}%)")
    print(f"{BASE} R@5 {p['recall@5'][BASE]:.4f} -> {SWITCH} {p['recall@5'][SWITCH]:.4f}")
    print(f"Δ {p['recall@5_pp']:+.2f} pp  CI95 [{lo:+.2f}, {hi:+.2f}]  "
          f"McNemar gained {p['mcnemar']['gained']} lost {p['mcnemar']['lost']} "
          f"p={p['mcnemar']['p']}  mde {p['detectable_pp_at_80pct_power']}pp")
    print(f"VERDICT {out['primary']['verdict']['label']} "
          f"({out['primary']['verdict']['zh']}) -- {out['primary']['verdict']['why']}")
    for s, row in by_subtype.items():
        slo, shi = row["ci95_pp"]
        print(f"  {s:11s} n={row['n']:3d} fired={row['fired']:3d} "
              f"Δ {row['recall@5_pp']:+.2f} pp CI95 [{slo:+.2f}, {shi:+.2f}] "
              f"mde {row['detectable_pp_at_80pct_power']}pp")
    for name, row in by_distance.items():
        print(f"  distance {name:5s} n={row['n']:3d} Δ {row['recall@5_pp']:+.2f} pp")
    fs = out["secondary"]["fired_subset"]
    if fs.get("n"):
        print(f"  fired subset     n={fs['n']:3d} Δ {fs['recall@5_pp']:+.2f} pp "
              f"CI95 {fs['ci95_pp']}")
    print(f"  not-fired subset n={quiet.get('n', 0):3d} "
          f"Δ {quiet.get('recall@5_pp', 0.0):+.2f} pp  "
          f"self-check {'PASS' if selfcheck_ok else 'FAIL -- verdict void'}")


if __name__ == "__main__":
    main()
