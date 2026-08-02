"""Collect candidate URLs for the evaluation corpus, with real timestamps.

Why these sources. The calibration library is one Chinese developer's bookmarks:
1505 hosts across 1688 entries, 93% of titles carrying CJK, save dates skewed
hard toward the present. A corpus of Hacker News front pages would reproduce
the host tail and none of the language mix. So the primary source is
``ruanyf/weekly`` -- a Chinese developer's curated weekly link digest, published
since 2018, mixing Chinese and English pages across a very long host tail. That
is structurally the same object as the target: one person's saved links over
years. Hacker News supplies additional English long tail and a second session
shape.

What is real and what is constructed. The **pages** are real and so are the
**batch dates** (a weekly issue's publication date, an HN story's creation
date). The per-bookmark *save* timestamps are constructed: a batch becomes one
or more sessions, spread over minutes inside the batch date. That is the honest
description -- real documents, real batch chronology, synthesised save events.
It is recorded in the manifest so the evaluation report can state it.

Output: ``candidates.jsonl``, one record per URL:
    {url, title, source, batch_id, batch_ts, lang_hint}
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx

OUT = Path(__file__).resolve().parent / "candidates.jsonl"
UA = "facetmark-eval-corpus/1.0 (+https://github.com/88lin/facetmark)"

# Hosts that are the digest's own plumbing, not a saved page.
SKIP_HOST_SUFFIX = (
    "beekka.com",
    "wangbase.com",
    "ruanyifeng.com",
    "githubusercontent.com",
    "shields.io",
    "gravatar.com",
    "w.org",
)
SKIP_PATH_RE = re.compile(r"\.(png|jpe?g|gif|webp|svg|mp4|mp3|zip|pdf|ico)$", re.I)
# ruanyf/weekly links to its own issues and job postings constantly.
SKIP_URL_RE = re.compile(r"github\.com/ruanyf/weekly|/issues/\d+|mailto:|^javascript:", re.I)
MD_LINK_RE = re.compile(r"\[([^\]]{1,200})\]\((https?://[^\s)]+)\)")
COVER_DATE_RE = re.compile(r"bg(\d{4})(\d{2})(\d{2})")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def lang_hint(title: str) -> str:
    return "zh" if len(CJK_RE.findall(title)) >= 2 else "en"


def usable(url: str) -> bool:
    if SKIP_URL_RE.search(url) or SKIP_PATH_RE.search(urlsplit(url).path):
        return False
    host = urlsplit(url).hostname or ""
    return bool(host) and not any(host == s or host.endswith("." + s) for s in SKIP_HOST_SUFFIX)


def weekly(client: httpx.Client, records: list[dict]) -> None:
    """One markdown file per issue. The issue date comes from the cover image
    path (``bg20240515xx.webp``), which nearly every issue carries; issues
    without one are skipped rather than guessed at."""
    listing = client.get("https://api.github.com/repos/ruanyf/weekly/contents/docs").json()
    names = sorted(
        (f["name"] for f in listing if re.fullmatch(r"issue-\d+\.md", f["name"])),
        key=lambda n: int(re.findall(r"\d+", n)[0]),
        reverse=True,  # newest first: the corpus is recency-skewed
    )
    print(f"weekly: {len(names)} issue files", file=sys.stderr)
    kept = 0
    for name in names:
        num = int(re.findall(r"\d+", name)[0])
        raw = f"https://raw.githubusercontent.com/ruanyf/weekly/master/docs/{name}"
        try:
            body = client.get(raw).text
        except Exception as exc:  # noqa: BLE001 - one bad issue must not stop the sweep
            print(f"  {name}: {exc!r}", file=sys.stderr)
            continue
        m = COVER_DATE_RE.search(body)
        if not m:
            continue
        y, mo, d = (int(x) for x in m.groups())
        if not (2021 <= y <= 2026 and 1 <= mo <= 12 and 1 <= d <= 31):
            continue
        try:
            batch_ts = int(time.mktime((y, mo, d, 10, 0, 0, 0, 0, -1)))
        except (ValueError, OverflowError):
            continue
        seen: set[str] = set()
        before = len(records)
        for title, url in MD_LINK_RE.findall(body):
            url = url.rstrip(".,;)")
            if not usable(url) or url in seen:
                continue
            title = re.sub(r"\s+", " ", re.sub(r"[*`_]", "", title)).strip()
            if len(title) < 4 or title.lower() in {"via", "link", "here", "原文", "文章", "官网"}:
                continue
            seen.add(url)
            records.append({
                "url": url, "title": title[:200], "source": f"weekly-{num}",
                "batch_id": f"weekly-{num}", "batch_ts": batch_ts,
                "lang_hint": lang_hint(title),
            })
        if len(records) > before:
            kept += 1
            if kept % 40 == 0:
                print(f"  {kept} dated issues -> {len(records)} urls", file=sys.stderr)
    print(f"weekly: {kept} dated issues, {len(records)} urls", file=sys.stderr)


def hackernews(client: httpx.Client, records: list[dict], per_window: int = 200) -> None:
    """Algolia's date-ranged story search. One calendar day becomes one batch,
    a different session shape from a weekly digest: tighter in time, looser in
    topic."""
    # Denser in 2025-2026 because the target library is recency-skewed and the
    # weekly digest alone cannot fill the recent quota.
    windows = [
        (2022, 6), (2023, 3), (2023, 10), (2024, 4), (2024, 11),
        (2025, 1), (2025, 3), (2025, 5), (2025, 7), (2025, 9), (2025, 11),
        (2026, 1), (2026, 2), (2026, 3), (2026, 4), (2026, 5), (2026, 6), (2026, 7),
    ]
    for y, mo in windows:
        start = int(time.mktime((y, mo, 1, 0, 0, 0, 0, 0, -1)))
        end = start + 10 * 86400
        url = ("https://hn.algolia.com/api/v1/search_by_date?tags=story"
               f"&numericFilters=created_at_i>{start},created_at_i<{end}"
               f"&hitsPerPage={per_window}")
        try:
            hits = client.get(url).json().get("hits", [])
        except Exception as exc:  # noqa: BLE001
            print(f"hn {y}-{mo}: {exc!r}", file=sys.stderr)
            continue
        n = 0
        for h in hits:
            u, t, ts = h.get("url"), h.get("title"), h.get("created_at_i")
            if not (u and t and ts) or not usable(u):
                continue
            day = time.strftime("%Y%m%d", time.localtime(ts))
            records.append({
                "url": u, "title": re.sub(r"\s+", " ", t)[:200], "source": "hn",
                "batch_id": f"hn-{day}", "batch_ts": int(ts), "lang_hint": lang_hint(t),
            })
            n += 1
        print(f"hn {y}-{mo:02d}: +{n}", file=sys.stderr)


def main() -> None:
    hn_only = "--hn-only" in sys.argv
    records: list[dict] = []
    if hn_only and OUT.exists():
        records = [json.loads(x) for x in OUT.read_text("utf-8").splitlines() if x]
        print(f"reusing {len(records)} existing candidates", file=sys.stderr)
    headers = {"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}
    with httpx.Client(timeout=30.0, headers=headers, follow_redirects=True) as client:
        if not hn_only:
            weekly(client, records)
        hackernews(client, records, per_window=400)
    # Dedupe on url, keeping the earliest batch: first save wins, as in a real library.
    best: dict[str, dict] = {}
    for r in records:
        prev = best.get(r["url"])
        if prev is None or r["batch_ts"] < prev["batch_ts"]:
            best[r["url"]] = r
    rows = sorted(best.values(), key=lambda r: r["batch_ts"])
    OUT.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8"
    )
    zh = sum(1 for r in rows if r["lang_hint"] == "zh")
    hosts = {urlsplit(r["url"]).hostname for r in rows}
    years: dict[int, int] = {}
    for r in rows:
        y = time.localtime(r["batch_ts"]).tm_year
        years[y] = years.get(y, 0) + 1
    print(f"\ncandidates={len(rows)} zh={zh} ({zh / max(len(rows), 1):.0%}) "
          f"hosts={len(hosts)} batches={len({r['batch_id'] for r in rows})}", file=sys.stderr)
    print("by year:", dict(sorted(years.items())), file=sys.stderr)


if __name__ == "__main__":
    main()
