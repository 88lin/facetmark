"""Tests for the gate-precision verdict script.

The script's job is to apply a pre-registered rule without editing it, so the
tests are mostly about the rule's edges -- including the one the protocol's
table does not cover, where a real cost sits above the threshold that triggers
a remedy.

The other half is the self-check. Two rungs that differ only by a gate cannot
disagree on a query the gate ignored, so a non-zero delta there means the
measurement is measuring something else. The script is required to void its own
verdict in that case, and that is worth a test precisely because it is the
branch nobody expects to hit.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "gate_precision.py"


def _load():
    spec = importlib.util.spec_from_file_location("gate_precision_under_test", _PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


gpv = _load()


# ---------------------------------------------------------------------------
# the verdict table, including the row it is missing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("point", "lo", "hi", "label", "disposition"), [
    # unqualified: at or past the threshold, interval clear of zero
    (-9.94, -14.62, -5.26, "gate_precision_unqualified", True),
    (-2.00, -3.10, -0.40, "gate_precision_unqualified", True),
    # no cost found
    (-1.20, -3.40, 1.10, "no_cost_detected", False),
    (0.00, -1.00, 1.00, "no_cost_detected", False),
    # beneficial
    (3.09, 1.79, 4.55, "beneficial", False),
    # the gap: a credible cost that is too small to trigger the remedy
    (-1.20, -2.30, -0.10, "cost_below_threshold", False),
    # past the point threshold but the interval still touches zero
    (-2.50, -5.10, 0.30, "no_cost_detected", False),
])
def test_verdict_table(point, lo, hi, label, disposition):
    v = gpv.verdict_for(point, lo, hi)
    assert v["label"] == label
    assert v["triggers_disposition"] is disposition


def test_unqualified_is_the_only_verdict_that_triggers_a_remedy():
    """``gate_v2`` is pre-registered as the response to one verdict, not to
    "the number looked bad"."""
    triggered = [lab for lab in ("gate_precision_unqualified", "no_cost_detected",
                                 "beneficial", "cost_below_threshold")
                 if gpv.verdict_for(*{
                     "gate_precision_unqualified": (-5.0, -8.0, -2.0),
                     "no_cost_detected": (-1.0, -3.0, 1.0),
                     "beneficial": (3.0, 1.0, 5.0),
                     "cost_below_threshold": (-1.0, -2.0, -0.5),
                 }[lab])["triggers_disposition"]]
    assert triggered == ["gate_precision_unqualified"]


def test_detectable_pp_matches_the_w2w3_number():
    """Same formula as ``switch_verdicts.py``: 19 discordant over 616 queries was
    reported as 1.98pp, and the two runs have to stay comparable."""
    assert gpv.detectable_pp(19, 616) == 1.98
    assert gpv.detectable_pp(0, 616) != gpv.detectable_pp(0, 616)  # nan


# ---------------------------------------------------------------------------
# end to end on a synthetic report
# ---------------------------------------------------------------------------


def _report(ranks_a, ranks_b, texts):
    return {
        "queries": [{"i": i, "qtype": "q_content", "target_id": i, "note": "p_year",
                     "text": t} for i, t in enumerate(texts)],
        "outcomes": {
            "A": [{"rank": r, "expanded": False, "ms": 1.0} for r in ranks_a],
            "A_gatedctx": [{"rank": r, "expanded": False, "ms": 1.0} for r in ranks_b],
        },
    }


def _probe_lines(texts, subtypes=None, distances=None):
    out = []
    for i, t in enumerate(texts):
        out.append({"text": t, "qtype": "q_content", "target_url": f"https://e.com/{i}",
                    "note": "p_year", "subtype": (subtypes or ["p_year"] * len(texts))[i],
                    "time_token": "2011", "save_year": 2026, "content_year": 2011,
                    "year_distance": (distances or [15] * len(texts))[i]})
    return out


def _run(tmp_path, ranks_a, ranks_b, texts, **kw):
    rep = tmp_path / "eval.json"
    qs = tmp_path / "probe.jsonl"
    out = tmp_path / "verdict.json"
    rep.write_text(json.dumps(_report(ranks_a, ranks_b, texts)), encoding="utf-8")
    qs.write_text("// header\n" + "\n".join(
        json.dumps(r, ensure_ascii=False) for r in _probe_lines(texts, **kw)),
        encoding="utf-8")
    argv = ["--report", str(rep), "--queries", str(qs), "--out", str(out),
            "--now", "1785649110", "--bootstrap", "300"]
    import sys
    old = sys.argv
    sys.argv = ["gate_precision.py", *argv]
    try:
        gpv.main()
    finally:
        sys.argv = old
    return json.loads(out.read_text(encoding="utf-8"))


_FIRES = "1999年c10k问题怎么用回调解决的"       # time:absolute_year
_QUIET = "c10k问题怎么用回调解决的"              # no time expression at all


def test_end_to_end_prices_a_cost_and_passes_its_self_check(tmp_path):
    texts = [_FIRES] * 20 + [_QUIET] * 10
    # the gate costs eight of the firing queries their top-5 slot
    ranks_a = [1] * 20 + [1] * 10
    ranks_b = [1] * 12 + [99] * 8 + [1] * 10
    res = _run(tmp_path, ranks_a, ranks_b, texts)
    assert res["n"] == 30
    assert res["firing"]["overall"]["fired"] == 20
    assert res["secondary"]["not_fired_subset"]["recall@5_pp"] == 0.0
    assert res["self_check"]["state"] == "passed"
    assert res["self_check"]["passed"] is True
    assert res["primary"]["recall@5_pp"] == pytest.approx(-26.67, abs=0.01)
    assert res["primary"]["verdict"]["label"] == "gate_precision_unqualified"
    # the fired subset is the cleaner unit price: 8 of 20, not 8 of 30
    assert res["secondary"]["fired_subset"]["recall@5_pp"] == pytest.approx(-40.0)


def test_self_check_voids_the_verdict_when_a_quiet_query_moves(tmp_path):
    """The branch that says "do not believe this run"."""
    texts = [_FIRES] * 10 + [_QUIET] * 10
    ranks_a = [1] * 20
    ranks_b = [1] * 10 + [99] + [1] * 9      # a query the gate never saw changed
    res = _run(tmp_path, ranks_a, ranks_b, texts)
    assert res["self_check"]["passed"] is False
    assert res["primary"]["verdict"]["label"] == "void"
    assert res["primary"]["verdict"]["triggers_disposition"] is False


def test_an_all_firing_set_reports_the_self_check_as_vacuous_not_passed(tmp_path):
    """The expected shape of an adversarial probe set. "Passed" on an empty
    subset is a claim about nothing; the run has to say so and point at the
    dataset where the check does have data."""
    res = _run(tmp_path, [1] * 10, [99] * 10, [_FIRES] * 10)
    assert res["self_check"]["state"] == "not_applicable"
    assert res["self_check"]["not_fired_n"] == 0
    assert "q_vague" in res["self_check"]["note"]
    assert res["primary"]["verdict"]["label"] != "void"


def test_subtypes_and_distance_buckets_are_reported_separately(tmp_path):
    """The protocol asks for the two subtypes apart, because a relative word can
    resolve to a window that happens to contain the save time and help."""
    texts = [_FIRES] * 10 + ["最近的固态电池能量密度进展"] * 10
    res = _run(tmp_path, [1] * 20, [1] * 10 + [99] * 10, texts,
               subtypes=["p_year"] * 10 + ["p_relative"] * 10,
               distances=[15] * 10 + [None] * 10)
    assert res["secondary"]["by_subtype"]["p_year"]["recall@5_pp"] == 0.0
    assert res["secondary"]["by_subtype"]["p_relative"]["recall@5_pp"] == -100.0
    assert res["secondary"]["by_subtype"]["p_relative"]["fired"] == 10
    # p_relative rows carry no year distance, so only p_year lands in a bucket
    assert res["secondary"]["by_year_distance"]["8y+"]["n"] == 10


def test_order_mismatch_between_probe_file_and_report_is_fatal(tmp_path):
    """Joining by position is only safe if position means the same thing in both
    files; an unnoticed reorder would silently mislabel every subtype."""
    rep = tmp_path / "eval.json"
    qs = tmp_path / "probe.jsonl"
    rep.write_text(json.dumps(_report([1, 1], [1, 1], [_FIRES, _QUIET])),
                   encoding="utf-8")
    qs.write_text("\n".join(json.dumps(r, ensure_ascii=False)
                            for r in _probe_lines([_QUIET, _FIRES])), encoding="utf-8")
    import sys
    old = sys.argv
    sys.argv = ["gate_precision.py", "--report", str(rep), "--queries", str(qs),
                "--out", str(tmp_path / "v.json"), "--now", "1785649110"]
    try:
        with pytest.raises(SystemExit, match="not in the same order"):
            gpv.main()
    finally:
        sys.argv = old
