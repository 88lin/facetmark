"""Generate the evaluation query set from real fetched pages.

Three query types, because the ablation's whole claim is that different kinds
of forgetting need different retrieval mechanisms. Each type has a validator,
and the validators are the point of this file -- a generator without them
produces queries that look plausible and silently destroy the experiment.

``q_content``   the user remembers roughly what the page said.
                Gates: at least one content token absent from the title, and
                no more than ``--content-overlap`` of its content tokens shared
                with the title. The first gate alone lets "多面手和专才专题"
                through: the title plus one filler word, which every rung
                answers perfectly, so the type stops separating anything.

``q_vague``     the user remembers only what the page was *for*, in their own
                words. This type decides C-B, so it is worthless if the model
                borrows the page's vocabulary.
                Gates: (1) no *rare* token shared with the page -- rare being
                document frequency below ``--rare-df`` of the library, and one
                such token lets BM25 find the target without understanding
                anything; (2) no more than ``--title-overlap`` of its content
                tokens shared with the title, which catches the compositional
                leak that gate 1 misses ("hide photo inside photo" holds no
                rare token but is a translation of the title).

``q_episodic``  the user remembers *when*, or *what else they were saving*.
                The time expression is **not** written by the model. A 3B model
                asked to date a page relative to today gets it wrong nearly
                every time -- in the v2 smoke test, five times out of five --
                and a wrong date is worse than no date: it turns the D-C
                comparison, the one the contextual facet is on trial for, into
                a measurement of noise. So the phrase is computed here from
                ``date_added``, the model writes only the topical hint, and the
                composed query is then parsed by the *product's own*
                ``understand.classify`` and rejected unless the resolved window
                actually contains the save time. Wrong dates become impossible
                by construction rather than unlikely by prompting.

                Three subtypes, in the mix given by ``--episodic-mix``:
                  ``year``      an absolute year, the coarsest thing the
                                resolver understands.
                  ``relative``  今年/去年/前年/最近, chosen to be true.
                  ``anchor``    no date at all, only a vague episodic marker
                                plus a hint about a page saved in the same
                                sitting. This is the only subtype that
                                exercises anchor-then-window, so it is kept
                                even though it is the hardest.

Failures are retried with the reason fed back to the model, then dropped and
counted. Both a silently kept bad query and a silently dropped one corrupt the
measurement, so the drop rate is reported next to the numbers.

**Pages with no text.** The three types above all read the body, so for years
this generator could only see pages the fetcher succeeded on. Measured on the
W1 library that was 79% of it: 500 of 2,376 bookmarks have ``char_count = 0``
-- fetch failures, login walls, pure client-side apps, PDFs -- and every W1
conclusion silently excluded them (see ``docs/w4-intent-strata.md`` §2.6).
Those pages are not a rounding error; they are exactly where the intent facet
was caught inventing 62% of its vocabulary, because there was nothing to read.

``--bodyless-share`` adds a second target pool drawn from them. The material is
what a person could actually have seen: the title, the words in the address,
the folder, the save time, and the titles saved in the same sitting. Two
consequences are deliberate:

  * **No ``q_content``.** Remembering the subject matter of a page whose text
    we never captured is not a query we can write, only one we can invent, and
    an invented one puts words in the query set that the page may never have
    contained. The body-less pool emits ``q_vague`` and ``q_episodic`` only.

  * **The address is treated as leaked vocabulary.** It is indexed, so a vague
    query that reuses the slug is solved lexically before retrieval begins --
    the same trap that made v1's ``q_content`` (the title, verbatim) score
    100%. The rare-token gate therefore covers title *and* slug, which makes
    this pool harder to satisfy than the body pool, and its drop rate higher.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import sqlite3
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

from facetmark.config import get_settings
from facetmark.providers import get_provider
from facetmark.search.understand import _RELATIVE, classify
from facetmark.text import segment, segment_query

SYSTEM = (
    "You write realistic search queries that a person types months after "
    "bookmarking a page, when they only half-remember it. You answer with a "
    "single JSON object and nothing else."
)

# Deliberately invented pages, rotated per target. The v2 examples described a
# page that is actually in the corpus and the model echoed them verbatim; a
# single example, even an invented one, still stamps its frame on a third of
# the output -- in the v3 smoke test "帮人选择一个网络库" came back as the vague
# query for a page about artificial photosynthesis.
EXAMPLES_EN = (
    """EXAMPLE (page: "Choosing a Rust HTTP client in 2021")
{"content": "comparing rust http client throughput", "vague": "the writeup that helped me pick a networking library", "hint": "I was rewriting the backend"}""",
    """EXAMPLE (page: "Sous vide brisket without a smoker")
{"content": "long low temperature beef in a water bath", "vague": "the trick for getting tough meat tender indoors", "hint": "I was cooking for a crowd"}""",
    """EXAMPLE (page: "What the EU AI Act actually requires of small vendors")
{"content": "obligations for limited risk systems and disclosure", "vague": "the plain english explainer about the new rules", "hint": "the compliance paperwork was piling up"}""",
    """EXAMPLE (page: "Teardown: why this laptop hinge always cracks")
{"content": "stress concentration in the hinge mounting bracket", "vague": "the post explaining why the lid keeps breaking", "hint": "my old machine was falling apart"}""",
)

EXAMPLES_ZH = (
    """\u793a\u4f8b\uff08\u9875\u9762\uff1a\u300a2021 \u5e74\u9009\u578b Rust HTTP \u5ba2\u6237\u7aef\u300b\uff09
{"content": "\u51e0\u4e2a rust \u7f51\u7edc\u5e93\u7684\u541e\u5410\u5bf9\u6bd4", "vague": "\u90a3\u7bc7\u5e2e\u6211\u62ff\u4e3b\u610f\u9009\u5e93\u7684\u6d4b\u8bc4", "hint": "\u5f53\u65f6\u5728\u91cd\u5199\u540e\u7aef"}""",
    """\u793a\u4f8b\uff08\u9875\u9762\uff1a\u300a\u4e0d\u7528\u70df\u718f\u7089\u505a\u4f4e\u6e29\u725b\u80f8\u8089\u300b\uff09
{"content": "\u4f4e\u6e29\u6c34\u6d74\u957f\u65f6\u95f4\u5904\u7406\u725b\u8089", "vague": "\u90a3\u7bc7\u8bb2\u600e\u4e48\u628a\u67f4\u8089\u5f04\u5ae9\u7684", "hint": "\u90a3\u9635\u5b50\u8981\u7ed9\u5f88\u591a\u4eba\u505a\u996d"}""",
    """\u793a\u4f8b\uff08\u9875\u9762\uff1a\u300a\u6b27\u76df AI \u6cd5\u6848\u5bf9\u5c0f\u5382\u5546\u5230\u5e95\u8981\u6c42\u4ec0\u4e48\u300b\uff09
{"content": "\u6709\u9650\u98ce\u9669\u7cfb\u7edf\u7684\u544a\u77e5\u4e49\u52a1", "vague": "\u90a3\u7bc7\u628a\u65b0\u89c4\u5b9a\u8bf4\u4eba\u8bdd\u7684\u89e3\u8bfb", "hint": "\u5408\u89c4\u6750\u6599\u5806\u6210\u5c71\u7684\u65f6\u5019"}""",
    """\u793a\u4f8b\uff08\u9875\u9762\uff1a\u300a\u62c6\u89e3\uff1a\u8fd9\u6b3e\u7b14\u8bb0\u672c\u7684\u8f6c\u8f74\u4e3a\u4ec0\u4e48\u603b\u88c2\u300b\uff09
{"content": "\u8f6c\u8f74\u5b89\u88c5\u5ea7\u7684\u5e94\u529b\u96c6\u4e2d", "vague": "\u90a3\u7bc7\u89e3\u91ca\u5c4f\u5e55\u4e3a\u4ec0\u4e48\u8001\u574f\u7684\u6587\u7ae0", "hint": "\u65e7\u673a\u5668\u5feb\u6563\u67b6\u4e86"}""",
)

TEMPLATE = """A person bookmarked this page and is now trying to find it again.

TITLE: {title}
FOLDER: {folder}
SAVED IN THE SAME SITTING AS: {neighbours}
PAGE TEXT:
{body}

{examples}

Answer in {lang}. Each value is one natural phrase of 4-14 words (or 8-25
Chinese characters) that a person would actually type into a search box.
Lowercase, no quotes, no trailing punctuation, and NOT a list of keywords
separated by commas.

"content" -- what they type remembering the SUBJECT MATTER. Use words from the
   page's argument, not its title. Most of the words must be ones the title
   does not use.

"vague"   -- what they type remembering only what the page was FOR. Describe
   the purpose, or the problem it solved, in everyday words, as if explaining
   it to a friend who has never seen the page. Use no proper noun, product
   name, library name, acronym or unusual technical term from the page, do not
   paraphrase the title, and make it clearly different from your "content"
   answer rather than a shortened copy of it.{avoid}

"hint"    -- {hint_brief} Keep it under ten words, stay general, and write NO
   date, NO year, NO month and NO season: the date is added separately and
   yours would be wrong.

The example above is about a different page. Take its shape, never its words.

JSON only: {{"content": "...", "vague": "...", "hint": "..."}}"""

BODYLESS_TEMPLATE = """A person bookmarked this page and is now trying to find it
again. Nobody knows what the page says -- the fetch failed, or it is behind a
login, or it renders entirely in the browser. Everything that is known about it
is below, and it is all you may use.

TITLE: {title}
ADDRESS: {url}
WORDS IN THE ADDRESS: {slug}
FOLDER: {folder}
SAVED IN THE SAME SITTING AS: {neighbours}

{examples}

Answer in {lang}. Each value is one natural phrase of 4-14 words (or 8-25
Chinese characters) that a person would actually type into a search box.
Lowercase, no quotes, no trailing punctuation, and NOT a list of keywords
separated by commas.

"vague"   -- what they type remembering only what the page was FOR. Say what a
   page with this title, at this address, is *for* -- what someone opens it to
   do -- in everyday words, as if explaining it to a friend who has never seen
   it. Use none of the distinctive words from the title or from the address: no
   proper noun, product name, library name, acronym or unusual technical term
   from either. If the title tells you almost nothing, describe the kind of
   thing it is rather than inventing a topic for it.{avoid}

"hint"    -- {hint_brief} Keep it under ten words, stay general, and write NO
   date, NO year, NO month and NO season: the date is added separately and
   yours would be wrong.

Do NOT write a "content" answer. Nobody read this page, and a guessed one would
put words into the query set that the page may never have contained.

The example above is about a different page. Take its shape, never its words.

JSON only: {{"vague": "...", "hint": "..."}}"""

HINT_TOPIC = (
    "the situation they were in when they saved this page -- what they were "
    "working on or curious about, described loosely rather than by name."
)
HINT_NEIGHBOUR = (
    "what ELSE they were saving in that same sitting -- lean on the pages "
    "listed above rather than on this one."
)

#: The model answers three keys; the query file names three types. Ordered,
#: because the emitted file is read by humans as much as by the harness.
KEY_TO_QTYPE = {"content": "q_content", "vague": "q_vague", "hint": "q_episodic"}


# ---------------------------------------------------------------------------
# tokenisation shared with the index
# ---------------------------------------------------------------------------

_TOKEN = re.compile(r"[0-9a-z_\u4e00-\u9fff]+")

#: Time words that satisfy the episodic requirement but do not count towards
#: the "at least two other tokens" rule.
_TIME_RE = re.compile(
    r"(20[0-2]\d)|(去年|前年|今年|上个?月|这个?月|最近|年初|年底|年中"
    r"|春天|夏天|秋天|冬天|一月|二月|三月|四月|五月|六月|七月|八月|九月|十月"
    r"|十一月|十二月|\d{1,2}月)"
    r"|\b(last|this|early|late|recently|spring|summer|autumn|fall|winter|january"
    r"|february|march|april|may|june|july|august|september|october|november"
    r"|december|year|month)\b",
    re.I,
)
_STOP = {
    "the", "that", "this", "with", "for", "and", "was", "were", "have", "had",
    "about", "from", "into", "when", "what", "which", "some", "thing", "stuff",
    "saved", "bookmark", "page", "article", "post", "one", "you", "your",
    "那个", "这个", "那些", "存的", "保存", "收藏", "文章", "网页", "东西", "时候",
    "一个", "的", "了", "在", "是", "和", "关于", "怎么", "如何",
}

def tokens(text: str) -> set[str]:
    return {t for t in _TOKEN.findall(segment(text.lower())) if len(t) > 1}


def query_tokens(text: str) -> set[str]:
    return {t for t in _TOKEN.findall(segment_query(text.lower())) if len(t) > 1}


def content_tokens(text: str) -> set[str]:
    return {t for t in query_tokens(text) if t not in _STOP and not _TIME_RE.fullmatch(t)}


def cjk_ratio(text: str) -> float:
    letters = re.findall(r"[a-zA-Z\u4e00-\u9fff]", text)
    if not letters:
        return 0.0
    return sum(1 for c in letters if "\u4e00" <= c <= "\u9fff") / len(letters)


#: Path components that say nothing about the page. Left in, they crowd out the
#: two or three words that carry the meaning and invite the model to write a
#: query about "articles" or "index".
_URL_NOISE = {
    "http", "https", "www", "com", "net", "org", "edu", "gov", "io", "cn", "co",
    "html", "htm", "php", "asp", "aspx", "jsp", "shtml", "amp", "index",
    "default", "home", "main", "page", "pages", "post", "posts", "article",
    "articles", "blog", "news", "view", "detail", "details", "content", "item",
    "items", "show", "read", "en", "zh", "cgi", "bin", "static", "wp", "id",
    "utm", "src", "ref", "pdf", "wiki", "docs", "doc", "tag", "tags",
    "category", "categories", "archive", "archives", "search", "mobile", "app",
}

_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_HEXISH = re.compile(r"[0-9a-f]{8,}|[a-z]*\d{4,}[a-z]*")


def url_slug_words(url: str, limit: int = 12) -> list[str]:
    """The words a person could have read off the address bar, in order.

    Kept deliberately lossy: percent-escapes decoded, camel case split, ids and
    hashes and file extensions dropped. What survives is the handful of words a
    human would recognise -- which is both what the prompt may show and, more
    importantly, what the leak gate must forbid the query from reusing.
    """
    try:
        path = unquote(urlsplit(url).path)
    except ValueError:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for chunk in re.split(r"[^0-9A-Za-z\u4e00-\u9fff]+", _CAMEL.sub(" ", path)):
        for word in re.findall(r"[\u4e00-\u9fff]+|[A-Za-z]+|\d+", chunk):
            low = word.lower()
            if low in _URL_NOISE or low.isdigit() or _HEXISH.fullmatch(low):
                continue
            if len(low) < 2 and not re.match(r"[\u4e00-\u9fff]", word):
                continue
            if low not in seen:
                seen.add(low)
                out.append(low)
    return out[:limit]


def example_without_content(block: str) -> str:
    """Drop the ``content`` key from a shared example.

    The body-less prompt asks for two keys, and an example showing three is an
    invitation to answer the question it says not to answer.
    """
    return re.sub(r'\{"content": "[^"]*", ', "{", block)


def build_df(db: str) -> tuple[Counter, int]:
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = c.execute(
        "SELECT b.title, coalesce(ct.body_text,'') FROM bookmark b "
        "LEFT JOIN content ct ON ct.bookmark_id = b.id WHERE b.indexable = 1"
    ).fetchall()
    c.close()
    df: Counter = Counter()
    for title, body in rows:
        df.update(tokens(f"{title or ''} {body[:20000]}"))
    return df, len(rows)


# ---------------------------------------------------------------------------
# the time phrase, computed rather than hallucinated
# ---------------------------------------------------------------------------

_YEAR_EN = ("in {y}", "back in {y}", "sometime in {y}")
_YEAR_ZH = ("{y}年", "{y}年那会儿", "大概{y}年")
_ANCHOR_EN = ("back when", "around the time")
_ANCHOR_ZH = ("那阵子", "那段时间", "当时")

#: Surfaces we are willing to emit for each relative rule in the product's own
#: table, keyed by that table's pattern. Deriving the candidates from
#: ``_RELATIVE`` rather than restating the windows here is the point: a marker
#: is only offered if the shipped resolver puts its window over the save time,
#: so "去年" can never be attached to a page from fourteen months ago.
_RELATIVE_SURFACE: dict[str, tuple[str | None, str | None]] = {
    r"这个月|本月|this month": ("这个月", "this month"),
    r"上个月|上月|last month": ("上个月", "last month"),
    r"最近|recently|lately": ("最近", "recently"),
    r"今年|this year": ("今年", "this year"),
    r"去年|last year": ("去年", "last year"),
    r"前年": ("前年", None),
}


#: Calendar truth, checked *in addition* to the resolver's window. The product
#: windows are deliberately fuzzy -- "去年" spans 1.3 years -- so containment
#: alone would let "前年" be attached to a page from 35 months ago just because
#: the fuzzy window reaches that far. A query set validated only against the
#: system under test is calibrated to that system's opinions; this second
#: predicate is what a person would agree with.
def _calendar_ok(pattern: str, saved: datetime, now: datetime) -> bool:
    if pattern.startswith("这个月"):
        return (saved.year, saved.month) == (now.year, now.month)
    if pattern.startswith("上个月"):
        prev = (now.year, now.month - 1) if now.month > 1 else (now.year - 1, 12)
        return (saved.year, saved.month) == prev
    if pattern.startswith("最近"):
        return 0 <= (now - saved).days <= 90
    if pattern.startswith("今年"):
        return saved.year == now.year
    if pattern.startswith("去年"):
        return saved.year == now.year - 1
    if pattern.startswith("前年"):
        return saved.year == now.year - 2
    return False


def true_relative_markers(saved: datetime, now: datetime, zh: bool) -> list[str]:
    saved_ts, now_ts = int(saved.timestamp()), int(now.timestamp())
    out: list[str] = []
    for pattern, start_ago, end_ago in _RELATIVE:
        surface = _RELATIVE_SURFACE.get(pattern)
        if not surface:
            continue
        word = surface[0] if zh else surface[1]
        if not word or not _calendar_ok(pattern, saved, now):
            continue
        if now_ts - start_ago <= saved_ts <= now_ts - end_ago:
            out.append(word)
    return out


def time_phrase(subtype: str, saved: datetime, now: datetime, zh: bool,
                rng: random.Random) -> str:
    if subtype == "anchor":
        return rng.choice(_ANCHOR_ZH if zh else _ANCHOR_EN)
    if subtype == "relative":
        cands = true_relative_markers(saved, now, zh)
        if cands:
            return rng.choice(cands)
    return rng.choice(_YEAR_ZH if zh else _YEAR_EN).format(y=saved.year)


def compose_episodic(phrase: str, hint: str, zh: bool, rng: random.Random) -> str:
    """Join the computed phrase and the model's hint into one query.

    Word order follows how the marker is normally used, not a fixed slot: an
    anchor marker leads ("那阵子 ..."), a date trails ("... in 2023"). The
    resolver does not care, but a query set nobody would believe a person
    typed is a query set nobody should believe the numbers from.
    """
    hint = hint.strip().rstrip("。.")
    if zh:
        tail = rng.choice(("存的", "收的", "存的那篇"))
        if phrase in _ANCHOR_ZH:
            return f"{phrase}{hint}{tail}"
        return f"{phrase}{hint}{tail}"
    if phrase in _ANCHOR_EN:
        return f"{phrase} {hint}"
    return f"{hint} {phrase}"


# ---------------------------------------------------------------------------
# validators -- one per query type, each returning "" or a reason to retry
# ---------------------------------------------------------------------------


def check_shape(text: str, zh: bool, example_toks: set[str],
                page_toks: set[str]) -> str:
    if not text:
        return "empty"
    if len(text) < (8 if zh else 15):
        return "too short, write a phrase not a keyword"
    if len(text) > 120:
        return "too long"
    if len(content_tokens(text)) < 2:
        return "needs at least two meaningful words"
    if len(re.findall(r"[,\uff0c;\uff1b\u3001/|]", text)) >= 2:
        return "this is a keyword list; write one natural phrase instead"
    r = cjk_ratio(text)
    if zh and r < 0.5:
        return "answer in Chinese"
    if not zh and r > 0.3:
        return "answer in English"
    # A word taken from the example that the page itself never uses is the
    # example bleeding through, and it points the query at the wrong page.
    parroted = sorted((content_tokens(text) & example_toks) - page_toks)
    if parroted:
        return (f"the example is about a different page; drop: "
                f"{', '.join(parroted[:6])}")
    return ""


def check_content(text: str, title_toks: set[str], zh: bool, max_overlap: float,
                  example_toks: set[str], page_toks: set[str]) -> str:
    bad = check_shape(text, zh, example_toks, page_toks)
    if bad:
        return bad
    ct = content_tokens(text)
    shared = ct & title_toks
    if ct <= title_toks:
        return ("every word is already in the title; use a word from the body of "
                "the page instead")
    if ct and len(shared) / len(ct) > max_overlap:
        return (f"this is the title with a word added; say what the page argues, "
                f"avoiding: {', '.join(sorted(shared)[:8])}")
    return ""


def check_vague(text: str, page_rare: set[str], title_toks: set[str],
                zh: bool, max_overlap: float, example_toks: set[str],
                page_toks: set[str], content_cand: str) -> str:
    bad = check_shape(text, zh, example_toks, page_toks)
    if bad:
        return bad
    ct = content_tokens(text)
    leaked = sorted(ct & page_rare)
    if leaked:
        return f"do not use these words from the page: {', '.join(leaked[:8])}"
    shared = ct & title_toks
    if ct and len(shared) / len(ct) > max_overlap:
        return (f"this is a paraphrase of the title; avoid: "
                f"{', '.join(sorted(shared)[:8])}")
    # C-B is the comparison this type decides. If it is the content query with
    # two words removed, the two types measure the same thing twice.
    cc = content_tokens(content_cand)
    if cc and len(ct & cc) / len(ct | cc) > 0.5:
        return "too close to your content answer; describe the purpose, not the subject"
    return ""


def check_hint(text: str, page_rare: set[str], zh: bool, example_toks: set[str],
               page_toks: set[str], content_cand: str) -> str:
    """The model's half of an episodic query: topic only, never a date."""
    bad = check_shape(text, zh, example_toks, page_toks)
    if bad:
        return bad
    if _TIME_RE.search(text):
        return "remove the date; a date is added automatically and yours is wrong"
    leaked = sorted(content_tokens(text) & page_rare)
    if leaked:
        return f"too specific, do not name: {', '.join(leaked[:8])}"
    ct, cc = content_tokens(text), content_tokens(content_cand)
    if cc and len(ct & cc) / len(ct | cc) > 0.5:
        return "too close to your content answer; say what you were doing, not what the page says"
    return ""


def check_episodic_resolves(text: str, subtype: str, saved_ts: int,
                            now_ts: int) -> str:
    """Parse the composed query with the product's own understanding layer.

    This is the gate that makes the type trustworthy. If the shipped resolver
    cannot turn the query into a window containing the save time, the query
    carries no episodic signal whatever the words look like, and scoring it
    would credit or blame the contextual facet for something it never saw.
    """
    u = classify(text, now_ts=now_ts)
    if subtype == "anchor":
        if not u.is_episodic:
            return "not recognised as episodic"
        return ""
    if u.time_window is None:
        return "no resolvable time window"
    lo, hi = u.time_window
    if not (lo <= saved_ts <= hi):
        return (f"window {datetime.fromtimestamp(lo, UTC):%Y-%m} .."
                f"{datetime.fromtimestamp(hi, UTC):%Y-%m} excludes the save time")
    return ""


# ---------------------------------------------------------------------------
# target selection
# ---------------------------------------------------------------------------


_BODY_SQL = (
    "SELECT b.id, b.url, b.title, b.folder, b.date_added, b.host, "
    "       ct.body_text, ct.char_count, ct.lang "
    "FROM bookmark b JOIN content ct ON ct.bookmark_id = b.id "
    "WHERE b.indexable = 1 AND ct.body_hash IS NOT NULL AND ct.char_count >= ? "
    "ORDER BY b.id"
)

#: Everything indexable the fetcher came back empty-handed on. ``LEFT JOIN``
#: because a bookmark with no ``content`` row at all belongs here too, and an
#: inner join would quietly shrink the pool it is supposed to expose.
_BODYLESS_SQL = (
    "SELECT b.id, b.url, b.title, b.folder, b.date_added, b.host, "
    "       '' AS body_text, 0 AS char_count, ct.lang "
    "FROM bookmark b LEFT JOIN content ct ON ct.bookmark_id = b.id "
    "WHERE b.indexable = 1 AND coalesce(ct.char_count, 0) = 0 "
    "ORDER BY b.id"
)


def _stratify_by_year(rows: list, n: int, seed: int) -> list[dict]:
    """Stratified by save year, so episodic queries are not all from 2026."""
    if not rows or n <= 0:
        return []
    by_year: dict[int, list] = {}
    for r in rows:
        by_year.setdefault(datetime.fromtimestamp(r["date_added"] or 0, UTC).year,
                           []).append(r)
    rng = random.Random(seed)
    out: list[dict] = []
    for _y, v in sorted(by_year.items()):
        pool = list(v)
        rng.shuffle(pool)
        out.extend(dict(r) for r in pool[: max(1, round(n * len(v) / len(rows)))])
    rng.shuffle(out)
    return out[:n]


def _attach_neighbours(c: sqlite3.Connection, out: list[dict]) -> None:
    ids = [o["id"] for o in out]
    nb: dict[int, list[str]] = {}
    for i in range(0, len(ids), 400):
        chunk = ids[i:i + 400]
        marks = ",".join("?" * len(chunk))
        for bid, title in c.execute(
            f"""SELECT s1.bookmark_id, b2.title FROM bookmark_session s1
                JOIN bookmark_session s2 ON s2.session_id = s1.session_id
                                        AND s2.bookmark_id != s1.bookmark_id
                JOIN bookmark b2 ON b2.id = s2.bookmark_id
                WHERE s1.bookmark_id IN ({marks})""", chunk):
            nb.setdefault(bid, []).append(title)
    for o in out:
        o["neighbours"] = nb.get(o["id"], [])[:3]


def pick_targets(db: str, n: int, min_chars: int, seed: int) -> list[dict]:
    """Pages with enough text to write a content query about."""
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    rows = c.execute(_BODY_SQL, (min_chars,)).fetchall()
    out = _stratify_by_year(rows, n, seed)
    _attach_neighbours(c, out)
    c.close()
    for o in out:
        o["kind"] = "body"
        o["slug"] = []
    return out


def pick_bodyless_targets(db: str, n: int, seed: int) -> tuple[list[dict], int]:
    """Pages the fetcher never got text for. Returns the pool and how many of
    them had nothing usable to write a query from.

    "Usable" is two content words across the title and the address. Below that
    -- a bare host, an untitled id, ``login`` -- the only honest query is one
    the model would have to invent, so the page is skipped and counted rather
    than filled in.
    """
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    rows = []
    unusable = 0
    for r in c.execute(_BODYLESS_SQL):
        slug = url_slug_words(r["url"] or "")
        if len(content_tokens(f"{r['title'] or ''} {' '.join(slug)}")) < 2:
            unusable += 1
            continue
        rows.append((r, slug))
    out = _stratify_by_year([r for r, _ in rows], n, seed)
    _attach_neighbours(c, out)
    c.close()
    slugs = {r["id"]: s for r, s in rows}
    for o in out:
        o["kind"] = "bodyless"
        o["slug"] = slugs.get(o["id"], [])
    return out, unusable


def bodyless_share(db: str, min_chars: int) -> float:
    """The share of the *eligible* library that has no text.

    Eligible means "could be sampled at all": pages with 1..min_chars-1
    characters are in neither pool, so they are excluded from the denominator
    rather than silently counted as if the generator could reach them.
    """
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    n_body = c.execute(
        "SELECT COUNT(*) FROM bookmark b JOIN content ct ON ct.bookmark_id = b.id "
        "WHERE b.indexable = 1 AND ct.body_hash IS NOT NULL AND ct.char_count >= ?",
        (min_chars,)).fetchone()[0]
    n_bodyless = c.execute(
        "SELECT COUNT(*) FROM bookmark b LEFT JOIN content ct ON ct.bookmark_id = b.id "
        "WHERE b.indexable = 1 AND coalesce(ct.char_count, 0) = 0").fetchone()[0]
    c.close()
    total = n_body + n_bodyless
    return (n_bodyless / total) if total else 0.0


# ---------------------------------------------------------------------------
# generation
# ---------------------------------------------------------------------------


def prompt_for(t: dict, body_chars: int, subtype: str, feedback: dict[str, str]) -> str:
    nb = "; ".join(x[:60] for x in t["neighbours"]) or "(nothing else that sitting)"
    zh = t["zh"]
    pool = EXAMPLES_ZH if zh else EXAMPLES_EN
    fb = ""
    if feedback:
        fb = "\n\nYour previous answer was rejected:\n" + "\n".join(
            f'  "{k}": {v}' for k, v in feedback.items())
    avoid = feedback.get("vague", "")
    common = {
        "title": (t["title"] or "")[:200] or "(untitled)",
        "folder": t["folder"] or "(none)",
        "neighbours": nb,
        "lang": "Chinese" if zh else "English",
        "hint_brief": HINT_NEIGHBOUR if subtype == "anchor" else HINT_TOPIC,
        "avoid": f" {avoid}" if avoid else "",
    }
    if t.get("kind") == "bodyless":
        return BODYLESS_TEMPLATE.format(
            url=(t["url"] or "")[:200],
            slug=", ".join(t["slug"]) or "(none)",
            examples=example_without_content(pool[t["example"] % len(pool)]),
            **common) + fb
    return TEMPLATE.format(
        body=(t["body_text"] or "")[:body_chars],
        examples=pool[t["example"] % len(pool)], **common) + fb


def choose_subtype(t: dict, mix: tuple[float, float, float], rng: random.Random) -> str:
    """anchor needs neighbours to lean on; without them it degenerates."""
    r = rng.random()
    if r < mix[0]:
        return "year"
    if r < mix[0] + mix[1]:
        return "relative"
    return "anchor" if t["neighbours"] else "year"


async def generate(args) -> None:
    st = get_settings()
    db = str(st.db_path)
    now = datetime.now(UTC)
    now_ts = int(now.timestamp())
    print("building document frequency table ...", flush=True)
    df, ndocs = build_df(db)
    rare_cut = max(2, int(args.rare_df * ndocs))
    print(f"  {len(df):,} distinct tokens over {ndocs:,} docs; rare = df < {rare_cut}",
          flush=True)

    share = args.bodyless_share
    if share < 0:
        share = bodyless_share(db, args.min_chars)
        print(f"  --bodyless-share not given; using the library's own share "
              f"{share:.3f}", flush=True)
    n_bodyless = min(round(args.n * share), args.n)
    targets = pick_targets(db, args.n - n_bodyless, args.min_chars, args.seed)
    bodyless, unusable = ((pick_bodyless_targets(db, n_bodyless, args.seed))
                          if n_bodyless else ([], 0))
    if n_bodyless and len(bodyless) < n_bodyless:
        # Asking for more text-less pages than exist is a fact about the
        # library, not a failure; say so rather than silently returning fewer.
        print(f"  only {len(bodyless)} usable text-less pages available "
              f"(asked for {n_bodyless}; {unusable} had nothing to write from)",
              flush=True)
    targets = targets + bodyless

    rng = random.Random(args.seed)
    mix = tuple(float(x) for x in args.episodic_mix.split(","))
    for t in targets:
        t["zh"] = len(re.findall(r"[\u4e00-\u9fff]", t["title"] or "")) >= 2
        t["saved"] = datetime.fromtimestamp(t["date_added"] or 0, UTC)
        t["subtype"] = choose_subtype(t, mix, rng)
        t["example"] = rng.randrange(4)
        t["phrase"] = time_phrase(t["subtype"], t["saved"], now, t["zh"], rng)
    rng.shuffle(targets)
    yrs = Counter(t["saved"].year for t in targets)
    print(f"selected {len(targets)} targets ({len(bodyless)} with no page text, "
          f"{unusable} text-less pages skipped as unwritable); "
          f"years {dict(sorted(yrs.items()))}; "
          f"{sum(1 for t in targets if t['neighbours'])} have session neighbours; "
          f"subtypes {dict(Counter(t['subtype'] for t in targets))}; "
          f"{sum(1 for t in targets if t['zh'])} Chinese-titled", flush=True)

    prov = get_provider(st)
    gate = asyncio.Semaphore(args.concurrency)
    stats: Counter = Counter()
    t0 = time.monotonic()
    done = 0

    async def one(t: dict) -> list[dict]:
        nonlocal done
        bodyless = t["kind"] == "bodyless"
        # What the page puts in front of a person, and therefore what a query
        # may not simply hand back. For a text-less page that is the title plus
        # the address; both are indexed, so both leak.
        material = (f"{t['title'] or ''} {' '.join(t['slug'])} {t['folder'] or ''}"
                    if bodyless else
                    f"{t['title'] or ''} {(t['body_text'] or '')[:20000]}")
        page_toks = tokens(material)
        page_rare = {tok for tok in page_toks if df.get(tok, 0) < rare_cut}
        title_toks = content_tokens(t["title"] or "")
        if bodyless:
            title_toks = title_toks | content_tokens(" ".join(t["slug"]))
        zh = t["zh"]
        pool = EXAMPLES_ZH if zh else EXAMPLES_EN
        example_toks = content_tokens(pool[t["example"] % len(pool)])
        saved_ts = int(t["saved"].timestamp())
        keys = ("vague", "hint") if bodyless else ("content", "vague", "hint")
        for _k, qt in KEY_TO_QTYPE.items():
            if _k in keys:
                stats[f"asked:{qt}"] += 1
        accepted: dict[str, str] = {}
        feedback: dict[str, str] = {}
        async with gate:
            for attempt in range(args.retries + 1):
                if len(accepted) == len(keys):
                    break
                try:
                    payload = await prov.chat_json(
                        system=SYSTEM,
                        user=prompt_for(t, args.body_chars, t["subtype"], feedback))
                except Exception as e:  # noqa: BLE001
                    stats[f"call_error:{type(e).__name__}"] += 1
                    break
                feedback = {}
                content_cand = accepted.get("content") or str(payload.get("content") or "")
                if bodyless:
                    # There is no content answer to differ from, so the vague
                    # answer takes its place: the hint must still say something
                    # the query set does not already contain twice.
                    content_cand = accepted.get("vague", "")
                for key in keys:
                    if key in accepted:
                        continue
                    cand = str(payload.get(key) or "").strip().strip('"').rstrip("。.")
                    if key == "content":
                        reason = check_content(cand, title_toks, zh, args.content_overlap,
                                               example_toks, page_toks)
                    elif key == "vague":
                        reason = check_vague(cand, page_rare, title_toks, zh,
                                             args.title_overlap, example_toks,
                                             page_toks, content_cand)
                    else:
                        reason = check_hint(cand, page_rare, zh, example_toks,
                                            page_toks, content_cand)
                        if not reason:
                            composed = compose_episodic(t["phrase"], cand, zh, rng)
                            reason = check_episodic_resolves(
                                composed, t["subtype"], saved_ts, now_ts)
                            if reason:
                                # The phrase is ours, so a resolver failure is our
                                # bug, not the model's. Do not ask it to retry.
                                stats[f"resolve_fail:{t['subtype']}"] += 1
                            else:
                                cand = composed
                    if reason:
                        feedback[key] = reason
                        stats[f"reject:{key}"] += 1
                    else:
                        accepted[key] = cand
                        stats[f"ok:{key}:attempt{attempt}"] += 1
        rows = []
        for key, qtype in KEY_TO_QTYPE.items():
            if key not in keys:
                continue
            if key in accepted:
                row = {"text": accepted[key], "qtype": qtype, "target_url": t["url"]}
                if bodyless:
                    # Not read by load_query_file(); downstream stratification
                    # should re-derive this from the library's char_count so it
                    # stays true if the page is re-fetched. Kept for humans.
                    row["material"] = "bodyless"
                if qtype == "q_episodic":
                    # "note" is the slot load_query_file() carries into
                    # EvalQuery; "subtype" is kept for human readability.
                    row["subtype"] = row["note"] = t["subtype"]
                rows.append(row)
            else:
                stats[f"dropped:{qtype}"] += 1
        done += 1
        if done % 20 == 0:
            el = time.monotonic() - t0
            print(f"  {done}/{len(targets)} {el / 60:5.1f}min "
                  f"eta={(len(targets) - done) / max(done / el, 1e-9) / 60:5.1f}min "
                  f"kept={sum(v for k, v in stats.items() if k.startswith('ok:'))}",
                  flush=True)
        return rows

    out: list[dict] = []
    for rows in await asyncio.gather(*(one(t) for t in targets)):
        out.extend(rows)
    await prov.aclose()

    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        fh.write(f"// generated {datetime.now(UTC).isoformat()} from {db}\n")
        fh.write(f"// targets={len(targets)} bodyless_targets={len(bodyless)} "
                 f"min_chars={args.min_chars} rare_df_cut={rare_cut} ndocs={ndocs} "
                 f"title_overlap_max={args.title_overlap} "
                 f"content_overlap_max={args.content_overlap} "
                 f"episodic_mix={args.episodic_mix}\n")
        for r in out:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    by_type = Counter(r["qtype"] for r in out)
    summary = {
        "targets": len(targets), "queries": len(out), "by_type": dict(by_type),
        "bodyless": {
            "targets": len(bodyless), "share": round(share, 4),
            "unusable_skipped": unusable,
            "queries": sum(1 for r in out if r.get("material") == "bodyless"),
        },
        "episodic_subtypes": dict(Counter(r.get("subtype", "") for r in out
                                          if r["qtype"] == "q_episodic")),
        "rare_df_cut": rare_cut, "ndocs": ndocs, "min_chars": args.min_chars,
        # Denominator is how many targets were *asked* for this type, not how
        # many targets exist: the text-less pool is never asked for q_content,
        # and dividing by every target would report a drop rate it never had.
        "drop_rate": {t: round(stats[f"dropped:{t}"] / max(stats[f"asked:{t}"], 1), 4)
                      for t in ("q_content", "q_vague", "q_episodic")},
        "stats": dict(stats.most_common()),
        "minutes": round((time.monotonic() - t0) / 60, 1),
        "usage": prov.usage.as_dict(),
    }
    path.with_suffix(".summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nQUERIES_DONE " + json.dumps(summary, ensure_ascii=False), flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200,
                    help="total targets, split between the two pools")
    ap.add_argument("--out", default="/workspace/corpus/queries.jsonl")
    # 800 was the W1 default and it cost the query set a third of the library
    # for no stated reason. 300 is enough text to write a content query from,
    # and moves the sampling frame on the W1 library from 65.7% to 72.7%.
    ap.add_argument("--min-chars", type=int, default=300)
    ap.add_argument("--bodyless-share", type=float, default=-1.0,
                    help="fraction of targets drawn from pages with no text; "
                         "-1 (default) uses the library's own share, 0 disables")
    ap.add_argument("--body-chars", type=int, default=2500)
    ap.add_argument("--rare-df", type=float, default=0.01)
    ap.add_argument("--title-overlap", type=float, default=0.5)
    ap.add_argument("--content-overlap", type=float, default=0.6)
    ap.add_argument("--episodic-mix", default="0.55,0.25,0.20",
                    help="fractions for year,relative,anchor")
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--concurrency", type=int, default=12)
    ap.add_argument("--seed", type=int, default=17)
    asyncio.run(generate(ap.parse_args()))


if __name__ == "__main__":
    main()
