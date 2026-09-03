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
"""

from __future__ import annotations

import sqlite3
from collections.abc import Collection

from ..db import jdump
from ..text import build_fts_query

#: bm25 column weights: title, body, summary, extra.
WEIGHTS_SEG = (10.0, 1.0, 4.0, 3.0)
WEIGHTS_TRI = (10.0, 1.0, 4.0, 3.0)


def _run_scored(
    conn: sqlite3.Connection, table: str, match: str, weights, limit: int,
    allow: Collection[int] | None = None,
) -> list[tuple[int, float]]:
    """Ranked ids with their bm25 score, sign-flipped so higher is better.

    FTS5's ``bm25()`` returns more-negative for better matches, which is fine
    for ``ORDER BY`` and confusing everywhere else. Negating here means every
    facet in the system hands back the same convention.

    ``allow`` restricts the match *before* the ``LIMIT``. That is the whole
    point of passing it: a query language filter applied after the fact can
    only ever cut the list it was handed, so ``postgres domain:github.com``
    used to return whatever survived among the top 50 for "postgres" -- often
    nothing, on a library where the github pages rank 200th. Pushed down, rows
    that fail the filter never occupy a ranked slot and deeper rows that pass
    it move up into it. The ids arrive as one JSON parameter rather than an
    ``IN (?,?,...)`` of unbounded length.
    """
    w = ", ".join(str(x) for x in weights)
    gate = "" if allow is None else " AND rowid IN (SELECT value FROM json_each(?))"
    sql = (
        f"SELECT rowid AS id, bm25({table}, {w}) AS score FROM {table} "
        f"WHERE {table} MATCH ?{gate} ORDER BY score LIMIT ?"
    )
    params: tuple = (match, limit) if allow is None else (
        match, jdump(sorted(allow)), limit
    )
    try:
        return [(r["id"], -float(r["score"])) for r in conn.execute(sql, params)]
    except sqlite3.OperationalError:
        # A query that survives sanitising can still be invalid FTS5 syntax.
        # An empty facet is a correct answer here; raising would take down a
        # search that three other facets could still have answered.
        return []


def _run(
    conn: sqlite3.Connection, table: str, match: str, weights, limit: int,
    allow: Collection[int] | None = None,
) -> list[int]:
    return [i for i, _ in _run_scored(conn, table, match, weights, limit, allow)]


def lexical_lists(
    conn: sqlite3.Connection, query: str, *, limit: int = 50,
    allow: Collection[int] | None = None,
) -> dict[str, list[int]]:
    """Both lexical paths, as separate ranked lists for the fusion step.

    They are kept separate rather than merged because RRF already knows what to
    do with two lists that agree, and merging first would throw away the
    agreement signal.

    ``allow``, when given, is the set of ids a query-language filter leaves
    eligible; it is applied inside the SQL, before the ``LIMIT``.
    """
    return {
        k: [i for i, _ in v]
        for k, v in lexical_lists_scored(conn, query, limit=limit, allow=allow).items()
    }


def lexical_lists_scored(
    conn: sqlite3.Connection, query: str, *, limit: int = 50,
    allow: Collection[int] | None = None,
) -> dict[str, list[tuple[int, float]]]:
    """:func:`lexical_lists` with the bm25 score kept, higher being better.

    Only the abstention path needs the scores. Everything else takes the ids,
    because RRF is deliberately rank-only and handing it scores would invite
    exactly the cross-facet score normalisation it was chosen to avoid.
    """
    out: dict[str, list[tuple[int, float]]] = {}
    seg = build_fts_query(query, segmented=True)
    if seg:
        out["lex_seg"] = _run_scored(conn, "fts_seg", seg, WEIGHTS_SEG, limit, allow)
    tri = build_fts_query(query, segmented=False)
    if tri:
        out["lex_tri"] = _run_scored(conn, "fts_tri", tri, WEIGHTS_TRI, limit, allow)
    return {k: v for k, v in out.items() if v}


def lexical_search(conn: sqlite3.Connection, query: str, *, limit: int = 50) -> list[int]:
    """Single merged list, for callers that want one lexical ranking."""
    lists = lexical_lists(conn, query, limit=limit)
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
