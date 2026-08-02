#!/usr/bin/env bash
# W1 决策闸门的一次性测量链。
#
# 顺序是有意的：候选池探针必须在消融**之前**跑完。拿到 D−C≈0 时，只有探针
# 能区分"上下文乘子无效"和"目标压根没进候选池，乘子没东西可抬"——事后补跑
# 探针也行，但那时候已经很容易先入为主地解读数字了。
#
# 每一步都单独落盘，任何一步失败都不影响前面已经拿到的结果；最后统一快照到
# 共享卷，因为本地盘不保证活过机器生命周期事件。
#
# 用法：bash scripts/corpus/run_w1.sh [查询文件]

set -uo pipefail
cd /workspace/facetmark || exit 1
# shellcheck disable=SC1091
source /workspace/corpus/env.sh

Q="${1:-/workspace/corpus/queries.final.jsonl}"
OUT=/workspace/corpus/w1
SNAP=/mnt/shared-workspace/shared/facetmark_w1/w1
mkdir -p "$OUT" "$SNAP"
PY=.venv/bin/python

step() { echo; echo "=== $* === $(date -u +%H:%M:%S)"; }

step "0/4 查询集"
$PY - "$Q" <<'PY'
import json, sys
from collections import Counter
rows = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8")
        if l.strip() and not l.startswith("//")]
print(f"{len(rows)} 条  qtype={dict(Counter(r['qtype'] for r in rows))}")
print("  episodic 子类型:",
      dict(Counter(r.get('note','') for r in rows if r['qtype'] == 'q_episodic')))
PY

step "1/4 候选池探针"
$PY scripts/corpus/probe_pool.py --queries "$Q" --concurrency 8 \
    --out "$OUT/probe.json" 2>&1 | tee "$OUT/probe.txt"

step "2/4 A–E 消融（concurrency 8，质量数字）"
$PY -m facetmark.cli eval --no-build --db "$FACETMARK_DATA_DIR/facetmark.db" \
    --queries "$Q" --ablation --bootstrap 1000 --concurrency 8 \
    --out "$OUT/eval_ablation.json" 2>&1 | tee "$OUT/ablation.txt"

step "3/4 延迟子样本（concurrency 1，120 条分层抽样）"
$PY - "$Q" "$OUT/queries.latency.jsonl" <<'PY'
import json, random, sys
from collections import defaultdict
src, dst = sys.argv[1], sys.argv[2]
head = [l.rstrip("\n") for l in open(src, encoding="utf-8") if l.startswith("//")]
rows = [json.loads(l) for l in open(src, encoding="utf-8")
        if l.strip() and not l.startswith("//")]
by = defaultdict(list)
for r in rows:
    by[r["qtype"]].append(r)
rng = random.Random(11)
pick = []
for qt in sorted(by):
    pool = by[qt][:]
    rng.shuffle(pool)
    pick += pool[:40]
rng.shuffle(pick)
open(dst, "w", encoding="utf-8").write(
    "\n".join(head + ["// latency subsample, seed 11, 40 per qtype"]
              + [json.dumps(r, ensure_ascii=False) for r in pick]) + "\n")
print(f"{len(pick)} 条 -> {dst}")
PY
$PY -m facetmark.cli eval --no-build --db "$FACETMARK_DATA_DIR/facetmark.db" \
    --queries "$OUT/queries.latency.jsonl" --ablation --bootstrap 200 --concurrency 1 \
    --out "$OUT/eval_latency.json" 2>&1 | tee "$OUT/latency.txt"

step "4/4 闸门判定"
$PY scripts/corpus/analyze_eval.py --report "$OUT/eval_ablation.json" \
    --md "$OUT/gate.md" 2>&1 | tee "$OUT/gate.txt"

step "快照"
cp -f "$Q" "$OUT"/*.json "$OUT"/*.txt "$OUT"/*.md "$OUT"/*.jsonl "$SNAP"/ 2>/dev/null
ls -la "$SNAP"
echo "W1_CHAIN_DONE $(date -u +%H:%M:%S)"
