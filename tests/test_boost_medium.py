"""Tests for the medium-sizing script's newly parameterised parts.

``scripts/`` is not a package, so the module is loaded by path, the same way
``test_gen_queries.py`` does it.

The replay loop needs an indexed library and (for the vector media) an
embedding model, so it is not unit-tested here. What is tested is everything
that decides *what gets measured*: which rung a ``--media`` name resolves to,
what happens when a vector medium is asked for without a vector, where the
clock comes from, and whether the vector cache actually spares the model.
"""
from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

from facetmark.config import Settings

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "boost_medium.py"


def _load():
    spec = importlib.util.spec_from_file_location("boost_medium_under_test", _PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def bm():
    return _load()


class TestWhichRungAMediumNameMeansThe:
    def test_ladder_rungs_resolve(self, bm):
        assert sorted(bm.rung("A").facets) == ["content"]
        assert sorted(bm.rung("C").facets) == ["content", "intent", "lex_seg", "lex_tri"]

    def test_exploratory_rungs_resolve(self, bm):
        assert sorted(bm.rung("seg_only").facets) == ["lex_seg"]
        assert sorted(bm.rung("C_nolex").facets) == ["content", "intent"]

    def test_c_and_d_are_the_same_medium(self, bm):
        # The whole reason A-vs-C stands in for A-vs-D: identical facet sets,
        # therefore identical fusion arithmetic.
        assert bm.rung("C").facets == bm.rung("D").facets
        assert bm.rung("C").facet_weights == bm.rung("D").facet_weights

    def test_an_unknown_name_names_the_known_ones(self, bm):
        with pytest.raises(SystemExit) as e:
            bm.rung("C_nolexx")
        assert "C_nolex" in str(e.value)

    def test_the_default_media_are_the_model_free_ones(self, bm):
        assert bm.MEDIA == ("seg_only", "lex_only")
        for name in bm.MEDIA:
            assert not (bm.rung(name).facets & bm.VECTOR_FACETS)


class TestAVectorMediumWillNotQuietlyRunWithoutVectors:
    def test_it_refuses_rather_than_reporting_a_narrower_medium(self, bm):
        conn = sqlite3.connect(":memory:")
        with pytest.raises(SystemExit) as e:
            bm.fused_scores(conn, "anything", "A", Settings(use_mock_provider=True))
        assert "query vector" in str(e.value)
        conn.close()

    def test_a_lexical_medium_does_not_need_one(self, bm, tmp_path):
        # No vec argument, no failure: the rung has no vector facet to feed.
        db = tmp_path / "empty.db"
        conn = sqlite3.connect(db)
        conn.executescript(
            "CREATE VIRTUAL TABLE fts_seg USING fts5(title, body);"
            "CREATE VIRTUAL TABLE fts_tri USING fts5(title, body);"
        )
        conn.row_factory = sqlite3.Row
        assert bm.fused_scores(conn, "anything", "seg_only",
                               Settings(use_mock_provider=True)) == []
        conn.close()


class TestTheClockIsAPropertyOfTheLibraryNotOfToday:
    def _db(self, path: Path, created_at: str | None) -> str:
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        if created_at is not None:
            conn.execute("INSERT INTO meta VALUES ('created_at', ?)", (created_at,))
        conn.commit()
        conn.close()
        return str(path)

    def test_it_comes_from_the_index(self, bm, tmp_path):
        assert bm.index_clock(self._db(tmp_path / "a.db", "1785649110")) == 1785649110

    def test_a_library_that_does_not_say_leaves_it_unpinned(self, bm, tmp_path):
        # None, not 0 -- 0 would silently resolve every relative window against
        # 1970 and report that nothing was ever recent.
        assert bm.index_clock(self._db(tmp_path / "b.db", None)) is None


class TestTheVectorCacheSparesTheModel:
    def test_a_complete_cache_needs_no_provider(self, bm, tmp_path, monkeypatch):
        def explode(_settings):
            raise AssertionError("a complete cache must not reach for a model")

        monkeypatch.setattr(bm, "get_provider", explode)
        cache = tmp_path / "qvec.jsonl"
        cache.write_text(
            json.dumps({"text": "hi", "vec": [0.1, 0.2]}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        got = bm.query_vectors([{"text": "hi"}, {"text": "hi"}],
                               Settings(use_mock_provider=True), cache)
        assert got == {"hi": [0.1, 0.2]}

    def test_only_the_missing_texts_are_embedded_and_the_cache_is_rewritten(
        self, bm, tmp_path, monkeypatch
    ):
        asked: list[list[str]] = []

        class _Prov:
            async def embed(self, texts):
                asked.append(list(texts))
                return [[float(len(t))] for t in texts]

            async def aclose(self):
                return None

        monkeypatch.setattr(bm, "get_provider", lambda _s: _Prov())
        cache = tmp_path / "qvec.jsonl"
        cache.write_text(
            json.dumps({"text": "old", "vec": [9.0]}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        queries = [{"text": "old"}, {"text": "newer"}, {"text": "old"}]
        got = bm.query_vectors(queries, Settings(use_mock_provider=True), cache)

        assert asked == [["newer"]]
        assert got == {"old": [9.0], "newer": [5.0]}
        rows = [json.loads(x) for x in cache.read_text(encoding="utf-8").splitlines()]
        assert [r["text"] for r in rows] == ["old", "newer"]

    def test_no_cache_path_still_works(self, bm, monkeypatch):
        class _Prov:
            async def embed(self, texts):
                return [[1.0] for _ in texts]

            async def aclose(self):
                return None

        monkeypatch.setattr(bm, "get_provider", lambda _s: _Prov())
        got = bm.query_vectors([{"text": "x"}], Settings(use_mock_provider=True), None)
        assert got == {"x": [1.0]}


class TestTheClosedFormTheEmpiricalNumbersAreCheckedAgainst:
    def test_a_single_facet_range_is_rank_and_nothing_else(self, bm):
        row = next(r for r in bm.dynamic_range(60, 50, {"content": 1.0})["per_config"]
                   if r["config"] == "A")
        assert row["dynamic_range"] == round(110 / 61, 3) == 1.803

    def test_one_sixty_reaches_rank_one_from_rank_thirty_seven(self, bm):
        d = bm.single_facet_displacement(60, 50, 1.60)
        assert d["deepest_rank_that_reaches_first"] == 37
        assert d["lands_from"]["20"] == 1

    def test_displacement_counts_only_the_probed_document(self, bm):
        scores = [(1, 0.020), (2, 0.017), (3, 0.010)]
        # 0.010 * 1.6 = 0.016 still trails both, so the probed document stays
        # third -- nothing else moved, which is the point of boosting one.
        assert bm.displacement(scores, 3, 1.60) == 3
        assert bm.displacement(scores, 3, 2.10) == 1
        assert bm.displacement(scores, 9, 1.60) is None
