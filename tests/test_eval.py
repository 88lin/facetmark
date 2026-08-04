"""The bench has to be trustworthy before its numbers mean anything."""

from __future__ import annotations

import json

import pytest

from facetmark.config import get_settings
from facetmark.db import open_db
from facetmark.eval import (
    RUNGS,
    Outcome,
    QueryFileError,
    bootstrap_ci,
    generate_corpus,
    load_corpus,
    load_query_file,
    mcnemar,
    resolve_rungs,
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


class TestQueryFile:
    """Judgements for a library the bench did not generate.

    The synthetic corpus knows its own answers. A real library does not, so the
    answers arrive as a file -- and every way that file can be wrong has to fail
    loudly, because a silently dropped query changes the denominator of every
    recall number in the report.
    """

    @staticmethod
    def _library():
        st = get_settings(use_mock_provider=True)
        conn = open_db(":memory:")
        c = generate_corpus(size=12, seed=5)
        load_corpus(conn, c, settings=st)
        return conn, c

    @staticmethod
    def _write(tmp_path, records):
        p = tmp_path / "q.jsonl"
        p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records),
                     encoding="utf-8")
        return p

    def test_targets_are_bound_by_url_not_by_row_id(self, tmp_path):
        conn, c = self._library()
        page = c.pages[3]
        f = self._write(tmp_path, [
            {"text": "how do I do the thing", "qtype": "q_vague", "target_url": page.url},
        ])
        loaded = load_query_file(conn, f)
        assert len(loaded.queries) == 1
        assert loaded.queries[0].target_id == page.bookmark_id

    def test_tracking_parameters_on_the_target_url_still_match(self, tmp_path):
        """The judgement file is written by hand or by a script that copied a
        URL out of a browser. It should not have to know about utm tags."""
        conn, c = self._library()
        page = c.pages[1]
        f = self._write(tmp_path, [
            {"text": "q", "qtype": "q_content",
             "target_url": page.url + "?utm_source=newsletter"},
        ])
        assert load_query_file(conn, f).queries[0].target_id == page.bookmark_id

    def test_a_target_outside_the_library_is_a_hard_error(self, tmp_path):
        conn, c = self._library()
        f = self._write(tmp_path, [
            {"text": "q", "qtype": "q_content", "target_url": c.pages[0].url},
            {"text": "q", "qtype": "q_content", "target_url": "https://nowhere.example/x"},
        ])
        with pytest.raises(QueryFileError, match="not in this library"):
            load_query_file(conn, f)

    @pytest.mark.parametrize("bad", [
        {"text": "q", "qtype": "q_typo", "target_url": "U"},
        {"text": "", "qtype": "q_content", "target_url": "U"},
        {"qtype": "q_content", "target_url": "U"},
    ])
    def test_a_malformed_record_is_refused(self, tmp_path, bad):
        conn, c = self._library()
        bad = {**bad, "target_url": c.pages[0].url}
        with pytest.raises(QueryFileError):
            load_query_file(conn, self._write(tmp_path, [bad]))

    def test_unparseable_json_names_the_line(self, tmp_path):
        conn, _ = self._library()
        p = tmp_path / "q.jsonl"
        p.write_text('{"text": "ok"}\nnot json at all\n', encoding="utf-8")
        with pytest.raises(QueryFileError, match=":2:"):
            load_query_file(conn, p)

    def test_blank_lines_and_comments_are_skipped(self, tmp_path):
        conn, c = self._library()
        p = tmp_path / "q.jsonl"
        p.write_text(
            "// generated 2026-08-02\n\n"
            + json.dumps({"text": "q", "qtype": "q_vague",
                          "target_url": c.pages[0].url}) + "\n\n",
            encoding="utf-8")
        assert len(load_query_file(conn, p).queries) == 1

    def test_an_empty_file_is_refused(self, tmp_path):
        conn, _ = self._library()
        p = tmp_path / "q.jsonl"
        p.write_text("\n\n", encoding="utf-8")
        with pytest.raises(QueryFileError, match="no queries"):
            load_query_file(conn, p)

    def test_counts_report_the_library_size_not_zero_pages(self, tmp_path):
        conn, c = self._library()
        f = self._write(tmp_path, [
            {"text": "q", "qtype": "q_vague", "target_url": c.pages[0].url},
        ])
        counts = load_query_file(conn, f).counts
        assert counts["pages"] == 12
        assert counts["q_vague"] == 1

    async def test_no_build_without_a_query_file_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="--queries"):
            await run_eval(build=False, db=tmp_path / "x.db")

    async def test_an_existing_library_can_be_measured_from_a_file(self, tmp_path):
        """The end-to-end shape of the real-corpus run, on a mock library."""
        st = get_settings(use_mock_provider=True, data_dir=str(tmp_path))
        db = tmp_path / "lib.db"
        conn = open_db(db)
        c = generate_corpus(size=24, seed=6)
        load_corpus(conn, c, settings=st)
        from facetmark.providers import get_provider
        from facetmark.service import index_all
        prov = get_provider(st)
        await index_all(conn, provider=prov, settings=st, fetch=False)
        await prov.aclose()
        conn.commit()
        conn.close()

        f = self._write(tmp_path, [
            {"text": q.text, "qtype": q.qtype, "target_url": c.pages[q.target].url}
            for q in c.queries[:12]
        ])
        rep = await run_eval(db=db, build=False, queries_path=f, bootstrap=50)
        assert rep["corpus"]["pages"] == 24
        assert rep["rungs"][0]["overall"]["n"] == 12
        assert rep["queries_from"] == str(f)

    async def test_the_report_carries_the_per_query_judgements(self, tmp_path):
        """Aggregates alone cannot be re-cut by a slice the author missed.

        The episodic reading in particular has to be split by how the time
        phrase was written, which is a label the query file supplies in
        ``note`` and no summary column knows about.
        """
        st = get_settings(use_mock_provider=True, data_dir=str(tmp_path))
        db = tmp_path / "lib.db"
        conn = open_db(db)
        c = generate_corpus(size=24, seed=6)
        load_corpus(conn, c, settings=st)
        from facetmark.providers import get_provider
        from facetmark.service import index_all
        prov = get_provider(st)
        await index_all(conn, provider=prov, settings=st, fetch=False)
        await prov.aclose()
        conn.commit()
        conn.close()

        f = self._write(tmp_path, [
            {"text": q.text, "qtype": q.qtype, "target_url": c.pages[q.target].url,
             "note": "subtype-x"}
            for q in c.queries[:8]
        ])
        rep = await run_eval(db=db, build=False, queries_path=f, bootstrap=20,
                             ablation=True)

        assert [q["note"] for q in rep["queries"]] == ["subtype-x"] * 8
        assert set(rep["outcomes"]) == set(RUNGS)
        for key in RUNGS:
            outs = rep["outcomes"][key]
            # One judgement per query, in query order, so a slice of the query
            # list indexes the same rows of every rung.
            assert len(outs) == len(rep["queries"])
            summary = next(r for r in rep["rungs"] if r["config"] == key)["overall"]
            hits = sum(1 for o in outs if 0 < o["rank"] <= 5)
            assert round(hits / len(outs), 4) == summary["recall@5"]


class TestChoosingWhichRungsToRun:
    """A candidate switch is only worth measuring if it can be named.

    Every exploratory rung exists to be judged on a query set it did not help
    produce. Until the bench could be pointed at one, "judge it" meant editing
    ``RUNGS`` and remembering to put it back.
    """

    def test_the_default_is_still_the_pre_registered_ladder(self):
        assert resolve_rungs(None, ablation=True) == ["A", "B", "C", "D", "E"]
        assert resolve_rungs([], ablation=True) == list(RUNGS)
        assert resolve_rungs(None, ablation=False) == ["full"]

    def test_named_rungs_keep_the_order_they_were_given(self):
        # deltas compare adjacent entries, so order is the hypothesis direction.
        assert resolve_rungs(["C", "C_notri"], ablation=False) == ["C", "C_notri"]
        assert resolve_rungs(["C_notri", "C"], ablation=True) == ["C_notri", "C"]

    def test_whitespace_is_tolerated_because_the_flag_is_comma_separated(self):
        assert resolve_rungs([" C ", "", "  D_gated"], ablation=False) == ["C", "D_gated"]

    def test_an_unknown_rung_fails_before_the_replay_starts(self):
        with pytest.raises(ValueError, match="unknown rung"):
            resolve_rungs(["C", "C_notrigram"], ablation=False)

    def test_the_error_lists_what_is_available(self):
        with pytest.raises(ValueError) as e:
            resolve_rungs(["nope"], ablation=False)
        assert "A_gatedctx" in str(e.value) and "full" in str(e.value)

    def test_a_rung_cannot_be_compared_against_itself(self):
        with pytest.raises(ValueError, match="named twice"):
            resolve_rungs(["C", "D", "C"], ablation=False)

    def test_naming_only_blanks_is_not_the_same_as_naming_nothing(self):
        with pytest.raises(ValueError, match="named nothing"):
            resolve_rungs(["  ", ""], ablation=True)

    async def test_a_custom_ladder_does_not_inherit_the_pre_registered_bar(self):
        rep = await run_eval(size=24, bootstrap=50, rungs=["A", "C_nolex"])
        assert rep["rungs_run"] == ["A", "C_nolex"]
        assert [r["config"] for r in rep["rungs"]] == ["A", "C_nolex"]
        assert len(rep["deltas"]) == 1
        assert "meets_bar" not in rep["end_to_end"]
        assert "pre-registered" in rep["end_to_end"]["bar_not_applicable"]

    async def test_the_ae_ladder_still_reports_the_bar(self):
        rep = await run_eval(size=24, bootstrap=50, rungs=list(RUNGS))
        assert isinstance(rep["end_to_end"]["meets_bar"], bool)
        assert "bar_not_applicable" not in rep["end_to_end"]
