"""Make a freshly generated query file safe to hand to the eval harness.

``gen_queries.py`` writes what the generator knows; the harness needs a
slightly different shape, and a query file that is wrong in a small way costs a
whole ablation run to find out. Three jobs:

* Copy ``subtype`` into ``note``. ``load_query_file`` only carries ``note``
  through to ``EvalQuery``, and the ``q_episodic`` strata (year / relative /
  anchor) are the whole reason the subtype was recorded -- without this the
  stratified read of D-C has no labels to group by.
* Resolve every ``target_url`` against the library. The harness treats a
  missing target as a hard error mid-run, which is the worst time to find out.
  Report them here instead, and optionally drop them.
* Print the distribution the report will have to quote, so a skew is visible
  before an hour of model time goes into measuring it.

Usage::

    python finalize_queries.py --in queries.jsonl --out queries.final.jsonl \
        --db /workspace/eval-data/facetmark.db
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from facetmark.db import open_db
from facetmark.normalize import normalize_url


def load(path: Path) -> tuple[list[dict], list[str]]:
    """Records plus the ``//`` header the generator writes, which is kept.

    Those lines carry the generator's seed and thresholds. They are the only
    record of how the query set was made, and ``load_query_file`` skips them,
    so there is no reason to strip them out of the finalised file.
    """
    rows: list[dict] = []
    header: list[str] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        if line.startswith("//"):
            header.append(line)
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:  # pragma: no cover - operator tool
            raise SystemExit(f"{path}:{i}: not JSON: {exc}") from exc
    return rows, header


def url_index(db: str) -> dict[str, int]:
    """The same key ``load_query_file`` will use: ``bookmark.url_norm``.

    Matching on anything else here would let a query file pass this check and
    still blow up inside the harness.
    """
    conn = open_db(db)
    try:
        rows = conn.execute("SELECT id, url_norm FROM bookmark").fetchall()
    finally:
        conn.close()
    return {str(dict(r)["url_norm"]): int(dict(r)["id"]) for r in rows}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", dest="dst", required=True)
    ap.add_argument("--db", default="/workspace/eval-data/facetmark.db")
    ap.add_argument("--drop-unresolvable", action="store_true",
                    help="drop rows whose target is not in the library instead of failing")
    args = ap.parse_args()

    rows, header = load(Path(args.src))
    index = url_index(args.db)

    kept: list[dict] = []
    missing: list[dict] = []
    for row in rows:
        sub = row.get("subtype") or row.get("note") or ""
        if sub:
            row["note"] = sub
            row["subtype"] = sub
        url = str(row.get("target_url") or "")
        hit = index.get(normalize_url(url).normalized) if url else None
        if hit is None:
            missing.append(row)
            continue
        row["target_id"] = hit
        kept.append(row)

    if missing and not args.drop_unresolvable:
        for row in missing[:10]:
            print(f"  unresolved: {row.get('target_url')!r}")
        raise SystemExit(
            f"{len(missing)}/{len(rows)} targets are not in {args.db}; "
            "pass --drop-unresolvable to write the rest anyway"
        )

    lines = [*header, f"// finalised from {args.src} against {args.db}"]
    lines += [json.dumps(r, ensure_ascii=False) for r in kept]
    Path(args.dst).write_text("\n".join(lines) + "\n", encoding="utf-8")

    qtypes = Counter(r.get("qtype", "?") for r in kept)
    subs = Counter(r.get("note", "") for r in kept if r.get("qtype") == "q_episodic")
    targets = Counter(r.get("target_url") for r in kept)
    print(f"wrote {len(kept)} queries -> {args.dst}"
          + (f" (dropped {len(missing)} unresolvable)" if missing else ""))
    print("  qtype:    " + json.dumps(dict(qtypes), ensure_ascii=False))
    print("  episodic: " + json.dumps(dict(subs), ensure_ascii=False))
    print(f"  distinct targets: {len(targets)}; "
          f"max queries on one target: {max(targets.values()) if targets else 0}")
    lens = sorted(len(r.get("text", "")) for r in kept)
    if lens:
        print(f"  text chars: min {lens[0]} / median {lens[len(lens) // 2]} / max {lens[-1]}")


if __name__ == "__main__":
    main()
