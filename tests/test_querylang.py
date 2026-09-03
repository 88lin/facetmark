"""The query language: parser, filter resolution, and end-to-end search.

The parser tests pin the compatibility rule first -- a query without syntax
parses to itself -- because the whole port lives or dies on that: every
existing query set and eval corpus is plain text, and any behaviour change on
it would be an unmeasured retrieval change wearing a feature's clothes.

The end-to-end tests then exercise one of each construct through both
``quick_search`` and ``search``, on a small library built the way the eval
corpus builds one (mock provider, real FTS indexes). Filters are asserted on
*which ids came back*, never on scores: a filter is a constraint, and its
tests should not inherit the fusion's ranking semantics.
"""

from __future__ import annotations

import pytest

from facetmark.db import open_db
from facetmark.search.pipeline import FULL, quick_search
from facetmark.search.querylang import (
    apply_filters,
    filter_sets,
    parse_query,
    pool_from_filters,
    resolve_date_span,
    resolve_date_value,
    sort_pool,
)

# A fixed "now" so date tests are deterministic. 2026-08-04T00:13:20Z.
NOW = 1785792800.0


# ---------------------------------------------------------------------------
# parser
# ---------------------------------------------------------------------------


class TestParser:
    def test_plain_text_parses_to_itself(self):
        p = parse_query("那个讲 Postgres 索引类型的")
        assert p.text == "那个讲 Postgres 索引类型的"
        assert p.plain_text == p.text
        assert not p.filters
        assert not p.sort
        assert not p.has_syntax

    def test_a_colon_that_is_not_a_field_is_text(self):
        p = parse_query("note: something https://example.com/x state-of-the-art")
        assert p.text == "note: something https://example.com/x state-of-the-art"
        assert not p.filters

    def test_filters_strip_out_of_the_free_text(self):
        p = parse_query("postgres domain:github.com", now=NOW)
        assert p.text == "postgres"
        assert [(f.field, f.value) for f in p.filters] == [("domain", "github.com")]

    def test_site_is_an_alias_of_domain(self):
        p = parse_query("site:github.com", now=NOW)
        assert p.filters[0].field == "domain"

    def test_negation_of_term_and_field(self):
        p = parse_query("privacy -facebook -domain:facebook.com", now=NOW)
        assert p.text == "privacy"
        neg_terms = [t.plain for t in p.terms if t.negated]
        assert neg_terms == ["facebook"]
        assert [(f.field, f.negate) for f in p.filters] == [("domain", True)]

    def test_a_hyphen_inside_a_word_is_not_a_negation(self):
        p = parse_query("state-of-the-art")
        assert p.terms[0].plain == "state-of-the-art"
        assert not p.terms[0].negated

    def test_phrases_survive_with_their_quotes(self):
        p = parse_query('kafka "consumer group rebalancing"')
        assert p.text == 'kafka "consumer group rebalancing"'
        assert p.plain_text == "kafka consumer group rebalancing"
        assert any(t.is_phrase for t in p.terms)

    def test_alternation_expands_to_terms(self):
        p = parse_query("(security|privacy|encryption)")
        assert sorted(t.plain for t in p.terms if not t.negated) == [
            "encryption", "privacy", "security",
        ]

    def test_sort_directive(self):
        p = parse_query("golang sort:-date")
        assert p.text == "golang"
        assert p.sort == "-date"

    def test_an_unknown_sort_value_is_reported_not_applied(self):
        p = parse_query("kafka sort:weird")
        assert p.sort == ""
        assert p.ignored == ["sort:weird"]
        assert p.text == "kafka"

    def test_quoted_field_values(self):
        p = parse_query('text:"GDPR compliance" domain:"example.com"', now=NOW)
        assert [(f.field, f.value) for f in p.filters] == [
            ("text", "GDPR compliance"), ("domain", "example.com"),
        ]
        assert not p.text

    def test_negated_phrase(self):
        p = parse_query('privacy -"social media"')
        assert p.text == "privacy"
        neg = [t for t in p.terms if t.negated]
        assert len(neg) == 1 and neg[0].is_phrase and neg[0].plain == "social media"

    def test_field_alternation(self):
        p = parse_query("domain:(github.com|gitlab.com) postgres", now=NOW)
        assert p.filters[0].value == "github.com|gitlab.com"
        assert p.text == "postgres"

    def test_host_is_its_own_field(self):
        p = parse_query("host:news.ycombinator.com", now=NOW)
        assert [(f.field, f.value) for f in p.filters] == [
            ("host", "news.ycombinator.com"),
        ]
        assert not p.text

    def test_a_relative_before_after_inverts_onto_an_age(self):
        """`after:30d` is "saved in the last 30 days".

        A duration is an age, so the comparison flips -- the same rule
        `added:<30d` follows. The fold happens before the value is validated,
        because `added:30d` on its own is *not* a filter and checking the
        unfolded form threw the legal one away.
        """
        p = parse_query("after:30d before:1y", now=NOW)
        assert [f.value for f in p.filters] == ["<30d", ">1y"]
        assert not p.ignored

    def test_sort_by_open_count(self):
        assert parse_query("sort:opened").sort == "opened"
        assert parse_query("sort:open_count").sort == "opened"
        assert parse_query("sort:-opened").sort == "-opened"

    def test_before_after_fold_onto_added(self):
        p = parse_query("before:2026-05-01 after:2024-01-01", now=NOW)
        assert [f.field for f in p.filters] == ["added", "added"]
        assert p.filters[0].value == "<2026-05-01"
        assert p.filters[1].value == ">=2024-01-01"


class TestDateValues:
    def test_relative_age_inverts_onto_the_timestamp(self):
        # added:>90d = older than 90 days = date_added < now - 90d
        op, ts = resolve_date_value(">90d", now=NOW)
        assert op == "<"
        assert ts == int(NOW - 90 * 86400)

    def test_relative_younger_than(self):
        op, ts = resolve_date_value("<7d", now=NOW)
        assert op == ">"
        assert ts == int(NOW - 7 * 86400)

    def test_absolute_comparison_is_direct(self):
        op, ts = resolve_date_value(">=2026-04-01", now=NOW)
        assert op == ">="
        assert ts == 1775001600  # 2026-04-01T00:00:00Z

    def test_bare_absolute_day_is_a_span(self):
        assert resolve_date_span("2026-04-01") == (1775001600, 1775088000)

    def test_bare_month_and_year_are_spans(self):
        lo, hi = resolve_date_span("2026-04")
        assert lo == 1775001600 and hi == 1777593600
        lo, hi = resolve_date_span("2026")
        assert lo == 1767225600 and hi == 1798761600

    def test_a_bare_duration_is_not_a_date_filter(self):
        assert resolve_date_value("90d", now=NOW) is None
        assert resolve_date_span("90d") is None


# ---------------------------------------------------------------------------
# a small library to resolve against
# ---------------------------------------------------------------------------


@pytest.fixture()
def lib():
    conn = open_db(":memory:")
    rows = [
        # id, url, title, folder, domain, date_added (days before NOW)
        (1, "https://github.com/a/b", "Postgres index types", "study", "github.com", 10),
        (2, "https://github.com/c/d", "CRDT practice notes", "study", "github.com", 400),
        (3, "https://sqlite.org/docs/fts5", "SQLite FTS5 tokenizer", "study", "sqlite.org", 100),
        (4, "https://facebook.com/post", "Facebook privacy scandal", "news", "facebook.com", 5),
        (5, "https://example.com/kafka", "Kafka consumer rebalancing guide", "work", "example.com", 30),
    ]
    for i, url, title, folder, domain, days in rows:
        conn.execute(
            "INSERT INTO bookmark(id, url, url_norm, url_hash, title, folder, folder_depth,"
            " host, domain, date_added, source, indexable, created_at, updated_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (i, url, url, f"h{i}", title, folder, 1, domain, domain,
             int(NOW - days * 86400), "api", 1, int(NOW), int(NOW)),
        )
        from facetmark.text import sync_fts
        sync_fts(conn, i, title=title, body=f"{title} body text {title.lower()}",
                 summary=f"summary of {title}")
    conn.commit()
    yield conn
    conn.close()


class TestFilterSets:
    def test_domain_filter(self, lib):
        parsed = parse_query("domain:github.com", now=NOW)
        include, exclude, ignored = filter_sets(lib, parsed, now=NOW)
        assert include == {1, 2}
        assert not exclude and not ignored

    def test_two_filters_intersect(self, lib):
        parsed = parse_query("domain:github.com added:>90d", now=NOW)
        include, _, _ = filter_sets(lib, parsed, now=NOW)
        assert include == {2}   # 400 days old, from github.com

    def test_negated_field_excludes(self, lib):
        parsed = parse_query("-domain:facebook.com", now=NOW)
        include, exclude, _ = filter_sets(lib, parsed, now=NOW)
        assert include is None
        assert exclude == {4}

    def test_url_wildcards(self, lib):
        parsed = parse_query("url:*/docs/*", now=NOW)
        include, _, _ = filter_sets(lib, parsed, now=NOW)
        assert include == {3}

    def test_title_substring(self, lib):
        parsed = parse_query("title:rebalancing", now=NOW)
        include, _, _ = filter_sets(lib, parsed, now=NOW)
        assert include == {5}

    def test_text_filter_matches_the_stored_body(self, lib):
        """``text:`` is a filter over ``content.body_text``, so it needs a real
        content row -- the fixture's FTS rows are the ranker's index, not this.
        """
        lib.execute(
            "INSERT INTO content(bookmark_id, body_text) VALUES"
            " (3, 'the tokenizer chapter, plus a note on GDPR compliance')"
        )
        lib.commit()
        parsed = parse_query('text:"GDPR compliance"', now=NOW)
        include, _, ignored = filter_sets(lib, parsed, now=NOW)
        assert include == {3}
        assert not ignored

    def test_tag_filter_is_membership_not_a_substring(self, lib):
        """Tags are a closed vocabulary the user typed themselves, so the
        filter is membership in the JSON array. A substring match would make
        ``tag:work`` quietly answer for ``workshop`` -- a filter that widens.
        """
        lib.execute("""UPDATE bookmark SET tags = '["work","rust"]' WHERE id = 1""")
        lib.execute("""UPDATE bookmark SET tags = '["workshop"]' WHERE id = 2""")
        lib.commit()
        parsed = parse_query("tag:work", now=NOW)
        include, _, ignored = filter_sets(lib, parsed, now=NOW)
        assert include == {1}
        assert not ignored

    def test_tag_alternation_is_one_membership_test(self, lib):
        lib.execute("""UPDATE bookmark SET tags = '["work"]' WHERE id = 1""")
        lib.execute("""UPDATE bookmark SET tags = '["rust"]' WHERE id = 3""")
        lib.commit()
        parsed = parse_query("tag:(work|rust)", now=NOW)
        include, _, _ = filter_sets(lib, parsed, now=NOW)
        assert include == {1, 3}

    def test_host_filter_is_a_substring_of_the_hostname(self, lib):
        """`domain:` is the site; `host:` is the machine. The fixture's hosts
        are the same as its domains, so a substring is what distinguishes the
        two fields here."""
        parsed = parse_query("host:sqlite", now=NOW)
        include, _, _ = filter_sets(lib, parsed, now=NOW)
        assert include == {3}

    def test_a_relative_after_window_resolves(self, lib):
        """`after:30d` = saved in the last 30 days. ids 1 (10d) and 4 (5d)."""
        parsed = parse_query("after:30d", now=NOW)
        include, _, ignored = filter_sets(lib, parsed, now=NOW)
        assert include == {1, 4}
        assert not ignored

    def test_opened_range(self, lib):
        lib.execute("UPDATE bookmark SET open_count = 12 WHERE id = 2")
        lib.commit()
        parsed = parse_query("opened:10..", now=NOW)
        include, _, _ = filter_sets(lib, parsed, now=NOW)
        assert include == {2}

    def test_unparseable_filter_is_reported(self, lib):
        """A value that does not resolve is reported by the *parser*.

        It used to be reported by ``filter_sets``, whose third return value
        every caller discards, so the response echoed ``added:90d`` as a filter
        that had applied and quietly answered the query without it.
        """
        parsed = parse_query("added:90d", now=NOW)
        assert not parsed.filters
        assert parsed.ignored == ["added:90d"]
        assert parsed.echo() == {"ignored": ["added:90d"]}
        include, _, ignored = filter_sets(lib, parsed, now=NOW)
        assert include is None and not ignored

    def test_a_filter_that_cannot_resolve_is_still_reported_at_resolution(self, lib):
        """The parser is the gate, not the only check.

        ``filter_sets`` keeps its own report for a filter built by hand rather
        than parsed -- the API takes ``ParsedQuery`` objects, not only strings.
        """
        from facetmark.search.querylang import FieldFilter, ParsedQuery

        parsed = ParsedQuery(filters=[FieldFilter("added", "90d", False, alias="added")])
        include, _, ignored = filter_sets(lib, parsed, now=NOW)
        assert include is None
        assert ignored == ["added:90d"]


class TestPoolFromFilters:
    def test_a_browse_is_date_descending_by_default(self, lib):
        parsed = parse_query("domain:github.com", now=NOW)
        assert pool_from_filters(lib, parsed, limit=10, now=NOW) == [1, 2]

    def test_sort_directive_orders_the_browse(self, lib):
        parsed = parse_query("sort:-date domain:github.com", now=NOW)
        assert pool_from_filters(lib, parsed, limit=10, now=NOW) == [2, 1]

    def test_negated_text_term_browses_the_whole_library_minus_that(self, lib):
        parsed = parse_query("-facebook", now=NOW)
        ids = pool_from_filters(lib, parsed, limit=10, now=NOW)
        assert 4 not in ids and set(ids) == {1, 2, 3, 5}

    def test_sort_relevance_on_a_browse_is_the_default_order(self, lib):
        """A browse has nothing to rank -- the filters *are* the retrieval --
        so the one sort that names the ranking degrades to the default
        timeline. It is a legal directive, so it cannot be an error either.
        """
        parsed = parse_query("domain:github.com sort:relevance", now=NOW)
        assert parsed.sort == "relevance"
        assert pool_from_filters(lib, parsed, limit=10, now=NOW) == [1, 2]

    def test_a_bare_sort_directive_is_a_browse(self, lib):
        """``sort:date`` on its own is "the library, newest first".

        There is no text to rank and no filter to apply, but the query still
        asked for something, so both entry points have to answer it the same
        way. They did not: the first paint browsed and the ranked pass returned
        nothing, so the results blinked out a moment after appearing.
        """
        parsed = parse_query("sort:date", now=NOW)
        assert parsed.is_browse and not parsed.filters
        assert pool_from_filters(lib, parsed, limit=10, now=NOW) == [4, 1, 5, 3, 2]

    def test_an_empty_query_is_not_a_browse(self, lib):
        """Nothing typed is not a request for everything."""
        assert not parse_query("", now=NOW).is_browse

    def test_a_percent_in_a_negated_phrase_is_a_literal(self, lib):
        """The title LIKE behind a negation declares an ESCAPE, so ``%`` is a
        character the user typed, not a wildcard. Left unescaped this phrase
        would span three words of id 5's title and exclude a page nobody
        named -- the FTS side already refuses it, since a phrase has to be
        adjacent.
        """
        parsed = parse_query('-"Kafka%guide"', now=NOW)
        assert 5 in pool_from_filters(lib, parsed, limit=10, now=NOW)


class TestSortPool:
    def test_relevance_is_a_no_op(self, lib):
        assert sort_pool(lib, [4, 1, 3], "relevance") == [4, 1, 3]

    def test_date_sort(self, lib):
        assert sort_pool(lib, [1, 2, 3], "date") == [1, 3, 2]

    def test_open_count_sort(self, lib):
        lib.execute("UPDATE bookmark SET open_count = 5 WHERE id = 3")
        lib.execute("UPDATE bookmark SET open_count = 9 WHERE id = 1")
        lib.commit()
        assert sort_pool(lib, [1, 2, 3], "opened") == [1, 3, 2]
        assert sort_pool(lib, [1, 2, 3], "-opened") == [2, 3, 1]

    def test_domain_sort(self, lib):
        assert sort_pool(lib, [1, 3, 4], "domain") == [4, 1, 3]


class TestApplyFilters:
    def test_filtering_keeps_pool_order(self, lib):
        parsed = parse_query("domain:github.com", now=NOW)
        assert apply_filters(lib, parsed, [3, 1, 2, 5], now=NOW) == [1, 2]


# ---------------------------------------------------------------------------
# end to end
# ---------------------------------------------------------------------------


class TestQuickSearch:
    def test_plain_query_is_unchanged_by_the_language(self, lib):
        r = quick_search(lib, "kafka rebalancing")
        assert r.filters is None and r.sort == ""
        assert [h.bookmark_id for h in r.hits] == [5]

    def test_a_tag_browse_returns_the_tags_it_filtered_on(self, lib):
        """The hit carries the tags back: the filing vocabulary is the user's
        own, so every client can render it the way it renders the folder.
        """
        lib.execute("""UPDATE bookmark SET tags = '["work"]' WHERE id = 5""")
        lib.commit()
        r = quick_search(lib, "tag:work")
        assert [h.bookmark_id for h in r.hits] == [5]
        assert [h.tags for h in r.hits] == [["work"]]

    def test_domain_filter_on_first_paint(self, lib):
        r = quick_search(lib, "domain:github.com")
        assert {h.bookmark_id for h in r.hits} == {1, 2}
        assert r.filters == {"fields": [{"field": "domain", "value": "github.com",
                                         "negate": False}]}

    def test_filter_plus_text(self, lib):
        r = quick_search(lib, "postgres domain:github.com")
        assert [h.bookmark_id for h in r.hits] == [1]

    def test_negation_on_first_paint(self, lib):
        r = quick_search(lib, "privacy -facebook")
        assert [h.bookmark_id for h in r.hits] == []

    def test_sort_date_desc(self, lib):
        r = quick_search(lib, "domain:github.com sort:-date")
        assert [h.bookmark_id for h in r.hits] == [2, 1]
        assert r.sort == "-date"

    def test_a_bare_sort_is_answered_on_first_paint(self, lib):
        r = quick_search(lib, "sort:date")
        assert [h.bookmark_id for h in r.hits] == [4, 1, 5, 3, 2]
        assert r.sort == "date"

    def test_an_unresolvable_date_is_echoed_as_ignored(self, lib):
        """The user sees which token was dropped, and the rest still answers."""
        r = quick_search(lib, "postgres added:90d")
        assert r.filters == {"ignored": ["added:90d"]}
        assert [h.bookmark_id for h in r.hits] == [1]

    def test_sort_relevance_with_a_filter_still_answers(self, lib):
        """First paint of ``domain:x sort:relevance``: a browse asked to rank
        by a ranking that never ran. It reports the sort it was given and
        falls back to the browse order.
        """
        r = quick_search(lib, "domain:github.com sort:relevance")
        assert [h.bookmark_id for h in r.hits] == [1, 2]
        assert r.sort == "relevance"


class TestFullSearch:
    @pytest.fixture()
    def settings(self, tmp_path):
        from facetmark.config import Settings

        return Settings(
            data_dir=tmp_path, use_mock_provider=True, embed_dim=64,
            embed_model="mock-embed", chat_model="mock-chat",
            health_enable_external=False,
        )

    async def test_a_filtered_query_reports_what_applied(self, lib, settings):
        import asyncio

        from facetmark.search.pipeline import search

        r = await asyncio.wait_for(
            search(lib, "kafka domain:example.com", limit=5, settings=settings), 5
        )
        assert set(r.ids) == {5}
        assert r.filters["fields"][0]["field"] == "domain"

    async def test_a_browse_makes_no_model_call(self, lib, settings):
        """The filters are the retrieval; nothing should be embedded for them."""
        import asyncio

        from facetmark.search.pipeline import search

        r = await asyncio.wait_for(
            search(lib, "domain:github.com", limit=5, settings=settings), 5
        )
        assert set(r.ids) == {1, 2}
        assert "filter" in r.facet_sizes
        # A browse never touches the vector path -- mock provider would still
        # have answered, but no call means no `vectors` timing entry either.
        assert "vectors" not in r.took_ms

    async def test_browse_skips_decay_on_old_bookmarks(self, lib, settings):
        """`added:>90d` asks for old pages; the cold layer must not demote them."""
        import asyncio

        from facetmark.search.pipeline import search

        cfg = FULL
        r = await asyncio.wait_for(
            search(lib, "added:>90d", limit=5, config=cfg, settings=settings), 5
        )
        assert set(r.ids) == {2, 3}
        assert not any(h.cold for h in r.hits)

    async def test_plain_full_search_is_unchanged(self, lib, settings):
        import asyncio

        from facetmark.search.pipeline import search

        r = await asyncio.wait_for(
            search(lib, "kafka rebalancing", limit=5, settings=settings), 5
        )
        assert r.filters is None
        assert 5 in set(r.ids)

    async def test_phrase_query_matches_the_phrase_only(self, lib, settings):
        import asyncio

        from facetmark.search.pipeline import search

        r = await asyncio.wait_for(
            search(lib, '"index types"', limit=5, settings=settings), 5
        )
        assert set(r.ids) == {1}

    async def test_a_bare_sort_agrees_with_the_first_paint(self, lib, settings):
        """The ranked pass has to answer a browse the same way the paint did."""
        import asyncio

        from facetmark.search.pipeline import search

        r = await asyncio.wait_for(
            search(lib, "sort:date", limit=10, settings=settings), 5
        )
        assert r.ids == [4, 1, 5, 3, 2]
        assert r.sort == "date"
        # Still a browse: the order is the retrieval, so nothing was embedded.
        assert "vectors" not in r.took_ms
