"""Merge query chunks into one set, with the de-duplication rule written down.

The generator runs one seed at a time because a single long run costs more when
it fails than four short ones do. Four chunks then have to become one query set,
and *how* they are merged is a measurement decision, not a file operation:

* **Two chunks can draw the same page.** Seeds are independent, so the same
  target turns up in more than one chunk a few times per hundred. Keeping both
  queries would weight that page twice in every recall number computed on the
  set - once because it was sampled, once because it was sampled again.
* **The unit of duplication is ``(target, qtype)``, not the target.** One page
  legitimately carries a ``q_content``, a ``q_vague`` and a ``q_episodic``
  query; that is the design, and the strata read of D-C depends on it. What is
  not legitimate is two chunks each writing a ``q_content`` query for the same
  page, which is two draws of one cell.
* **Identical text is dropped even across different targets.** Two pages about
  the same thing can produce the same sentence, and then the "correct" answer
  is a coin flip that no ranker can win. Dropping both would be tidier; the
  first one is kept because the second is the one that has no claim.

Every drop is counted and printed, and the ``//`` provenance headers from all
chunks are carried into the output, so the merged file still says which seeds
and thresholds produced it.

This runs *before* anything is measured on the set. Merging after a first look
at the results would let the rule be chosen for its effect on the numbers.

Usage::

    python merge_queries.py --out merged.jsonl chunk1.jsonl chunk2.jsonl ...
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

_WS = re.compile(r"\s+")


def text_key(text: str) -> str:
    """Whitespace-insensitive identity for a query.

    CJK text carries no spaces and Latin text carries several kinds, so a raw
    string compare would call two identical questions different because one of
    them came back from the model with a full-width space in it.
    """
    return _WS.sub(" ", text).strip().casefold()


def read_chunk(path: Path) -> tuple[list[dict], list[str]]:
    """Records and the ``//`` header lines, which are provenance and are kept."""
    rows: list[dict] = []
    header: list[str] = []
    for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
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


def merge(chunks: list[tuple[str, list[dict]]]) -> tuple[list[dict], Counter]:
    """First occurrence wins, in the order the chunks were given.

    Returns the kept rows and a counter of why rows were dropped, so the caller
    can print it rather than have it disappear into a length difference.
    """
    kept: list[dict] = []
    seen_pair: dict[tuple[str, str], str] = {}
    seen_text: dict[str, str] = {}
    dropped: Counter = Counter()
    for name, rows in chunks:
        for row in rows:
            pair = (str(row.get("target_url") or ""), str(row.get("qtype") or ""))
            tkey = text_key(str(row.get("text") or ""))
            if not tkey:
                dropped["empty text"] += 1
                continue
            if pair in seen_pair:
                dropped[f"repeat of ({pair[1]}) target already in {seen_pair[pair]}"] += 1
                continue
            if tkey in seen_text:
                dropped[f"text already in {seen_text[tkey]}"] += 1
                continue
            seen_pair[pair] = name
            seen_text[tkey] = name
            kept.append({**row, "chunk": name})
    return kept, dropped


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("chunks", nargs="+", help="query JSONL files, in priority order")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    loaded: list[tuple[str, list[dict]]] = []
    headers: list[str] = []
    for spec in args.chunks:
        path = Path(spec)
        rows, header = read_chunk(path)
        loaded.append((path.name, rows))
        headers += [f"// from {path.name}: {h[2:].strip()}" for h in header]
        print(f"read {len(rows):4d} from {path.name}")

    kept, dropped = merge(loaded)
    total = sum(len(rows) for _, rows in loaded)

    lines = [*headers, f"// merged {len(args.chunks)} chunks: {total} -> {len(kept)} queries"]
    lines += [json.dumps(r, ensure_ascii=False) for r in kept]
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\nwrote {len(kept)} of {total} -> {args.out}")
    for reason, n in dropped.most_common():
        print(f"  dropped {n:3d}: {reason}")
    qtypes = Counter(r.get("qtype", "?") for r in kept)
    subs = Counter(r.get("subtype") or r.get("note") or ""
                   for r in kept if r.get("qtype") == "q_episodic")
    targets = Counter(r.get("target_url") for r in kept)
    print("  qtype:    " + json.dumps(dict(qtypes), ensure_ascii=False))
    print("  episodic: " + json.dumps(dict(subs), ensure_ascii=False))
    print(f"  distinct targets: {len(targets)}; "
          f"max queries on one target: {max(targets.values()) if targets else 0}")


if __name__ == "__main__":
    main()
