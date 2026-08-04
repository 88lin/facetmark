"""Generate the gate-precision probe set: queries that carry a time expression
and mean nothing by it.

``docs/gate-precision-protocol.md`` is the pre-registration; this file is its
generator. The one sentence worth repeating here is the inversion that makes
this set different from every other one in the repo:

    In ``gen_queries.py`` the product's own ``classify()`` is the **entrance
    ticket** -- an episodic query that the resolver cannot turn into a window
    containing the save time is thrown away, because it carries no episodic
    signal whatever its words look like.

    Here ``classify()`` is the **outcome variable**. Whether the gate fires on
    these queries is exactly what is being measured, so filtering on it would
    delete the measurement and leave a number that only says "the queries I
    kept are the ones I kept".

Every probe query is a *content* query -- it asks what the page says -- that
happens to contain a time expression belonging to the subject matter:

``p_year``      a four-digit year that appears in the page's own text and is
                **not** the year the bookmark was saved. The gate reads it as a
                save-time window, and that window is wrong by construction.
                Real shape: "that batch of 2015 papers".

``p_relative``  a relative time word (最近 / 去年 / recently / last year) that
                describes how recent the *subject matter* is, not when anything
                was saved. Real shape: "the recent work on X".
                This subtype cuts both ways on purpose: if the target happens
                to have been saved inside the resolved window, the misfire
                *helps*. That is real behaviour, so the two subtypes are
                reported separately rather than averaged into one number.

Rejected, with the reason fed back, up to ``--retries`` times:

* everything ``check_content`` rejects (a reworded title, a keyword list, the
  example bleeding through, the wrong language);
* a query missing its required time expression -- without it there is nothing
  for the gate to misread;
* a query containing the save year, which would make the wrong window
  accidentally right;
* **any word about saving** -- 保存 / 收藏 / 上次 / 那阵子 / saved / bookmarked
  / back when. A query that says "the one I saved" is an episodic query, and
  scoring it would measure the gate's recall for the second time instead of
  its precision for the first.

One query per target page: two queries written from the same page are not
independent, and the paired bootstrap downstream assumes they are.
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import random
import re
import sqlite3
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from facetmark.config import get_settings
from facetmark.providers import get_provider

_SPEC = importlib.util.spec_from_file_location(
    "_gen_queries", Path(__file__).with_name("gen_queries.py"))
_GQ = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_GQ)

build_df = _GQ.build_df
check_content = _GQ.check_content
content_tokens = _GQ.content_tokens
tokens = _GQ.tokens
_attach_neighbours = _GQ._attach_neighbours
_stratify_by_year = _GQ._stratify_by_year

SYSTEM = (
    "You write realistic search queries that a person types months after "
    "bookmarking a page, when they only half-remember it. You answer with a "
    "single JSON object and nothing else."
)

#: Years a page can plausibly be *about*, 1990-2025, exactly the band the
#: protocol fixes. The product's resolver accepts 1980-2049; the narrower band
#: keeps out version numbers, and stops at 2025 because 2026 is the library's
#: own "now" -- a 2026 content year and a 2026 save year are not distinguishable
#: as intents, which is the distinction the whole probe rests on.
_CONTENT_YEAR = re.compile(r"(?<![0-9A-Za-z_])(199\d|20[01]\d|202[0-5])(?![0-9A-Za-z_])")

#: Relative phrases offered to the model. Each one is a literal that the
#: product's ``_RELATIVE`` table matches, because a probe the gate cannot even
#: see would measure nothing.
_REL_ZH = ("最近", "今年", "去年", "前年")
_REL_EN = ("recently", "this year", "last year", "lately")

#: Saying any of these turns a content query into an episodic one. The first
#: block is the product's own vague-episodic marker list (kept in sync by the
#: test); the second is the vocabulary of saving.
_SAVE_WORDS = (
    "那阵子", "那段时间", "那会儿", "那时候", "当时", "刚开始", "最初",
    "一开始", "同一批", "同时期", "前后", "顺手存的", "一起存",
    "back when", "around the time", "at the time", "same batch",
    "along with", "when i was",
    "保存", "收藏", "存的", "存过", "书签", "上次", "那天", "我存",
    "saved", "bookmark", "bookmarked", "i kept", "my bookmarks",
)

_EXAMPLES = {
    ("p_year", False): (
        """EXAMPLE (page: "How the 2016 rewrite of the tax code changed small business filing")
{"query": "what the 2016 tax code rewrite did to sole proprietors"}""",
        """EXAMPLE (page: "Revisiting the 1998 harbour dredging survey")
{"query": "sediment findings from the 1998 harbour dredging survey"}""",
        """EXAMPLE (page: "A retrospective on the 2011 grid failure")
{"query": "cascading substation trips during the 2011 blackout"}""",
    ),
    ("p_year", True): (
        """\u793a\u4f8b\uff08\u9875\u9762\uff1a\u300a2016 \u5e74\u7a0e\u6cd5\u6539\u5199\u5bf9\u5c0f\u5546\u6237\u7533\u62a5\u7684\u5f71\u54cd\u300b\uff09
{"query": "2016\u5e74\u7a0e\u6cd5\u6539\u5199\u540e\u4e2a\u4f53\u5de5\u5546\u6237\u600e\u4e48\u7533\u62a5"}""",
        """\u793a\u4f8b\uff08\u9875\u9762\uff1a\u300a\u91cd\u8bfb 1998 \u5e74\u90a3\u4efd\u6e2f\u53e3\u75a2\u6d5a\u8c03\u67e5\u300b\uff09
{"query": "1998\u5e74\u6e2f\u53e3\u75a2\u6d5a\u8c03\u67e5\u91cc\u7684\u6cc9\u6c99\u7ed3\u8bba"}""",
        """\u793a\u4f8b\uff08\u9875\u9762\uff1a\u300a2011 \u5e74\u90a3\u6b21\u7535\u7f51\u4e8b\u6545\u56de\u987e\u300b\uff09
{"query": "2011\u5e74\u5927\u505c\u7535\u91cc\u53d8\u7535\u7ad9\u8fde\u9501\u8df3\u95f8\u7684\u8fc7\u7a0b"}""",
    ),
    ("p_relative", False): (
        """EXAMPLE (page: "Where solid-state battery research stands")
{"query": "recently reported gains in solid state cell density"}""",
        """EXAMPLE (page: "The state of remote work policy at mid-size firms")
{"query": "how hybrid schedules changed at midsize firms this year"}""",
        """EXAMPLE (page: "Reef restoration methods that survived the last bleaching")
{"query": "lately tried coral transplant methods after bleaching"}""",
    ),
    ("p_relative", True): (
        """\u793a\u4f8b\uff08\u9875\u9762\uff1a\u300a\u56fa\u6001\u7535\u6c60\u7814\u7a76\u8d70\u5230\u54ea\u4e86\u300b\uff09
{"query": "\u6700\u8fd1\u56fa\u6001\u7535\u6c60\u80fd\u91cf\u5bc6\u5ea6\u63d0\u5347\u7684\u8fdb\u5c55"}""",
        """\u793a\u4f8b\uff08\u9875\u9762\uff1a\u300a\u4e2d\u578b\u516c\u53f8\u7684\u8fdc\u7a0b\u529e\u516c\u653f\u7b56\u73b0\u72b6\u300b\uff09
{"query": "\u4eca\u5e74\u4e2d\u578b\u516c\u53f8\u6df7\u5408\u529e\u516c\u5b89\u6392\u7684\u53d8\u5316"}""",
        """\u793a\u4f8b\uff08\u9875\u9762\uff1a\u300a\u767d\u5316\u4e4b\u540e\u5b58\u6d3b\u4e0b\u6765\u7684\u73ca\u745a\u4fee\u590d\u65b9\u6cd5\u300b\uff09
{"query": "\u53bb\u5e74\u73ca\u745a\u79fb\u690d\u4fee\u590d\u54ea\u4e9b\u65b9\u6cd5\u6709\u6548"}""",
    ),
}

TEMPLATE = """A person bookmarked this page and is now looking for it again.
They are searching for WHAT THE PAGE SAYS. The time expression in their query
belongs to the subject matter -- it is part of the topic, not a memory of when
they saved anything.

TITLE: {title}
FOLDER: {folder}
PAGE TEXT:
{body}

{examples}

Answer in {lang}. One natural phrase of 4-14 words (or 8-25 Chinese
characters) that a person would actually type into a search box. Lowercase, no
quotes, no trailing punctuation, and NOT a list of keywords separated by
commas.

"query" -- what they type, remembering the SUBJECT MATTER. It MUST contain
   {requirement}
   The rest of it must describe the page's argument using words the title does
   not use.

Never say that they saved, bookmarked or collected anything. Never write "back
when", "at the time", "那阵子", "当时", "上次", "顺手存的" or anything like
them. This person is asking about a topic; they are not recalling an occasion.

The example above is about a different page. Take its shape, never its words.

JSON only: {{"query": "..."}}"""

_REQ_YEAR = ('the year {year}, written exactly as four digits, because the page '
             'itself argues about {year}.')
_REQ_YEAR_ZH = ('\u5e74\u4efd {year}\uff08\u56db\u4f4d\u6570\u5b57\u539f\u6837\u5199\u51fa\uff09\uff0c'
                '\u56e0\u4e3a\u9875\u9762\u672c\u8eab\u8bb2\u7684\u5c31\u662f {year} \u5e74\u7684\u4e8b\u3002')
_REQ_REL = ('the word "{phrase}", used to say how recent the subject matter is.')


def requirement_for(subtype: str, zh: bool, year: int | None, phrase: str | None) -> str:
    if subtype == "p_year":
        return (_REQ_YEAR_ZH if zh else _REQ_YEAR).format(year=year)
    return _REQ_REL.format(phrase=phrase)


# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------


def year_in(text: str, year: int) -> bool:
    return re.search(rf"(?<![0-9A-Za-z_]){year}(?![0-9A-Za-z_])", text) is not None


def save_words_in(text: str) -> list[str]:
    low = text.lower()
    return [w for w in _SAVE_WORDS if w in low]


# A digit filter over the example's tokens used to live here, on the theory
# that the parrot check would reject a query for writing the one year it was
# required to write. It cannot: the parrot check is
# ``(query_tokens & example_tokens) - page_tokens``, and ``content_year`` only
# ever returns a year that is in the page, so the year is always subtracted out.
# Tested, not assumed -- see ``test_the_required_year_cannot_be_parroted``.


def check_probe(text: str, *, subtype: str, year: int | None, save_year: int,
                phrase: str | None, title_toks: set[str], zh: bool,
                max_overlap: float, example_toks: set[str],
                page_toks: set[str]) -> str:
    """Empty string means accepted; anything else is fed back to the model."""
    bad = check_content(text, title_toks, zh, max_overlap, example_toks, page_toks)
    if bad:
        return bad
    leaked = save_words_in(text)
    if leaked:
        return (f"this person is not remembering when they saved it; drop: "
                f"{', '.join(leaked[:4])}")
    if year_in(text, save_year):
        return (f"do not write the year {save_year}; write about what the page "
                f"argues instead")
    if subtype == "p_year":
        if year is None or not year_in(text, year):
            return f"the query must contain the year {year}"
    elif not phrase or phrase.lower() not in text.lower():
        return f'the query must contain the word "{phrase}"'
    return ""


# ---------------------------------------------------------------------------
# target selection
# ---------------------------------------------------------------------------

_SQL = (
    "SELECT b.id, b.url, b.title, b.folder, b.date_added, b.host, "
    "       ct.body_text, ct.char_count, ct.lang "
    "FROM bookmark b JOIN content ct ON ct.bookmark_id = b.id "
    "WHERE b.indexable = 1 AND ct.body_hash IS NOT NULL AND ct.char_count >= ? "
    "ORDER BY b.id"
)


def content_year(body: str, save_year: int, head_chars: int) -> int | None:
    """The year this page is *about*, or None if it is not about one.

    One guard beyond the protocol's two (in the body, not the save year): the
    year must appear in ``body[:head_chars]``, the slice the model is actually
    shown. Asking a model to write about a year it cannot see does not produce
    a probe, it produces an invention.

    An earlier draft also required the year to appear **twice**, to keep "©
    2024" footers out. Measured on the library, that guard cut the frame from
    468 pages to 195 -- and reading the singles showed most of them are real
    subject-matter years ("lava tubes were discovered in 2009", "dating back to
    2012"). It was stricter than the protocol, it cost more than half the
    statistical power, and the noise it removes is paired noise that cancels
    between the two rungs. It is gone.

    Ties break toward the year **furthest from the save year**. That is the
    protocol's own construction taken seriously: the point of the probe is that
    the gate resolves a window that is wrong, so where the page offers a choice,
    take the one that is most wrong. Distance is reported with the results.
    """
    counts = Counter(int(m.group(1)) for m in _CONTENT_YEAR.finditer(body))
    head = {int(m.group(1)) for m in _CONTENT_YEAR.finditer(body[:head_chars])}
    best = [(n, abs(y - save_year), y) for y, n in counts.items()
            if y in head and y != save_year]
    if not best:
        return None
    best.sort(key=lambda t: (-t[0], -t[1], -t[2]))
    return best[0][2]


def pick_targets(db: str, n: int, min_chars: int, seed: int,
                 head_chars: int) -> tuple[list[dict], dict]:
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    rows = c.execute(_SQL, (min_chars,)).fetchall()
    frame: list[dict] = []
    for r in rows:
        save_year = datetime.fromtimestamp(r["date_added"] or 0, UTC).year
        y = content_year(r["body_text"] or "", save_year, head_chars)
        if y is None:
            continue
        d = dict(r)
        d["content_year"] = y
        d["save_year"] = save_year
        frame.append(d)
    out = _stratify_by_year(frame, n, seed)
    _attach_neighbours(c, out)
    c.close()
    for o in out:
        o["kind"] = "body"
        o["slug"] = []
    return out, {"pages_with_body": len(rows), "pages_about_a_year": len(frame)}


def prompt_for(t: dict, body_chars: int, feedback: str) -> str:
    zh = t["zh"]
    fb = f"\n\nYour previous answer was rejected: {feedback}" if feedback else ""
    return TEMPLATE.format(
        title=(t["title"] or "")[:200] or "(untitled)",
        folder=t["folder"] or "(none)",
        body=(t["body_text"] or "")[:body_chars],
        examples=t["example_text"],
        lang="Chinese" if zh else "English",
        requirement=requirement_for(t["subtype"], zh, t.get("content_year"),
                                    t.get("phrase")),
    ) + fb


async def generate(args) -> None:
    st = get_settings()
    db = str(st.db_path)
    print("building document frequency table ...", flush=True)
    df, ndocs = build_df(db)
    rare_cut = max(2, int(args.rare_df * ndocs))

    targets, frame = pick_targets(db, args.n, args.min_chars, args.seed,
                                  args.body_chars)
    rng = random.Random(args.seed)
    for t in targets:
        t["zh"] = len(re.findall(r"[\u4e00-\u9fff]", t["title"] or "")) >= 2
        t["subtype"] = "p_year" if rng.random() < args.year_share else "p_relative"
        pool = _REL_ZH if t["zh"] else _REL_EN
        t["phrase"] = pool[rng.randrange(len(pool))]
        ex = _EXAMPLES[(t["subtype"], t["zh"])]
        t["example_text"] = ex[rng.randrange(len(ex))]
    rng.shuffle(targets)
    print(f"frame: {frame['pages_with_body']:,} pages with >= {args.min_chars} chars, "
          f"{frame['pages_about_a_year']:,} of them about a year that is not their "
          f"save year", flush=True)
    print(f"selected {len(targets)} targets; "
          f"subtypes {dict(Counter(t['subtype'] for t in targets))}; "
          f"{sum(1 for t in targets if t['zh'])} Chinese-titled; "
          f"save years {dict(sorted(Counter(t['save_year'] for t in targets).items()))}",
          flush=True)

    prov = get_provider(st)
    gate = asyncio.Semaphore(args.concurrency)
    stats: Counter = Counter()
    t0 = time.monotonic()
    done = 0

    async def one(t: dict) -> dict | None:
        nonlocal done
        material = f"{t['title'] or ''} {(t['body_text'] or '')[:20000]}"
        page_toks = tokens(material)
        title_toks = content_tokens(t["title"] or "")
        example_toks = content_tokens(t["example_text"])
        stats["asked"] += 1
        feedback = ""
        row = None
        async with gate:
            for attempt in range(args.retries + 1):
                try:
                    payload = await prov.chat_json(
                        system=SYSTEM,
                        user=prompt_for(t, args.body_chars, feedback))
                except Exception as e:  # noqa: BLE001
                    stats[f"call_error:{type(e).__name__}"] += 1
                    break
                cand = str(payload.get("query") or "").strip().strip('"').rstrip("。.")
                reason = check_probe(
                    cand, subtype=t["subtype"], year=t.get("content_year"),
                    save_year=t["save_year"], phrase=t["phrase"],
                    title_toks=title_toks, zh=t["zh"],
                    max_overlap=args.content_overlap, example_toks=example_toks,
                    page_toks=page_toks)
                if reason:
                    feedback = reason
                    stats[f"reject:{t['subtype']}"] += 1
                    continue
                stats[f"ok:{t['subtype']}:attempt{attempt}"] += 1
                row = {
                    "text": cand,
                    "qtype": "q_content",
                    "target_url": t["url"],
                    "note": t["subtype"],
                    "subtype": t["subtype"],
                    "time_token": (str(t["content_year"]) if t["subtype"] == "p_year"
                                   else t["phrase"]),
                    "save_year": t["save_year"],
                    "content_year": t["content_year"],
                    "year_distance": abs(t["content_year"] - t["save_year"]),
                }
                break
        if row is None:
            stats[f"dropped:{t['subtype']}"] += 1
        done += 1
        if done % 20 == 0:
            el = time.monotonic() - t0
            print(f"  {done}/{len(targets)} {el / 60:5.1f}min "
                  f"eta={(len(targets) - done) / max(done / el, 1e-9) / 60:5.1f}min "
                  f"kept={sum(v for k, v in stats.items() if k.startswith('ok:'))}",
                  flush=True)
        return row

    out = [r for r in await asyncio.gather(*(one(t) for t in targets)) if r]
    await prov.aclose()

    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        fh.write(f"// generated {datetime.now(UTC).isoformat()} from {db}\n")
        fh.write("// gate-precision probe set; protocol: "
                 "docs/gate-precision-protocol.md\n")
        fh.write(f"// targets={len(targets)} min_chars={args.min_chars} "
                 f"year_share={args.year_share} seed={args.seed} "
                 f"content_overlap_max={args.content_overlap} "
                 f"rare_df_cut={rare_cut} ndocs={ndocs}\n")
        for r in out:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    by_sub = Counter(r["subtype"] for r in out)
    summary = {
        "targets": len(targets),
        "queries": len(out),
        "by_subtype": dict(by_sub),
        "frame": frame,
        "drop_rate": {
            s: round(stats[f"dropped:{s}"] / max(sum(1 for t in targets
                                                     if t["subtype"] == s), 1), 4)
            for s in ("p_year", "p_relative")
        },
        "stats": dict(stats.most_common()),
        "minutes": round((time.monotonic() - t0) / 60, 1),
        "usage": prov.usage.as_dict(),
    }
    path.with_suffix(".summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nPROBE_DONE " + json.dumps(summary, ensure_ascii=False), flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=400, help="targets to ask about")
    ap.add_argument("--out", default="/workspace/corpus3/gate-probe.jsonl")
    ap.add_argument("--min-chars", type=int, default=300)
    ap.add_argument("--body-chars", type=int, default=2500)
    ap.add_argument("--rare-df", type=float, default=0.01)
    ap.add_argument("--content-overlap", type=float, default=0.6)
    ap.add_argument("--year-share", type=float, default=0.6,
                    help="fraction of probes that carry a content year; the "
                         "rest carry a relative time word")
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--concurrency", type=int, default=12)
    ap.add_argument("--seed", type=int, default=20260808)
    asyncio.run(generate(ap.parse_args()))


if __name__ == "__main__":
    main()
