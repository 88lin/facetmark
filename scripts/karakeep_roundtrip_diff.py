"""Where exactly did the bridged library stop being the source library?

The round-trip verdict says the two libraries do not return the same lists.
This walks the causal chain backwards from that symptom to the field that
caused it, and writes every number the results write-up quotes:

1. candidate pool -- do both sides even have the same rows to rank?
2. bodies         -- is the text karakeep sent back byte-identical?
3. vectors        -- are the stored content vectors identical, and if not, how
                     far apart, split by whether the page has a body?
4. enrichment     -- field by field, how many of the embedder's four non-body
                     inputs survived the round trip?

Usage::

    python scripts/karakeep_roundtrip_diff.py --source source.db \\
        --bridged bridged.db --json diff.json
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import struct
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from facetmark.db import connect  # noqa: E402


def _vectors(conn: sqlite3.Connection) -> dict[int, bytes]:
    return {
        int(r["bookmark_id"]): bytes(r["embedding"])
        for r in conn.execute("SELECT bookmark_id, embedding FROM vec_content")
    }


def _cos(a: bytes, b: bytes) -> float:
    n = len(a) // 4
    va = struct.unpack(f"<{n}f", a)
    vb = struct.unpack(f"<{n}f", b)
    dot = sum(x * y for x, y in zip(va, vb, strict=True))
    na = sum(x * x for x in va) ** 0.5
    nb = sum(y * y for y in vb) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def _quantiles(xs: list[float]) -> dict:
    if not xs:
        return {}
    s = sorted(xs)

    def q(p: float) -> float:
        return round(s[min(len(s) - 1, int(p * len(s)))], 6)

    return {"n": len(s), "min": round(s[0], 6), "p05": q(0.05), "median": q(0.5),
            "p95": q(0.95), "max": round(s[-1], 6)}


def run(source: Path, bridged: Path) -> dict:
    cs, cb = connect(source), connect(bridged)
    try:
        out: dict = {}

        def counts(c: sqlite3.Connection) -> dict:
            one = lambda sql: c.execute(sql).fetchone()[0]  # noqa: E731
            return {
                "bookmark": one("SELECT COUNT(*) FROM bookmark"),
                "content_rows": one("SELECT COUNT(*) FROM content"),
                "content_with_body": one(
                    "SELECT COUNT(*) FROM content WHERE COALESCE(body_text,'')<>''"),
                "enrichment": one("SELECT COUNT(*) FROM enrichment"),
                "vec_content": one("SELECT COUNT(*) FROM vec_content"),
                "vec_intent": one("SELECT COUNT(*) FROM vec_intent"),
                "session": one("SELECT COUNT(*) FROM session"),
                "edge": one("SELECT COUNT(*) FROM edge"),
            }

        out["pool"] = {"source": counts(cs), "bridged": counts(cb)}

        # --- bodies ---------------------------------------------------------
        bs = {int(r["bookmark_id"]): (r["body_text"] or "")
              for r in cs.execute("SELECT bookmark_id, body_text FROM content")}
        bb = {int(r["bookmark_id"]): (r["body_text"] or "")
              for r in cb.execute("SELECT bookmark_id, body_text FROM content")}
        both_body = [i for i in bs.keys() & bb.keys() if bs[i] and bb[i]]
        out["bodies"] = {
            "shared_nonempty": len(both_body),
            "identical": sum(1 for i in both_body if bs[i] == bb[i]),
            "differ": sum(1 for i in both_body if bs[i] != bb[i]),
        }

        # --- vectors --------------------------------------------------------
        vs, vb = _vectors(cs), _vectors(cb)
        shared = sorted(vs.keys() & vb.keys())
        has_body = {i for i in shared if bs.get(i) or bb.get(i)}
        identical = sum(1 for i in shared if vs[i] == vb[i])
        cos_body = [_cos(vs[i], vb[i]) for i in shared if i in has_body]
        cos_none = [_cos(vs[i], vb[i]) for i in shared if i not in has_body]
        out["vectors"] = {
            "shared": len(shared),
            "byte_identical": identical,
            "cosine_with_body": _quantiles(cos_body),
            "cosine_without_body": _quantiles(cos_none),
        }

        # --- enrichment fields ----------------------------------------------
        es = {int(r["bookmark_id"]): r for r in cs.execute(
            "SELECT bookmark_id, summary, topics, entities FROM enrichment")}
        eb = {int(r["bookmark_id"]): r for r in cb.execute(
            "SELECT bookmark_id, summary, topics, entities FROM enrichment")}
        common = sorted(es.keys() & eb.keys())
        fields = {}
        for f in ("summary", "topics", "entities"):
            same = sum(1 for i in common if (es[i][f] or "") == (eb[i][f] or ""))
            fields[f] = {"same": same, "of": len(common),
                         "pct": round(100.0 * same / len(common), 2) if common else 0.0}
        out["enrichment_fields"] = fields
        out["enrichment_rows"] = {"source": len(es), "bridged": len(eb), "common": len(common)}

        # The resolution of the keyword line, which is what actually moved.
        # karakeep tags are folder-level labels; model topics are per-page.
        def vocab(rows) -> dict:
            terms: Counter[str] = Counter()
            per = []
            empty_topics = empty_entities = 0
            for r in rows.values():
                t = json.loads(r["topics"] or "[]")
                e = json.loads(r["entities"] or "[]")
                per.append(len(t) + len(e))
                terms.update(t)
                terms.update(e)
                empty_topics += int(not t)
                empty_entities += int(not e)
            return {
                "pages": len(per),
                "distinct_terms": len(terms),
                "mean_terms_per_page": round(sum(per) / len(per), 2) if per else 0.0,
                "pages_with_no_topics": empty_topics,
                "pages_with_no_entities": empty_entities,
                "most_common": terms.most_common(5),
            }

        out["keyword_line"] = {"source": vocab(es), "bridged": vocab(eb)}

        # One worked example, so the write-up can show the substitution rather
        # than only counting it.
        example = None
        for i in common:
            if json.loads(es[i]["topics"] or "[]") and json.loads(eb[i]["topics"] or "[]"):
                url = cs.execute("SELECT url FROM bookmark WHERE id=?", (i,)).fetchone()[0]
                example = {
                    "url": url,
                    "source_topics": json.loads(es[i]["topics"] or "[]"),
                    "source_entities": json.loads(es[i]["entities"] or "[]"),
                    "bridged_topics": json.loads(eb[i]["topics"] or "[]"),
                    "bridged_entities": json.loads(eb[i]["entities"] or "[]"),
                }
                break
        out["example"] = example
        return out
    finally:
        cs.close()
        cb.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--bridged", type=Path, required=True)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args()
    res = run(a.source, a.bridged)
    text = json.dumps(res, ensure_ascii=False, indent=2)
    print(text)
    if a.json:
        a.json.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
