"""P4 gate: run the whole retrieval pipeline against the real library.

Privacy contract, enforced by construction:
  * the database is ``:memory:`` -- nothing is written to disk;
  * the provider is ``MockProvider`` -- no network call is possible;
  * no page is fetched, so the index is title-only.

What this can prove: the pipeline runs on 1,688 real bookmarks, the facets
produce non-degenerate lists, the intent filter rejects things, latency is
inside the design budget.

What this CANNOT prove: retrieval quality. The mock embedder is feature
hashing over lexical tokens. Every "semantic" number below is a plumbing
check.
"""

from __future__ import annotations

import asyncio
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from facetmark.config import Settings  # noqa: E402
from facetmark.db import count_vectors, open_db  # noqa: E402
from facetmark.edges import build_edges  # noqa: E402
from facetmark.enrich import embed_content, enrich_all, filter_intents  # noqa: E402
from facetmark.enrich.vectors import embed_intents  # noqa: E402
from facetmark.importers import import_bookmarks  # noqa: E402
from facetmark.providers import MockProvider  # noqa: E402
from facetmark.search import (  # noqa: E402
    CONFIGS,
    FULL,
    build_context,
    classify,
    quick_search,
    search,
)
from facetmark.sessions import build_sessions  # noqa: E402

SRC = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0


def hr(title: str) -> None:
    print(f"\n{'=' * 68}\n{title}\n{'=' * 68}")


async def main() -> None:
    settings = Settings(
        data_dir=Path("/tmp/fm-gate"), use_mock_provider=True,
        embed_dim=64, embed_model="mock-embed", chat_model="mock-chat",
        health_enable_external=False,
    )
    provider = MockProvider(settings)
    conn = open_db(":memory:")

    hr("import")
    t0 = time.perf_counter()
    rep = import_bookmarks(conn, path=SRC)
    print(f"parsed={rep.total_parsed}  inserted={rep.inserted}  merged_dup={rep.merged_duplicates}  folders={rep.folders}")
    if LIMIT:
        conn.execute("DELETE FROM bookmark WHERE id > ?", (LIMIT,))
        conn.commit()
    n = conn.execute("SELECT count(*) AS n FROM bookmark").fetchone()["n"]
    print(f"rows in db={n}   {time.perf_counter() - t0:.1f}s")

    hr("sessions + edges")
    t0 = time.perf_counter()
    sres = build_sessions(conn)
    print(f"sessions={sres.n_sessions}  eps={sres.eps}s ({sres.eps // 60}min, {sres.reason})  coverage={sres.coverage:.1%}")
    stats = build_edges(conn, kinds=["session", "same_domain", "anchor_sibling",
                                     "supersession"])
    print(f"edges={stats.counts}   {time.perf_counter() - t0:.1f}s")

    hr("enrichment (mock, title-only -- no page was fetched)")
    t0 = time.perf_counter()
    er = await enrich_all(conn, provider=provider, settings=settings, concurrency=8)
    print(f"enriched={er.enriched} unchanged={er.skipped_unchanged} failed={er.failed} "
          f"queries={er.queries_generated}   {time.perf_counter() - t0:.1f}s")

    t0 = time.perf_counter()
    cv = await embed_content(conn, provider=provider, settings=settings)
    print(f"content vectors={cv.content_written} skipped={cv.content_skipped} "
          f"  {time.perf_counter() - t0:.1f}s")

    hr("intent self-consistency filter")
    t0 = time.perf_counter()
    ir = await filter_intents(conn, provider=provider, settings=settings)
    print(f"candidates={ir.candidates} kept={ir.kept} dropped={ir.dropped} "
          f"keep_rate={ir.keep_rate:.1%}")
    print(f"rank histogram (where the source page landed when probed): "
          f"{ir.rank_histogram}")
    print(f"bookmarks left with no kept query: {ir.bookmarks_with_none_kept}")
    print(f"{time.perf_counter() - t0:.1f}s")

    t0 = time.perf_counter()
    iv = await embed_intents(conn, provider=provider, settings=settings)
    print(f"intent vectors={iv.intent_written}   {time.perf_counter() - t0:.1f}s")
    print(f"vector totals (content, intent) = {count_vectors(conn)}")

    # -----------------------------------------------------------------
    hr("query understanding on realistic phrasings")
    probes = [
        "向量数据库怎么选",
        '"sqlite-vec" 的性能',
        "去年存的那些提示词",
        "配 Docker 那阵子存的东西",
        "github.com 上那个书签管理器",
        "3 个月前看的论文",
        "getUserMedia 权限",
    ]
    for q in probes:
        u = classify(q, now_ts=int(time.time()))
        win = (
            f" window={time.strftime('%Y-%m-%d', time.gmtime(u.time_window[0]))}"
            f"..{time.strftime('%Y-%m-%d', time.gmtime(u.time_window[1]))}"
            if u.time_window else ""
        )
        print(f"  {q:<28} -> {sorted(u.labels)}  conf={u.episodic_confidence:.1f} "
              f"rules={u.rule_hits}{win}")

    # -----------------------------------------------------------------
    hr("facet behaviour on real queries (mock embeddings: plumbing only)")
    queries = [
        "工具", "论文", "提示词", "效率工具", "机器学习",
        "vector database", "prompt engineering", "docker",
        "开源项目", "数据分析", "comparison", "agent",
    ]
    quick_ms, full_ms = [], []
    print(f"{'query':<20} {'lex_seg':>8} {'lex_tri':>8} {'content':>8} {'intent':>8} "
          f"{'quick':>7} {'full':>7}")
    for q in queries:
        t = time.perf_counter()
        qs = quick_search(conn, q, limit=20)
        quick_ms.append((time.perf_counter() - t) * 1000)
        t = time.perf_counter()
        r = await search(conn, q, limit=20, config=FULL, provider=provider,
                         settings=settings)
        full_ms.append((time.perf_counter() - t) * 1000)
        f = r.facet_sizes
        print(f"{q:<20} {f.get('lex_seg', 0):>8} {f.get('lex_tri', 0):>8} "
              f"{f.get('content', 0):>8} {f.get('intent', 0):>8} "
              f"{quick_ms[-1]:>6.1f}m {full_ms[-1]:>6.1f}m")
        _ = qs

    def pct(v, q):
        return statistics.quantiles(v, n=100)[q - 1] if len(v) > 2 else max(v)

    print(f"\nquick_search  p50={statistics.median(quick_ms):.1f}ms  "
          f"p95={pct(quick_ms, 95):.1f}ms   (budget: first paint < 20ms)")
    print(f"full search   p50={statistics.median(full_ms):.1f}ms  "
          f"p95={pct(full_ms, 95):.1f}ms   (budget: final paint < 400ms)")

    # -----------------------------------------------------------------
    hr("how much does each facet actually change the answer?")
    agree = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0}
    base_ids: dict[str, list[list[int]]] = {k: [] for k in agree}
    for q in queries:
        for name in agree:
            r = await search(conn, q, limit=10, config=CONFIGS[name],
                             provider=provider, settings=settings)
            base_ids[name].append(r.ids)
    for name in ("B", "C", "D", "E"):
        prev = "ABCD"["ABCDE".index(name) - 1]
        same_top1 = sum(
            1 for a, b in zip(base_ids[prev], base_ids[name], strict=True)
            if a[:1] == b[:1]
        )
        jac = []
        for a, b in zip(base_ids[prev], base_ids[name], strict=True):
            sa, sb = set(a), set(b)
            jac.append(len(sa & sb) / len(sa | sb) if (sa | sb) else 1.0)
        print(f"  {prev} -> {name}:  top-1 unchanged {same_top1}/{len(queries)}   "
              f"mean Jaccard@10 = {statistics.mean(jac):.2f}")

    # -----------------------------------------------------------------
    hr("anchor-then-window on a real topic")
    r = await search(conn, "提示词", limit=20, config=CONFIGS["C"],
                     provider=provider, settings=settings)
    anchors = r.ids[:10]
    sig = build_context(conn, anchors=anchors, candidates=r.ids,
                        episodic_confidence=0.6)
    if sig.window:
        lo, hi = sig.window
        print(f"anchors: {len(anchors)}")
        print(f"derived window: {time.strftime('%Y-%m-%d', time.gmtime(lo))} .. "
              f"{time.strftime('%Y-%m-%d', time.gmtime(hi))}  "
              f"({(hi - lo) / 86400:.0f} days)")
        span = conn.execute(
            "SELECT min(date_added) a, max(date_added) b FROM bookmark "
            "WHERE date_added IS NOT NULL"
        ).fetchone()
        print(f"library span: {(span['b'] - span['a']) / 86400:.0f} days  -> the window "
              f"is {(hi - lo) / (span['b'] - span['a']):.1%} of it")
        print(f"session peers found: {len(sig.session_peers)}  "
              f"folder peers: {len(sig.folder_peers)}")
    else:
        print("no window derived (anchors too sparse)")

    # -----------------------------------------------------------------
    hr("cold layer on the real library")
    from facetmark.search import cold_bookmark_ids
    cold = cold_bookmark_ids(conn, age_days=365)
    older = conn.execute(
        "SELECT count(*) n FROM bookmark WHERE date_added < ?",
        (int(time.time()) - 365 * 86400,),
    ).fetchone()["n"]
    print(f"older than 365 days: {older}")
    print(f"of those, meeting ALL three demotion conditions: {len(cold)}")
    print("(condition 3 needs a supersession edge or a health verdict; no health "
          "probe has run, so this is supersession-only)")

    conn.close()


asyncio.run(main())
