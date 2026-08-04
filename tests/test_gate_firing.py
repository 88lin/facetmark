"""Tests for the gate-firing diagnostic.

The measurement it reports is a rate over query types, so what matters is that
it counts the right denominator (comment lines are not queries), that it reads
the clock from the library instead of the wall (a "last week" query changes
class overnight otherwise), and that it keeps the false positives it finds --
those examples are the whole point of running it.
"""
from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "gate_firing.py"


def _load():
    spec = importlib.util.spec_from_file_location("gate_firing_under_test", _PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


GF = _load()


class TestReadingTheQueryFile:
    def test_header_comments_are_not_queries(self, tmp_path):
        p = tmp_path / "q.jsonl"
        p.write_text(
            '// provenance\n'
            '{"text": "a", "qtype": "q_content"}\n'
            '\n'
            '// another note\n'
            '{"text": "b", "qtype": "q_vague"}\n',
            encoding="utf-8",
        )
        rows = GF.load_queries(p)
        assert [r["text"] for r in rows] == ["a", "b"]


class TestTheClock:
    def test_the_library_timestamp_is_preferred_over_the_wall(self, tmp_path):
        db = tmp_path / "lib.db"
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO meta VALUES ('created_at', '1785649110')")
        conn.commit()
        conn.close()
        assert GF.index_clock(str(db)) == 1785649110

    def test_a_library_without_the_key_says_so_instead_of_guessing(self, tmp_path):
        db = tmp_path / "empty.db"
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        conn.commit()
        conn.close()
        assert GF.index_clock(str(db)) is None

    def test_a_library_without_a_meta_table_does_not_raise(self, tmp_path):
        db = tmp_path / "bare.db"
        sqlite3.connect(db).close()
        assert GF.index_clock(str(db)) is None


class TestTheReport:
    def _run(self, tmp_path, rows, monkeypatch):
        p = tmp_path / "q.jsonl"
        p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                     encoding="utf-8")
        out = tmp_path / "out.json"
        monkeypatch.setattr(
            "sys.argv",
            ["gate_firing.py", "--queries", str(p), "--now", "1785649110",
             "--out", str(out)],
        )
        GF.main()
        return json.loads(out.read_text(encoding="utf-8"))

    def test_a_year_in_a_content_query_is_reported_as_a_false_positive(
        self, tmp_path, monkeypatch
    ):
        rep = self._run(
            tmp_path,
            [
                {"text": "reading for fun declined since 2012", "qtype": "q_content"},
                {"text": "vector database comparison", "qtype": "q_content"},
                {"text": "the thing I saved in 2024", "qtype": "q_episodic"},
            ],
            monkeypatch,
        )
        c = rep["by_type"]["q_content"]
        assert (c["n"], c["fired"]) == (2, 1)
        assert c["share"] == 0.5
        # the example is kept verbatim, with the rule that fired
        assert any("2012" in e for e in rep["false_positive_examples"]["q_content"])
        assert rep["by_type"]["q_episodic"]["fired"] == 1

    def test_episodic_queries_are_not_listed_as_false_positives(
        self, tmp_path, monkeypatch
    ):
        rep = self._run(
            tmp_path,
            [{"text": "that page from last week", "qtype": "q_episodic"}],
            monkeypatch,
        )
        assert "q_episodic" not in rep["false_positive_examples"]

    def test_a_type_that_never_fires_reports_zero_not_a_missing_key(
        self, tmp_path, monkeypatch
    ):
        rep = self._run(
            tmp_path,
            [{"text": "some fuzzy thing about rendering", "qtype": "q_vague"}],
            monkeypatch,
        )
        v = rep["by_type"]["q_vague"]
        assert (v["fired"], v["share"], v["rules"]) == (0, 0.0, {})
        assert v["median_multiplier"] is None

    def test_the_clock_is_recorded_in_the_output(self, tmp_path, monkeypatch):
        rep = self._run(tmp_path, [{"text": "x", "qtype": "q_content"}], monkeypatch)
        assert rep["clock"] == 1785649110
