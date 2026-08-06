"""把消融报告切成闸门判定 + 分层读数。

`facetmark eval --ablation` 给的是每档 × 每类型的汇总。闸门要的是**成对差
值**加区间和检验，而且 q_episodic 必须按子类型拆开——year/relative 靠时间
窗后的上下文乘子，anchor 没有时间窗、只能靠图扩展，两者混在一起的均值不指
向任何一个可操作的结论。

判定规则（设计报告 §13.5，原文照搬，不在这里放宽）：
  C−B 在 q_vague 上   Recall@5 ≥ +10pp
  D−C 在 q_episodic 上 Recall@5 ≥ +10pp
  E vs A 在 q_content 上 不显著劣化（差值 ≥0，或 McNemar p > 0.05）

同时报告 recall@5+exp：图扩展的命中不进主列表（SearchResponse.ids 只含
hits），按主指标口径它对 D−C 的贡献恒为 0。两个数字一起看才能说清差值来自
上下文乘子还是图扩展。

用法：
  .venv/bin/python /workspace/corpus/analyze_eval.py --report eval_ablation.json \
      [--md /mnt/results/.../gate.md]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from facetmark.eval import Outcome, bootstrap_ci, mcnemar, summarise

PASS_PP = 10.0


def rebuild(report: dict) -> dict[str, list[Outcome]]:
    """从原始判决重建 Outcome，顺序与 report["queries"] 一一对应。"""
    qs = report["queries"]
    by: dict[str, list[Outcome]] = {}
    for rung, outs in report["outcomes"].items():
        if len(outs) != len(qs):
            raise SystemExit(f"rung {rung}: {len(outs)} 条判决 vs {len(qs)} 条查询，对不齐")
        by[rung] = [
            Outcome(qtype=q["qtype"], rank=o["rank"], ms=o["ms"], expanded=o["expanded"])
            for q, o in zip(qs, outs, strict=True)
        ]
    return by


def select(report: dict, outs: list[Outcome], qtype: str, note: str | None = None
           ) -> list[Outcome]:
    keep = []
    for q, o in zip(report["queries"], outs, strict=True):
        if q["qtype"] != qtype:
            continue
        if note is not None and q["note"] != note:
            continue
        keep.append(o)
    return keep


def delta(a: list[Outcome], b: list[Outcome], metric: str, resamples: int) -> dict:
    """成对差值。bootstrap_ci 重采样的是配对索引，所以两侧长度必须相同。"""
    pp = (summarise(b)[metric] - summarise(a)[metric]) * 100
    row = {"n": len(a), "from_pct": summarise(a)[metric] * 100,
           "to_pct": summarise(b)[metric] * 100, "pp": round(pp, 2)}
    if metric == "recall@5":
        lo, hi = bootstrap_ci(a, b, resamples=resamples)
        row["ci95"] = (lo, hi)
        row["p"] = mcnemar(a, b)["p"]
    return row


def fmt(row: dict) -> str:
    ci = f"  CI95 [{row['ci95'][0]:+.1f}, {row['ci95'][1]:+.1f}]" if "ci95" in row else ""
    p = f"  p={row['p']:.4f}" if "p" in row else ""
    return (f"n={row['n']:<4} {row['from_pct']:5.1f}% -> {row['to_pct']:5.1f}% "
            f"{row['pp']:+6.2f}pp{ci}{p}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--resamples", type=int, default=1000)
    ap.add_argument("--md", default="")
    args = ap.parse_args()

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    by = rebuild(report)
    lines: list[str] = []

    def emit(s: str = "") -> None:
        print(s)
        lines.append(s)

    emit(f"provider={report['provider']}  embed={report['embed_model']}  "
         f"reranker={report.get('reranker') or 'none'}  "
         f"queries={len(report['queries'])}  语料={report['corpus']['pages']} 页")
    if report.get("latency_caveat"):
        emit(f"延迟口径：{report['latency_caveat']}")
    emit()

    emit("## 各档 Recall@5（分查询类型）")
    emit()
    emit("| 档位 | 机制 | q_content | q_vague | q_episodic | q_save_action | 总体 |")
    emit("|---|---|---|---|---|---|---|")
    mech = {"A": "单向量内容", "B": "+词面 RRF", "C": "+意图面",
            "D": "+上下文乘子/图扩展", "E": "+LLM 重排"}
    for rung in ("A", "B", "C", "D", "E"):
        if rung not in by:
            continue
        o = by[rung]
        cells = [f"{summarise(select(report, o, t))['recall@5'] * 100:.1f}%"
                 for t in ("q_content", "q_vague", "q_episodic", "q_save_action")]
        emit(f"| {rung} | {mech[rung]} | " + " | ".join(cells)
             + f" | {summarise(o)['recall@5'] * 100:.1f}% |")
    emit()

    emit("## 闸门三条判据")
    emit()
    gate = []
    for name, lo_rung, hi_rung, qtype, passes in (
        ("C−B on q_vague", "B", "C", "q_vague", lambda r: r["pp"] >= PASS_PP),
        ("D−C on q_episodic", "C", "D", "q_episodic", lambda r: r["pp"] >= PASS_PP),
        # "不显著劣化"：要么没有退步，要么退步没有统计显著性。
        ("E vs A on q_content", "A", "E", "q_content",
         lambda r: r["pp"] >= 0 or r["p"] > 0.05),
    ):
        a = select(report, by[lo_rung], qtype)
        b = select(report, by[hi_rung], qtype)
        row = delta(a, b, "recall@5", args.resamples)
        ok = passes(row)
        gate.append((name, ok))
        emit(f"{'通过' if ok else '未通过'}  {name:<22} {fmt(row)}")
        exp = delta(a, b, "recall@5+exp", args.resamples)
        emit(f"      {'':<22} recall@5+exp {exp['pp']:+6.2f}pp "
             f"({exp['from_pct']:.1f}% -> {exp['to_pct']:.1f}%)")
    emit()
    emit(f"闸门整体：{'全部通过' if all(ok for _, ok in gate) else '未通过'}"
         f"（{sum(ok for _, ok in gate)}/3）")
    emit()

    notes = sorted({q["note"] for q in report["queries"]
                    if q["qtype"] == "q_episodic" and q["note"]})
    if notes:
        emit("## q_episodic 按子类型分层的 D−C")
        emit()
        emit("| 子类型 | n | C | D | Δ recall@5 | Δ recall@5+exp | 机制 |")
        emit("|---|---|---|---|---|---|---|")
        why = {"year": "绝对年份→时间窗→上下文乘子",
               "relative": "相对时间词→时间窗→上下文乘子",
               "anchor": "无时间窗，只有同会话邻居线索→只能靠图扩展"}
        for note in notes:
            a = select(report, by["C"], "q_episodic", note)
            b = select(report, by["D"], "q_episodic", note)
            if not a:
                continue
            r5 = delta(a, b, "recall@5", args.resamples)
            re5 = delta(a, b, "recall@5+exp", args.resamples)
            emit(f"| {note} | {r5['n']} | {r5['from_pct']:.1f}% | {r5['to_pct']:.1f}% "
                 f"| {r5['pp']:+.2f}pp | {re5['pp']:+.2f}pp | {why.get(note, '')} |")
        emit()

    emit("## 相邻档全量差值（所有查询）")
    emit()
    for d in report["deltas"]:
        emit(f"{d['from']} -> {d['to']}  {d['recall@5_pp']:+6.2f}pp  "
             f"CI95 [{d['ci95_pp'][0]:+.2f}, {d['ci95_pp'][1]:+.2f}]  "
             f"p={d['mcnemar']['p']:.4f}")
    if "end_to_end" in report:
        e = report["end_to_end"]
        emit(f"\n{e['from']} -> {e['to']}  {e['recall@5_pp']:+.2f}pp  "
             f"CI95 [{e['ci95_pp'][0]:+.2f}, {e['ci95_pp'][1]:+.2f}]  "
             f"达到 {report['pass_margin_pp']}pp 线：{e['meets_bar']}")

    if args.md:
        Path(args.md).write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n写入 {args.md}")


if __name__ == "__main__":
    main()
