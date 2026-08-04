"""Does the remedy the docs recommend -- backfill, then re-run ``facetmark index``
-- actually repair a bridged library?

The documentation told people to do this. Nothing checked that the pipeline
agrees. Every stage of ``index_all`` decides for itself what work is pending,
and each of those decisions is a query the bridge had never been run against.
This probe asks each stage, against the real bridged library from the
round-trip experiment, what it would do -- without calling a model, and on a
copy so the artifact is untouched.

Stages and the question each is asked:

* fetch      -- ``pending_targets``: would it re-request pages karakeep already
                gave us bodies for? (It must not: those bodies are the user's,
                and re-fetching them is both slow and possibly different.)
* enrich     -- ``targets``: are bridge-written rows recognised as stale?
                ``enrichment.source_hash`` is the literal string ``karakeep``,
                which cannot equal a body hash or a title hash, so the answer
                should be "all of them" -- but "should" is why this file exists.
* embed      -- ``content_work``: are the vectors currently considered current
                (they were built from the bridged text, so yes -- this is the
                "a vector can exist and be wrong" trap), and do they become
                pending the moment the enrichment changes?
* sessions   -- do they build at all from karakeep's ``createdAt``?
* edges      -- likewise, and how does the rebuilt graph compare to the source?

Note on transactions: :func:`facetmark.db.connect` opens with
``isolation_level=None``, i.e. autocommit. The mutation used to test the
embedder's staleness logic is therefore wrapped in an explicit
``BEGIN``/``ROLLBACK``, and the probe asserts afterwards that the row count it
changed is back where it started. A bare ``conn.rollback()`` is a no-op here
and silently keeps the change -- which is exactly what the first version of
this file did.

Usage::

    python scripts/karakeep_remedy_probe.py --db bridged.db --json out.json
    python scripts/karakeep_remedy_probe.py --db source.db --graph-only
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from facetmark import edges as edgemod  # noqa: E402
from facetmark import sessions as sessmod  # noqa: E402
from facetmark.db import connect  # noqa: E402
from facetmark.enrich.pipeline import targets as enrich_targets  # noqa: E402
from facetmark.enrich.vectors import _content_rows, content_text, content_work  # noqa: E402
from facetmark.fetch.store import pending_targets  # noqa: E402


def counts(conn: sqlite3.Connection) -> dict:
    def one(sql: str) -> int:
        return conn.execute(sql).fetchone()[0]

    return {
        "bookmark": one("SELECT COUNT(*) FROM bookmark"),
        "content": one("SELECT COUNT(*) FROM content"),
        "content_with_body": one("SELECT COUNT(*) FROM content WHERE body_hash IS NOT NULL"),
        "enrichment": one("SELECT COUNT(*) FROM enrichment"),
        "enrichment_karakeep": one("SELECT COUNT(*) FROM enrichment WHERE source_hash='karakeep'"),
        "vec_content": one("SELECT COUNT(*) FROM vec_content"),
        "vec_intent": one("SELECT COUNT(*) FROM vec_intent"),
        "session": one("SELECT COUNT(*) FROM session"),
        "edge": one("SELECT COUNT(*) FROM edge"),
    }


def _graph(conn: sqlite3.Connection) -> dict:
    conn.execute("DELETE FROM edge")
    conn.execute("DELETE FROM bookmark_session")
    conn.execute("DELETE FROM session")
    sr = sessmod.build_sessions(conn)
    es = edgemod.build_edges(conn)
    return {
        "sessions": {
            "built": sr.n_sessions, "assigned": sr.n_assigned,
            "coverage": round(sr.coverage, 4), "eps": sr.eps, "reason": sr.reason,
        },
        "edges": {"total": es.total, "counts": es.counts, "skipped": es.skipped},
    }


def _texts(conn: sqlite3.Connection) -> dict[int, str]:
    """The exact string facet 1 embeds, per bookmark, keyed by id."""
    from facetmark.db import jload

    out: dict[int, str] = {}
    for r in _content_rows(conn, None):
        out[r["id"]] = content_text(
            title=r["title"] or "", summary=r["summary"] or "",
            topics=jload(r["topics"], []), entities=jload(r["entities"], []),
            body=r["body_text"] or "",
        )
    return out


def attribute(bridged: Path, source: Path) -> dict:
    """Is the enrichment mapping the *whole* explanation for the vector drift?

    Build a third library -- the bridged one with the source library's
    enrichment rows transplanted in, i.e. what a re-enrichment would produce if
    it reproduced the source exactly -- and compare the embedder's input string
    against the source, character for character. If every page matches, then
    nothing outside ``enrichment`` contributed to the drift, and the remedy
    repairs the input completely. If some do not, whatever is left is a second
    fidelity gap the round-trip experiment did not isolate.
    """
    tmpdir = Path(tempfile.mkdtemp(prefix="attrib-"))
    b = tmpdir / "remedied.db"
    s = tmpdir / "source.db"
    shutil.copy(bridged, b)
    shutil.copy(source, s)
    cb, cs = connect(b), connect(s)
    try:
        base_b, base_s = _texts(cb), _texts(cs)
        shared = sorted(set(base_b) & set(base_s))
        before_same = sum(1 for i in shared if base_b[i] == base_s[i])

        # Transplant the source enrichment, which is what a faithful
        # re-enrichment would land on, and re-ask.
        cb.execute("BEGIN")
        rows = cs.execute(
            "SELECT bookmark_id, summary, key_points, entities, topics, utility,"
            " content_type, source_hash, model, created_at FROM enrichment"
        ).fetchall()
        cb.execute("DELETE FROM enrichment")
        cb.executemany(
            "INSERT INTO enrichment(bookmark_id, summary, key_points, entities, topics,"
            " utility, content_type, source_hash, model, created_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?)",
            [tuple(r) for r in rows],
        )
        after_b = _texts(cb)
        cb.execute("COMMIT")
        after_same = sum(1 for i in shared if after_b[i] == base_s[i])
        differ = [i for i in shared if after_b[i] != base_s[i]]

        # Where a residual difference survives, say which field it is in.
        residual: dict[str, int] = {}
        for i in differ[:200]:
            tb = cb.execute("SELECT title FROM bookmark WHERE id=?", (i,)).fetchone()[0] or ""
            ts = cs.execute("SELECT title FROM bookmark WHERE id=?", (i,)).fetchone()[0] or ""
            bb = cb.execute(
                "SELECT body_text FROM content WHERE bookmark_id=?", (i,)).fetchone()
            bs = cs.execute(
                "SELECT body_text FROM content WHERE bookmark_id=?", (i,)).fetchone()
            key = "title" if tb != ts else (
                "body" if (bb["body_text"] if bb else "") != (bs["body_text"] if bs else "")
                else "other")
            residual[key] = residual.get(key, 0) + 1

        return {
            "shared_bookmarks": len(shared),
            "identical_embed_text_before_remedy": before_same,
            "identical_embed_text_after_remedy": after_same,
            "residual_differences": len(differ),
            "residual_by_field": residual,
        }
    finally:
        cb.close()
        cs.close()
        shutil.rmtree(tmpdir, ignore_errors=True)


def probe(db: Path, *, graph_only: bool = False) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="remedy-")) / "probe.db"
    shutil.copy(db, tmp)
    conn = connect(tmp)
    out: dict = {"db": db.name, "before": counts(conn)}
    try:
        # Graph first: it writes, and everything below must see a pristine library.
        out["rebuild_graph"] = _graph(conn)
        if graph_only:
            out["after"] = counts(conn)
            return out

        # --- fetch stage ---------------------------------------------------
        pend_fetch = pending_targets(conn, refetch=False)
        have_body = {
            r[0] for r in conn.execute(
                "SELECT bookmark_id FROM content WHERE body_hash IS NOT NULL")
        }
        out["fetch"] = {
            "would_request": len(pend_fetch),
            # The number that matters: bridge-supplied bodies must be left alone.
            "would_refetch_bridged_bodies":
                sum(1 for bid, _u, _t in pend_fetch if bid in have_body),
            "indexable": conn.execute(
                "SELECT COUNT(*) FROM bookmark WHERE indexable=1 AND privacy_skipped=0"
            ).fetchone()[0],
        }

        # --- enrich stage --------------------------------------------------
        tg = enrich_targets(conn, force=False)
        karakeep_ids = {
            r[0] for r in conn.execute(
                "SELECT bookmark_id FROM enrichment WHERE source_hash='karakeep'")
        }
        picked = {t.bookmark_id for t in tg}
        out["enrich"] = {
            "would_re_enrich": len(tg),
            "bridge_rows_total": len(karakeep_ids),
            "bridge_rows_picked_up": len(karakeep_ids & picked),
            "bridge_rows_skipped": len(karakeep_ids - picked),
        }

        # --- embed stage, as things stand ------------------------------------
        pending, empty, current = content_work(conn, force=False)
        out["embed_before_enrich"] = {"pending": len(pending), "empty": empty, "current": current}

        # --- embed stage, once the enrichment moves --------------------------
        # Simulate what re-enrichment does to the embedder's input without
        # paying for a model: change topics on every bridge row and re-ask. If
        # the fingerprint logic works, the whole library goes pending.
        n_before = out["before"]["enrichment_karakeep"]
        conn.execute("BEGIN")
        conn.execute(
            "UPDATE enrichment SET topics=?, source_hash=? WHERE source_hash='karakeep'",
            (json.dumps(["probe-sentinel"]), "probe"),
        )
        pending2, empty2, current2 = content_work(conn, force=False)
        conn.execute("ROLLBACK")
        n_after = conn.execute(
            "SELECT COUNT(*) FROM enrichment WHERE source_hash='karakeep'").fetchone()[0]
        out["embed_after_enrich_changes"] = {
            "pending": len(pending2), "empty": empty2, "current": current2,
            "rollback_restored": n_after == n_before,
        }
        out["after"] = counts(conn)
        return out
    finally:
        conn.close()
        shutil.rmtree(tmp.parent, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, required=True)
    ap.add_argument("--graph-only", action="store_true",
                    help="Only rebuild sessions/edges (for a source-library baseline).")
    ap.add_argument("--attribute", type=Path,
                    help="Source library to attribute the embed-text drift against.")
    ap.add_argument("--json", type=Path)
    a = ap.parse_args()
    if a.attribute:
        res = {"db": a.db.name, "attribution": attribute(a.db, a.attribute)}
    else:
        res = probe(a.db, graph_only=a.graph_only)
    text = json.dumps(res, ensure_ascii=False, indent=2)
    print(text)
    if a.json:
        a.json.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
