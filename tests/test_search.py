"""Tests for the retrieval pipeline (P4).

The tests here are written against *behaviour a user would notice*, not against
the shape of the data structures. Where a mechanism has a known degeneracy, the
test asserts the degeneracy rather than papering over it -- a suite that only
proves the happy path is a suite that will not warn anyone.
"""

from __future__ import annotations

import sqlite3
import time

import pytest

from facetmark.config import Settings
from facetmark.db import ensure_vec_tables, open_db, upsert_content_vector
from facetmark.db import now as db_now
from facetmark.edges import build_edges
from facetmark.enrich import embed_content, enrich_all, filter_intents
from facetmark.enrich.vectors import embed_intents
from facetmark.providers import MockProvider
from facetmark.search import (
    CONFIGS,
    FULL,
    Config,
    OverlapReranker,
    anchor_window,
    apply_decay,
    build_context,
    classify,
    classify_assisted,
    cold_bookmark_ids,
    expand,
    hydrate,
    intent_list,
    lexical_lists,
    lexical_search,
    quick_search,
    rank_of,
    related,
    rrf,
    search,
    window_filter,
)
from facetmark.search.context import MAX_BOOST, percentile
from facetmark.search.pipeline import (
    DEFAULT_FACET_WEIGHTS,
    LEXICAL_FACETS,
    SNIPPET_CHARS,
    degrade_for_vector_store,
)
from facetmark.search.rerank import RerankDoc, get_reranker, reorder
from facetmark.search.understand import clear_cache
from facetmark.text import sync_fts

DAY = 86400


# ===========================================================================
# query understanding
# ===========================================================================


class TestQueryUnderstanding:
    def test_a_bare_topic_is_semantic_and_nothing_else(self):
        u = classify("向量数据库怎么选")
        assert u.labels == {"semantic"}
        assert u.rule_hits == []
        assert u.episodic_confidence == 0.0

    def test_quoted_text_is_lexical_and_the_phrase_is_kept(self):
        u = classify('"exactly this phrase" 相关的')
        assert "lexical" in u.labels
        assert u.phrases == ["exactly this phrase"]
        assert "quoted" in u.rule_hits

    def test_cjk_quotes_count_too(self):
        u = classify("「渐进式渲染」怎么做")
        assert u.phrases == ["渐进式渲染"]

    @pytest.mark.parametrize(
        "q", ["getUserMedia", "read_csv 的参数", "HTTP 缓存", "config.yaml 在哪"]
    )
    def test_identifiers_are_lexical(self, q):
        assert "lexical" in classify(q).labels

    def test_a_plain_capitalised_word_is_not_an_identifier(self):
        # Otherwise half of all English queries get labelled lexical.
        u = classify("Docker networking guide")
        assert "identifier" not in u.rule_hits

    def test_a_domain_is_navigational(self):
        u = classify("github.com 上那个仓库")
        assert "navigational" in u.labels

    def test_a_url_is_both_navigational_and_lexical(self):
        u = classify("https://example.com/a/b")
        assert {"navigational", "lexical"} <= u.labels

    def test_last_year_resolves_to_a_window_in_the_past(self):
        now = 1_700_000_000
        u = classify("去年存的那些论文", now_ts=now)
        assert u.is_episodic
        assert u.time_window is not None
        lo, hi = u.time_window
        assert lo < hi <= now
        assert u.episodic_confidence == 1.0

    def test_n_units_ago_resolves(self):
        now = 1_700_000_000
        u = classify("3 个月前看的", now_ts=now)
        lo, hi = u.time_window
        centre = now - 3 * 30 * DAY
        assert lo <= centre <= hi

    def test_an_explicit_year_resolves_to_that_calendar_year(self):
        u = classify("2023 年的会议记录", now_ts=1_700_000_000)
        lo, hi = u.time_window
        assert time.gmtime(lo).tm_year == 2023
        assert hi - lo > 360 * DAY

    def test_a_year_glued_to_chinese_text_still_resolves(self):
        # Python counts CJK as word characters, so the \b that used to close
        # the year pattern never fired here and the commonest Chinese way of
        # writing a year -- no space before 年, no space after it -- resolved
        # to nothing at all.
        for q in ("2023年的那篇文章", "2023年那会儿存的部署笔记", "看2023年存的"):
            u = classify(q, now_ts=1_700_000_000)
            assert u.time_window is not None, q
            assert time.gmtime(u.time_window[0]).tm_year == 2023, q

    def test_a_year_inside_an_identifier_is_not_a_date(self):
        for q in ("es2015 modules", "port 2024px", "vue 2 教程", "abc2023def"):
            assert classify(q, now_ts=1_700_000_000).time_window is None, q

    def test_spelled_out_counts_resolve_like_digits(self):
        now = 1_700_000_000
        for q, months in (("三个月前存的", 3), ("a few months ago", 3),
                          ("saved this two years ago", 24), ("两年前那个工具", 24)):
            u = classify(q, now_ts=now)
            assert u.time_window is not None, q
            lo, hi = u.time_window
            assert lo <= now - months * 30 * DAY <= hi, q

    def test_chinese_teens_resolve(self):
        now = 1_700_000_000
        lo, hi = classify("十五天前", now_ts=now).time_window
        assert lo <= now - 15 * DAY <= hi

    def test_a_vague_marker_is_episodic_but_carries_no_window(self):
        u = classify("配 Docker 那阵子存的东西")
        assert u.is_episodic
        assert u.time_window is None          # anchor-then-window must derive it
        assert u.episodic_confidence == pytest.approx(0.6)

    def test_a_resolvable_date_outranks_a_vague_marker(self):
        u = classify("去年那阵子", now_ts=1_700_000_000)
        assert u.episodic_confidence == 1.0   # not clobbered down to 0.6

    def test_the_boost_stays_inside_the_documented_range(self):
        assert classify("nothing episodic").episodic_boost == 1.0
        assert classify("去年", now_ts=1_700_000_000).episodic_boost == 1.5

    def test_empty_query_produces_no_labels_and_does_not_raise(self):
        assert classify("   ").labels == set()

    async def test_assisted_classification_skips_the_model_when_a_rule_fired(self):
        clear_cache()
        prov = _CountingProvider()
        u = await classify_assisted("去年存的", provider=prov, now_ts=1_700_000_000)
        assert prov.chat_calls == 0
        assert u.source == "rules"

    async def test_assisted_classification_calls_the_model_when_no_rule_fired(self):
        clear_cache()
        prov = _CountingProvider(reply={"labels": ["episodic"], "episodic_confidence": 0.8})
        u = await classify_assisted("那个东西", provider=prov)
        assert prov.chat_calls == 1
        assert u.labels == {"episodic"}
        assert u.episodic_confidence == pytest.approx(0.8)
        assert u.source == "llm"

    async def test_the_second_identical_query_is_served_from_cache(self):
        clear_cache()
        prov = _CountingProvider(reply={"labels": ["semantic"]})
        await classify_assisted("同一个查询", provider=prov)
        again = await classify_assisted("同一个查询", provider=prov)
        assert prov.chat_calls == 1
        assert again.source == "cache"

    async def test_a_failing_model_degrades_to_the_rule_result(self):
        clear_cache()
        prov = _CountingProvider(raise_on_chat=True)
        u = await classify_assisted("那个东西", provider=prov)
        assert u.labels == {"semantic"}
        assert u.source == "rules"


class _CountingProvider:
    def __init__(self, reply=None, raise_on_chat=False):
        self.chat_calls = 0
        self.reply = reply or {}
        self.raise_on_chat = raise_on_chat

    async def chat_json(self, *, system, user, **kw):
        self.chat_calls += 1
        if self.raise_on_chat:
            raise RuntimeError("boom")
        return self.reply

    async def embed(self, texts):
        return [[0.0] * 8 for _ in texts]


# ===========================================================================
# contextual facet
# ===========================================================================


class TestAnchorWindow:
    def test_percentile_interpolates(self):
        assert percentile([0, 10], 0.5) == pytest.approx(5.0)
        assert percentile([0, 10, 20, 30], 0.0) == 0.0
        assert percentile([0, 10, 20, 30], 1.0) == 30.0

    def test_a_single_anchor_cannot_define_a_window(self):
        assert anchor_window([1000]) is None
        assert anchor_window([]) is None

    def test_one_stray_anchor_cannot_stretch_the_window_across_the_library(self):
        # Nine anchors in one afternoon, one from three years earlier.
        cluster = [1_700_000_000 + i * 600 for i in range(9)]
        ts = [*cluster, 1_600_000_000]
        lo, hi = anchor_window(ts)
        full_span = max(ts) - min(ts)        # ~1157 days if we used min-max
        assert hi - lo < 0.2 * full_span

    def test_identical_timestamps_still_produce_a_usable_window(self):
        lo, hi = anchor_window([500, 500, 500])
        assert hi > lo


@pytest.fixture
def ctxdb():
    """Three folders, two sessions, timestamps a month apart."""
    conn = open_db(":memory:")
    base = 1_700_000_000
    rows = [
        # id, title, folder, date_added
        (1, "kubernetes networking", "infra", base),
        (2, "cilium ebpf notes", "infra", base + 300),
        (3, "istio sidecar", "infra", base + 600),
        (4, "sourdough starter", "cooking", base + 60 * DAY),
        (5, "pasta water ratio", "cooking", base + 60 * DAY + 300),
    ]
    for bid, title, folder, ts in rows:
        conn.execute(
            "INSERT INTO bookmark(id,url,url_norm,url_hash,title,folder,domain,"
            "date_added,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (bid, f"https://e{bid}.test/", f"https://e{bid}.test/", f"h{bid}",
             title, folder, f"e{bid}.test", ts, ts, ts),
        )
        sync_fts(conn, bid, title=title)
    conn.execute(
        "INSERT INTO session(id,started_at,ended_at,size,method) VALUES(1,?,?,3,'temporal')",
        (base, base + 600),
    )
    for bid in (1, 2, 3):
        conn.execute("INSERT INTO bookmark_session VALUES(?,1)", (bid,))
    conn.commit()
    return conn


class TestContextSignals:
    def test_session_peers_of_a_top_anchor_get_a_boost(self, ctxdb):
        sig = build_context(ctxdb, anchors=[1], candidates=[1, 2, 3, 4, 5])
        assert sig.session_peers.keys() >= {2, 3}
        assert sig.boost(2) > 1.0
        assert sig.boost(4) == 1.0

    def test_folder_peers_get_a_smaller_boost_than_session_peers(self, ctxdb):
        sig = build_context(ctxdb, anchors=[1], candidates=[2, 4])
        assert sig.boost(2) > 1.0
        # 4 shares neither session nor folder with anchor 1
        assert sig.boost(4) == 1.0

    def test_a_huge_folder_is_treated_as_a_filing_cabinet_not_a_context(self, ctxdb):
        base = 1_700_000_000
        for i in range(100, 160):
            ctxdb.execute(
                "INSERT INTO bookmark(id,url,url_norm,url_hash,title,folder,"
                "date_added,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (i, f"https://x{i}.test/", f"https://x{i}.test/", f"hx{i}",
                 f"misc {i}", "inbox", base, base, base),
            )
        ctxdb.execute("UPDATE bookmark SET folder='inbox' WHERE id=1")
        ctxdb.commit()
        sig = build_context(ctxdb, anchors=[1], candidates=[105, 106])
        assert sig.folder_peers == {}

    def test_the_window_comes_from_the_query_when_the_query_has_a_date(self, ctxdb):
        sig = build_context(
            ctxdb, anchors=[1], candidates=[1, 2, 3, 4, 5],
            query_window=(1_700_000_000 - DAY, 1_700_000_000 + DAY),
            episodic_confidence=1.0,
        )
        assert sig.window_source == "query"
        assert sig.in_window == {1, 2, 3}

    def test_the_window_is_derived_from_the_anchors_when_the_query_has_none(self, ctxdb):
        sig = build_context(
            ctxdb, anchors=[1, 2, 3], candidates=[1, 2, 3, 4, 5],
            episodic_confidence=0.6,
        )
        assert sig.window_source == "anchor"
        assert 4 not in sig.in_window        # a month later, outside the span

    def test_no_episodic_signal_means_no_window_at_all(self, ctxdb):
        sig = build_context(ctxdb, anchors=[1, 2, 3], candidates=[1, 2, 3])
        assert sig.window is None
        assert sig.in_window == set()

    def test_the_total_boost_is_clamped(self, ctxdb):
        sig = build_context(
            ctxdb, anchors=[1], candidates=[2],
            query_window=(0, 2_000_000_000), episodic_confidence=1.0,
        )
        assert sig.boost(2) <= MAX_BOOST

    def test_reasons_explain_the_boost_in_words(self, ctxdb):
        sig = build_context(
            ctxdb, anchors=[1], candidates=[2],
            query_window=(0, 2_000_000_000), episodic_confidence=1.0,
        )
        assert "saved in the same sitting" in sig.reasons(2)
        assert sig.reasons(999) == []

    def test_window_filter_returns_the_library_slice_newest_first(self, ctxdb):
        ids = window_filter(ctxdb, (1_700_000_000, 1_700_000_000 + 700))
        assert ids == [3, 2, 1]


# ===========================================================================
# graph expansion
# ===========================================================================


@pytest.fixture
def graphdb(ctxdb):
    build_edges(ctxdb, kinds=["session", "same_domain", "anchor_sibling", "supersession"])
    return ctxdb


class TestExpansion:
    def test_an_expanded_item_scores_below_the_seed_that_produced_it(self, graphdb):
        out = expand(graphdb, [(1, 1.0)], factor=0.6, limit=5)
        assert out
        assert all(e.score < 1.0 for e in out)

    def test_the_seeds_themselves_are_never_returned(self, graphdb):
        out = expand(graphdb, [(1, 1.0), (2, 0.9)], limit=10)
        assert {e.doc_id for e in out}.isdisjoint({1, 2})

    def test_already_shown_results_are_excluded(self, graphdb):
        out = expand(graphdb, [(1, 1.0)], limit=10, exclude=[2, 3])
        assert out == []

    def test_each_expansion_records_why_it_is_there(self, graphdb):
        out = expand(graphdb, [(1, 1.0)], limit=5)
        e = out[0]
        assert e.via == 1
        assert e.kind in {"session", "same_domain", "anchor_sibling", "supersession"}
        assert "kind" in e.as_dict()

    def test_the_best_path_wins_when_two_seeds_reach_the_same_item(self, graphdb):
        out = expand(graphdb, [(1, 1.0), (3, 0.1)], limit=5)
        two = [e for e in out if e.doc_id == 2][0]
        assert two.via == 1                   # the stronger seed

    def test_expansion_is_capped_by_limit(self, graphdb):
        assert len(expand(graphdb, [(1, 1.0)], limit=1)) == 1

    def test_no_seeds_means_no_expansion(self, graphdb):
        assert expand(graphdb, [], limit=5) == []

    def test_a_hit_past_the_seed_cap_still_has_to_be_excluded_by_name(self, graphdb):
        """``max_seeds`` caps who gets *walked*, not who gets *blocked*.

        The pipeline shows up to ``limit`` hits but only seeds the first
        ``DEFAULT_SEEDS`` of them. If it relied on the built-in seed blocking
        to keep the expansion group disjoint from the result list, hit number
        eleven could reappear one row below itself under a "related" heading.
        """
        walked = expand(graphdb, [(1, 1.0), (2, 0.9)], limit=10, max_seeds=1)
        assert 2 in {e.doc_id for e in walked}         # unseeded, so not blocked
        named = expand(graphdb, [(1, 1.0), (2, 0.9)], limit=10, max_seeds=1,
                       exclude=[1, 2])
        assert 2 not in {e.doc_id for e in named}

    def test_related_walks_one_hop_from_a_single_bookmark(self, graphdb):
        out = related(graphdb, 1, limit=10)
        assert {e.doc_id for e in out} >= {2, 3}

    def test_related_can_be_filtered_to_one_edge_kind(self, graphdb):
        out = related(graphdb, 1, kind="session", limit=10)
        assert {e.kind for e in out} == {"session"}


# ===========================================================================
# metabolism
# ===========================================================================


@pytest.fixture
def colddb():
    conn = open_db(":memory:")
    now = db_now()
    old = now - 800 * DAY
    specs = [
        (1, "old superseded unopened", old, 0),
        (2, "old unopened but nothing replaced it", old, 0),
        (3, "old superseded but opened", old, 5),
        (4, "recent superseded unopened", now - 10 * DAY, 0),
        (5, "old unopened, health says gone", old, 0),
    ]
    for bid, title, ts, opens in specs:
        conn.execute(
            "INSERT INTO bookmark(id,url,url_norm,url_hash,title,date_added,"
            "open_count,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (bid, f"https://c{bid}.test/", f"https://c{bid}.test/", f"hc{bid}",
             title, ts, opens, ts, ts),
        )
    for src in (1, 3, 4):
        conn.execute(
            "INSERT INTO edge(src,dst,kind,weight) VALUES(?,?, 'supersession', 0.7)", (src, 2)
        )
    conn.execute(
        "INSERT INTO health(bookmark_id,checked_at,verdict,confidence) VALUES(5,?, 'gone', 0.9)",
        (now,),
    )
    conn.commit()
    return conn


class TestColdLayer:
    def test_all_three_conditions_are_required(self, colddb):
        cold = cold_bookmark_ids(colddb, age_days=365)
        assert cold == {1, 5}

    def test_being_opened_once_keeps_a_bookmark_out_of_the_cold_layer(self, colddb):
        assert 3 not in cold_bookmark_ids(colddb, age_days=365)

    def test_age_alone_is_not_enough(self, colddb):
        # 2 is old and unopened but nothing supersedes it: reference material.
        assert 2 not in cold_bookmark_ids(colddb, age_days=365)

    def test_a_health_verdict_can_stand_in_for_a_supersession_edge(self, colddb):
        assert 5 in cold_bookmark_ids(colddb, age_days=365)

    def test_a_later_healthy_check_clears_an_earlier_gone(self, colddb):
        colddb.execute(
            "INSERT INTO health(bookmark_id,checked_at,verdict,confidence) "
            "VALUES(5,?, 'ok', 0.9)", (db_now() + 10,)
        )
        colddb.commit()
        assert 5 not in cold_bookmark_ids(colddb, age_days=365)

    def test_the_scan_can_be_restricted_to_the_current_page(self, colddb):
        assert cold_bookmark_ids(colddb, age_days=365, ids=[2, 3]) == set()


class TestDecay:
    def test_cold_results_are_demoted_not_removed(self):
        out, info = apply_decay([(1, 1.0), (2, 0.8)], {1}, factor=0.5, rescue_threshold=0.0)
        assert dict(out) == {1: 0.5, 2: 0.8}
        assert [i for i, _ in out] == [2, 1]
        assert info.demoted == 1
        assert not info.rescued

    def test_nothing_happens_when_no_result_is_cold(self):
        out, info = apply_decay([(1, 1.0)], set())
        assert out == [(1, 1.0)]
        assert info.demoted == 0

    def test_the_demotion_is_lifted_when_the_hot_layer_has_nothing(self):
        out, info = apply_decay(
            [(1, 0.9), (2, 0.001)], {1}, factor=0.5, rescue_threshold=0.02
        )
        assert info.rescued
        assert out[0] == (1, 0.9)             # undecayed

    def test_a_page_that_is_entirely_cold_is_always_rescued(self):
        _out, info = apply_decay([(1, 0.9)], {1}, rescue_threshold=0.02)
        assert info.rescued


# ===========================================================================
# rerank
# ===========================================================================


class TestRerank:
    async def test_the_offline_reranker_prefers_title_overlap(self):
        rr = OverlapReranker()
        docs = [
            RerankDoc(1, "unrelated cooking notes", ""),
            RerankDoc(2, "docker compose networking", ""),
        ]
        scores = await rr.score("docker networking", docs)
        assert scores[1] > scores[0]

    async def test_an_empty_query_scores_everything_zero(self):
        assert await OverlapReranker().score("", [RerankDoc(1, "x")]) == [0.0]

    def test_an_all_zero_reranker_is_a_no_op_not_a_shuffle(self):
        hits = [1, 2, 3, 4]
        assert reorder(hits, [0.0, 0.0, 0.0, 0.0], depth=4) == hits

    def test_only_the_head_is_reordered(self):
        hits = [1, 2, 3, 4]
        out = reorder(hits, [0.0, 1.0], depth=2)
        assert out == [2, 1, 3, 4]

    def test_mock_settings_get_the_offline_reranker(self, mock_settings):
        rr = get_reranker(mock_settings, MockProvider(mock_settings))
        assert isinstance(rr, OverlapReranker)

    def test_a_configured_key_gets_the_llm_reranker(self):
        s = Settings(api_key="sk-test", use_mock_provider=False)
        rr = get_reranker(s, MockProvider(s))
        assert rr.name.startswith("llm-listwise")

    async def test_a_failing_llm_reranker_returns_neutral_scores(self):
        from facetmark.search.rerank import LLMReranker

        rr = LLMReranker(_CountingProvider(raise_on_chat=True))
        assert await rr.score("q", [RerankDoc(1, "a"), RerankDoc(2, "b")]) == [0.0, 0.0]

    async def test_the_llm_reranker_reads_scores_keyed_by_id(self):
        from facetmark.search.rerank import LLMReranker

        rr = LLMReranker(_CountingProvider(reply={"scores": {"1": 0.2, "2": 0.9}}))
        assert await rr.score("q", [RerankDoc(1, "a"), RerankDoc(2, "b")]) == [0.2, 0.9]

    async def test_a_garbage_reranker_payload_does_not_crash_the_search(self):
        from facetmark.search.rerank import LLMReranker

        rr = LLMReranker(_CountingProvider(reply={"scores": "not a dict"}))
        assert await rr.score("q", [RerankDoc(1, "a")]) == [0.0]


# ===========================================================================
# fusion weights
# ===========================================================================


class TestFusionWeights:
    def test_trigram_is_damped_relative_to_the_word_index(self):
        assert DEFAULT_FACET_WEIGHTS["lex_tri"] < DEFAULT_FACET_WEIGHTS["lex_seg"]

    def test_a_document_found_by_two_facets_outranks_one_found_by_one(self):
        fused = rrf({"content": [1, 2], "lex_seg": [2, 1]}, weights=DEFAULT_FACET_WEIGHTS)
        # 1 and 2 both appear in both lists; the one ranked 1st twice wins.
        assert len(fused) == 2
        fused2 = rrf({"content": [3], "lex_seg": [3], "intent": [4]})
        assert fused2[0].doc_id == 3


# ===========================================================================
# end-to-end pipeline
# ===========================================================================

PAGES = {
    "https://k8s.test/net": (
        "Kubernetes networking deep dive",
        "infra",
        "A walkthrough of pod to pod networking, CNI plugins, cilium and ebpf "
        "dataplanes, service meshes and how packets actually move between nodes "
        "inside a kubernetes cluster.",
    ),
    "https://vec.test/db": (
        "Choosing a vector database",
        "infra",
        "Comparison of sqlite-vec, faiss, qdrant and pgvector for small local "
        "corpora, covering brute force exact scan versus approximate nearest "
        "neighbour indexes and the crossover point between them.",
    ),
    "https://cook.test/bread": (
        "Sourdough starter maintenance",
        "cooking",
        "How to keep a sourdough starter alive, feeding ratios, hydration and "
        "what a healthy starter smells like after twelve hours at room "
        "temperature.",
    ),
}


@pytest.fixture
async def indexed(mock_settings):
    """A tiny but fully indexed library: content, enrichment, vectors, edges."""
    conn = open_db(":memory:")
    base = 1_700_000_000
    provider = MockProvider(mock_settings)
    for i, (url, (title, folder, body)) in enumerate(PAGES.items(), start=1):
        ts = base + i * 300
        conn.execute(
            "INSERT INTO bookmark(id,url,url_norm,url_hash,title,folder,domain,"
            "date_added,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (i, url, url, f"h{i}", title, folder, url.split("/")[2], ts, ts, ts),
        )
        conn.execute(
            "INSERT INTO content(bookmark_id,body_text,body_hash,char_count,extractor) "
            "VALUES(?,?,?,?, 'trafilatura')",
            (i, body, f"bh{i}", len(body)),
        )
        sync_fts(conn, i, title=title, body=body)
    conn.commit()
    # The mandated order: enrich -> content vectors -> intent filter -> intent
    # vectors. The filter needs the content vectors to probe against.
    await enrich_all(conn, provider=provider, settings=mock_settings)
    await embed_content(conn, provider=provider, settings=mock_settings)
    await filter_intents(conn, provider=provider, settings=mock_settings)
    await embed_intents(conn, provider=provider, settings=mock_settings)
    build_edges(conn, kinds=["same_domain", "anchor_sibling", "supersession"])
    return conn, provider


@pytest.fixture
async def graphed(indexed):
    """``indexed`` plus the edges that make a graph lane mean anything.

    The base fixture is three pages on three unrelated domains, so the kinds it
    builds -- same_domain, anchor_sibling, supersession -- produce an empty edge
    table. Every assertion about the expansion group written against it was
    therefore vacuously true, which is how a broken graph lane kept three green
    tests.
    """
    conn, provider = indexed
    conn.executemany(
        "INSERT OR REPLACE INTO edge(src,dst,kind,weight) VALUES(?,?,?,?)",
        [(1, 3, "session", 1.0), (3, 1, "session", 1.0),
         (2, 3, "semantic", 0.8), (3, 2, "semantic", 0.8)],
    )
    conn.commit()
    return conn, provider


class TestQuickSearch:
    def test_the_first_paint_needs_no_model_and_finds_the_obvious_hit(self, indexed):
        conn, _ = indexed
        r = quick_search(conn, "sourdough")
        assert r.hits
        assert r.hits[0].bookmark_id == 3
        assert r.config == "quick"

    def test_the_first_paint_still_classifies_the_query(self, indexed):
        conn, _ = indexed
        r = quick_search(conn, '"sourdough starter"')
        assert "lexical" in r.understanding.labels

    def test_a_two_character_cjk_query_survives_the_trigram_blind_spot(self):
        conn = open_db(":memory:")
        ts = 1_700_000_000
        conn.execute(
            "INSERT INTO bookmark(id,url,url_norm,url_hash,title,date_added,"
            "created_at,updated_at) VALUES(1,'https://z.test/','https://z.test/','hz',"
            "'效率工具合集',?,?,?)", (ts, ts, ts),
        )
        sync_fts(conn, 1, title="效率工具合集")
        conn.commit()
        r = quick_search(conn, "工具")
        assert r.ids == [1]
        assert "lex_seg" in r.facet_sizes      # trigram alone would return nothing


class TestFullSearch:
    async def test_it_returns_hits_with_provenance(self, indexed, mock_settings):
        conn, prov = indexed
        r = await search(conn, "kubernetes networking", provider=prov, settings=mock_settings)
        assert r.hits
        top = r.hits[0]
        assert top.bookmark_id == 1
        assert top.facets                       # which facets voted for it
        assert top.ranks
        assert top.snippet
        assert len(top.snippet) <= SNIPPET_CHARS

    async def test_every_stage_is_timed(self, indexed, mock_settings):
        conn, prov = indexed
        r = await search(conn, "vector database", provider=prov, settings=mock_settings)
        assert {"understand", "lexical", "vectors", "fuse", "total"} <= set(r.took_ms)

    async def test_the_ablation_ladder_turns_facets_on_one_at_a_time(
        self, indexed, mock_settings
    ):
        conn, prov = indexed
        seen = {}
        for name in "ABCDE":
            r = await search(
                conn, "vector database", config=CONFIGS[name],
                provider=prov, settings=mock_settings,
            )
            seen[name] = set(r.facet_sizes)
        assert seen["A"] <= {"content"}
        assert "lex_seg" in seen["B"]
        assert "intent" in seen["C"]
        assert seen["C"] == seen["D"] == seen["E"]   # D and E add stages, not facets

    async def test_only_configs_d_and_up_produce_an_expansion_group(
        self, graphed, mock_settings
    ):
        conn, prov = graphed
        b = await search(conn, "networking", config=CONFIGS["B"], limit=2,
                         provider=prov, settings=mock_settings)
        d = await search(conn, "networking", config=CONFIGS["D"], limit=2,
                         provider=prov, settings=mock_settings)
        assert b.expanded == []
        assert [h.bookmark_id for h in d.expanded] == [3]

    async def test_the_expansion_group_never_overlaps_the_main_results(
        self, graphed, mock_settings
    ):
        conn, prov = graphed
        r = await search(conn, "infra", limit=2, provider=prov, settings=mock_settings)
        assert r.expanded, "disjointness from an empty list proves nothing"
        assert {h.bookmark_id for h in r.expanded}.isdisjoint(r.ids)

    async def test_an_expanded_row_says_which_bookmark_it_came_from(
        self, graphed, mock_settings
    ):
        conn, prov = graphed
        r = await search(conn, "kubernetes networking", limit=2,
                         provider=prov, settings=mock_settings)
        exp = [h for h in r.expanded if h.bookmark_id == 3]
        assert exp, "the graph neighbour of a hit never surfaced"
        assert exp[0].via in {1, 2}
        assert exp[0].via_kind in {"session", "semantic"}

    async def test_a_neighbour_the_retriever_also_considered_is_still_expandable(
        self, graphed, mock_settings
    ):
        """Exclude what the user *sees*, not what the retriever *weighed*.

        Every vector facet hands back ``candidates_per_facet`` neighbours
        whether or not any of them is any good, so the fused pool here is the
        entire library. Excluding the pool -- which is what this used to do --
        left the expansion group with only those documents that no facet
        retrieved at all: on a small library that is the empty set, and on a
        large one it is precisely the documents with the weakest claim to being
        shown. A graph neighbour of a hit is *by construction* the sort of
        document a vector facet also drags in, so the pool and the graph lane
        overlap almost completely, and the exclusion ate the feature.
        """
        conn, prov = graphed
        n = conn.execute("SELECT COUNT(*) AS c FROM bookmark").fetchone()["c"]
        r = await search(conn, "kubernetes networking", config=CONFIGS["D"], limit=2,
                         provider=prov, settings=mock_settings)
        assert r.facet_sizes["content"] == n      # the pool really is everything
        assert [h.bookmark_id for h in r.expanded] == [3]

    async def test_config_e_records_which_reranker_actually_ran(
        self, indexed, mock_settings
    ):
        conn, prov = indexed
        r = await search(conn, "sourdough", config=CONFIGS["E"],
                         provider=prov, settings=mock_settings)
        # Honesty requirement: an offline placeholder must announce itself.
        assert "placeholder" in r.reranker

    async def test_the_contextual_boost_is_reported_per_hit(self, indexed, mock_settings):
        conn, prov = indexed
        r = await search(conn, "infra 那阵子", config=CONFIGS["D"],
                         provider=prov, settings=mock_settings)
        assert r.context is not None
        assert all(1.0 <= h.context_boost <= MAX_BOOST for h in r.hits)

    async def test_context_never_changes_the_facet_lists(self, indexed, mock_settings):
        conn, prov = indexed
        c = await search(conn, "vector database", config=CONFIGS["C"],
                         provider=prov, settings=mock_settings)
        d = await search(conn, "vector database", config=CONFIGS["D"],
                         provider=prov, settings=mock_settings)
        assert c.facet_sizes == d.facet_sizes

    async def test_a_purely_episodic_query_falls_back_to_the_time_window(
        self, indexed, mock_settings
    ):
        conn, prov = indexed
        base = 1_700_000_000
        r = await search(
            conn, "上个月", provider=prov, settings=mock_settings,
            now_ts=base + 40 * DAY,
        )
        # No topic in the query, so the window is the query.
        assert r.understanding.time_window is not None
        assert r.hits

    async def test_a_lexically_unmatchable_query_returns_an_empty_page_not_an_error(
        self, indexed, mock_settings
    ):
        conn, prov = indexed
        cfg = Config("lex-only", frozenset({"lex_seg", "lex_tri"}))
        r = await search(conn, "zzzzqqq", config=cfg, provider=prov, settings=mock_settings)
        assert r.hits == []

    async def test_a_vector_facet_has_no_distance_floor_and_returns_the_whole_library(
        self, indexed, mock_settings
    ):
        """A known and deliberate degeneracy, asserted so it cannot surprise anyone.

        KNN returns the k nearest vectors, full stop -- there is no notion of
        "too far to bother". On a library smaller than k that means *every*
        bookmark comes back for *every* query, however nonsensical. It is
        harmless in the fused ranking (the lexical facets abstain, so the
        garbage scores are uniformly low), but it is the reason a
        vector-only configuration cannot be judged on a toy corpus, and the
        reason the intent self-consistency filter is powerless below its probe
        depth.
        """
        conn, prov = indexed
        cfg = Config("vec-only", frozenset({"content"}))
        r = await search(conn, "zzzzqqq", config=cfg, provider=prov, settings=mock_settings)
        assert len(r.hits) == 3

    async def test_the_response_serialises_to_plain_json_types(
        self, indexed, mock_settings
    ):
        import json

        conn, prov = indexed
        r = await search(conn, "kubernetes", provider=prov, settings=mock_settings)
        json.dumps(r.as_dict())                    # must not raise

    async def test_a_cold_result_is_marked_and_demoted(self, indexed, mock_settings):
        conn, prov = indexed
        old = db_now() - 900 * DAY
        conn.execute("UPDATE bookmark SET date_added=?, open_count=0 WHERE id=3", (old,))
        conn.execute("INSERT INTO edge(src,dst,kind,weight) VALUES(3,1,'supersession',0.7)")
        conn.commit()
        hot = await search(conn, "sourdough starter", config=CONFIGS["E"],
                           provider=prov, settings=mock_settings)
        full = await search(conn, "sourdough starter", config=FULL,
                            provider=prov, settings=mock_settings)
        cold_hit = [h for h in full.hits if h.bookmark_id == 3]
        assert cold_hit and cold_hit[0].cold
        # It is still present -- demotion, never deletion.
        assert 3 in hot.ids and 3 in full.ids

    async def test_a_config_can_be_built_by_hand(self, indexed, mock_settings):
        conn, prov = indexed
        cfg = Config("custom", frozenset({"lex_seg"}))
        r = await search(conn, "sourdough", config=cfg, provider=prov, settings=mock_settings)
        assert set(r.facet_sizes) <= {"lex_seg"}
        assert r.config == "custom"


class TestIntentFacetPlumbing:
    async def test_intent_vectors_resolve_back_to_their_bookmarks(
        self, indexed, mock_settings
    ):
        conn, prov = indexed
        vec = (await prov.embed(["how do I keep sourdough alive"]))[0]
        ids = intent_list(conn, vec, limit=5)
        assert ids
        assert all(isinstance(i, int) for i in ids)

    async def test_a_bookmark_appears_at_most_once_however_many_intents_it_owns(
        self, indexed, mock_settings
    ):
        conn, prov = indexed
        vec = (await prov.embed(["kubernetes"]))[0]
        ids = intent_list(conn, vec, limit=10)
        assert len(ids) == len(set(ids))

    def test_an_unindexed_library_returns_empty_lists_rather_than_raising(self):
        conn = open_db(":memory:")
        assert intent_list(conn, [0.1] * 8, limit=5) == []


class TestHydration:
    def test_hydrate_of_nothing_is_nothing(self, ctxdb):
        assert hydrate(ctxdb, []) == {}

    def test_hydrate_skips_ids_that_do_not_exist(self, ctxdb):
        assert set(hydrate(ctxdb, [1, 9999])) == {1}


# ===========================================================================
# lexical facet internals
# ===========================================================================


@pytest.fixture
def lexdb():
    conn = open_db(":memory:")
    ts = 1_700_000_000
    rows = [
        (1, "comparison of vector stores", "faiss qdrant sqlite-vec benchmark"),
        (2, "效率工具合集", "整理了一批提示词和效率工具"),
        (3, "docker compose networking", "bridge host overlay networks"),
    ]
    for bid, title, body in rows:
        conn.execute(
            "INSERT INTO bookmark(id,url,url_norm,url_hash,title,date_added,"
            "created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
            (bid, f"https://l{bid}.test/", f"https://l{bid}.test/", f"hl{bid}",
             title, ts, ts, ts),
        )
        sync_fts(conn, bid, title=title, body=body)
    conn.commit()
    return conn


class TestLexicalFacet:
    def test_both_paths_are_returned_separately(self, lexdb):
        lists = lexical_lists(lexdb, "networking")
        assert set(lists) <= {"lex_seg", "lex_tri"}
        assert lists

    def test_a_two_character_cjk_word_is_found_only_by_the_word_index(self, lexdb):
        lists = lexical_lists(lexdb, "工具")
        assert lists.get("lex_seg") == [2]
        # The documented trigram blind spot: queries under 3 characters.
        assert "lex_tri" not in lists

    def test_trigram_rescues_a_partial_latin_word_the_word_index_misses(self, lexdb):
        lists = lexical_lists(lexdb, "compar")
        assert lists.get("lex_tri") == [1]

    def test_the_merged_list_interleaves_both_paths_without_duplicates(self, lexdb):
        merged = lexical_search(lexdb, "networking")
        assert merged
        assert len(merged) == len(set(merged))

    def test_the_merged_list_respects_the_limit(self, lexdb):
        assert len(lexical_search(lexdb, "e", limit=1)) <= 1

    def test_an_empty_query_yields_no_lists_at_all(self, lexdb):
        assert lexical_lists(lexdb, "   ") == {}
        assert lexical_search(lexdb, "   ") == []

    def test_a_query_that_survives_sanitising_but_breaks_fts5_returns_empty(self, lexdb):
        # An unbalanced NEAR/phrase construct: sanitising keeps the words, FTS5
        # still rejects the expression. One broken facet must not take down a
        # search the other three could have answered.
        from facetmark.search.lexical import _run

        assert _run(lexdb, "fts_seg", 'NEAR("a"', (1, 1, 1, 1), 10) == []


class TestTheAblationLadderAndItsComplements:
    """The pre-registered ladder is a scientific record, not a config file.

    W1's gate came back negative in a direction nobody planned for: rung A beat
    every rung above it on the primary metric. The natural follow-up -- "what if
    we remove the facets that hurt?" -- cannot be asked of an additive ladder,
    so leave-one-out rungs were added alongside it. These tests exist to keep
    the two things from blurring into each other: the ladder must stay byte-for-
    byte what was pre-registered, and the complements must be reachable by the
    harness without being mistaken for pre-registered rungs.
    """

    def test_the_pre_registered_ladder_is_still_exactly_what_was_pre_registered(self):
        from facetmark.search.pipeline import ALL_FACETS

        assert set(CONFIGS) == {"A", "B", "C", "D", "E"}
        assert CONFIGS["A"].facets == frozenset({"content"})
        assert CONFIGS["B"].facets == frozenset({"content", "lex_seg", "lex_tri"})
        assert CONFIGS["C"].facets == ALL_FACETS
        assert CONFIGS["D"].facets == ALL_FACETS
        assert CONFIGS["E"].facets == ALL_FACETS
        # Each rung adds exactly one mechanism to the one below it.
        mechanisms = [
            (c.context, c.graph, c.rerank, c.decay) for c in
            (CONFIGS["A"], CONFIGS["B"], CONFIGS["C"], CONFIGS["D"], CONFIGS["E"])
        ]
        assert mechanisms == [
            (False, False, False, False),
            (False, False, False, False),
            (False, False, False, False),
            (True, True, False, False),
            (True, True, True, False),
        ]

    def test_every_exploratory_rung_stays_cheap_and_stays_out_of_the_ladder(self):
        from facetmark.search.pipeline import EXPLORATORY

        assert EXPLORATORY, "the complements are the point of this dict"
        for name, cfg in EXPLORATORY.items():
            # Originally "content in facets", which was true of every rung here
            # while they were all content variants. `lex_only` is deliberately
            # not one: it is the diagnostic for how much of the query set word
            # matching alone can solve, and requiring the content facet would
            # make that unaskable. The invariant that was actually meant is
            # that a rung retrieves from somewhere.
            assert cfg.facets, f"{name} has to retrieve something"
            assert cfg.name == name, f"{name} reports itself as {cfg.name}"
            # 45 s/query at p50 makes a rung unusable for the repeated sweeps
            # these exist for; the reranker stays behind rung E.
            assert not cfg.rerank, f"{name} must stay cheap enough to re-run"
            assert name not in CONFIGS, f"{name} shadows a pre-registered rung"

    def test_the_leave_one_out_complements_are_the_ones_that_drop_a_facet(self):
        from facetmark.search.pipeline import EXPLORATORY, LEXICAL_FACETS

        for name in ("C_nolex", "D_nolex", "A_ctx", "A_graph"):
            cfg = EXPLORATORY[name]
            assert not (cfg.facets & LEXICAL_FACETS), f"{name} still carries a lexical facet"

    def test_lex_only_needs_no_embedding_model(self):
        """The property that makes the audit runnable at all.

        ``pipeline.search()`` guards the vector branch behind
        ``config.facets & VECTOR_FACETS``. If a vector facet ever leaks into
        this rung the audit silently starts requiring a model, and on a machine
        without one it would measure a mock instead of word matching.
        """
        from facetmark.search.pipeline import EXPLORATORY, VECTOR_FACETS

        cfg = EXPLORATORY["lex_only"]
        assert not (cfg.facets & VECTOR_FACETS)
        assert not (cfg.context or cfg.graph or cfg.rerank or cfg.decay)

    def test_a_complement_pairs_with_a_pre_registered_rung_on_everything_but_facets(self):
        from facetmark.search.pipeline import EXPLORATORY

        pairs = {"C_nolex": "C", "D_nolex": "D"}
        for lo, hi in pairs.items():
            a, b = EXPLORATORY[lo], CONFIGS[hi]
            assert (a.context, a.graph, a.decay) == (b.context, b.graph, b.decay), (
                f"{lo} differs from {hi} by more than the lexical facets, so the "
                f"difference between them is no longer attributable"
            )

    def test_the_harness_can_reach_a_complement_by_name(self):
        from facetmark.eval.harness import ALL_CONFIGS
        from facetmark.search.pipeline import EXPLORATORY

        for key in list(CONFIGS) + list(EXPLORATORY):
            assert key in ALL_CONFIGS
        # And the merge did not let a complement shadow a pre-registered rung.
        for key, cfg in CONFIGS.items():
            assert ALL_CONFIGS[key] is cfg

    def test_the_shipped_default_is_not_silently_one_of_the_rungs(self):
        # FULL is deliberately outside the ladder (it adds metabolism). If a
        # future edit makes it identical to a rung, the ladder stops describing
        # what ships and this test should be the thing that notices.
        assert FULL.name == "full"
        assert FULL.decay is True
        assert all(c.decay is False for c in CONFIGS.values())


class TestWhatThisDeploymentActuallyShips:
    """``default_config`` is where the W1 gate reaches the product.

    The gate measured a real embedding model on 2,376 real pages. None of it
    transfers to a deployment whose "embeddings" are a hash of the text, and a
    library that silently returns nothing because it dropped the only facet
    that worked is worse than one that ignores the gate.
    """

    def test_a_real_deployment_gets_the_configuration_the_gate_selected(self):
        from facetmark.search.pipeline import FULL, default_config

        st = Settings(api_key="sk-real", use_mock_provider=False)
        assert default_config(st) is FULL
        assert FULL.facets == frozenset({"content"}), "the gate picked A's facet set"
        assert FULL.graph is True, "expansion was free: 10 won / 0 lost, +9ms"
        # 1.2.0 turned the gated multiplier on: +3.09pp over plain A on 616
        # held-out queries. 1.3.0 turns it back off, because that set never
        # tested when the gate should *stay* out: on 361 probes whose time
        # expression belongs to the subject matter it fires 361/361 and costs
        # -18.83pp, CI95 [-23.27, -14.68]. docs/gate-precision.md.
        assert FULL.context is False, "the gate fires on 361/361 adversarial probes"
        assert FULL.context_gate is False, "no gate to configure with context off"
        assert FULL.rerank is False, "45.4s p50 to repair damage that is now absent"

    def test_a_deployment_with_no_embeddings_falls_back_to_retrieving_by_words(self):
        from facetmark.search.pipeline import FUSED, LEXICAL_FACETS, default_config

        assert default_config(Settings(use_mock_provider=True)) is FUSED
        assert default_config(Settings(api_key="")) is FUSED
        assert FUSED.facets >= LEXICAL_FACETS

    def test_an_injected_mock_overrules_settings_that_claim_otherwise(self):
        from facetmark.search.pipeline import FUSED, default_config

        st = Settings(api_key="sk-real", use_mock_provider=False)
        assert default_config(st, MockProvider(st)) is FUSED

    def test_knowing_nothing_at_all_still_returns_something_runnable(self):
        from facetmark.search.pipeline import FULL, default_config

        assert default_config() is FULL

    async def test_search_with_no_config_argument_resolves_one(self, indexed):
        conn, prov = indexed
        r = await search(conn, "kubernetes", limit=3, provider=prov, settings=prov.settings)
        # Resolved, not left as None, and reported honestly: the response names
        # the rung that actually ran, not the rung the caller asked for.
        assert r.config == "fused"
        assert r.hits


class TestTheTwoKnobsW2HasToFit:
    """Both W1 losses have an obvious repair. Neither repair is believed yet.

    The evidence that suggests each one came out of the same 479 queries any
    A/B would score on, so a win measured here would be a win measured on the
    training set. These tests fix the *mechanics* -- that the knob does what it
    says -- so W2 only has to supply new queries, not new plumbing.
    """

    def test_a_frozen_config_stays_hashable_with_weights_attached(self):
        from facetmark.search.pipeline import Config

        a = Config("x", frozenset({"content"}), weight_overrides=(("lex_tri", 0.2),))
        b = Config("x", frozenset({"content"}), weight_overrides=(("lex_tri", 0.2),))
        # A dict field here would raise on hash and silently break any code
        # that puts configurations in a set or memoises on them.
        assert hash(a) == hash(b)
        assert a == b
        assert len({a, b}) == 1

    def test_overrides_layer_over_the_defaults_instead_of_replacing_them(self):
        from facetmark.search.pipeline import ALL_FACETS, DEFAULT_FACET_WEIGHTS, Config

        cfg = Config("x", ALL_FACETS, weight_overrides=(("lex_seg", 0.3),))
        assert cfg.facet_weights["lex_seg"] == 0.3
        assert cfg.facet_weights["content"] == DEFAULT_FACET_WEIGHTS["content"]
        assert set(cfg.facet_weights) == set(DEFAULT_FACET_WEIGHTS)
        # And the module-level defaults are not mutated by reading a config.
        assert DEFAULT_FACET_WEIGHTS["lex_seg"] == 1.0

    def test_no_overrides_means_bit_identical_fusion_to_the_shipped_default(self):
        from facetmark.search.pipeline import ALL_CONFIGS, DEFAULT_FACET_WEIGHTS

        for name, cfg in ALL_CONFIGS.items():
            if name == "C_lowlex":
                continue
            assert cfg.facet_weights == DEFAULT_FACET_WEIGHTS, f"{name} moved a weight"

    def test_damping_a_facet_changes_who_wins_a_tie(self):
        from facetmark.search.pipeline import ALL_FACETS, Config

        lists = {"content": [1], "lex_seg": [2], "lex_tri": [2]}
        loud = rrf(lists, weights=Config("a", ALL_FACETS).facet_weights)
        quiet = rrf(
            lists,
            weights=Config(
                "b", ALL_FACETS, weight_overrides=(("lex_seg", 0.3), ("lex_tri", 0.2))
            ).facet_weights,
        )
        # Flat weights: two coincidences on weak facets (1.0 + 0.7) outvote one
        # confident hit on the strong one. That is the -5.43pp mechanism.
        assert loud[0].doc_id == 2
        assert quiet[0].doc_id == 1

    def test_the_gate_is_inert_unless_context_is_on(self):
        from facetmark.search.pipeline import ALL_CONFIGS, Config
        from facetmark.search.understand import classify

        plain = classify("kubernetes networking")
        cfg = Config("x", frozenset({"content"}), context=False, context_gate=True)
        assert cfg.wants_context(plain) is False
        # No *rung* turns the gate on -- the ladder measures mechanisms one at a
        # time, and A_gatedctx is a complement, not a rung. `full` turned it on
        # in 1.2.0 and turned it back off in 1.3.0, after 361 adversarial probes
        # priced its false positives at -18.83pp (docs/gate-precision.md), so no
        # shipped profile carries it now.
        for name in ("A", "B", "C", "D", "E", "fused", "full"):
            assert ALL_CONFIGS[name].context_gate is False, f"{name} enabled the gate"
        assert ALL_CONFIGS["A_gatedctx"].context_gate is True
        assert ALL_CONFIGS["A_gatedctx_v2"].context_gate is True

    def test_the_gate_admits_episodic_queries_and_turns_the_rest_away(self):
        from facetmark.search.pipeline import ALL_CONFIGS
        from facetmark.search.understand import QueryUnderstanding

        gated = ALL_CONFIGS["A_gatedctx"]
        ungated = ALL_CONFIGS["A_ctx"]
        episodic = QueryUnderstanding(query="上个月存的那些", labels={"episodic"})
        topical = QueryUnderstanding(query="kubernetes", labels={"content"})

        assert gated.wants_context(episodic) is True
        assert gated.wants_context(topical) is False
        # A_ctx is the unconditional version: +8.14pp episodic, -9.94pp content.
        assert ungated.wants_context(episodic) is True
        assert ungated.wants_context(topical) is True

    def test_the_w2_candidates_are_the_two_repairs_and_nothing_else(self):
        from facetmark.search.pipeline import ALL_CONFIGS, ALL_FACETS

        gated = ALL_CONFIGS["D_gated"]
        d = CONFIGS["D"]
        assert (gated.facets, gated.context, gated.graph) == (d.facets, d.context, d.graph)
        assert gated.context_gate is True and d.context_gate is False

        low = ALL_CONFIGS["C_lowlex"]
        assert low.facets == ALL_FACETS, "C_lowlex damps the lexical facets, it keeps them"
        assert low.facet_weights["lex_seg"] < low.facet_weights["content"]
        assert low.facet_weights["lex_tri"] < low.facet_weights["lex_seg"]

    def test_the_configuration_reports_both_knobs_when_asked_what_it_is(self):
        from facetmark.search.pipeline import ALL_CONFIGS

        d = ALL_CONFIGS["C_lowlex"].as_dict()
        assert d["weight_overrides"] == {"lex_seg": 0.3, "lex_tri": 0.2}
        assert d["context_gate"] is False
        assert ALL_CONFIGS["A_gatedctx"].as_dict()["context_gate"] is True

    async def test_the_gate_leaves_a_topical_query_ranked_exactly_as_plain_a_did(
        self, indexed
    ):
        from facetmark.search.pipeline import ALL_CONFIGS

        conn, prov = indexed
        kw = {"limit": 5, "provider": prov, "settings": prov.settings}
        plain = await search(conn, "kubernetes", config=ALL_CONFIGS["A_graph"], **kw)
        gated = await search(conn, "kubernetes", config=ALL_CONFIGS["A_gatedctx"], **kw)
        assert [h.bookmark_id for h in gated.hits] == [h.bookmark_id for h in plain.hits]
        assert gated.context is None, "the gate should not have built context signals"


class TestAFacetThatKnowsItHasNoOpinion:
    """The third repair: let a weak facet decline to vote.

    `docs/gate-w1.md` §4.1 measured the cost of fusing any weaker facet into a
    strong content vector at 5-6pp of Recall@5. The coincidence that does the
    damage sits at rank 1 of the weak facets, which is why truncating candidate
    lists -- the intuitive fix -- cannot touch it.
    """

    def test_a_clear_winner_reports_confidence_and_a_flat_list_reports_none(self):
        from facetmark.search.abstain import confidence

        assert confidence([10.0, 1.0, 1.0, 1.0, 1.0]) == pytest.approx(1.0)
        assert confidence([5.0, 5.0, 5.0, 5.0, 5.0]) == 0.0
        # A plateau at the top with a tail: the facet cannot tell its own best
        # four results apart, so its rank-1 is arbitrary.
        assert confidence([5.0, 5.0, 5.0, 5.0, 0.0]) == pytest.approx(0.0)
        assert confidence([5.0, 4.0, 3.0, 2.0, 1.0]) == pytest.approx(0.5)

    def test_confidence_survives_the_units_the_facet_happens_to_use(self):
        from facetmark.search.abstain import confidence

        base = [9.0, 4.0, 3.0, 2.0, 1.0]
        shifted = [x - 100.0 for x in base]      # bm25 lives below zero
        scaled = [x * 0.017 for x in base]       # cosine lives near zero
        both = [x * 3.5 - 12.0 for x in base]
        for other in (shifted, scaled, both):
            assert confidence(other) == pytest.approx(confidence(base))

    def test_a_facet_with_almost_nothing_to_say_is_never_silenced_for_saying_it(self):
        from facetmark.search.abstain import MIN_SAMPLE, confidence

        assert MIN_SAMPLE == 3
        assert confidence([1.0]) == 1.0
        assert confidence([1.0, 1.0]) == 1.0
        # One match may be the only answer to the query. Silencing it turns a
        # correct narrow result into an empty page.

    def test_abstention_drops_the_quiet_facets_and_keeps_the_confident_one(self):
        from facetmark.search import abstain

        scored = {
            "content": [(1, 0.9), (2, 0.2), (3, 0.1), (4, 0.05)],   # confident
            "lex_seg": [(5, 0.5), (6, 0.5), (7, 0.5), (8, 0.1)],    # no opinion
        }
        keep, conf = abstain.apply(scored, 0.25)
        assert set(keep) == {"content"}
        assert conf["lex_seg"] < 0.25 <= conf["content"]
        assert set(conf) == {"content", "lex_seg"}, "the silenced facet still reports"

    def test_abstention_never_turns_a_hard_query_into_an_empty_page(self):
        from facetmark.search import abstain

        scored = {
            # A shallow but real gradient: the best score stands above the
            # facet's own middle, just not by much.
            "lex_seg": [(1, 1.0), (2, 0.6), (3, 0.5), (4, 0.4)],
            # Four exact ties: this facet is enumerating, not ranking.
            "lex_tri": [(9, 1.0), (8, 1.0), (7, 1.0), (6, 1.0)],
        }
        keep, conf = abstain.apply(scored, 0.99)
        assert conf["lex_tri"] == 0.0
        assert 0.0 < conf["lex_seg"] < 0.99, "the premise of this test"
        assert len(keep) == 1, "a weak answer beats no answer"
        assert next(iter(keep)) == "lex_seg", "the least bad facet survives"
        assert abstain.apply({}, 0.5) == ({}, {})

    def test_the_all_tied_rescue_is_arbitrary_and_says_so(self):
        # Two facets that are equally, exactly useless both score 0.0, so the
        # rescue has nothing to rank them by and falls back to the facet name.
        # That is arbitrary. It is documented here so that a future change to
        # the tie-break is a deliberate one and not a silent reordering.
        from facetmark.search import abstain

        scored = {
            "lex_seg": [(1, 0.5), (2, 0.5), (3, 0.5)],
            "lex_tri": [(9, 1.0), (8, 1.0), (7, 1.0)],
        }
        keep, conf = abstain.apply(scored, 0.99)
        assert conf == {"lex_seg": 0.0, "lex_tri": 0.0}
        assert list(keep) == ["lex_tri"], "ties break on the name, high to low"
        flipped, _ = abstain.apply(dict(reversed(scored.items())), 0.99)
        assert list(flipped) == ["lex_tri"], "and not on insertion order"

    def test_it_repairs_the_exact_arithmetic_the_report_blames(self):
        from facetmark.search import abstain
        from facetmark.search.pipeline import DEFAULT_FACET_WEIGHTS as W

        # A wrong document ranked first by both lexical facets, the right one
        # ranked first by content. 1/61 + 0.7/61 = 0.0279 beats 1/61 = 0.0164.
        conf_scores = [0.9] + [0.1] * 49
        flat_scores = [0.5] * 50
        scored = {
            "content": list(zip([1] + [800 + i for i in range(49)], conf_scores, strict=True)),
            "lex_seg": list(zip([2] + [900 + i for i in range(49)], flat_scores, strict=True)),
            "lex_tri": list(zip([2] + [950 + i for i in range(49)], flat_scores, strict=True)),
        }
        naive = {n: [i for i, _ in rows] for n, rows in scored.items()}
        assert rrf(naive, weights=W)[0].doc_id == 2, "the documented failure"

        # Truncating candidate lists cannot help: the offenders are at rank 1.
        capped = {n: (v[:10] if n.startswith("lex") else v) for n, v in naive.items()}
        assert rrf(capped, weights=W)[0].doc_id == 2, "depth is the wrong lever"

        # Abstention can, because it removes the vote rather than the tail.
        kept, _ = abstain.apply(scored, 0.25)
        assert set(kept) == {"content"}
        assert rrf(kept, weights=W)[0].doc_id == 1

    def test_the_new_machinery_is_reachable_from_the_package_root(self):
        import facetmark.search as pkg

        for name in ("abstain", "lexical_lists_scored", "vector_lists_scored"):
            assert name in pkg.__all__, f"{name} is public but not exported"
        missing = [n for n in pkg.__all__ if not hasattr(pkg, n)]
        assert not missing, f"__all__ names nothing can import: {missing}"

    def test_nothing_that_ships_or_was_pre_registered_abstains(self):
        from facetmark.search.pipeline import ALL_CONFIGS

        for name, cfg in ALL_CONFIGS.items():
            if name == "C_abstain":
                assert cfg.abstain_margin > 0.0
            else:
                assert cfg.abstain_margin == 0.0, f"{name} turned abstention on"

    def test_the_scored_retrievers_rank_identically_to_the_ones_they_replaced(
        self, indexed
    ):
        from facetmark.search.lexical import lexical_lists, lexical_lists_scored

        conn, _prov = indexed
        plain = lexical_lists(conn, "kubernetes", limit=20)
        scored = lexical_lists_scored(conn, "kubernetes", limit=20)
        assert set(plain) == set(scored)
        for name, ids in plain.items():
            assert ids == [i for i, _ in scored[name]], f"{name} reordered"
            # bm25 is negated on the way out; better matches must sort first.
            vals = [v for _, v in scored[name]]
            assert vals == sorted(vals, reverse=True), f"{name} is not best-first"

    async def test_the_default_path_is_untouched_by_a_mechanism_it_never_runs(
        self, indexed
    ):
        conn, prov = indexed
        kw = {"limit": 5, "provider": prov, "settings": prov.settings}
        r = await search(conn, "kubernetes", config=CONFIGS["C"], **kw)
        assert r.facet_confidence == {}, "no scores computed when margin is 0"
        assert r.hits

    async def test_an_abstaining_search_says_which_facets_it_silenced(self, indexed):
        from facetmark.search.pipeline import ALL_CONFIGS

        conn, prov = indexed
        r = await search(
            conn, "kubernetes", limit=5, provider=prov,
            settings=prov.settings, config=ALL_CONFIGS["C_abstain"],
        )
        assert r.facet_confidence, "the whole point is to be able to fit this"
        assert set(r.facet_sizes) <= set(r.facet_confidence)
        assert all(0.0 <= c <= 1.0 for c in r.facet_confidence.values())
        assert r.hits, "abstention must never empty the page"
        assert "facet_confidence" in r.as_dict()


# ===========================================================================
# the floor the sum does not have
# ===========================================================================


def _worst_case_lists(depth: int = 50) -> dict[str, list[int]]:
    """Doc 1: ranked #1 by content, invisible to everything else.

    Doc 2: ranked last by all four facets. Fillers are unique per facet so
    nothing else accumulates votes. This is the pair the guarantee is about.
    """
    lists = {"content": [1] + [1000 + i for i in range(depth - 2)] + [2]}
    for n, base in (("intent", 2000), ("lex_seg", 3000), ("lex_tri", 4000)):
        lists[n] = [base + i for i in range(depth - 1)] + [2]
    return lists


def _score(fused, doc_id: int) -> float:
    return next(f.score for f in fused if f.doc_id == doc_id)


class TestTheFloorTheSumDoesNotHave:
    """RRF gives a confident single facet no protection at all.

    Two full-weight facets that merely *recall* a document beat a sole-facet #1
    at every rank inside the candidate depth -- crossover rank 62 against a
    depth of 50. That is arithmetic, not tuning, and 81 of the 102 sole-facet
    #1s in the W1 replay left the top 5 because of it
    (``docs/w2-fusion-anatomy.md``). ``max_bonus`` is the standard repair; these
    tests fix its mechanics, not its worth. No configuration that ships sets it.
    """

    def test_max_bonus_restores_the_sole_facet_guarantee(self):
        from facetmark.search.pipeline import DEFAULT_FACET_WEIGHTS as W
        from facetmark.search.rrf import DEFAULT_K, guarantee_bonus

        lists = _worst_case_lists()
        plain = rrf(lists, weights=W)
        # The documented failure: last place four times beats first place once.
        assert _score(plain, 2) > _score(plain, 1)
        assert _score(plain, 2) / _score(plain, 1) == pytest.approx(2.05, abs=0.01)

        lam = guarantee_bonus(DEFAULT_K, 50, W)
        at = rrf(lists, weights=W, max_bonus=lam)
        # Exactly at the crossover the worst case is a tie, not a win.
        assert _score(at, 1) == pytest.approx(_score(at, 2), rel=1e-12)
        above = rrf(lists, weights=W, max_bonus=lam * 1.01)
        assert _score(above, 1) > _score(above, 2)

        # And anything short of the worst case -- here a rival one facet fails
        # to list at all -- loses outright at the crossover itself.
        easier = dict(lists)
        easier["lex_tri"] = lists["lex_tri"][:-1]
        won = rrf(easier, weights=W, max_bonus=lam)
        assert _score(won, 1) > _score(won, 2)
        assert rank_of(won, 1) == 1

    def test_guarantee_bonus_matches_the_closed_form(self):
        from facetmark.search.rrf import guarantee_bonus

        w = {"content": 1.0, "intent": 1.0, "lex_seg": 1.0, "lex_tri": 0.7}
        assert guarantee_bonus(60, 50, w) == pytest.approx(2.361, abs=5e-4)
        # Config B: content + the two lexical facets.
        assert guarantee_bonus(60, 50, {k: w[k] for k in ("content", "lex_seg", "lex_tri")}) \
            == pytest.approx(1.116, abs=5e-4)
        # A single facet needs no bonus -- it cannot be outvoted.
        assert guarantee_bonus(60, 50, {"content": 1.0}) == 0.0
        # Degenerate inputs return 0.0 rather than a negative or a ZeroDivision.
        assert guarantee_bonus(60, 50, {}) == 0.0
        assert guarantee_bonus(60, 1, w) == 0.0
        assert guarantee_bonus(60, 50, {"content": 0.0}) == 0.0
        # Shallow candidate lists are what make the bonus necessary, not deep
        # ones: "last" means rank `depth`, so a deeper list puts the all-last
        # document further down. Past depth 165.7 for these weights it already
        # loses to a sole #1 and the required bonus falls to zero. This is the
        # opposite of the intuition that more candidates means more noise -- the
        # noise is at the top of the other lists, not the bottom.
        assert guarantee_bonus(60, 200, w) == 0.0
        assert guarantee_bonus(60, 166, w) == 0.0
        assert guarantee_bonus(60, 165, w) > 0.0
        assert guarantee_bonus(60, 50, w) > guarantee_bonus(60, 100, w) > 0.0

    def test_max_bonus_zero_is_bit_identical(self):
        from facetmark.search.pipeline import DEFAULT_FACET_WEIGHTS as W

        lists = _worst_case_lists()
        a = rrf(lists, weights=W)
        b = rrf(lists, weights=W, max_bonus=0.0)
        assert [(f.doc_id, f.score) for f in a] == [(f.doc_id, f.score) for f in b]
        assert all(f.max_term == 0.0 for f in b), "no term, no bookkeeping"
        # The max term is reported separately from the votes, so a caller can
        # still see what the sum alone said.
        c = rrf(lists, weights=W, max_bonus=1.0)
        for f in c:
            assert f.score == pytest.approx(sum(f.contributions.values()) + f.max_term)
            assert f.max_term == pytest.approx(max(f.contributions.values()))

    def test_c_max_is_off_by_default(self):
        from facetmark.config import Settings
        from facetmark.search.pipeline import (
            _GUARANTEE_DEPTH,
            ALL_CONFIGS,
            DEFAULT_FACET_WEIGHTS,
        )
        from facetmark.search.rrf import DEFAULT_K, guarantee_bonus

        for name, cfg in ALL_CONFIGS.items():
            if name == "C_max":
                assert cfg.max_bonus > 1.0, "the finding is that it has to be large"
            else:
                assert cfg.max_bonus == 0.0, f"{name} turned the max term on"
        # The coefficient is derived, never typed in.
        assert ALL_CONFIGS["C_max"].max_bonus == guarantee_bonus(
            DEFAULT_K, _GUARANTEE_DEPTH, DEFAULT_FACET_WEIGHTS
        )
        # ... and the depth it was derived for is the depth the search uses.
        assert Settings().candidates_per_facet == _GUARANTEE_DEPTH
        assert Settings().rrf_k == DEFAULT_K
        assert "max_bonus" in ALL_CONFIGS["C_max"].as_dict()

    async def test_the_max_term_reaches_the_pipeline(self, indexed):
        from facetmark.search.pipeline import ALL_CONFIGS

        conn, prov = indexed
        kw = {"limit": 5, "provider": prov, "settings": prov.settings}
        plain = await search(conn, "kubernetes", config=CONFIGS["C"], **kw)
        maxed = await search(conn, "kubernetes", config=ALL_CONFIGS["C_max"], **kw)
        assert plain.hits and maxed.hits
        # Same candidates, different arithmetic: every score moves up.
        top = maxed.hits[0]
        assert top.score > next(
            h.score for h in plain.hits if h.bookmark_id == top.bookmark_id
        )


# ===========================================================================
# the medium the contextual multiplier is measured in
# ===========================================================================


class TestTheMediumTheBoostIsMeasuredIn:
    """The same multiplier is a different instrument in A than in C/D.

    ``docs/gate-w1.md`` §9.2 blamed the +8.14pp / +3.49pp discrepancy on the
    medium without measuring it; ``docs/w3-criterion-medium.md`` measures it.
    These tests pin the two arithmetic facts that report rests on, so changing
    ``MAX_BOOST``, ``rrf_k`` or ``candidates_per_facet`` breaks the test rather
    than silently invalidating the document.
    """

    def test_a_single_facet_rung_is_almost_unbounded_under_the_cap(self):
        from facetmark.config import Settings
        from facetmark.search.context import MAX_BOOST

        s = Settings()
        depth = s.candidates_per_facet
        fused = rrf({"content": list(range(1, depth + 1))}, k=s.rrf_k)
        best = fused[0].score

        def reaches_first(rank: int) -> bool:
            return fused[rank - 1].score * MAX_BOOST >= best

        # 1.60 lifts anything in the top 37 of the candidate pool straight to
        # first place. "Bounded multiplier" is a very weak bound here.
        assert reaches_first(37)
        assert not reaches_first(38)
        # The whole rung spans less than a factor of two, so the cap covers
        # most of it: (60 + 50) / (60 + 1).
        assert fused[0].score / fused[-1].score == pytest.approx(1.803, abs=1e-3)

    def test_the_cap_means_something_different_in_a_fused_rung(self):
        from facetmark.config import Settings
        from facetmark.search.context import MAX_BOOST
        from facetmark.search.pipeline import ALL_FACETS
        from facetmark.search.pipeline import DEFAULT_FACET_WEIGHTS as W

        s = Settings()
        depth = s.candidates_per_facet
        # doc 1: first in one facet only. doc 2: first in the other three.
        lists = {"content": [1] + [1000 + i for i in range(depth - 1)]}
        for n, base in (("intent", 2000), ("lex_seg", 3000), ("lex_tri", 4000)):
            lists[n] = [2] + [base + i for i in range(depth - 1)]
        fused = rrf(lists, k=s.rrf_k, weights=W)
        one = _score(fused, 1)
        three = _score(fused, 2)
        # The MAX_BOOST docstring claims contextual agreement cannot outweigh
        # being several facets' top hit. In a fused rung that holds ...
        assert one * MAX_BOOST < three
        # ... and the rung's span is five times wider than the single-facet
        # one, which is why the same cap moves far fewer positions here.
        span = (sum(W[f] for f in ALL_FACETS) / (s.rrf_k + 1)) / (
            min(W[f] for f in ALL_FACETS) / (s.rrf_k + depth)
        )
        assert span == pytest.approx(9.532, abs=1e-3)
        assert span / 1.803 > 5


# ===========================================================================
# paging
#
# What needs pinning here is not that a slice slices -- that is Python -- but
# *which list* is being sliced, and whether page 2 is the continuation of page
# 1 or a second opinion about the same query. Those are different claims for
# one facet and for several, and the tests are split accordingly.
# ===========================================================================


def _paging_db(n: int = 70):
    """``n`` documents that all match one query, so the ranking is long.

    Lexical only, deliberately: two facets, no provider, no vectors, and the
    fused pool is far longer than ``candidates_per_facet``, which is the
    situation the old fixed depth could not express.
    """
    conn = open_db(":memory:")
    base = 1_700_000_000
    for i in range(1, n + 1):
        title = f"vector database note {i:03d}"
        body = f"note {i} on vector database indexing and nearest neighbour search"
        conn.execute(
            "INSERT INTO bookmark(id,url,url_norm,url_hash,title,folder,domain,"
            "date_added,created_at,updated_at) VALUES(?,?,?,?,?,'notes',?,?,?,?)",
            (i, f"https://p{i}.test/doc", f"https://p{i}.test/doc", f"ph{i}",
             title, f"p{i}.test", base + i, base + i, base + i),
        )
        conn.execute(
            "INSERT INTO content(bookmark_id,body_text,body_hash,char_count,extractor)"
            " VALUES(?,?,?,?,'trafilatura')", (i, body, f"pb{i}", len(body)),
        )
        sync_fts(conn, i, title=title, body=body)
    conn.commit()
    return conn


@pytest.fixture()
def paging_db():
    conn = _paging_db()
    yield conn
    conn.close()


@pytest.fixture()
def paging_settings(tmp_path) -> Settings:
    return Settings(
        data_dir=tmp_path, use_mock_provider=True, embed_dim=64,
        embed_model="mock-embed", chat_model="mock-chat",
        health_enable_external=False,
    )


class TestWhatDeepeningThePoolDoesToTheOrder:
    """The property the whole paging design rests on, and its limit."""

    def test_one_facet_only_appends(self):
        # A single list scores w/(k+rank), strictly decreasing in rank, so the
        # fused order *is* the facet's order and a deeper ask cannot reorder
        # what was already there.
        ids = list(range(1, 101))
        shallow = rrf({"content": ids[:30]}, k=60)
        deep = rrf({"content": ids[:80]}, k=60)
        assert [f.doc_id for f in deep[:30]] == [f.doc_id for f in shallow]
        assert [f.score for f in deep[:30]] == [f.score for f in shallow]

    def test_several_facets_reorder(self):
        """The counterexample the `depth` parameter exists for.

        Doc 1 is rank 1 in one facet and nowhere else, so its score is fixed at
        every depth. Doc 2 is rank 2 in that facet and rank 40 in another: below
        doc 1 while the second facet is only read 30 deep, above it once the
        second facet is read 50 deep. Nothing about doc 1 changed; the pool got
        deeper and the order flipped.
        """
        content = [1, 2] + list(range(1000, 1098))
        lex = list(range(2000, 2039)) + [2] + list(range(3000, 3060))

        def rank_of(depth: int, doc: int) -> int:
            fused = rrf({"content": content[:depth], "lex_seg": lex[:depth]}, k=60)
            return [f.doc_id for f in fused].index(doc)

        # Read 30 deep, doc 2 has only its content rank: 1/62 against doc 1's
        # 1/61, so it sits just below. Read 50 deep it picks up 1/100 from the
        # second facet, and 1/62 + 1/100 clears 1/61 comfortably.
        assert rank_of(30, 1) < rank_of(30, 2)
        assert rank_of(50, 2) < rank_of(50, 1)

    def test_the_shipped_default_has_one_facet(self, paging_settings):
        # Which is why paging the deployed configuration is exact for free,
        # and why `depth` is a correctness knob rather than a default-path one.
        assert len(FULL.facets) == 1


class TestPagingThePipeline:
    def test_a_pinned_depth_makes_every_page_a_slice_of_one_ranking(
        self, paging_db, paging_settings
    ):
        whole = quick_search(
            paging_db, "vector database", limit=70, offset=0, depth=70,
            settings=paging_settings,
        )
        walked: list[int] = []
        for off in range(0, 70, 10):
            p = quick_search(
                paging_db, "vector database", limit=10, offset=off, depth=70,
                settings=paging_settings,
            )
            assert p.offset == off and p.depth == 70
            walked.extend(p.ids)
        assert walked == whole.ids

    async def test_the_fifty_first_result_is_reachable(self, paging_db, paging_settings):
        # `candidates_per_facet` is 50 and used to be the whole pool, so this
        # window did not exist: it is past the end of a list that stopped at 50.
        r = await search(
            paging_db, "vector database", limit=10, offset=45,
            config=CONFIGS["B"], settings=paging_settings,
        )
        assert len(r.hits) == 10
        assert r.depth > paging_settings.candidates_per_facet
        first = await search(
            paging_db, "vector database", limit=45, offset=0, depth=r.depth,
            config=CONFIGS["B"], settings=paging_settings,
        )
        assert not (set(r.ids) & set(first.ids))

    async def test_pinning_the_old_depth_reproduces_the_old_ceiling(
        self, paging_db, paging_settings
    ):
        # Same call, depth pinned at what the pipeline used to use: five hits,
        # then the list stops. This is the behaviour being removed, stated as
        # a test so the removal is legible.
        r = await search(
            paging_db, "vector database", limit=10, offset=45, depth=50,
            config=CONFIGS["B"], settings=paging_settings,
        )
        assert len(r.hits) == 5
        assert r.total == 50

    def test_total_and_has_more_find_the_end_of_the_library(
        self, paging_db, paging_settings
    ):
        early = quick_search(
            paging_db, "vector database", limit=10, offset=0, depth=70,
            settings=paging_settings,
        )
        assert early.total == 70 and early.has_more
        last = quick_search(
            paging_db, "vector database", limit=10, offset=60, depth=70,
            settings=paging_settings,
        )
        assert last.total == 70 and not last.has_more

    def test_depth_capped_separates_the_ceiling_from_the_last_page(self, paging_db, tmp_path):
        # A short page at the depth ceiling is not the end of the results, and
        # a paging UI that cannot tell the two apart stops early and says so
        # with confidence. `depth_capped` is the difference.
        tight = Settings(
            data_dir=tmp_path, use_mock_provider=True, max_candidate_depth=20,
            health_enable_external=False,
        )
        r = quick_search(paging_db, "vector database", limit=10, offset=0, settings=tight)
        assert r.depth == 20
        assert r.has_more and r.depth_capped
        roomy = Settings(
            data_dir=tmp_path, use_mock_provider=True, health_enable_external=False
        )
        done = quick_search(
            paging_db, "vector database", limit=10, offset=60, depth=70, settings=roomy
        )
        assert not done.has_more and not done.depth_capped

    def test_an_oversized_window_is_clamped_and_the_response_says_which(
        self, paging_db, paging_settings
    ):
        # Clamped rather than rejected -- a caller asking for 10,000 rows wants
        # results -- but it must not be told it received 10,000 of them.
        r = quick_search(
            paging_db, "vector database", limit=10_000, offset=-5, settings=paging_settings
        )
        assert r.limit == paging_settings.max_page_size
        assert r.offset == 0
        assert r.depth <= paging_settings.max_candidate_depth

    async def test_a_bigger_page_no_longer_silently_retrieves_deeper(
        self, paging_db, paging_settings
    ):
        # `per_facet = max(candidates_per_facet, limit)` made page size and
        # retrieval depth the same knob. Pinning the depth separates them.
        small = await search(
            paging_db, "vector database", limit=5, depth=60,
            config=CONFIGS["B"], settings=paging_settings,
        )
        large = await search(
            paging_db, "vector database", limit=60, depth=60,
            config=CONFIGS["B"], settings=paging_settings,
        )
        assert small.facet_sizes == large.facet_sizes
        assert small.total == large.total
        assert large.ids[:5] == small.ids


class TestWhatAPageCosts:
    async def test_the_reranker_only_ever_sees_rerank_depth_documents(
        self, paging_db, tmp_path
    ):
        """Stage E used to be handed the whole page.

        `reorder(hits, scores, depth=len(hits))` overrode the module's own
        `DEFAULT_DEPTH`, so a 100-row page put 100 candidates into the single
        listwise call the LLM reranker makes -- both the prompt and the "score
        every id" JSON grow with the page. `docs/gate-w1.md` §7.3 measured that
        call at 45.4 s p50 with the harness's page size of 10.
        """
        seen: list[int] = []

        class Spy:
            name = "spy"

            async def score(self, query, docs):
                seen.append(len(docs))
                return [0.0] * len(docs)

        st = Settings(
            data_dir=tmp_path, use_mock_provider=True, rerank_depth=7,
            health_enable_external=False,
        )
        r = await search(
            paging_db, "vector database", limit=100,
            config=Config("rr", frozenset({"lex_seg", "lex_tri"}), rerank=True),
            settings=st, reranker=Spy(),
        )
        assert len(r.hits) > st.rerank_depth       # the page really is large
        assert seen == [st.rerank_depth]

    @pytest.mark.skipif(
        not hasattr(sqlite3.Connection, "setlimit"),
        reason="Connection.setlimit is 3.11+; the guard cannot be forced on 3.10",
    )
    def test_a_deep_page_survives_a_sqlite_built_with_999_variables(self, tmp_path):
        """`SQLITE_MAX_VARIABLE_NUMBER` is a compile-time constant.

        999 on older builds, 32766 since 3.32 -- so whether a query raises
        depends on which interpreter the user happens to have, and CI's is the
        generous one. Forcing the limit down is the only way to test the
        chunking on a modern host.
        """
        conn = _paging_db(1200)
        conn.setlimit(sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER, 999)
        st = Settings(
            data_dir=tmp_path, use_mock_provider=True, max_page_size=1200,
            max_candidate_depth=2000, health_enable_external=False,
        )
        try:
            r = quick_search(conn, "vector database", limit=1100, settings=st)
            assert len(r.hits) == 1100          # one hydrate of 1100 ids
            cold = cold_bookmark_ids(conn, ids=list(range(1, 1201)))
            assert cold == set()                # one scan over 1200 ids
        finally:
            conn.close()


# ===========================================================================
# running without a vector store
# ===========================================================================


class TestRunningWithoutAVectorStore:
    """What a chat-only deployment sees: a key that answers chat, an embedding
    endpoint that 404s, and therefore a library where no vector table ever got
    built -- while ``api_key`` is set, so ``default_config`` answers FULL.

    Before the degradation these tests pin, FULL over that library answered
    every query with an empty page, even when the words the reader typed were
    sitting in the lexical index the whole time. That is not a degraded
    answer; it is no answer.
    """

    async def test_full_over_an_empty_vector_store_degrades_to_lexical(
        self, paging_db, tmp_path
    ):
        st = Settings(
            data_dir=tmp_path, api_key="sk-chat-only",
            base_url="http://chat.example/v1", health_enable_external=False,
        )
        resp = await search(paging_db, "vector database", limit=5, settings=st)
        assert resp.degraded_from == "full"
        assert resp.config == "full/lex"
        assert resp.hits, "the words were in the lexical index all along"
        assert set(resp.facet_sizes) <= {"lex_seg", "lex_tri"}

    async def test_an_explicit_all_vector_config_degrades_the_same_way(
        self, paging_db, tmp_path
    ):
        """A caller who asks for ``A`` by name gets the same honesty."""
        st = Settings(data_dir=tmp_path, health_enable_external=False)
        resp = await search(paging_db, "vector database", limit=5,
                            config=CONFIGS["A"], settings=st)
        assert resp.degraded_from == "A"
        assert resp.hits

    def test_a_config_that_keeps_a_runnable_facet_runs_as_named(self, paging_db):
        cfg = Config("half", frozenset({"content", "lex_seg"}))
        assert degrade_for_vector_store(paging_db, cfg) == (cfg, "")

    def test_the_degraded_config_inherits_the_flags_it_can_still_honour(self, paging_db):
        cfg = Config("A", frozenset({"content"}), graph=True, decay=True)
        new, was = degrade_for_vector_store(paging_db, cfg)
        assert was == "A"
        assert new.facets == LEXICAL_FACETS
        assert (new.graph, new.decay, new.rerank) == (True, True, False)

    def test_a_library_with_vectors_is_not_downgraded(self, paging_db):
        ensure_vec_tables(paging_db, 4, "mock-embed")
        upsert_content_vector(paging_db, 1, [1.0, 0.0, 0.0, 0.0])
        cfg = Config("A", frozenset({"content"}))
        assert degrade_for_vector_store(paging_db, cfg) == (cfg, "")
