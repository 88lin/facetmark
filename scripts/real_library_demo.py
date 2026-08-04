"""End-to-end demo on a real browser export: what the shipped default returns.

Not an evaluation. There is no ground truth for someone else's bookmarks, so
nothing here is scored -- the point is that the shipped path runs on a real
1,700-item library and that the 1.3.0 revert is visible on real queries with a
year in them.

Usage:
    python scripts/real_library_demo.py --db <path> --out <json>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import time
from pathlib import Path

from facetmark.db import connect
from facetmark.search.pipeline import ALL_CONFIGS, Config, search
from facetmark.search.understand import classify

# Queries written by reading folder names and titles, before any was run.
QUERIES: list[tuple[str, str]] = [
    ("plain", "把文字稿变成 PPT 的工具"),
    ("plain", "网盘直链解析"),
    ("plain", "chrome 插件下载"),
    ("plain", "免费域名注册"),
    ("plain", "hexo 博客主题美化"),
    ("plain", "食疗 营养成分"),
    ("plain", "视频解析 去水印"),
    ("plain", "AI 提示词"),
    ("episodic", "上次存的那个签到脚本"),
    ("episodic", "那阵子收藏的白嫖 API"),
    ("topical_year", "2025 日历"),
    ("topical_year", "2024 年的开源模型"),
]

# 1.2.0's default: the same thing plus a gated context multiplier.
GATED = Config("shipped_1_2_0", frozenset({"content"}), context=True, context_gate=True, graph=True, decay=True)


def rows(db: sqlite3.Connection, urls: list[str]) -> dict[str, sqlite3.Row]:
    if not urls:
        return {}
    q = ",".join("?" * len(urls))
    return {r["url"]: r for r in db.execute(f"select url,title,folder,date_added from bookmark where url in ({q})", urls)}


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=5)
    args = ap.parse_args()

    full = ALL_CONFIGS["full"]
    db = connect(Path(args.db))
    db.row_factory = sqlite3.Row
    report: dict = {"db": args.db, "config": full.as_dict(), "queries": []}

    for kind, text in QUERIES:
        u = classify(text)
        t0 = time.perf_counter()
        resp = await search(db, text, limit=args.limit, config=full)
        hits = resp.hits
        ms = (time.perf_counter() - t0) * 1000
        urls = [h.url for h in hits]
        meta = rows(db, urls)
        entry = {
            "query": text,
            "kind": kind,
            "ms": round(ms, 1),
            "is_episodic": u.is_episodic,
            "rule_hits": list(u.rule_hits),
            "shipped": [
                {
                    "rank": i + 1,
                    "title": (meta[h.url]["title"] if h.url in meta else "")[:70],
                    "folder": (meta[h.url]["folder"] if h.url in meta else "") or "-",
                    "url": h.url[:90],
                }
                for i, h in enumerate(hits)
            ],
        }
        if u.is_episodic:
            gresp = await search(db, text, limit=args.limit, config=GATED)
            gated = gresp.hits
            gurls = [h.url for h in gated]
            gmeta = rows(db, gurls)
            entry["gated_1_2_0"] = [
                {
                    "rank": i + 1,
                    "title": (gmeta[h.url]["title"] if h.url in gmeta else "")[:70],
                    "moved_from": (urls.index(h.url) + 1) if h.url in urls else None,
                }
                for i, h in enumerate(gated)
            ]
            entry["top1_changed"] = bool(gurls and urls and gurls[0] != urls[0])
            entry["overlap_at_5"] = len(set(urls) & set(gurls))
        report["queries"].append(entry)

    report["summary"] = {
        "n_queries": len(QUERIES),
        "median_ms": sorted(q["ms"] for q in report["queries"])[len(QUERIES) // 2],
        "gate_fired": sum(1 for q in report["queries"] if q["is_episodic"]),
        "gate_fired_on_topical_year": sum(
            1 for q in report["queries"] if q["kind"] == "topical_year" and q["is_episodic"]
        ),
        "top1_changed_by_gate": sum(1 for q in report["queries"] if q.get("top1_changed")),
    }
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
