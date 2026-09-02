"""Facet 3: the word facet, over two FTS5 indexes that cover for each other.

Why two. Measured on the calibration library of 1,688 real bookmarks, using
``title LIKE '%word%'`` as ground truth:

    query   chars   true hits   trigram hits
    工具      2         159            0
    论文      2           6            0
    提示词    3          27           27
    效率工具  4           1            1

FTS5's ``trigram`` tokenizer cannot match a query shorter than three
characters, and two-character words are the dominant form in Chinese. It is not
that trigram ranks them badly -- it returns nothing at all. Meanwhile
``unicode61`` treats an unsegmented CJK run as one token, so it cannot match
inside a title either. Segmenting with jieba first fixes ``unicode61``; trigram
then earns its place by catching the substrings jieba mis-splits, and by
matching partial latin words (``compar`` -> ``comparison``) that a word index
cannot. The blind spots do not overlap, so both indexes are required.

Column weights favour the title heavily. A bookmark's title is the one piece of
text the user has actually seen and may half-remember.

Structural filters from the query language (:mod:`facetmark.search.querylang`)
are pushed down into this facet's SQL as a ``JOIN bookmark`` + ``WHERE``, the
same plan hister runs with bleve boolean conjunctions. Pushdown matters here
and post-filtering does not: the facet returns ``limit`` rows *after* ranking,
so filtering in Python after the fact would hand back a short list whose
missing tail was occupied by perfectly good -- filtered-out -- candidates.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence

from ..text import build_fts_query
from .querylang import FieldFilter, ParsedQuery, parse_query

#: bm25 column weights: title, body, summary, extra.
WEIGHTS_SEG = (10.0, 1.0, 4.0, 3.0)
WEIGHTS_TRI = (10.0, 1.0, 4.0, 3.0)

#: LIKE metacharacters are escaped so a value such as ``url:100%`` matches the
#: literal string rather than every URL ending in a digit.
_LIKE_ESCAPE = "\\"


def _like(value: str) -> str:
    """Escape LIKE metacharacters in a user value."""
    return (
        value.replace(_LIKE_ESCAPE, _LIKE_ESCAPE + _LIKE_ESCAPE)
        .replace("%", _LIKE_ESCAPE + "%")
        .replace("_", _LIKE_ESCAPE + "_")
    )


def sql_predicate(parsed: ParsedQuery) -> tuple[str, list[object]] | None:
    """One WHERE fragment (without ``WHERE``) for the parsed filters.

    Returns ``None`` when there is nothing to filter, so the no-syntax path
    can keep running the single-table SQL it always ran.
    """
    clauses: list[str] = []
    params: list[object] = []

    for f in parsed.field_filters:
        fragment, fparams = _field_predicate(f)
        clauses.append(fragment)
        params.extend(fparams)

    if parsed.dates is not None:
        d = parsed.dates
        if d.start is not None:
            clauses.append("b.date_added >= ?")
            params.append(d.start)
        if d.end is not None:
            clauses.append("b.date_added <= ?")
            params.append(d.end)

    if not clauses:
        return None
    return " AND ".join(clauses), params


def _field_predicate(f: FieldFilter) -> tuple[str, list[object]]:
    d = f.defn
    value_clauses: list[str] = []
    params: list[object] = []

    for v in f.values:
        esc = _like(v)
        if d.match == "exact_suffix":
            if "." in v:
                # domain:github.com -- the registrable domain itself, or any
                # host underneath it, mirroring hister's AllowedDomains
                # suffix semantics.
                value_clauses.append("(b.domain = ? OR b.host LIKE '%.' || ? ESCAPE '\\')")
                params.extend([v, esc])
            else:
                # domain:github -- no dot, so the user is typing a prefix of
                # the domain they half-remember; substring match on domain.
                value_clauses.append("b.domain LIKE '%' || ? || '%' ESCAPE '\\'")
                params.append(esc)
        elif d.match == "tag":
            marks = ",".join("?" * len(f.values))
            value_clauses.append(
                f"EXISTS (SELECT 1 FROM json_each(b.tags) WHERE json_each.value IN ({marks}))"
            )
            params.extend(f.values)
            break  # all values handled in one EXISTS
        else:  # contains
            value_clauses.append(f"b.{d.column} LIKE '%' || ? || '%' ESCAPE '\\'")
            params.append(esc)

    body = "(" + " OR ".join(value_clauses) + ")" if len(value_clauses) > 1 else value_clauses[0]
    if f.negated:
        return f"NOT {body}", params
    return body, params


def _run_scored(
    conn: sqlite3.Connection,
    table: str,
    match: str,
    weights,
    limit: int,
    predicate: tuple[str, list[object]] | None = None,
) -> list[tuple[int, float]]:
    """Ranked ids with their bm25 score, sign-flipped so higher is better.

    FTS5's ``bm25()`` returns more-negative for better matches, which is fine
    for ``ORDER BY`` and confusing everywhere else. Negating here means every
    facet in the system hands back the same convention.

    With a predicate, the query joins ``bookmark`` so structural filters
    (``domain:``, ``tag:``, dates) apply *before* the ``LIMIT``: rows that fail
    the filter never occupy a ranked slot, and deeper rows that pass it are
    pulled up into the candidate list. LIKE comparisons get the ASCII case
    folding SQLite applies by default; CJK values have no case to fold.
    """
    w = ", ".join(str(x) for x in weights)
    if predicate is None:
        sql = (
            f"SELECT rowid AS id, bm25({table}, {w}) AS score FROM {table} "
            f"WHERE {table} MATCH ? ORDER BY score LIMIT ?"
        )
        args: tuple = (match, limit)
    else:
        where, params = predicate
        sql = (
            f"SELECT f.rowid AS id, bm25({table}, {w}) AS score "
            f"FROM {table} f JOIN bookmark b ON b.id = f.rowid "
            f"WHERE {table} MATCH ? AND {where} ORDER BY score LIMIT ?"
        )
        args = (match, *params, limit)
    try:
        return [(r["id"], -float(r["score"])) for r in conn.execute(sql, args)]
    except sqlite3.OperationalError:
        # A query that survives sanitising can still be invalid FTS5 syntax.
        # An empty facet is a correct answer here; raising would take down a
        # search that three other facets could still have answered.
        return []


def _run(
    conn: sqlite3.Connection, table: str, match: str, weights, limit: int,
    predicate: tuple[str, list[object]] | None = None,
) -> list[int]:
    return [i for i, _ in _run_scored(conn, table, match, weights, limit, predicate)]


def _split(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int,
    parsed: ParsedQuery | None,
    extra_phrases: Sequence[str],
) -> dict[str, list[tuple[int, float]]]:
    """Both FTS paths with the parsed query applied, as scored lists."""
    if parsed is None:
        # A caller that never parsed (legacy tests, karakeep bridge) gets the
        # exact pre-query-language behaviour: the raw string, no phrases, no
        # filters, the single-table SQL.
        predicate = None
        text_src = query
        phrases: list[str] = list(extra_phrases)
        negatives: list[str] = []
        prefixes: list[str] = []
    else:
        predicate = sql_predicate(parsed)
        text_src = parsed.text
        phrases = list(dict.fromkeys([*parsed.phrases, *extra_phrases]))
        negatives = list(parsed.negatives)
        prefixes = list(parsed.prefixes)

    out: dict[str, list[tuple[int, float]]] = {}

    # A filter-only query ("tag:work", "domain:github.com after:30d") has no
    # words for the FTS index, and answering it with an empty list would make
    # the whole grammar look broken on its purest use. Hister runs these as a
    # MatchAll conjunction; the SQL equivalent here is the bookmark table
    # itself under the same predicate, newest first. It rides in the lex_seg
    # slot because that is the list every downstream consumer (RRF, paging,
    # abstention accounting) already knows how to rank, and a single facet is
    # order-preserving under RRF, so the page order *is* date order.
    if (
        predicate is not None
        and not text_src.strip()
        and not phrases
    ):
        where, params = predicate
        sql = (
            "SELECT b.id AS id, 0.0 AS score FROM bookmark b "
            f"WHERE {where} ORDER BY b.date_added DESC, b.id LIMIT ?"
        )
        try:
            rows = conn.execute(sql, (*params, limit)).fetchall()
        except sqlite3.OperationalError:
            rows = []
        out["lex_seg"] = [(int(r["id"]), 0.0) for r in rows]
        return {k: v for k, v in out.items() if v}

    seg = build_fts_query(
        text_src, segmented=True, phrases=phrases, negatives=negatives, prefixes=prefixes
    )
    if seg:
        out["lex_seg"] = _run_scored(conn, "fts_seg", seg, WEIGHTS_SEG, limit, predicate)
    tri = build_fts_query(
        text_src, segmented=False, phrases=phrases, negatives=negatives, prefixes=prefixes
    )
    if tri:
        out["lex_tri"] = _run_scored(conn, "fts_tri", tri, WEIGHTS_TRI, limit, predicate)
    return {k: v for k, v in out.items() if v}


def lexical_lists(
    conn: sqlite3.Connection, query: str, *, limit: int = 50,
    parsed: ParsedQuery | None = None, extra_phrases: Sequence[str] = (),
) -> dict[str, list[int]]:
    """Both lexical paths, as separate ranked lists for the fusion step.

    They are kept separate rather than merged because RRF already knows what to
    do with two lists that agree, and merging first would throw away the
    agreement signal.
    """
    return {
        k: [i for i, _ in v]
        for k, v in lexical_lists_scored(
            conn, query, limit=limit, parsed=parsed, extra_phrases=extra_phrases
        ).items()
    }


def lexical_lists_scored(
    conn: sqlite3.Connection, query: str, *, limit: int = 50,
    parsed: ParsedQuery | None = None, extra_phrases: Sequence[str] = (),
) -> dict[str, list[tuple[int, float]]]:
    """:func:`lexical_lists` with the bm25 score kept, higher being better.

    Only the abstention path needs the scores. Everything else takes the ids,
    because RRF is deliberately rank-only and handing it scores would invite
    exactly the cross-facet score normalisation it was chosen to avoid.

    ``parsed`` carries the query language: free text goes into the MATCH
    expression, phrases become FTS5 phrase clauses, negatives a ``NOT``
    clause, and structural filters a SQL predicate joined in *before* the
    LIMIT. ``extra_phrases`` lets the caller add phrases extracted elsewhere
    (``understand`` pulls them from CJK quotes); they are deduplicated against
    the parsed ones.
    """
    return _split(conn, query, limit=limit, parsed=parsed, extra_phrases=extra_phrases)


def lexical_search(conn: sqlite3.Connection, query: str, *, limit: int = 50) -> list[int]:
    """Single merged list, for callers that want one lexical ranking."""
    parsed = parse_query(query) if query else None
    lists = lexical_lists(conn, query, limit=limit, parsed=parsed)
    seen: set[int] = set()
    merged: list[int] = []
    for ids in zip(*lists.values(), strict=False):   # interleave, best-first
        for i in ids:
            if i not in seen:
                seen.add(i)
                merged.append(i)
    for ids in lists.values():                        # then the tails
        for i in ids:
            if i not in seen:
                seen.add(i)
                merged.append(i)
    return merged[:limit]
