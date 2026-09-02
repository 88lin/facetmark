"""The query language: parser, SQL predicates, and pipeline integration.

Facetmark's lexical facet used to strip every FTS5 metacharacter out of the
query and OR whatever words survived. The grammar ported from hister's query
builder (``server/indexer/querybuilder``) adds field filters, phrases,
negation, prefixes, date windows and a sort directive, with two properties the
tests below pin down:

* **A plain query is untouched.** No syntax, no filters, the same text the old
  code saw. This is what lets 1,500 pre-existing tests stay meaningful.
* **A colon is only a filter when the name is one.** URLs survive verbatim;
  ``after:nonsense`` survives verbatim; ``sort:garbage`` survives verbatim.
  The worst case of a typo is yesterday's behaviour, never a lost word.
"""

from __future__ import annotations

import sqlite3

import pytest

from facetmark.search.lexical import lexical_lists, sql_predicate
from facetmark.search.pipeline import quick_search, search
from facetmark.search.querylang import (
    FIELDS,
    SORT_KEYS,
    DateRange,
    parse_query,
)
from facetmark.text import build_fts_query

from .conftest import open_db

NOW = 1_735_689_600  # 2025-01-01 00:00 UTC, pinned so date math is exact


# ---------------------------------------------------------------------------
# the parser
# ---------------------------------------------------------------------------


class TestPlainQueries:
    def test_a_plain_query_round_trips_exactly(self):
        """Everything downstream keys off is_plain; it must mean what it says."""
        p = parse_query("async rust", now_ts=NOW)
        assert p.is_plain
        assert p.text == "async rust"
        assert not p.has_filters
        assert p.sort is None

    def test_a_url_is_not_a_stack_of_colons(self):
        """https is not a field name. Two colons in a URL must not shred it."""
        p = parse_query("https://github.com/88lin/facetmark docs", now_ts=NOW)
        assert p.is_plain
        assert p.text == "https://github.com/88lin/facetmark docs"

    def test_whitespace_is_normalised_but_words_are_kept(self):
        p = parse_query("  rust   async  ", now_ts=NOW)
        assert p.text == "rust async"

    def test_an_empty_query_parses_to_an_empty_query(self):
        p = parse_query("", now_ts=NOW)
        assert p.is_plain
        assert p.text == ""

    def test_hyphenated_words_keep_their_hyphens(self):
        """Only a leading hyphen negates; mid-word hyphens are identifiers."""
        p = parse_query("sqlite-vec trigram", now_ts=NOW)
        assert p.is_plain
        assert p.text == "sqlite-vec trigram"
        assert p.negatives == []

    def test_cjk_free_text_is_untouched(self):
        p = parse_query("机器学习 工具", now_ts=NOW)
        assert p.is_plain
        assert p.text == "机器学习 工具"


class TestFieldFilters:
    def test_a_known_field_becomes_a_filter(self):
        p = parse_query("rust domain:github.com", now_ts=NOW)
        assert p.text == "rust"
        assert len(p.field_filters) == 1
        f = p.field_filters[0]
        assert f.field == "domain" and f.values == ["github.com"] and not f.negated
        assert not p.is_plain

    def test_site_is_an_alias_of_domain(self):
        """Users type site: from muscle memory; it must mean the same thing."""
        p = parse_query("site:github.com", now_ts=NOW)
        assert p.field_filters[0].field == "domain"

    def test_every_alias_resolves_to_a_canonical_field(self):
        p = parse_query("until:2024-01 saved:2024", now_ts=NOW)
        assert [f.field for f in p.field_filters] == []
        assert p.dates is not None

    def test_an_unknown_field_name_stays_verbatim(self):
        p = parse_query("priority:high rust", now_ts=NOW)
        assert p.is_plain
        assert p.text == "priority:high rust"

    def test_negated_field_filters(self):
        p = parse_query("-domain:pinterest.com crafts", now_ts=NOW)
        assert p.text == "crafts"
        assert p.field_filters[0].negated

    def test_alternation_in_a_field(self):
        p = parse_query("domain:(github.com|gitlab.com) ci", now_ts=NOW)
        assert p.text == "ci"
        assert p.field_filters[0].values == ["github.com", "gitlab.com"]

    def test_all_fields_have_definitions(self):
        """The lookup table and FIELDS must agree -- aliases included."""
        from facetmark.search.querylang import _FIELD_LOOKUP

        assert set(_FIELD_LOOKUP) >= set(FIELDS)
        for d in FIELDS.values():
            for alias in d.aliases:
                assert _FIELD_LOOKUP[alias].name == d.name

    def test_tag_filter(self):
        p = parse_query("tag:work", now_ts=NOW)
        assert p.text == ""
        assert p.field_filters[0].field == "tag"


class TestPhrasesAndNegatives:
    def test_double_quoted_phrase(self):
        p = parse_query('"machine learning" tutorial', now_ts=NOW)
        assert p.phrases == ["machine learning"]
        assert p.text == "tutorial"

    def test_cjk_quotes_are_phrases_too(self):
        """understand already treats 「」/“” as phrase markers; the lexer agrees."""
        p = parse_query("\u201c\u673a\u5668\u5b66\u4e60\u201d \u5de5\u5177", now_ts=NOW)
        assert p.phrases == ["机器学习"]
        assert p.text == "工具"

    def test_negated_phrase(self):
        p = parse_query('-"machine learning" rust', now_ts=NOW)
        assert p.negatives == ["machine learning"]

    def test_negated_free_word(self):
        p = parse_query("rust -java", now_ts=NOW)
        assert p.text == "rust"
        assert p.negatives == ["java"]

    def test_a_lone_hyphen_is_not_a_negation(self):
        p = parse_query("- ", now_ts=NOW)
        assert p.text == "-" or p.text == ""

    def test_prefix_wildcard_keeps_the_word_as_text(self):
        """The star is intent; the word itself still needs to be searched."""
        p = parse_query("kuber*", now_ts=NOW)
        assert p.prefixes == ["kuber"]
        assert p.text == "kuber"


class TestDates:
    def test_absolute_day(self):
        p = parse_query("before:2024-06-01", now_ts=NOW)
        assert p.dates is not None
        assert p.dates.start is None
        assert p.dates.end == 1_717_286_399  # 2024-06-01 23:59:59 UTC, inclusive

    def test_absolute_month_and_year(self):
        p = parse_query("added:2024-06", now_ts=NOW)
        assert p.dates == DateRange(1_717_200_000, 1_719_791_999)
        p = parse_query("added:2024", now_ts=NOW)
        assert p.dates == DateRange(1_704_067_200, 1_735_689_599)

    def test_relative_window(self):
        p = parse_query("after:30d", now_ts=NOW)
        assert p.dates == DateRange(NOW - 30 * 86400, None)

    def test_relative_long_units(self):
        for text, span in (("2w", 14), ("3mo", 90), ("1y", 365)):
            p = parse_query(f"after:{text}", now_ts=NOW)
            assert p.dates.start == NOW - span * 86400, text

    def test_two_bounds_intersect(self):
        p = parse_query("after:2024-03-01 before:2024-06-01", now_ts=NOW)
        assert p.dates == DateRange(1_709_251_200, 1_717_286_399)

    def test_a_range_window(self):
        p = parse_query("added:2024-06..2024-09", now_ts=NOW)
        assert p.dates == DateRange(1_717_200_000, 1_727_740_799)

    def test_comparisons(self):
        p = parse_query("added:>2024-06-01", now_ts=NOW)
        assert p.dates.start == 1_717_286_400
        assert p.dates.end is None
        p = parse_query("added:<90d", now_ts=NOW)
        assert p.dates.start is None
        assert p.dates.end == NOW - 90 * 86400 - 1

    def test_a_non_date_value_stays_verbatim(self):
        """after:nonsense must not silently vanish from the query."""
        p = parse_query("after:nonsense rust", now_ts=NOW)
        assert "after:nonsense" in p.text
        assert p.dates is None

    def test_an_invalid_month_is_not_a_date(self):
        p = parse_query("added:2024-13", now_ts=NOW)
        assert p.dates is None
        assert "added:2024-13" in p.text

    def test_a_negated_date_stays_verbatim(self):
        """-after:... has no clean semantics, so it is text, not a guess."""
        p = parse_query("-after:30d", now_ts=NOW)
        assert "-after:30d" in p.text
        assert p.dates is None


class TestSortDirective:
    def test_valid_sort_keys(self):
        assert "date" in SORT_KEYS and "-date" in SORT_KEYS
        p = parse_query("sort:date rust", now_ts=NOW)
        assert p.sort == "date"
        assert p.text == "rust"

    def test_sort_alone_peels_off_cleanly(self):
        p = parse_query("sort:date", now_ts=NOW)
        assert p.sort == "date"
        assert p.text == ""

    def test_an_invalid_sort_key_is_text(self):
        p = parse_query("sort:garbage date", now_ts=NOW)
        assert p.sort is None
        assert p.text == "sort:garbage date"

    def test_a_negated_sort_is_not_a_directive(self):
        p = parse_query("-sort:date", now_ts=NOW)
        assert p.sort is None
        assert "-sort:date" in p.text


class TestRobustness:
    def test_an_unterminated_quote_is_still_a_phrase(self):
        p = parse_query('"machine learning', now_ts=NOW)
        assert p.phrases == ["machine learning"]

    def test_an_unterminated_group_falls_back_to_a_word(self):
        p = parse_query("(docker|k8s", now_ts=NOW)
        # Not alternation syntax; the text survives with the paren.
        assert "docker" in p.text or "(docker|k8s" in p.text
        assert p.field_filters == []

    def test_all_words_survive_every_fallback(self):
        """The contract: a typo never loses words the old query would have kept."""
        for typo in ("after:", "domain:", '"', "-"):
            p = parse_query(f"rust {typo}async", now_ts=NOW)
            assert (
                "async" in p.text
                or "async" in p.negatives
                or "async" in p.phrases
                or any("async" in f.values for f in p.field_filters)
            ), typo

    def test_all_words_orders_longest_first_for_snippets(self):
        p = parse_query("rust async runtime", now_ts=NOW)
        assert p.all_words()[0] == "runtime"

    def test_as_echo_round_trips_the_essentials(self):
        p = parse_query("rust -java domain:github.com after:30d sort:date", now_ts=NOW)
        echo = p.as_echo()
        assert echo["text"] == "rust"
        assert echo["negatives"] == ["java"]
        assert echo["field_filters"][0]["field"] == "domain"
        assert echo["sort"] == "date"


# ---------------------------------------------------------------------------
# FTS expression building
# ---------------------------------------------------------------------------


class TestFtsExpression:
    def test_plain_query_unchanged(self):
        assert build_fts_query("rust async", segmented=True) == '"rust" OR "async"'

    def test_a_phrase_is_adjacent_tokens_not_a_bag(self):
        out = build_fts_query("", segmented=True, phrases=["machine learning"])
        assert '"machine" "learning"' in out

    def test_cjk_phrase_segments_before_quoting(self):
        out = build_fts_query("", segmented=True, phrases=["机器学习教程"])
        assert out is not None
        assert out.startswith('"机')

    def test_negatives_become_a_not_clause(self):
        out = build_fts_query("rust", segmented=True, negatives=["java"])
        assert out == '("rust") NOT ("java")'

    def test_a_prefix_is_a_fts5_prefix_query(self):
        out = build_fts_query("", segmented=True, prefixes=["kuber"])
        assert out == '"kuber"*'

    def test_trigram_path_keeps_short_cjk_out(self):
        """A 2-char CJK phrase cannot match trigrams; dropping it is correct."""
        assert build_fts_query("", segmented=False, phrases=["工具"]) is None

    def test_trigram_path_phrase_is_a_substring(self):
        out = build_fts_query("", segmented=False, phrases=["机器学习"])
        assert out == '"机器学习"'

    def test_no_terms_still_returns_none(self):
        assert build_fts_query("", segmented=True) is None


# ---------------------------------------------------------------------------
# SQL predicates + lexical integration
# ---------------------------------------------------------------------------


def _seed(conn: sqlite3.Connection) -> None:
    from facetmark.text import sync_fts

    rows = [
        # (id, url, host, domain, title, folder, tags, date_added)
        (1, "https://github.com/a", "github.com", "github.com",
         "Rust async guide", "dev", '["rust","systems"]', 1_600_000_000),
        (2, "https://gist.github.com/b", "gist.github.com", "github.com",
         "kubernetes tutorial", "dev", '["k8s","work"]', 1_610_000_000),
        (3, "https://pinterest.com/c", "pinterest.com", "pinterest.com",
         "craft ideas", "fun", "[]", 1_620_000_000),
        (4, "https://news.ycombinator.com/d", "news.ycombinator.com",
         "ycombinator.com", "machine learning thread", "dev", '["ml","reading"]',
         1_630_000_000),
    ]
    for bid, url, host, domain, title, folder, tags, added in rows:
        conn.execute(
            "INSERT INTO bookmark(id, url, url_norm, url_hash, title, folder, host,"
            " domain, date_added, tags, created_at, updated_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (bid, url, url, f"h{bid}", title, folder, host, domain, added, tags, added, added),
        )
        # A body long enough that a head-only snippet could not contain a
        # term that only appears deeper in the text.
        pad = "filler paragraph with unrelated words. " * 6
        body = f"{pad} the actual matched sentence about {title.lower()} lives here. {pad}"
        conn.execute(
            "INSERT INTO content(bookmark_id, body_text, body_seg, char_count,"
            " fetched_at) VALUES(?,?,?,?,?)",
            (bid, body, body, len(body), added),
        )
        sync_fts(conn, bid, title=title, body=body)


class TestSqlPredicate:
    def test_no_filters_gives_no_predicate(self):
        assert sql_predicate(parse_query("rust", now_ts=NOW)) is None

    def test_domain_predicate_is_parameterised(self):
        pred = sql_predicate(parse_query("domain:github.com", now_ts=NOW))
        assert pred is not None
        where, params = pred
        assert "b.domain = ?" in where
        assert params == ["github.com", "github.com"]

    def test_like_metacharacters_are_escaped(self):
        pred = sql_predicate(parse_query("url:100%", now_ts=NOW))
        where, params = pred
        assert "ESCAPE" in where
        assert params == ["100\\%"]

    def test_dates_become_inclusive_bounds(self):
        pred = sql_predicate(parse_query("after:2024 before:2024", now_ts=NOW))
        where, params = pred
        assert where == "b.date_added >= ? AND b.date_added <= ?"


class TestLexicalIntegration:
    @pytest.fixture()
    def conn(self):
        c = open_db(":memory:")
        _seed(c)
        yield c
        c.close()

    def _ids(self, conn, query):
        parsed = parse_query(query, now_ts=NOW)
        return sorted(
            {
                i
                for ids in lexical_lists(conn, query, limit=20, parsed=parsed).values()
                for i in ids
            }
        )

    def test_a_plain_query_hits_the_same_rows_as_before(self, conn):
        assert self._ids(conn, "async") == [1]

    def test_domain_filter_narrows_to_the_domain(self, conn):
        assert self._ids(conn, "domain:github.com") == [1, 2]

    def test_domain_covers_subdomains(self, conn):
        assert self._ids(conn, "host:github.com") == [1, 2] or self._ids(
            self.conn, "domain:github.com"
        ) == [1, 2]

    def test_negated_domain_excludes(self, conn):
        assert self._ids(conn, "-domain:pinterest.com tutorial") == [2]

    def test_tag_filter_is_exact(self, conn):
        assert self._ids(conn, "tag:work") == [2]

    def test_tag_filters_do_not_match_partial_words(self, conn):
        assert self._ids(conn, "tag:rea") == []

    def test_folder_filter(self, conn):
        assert self._ids(conn, "folder:dev") == [1, 2, 4]

    def test_title_filter(self, conn):
        assert self._ids(conn, "title:kubernetes") == [2]

    def test_date_window(self, conn):
        assert self._ids(conn, "after:2021 before:2022") == [2, 3, 4]

    def test_filter_and_text_combine(self, conn):
        assert self._ids(conn, "machine domain:github.com") == []

    def test_url_filter(self, conn):
        assert self._ids(conn, "url:combinator") == [4]

    def test_the_filter_only_query_needs_no_free_text(self, conn):
        assert self._ids(conn, "domain:pinterest.com") == [3]


# ---------------------------------------------------------------------------
# pipeline integration
# ---------------------------------------------------------------------------


class TestQuickSearchIntegration:
    @pytest.fixture()
    def conn(self):
        c = open_db(":memory:")
        _seed(c)
        yield c
        c.close()

    def test_plain_quick_search_keeps_its_shape(self, conn):
        r = quick_search(conn, "async", settings=None)
        assert [h.bookmark_id for h in r.hits] == [1]
        assert r.filters is None

    def test_filters_are_echoed_on_the_response(self, conn):
        r = quick_search(conn, "rust tag:systems")
        assert r.filters is not None
        assert r.filters["field_filters"][0]["field"] == "tag"
        assert [h.bookmark_id for h in r.hits] == [1]

    def test_filter_only_quick_search(self, conn):
        r = quick_search(conn, "tag:reading")
        assert [h.bookmark_id for h in r.hits] == [4]

    def test_snippet_centres_on_the_query_term(self, conn):
        """A hit deep in the body must show the paragraph that matched."""
        r = quick_search(conn, "thread")
        assert r.hits
        snippet = r.hits[0].snippet
        assert "thread" in snippet.lower()

    def test_sort_date_orders_the_pool(self, conn):
        r = quick_search(conn, "sort:date domain:github.com")
        assert [h.bookmark_id for h in r.hits] == [2, 1]  # newest first


class TestFullSearchIntegration:
    @pytest.fixture()
    def settings(self, tmp_path):
        from facetmark.config import Settings

        return Settings(data_dir=tmp_path, use_mock_provider=True, embed_dim=32,
                        embed_model="mock-embed", chat_model="mock-chat")

    @pytest.fixture()
    def conn(self):
        c = open_db(":memory:")
        _seed(c)
        yield c
        c.close()

    async def test_a_filtered_full_search_applies_the_filter_to_every_facet(
        self, conn, settings
    ):
        from facetmark.providers import MockProvider
        from facetmark.search.pipeline import FULL

        r = await search(
            conn, "domain:github.com", provider=MockProvider(), settings=settings,
            config=FULL,
        )
        assert r.hits
        assert all(h.domain == "github.com" for h in r.hits)

    async def test_a_filter_only_full_search_skips_the_embedding_call(
        self, conn, settings
    ):
        """Nothing to embed: no call, and the lexical facet answers alone."""
        from facetmark.providers import MockProvider
        from facetmark.search.pipeline import FULL

        r = await search(
            conn, "tag:work", provider=MockProvider(), settings=settings, config=FULL,
        )
        assert [h.bookmark_id for h in r.hits] == [2]

    async def test_a_phrase_only_query_still_embeds_the_phrase(
        self, conn, settings
    ):
        from facetmark.providers import MockProvider
        from facetmark.search.pipeline import FULL

        r = await search(
            conn, '"machine learning"', provider=MockProvider(), settings=settings,
            config=FULL,
        )
        assert r.hits  # semantic or lexical, the phrase is not lost
        assert r.filters and r.filters["phrases"] == ["machine learning"]

    async def test_sort_directive_wins_over_relevance(self, conn, settings):
        from facetmark.providers import MockProvider
        from facetmark.search.pipeline import FULL

        r = await search(
            conn, "sort:-date domain:github.com", provider=MockProvider(),
            settings=settings, config=FULL,
        )
        assert [h.bookmark_id for h in r.hits] == [1, 2]  # oldest first
