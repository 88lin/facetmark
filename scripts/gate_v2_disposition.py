#!/usr/bin/env python
"""Which pre-registered branch the two gate_v2 bars select.

`scripts/gate_precision.py` decides whether the shipped gate failed. This
decides what happens next, and it exists as a script for one reason: the
disposition table in `docs/gate-precision-protocol.md` §6 is a conjunction, and
a conjunction is exactly the kind of rule that gets read loosely when one half
of it is a comfortable number.

    (a) the probe-set cost is gone        CI95 contains 0, or lower bound > 0
    (b) the W2/W3 win survives            CI95 lower bound > 0 vs A

    a and b        -> gate_v2 becomes the default, new version number
    a and not b    -> default reverts to 1.1.0's ungated behaviour
    not a          -> the remedy did not remedy it; same revert, because the
                      protocol offers no branch in which a gate that still
                      costs precision keeps the default

Usage:
    python scripts/gate_v2_disposition.py \
        --probe eval/gate-v2-probe.json \
        --holdout eval/gate-v2-holdout.json \
        --out eval/gate-v2-disposition.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from facetmark.eval.harness import Outcome, bootstrap_ci, mcnemar, summarise

BASE = "A"
V1 = "A_gatedctx"
V2 = "A_gatedctx_v2"


def outcomes(report: dict, key: str) -> list[Outcome]:
    if key not in report["outcomes"]:
        raise SystemExit(f"{key} was not run in this report; rungs: "
                         f"{sorted(report['outcomes'])}")
    return [
        Outcome(qtype=q["qtype"], rank=int(o["rank"]), ms=float(o.get("ms", 0.0)),
                expanded=bool(o.get("expanded")))
        for q, o in zip(report["queries"], report["outcomes"][key], strict=True)
    ]


def compare(a: list[Outcome], b: list[Outcome], *, resamples: int) -> dict:
    sa, sb = summarise(a), summarise(b)
    lo, hi = bootstrap_ci(a, b, resamples=resamples, seed=11)
    m = mcnemar(a, b)
    return {
        "n": len(a),
        "recall@5": {BASE: round(sa["recall@5"], 4), "switch": round(sb["recall@5"], 4)},
        "recall@5_pp": round((sb["recall@5"] - sa["recall@5"]) * 100, 2),
        "ci95_pp": [lo, hi],
        "mcnemar": m,
    }


def gate_a(res: dict) -> dict:
    """Cost gone: the interval either straddles zero or sits above it."""
    lo, hi = res["ci95_pp"]
    ok = lo > 0.0 or (lo <= 0.0 <= hi)
    return {
        "name": "probe-set cost is gone",
        "rule": "CI95 contains 0, or lower bound > 0",
        "passed": bool(ok),
        **res,
    }


def gate_b(res: dict) -> dict:
    """Benefit retained: strictly above zero."""
    lo, _hi = res["ci95_pp"]
    return {
        "name": "W2/W3 win survives",
        "rule": "CI95 lower bound > 0 versus A",
        "passed": bool(lo > 0.0),
        **res,
    }


def disposition(a_ok: bool, b_ok: bool) -> dict:
    if a_ok and b_ok:
        return {
            "action": "ship_gate_v2",
            "zh": "gate_v2 成为默认，版本号再走一次",
            "default_config": "content + context(gated, v2) + graph + decay",
            "why": "both pre-registered bars cleared",
        }
    revert = {
        "action": "revert_to_1_1_0_ungated",
        "zh": "默认值退回 1.1.0 的无门控行为",
        "default_config": "content + graph + decay",
    }
    if a_ok and not b_ok:
        return {**revert, "why": "the narrowed gate is precise enough but no "
                                 "longer pays for itself (protocol §6 rule 3)"}
    if b_ok and not a_ok:
        return {**revert, "why": "the narrowed gate still pays for itself but is "
                                 "still imprecise; the protocol requires both, "
                                 "and offers no branch where an imprecise gate "
                                 "keeps the default"}
    return {**revert, "why": "the remedy cleared neither bar"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", required=True, help="eval report over the probe set")
    ap.add_argument("--holdout", required=True, help="eval report over the 616 W2/W3 queries")
    ap.add_argument("--out", required=True)
    ap.add_argument("--bootstrap", type=int, default=10000)
    args = ap.parse_args()

    probe = json.loads(Path(args.probe).read_text(encoding="utf-8"))
    hold = json.loads(Path(args.holdout).read_text(encoding="utf-8"))

    a = gate_a(compare(outcomes(probe, BASE), outcomes(probe, V2),
                       resamples=args.bootstrap))
    b = gate_b(compare(outcomes(hold, BASE), outcomes(hold, V2),
                       resamples=args.bootstrap))
    d = disposition(a["passed"], b["passed"])

    # The v1 numbers on both sets, so the file answers "compared with what?"
    context = {}
    for name, rep in (("probe", probe), ("holdout", hold)):
        if V1 in rep["outcomes"]:
            context[name] = compare(outcomes(rep, BASE), outcomes(rep, V1),
                                    resamples=args.bootstrap)

    out = {
        "protocol": "docs/gate-precision-protocol.md",
        "report": "docs/gate-precision.md",
        "sources": {"probe": args.probe, "holdout": args.holdout},
        "bootstrap": args.bootstrap,
        "gate_a": a,
        "gate_b": b,
        "v1_for_comparison": context,
        "disposition": d,
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")

    for g in (a, b):
        lo, hi = g["ci95_pp"]
        print(f"{'PASS' if g['passed'] else 'FAIL'}  {g['name']:24s} "
              f"n={g['n']:3d}  Δ {g['recall@5_pp']:+6.2f} pp  "
              f"CI95 [{lo:+.2f}, {hi:+.2f}]  "
              f"{g['mcnemar']['gained']}/{g['mcnemar']['lost']}")
    print(f"\nDISPOSITION {d['action']} ({d['zh']})")
    print(f"  default becomes: {d['default_config']}")
    print(f"  because: {d['why']}")


if __name__ == "__main__":
    main()
