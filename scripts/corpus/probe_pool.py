"""候选池探针：目标页到底进没进 C 档的候选池？

闸门的第二条判据是 D−C 在 q_episodic 上 Recall@5 ≥10pp。D 相对 C 多的是
上下文乘子和图扩展，而上下文乘子是**后融合重排**——它只能把已经在候选池
里的条目往上抬，抬不进池外的东西。所以如果 q_episodic 的目标根本没进 C 的
融合列表，D−C 在结构上就恒等于 0，此时"情境面不成立"是个假结论：测到的是
召回缺失，不是排序机制无效。

这个探针精确复刻 search() 里 rung C 的前三步（understand → 四个面 →
RRF），但不截断到 limit，而是报告目标在**整条融合列表**里的名次，以及它是
被哪一路召回的。它必须在跑消融之前跑，否则拿到 D−C≈0 时无法区分两种解释。

用法：
  cd /workspace/facetmark && source /workspace/corpus/env.sh \
    && .venv/bin/python /workspace/corpus/probe_pool.py \
       --queries /workspace/corpus/queries.jsonl --concurrency 8
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from facetmark.config import get_settings
from facetmark.db import open_db
from facetmark.normalize import normalize_url
from facetmark.providers import get_provider
from facetmark.search.lexical import lexical_lists
from facetmark.search.pipeline import DEFAULT_FACET_WEIGHTS
from facetmark.search.rrf import rrf
from facetmark.search.understand import classify
from facetmark.search.vectors import vector_lists

FACETS = ("content", "intent", "lex_seg", "lex_tri")


def rank_of(ids: list[int], target: int) -> int:
    """1-based 名次，0 表示不在列表里。"""
    try:
        return ids.index(target) + 1
    except ValueError:
        return 0


def load_queries(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        rows.append(json.loads(line))
    return rows


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", required=True)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--out", default="/workspace/corpus/pool_probe.json")
    args = ap.parse_args()

    st = get_settings()
    conn = open_db(st.db_path)
    url2id = {
        r["url_norm"]: int(r["id"])
        for r in conn.execute("SELECT id, url_norm FROM bookmark")
    }
    rows = load_queries(Path(args.queries))
    missing = [r for r in rows if normalize_url(r["target_url"]).normalized not in url2id]
    if missing:
        raise SystemExit(f"{len(missing)} 条查询的目标不在库里，第一条 {missing[0]['target_url']}")

    prov = get_provider(st)
    per_facet = st.candidates_per_facet
    gate = asyncio.Semaphore(max(1, args.concurrency))
    out: list[dict] = []

    async def one(r: dict) -> dict:
        tid = url2id[normalize_url(r["target_url"]).normalized]
        async with gate:
            u = classify(r["text"])
            lists: dict[str, list[int]] = dict(
                lexical_lists(conn, r["text"], limit=per_facet)
            )
            vlists, _ = await vector_lists(
                conn, r["text"], provider=prov, settings=st, limit=per_facet,
                want_content=True, want_intent=True,
            )
            lists.update(vlists)
        fused = [f.doc_id for f in rrf(lists, k=st.rrf_k, weights=DEFAULT_FACET_WEIGHTS)]
        return {
            "qtype": r["qtype"],
            "subtype": r.get("subtype", ""),
            "text": r["text"],
            "target_url": r["target_url"],
            "fused_rank": rank_of(fused, tid),
            "fused_n": len(fused),
            "facet_rank": {f: rank_of(lists.get(f, []), tid) for f in FACETS},
            "has_window": u.time_window is not None,
            "episodic_confidence": round(u.episodic_confidence, 3),
        }

    out = list(await asyncio.gather(*(one(r) for r in rows)))
    await prov.aclose()
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    groups: dict[str, list[dict]] = defaultdict(list)
    for o in out:
        groups[o["qtype"]].append(o)
        if o["qtype"] == "q_episodic" and o["subtype"]:
            groups[f"  q_episodic/{o['subtype']}"].append(o)

    print(f"{'group':<26}{'n':>5}{'in pool':>9}{'top200':>8}{'top5':>7}"
          f"{'med rank':>10}{'window':>8}")
    for g, gs in sorted(groups.items()):
        n = len(gs)
        inpool = [o for o in gs if o["fused_rank"] > 0]
        ranks = [o["fused_rank"] for o in inpool]
        print(f"{g:<26}{n:>5}{len(inpool) / n:>9.2f}"
              f"{sum(1 for o in inpool if o['fused_rank'] <= 200) / n:>8.2f}"
              f"{sum(1 for o in inpool if o['fused_rank'] <= 5) / n:>7.2f}"
              f"{(statistics.median(ranks) if ranks else 0):>10.0f}"
              f"{sum(1 for o in gs if o['has_window']) / n:>8.2f}")

    print("\n目标是被哪一路召回的（各面单独命中前 50 的比例）")
    print(f"{'group':<26}" + "".join(f"{f:>10}" for f in FACETS))
    for g, gs in sorted(groups.items()):
        n = len(gs)
        print(f"{g:<26}" + "".join(
            f"{sum(1 for o in gs if o['facet_rank'][f] > 0) / n:>10.2f}" for f in FACETS))

    only = Counter()
    for o in out:
        hit = [f for f in FACETS if o["facet_rank"][f] > 0]
        if len(hit) == 1:
            only[f"{o['qtype']}:only {hit[0]}"] += 1
        elif not hit:
            only[f"{o['qtype']}:no facet"] += 1
    print("\n单面独占召回 / 完全召回不到：")
    for k, v in sorted(only.items()):
        print(f"  {k:<32}{v}")
    print(f"\n写入 {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
