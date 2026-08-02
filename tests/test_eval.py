"""The bench has to be trustworthy before its numbers mean anything."""

from __future__ import annotations

import pytest

from facetmark.config import get_settings
from facetmark.db import open_db
from facetmark.eval import (
    Outcome,
    bootstrap_ci,
    generate_corpus,
    load_corpus,
    mcnemar,
    run_demo,
    run_eval,
    summarise,
)


class TestCorpus:
    def test_pages_are_unique_and_carry_bodies(self):
        c = generate_corpus(size=60, seed=3)
        assert len(c.pages) == 60
        assert len({p.url for p in c.pages}) == 60
        assert len({p.title for p in c.pages}) == 60
        assert min(len(p.body) for p in c.pages) > 200

    def test_every_query_has_exactly_one_labelled_target(self):
        c = generate_corpus(size=60, seed=3)
        assert c.counts["q_content"] == 60
        assert c.counts["q_vague"] == 60
        for q in c.queries:
            assert 0 <= q.target < 60

    def test_vague_queries_never_leak_the_rare_signature(self):
        # If the paraphrase contained the signature term the lexical facet
        # would win it outright and rung C would look free.
        c = generate_corpus(size=60, seed=3)
        for q in c.by_type("q_vague"):
            assert c.pages[q.target].signature not in q.text

    def test_episodic_queries_name_a_session_sibling_not_the_target(self):
        c = generate_corpus(size=60, seed=3)
        for q in c.by_type("q_episodic"):
            page = c.pages[q.target]
            assert page.signature not in q.text
            sibs = [p for p in c.pages
                    if p.session_idx == page.session_idx and p.idx != page.idx]
            assert any(s.signature in q.text for s in sibs)

    def test_pages_cluster_in_time_so_sessions_exist(self):
        c = generate_corpus(size=60, seed=3)
        spans = {}
        for p in c.pages:
            spans.setdefault(p.session_idx, []).append(p.date_added)
        assert len(spans) >= 4
        for stamps in spans.values():
            if len(stamps) > 1:
                assert max(stamps) - min(stamps) < 6 * 3600

    def test_generation_is_deterministic_for_a_seed(self):
        a = generate_corpus(size=40, seed=5)
        b = generate_corpus(size=40, seed=5)
        assert [p.title for p in a.pages] == [p.title for p in b.pages]
        assert [q.text for q in a.queries] == [q.text for q in b.queries]

    def test_load_refuses_a_non_empty_database(self):
        st = get_settings(use_mock_provider=True)
        conn = open_db(":memory:")
        load_corpus(conn, generate_corpus(size=10, seed=1), settings=st)
        with pytest.raises(ValueError, match="empty database"):
            load_corpus(conn, generate_corpus(size=10, seed=2), settings=st)

    def test_loaded_pages_are_searchable_by_body_text(self):
        from facetmark.search.pipeline import quick_search

        st = get_settings(use_mock_provider=True)
        conn = open_db(":memory:")
        c = generate_corpus(size=30, seed=4)
        load_corpus(conn, c, settings=st)
        target = c.pages[0]
        hits = quick_search(conn, target.signature, limit=10)
        assert target.bookmark_id in [h.bookmark_id for h in hits.hits]


class TestMetrics:
    def test_summarise_counts_ranks_the_way_the_report_defines_them(self):
        outs = [Outcome("q_content", 1), Outcome("q_content", 5),
                Outcome("q_content", 11), Outcome("q_content", 0)]
        s = summarise(outs)
        assert s["recall@1"] == 0.25
        assert s["recall@5"] == 0.5
        assert s["recall@10"] == 0.5
        assert s["mrr@10"] == pytest.approx((1 + 0.2) / 4, abs=1e-4)

    def test_a_rank_past_ten_contributes_nothing_to_mrr(self):
        assert summarise([Outcome("q_vague", 11)])["mrr@10"] == 0.0

    def test_bootstrap_ci_brackets_a_real_improvement(self):
        a = [Outcome("q_content", 0) for _ in range(50)]
        b = [Outcome("q_content", 1) for _ in range(50)]
        lo, hi = bootstrap_ci(a, b, resamples=300)
        assert lo == 100.0 and hi == 100.0

    def test_bootstrap_ci_straddles_zero_when_nothing_changed(self):
        outs = [Outcome("q_content", i % 7) for i in range(60)]
        lo, hi = bootstrap_ci(outs, list(outs), resamples=300)
        assert lo == 0.0 and hi == 0.0

    def test_mcnemar_is_one_when_the_rungs_never_disagree(self):
        outs = [Outcome("q_content", 1), Outcome("q_content", 9)]
        assert mcnemar(outs, list(outs)) == {"gained": 0, "lost": 0, "p": 1.0}

    def test_mcnemar_counts_only_discordant_pairs(self):
        a = [Outcome("q_content", 1), Outcome("q_content", 0), Outcome("q_content", 1)]
        b = [Outcome("q_content", 1), Outcome("q_content", 2), Outcome("q_content", 0)]
        m = mcnemar(a, b)
        assert m["gained"] == 1 and m["lost"] == 1
        assert m["p"] == 1.0

    def test_mcnemar_is_significant_for_a_lopsided_swing(self):
        a = [Outcome("q_content", 0) for _ in range(20)]
        b = [Outcome("q_content", 1) for _ in range(20)]
        m = mcnemar(a, b)
        assert m["gained"] == 20 and m["lost"] == 0
        assert m["p"] < 0.001


class TestBench:
    async def test_demo_builds_indexes_and_searches_without_network(self):
        payload = await run_demo(size=24, keep=False)
        assert payload["corpus"]["pages"] == 24
        assert payload["provider"] == "mock"
        assert payload["samples"]
        assert {s["type"] for s in payload["samples"]} == {
            "q_content", "q_vague", "q_episodic"}
        assert all("hits" in s for s in payload["samples"])
        # the demo database is a scratch file and must not survive
        from pathlib import Path
        assert not Path(payload["db"]).exists()

    async def test_eval_reports_every_rung_split_by_query_type(self):
        rep = await run_eval(size=24, ablation=True, bootstrap=100)
        assert [r["config"] for r in rep["rungs"]] == ["A", "B", "C", "D", "E"]
        for row in rep["rungs"]:
            assert set(row["by_type"]) == {"q_content", "q_vague", "q_episodic"}
            assert row["overall"]["n"] == sum(
                row["by_type"][t]["n"] for t in row["by_type"])
        assert len(rep["deltas"]) == 4
        assert rep["end_to_end"]["from"] == "A" and rep["end_to_end"]["to"] == "E"

    async def test_eval_states_the_mock_caveat_and_the_actual_reranker(self):
        rep = await run_eval(size=18, ablation=False, bootstrap=50)
        assert "mock provider" in rep["caveat"]
        assert "placeholder" in rep["reranker"] or rep["reranker"]
        assert rep["provider"] == "mock"

    async def test_no_build_without_a_database_is_refused(self):
        with pytest.raises(ValueError, match="--no-build"):
            await run_eval(build=False, db=None)
