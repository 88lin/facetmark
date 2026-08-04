"""Where does the episodic gate actually fire, and on what evidence?

``A_gatedctx`` runs the contextual multiplier only when
:attr:`QueryUnderstanding.is_episodic` is true. Any recall gain it shows is
therefore a gain *of the multiplier on the queries the gate selected*, and the
gate's selection is a separate, checkable thing from the recall number.

It has to be checked separately on this query set in particular, because the
generator built episodic queries by inserting a time phrase and **keeping only
the ones the product's own classifier could parse** (`eval/queries/README.md`,
bias 1). So the gate agreeing with the ``q_episodic`` label is partly
construction, not evidence. What is *not* construction is the other direction:
nothing screened the content and vague queries for time words, so how often the
gate fires on them is a real measurement of its false-positive rate on this
distribution -- and that rate is what decides whether the -9.94pp the ungated
multiplier cost on content queries comes back.

This is a diagnostic, not part of the pre-registered verdict. It was written
after the rungs ran and it changes no threshold in ``switch_verdicts.py``.

Clock: ``classify`` resolves "last week" against ``time.time()`` unless told
otherwise, which makes counts drift by the day. ``--now`` pins it, defaulting
to the library's own ``meta.created_at`` -- the same fix ``boost_medium.py``
needed.

Usage::

    python gate_firing.py --queries eval/queries/w2w3-holdout.jsonl \
        --db library.db --out gate-firing.json
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path

from facetmark.search.understand import classify


def load_queries(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("//"):
            rows.append(json.loads(line))
    return rows


def index_clock(db: str) -> int | None:
    """``meta.created_at``, so the same file scores the same way tomorrow."""
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        row = conn.execute("SELECT value FROM meta WHERE key = 'created_at'").fetchone()
    except sqlite3.Error:  # pragma: no cover - operator tool
        return None
    finally:
        conn.close()
    return int(row[0]) if row and str(row[0]).isdigit() else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", required=True)
    ap.add_argument("--db")
    ap.add_argument("--now", type=int)
    ap.add_argument("--out")
    args = ap.parse_args()

    now_ts = args.now or (index_clock(args.db) if args.db else None)
    rows = load_queries(Path(args.queries))

    by_type: dict[str, Counter] = {}
    rules: dict[str, Counter] = {}
    confidence: dict[str, list[float]] = {}
    examples: dict[str, list[str]] = {}
    for r in rows:
        t = str(r.get("qtype", "?"))
        u = classify(str(r.get("text", "")), now_ts=now_ts)
        by_type.setdefault(t, Counter())["n"] += 1
        by_type[t]["fired"] += int(u.is_episodic)
        if u.is_episodic:
            rules.setdefault(t, Counter()).update(u.rule_hits or ["(none)"])
            confidence.setdefault(t, []).append(u.episodic_boost)
            if t != "q_episodic" and len(examples.setdefault(t, [])) < 8:
                examples[t].append(f"{r.get('text', '')}  [{','.join(u.rule_hits)}]")

    out = {
        "queries": args.queries,
        "clock": now_ts,
        "by_type": {
            t: {
                "n": c["n"],
                "fired": c["fired"],
                "share": round(c["fired"] / c["n"], 4) if c["n"] else 0.0,
                "rules": dict(rules.get(t, {})),
                "median_multiplier": (
                    round(sorted(confidence[t])[len(confidence[t]) // 2], 4)
                    if confidence.get(t) else None
                ),
            }
            for t, c in sorted(by_type.items())
        },
        "false_positive_examples": examples,
    }
    if args.out:
        Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                                  encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
