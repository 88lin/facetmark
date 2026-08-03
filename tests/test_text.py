"""Lexical layer.

The central assertion here is the measured one: neither FTS5 tokeniser can serve
a mixed CJK/latin bookmark library alone, so Facet 3 needs both.
"""

from __future__ import annotations

import sqlite3

import pytest

from facetmark.text import (
    TRI_MAX_TERMS,
    build_fts_query,
    detect_lang,
    drop_fts,
    has_cjk,
    segment,
    segment_query,
    sync_fts,
    truncate_head_tail,
)

DOCS = {
    1: ("用 Automerge 做协同编辑的 CRDT 实践", "Automerge 是一个 CRDT 库，用于本地优先的协同编辑应用。"),
    2: ("机器学习论文精读工具合集", "整理了一批读论文用的工具，包括标注、翻译和管理。"),
    3: ("Rust async runtime comparison", "A comparison of tokio, async-std and smol."),
    4: ("SQLite 全文检索 FTS5 中文分词踩坑", "unicode61 不切中文，trigram 有三字符下限。"),
}


def _load(conn):
    for bid, (title, body) in DOCS.items():
        conn.execute(
            "INSERT INTO bookmark(id, url, url_norm, url_hash, title, created_at, updated_at)"
            " VALUES(?,?,?,?,?,0,0)",
            (bid, f"https://e.com/{bid}", f"https://e.com/{bid}", f"h{bid}", title),
        )
        sync_fts(conn, bid, title=title, body=body)


def _hits(conn, table, query, *, segmented):
    q = build_fts_query(query, segmented=segmented)
    if not q:
        return set()
    rows = conn.execute(f"SELECT rowid FROM {table} WHERE {table} MATCH ?", (q,)).fetchall()
    return {int(r[0]) for r in rows}


class TestSegmentation:
    def test_cjk_is_split_into_words(self):
        assert segment("机器学习论文精读工具合集").split() == [
            "机器", "学习", "论文", "精读", "工具", "合集",
        ]

    def test_search_mode_emits_coarse_and_fine_grains(self):
        toks = segment("全文检索").split()
        assert "全文" in toks and "检索" in toks and "全文检索" in toks

    def test_query_mode_uses_precise_segmentation_only(self):
        # A query must not be diluted by the extra overlapping grains.
        assert segment_query("全文检索").split() == ["全文检索"]

    def test_latin_text_is_untouched_apart_from_whitespace(self):
        assert segment("Rust  async   runtime") == "Rust async runtime"

    def test_empty_input(self):
        assert segment("") == ""
        assert segment_query("") == ""

    def test_has_cjk(self):
        assert has_cjk("中文") and has_cjk("mixed 中文")
        assert not has_cjk("pure latin 123")


class TestWhyBothTokenisersAreNeeded:
    """The measurement that promoted jieba from optional to required."""

    def test_trigram_cannot_match_two_character_cjk_words(self, conn):
        _load(conn)
        for q in ("学习", "工具", "论文", "分词", "检索"):
            assert _hits(conn, "fts_tri", q, segmented=False) == set(), (
                f"trigram unexpectedly matched {q!r}"
            )

    def test_segmented_path_matches_them(self, conn):
        _load(conn)
        assert _hits(conn, "fts_seg", "学习", segmented=True) == {2}
        assert _hits(conn, "fts_seg", "工具", segmented=True) == {2}
        assert _hits(conn, "fts_seg", "分词", segmented=True) == {4}

    def test_trigram_still_earns_its_place_on_substrings(self, conn):
        _load(conn)
        # A latin substring that is not a whole token.
        assert 3 in _hits(conn, "fts_tri", "compar", segmented=False)
        assert _hits(conn, "fts_seg", "compar", segmented=True) == set()

    def test_union_of_the_two_paths_covers_everything(self, conn):
        _load(conn)
        for q in ("学习", "工具", "论文", "协同编辑", "机器学习", "Rust", "compar", "分词"):
            union = _hits(conn, "fts_tri", q, segmented=False) | _hits(
                conn, "fts_seg", q, segmented=True
            )
            assert union, f"neither path matched {q!r}"

    def test_absent_term_matches_nothing(self, conn):
        _load(conn)
        union = _hits(conn, "fts_tri", "量子纠缠", segmented=False) | _hits(
            conn, "fts_seg", "量子纠缠", segmented=True
        )
        assert union == set()


class TestFtsQueryBuilding:
    def test_terms_are_quoted_so_operators_are_literal(self):
        q = build_fts_query("rust OR tokio", segmented=True)
        assert q.count('"') == 6  # three quoted terms

    def test_fts_syntax_characters_are_neutralised(self):
        # These would otherwise be a syntax error or an unintended prefix search.
        for bad in ('"', "*", "(", ")", ":", "^", "-"):
            q = build_fts_query(f"rust {bad} tokio", segmented=True)
            assert bad not in q.replace('"', "")

    def test_short_terms_are_dropped_on_the_trigram_path(self):
        # They can never match, and leaving them in guarantees a miss.
        assert build_fts_query("学习", segmented=False) is None
        assert build_fts_query("ab", segmented=False) is None

    def test_short_terms_are_kept_on_the_segmented_path(self):
        assert build_fts_query("学习", segmented=True) == '"学习"'

    def test_a_cjk_sentence_becomes_overlapping_trigrams(self):
        """The regression that made lex_tri absent on 88% of Chinese queries.

        A CJK run has no spaces, so it used to arrive as one quoted term and ask
        the trigram index for the user's whole sentence, verbatim.
        """
        q = build_fts_query("如何查看浏览器历史记录", segmented=False)
        terms = q.split(" OR ")
        assert '"如何查看浏览器历史记录"' not in terms
        assert terms[0] == '"如何查"' and terms[1] == '"何查看"'
        assert all(len(t) == 5 for t in terms)  # three chars plus two quotes
        assert len(terms) == len("如何查看浏览器历史记录") - 2

    def test_trigrams_actually_match_a_document(self, conn):
        """Whole-sentence quoting matched nothing; trigrams find the page."""
        _load(conn)
        # A question, not a substring of any title -- the shape a user types.
        assert _hits(conn, "fts_tri", "有没有读机器学习论文的工具", segmented=False) == {2}
        # the pre-fix expression, kept literal, to show it really was a dead end
        dead = conn.execute(
            "SELECT rowid FROM fts_tri WHERE fts_tri MATCH ?", ('"有没有读机器学习论文的工具"',)
        ).fetchall()
        assert dead == []

    def test_latin_words_are_not_shredded(self):
        # "compar" already matches "comparison" through the trigram tokenizer;
        # cutting latin into 3-grams would only add noise.
        assert build_fts_query("comparison runtime", segmented=False) == (
            '"comparison" OR "runtime"'
        )

    def test_trigram_expansion_is_capped(self):
        long_cjk = "".join(chr(0x4E00 + i) for i in range(400))
        q = build_fts_query(long_cjk, segmented=False)
        assert len(q.split(" OR ")) == TRI_MAX_TERMS

    def test_mixed_script_keeps_latin_whole_and_cuts_cjk(self):
        terms = build_fts_query("sqlite 向量检索", segmented=False).split(" OR ")
        assert terms == ['"sqlite"', '"向量检"', '"量检索"']

    def test_empty_and_punctuation_only_input(self):
        assert build_fts_query("", segmented=True) is None
        assert build_fts_query("()*", segmented=True) is None

    def test_none_not_empty_string_because_empty_match_is_a_syntax_error(self, conn):
        """An empty MATCH expression raises; None forces the caller to branch."""
        assert build_fts_query("学习", segmented=False) is None
        with pytest.raises(sqlite3.OperationalError, match="syntax error"):
            conn.execute("SELECT 1 FROM fts_tri WHERE fts_tri MATCH ?", ("",)).fetchall()


class TestSyncAndDrop:
    def test_sync_is_idempotent(self, conn):
        _load(conn)
        before = conn.execute("SELECT count(*) FROM fts_seg").fetchone()[0]
        sync_fts(conn, 1, title=DOCS[1][0], body=DOCS[1][1])
        assert conn.execute("SELECT count(*) FROM fts_seg").fetchone()[0] == before

    def test_sync_reflects_updated_text(self, conn):
        _load(conn)
        sync_fts(conn, 1, title="完全不同的标题", body="全新的正文")
        assert _hits(conn, "fts_seg", "协同编辑", segmented=True) == set()
        assert _hits(conn, "fts_seg", "全新", segmented=True) == {1}

    def test_extra_fields_are_searchable(self, conn):
        _load(conn)
        sync_fts(
            conn, 1, title=DOCS[1][0], body=DOCS[1][1],
            summary="本地优先的数据同步", topics=["CRDT", "本地优先"], entities=["Automerge"],
            key_points=["当时在选型"],
        )
        assert _hits(conn, "fts_seg", "选型", segmented=True) == {1}
        assert _hits(conn, "fts_seg", "本地优先", segmented=True) == {1}

    def test_drop_removes_from_both_tables(self, conn):
        _load(conn)
        drop_fts(conn, 1)
        assert conn.execute("SELECT count(*) FROM fts_tri WHERE rowid=1").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM fts_seg WHERE rowid=1").fetchone()[0] == 0


class TestTruncateAndLang:
    def test_head_and_tail_are_both_kept(self):
        text = "HEAD" + "x" * 5000 + "TAIL"
        out = truncate_head_tail(text, 100)
        assert out.startswith("HEAD") and out.endswith("TAIL") and len(out) <= 110

    def test_short_text_is_returned_unchanged(self):
        assert truncate_head_tail("short", 100) == "short"

    def test_lang_detection(self):
        assert detect_lang("这是一段中文正文内容") == "zh"
        assert detect_lang("this is english body text") == "en"
        assert detect_lang("") == "unknown"
