"""Tests for the shared read model.

The contract worth testing here is not "the SQL runs". It is that the three
entry points cannot disagree, that payloads stay bounded, and that a dead link
is still a first-class member of the library.
"""

from __future__ import annotations

import json
import sqlite3
import time

import pytest

from facetmark import service
from facetmark.config import Settings
from facetmark.db import open_db
from facetmark.health import store as hstore
from facetmark.health.synth import HealthCheck
from facetmark.health.verdicts import Status
from facetmark.providers import MockProvider
from facetmark.text import sync_fts

DAY = 86_400


@pytest.fixture()
def st(tmp_path) -> Settings:
    return Settings(data_dir=tmp_path / "fm", use_mock_provider=True,
                    privacy_excluded_domains=("internal.example",))


@pytest.fixture()
def conn(st):
    c = open_db(":memory:")
    yield c
    c.close()


def put(conn: sqlite3.Connection, url: str, title: str, *, folder: str = "",
        added: int | None = None, body: str = "", summary: str = "") -> int:
    rec = service.save_bookmark(conn, url, title=title, folder=folder, date_added=added)
    bid = rec["bookmark_id"]
    if body:
        conn.execute(
            "INSERT INTO content(bookmark_id, body_text, body_hash, char_count, "
            "  extractor, fetch_channel, http_status, fetched_at) "
            "VALUES(?,?,?,?,'test','a',200,?)",
            (bid, body, "h" + str(bid), len(body), int(time.time())),
        )
    if summary:
        conn.execute(
            "INSERT INTO enrichment(bookmark_id, summary, topics, entities, key_points, "
            "  utility, content_type, source_hash, model, created_at) "
            "VALUES(?,?,?,?,?,'reference','article','h','test',?)",
            (bid, summary, json.dumps(["alpha", "beta"]), json.dumps(["Alpha"]),
             json.dumps(["one point"]), int(time.time())),
        )
    sync_fts(conn, bid, title=title, body=body, summary=summary)
    conn.commit()
    return bid


# ---------------------------------------------------------------------------
# pairing token
# ---------------------------------------------------------------------------


class TestPairingToken:
    def test_the_token_is_minted_once_and_then_reused(self, st):
        a = service.pairing_token(st)
        b = service.pairing_token(st)
        assert a == b
        assert len(a) >= 24
        assert st.token_path.read_text(encoding="utf-8").strip() == a

    def test_rotating_replaces_the_token(self, st):
        a = service.pairing_token(st)
        b = service.rotate_token(st)
        assert a != b
        assert service.pairing_token(st) == b

    def test_reading_without_creating_returns_empty(self, st):
        assert service.pairing_token(st, create=False) == ""
        assert not st.token_path.exists()


# ---------------------------------------------------------------------------
# record shaping
# ---------------------------------------------------------------------------


class TestBookmarkRecord:
    def test_a_missing_id_is_none_not_an_exception(self, conn, st):
        assert service.bookmark_record(conn, 999, settings=st) is None

    def test_the_summary_is_clipped_to_the_documented_length(self, conn, st):
        bid = put(conn, "https://a.example/1", "T", summary="x" * 900)
        rec = service.bookmark_record(conn, bid, settings=st)
        assert len(rec["summary"]) <= service.SUMMARY_CHARS

    def test_a_bookmark_with_no_summary_falls_back_to_the_body_head(self, conn, st):
        bid = put(conn, "https://a.example/2", "T", body="the body text " * 40)
        rec = service.bookmark_record(conn, bid, settings=st)
        assert rec["summary"].startswith("the body text")
        assert len(rec["summary"]) <= service.SUMMARY_CHARS

    def test_the_body_is_withheld_unless_asked_for(self, conn, st):
        bid = put(conn, "https://a.example/3", "T", body="secret body")
        assert "body_text" not in service.bookmark_record(conn, bid, settings=st)
        full = service.bookmark_record(conn, bid, settings=st, include_body=True)
        assert full["body_text"] == "secret body"

    def test_json_columns_survive_a_round_trip(self, conn, st):
        bid = put(conn, "https://a.example/4", "T", summary="s")
        rec = service.bookmark_record(conn, bid, settings=st)
        assert rec["topics"] == ["alpha", "beta"]
        assert rec["entities"] == ["Alpha"]

    def test_corrupt_json_degrades_to_an_empty_list(self, conn, st):
        bid = put(conn, "https://a.example/5", "T", summary="s")
        conn.execute("UPDATE enrichment SET topics='not json' WHERE bookmark_id=?", (bid,))
        rec = service.bookmark_record(conn, bid, settings=st)
        assert rec["topics"] == []

    def test_a_dead_link_still_returns_a_full_record(self, conn, st):
        """The UI contract: gone means badged, not hidden."""
        bid = put(conn, "https://a.example/6", "Dead page")
        now = int(time.time())
        for t in (now - 30 * DAY, now):
            hstore.record_check(conn, bid, HealthCheck(
                url="https://a.example/6", status=Status.GONE, confidence=0.9,
                http_status=404, checked_at=t,
                archive_url="https://web.archive.org/web/2020/https://a.example/6"))
        rec = service.bookmark_record(conn, bid, settings=st)
        assert rec is not None
        assert rec["health"]["status"] == "gone"
        assert rec["in_graveyard"] is True
        assert rec["url"] == "https://a.example/6"
        assert rec["health"]["archive_url"].startswith("https://web.archive.org/")


# ---------------------------------------------------------------------------
# sessions and relations
# ---------------------------------------------------------------------------


class TestSessionsAndRelations:
    def test_sessions_list_newest_first_and_skip_singletons(self, conn, st):
        conn.execute("INSERT INTO session(id, started_at, ended_at, size, label, method) "
                     "VALUES(1, 100, 200, 3, 'early', 'temporal')")
        conn.execute("INSERT INTO session(id, started_at, ended_at, size, label, method) "
                     "VALUES(2, 900, 950, 1, 'lonely', 'temporal')")
        conn.execute("INSERT INTO session(id, started_at, ended_at, size, label, method) "
                     "VALUES(3, 500, 600, 2, 'later', 'temporal')")
        rows = service.session_list(conn)
        assert [r["session_id"] for r in rows] == [3, 1]

    def test_a_missing_session_is_none(self, conn):
        assert service.session_record(conn, 42) is None

    def test_a_session_record_lists_members_in_saving_order(self, conn, st):
        b1 = put(conn, "https://s.example/1", "first", added=100)
        b2 = put(conn, "https://s.example/2", "second", added=200)
        conn.execute("INSERT INTO session(id, started_at, ended_at, size, method) "
                     "VALUES(7, 100, 200, 2, 'temporal')")
        conn.executemany("INSERT INTO bookmark_session(bookmark_id, session_id) VALUES(?,7)",
                         [(b1,), (b2,)])
        rec = service.session_record(conn, 7)
        assert [m["bookmark_id"] for m in rec["bookmarks"]] == [b1, b2]
        assert rec["span_seconds"] == 100

    def test_an_unknown_edge_kind_is_rejected_rather_than_silently_empty(self, conn, st):
        bid = put(conn, "https://r.example/1", "x")
        with pytest.raises(ValueError, match="unknown edge kind"):
            service.related_records(conn, bid, kind="friendship")

    def test_related_returns_the_edge_kind_that_produced_each_neighbour(self, conn, st):
        a = put(conn, "https://r.example/a", "A")
        b = put(conn, "https://r.example/b", "B")
        conn.execute("INSERT INTO edge(src,dst,kind,weight) VALUES(?,?,'session',1.0)", (a, b))
        conn.execute("INSERT INTO edge(src,dst,kind,weight) VALUES(?,?,'session',1.0)", (b, a))
        out = service.related_records(conn, a)
        assert [r["bookmark_id"] for r in out] == [b]
        assert out[0]["kind"] == "session"


# ---------------------------------------------------------------------------
# suggest
# ---------------------------------------------------------------------------


class TestSuggestFromContext:
    def test_empty_text_returns_empty_without_touching_the_index(self, conn):
        assert service.suggest_from_context(conn, "   ")["hits"] == []

    def test_it_pools_several_sentence_probes(self, conn, st):
        put(conn, "https://c.example/vector", "sqlite-vec benchmark notes",
            body="sqlite vec brute force scan latency")
        put(conn, "https://c.example/other", "unrelated cooking recipe",
            body="onions garlic butter")
        out = service.suggest_from_context(
            conn, "I am comparing sqlite-vec latency.\nNeed a benchmark for brute force scan.")
        assert out["hits"]
        assert out["hits"][0]["title"].startswith("sqlite-vec")
        assert len(out["probes"]) == 2

    def test_snippets_are_clipped(self, conn, st):
        put(conn, "https://c.example/long", "long page", body="lorem ipsum " * 500,
            summary="lorem ipsum " * 100)
        out = service.suggest_from_context(conn, "lorem ipsum")
        for h in out["hits"]:
            assert len(h["snippet"]) <= service.SNIPPET_CHARS

    def test_a_very_long_context_is_truncated_before_use(self, conn, st):
        put(conn, "https://c.example/x", "anything")
        out = service.suggest_from_context(conn, "word " * 5000)
        assert len(out["query"]) <= 200


# ---------------------------------------------------------------------------
# synthesis
# ---------------------------------------------------------------------------


class _ShapedProvider(MockProvider):
    """A provider that answers the synthesis prompt in the required shape."""

    name = "shaped"

    def __init__(self, settings, payload):
        super().__init__(settings)
        self.payload = payload
        self.seen: list[str] = []

    async def chat_json(self, system: str, user: str) -> dict:
        self.seen.append(user)
        return self.payload


class TestSynthesis:
    async def test_it_returns_claims_sources_and_gaps(self, conn, st):
        put(conn, "https://y.example/1", "RRF explained",
            body="reciprocal rank fusion", summary="RRF fuses ranked lists.")
        prov = _ShapedProvider(st, {
            "claims": [{"text": "RRF fuses ranked lists without score calibration.",
                        "sources": [1]}],
            "gaps": ["nothing on learned sparse retrieval"],
        })
        out = await service.synthesize(conn, "RRF", provider=prov, settings=st)
        assert out.degraded is False
        assert out.claims[0]["sources"] == [1]
        assert "nothing on learned sparse retrieval" in out.gaps
        assert out.sources[0]["n"] == 1

    async def test_an_uncited_claim_is_dropped(self, conn, st):
        """A synthesis tool whose claims are not traceable is worse than none."""
        put(conn, "https://y.example/2", "page", summary="text")
        prov = _ShapedProvider(st, {"claims": [{"text": "confident and unsourced"}]})
        out = await service.synthesize(conn, "page", provider=prov, settings=st)
        assert out.degraded is True
        assert all(c["sources"] for c in out.claims)

    async def test_a_citation_out_of_range_is_dropped(self, conn, st):
        put(conn, "https://y.example/3", "page", summary="text")
        prov = _ShapedProvider(st, {"claims": [{"text": "hallucinated cite", "sources": [99]}]})
        out = await service.synthesize(conn, "page", provider=prov, settings=st)
        assert out.degraded is True

    async def test_the_mock_provider_degrades_instead_of_raising(self, conn, st):
        put(conn, "https://y.example/4", "page", summary="a real summary here")
        out = await service.synthesize(conn, "page", provider=MockProvider(st), settings=st)
        assert out.degraded is True
        assert out.claims and out.claims[0]["sources"] == [1]

    async def test_a_provider_exception_degrades_and_says_so(self, conn, st):
        put(conn, "https://y.example/5", "page", summary="summary")

        class Broken(MockProvider):
            async def chat_json(self, system, user):
                raise RuntimeError("no api key")

        out = await service.synthesize(conn, "page", provider=Broken(st), settings=st)
        assert out.degraded is True
        assert any("model unavailable" in g for g in out.gaps)

    async def test_an_empty_library_reports_a_gap_and_calls_no_model(self, conn, st):
        prov = _ShapedProvider(st, {"claims": []})
        out = await service.synthesize(conn, "anything", provider=prov, settings=st)
        assert out.claims == []
        assert prov.seen == []
        assert out.gaps

    async def test_sources_with_nothing_to_quote_never_call_the_model(self, conn, st):
        """The shape a chat-only smoke test actually saw: sources, no answer.

        A lexical hit on an imported-but-unindexed page carries a title and
        nothing else. The prompt's own rule makes the model decline, so the
        call is predetermined to fail -- and its failure used to surface as
        "model returned no usable claims", blaming a model that never had a
        claim to make for a library that had nothing to quote.
        """
        put(conn, "https://y.example/7", "unindexed page")   # no body, no summary
        prov = _ShapedProvider(
            st, {"claims": [{"text": "cannot happen", "sources": [1]}]}
        )
        out = await service.synthesize(conn, "unindexed", provider=prov, settings=st)
        assert prov.seen == []
        assert out.claims == []
        assert out.model == "none"
        assert any("no indexed text" in g for g in out.gaps)

    async def test_a_title_only_summary_is_labelled_in_sources_and_prompts(self, conn, st):
        """The basis column follows the excerpt everywhere it is used."""
        bid = put(conn, "https://y.example/8", "inferred page",
                  summary="an inferred summary")
        conn.execute(
            "UPDATE enrichment SET basis='title', source_hash='t:1' WHERE bookmark_id=?",
            (bid,),
        )
        conn.commit()
        prov = _ShapedProvider(st, {"claims": [{"text": "c", "sources": [1]}]})
        out = await service.synthesize(conn, "inferred", provider=prov, settings=st)
        assert out.sources[0]["basis"] == "title"
        assert "inferred from the page's title" in prov.seen[0]
        assert any("titles only" in g for g in out.gaps)

    async def test_a_body_summary_carries_the_body_basis(self, conn, st):
        put(conn, "https://y.example/9", "real page", summary="read off the page")
        prov = _ShapedProvider(st, {"claims": [{"text": "c", "sources": [1]}]})
        out = await service.synthesize(conn, "real", provider=prov, settings=st)
        assert out.sources[0]["basis"] == "body"
        assert "inferred from the page's title" not in prov.seen[0]

    async def test_a_dead_source_is_flagged_as_a_gap(self, conn, st):
        bid = put(conn, "https://y.example/6", "dead page", summary="still indexed")
        now = int(time.time())
        for t in (now - 30 * DAY, now):
            hstore.record_check(conn, bid, HealthCheck(
                url="https://y.example/6", status=Status.GONE, confidence=0.9,
                http_status=404, checked_at=t))
        prov = _ShapedProvider(st, {"claims": [{"text": "c", "sources": [1]}]})
        out = await service.synthesize(conn, "dead", provider=prov, settings=st)
        assert any("look dead" in g for g in out.gaps)


# ---------------------------------------------------------------------------
# writes
# ---------------------------------------------------------------------------


class TestSaveBookmark:
    def test_saving_the_same_url_twice_does_not_duplicate(self, conn, st):
        a = service.save_bookmark(conn, "https://w.example/p", title="one", settings=st)
        b = service.save_bookmark(conn, "https://w.example/p", title="two", settings=st)
        assert a["created"] is True and b["created"] is False
        assert a["bookmark_id"] == b["bookmark_id"]
        assert conn.execute("SELECT COUNT(*) FROM bookmark").fetchone()[0] == 1

    def test_tracking_parameters_collapse_to_the_same_row(self, conn, st):
        a = service.save_bookmark(conn, "https://w.example/q?utm_source=news", settings=st)
        b = service.save_bookmark(conn, "https://w.example/q?utm_campaign=x", settings=st)
        assert a["bookmark_id"] == b["bookmark_id"]

    def test_the_original_url_is_what_we_navigate_to(self, conn, st):
        rec = service.save_bookmark(conn, "http://w.example/r?utm_source=n#frag", settings=st)
        assert rec["url"] == "http://w.example/r?utm_source=n#frag"

    def test_an_excluded_domain_is_marked_on_the_way_in(self, conn, st):
        rec = service.save_bookmark(conn, "https://internal.example/secret", settings=st)
        assert rec["privacy_skipped"] is True

    def test_a_saved_bookmark_is_searchable_immediately(self, conn, st):
        service.save_bookmark(conn, "https://w.example/s", title="quokka husbandry",
                              settings=st)
        hits = service.quick_search(conn, "quokka").hits
        assert [h.title for h in hits] == ["quokka husbandry"]

    def test_folder_depth_is_not_derived_by_splitting_on_slash(self, conn, st):
        """Folder names legitimately contain '/'. Splitting corrupts 6.5% of a
        real library, so the display path is stored verbatim."""
        rec = service.save_bookmark(conn, "https://w.example/t", folder="AI/ML papers",
                                    settings=st)
        assert rec["folder"] == "AI/ML papers"
        assert rec["folder_depth"] == 1

    def test_a_non_http_scheme_is_stored_but_not_indexable(self, conn, st):
        rec = service.save_bookmark(conn, "data:text/html,hello", settings=st)
        row = conn.execute("SELECT indexable FROM bookmark WHERE id=?",
                           (rec["bookmark_id"],)).fetchone()
        assert row["indexable"] == 0


class TestRecordOpen:
    def test_opening_increments_the_counter_and_logs_the_query(self, conn, st):
        bid = put(conn, "https://o.example/1", "page")
        service.record_open(conn, bid, query="how to")
        service.record_open(conn, bid)
        rec = service.bookmark_record(conn, bid, settings=st)
        assert rec["open_count"] == 2
        rows = conn.execute("SELECT query FROM interaction WHERE bookmark_id=?",
                            (bid,)).fetchall()
        assert sorted(r["query"] or "" for r in rows) == ["", "how to"]

    def test_a_stale_id_is_reported_not_a_database_error(self, conn):
        """A client can hold an id the library no longer has: the extension
        paints a list, the row goes, the user clicks. The `interaction` insert
        then trips a foreign key, which used to surface as a 500 with the SQL
        string in the body."""
        assert service.record_open(conn, 999999, query="gone") is False
        assert conn.execute("SELECT COUNT(*) FROM interaction").fetchone()[0] == 0


# ---------------------------------------------------------------------------
# stats and orchestration
# ---------------------------------------------------------------------------


class TestStats:
    def test_stats_reports_every_stage_even_when_zero(self, conn, st):
        put(conn, "https://st.example/1", "a", body="body")
        s = service.library_stats(conn)
        for key in ("bookmarks", "indexable", "with_body", "enriched", "intent_kept",
                    "sessions", "edges", "domains", "queue", "health", "edges_by_kind"):
            assert key in s
        assert s["bookmarks"] == 1
        assert s["with_body"] == 1


class TestIndexAll:
    async def test_the_pipeline_runs_in_the_order_the_filter_depends_on(self, conn, st):
        """Content vectors must exist before intent filtering probes the index."""
        for i in range(4):
            put(conn, f"https://ix.example/{i}", f"page {i} about vectors",
                body=f"page {i} discusses vector search and sqlite storage " * 6)
        seen: list[str] = []
        rep = await service.index_all(
            conn, settings=st, fetch=False, progress=lambda n, v: seen.append(n)
        )
        assert seen == ["enrich", "embed_content", "filter_intents", "embed_intents",
                        "sessions", "edges"]
        assert rep.steps["enrich"]["enriched"] == 4
        assert rep.steps["embed_content"]["embedded"] == 4
        assert set(rep.seconds) == set(seen)

    async def test_skipping_the_fetch_stage_omits_it_from_the_report(self, conn, st):
        put(conn, "https://ix.example/x", "solo", body="text " * 60)
        rep = await service.index_all(conn, settings=st, fetch=False)
        assert "fetch" not in rep.steps


class _Ledger(MockProvider):
    """A ``MockProvider`` that remembers every call it was asked to make.

    Counting *texts* rather than requests, because the embedding stages batch:
    one request for sixty-four strings is sixty-four things paid for.
    """

    name = "ledger"

    def __init__(self, settings):
        super().__init__(settings)
        self.chats = 0
        self.embedded: list[str] = []

    async def chat_json(self, system: str, user: str) -> dict:
        self.chats += 1
        return await super().chat_json(system, user)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.embedded.extend(texts)
        return await super().embed(texts)

    def reset(self) -> None:
        self.chats = 0
        self.embedded.clear()


class TestIndexingTwiceIsNotPayingTwice:
    """`facetmark index` is the command a user runs after every import.

    Every stage inside it is separately incremental, which is not the same
    claim as the pipeline being incremental: one stage that re-reads the whole
    library makes the whole command cost a full pass. On a real library that is
    the difference between twenty new pages and nineteen thousand model calls,
    and it is the reason a `--since` flag looked necessary. Asserted here
    end-to-end rather than stage by stage, because it is the composition that
    the user pays for.
    """

    async def test_a_second_pass_over_an_unchanged_library_buys_nothing(self, conn, st):
        for i in range(5):
            put(conn, f"https://twice.example/{i}", f"page {i} on vector search",
                body=f"page {i} discusses vector search, sqlite storage and rank fusion " * 6)
        prov = _Ledger(st)
        await service.index_all(conn, provider=prov, settings=st, fetch=False)
        assert prov.chats >= 5 and prov.embedded, "the first pass has to actually cost something"

        prov.reset()
        rep = await service.index_all(conn, provider=prov, settings=st, fetch=False)

        assert prov.chats == 0, "nothing was re-enriched"
        assert prov.embedded == [], "nothing was re-embedded, for content or for intents"
        assert rep.steps["enrich"]["enriched"] == 0
        assert rep.steps["embed_content"]["embedded"] == 0
        assert rep.steps["embed_intents"]["embedded"] == 0
        assert rep.steps["filter_intents"]["already_scored"] == rep.steps["filter_intents"][
            "candidates"
        ]

    async def test_one_new_bookmark_costs_one_new_bookmark(self, conn, st):
        for i in range(5):
            put(conn, f"https://twice.example/{i}", f"page {i} on vector search",
                body=f"page {i} discusses vector search, sqlite storage and rank fusion " * 6)
        prov = _Ledger(st)
        await service.index_all(conn, provider=prov, settings=st, fetch=False)
        prov.reset()

        put(conn, "https://twice.example/new", "a late arrival about rank fusion",
            body="this one arrived after the library was already indexed " * 6)
        rep = await service.index_all(conn, provider=prov, settings=st, fetch=False)

        assert rep.steps["enrich"]["enriched"] == 1
        assert prov.chats == 1
        # One content vector, plus the intent candidates that came with it. The
        # bound that matters is that it does not scale with the library.
        assert 1 <= len(prov.embedded) <= 1 + st.intent_generate_n
        assert rep.steps["embed_content"]["embedded"] == 1

    async def test_force_still_pays_for_everything(self, conn, st):
        """The escape hatch has to remain an escape hatch."""
        for i in range(4):
            put(conn, f"https://twice.example/{i}", f"page {i} on vector search",
                body=f"page {i} discusses vector search and sqlite storage " * 6)
        prov = _Ledger(st)
        await service.index_all(conn, provider=prov, settings=st, fetch=False)
        prov.reset()

        rep = await service.index_all(conn, provider=prov, settings=st, fetch=False, force=True)
        assert rep.steps["enrich"]["enriched"] == 4
        assert prov.chats == 4
        assert rep.steps["embed_content"]["embedded"] == 4
        assert rep.steps["filter_intents"]["already_scored"] == 0

    def test_tags_are_saved_and_returned(self, conn, st):
        """Tags ride on the record the same way folder does: write, read, echo."""
        rec = service.save_bookmark(conn, "https://w.example/tags", title="tagged",
                                    tags=["work", "rust"], settings=st)
        assert rec["tags"] == ["work", "rust"]

    def test_saving_the_same_url_unions_tags(self, conn, st):
        """A second save is an edit: it adds tags, it does not replace them."""
        service.save_bookmark(conn, "https://w.example/union", tags=["a"], settings=st)
        rec = service.save_bookmark(conn, "https://w.example/union", tags=["b", "a"],
                                    settings=st)
        assert rec["tags"] == ["a", "b"]

    def test_saved_tags_are_searchable_as_free_text(self, conn, st):
        """A tag word is a word: the lexical index must see it immediately."""
        service.save_bookmark(conn, "https://w.example/fts", title="untitled page",
                              tags=["zephyr"], settings=st)
        hits = service.quick_search(conn, "zephyr").hits
        assert [h.title for h in hits] == ["untitled page"]

    def test_saved_tags_answer_the_tag_filter(self, conn, st):
        service.save_bookmark(conn, "https://w.example/filter", title="p",
                              tags=["work"], settings=st)
        hits = service.quick_search(conn, "tag:work").hits
        assert [h.title for h in hits] == ["p"]

    def test_bookmark_record_carries_tags(self, conn, st):
        """bookmark_record is what /bookmark/{id} and MCP get_bookmark return."""
        rec = service.save_bookmark(conn, "https://w.example/rec", tags=["x"], settings=st)
        got = service.bookmark_record(conn, rec["bookmark_id"], settings=st)
        assert got is not None and got["tags"] == ["x"]
