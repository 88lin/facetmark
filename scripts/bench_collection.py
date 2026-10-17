"""Cloud-only 200k collection acceptance. No real bookmarks or model calls."""
from __future__ import annotations

import json
import os
import tempfile
import time
import tracemalloc
from pathlib import Path
from types import SimpleNamespace

from large_collection_fixture import populate

from facetmark.collection import CollectionScope
from facetmark.db import open_db
from facetmark.processing import pending_batch, preview, snapshot
from facetmark.workbench import browse, browse_facets


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise SystemExit("Run scale validation in GitHub Actions only")
    evidence = {"records": 200_000, "timings_ms": {}}
    with tempfile.TemporaryDirectory(prefix="facetmark-scale-") as temporary:
        conn = open_db(Path(temporary) / "scale.db")
        started = time.perf_counter()
        populate(conn)
        evidence["build_seconds"] = round(time.perf_counter() - started, 3)
        def measure(name, fn):
            started = time.perf_counter()
            result = fn()
            duration = (time.perf_counter() - started) * 1000
            evidence["timings_ms"][name] = round(duration, 2)
            assert duration < 5000, f"{name} took {duration:.0f}ms"
            return result
        first = measure("first_page", lambda: browse(conn, limit=30))
        last = measure("deep_page", lambda: browse(conn, offset=199980, limit=30))
        assert first["total"] == last["total"] == 200000
        assert len(first["items"]) == 30 and len(last["items"]) == 20
        assert not last["has_more"]
        assert first["summary_counts"] == {"total": 200000, "done": 40000, "pending": 160000, "failed": 0}
        found = measure("full_keyword_scope", lambda: browse(conn, q="needle", limit=30))
        assert found["total"] == 20000
        for order in ("oldest", "title", "domain"):
            measure("sort_" + order, lambda order=order: browse(conn, sort=order, offset=199980, limit=30))
        categories = measure("category_directory", lambda: browse_facets(conn, "folders", q="Scale/4095"))
        assert categories["items"][0]["value"] == "Scale/4095"
        scope = CollectionScope(exclude_ids=[1, 2])
        assert measure("scope_preview", lambda: preview(conn, scope=scope, ids=None, mode="summarize", force=True)) == 199998
        job = SimpleNamespace(id="scale-job", scope=scope.model_dump(), bookmark_ids=None, mode="summarize", force=True, limit=None, snapshot_ready=False)
        tracemalloc.start()
        measure("durable_snapshot", lambda: snapshot(conn, job))
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        assert job.items_total == 199998
        assert len(pending_batch(conn, job)) == 64
        assert 1 not in pending_batch(conn, job) and 2 not in pending_batch(conn, job)
        assert peak < 16 * 1024 * 1024, peak
        evidence["snapshot_python_peak_bytes"] = peak
        evidence["snapshot_items"] = job.items_total
        evidence["pending_batch_size"] = 64
        conn.close()
    output = Path("frontend/visual-evidence/collection-200k.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
