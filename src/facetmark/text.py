"""Text handling for the lexical facet: CJK segmentation, FTS5 query building,
and the two-path lexical index sync.

Why two FTS tables (measured, not assumed):

* ``trigram`` cannot match a query shorter than 3 characters. Two-character CJK
  words (学习, 工具, 论文, 异步) are the single most common query form, and they
  return **zero** hits under trigram.
* ``unicode61`` tokenises a whole CJK run as one token, so ``机器学习`` does not
  match a document containing ``机器学习论文精读工具合集``. Useless for CJK on
  its own.
* jieba segmentation + ``unicode61`` fixes both, and ``trigram`` still earns its
  place by catching substrings that jieba splits the wrong way.

So both paths are required, and Facet 3 fuses them.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from collections.abc import Iterable

import jieba

jieba.setLogLevel(logging.ERROR)

CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3040-\u30ff]")
_WS_RE = re.compile(r"\s+")
#: FTS5 syntax characters. We quote every term instead of trying to escape
#: these individually, which is both simpler and safer.
_FTS_STRIP_RE = re.compile(r'["*():^\-]+')


def has_cjk(text: str) -> bool:
    return bool(CJK_RE.search(text or ""))


def segment(text: str) -> str:
    """Segment for indexing.

    ``cut_for_search`` emits both coarse and fine grains (全文检索 -> 全文 /
    检索 / 全文检索), which raises recall at a small index-size cost. That is the
    right trade for a personal library where a miss is the expensive outcome.
    """
    if not text:
        return ""
    if not has_cjk(text):
        return _WS_RE.sub(" ", text).strip()
    return _WS_RE.sub(" ", " ".join(jieba.cut_for_search(text))).strip()


def segment_query(text: str) -> str:
    """Segment a query.

    Uses precise mode rather than search mode: the extra fine-grained fragments
    that help an index would dilute a query into unrelated matches.
    """
    if not text:
        return ""
    if not has_cjk(text):
        return _WS_RE.sub(" ", text).strip()
    return _WS_RE.sub(" ", " ".join(jieba.cut(text))).strip()


def build_fts_query(query: str, *, segmented: bool) -> str | None:
    """Turn free-form user input into a safe FTS5 MATCH expression.

    Every term is double-quoted, so FTS5 operators typed by the user are treated
    as literal text rather than syntax. Terms are OR-ed: for bookmark retrieval,
    recall matters more than the precision of an implicit AND, and RRF fusion
    downstream will sort out the ranking.

    Returns ``None`` -- never ``""`` -- when nothing searchable survives, which
    is routine on the trigram path for short CJK queries. An empty string passed
    to ``MATCH`` raises ``fts5: syntax error``, so the caller is forced to check.
    """
    src = segment_query(query) if segmented else query
    raw_terms = [t for t in _WS_RE.split(src.strip()) if t]
    terms: list[str] = []
    for t in raw_terms:
        # Syntax characters become spaces rather than vanishing. Deleting them
        # turned "sqlite-vec" into "sqlitevec", a token that exists in no index:
        # unicode61 stores it as "sqlite" + "vec", so the query matched nothing
        # even though the page said the word. Hyphenated identifiers are the
        # normal case in a developer's library, so this was a silent hole.
        cleaned = _FTS_STRIP_RE.sub(" ", t).strip()
        for piece in _WS_RE.split(cleaned):
            if not piece:
                continue
            if not segmented and len(piece) < 3:
                # trigram path: a sub-3-character term can never match, and
                # leaving it in would turn the whole OR expression into a
                # guaranteed miss for that clause.
                continue
            quoted = f'"{piece}"'
            if quoted not in terms:
                terms.append(quoted)
    if not terms:
        return None
    return " OR ".join(terms)


def truncate_head_tail(text: str, limit: int) -> str:
    """Keep the head and the tail.

    Page bodies put the thesis at the top and the conclusion at the bottom;
    boilerplate and related-links sludge sit in the middle.
    """
    if not text or len(text) <= limit:
        return text or ""
    head = int(limit * 0.65)
    tail = limit - head
    return text[:head] + "\n...\n" + text[-tail:]


def detect_lang(text: str) -> str:
    """Coarse language tag. Only used for reporting and prompt hinting."""
    if not text:
        return "unknown"
    sample = text[:2000]
    cjk = len(CJK_RE.findall(sample))
    if cjk / max(len(sample), 1) > 0.05:
        return "zh"
    return "en"


# ---------------------------------------------------------------------------
# Lexical index sync
# ---------------------------------------------------------------------------

_FTS_UPSERT_TRI = "INSERT INTO fts_tri(rowid, title, body, summary, extra) VALUES(?,?,?,?,?)"
_FTS_UPSERT_SEG = "INSERT INTO fts_seg(rowid, title, body, summary, extra) VALUES(?,?,?,?,?)"


def _extra_blob(topics: Iterable[str], entities: Iterable[str], key_points: Iterable[str]) -> str:
    return " ".join(
        [
            *(t for t in topics if t),
            *(e for e in entities if e),
            *(k for k in key_points if k),
        ]
    )


def sync_fts(
    conn: sqlite3.Connection,
    bookmark_id: int,
    *,
    title: str,
    body: str = "",
    body_seg: str | None = None,
    summary: str = "",
    topics: Iterable[str] = (),
    entities: Iterable[str] = (),
    key_points: Iterable[str] = (),
) -> None:
    """Rewrite both lexical index rows for one bookmark.

    Delete-then-insert because FTS5 external-content UPDATE semantics are
    fiddlier than they are worth at this scale.
    """
    extra = _extra_blob(topics, entities, key_points)
    seg_body = body_seg if body_seg is not None else segment(body)
    seg_title = segment(title)
    seg_summary = segment(summary)
    seg_extra = segment(extra)

    conn.execute("DELETE FROM fts_tri WHERE rowid=?", (bookmark_id,))
    conn.execute("DELETE FROM fts_seg WHERE rowid=?", (bookmark_id,))
    conn.execute(_FTS_UPSERT_TRI, (bookmark_id, title, body, summary, extra))
    conn.execute(_FTS_UPSERT_SEG, (bookmark_id, seg_title, seg_body, seg_summary, seg_extra))


def drop_fts(conn: sqlite3.Connection, bookmark_id: int) -> None:
    conn.execute("DELETE FROM fts_tri WHERE rowid=?", (bookmark_id,))
    conn.execute("DELETE FROM fts_seg WHERE rowid=?", (bookmark_id,))
