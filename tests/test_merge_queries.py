"""Tests for the chunk merger's de-duplication rule.

``scripts/`` is not a package, so the module is loaded by path, the same way
``test_gen_queries.py`` does it.

The rule decides how many times a page gets to influence a recall number, so it
is worth more than a length assertion: what is checked here is which row
survives, which one is dropped, and whether the reason is reported.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "corpus" / "merge_queries.py"


def _load():
    spec = importlib.util.spec_from_file_location("merge_queries_under_test", _PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


mq = _load()


def q(text: str, qtype: str = "q_content", url: str = "https://a/1") -> dict:
    return {"text": text, "qtype": qtype, "target_url": url}


class TestWhatCountsAsTheSameQuery:
    def test_one_page_may_carry_one_query_per_type(self):
        """The strata read of D-C is grouped by qtype, so this is the design."""
        rows = [q("what", "q_content"), q("that thing", "q_vague"),
                q("last week", "q_episodic")]
        kept, dropped = mq.merge([("a.jsonl", rows)])
        assert len(kept) == 3 and not dropped

    def test_two_chunks_drawing_the_same_page_and_type_is_one_draw(self):
        kept, dropped = mq.merge([
            ("a.jsonl", [q("first ask")]),
            ("b.jsonl", [q("second ask")]),
        ])
        assert [r["text"] for r in kept] == ["first ask"]
        assert sum(dropped.values()) == 1
        assert "a.jsonl" in next(iter(dropped))

    def test_the_same_page_in_two_chunks_can_still_add_a_different_type(self):
        kept, _ = mq.merge([
            ("a.jsonl", [q("first ask", "q_content")]),
            ("b.jsonl", [q("when was it", "q_episodic")]),
        ])
        assert len(kept) == 2

    def test_identical_text_on_two_targets_leaves_no_winnable_answer(self):
        kept, dropped = mq.merge([
            ("a.jsonl", [q("rust async runtime", url="https://a/1")]),
            ("b.jsonl", [q("rust async runtime", url="https://b/2")]),
        ])
        assert [r["target_url"] for r in kept] == ["https://a/1"]
        assert sum(dropped.values()) == 1

    def test_whitespace_does_not_make_two_queries_different(self):
        kept, _ = mq.merge([
            ("a.jsonl", [q("rust  async\truntime", url="https://a/1")]),
            ("b.jsonl", [q("rust async runtime", url="https://b/2")]),
        ])
        assert len(kept) == 1

    def test_an_empty_query_is_dropped_rather_than_carried(self):
        kept, dropped = mq.merge([("a.jsonl", [q("   ")])])
        assert not kept and dropped["empty text"] == 1

    def test_every_row_records_which_chunk_it_came_from(self):
        kept, _ = mq.merge([("a.jsonl", [q("x")]), ("b.jsonl", [q("y", url="https://b/2")])])
        assert [r["chunk"] for r in kept] == ["a.jsonl", "b.jsonl"]


class TestTheFileItReads:
    def test_provenance_headers_are_not_records(self, tmp_path: Path):
        p = tmp_path / "c.jsonl"
        p.write_text("// seed=1\n// n=64\n" + json.dumps(q("x"), ensure_ascii=False) + "\n",
                     encoding="utf-8")
        rows, header = mq.read_chunk(p)
        assert len(rows) == 1 and len(header) == 2

    def test_blank_lines_are_skipped(self, tmp_path: Path):
        p = tmp_path / "c.jsonl"
        p.write_text("\n" + json.dumps(q("x"), ensure_ascii=False) + "\n\n", encoding="utf-8")
        rows, _ = mq.read_chunk(p)
        assert len(rows) == 1
