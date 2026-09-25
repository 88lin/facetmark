"""Time the hot paths on a library big enough to have an opinion.

Everything in memory: this is a CPU-and-SQL benchmark, and a disk-backed file
would measure the disk. Sizes are tunable because the interesting question is
not "how slow" but "slow in N".
"""
from __future__ import annotations

import asyncio
import random
import statistics
import sys
import time

from facetmark.config import Settings
from facetmark.db import open_db
from facetmark.search.pipeline import FULL, quick_search, search
from facetmark.service import suggest_query_syntax, timeline
from facetmark.text import sync_fts

N = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
NOW = 1788400000
random.seed(7)

WORDS = (
    "postgres", "index", "types", "kafka", "rebalancing", "sqlite", "fts5",
    "tokenizer", "vector", "embedding", "rust", "ownership", "borrow", "docker",
    "compose", "networking", "privacy", "encryption", "signal", "matrix",
    "crdt", "practice", "notes", "索引", "类型", "效率", "工具", "提示词",
    "检索", "向量",
)
DOMAINS = [f"blog{i}.example" for i in range(200)] + [
    "github.com", "sqlite.org", "news.ycombinator.com", "facebook.com"]
TAGS = ("work", "reading", "rust", "shopping", "archive", "later")


def build(n: int):
    conn = open_db(":memory:")
    t0 = time.perf_counter()
    for i in range(1, n + 1):
        dom = random.choice(DOMAINS)
        title = " ".join(random.sample(WORDS, 5))
        tags = random.sample(TAGS, random.randint(0, 2))
        conn.execute(
            "INSERT INTO bookmark(id,url,url_norm,url_hash,title,folder,folder_depth,"
            "host,domain,date_added,source,indexable,open_count,tags,created_at,updated_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (i, f"https://{dom}/p{i}", f"https://{dom}/p{i}", f"h{i}", title,
             random.choice(("", "study", "work/deep")), 1, dom, dom,
             NOW - random.randint(0, 900) * 86400, "api", 1,
             random.choice((0, 0, 0, 1, 3, 12)),
             '["' + '","'.join(tags) + '"]' if tags else "[]", NOW, NOW),
        )
        sync_fts(conn, i, title=title, body=title + " " + " ".join(random.sample(WORDS, 8)))
    conn.commit()
    return conn, time.perf_counter() - t0


def bench(label, fn, reps=5):
    # One warm-up: the first call pays for jieba's dictionary and SQLite's page
    # cache, and neither is what any of these measurements is about.
    fn()
    times = []
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t) * 1000)
    print(f"  {label:52} {statistics.median(times):8.1f} ms   "
          f"(min {min(times):.1f}, max {max(times):.1f})")


conn, secs = build(N)
rows = conn.execute("SELECT COUNT(*) FROM bookmark").fetchone()[0]
print(f"library: {rows} bookmarks, built in {secs:.1f}s\n")

st = Settings(data_dir="/tmp/fmbench", use_mock_provider=True, embed_dim=64,
              embed_model="mock-embed", chat_model="mock-chat",
              health_enable_external=False)

print("=== first paint (quick_search) ===")
bench("plain text            'postgres index'", lambda: quick_search(conn, "postgres index", settings=st))
bench("one filter            'postgres domain:github.com'",
      lambda: quick_search(conn, "postgres domain:github.com", settings=st))
bench("three filters         'postgres tag:work domain:github.com added:>90d'",
      lambda: quick_search(conn, "postgres tag:work domain:github.com added:>90d", settings=st))
bench("browse, one filter    'domain:github.com'", lambda: quick_search(conn, "domain:github.com", settings=st))
bench("browse, negation only '-facebook'", lambda: quick_search(conn, "-facebook", settings=st))
bench("browse, sort only     'sort:date'", lambda: quick_search(conn, "sort:date", settings=st))
bench("browse, opened sort   'sort:opened'", lambda: quick_search(conn, "sort:opened", settings=st))

print()
print("=== full pipeline ===")
bench("plain                 'postgres index'",
      lambda: asyncio.run(search(conn, "postgres index", limit=20, config=FULL, settings=st)))
bench("filtered              'postgres domain:github.com'",
      lambda: asyncio.run(search(conn, "postgres domain:github.com", limit=20, config=FULL, settings=st)))

print()
print("=== the other two things the UI calls on every visit ===")
bench("timeline()", lambda: timeline(conn))
bench("suggest_query_syntax('domain:git')", lambda: suggest_query_syntax(conn, "domain:git"))
bench("suggest_query_syntax('tag:w')", lambda: suggest_query_syntax(conn, "tag:w"))
