"""The v2 context gate: a bare year stops meaning "when I saved it".

The remedy was written down in ``docs/gate-precision-protocol.md`` §6 before
the probe set existed, so these tests are about whether the code implements
*that* rule -- not a rule chosen after seeing -18.83pp.

The one thing worth restating: v2 narrows ``time:absolute_year`` and nothing
else. ``time:relative`` costs just as much on the probe set (-22.84pp over 162
queries) and is deliberately left alone here, because the pre-registered remedy
said years. Fixing what the protocol did not name would be the same mistake
1.2.0 made, in the other direction.
"""

from __future__ import annotations

import pytest

from facetmark.search.pipeline import ALL_CONFIGS, FULL
from facetmark.search.understand import (
    _SAVE_ACTION,
    _VAGUE_EPISODIC,
    classify,
    episodic_beyond_a_bare_year,
)

NOW = 1785649110  # the indexed library's clock, 2026-08-02

V1 = ALL_CONFIGS["A_gatedctx"]
V2 = ALL_CONFIGS["A_gatedctx_v2"]


def _gates(query: str) -> tuple[bool, bool]:
    u = classify(query, now_ts=NOW)
    return V1.wants_context(u), V2.wants_context(u)


# ---------------------------------------------------------------------------
# the one behaviour that changes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("query", [
    "2015年空间站咖啡机为什么那么贵",
    "1994四大导演聚餐敲定四部动画",
    "2012 sweet breakfast import struggled against savory traditions",
    "2025特斯拉财报电话会宣布停产model s x",
])
def test_a_bare_year_opened_the_v1_gate_and_no_longer_opens_v2(query):
    """These are real lines from the probe set. Every one of them is a query
    about a *topic* that has a year in it."""
    v1, v2 = _gates(query)
    assert v1 is True
    assert v2 is False


@pytest.mark.parametrize("query", [
    "2015年我存的那篇空间站咖啡机",          # save vocabulary, Chinese
    "上次那个2012年的早餐文章",              # 上次
    "bookmarked in 2019 that essay on savory breakfasts",
    "当时存的2015空间站咖啡机",              # vague marker *and* save word
    "那阵子看的1994动画会议",                # vague marker alone
])
def test_a_year_with_evidence_of_filing_still_opens_both_gates(query):
    v1, v2 = _gates(query)
    assert v1 is True
    assert v2 is True


# ---------------------------------------------------------------------------
# the three signals the protocol said not to touch
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("query", [
    "最近的固态电池能量密度进展",             # time:relative
    "recently overhyped tech fads that flopped",
    "去年adsense收益计算器",
    "三个月前存的教程",                     # time:n_ago
    "那阵子在看的东西",                     # episodic_marker, no date at all
])
def test_relative_n_ago_and_vague_markers_are_untouched(query):
    v1, v2 = _gates(query)
    assert v1 is True
    assert v2 is True


@pytest.mark.parametrize("query", [
    "收藏夹里的postgres教程",                # save vocabulary, no time expression
    "c10k问题怎么用回调解决的",
    "",
])
def test_a_query_with_no_time_signal_opens_neither(query):
    assert _gates(query) == (False, False)


def test_save_vocabulary_alone_does_not_make_a_query_episodic():
    """_SAVE_ACTION is a *qualifier* for a year, not a label of its own. If it
    labelled queries episodic the gate would widen, which is the opposite of
    what the remedy is for."""
    u = classify("收藏夹里的postgres教程", now_ts=NOW)
    assert u.is_episodic is False
    assert episodic_beyond_a_bare_year(u) is False


# ---------------------------------------------------------------------------
# wiring
# ---------------------------------------------------------------------------


def test_version_1_is_still_the_default_until_v2_passes_both_tests():
    """The protocol requires v2 to clear two frozen bars before it ships. Until
    a run says it did, the shipped default stays what 1.2.0 released."""
    assert FULL.context is False, "1.3.0 reverted the default; there is no gate to version"
    assert V1.context_gate_version == 1
    assert V2.context_gate_version == 2


def test_the_version_travels_in_the_config_dict():
    """Every eval report records the config it ran; a silent gate swap would be
    unattributable otherwise."""
    assert V2.as_dict()["context_gate_version"] == 2
    assert V1.as_dict()["context_gate_version"] == 1


def test_ungated_context_ignores_the_version():
    """context_gate=False means "always on"; the version must not resurrect a
    gate for the rung whose whole purpose is not having one."""
    from dataclasses import replace

    ctx_only = replace(V2, name="A_ctx_v2", context_gate=False)
    u = classify("2015年空间站咖啡机", now_ts=NOW)
    assert ctx_only.wants_context(u) is True


def test_no_frozen_probe_contains_the_vocabulary_v2_looks_for():
    """The probe set was frozen before v2 existed, so it is worth checking
    rather than assuming: a probe containing save vocabulary would open the v2
    gate too, and the remedy would be measured against a contaminated set.

    Checked against the file, not against the generator's rejection list --
    ``_SAVE_ACTION`` gained ``存了`` when it moved into the product, and a
    superset assertion would have failed on a word that turns out to appear in
    none of the 361 lines anyway."""
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "eval" / "queries" / "gate-precision.jsonl"
    if not path.exists():                      # pragma: no cover - sdist without eval data
        pytest.skip("probe set not present")
    words = {*_SAVE_ACTION, *_VAGUE_EPISODIC}
    hits = [
        (row["text"], w)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("//")
        for row in [json.loads(line)]
        for w in words
        if w in row["text"].lower()
    ]
    assert hits == []
