"""Does facet 2 see anything facet 1 does not?

W4's read of 50 intent queries (``docs/w4-intent-read.md``) found that most of
the usable ones are the page's own title in other words. If that is what the
intent space mostly holds, an intent vector is a paraphrase of the content
vector, and a KNN over intent space should land on the bookmarks a KNN over
content space already found. That would be a mechanical explanation for W1's
result that switching F2 on brought correlated noise and no new signal.

This measures it directly, with no model and no query set: probe both facets
with the *same* vector -- a bookmark's own content vector -- drop the probe
document itself, and count how much of the two neighbourhoods coincide.

Two reference points are printed beside it:

* ``random``  -- k/N, the overlap two independent facets would produce;
* ``lex_seg`` -- the segmented lexical facet, probed with the document's
  title. Its probe is a string rather than a vector, so this is a rough
  reference for "what a genuinely different facet scores", not a matched
  control.

What the numbers cannot say: high overlap does not prove the intent facet is
useless, because the two facets are probed here with a *document* vector,
while a real search probes them with a *question*. It does say that on this
library the second facet's neighbourhood is largely the first one's.

Usage:
    python scripts/facet_overlap.py --db path/to/library.db [--n 300] [--k 10]
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from facetmark.db import connect, unpack_vector, vec_tables_exist  # noqa: E402
from facetmark.search.lexical import lexical_lists  # noqa: E402
from facetmark.search.vectors import content_list, intent_list  # noqa: E402


def _probe_ids(conn, n: int, seed: int) -> list[int]:
    ids = sorted(int(r[0]) for r in conn.execute("SELECT bookmark_id FROM vec_content"))
    if n >= len(ids):
        return ids
    return sorted(random.Random(seed).sample(ids, n))


def _vector(conn, bookmark_id: int) -> list[float] | None:
    row = conn.execute(
        "SELECT embedding FROM vec_content WHERE bookmark_id=?", (bookmark_id,)
    ).fetchone()
    if row is None:
        return None
    blob = row[0]
    return unpack_vector(bytes(blob))


def _without(ids: list[int], drop: int, k: int) -> list[int]:
    return [i for i in ids if i != drop][:k]


def overlap(a: list[int], b: list[int], k: int) -> float:
    """Fraction of the first list's top-k that the second list also holds."""
    if not a:
        return 0.0
    return len(set(a[:k]) & set(b[:k])) / min(k, len(a))


def run(db_path: str, n: int, k: int, seed: int) -> dict:
    conn = connect(db_path)
    if not vec_tables_exist(conn):
        raise SystemExit(f"{db_path} has no vector tables")

    total = conn.execute("SELECT count(*) AS n FROM vec_content").fetchone()["n"]
    n_intent = conn.execute("SELECT count(*) AS n FROM vec_intent").fetchone()["n"]
    probes = _probe_ids(conn, n, seed)

    rows = []
    for bid in probes:
        vec = _vector(conn, bid)
        if vec is None:
            continue
        title = conn.execute("SELECT title FROM bookmark WHERE id=?", (bid,)).fetchone()
        title = (title["title"] or "") if title else ""

        c_raw = content_list(conn, vec, limit=k + 1)
        i_raw = intent_list(conn, vec, limit=k + 1)
        con = _without(c_raw, bid, k)
        itt = _without(i_raw, bid, k)

        lex = lexical_lists(conn, title, limit=k + 1).get("lex_seg", []) if title else []
        lex = _without(list(lex), bid, k)

        rows.append(
            {
                "id": bid,
                "self_rank_content": (c_raw.index(bid) + 1) if bid in c_raw else None,
                "self_rank_intent": (i_raw.index(bid) + 1) if bid in i_raw else None,
                "overlap_1": overlap(con, itt, 1),
                "overlap_5": overlap(con, itt, 5),
                "overlap_k": overlap(con, itt, k),
                "overlap_k_lex": overlap(con, lex, k) if lex else None,
                "n_lex": len(lex),
            }
        )

    def mean(key: str) -> float:
        vals = [r[key] for r in rows if r[key] is not None]
        return round(statistics.fmean(vals), 4) if vals else 0.0

    lex_rows = [r for r in rows if r["overlap_k_lex"] is not None]
    out = {
        "db": db_path,
        "bookmarks_with_content_vector": total,
        "intent_vectors": n_intent,
        "probes": len(rows),
        "k": k,
        "seed": seed,
        "intent_vs_content": {
            "overlap_at_1": mean("overlap_1"),
            "overlap_at_5": mean("overlap_5"),
            f"overlap_at_{k}": mean("overlap_k"),
            "probes_with_zero_overlap": sum(1 for r in rows if r["overlap_k"] == 0.0),
            "probes_with_half_or_more": sum(1 for r in rows if r["overlap_k"] >= 0.5),
            "self_found_in_intent_topk": sum(
                1 for r in rows if r["self_rank_intent"] is not None
            ),
        },
        "reference_lex_seg_vs_content": {
            f"overlap_at_{k}": round(
                statistics.fmean([r["overlap_k_lex"] for r in lex_rows]), 4
            )
            if lex_rows
            else None,
            "probes": len(lex_rows),
        },
        "reference_random": round(k / total, 4) if total else None,
        "rows": rows,
    }
    conn.close()
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", required=True)
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--seed", type=int, default=20260803)
    ap.add_argument("--json", default=None, help="write the full record here")
    args = ap.parse_args()

    out = run(args.db, args.n, args.k, args.seed)
    if args.json:
        Path(args.json).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    summary = {k: v for k, v in out.items() if k != "rows"}
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
