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
#: Ceiling on the number of terms the trigram path may emit for one query. A CJK
#: sentence expands to roughly one trigram per character, so a pasted paragraph
#: would otherwise build an OR expression with hundreds of clauses.
TRI_MAX_TERMS = 48


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


def build_fts_query(
    query: str,
    *,
    segmented: bool,
    phrases: Iterable[str] = (),
    negatives: Iterable[str] = (),
    prefixes: Iterable[str] = (),
) -> str | None:
    """Turn free-form user input into a safe FTS5 MATCH expression.

    Every term is double-quoted, so FTS5 operators typed by the user are treated
    as literal text rather than syntax. Terms are OR-ed: for bookmark retrieval,
    recall matters more than the precision of an implicit AND, and RRF fusion
    downstream will sort out the ranking.

    Returns ``None`` -- never ``""`` -- when nothing searchable survives, which
    is routine on the trigram path for short CJK queries. An empty string passed
    to ``MATCH`` raises ``fts5: syntax error``, so the caller is forced to check.

    The trigram path cuts CJK runs into overlapping 3-grams. It has to: a CJK
    sentence contains no spaces, so the whole run arrives here as one "term", and
    quoting it whole asks the trigram index for that exact 12-character string.
    A real page never contains a user's whole sentence verbatim, so the clause
    was a guaranteed miss -- measured on the W1 query set, ``lex_tri`` returned
    nothing for 186 of 211 Chinese queries, i.e. the facet whose entire
    justification is the CJK blind spot was absent on 88% of CJK queries.

    The three keyword-only arguments carry the query language (see
    :mod:`facetmark.search.querylang`) into the MATCH expression, in the same
    recall-first spirit:

    * ``phrases`` become FTS5 phrase clauses -- adjacent tokens, not a bag. On
      the trigram path a phrase is substring matching; on the segmented path
      jieba splits it and the tokens must appear consecutively. Phrases are
      OR-ed with the free terms: a document containing the exact phrase scores
      higher in bm25 because it contains every term adjacent, which is the
      ranking effect without inventing clause weights FTS5 does not have.
    * ``negatives`` become a single ``NOT`` clause over the excluded terms:
      ``(free terms) NOT ("n1" OR "n2")``. Excluding is the one intent where
      recall-first is wrong by definition.
    * ``prefixes`` become FTS5 prefix queries ``"term"*`` on the segmented
      path. The trigram path leaves them as plain terms: trigram matching is
      substring matching, so a prefix is already covered.
    """
    phrases = list(phrases)
    negatives = list(negatives)
    prefixes = list(prefixes)

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
            if segmented:
                candidates = [piece]
            elif has_cjk(piece):
                # Overlapping 3-grams, which is what a trigram index indexes.
                # Latin pieces are left whole on purpose: quoting "compar"
                # already matches "comparison" through the same tokenizer, and
                # shredding words would only add noise.
                candidates = [piece[i : i + 3] for i in range(len(piece) - 2)]
            else:
                candidates = [piece]
            for cand in candidates:
                if not segmented and len(cand) < 3:
                    # trigram path: a sub-3-character term can never match, and
                    # leaving it in would turn the whole OR expression into a
                    # guaranteed miss for that clause.
                    continue
                quoted = f'"{cand}"'
                if quoted not in terms:
                    terms.append(quoted)

    for phrase in phrases:
        clause = _phrase_clause(phrase, segmented=segmented)
        if clause and clause not in terms:
            terms.append(clause)

    for prefix in prefixes:
        if segmented:
            clause = _prefix_clause(prefix)
        else:
            # Trigram terms are substring matches already; a prefix is the
            # case where the substring happens to be at the front.
            clause = f'"{prefix}"' if len(prefix) >= 3 else None
        if clause and clause not in terms:
            terms.append(clause)

    if not terms:
        return None
    if not segmented:
        terms = terms[:TRI_MAX_TERMS]

    positive = " OR ".join(terms)
    if negatives:
        neg_terms = _negative_clauses(negatives, segmented=segmented)
        if neg_terms:
            return f"({positive}) NOT ({' OR '.join(neg_terms)})"
    return positive


def _phrase_clause(phrase: str, *, segmented: bool) -> str | None:
    """One quoted phrase as an FTS5 phrase clause.

    On the segmented path the phrase is jieba-split and the tokens re-joined
    inside one pair of quotes, which is FTS5's "these tokens, adjacent" form.
    On the trigram path the phrase goes in whole: the tokenizer cuts it to
    trigrams on both sides, and adjacency of those trigrams is substring
    matching. A phrase shorter than the path can index is dropped rather than
    becoming a clause that can never match.
    """
    phrase = (phrase or "").strip()
    if not phrase:
        return None
    if segmented:
        seg = segment_query(phrase)
        if not seg:
            return None
        # Re-quote each token: a phrase containing an operator-looking token
        # must not get to be one. FTS5 accepts quoted tokens inside a phrase.
        toks = [f'"{t}"' for t in _WS_RE.split(seg) if t]
        return " ".join(toks) if toks else None
    if has_cjk(phrase):
        # trigram: needs >= 3 characters to have any trigram at all
        return f'"{phrase}"' if len(phrase) >= 3 else None
    return f'"{phrase}"' if len(phrase) >= 3 else None


def _prefix_clause(term: str) -> str | None:
    """``term*`` as an FTS5 prefix query, ``"term"*`` in the quoted form."""
    term = (term or "").strip().rstrip("*")
    if not term:
        return None
    return f'"{term}"*'


def _negative_clauses(negatives: Iterable[str], *, segmented: bool) -> list[str]:
    """Quoted clauses for the right side of ``NOT``.

    Same per-path constraints as positive terms: a sub-3-character term on the
    trigram path cannot match anything, so excluding it would be a no-op that
    still costs the parser work -- it is skipped instead.
    """
    out: list[str] = []
    for neg in negatives:
        neg = (neg or "").strip()
        if not neg:
            continue
        if segmented:
            for t in _WS_RE.split(segment_query(neg)):
                if t:
                    out.append(f'"{t}"')
        else:
            if has_cjk(neg):
                for i in range(len(neg) - 2):
                    tri = neg[i : i + 3]
                    if f'"{tri}"' not in out:
                        out.append(f'"{tri}"')
            elif len(neg) >= 3:
                out.append(f'"{neg}"')
    return out


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


def _extra_blob(
    topics: Iterable[str],
    entities: Iterable[str],
    key_points: Iterable[str],
    tags: Iterable[str] = (),
) -> str:
    return " ".join(
        [
            *(t for t in topics if t),
            *(e for e in entities if e),
            *(k for k in key_points if k),
            *(t for t in tags if t),
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
    tags: Iterable[str] = (),
) -> None:
    """Rewrite both lexical index rows for one bookmark.

    Delete-then-insert because FTS5 external-content UPDATE semantics are
    fiddlier than they are worth at this scale.

    Tags are folded into ``extra`` (same weight as topics/entities) so a tag
    word is retrievable as free text; the query language's ``tag:`` filter is
    the exact-match view over the same vocabulary, straight off the JSON
    column instead.
    """
    extra = _extra_blob(topics, entities, key_points, tags)
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
