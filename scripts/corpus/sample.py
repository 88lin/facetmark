"""Sample candidates into a library shaped like the calibration library.

Targets, all measured on the real 1688-entry library and reported in the design
document:

  * year histogram 2022..2026 = 121/192/235/372/777, i.e. hard recency skew;
  * ~0.89 unique hosts per entry (1505 hosts / 1688 entries), busiest host 78;
  * session coverage ~60%: four entries in ten were saved alone, not in a burst;
  * majority-Chinese titles.

Two deliberate deviations, both recorded in the report:

  1. Chinese share is targeted at 70%, not the library's 93%. Pushing to 93%
     would mean drawing almost everything from one digest and collapsing the
     host tail, which is the property the retrieval layer is actually sensitive
     to. Language mix shifts all five ablation rungs together, so it does not
     favour any rung.
  2. Save timestamps are constructed from real batch dates (see collect.py).

Two phases, because sessions and singletons are different objects:

  * cluster phase -- walk batches repeatedly, each visit contributing a burst of
    3..11 saves minutes apart, until 60% of the quota is met;
  * singleton phase -- draw the rest as isolated saves and push each one at
    least 30 minutes away from every neighbour, so the session builder (eps =
    1200s) genuinely leaves them alone.

Oversamples by ``--factor`` because a quarter of any real link set is dead,
paywalled or JavaScript-only by the time you fetch it. Survivors are counted
after fetching, not here.
"""

from __future__ import annotations

import argparse
import bisect
import json
import random
import re
import time
from collections import defaultdict
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
YEAR_TARGET = {2022: 121, 2023: 192, 2024: 235, 2025: 372, 2026: 777}  # real library
ZH_SHARE = 0.70
HOST_CAP = 12          # real library's busiest host held 4.6% of entries
SINGLETON_SHARE = 0.40  # matches ~60% session coverage
CLUSTER_MIN, CLUSTER_MAX = 3, 11
ISOLATION_S = 1800      # > sessions eps (1200s)

FOLDER_RULES: list[tuple[str, str]] = [
    (r"(llm|gpt|claude|人工智能|大模型|机器学习|deep learning|neural|prompt|agent|ai\b)", "AI/模型"),
    (r"(rust|golang|python|typescript|javascript|java|c\+\+|编程语言|compiler|编译)", "编程/语言"),
    (r"(react|vue|css|html|前端|浏览器|browser|web dev|tailwind)", "编程/前端"),
    (r"(docker|kubernetes|k8s|linux|服务器|运维|devops|nginx|ssh|部署)", "编程/运维"),
    (r"(database|sqlite|postgres|mysql|redis|数据库|sql)", "编程/数据库"),
    (r"(security|安全|加密|隐私|privacy|漏洞|cve|密码)", "安全隐私"),
    (r"(tool|工具|软件|应用|插件|extension|cli)", "工具"),
    (r"(游戏|game|音乐|music|电影|摄影|photo|设计|design)", "兴趣"),
    (r"(创业|职场|管理|产品|business|startup|career|工作)", "职业"),
    (r"(科学|物理|数学|生物|space|science|research|论文|paper)", "科学"),
]


def folder_for(title: str, rng: random.Random) -> str:
    if rng.random() < 0.35:
        return ""  # unfiled, like most real libraries
    low = title.lower()
    for pat, folder in FOLDER_RULES:
        if re.search(pat, low):
            return folder
    return "未分类"


def host_of(url: str) -> str:
    return urlsplit(url).hostname or ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--factor", type=float, default=1.40, help="oversample vs the target")
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    rows = [json.loads(x) for x in (HERE / "candidates.jsonl").read_text("utf-8").splitlines() if x]
    by_year: dict[int, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        y = time.localtime(r["batch_ts"]).tm_year
        if y in YEAR_TARGET:
            by_year[y][r["batch_id"]].append(r)

    host_used: dict[str, int] = defaultdict(int)
    taken: set[str] = set()
    picked: list[dict] = []

    def pick_from(cands: list[dict], want: int, zh_deficit: bool) -> list[dict]:
        pool = [c for c in cands
                if c["url"] not in taken and host_used[host_of(c["url"])] < HOST_CAP]
        if not pool:
            return []
        # Prefer unseen hosts, but only probabilistically: a real library does
        # revisit favourite domains.
        pool.sort(key=lambda c: (
            min(host_used[host_of(c["url"])], 2) if rng.random() < 0.8 else 0,
            0 if (zh_deficit and c["lang_hint"] == "zh") else 1,
            rng.random(),
        ))
        out = []
        for c in pool[: want * 3]:
            if len(out) >= want:
                break
            h = host_of(c["url"])
            if host_used[h] >= HOST_CAP:
                continue
            host_used[h] += 1
            taken.add(c["url"])
            out.append(dict(c))
        return out

    def zh_short() -> bool:
        n = len(picked) or 1
        return sum(1 for p in picked if p["lang_hint"] == "zh") < ZH_SHARE * n

    for year in sorted(YEAR_TARGET):
        quota = int(round(YEAR_TARGET[year] * args.factor))
        n_cluster = int(quota * (1 - SINGLETON_SHARE))
        batches = list(by_year[year].items())
        rng.shuffle(batches)
        got = 0

        # --- cluster phase: repeated passes, each visit is one saving sitting
        stalled = 0
        while got < n_cluster and stalled < 2:
            progress = False
            for batch_id, cands in batches:
                if got >= n_cluster:
                    break
                want = min(rng.randint(CLUSTER_MIN, CLUSTER_MAX), n_cluster - got)
                chosen = pick_from(cands, want, zh_short())
                if len(chosen) < 2:  # a burst of one is not a session
                    for c in chosen:
                        taken.discard(c["url"])
                        host_used[host_of(c["url"])] -= 1
                    continue
                t = chosen[0]["batch_ts"] + rng.randint(0, 12 * 3600)
                for c in chosen:
                    c["saved_at"] = t
                    c["session_hint"] = batch_id
                    c["folder"] = folder_for(c["title"], rng)
                    picked.append(c)
                    t += rng.randint(45, 300)
                got += len(chosen)
                progress = True
            stalled = 0 if progress else stalled + 1

        # --- singleton phase: isolated saves, nudged apart from everything else
        stalled = 0
        while got < quota and stalled < 2:
            progress = False
            for _batch_id, cands in batches:
                if got >= quota:
                    break
                chosen = pick_from(cands, 1, zh_short())
                if not chosen:
                    continue
                c = chosen[0]
                c["saved_at"] = c["batch_ts"] + rng.randint(0, 3 * 86400)
                c["session_hint"] = "single"
                c["folder"] = folder_for(c["title"], rng)
                picked.append(c)
                got += 1
                progress = True
            stalled = 0 if progress else stalled + 1
        print(f"{year}: quota={quota} picked={got}")

    # Enforce isolation for singletons against every other save.
    picked.sort(key=lambda r: r["saved_at"])
    times = [r["saved_at"] for r in picked]
    for r in picked:
        if r["session_hint"] != "single":
            continue
        for _ in range(40):
            i = bisect.bisect_left(times, r["saved_at"])
            near = [t for t in times[max(0, i - 3): i + 3] if t != r["saved_at"]]
            if all(abs(t - r["saved_at"]) > ISOLATION_S for t in near):
                break
            r["saved_at"] += ISOLATION_S + rng.randint(0, 7200)
            times = sorted(x["saved_at"] for x in picked)
    picked.sort(key=lambda r: r["saved_at"])

    (HERE / "manifest.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in picked) + "\n", encoding="utf-8"
    )

    lines = ["<!DOCTYPE NETSCAPE-Bookmark-file-1>",
             '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
             "<TITLE>Bookmarks</TITLE>", "<H1>Bookmarks</H1>", "<DL><p>"]
    by_folder: dict[str, list[dict]] = defaultdict(list)
    for r in picked:
        by_folder[r["folder"]].append(r)
    for r in by_folder.get("", []):
        lines.append(f'    <DT><A HREF="{escape(r["url"], quote=True)}" '
                     f'ADD_DATE="{r["saved_at"]}">{escape(r["title"])}</A>')
    for folder in sorted(f for f in by_folder if f):
        parts = folder.split("/")
        for depth, part in enumerate(parts):
            pad = "    " * (depth + 1)
            lines.append(f"{pad}<DT><H3>{escape(part)}</H3>")
            lines.append(f"{pad}<DL><p>")
        pad = "    " * (len(parts) + 1)
        for r in by_folder[folder]:
            lines.append(f'{pad}<DT><A HREF="{escape(r["url"], quote=True)}" '
                         f'ADD_DATE="{r["saved_at"]}">{escape(r["title"])}</A>')
        for depth in range(len(parts) - 1, -1, -1):
            lines.append("    " * (depth + 1) + "</DL><p>")
    lines.append("</DL><p>")
    (HERE / "bookmarks.html").write_text("\n".join(lines) + "\n", encoding="utf-8")

    per_host: dict[str, int] = defaultdict(int)
    for r in picked:
        per_host[host_of(r["url"])] += 1
    years: dict[int, int] = defaultdict(int)
    zh_year: dict[int, int] = defaultdict(int)
    for r in picked:
        y = time.localtime(r["saved_at"]).tm_year
        years[y] += 1
        zh_year[y] += r["lang_hint"] == "zh"
    zh = sum(1 for r in picked if r["lang_hint"] == "zh")
    singles = sum(1 for r in picked if r["session_hint"] == "single")
    print(f"\nsampled={len(picked)} zh={zh} ({zh / len(picked):.0%}) "
          f"hosts={len(per_host)} ({len(per_host) / len(picked):.2f}/entry) "
          f"busiest={max(per_host.values())} singles={singles / len(picked):.0%} "
          f"folders={len(by_folder)}")
    print("by year:", {y: f"{years[y]} ({zh_year[y] / years[y]:.0%} zh)" for y in sorted(years)})


if __name__ == "__main__":
    main()
