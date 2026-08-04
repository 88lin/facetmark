"""Judge the W2/W3 candidate switches on a query set that did not suggest them.

Six rungs were implemented after the W1 gate came back negative, and every one
of them was motivated by the same 479 queries any A/B against them would have
used. `search/pipeline.py` says so next to each: *implemented, off, unjudged*.
This script is what un-defers that, and it exists **before** the fresh query set
has been run, so the comparisons, the families and the correction are fixed
rather than chosen once the numbers are visible.

Two levels of judgement, deliberately not mixed:

* **Mechanism** -- the switch against the rung it modifies. Answers "does this
  do the thing it was built to do".
* **Shipping** -- the switch against ``A``, the retrieval core of what actually
  ships. Only this level can change a default. The C family sat 5-6pp *below*
  ``A`` in W1, so a switch can win its mechanism test and still be far from
  shippable, and reporting only the first would be a way of not saying that.

``A`` stands in for the shipping default (``full`` = content + graph + decay)
on ranked metrics because W1 measured ``A -> A_graph`` at exactly +0.00pp with
**zero** discordant queries: expansion never touches the ranked list. Decay is
outside the ladder by construction.

Usage::

    python switch_verdicts.py --report eval.json --out verdicts.json
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from facetmark.eval.harness import Outcome, bootstrap_ci, mcnemar, summarise

#: The switch, the rung it modifies, and what it was built to do. Fixed here
#: before the run: nothing gets added to this list after results exist, and an
#: afterthought comparison is reported as exploratory, in its own section, with
#: no verdict attached.
SWITCHES: list[tuple[str, str, str]] = [
    ("A_gatedctx", "A_ctx", "contextual multiplier fires only on episodic-looking queries"),
    ("D_gated", "D", "the same gate inside the full fusion stack"),
    ("C_notri", "C", "delete the trigram half of the lexical facet"),
    ("C_lowlex", "C", "damp both lexical facets to 0.3/0.2 instead of deleting them"),
    ("C_abstain", "C", "a facet that cannot tell its own results apart does not vote"),
    ("C_max", "C", "CombMAX term sized to restore the sole-facet guarantee"),
]

#: Every switch is judged against this for the shipping question.
SHIPPING_BASELINE = "A"

#: Family-wise error rate for each family, controlled by Holm-Bonferroni.
ALPHA = 0.05

#: The gate's justification is stratified, so its verdict has a stratified
#: requirement: the content regression has to stop being credible and the
#: episodic gain has to stay credible. Applied to the shipping comparison
#: (switch vs A), because that is the pair the +8.14 / -9.94 was measured on.
GATED = {"A_gatedctx", "D_gated"}


def outcomes(report: dict, key: str) -> list[Outcome]:
    """Rebuild the per-query judgements a rung produced.

    The report stores ranks rather than :class:`Outcome`s, so every aggregate
    in it can be recomputed from what it publishes -- including slices its
    author did not cut.
    """
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


def holm(pvals: dict[str, float], alpha: float = ALPHA) -> dict[str, dict]:
    """Holm-Bonferroni over one family of tests.

    Six switches judged at 0.05 each would expect a winner roughly a quarter of
    the time with nothing going on. Holm is used rather than Bonferroni because
    it is uniformly more powerful and needs no extra assumption, and rather
    than FDR because the question here is "should this ship", where one false
    positive is a wrong default, not one wrong row in a gene list.
    """
    order = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(order)
    out: dict[str, dict] = {}
    prev_reject = True
    for i, (name, p) in enumerate(order):
        thresh = alpha / (m - i)
        reject = bool(prev_reject and p <= thresh)
        prev_reject = reject
        out[name] = {"p": p, "holm_threshold": round(thresh, 5), "significant": reject,
                     "rank_in_family": i + 1, "family_size": m}
    return out


def compare(report: dict, base: str, switch: str, *, resamples: int) -> dict:
    a, b = outcomes(report, base), outcomes(report, switch)
    sa, sb = summarise(a), summarise(b)
    row = {
        "from": base,
        "to": switch,
        "recall@5": {base: sa["recall@5"], switch: sb["recall@5"]},
        "recall@5_pp": round((sb["recall@5"] - sa["recall@5"]) * 100, 2),
        "ci95_pp": list(bootstrap_ci(a, b, resamples=resamples)),
        "mcnemar": mcnemar(a, b),
        "by_type": {},
    }
    for t in sorted({o.qtype for o in a}):
        ia = [o for o in a if o.qtype == t]
        ib = [o for o in b if o.qtype == t]
        row["by_type"][t] = {
            "n": len(ia),
            "recall@5_pp": round((summarise(ib)["recall@5"] - summarise(ia)["recall@5"]) * 100, 2),
            "ci95_pp": list(bootstrap_ci(ia, ib, resamples=resamples)),
            "mcnemar": mcnemar(ia, ib),
        }
    return row


def detectable_pp(discordant: int, n: int, alpha: float = ALPHA, power: float = 0.80) -> float:
    """Smallest net difference this pairing could have seen, in percentage points.

    Normal approximation to the sign test: with ``m`` discordant queries, 80%
    power at two-sided ``alpha`` needs the gained-minus-lost count to reach
    about ``(z_alpha + z_power) * sqrt(m)``. Reported per comparison because it
    depends on ``m``, and ``m`` is a property of how similar the two rungs are
    -- two rungs that differ by a weight disagree on few queries and are
    therefore *more* sensitive to a small effect than the A->B step ever was.
    """
    if discordant <= 0 or n <= 0:
        return float("nan")
    z = 1.959963985 + 0.841621234
    return round(z * math.sqrt(discordant) / n * 100, 2)


def verdict(row: dict, sig: dict, *, gated: bool, strata: dict | None) -> dict:
    """Pre-registered rule: point estimate up, CI clear of zero, Holm-significant.

    "Not supported" is not "harmful" and is not "no effect" -- see the
    detectable effect reported next to it.
    """
    lo, hi = row["ci95_pp"]
    reasons: list[str] = []
    if row["recall@5_pp"] <= 0:
        reasons.append("point estimate is not positive")
    if lo <= 0:
        # The test is `lo > 0` either way, but the sentence has to say what the
        # interval actually did. Writing "CI95 includes zero" under
        # CI[-9.58, -2.27] is a false statement about a real measurement: that
        # interval excludes zero, on the losing side.
        reasons.append("CI95 lies below zero" if hi < 0 else "CI95 includes zero")
    if not sig["significant"]:
        reasons.append(f"McNemar p={sig['p']} above Holm threshold {sig['holm_threshold']}")
    if gated and strata is not None:
        content_lo, content_hi = strata["q_content"]["ci95_pp"]
        epi_lo, _ = strata["q_episodic"]["ci95_pp"]
        if not (content_lo <= 0 <= content_hi):
            reasons.append("gate requirement: q_content CI still excludes zero")
        if epi_lo <= 0:
            reasons.append("gate requirement: q_episodic CI includes zero")
    return {"supported": not reasons, "failed": reasons}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True, help="eval report JSON with per-rung outcomes")
    ap.add_argument("--out", required=True)
    ap.add_argument("--bootstrap", type=int, default=10000)
    args = ap.parse_args()

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    n = len(report["queries"])

    families: dict[str, list[dict]] = {"mechanism": [], "shipping": []}
    for switch, base, claim in SWITCHES:
        m = compare(report, base, switch, resamples=args.bootstrap)
        m["claim"] = claim
        families["mechanism"].append(m)
        s = compare(report, SHIPPING_BASELINE, switch, resamples=args.bootstrap)
        s["claim"] = claim
        families["shipping"].append(s)

    out: dict = {
        "source": args.report,
        "n_queries": n,
        "alpha": ALPHA,
        "correction": "Holm-Bonferroni within each family, families corrected separately",
        "shipping_baseline": SHIPPING_BASELINE,
        "families": {},
    }
    for fam, rows in families.items():
        sigs = holm({r["to"]: r["mcnemar"]["p"] for r in rows})
        for r in rows:
            sig = sigs[r["to"]]
            disc = r["mcnemar"]["gained"] + r["mcnemar"]["lost"]
            r["holm"] = sig
            r["discordant"] = disc
            r["detectable_pp_at_80pct_power"] = detectable_pp(disc, n)
            r["verdict"] = verdict(
                r, sig,
                gated=(fam == "shipping" and r["to"] in GATED),
                strata=r["by_type"],
            )
        out["families"][fam] = rows

    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")

    for fam, rows in out["families"].items():
        print(f"\n=== {fam} (n={n}) ===")
        for r in rows:
            v = "SUPPORTED" if r["verdict"]["supported"] else "not supported"
            print(f"  {r['from']:>10} -> {r['to']:<12} {r['recall@5_pp']:+6.2f}pp "
                  f"CI{r['ci95_pp']} p={r['mcnemar']['p']:<8} "
                  f"disc={r['discordant']:<4} mde={r['detectable_pp_at_80pct_power']}pp  {v}")
            for reason in r["verdict"]["failed"]:
                print(f"        - {reason}")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
