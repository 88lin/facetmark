"""Tests for the retrieval pipeline (P4).

The tests here are written against *behaviour a user would notice*, not against
the shape of the data structures. Where a mechanism has a known degeneracy, the
test asserts the degeneracy rather than papering over it -- a suite that only
proves the happy path is a suite that will not warn anyone.
"""

from __future__ import annotations

import time

import pytest

from facetmark.config import Settings
from facetmark.db import now as db_now
from facetmark.db import open_db
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
    related,
    rrf,
    search,
    window_filter,
)
from facetmark.search.context import MAX_BOOST, percentile
from facetmark.search.pipeline import DEFAULT_FACET_WEIGHTS, SNIPPET_CHARS
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

    def test_every_exploratory_rung_drops_the_lexical_facets_and_nothing_else(self):
        from facetmark.search.pipeline import EXPLORATORY, LEXICAL_FACETS

        assert EXPLORATORY, "the complements are the point of this dict"
        for name, cfg in EXPLORATORY.items():
            assert not (cfg.facets & LEXICAL_FACETS), f"{name} still carries a lexical facet"
            assert "content" in cfg.facets, f"{name} has to retrieve something"
            assert cfg.name == name, f"{name} reports itself as {cfg.name}"
            assert not cfg.rerank, f"{name} must stay cheap enough to re-run"

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
