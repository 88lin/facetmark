"""The disposition table is a conjunction, so test all four corners of it.

The run this ships with lands on the corner that is easiest to misread: the
remedy still pays for itself (+1.79pp, lower bound above zero) and is still
imprecise (-10.52pp, interval nowhere near zero). One comfortable number out of
two is not a pass, and the protocol wrote no branch in which an imprecise gate
keeps the default.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "gate_v2_disposition.py"


def _load():
    spec = importlib.util.spec_from_file_location("gate_v2_disposition_under_test", _PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gvd = _load()


# ---------------------------------------------------------------------------
# the four corners
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("a_ok,b_ok,action", [
    (True, True, "ship_gate_v2"),
    (True, False, "revert_to_1_1_0_ungated"),
    (False, True, "revert_to_1_1_0_ungated"),
    (False, False, "revert_to_1_1_0_ungated"),
])
def test_only_both_bars_ship_the_remedy(a_ok, b_ok, action):
    assert gvd.disposition(a_ok, b_ok)["action"] == action


def test_the_three_reverts_do_not_share_one_reason():
    """Same action, different findings. Collapsing them would hide whether the
    remedy failed on precision, on benefit, or on both."""
    whys = {gvd.disposition(a, b)["why"]
            for a, b in ((True, False), (False, True), (False, False))}
    assert len(whys) == 3


def test_the_shipping_branch_names_the_gated_config():
    assert "gated" in gvd.disposition(True, True)["default_config"]
    assert "context" not in gvd.disposition(False, True)["default_config"]


# ---------------------------------------------------------------------------
# the bar predicates
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lo,hi,passed", [
    (-13.85, -7.48, False),     # this run: cost intact
    (-5.26, 5.26, True),        # straddles zero: cost not detectable
    (0.81, 2.92, True),         # above zero: the gate helps on the probes too
    (-0.01, -0.001, False),     # tiny but still entirely negative
    (0.0, 4.0, True),           # lower bound exactly zero counts as straddling
])
def test_gate_a_asks_whether_the_cost_could_be_zero(lo, hi, passed):
    res = gvd.gate_a({"ci95_pp": [lo, hi], "recall@5_pp": (lo + hi) / 2})
    assert res["passed"] is passed


@pytest.mark.parametrize("lo,passed", [
    (0.81, True), (0.001, True), (0.0, False), (-1.0, False),
])
def test_gate_b_asks_whether_the_benefit_is_strictly_positive(lo, passed):
    res = gvd.gate_b({"ci95_pp": [lo, lo + 2.0], "recall@5_pp": lo + 1.0})
    assert res["passed"] is passed


def test_the_two_bars_are_not_the_same_predicate():
    """A straddling interval passes (a) and fails (b). If one predicate were
    reused for both, this run would have reported two passes."""
    straddle = {"ci95_pp": [-5.0, 5.0], "recall@5_pp": 0.0}
    assert gvd.gate_a(straddle)["passed"] is True
    assert gvd.gate_b(straddle)["passed"] is False


# ---------------------------------------------------------------------------
# end to end
# ---------------------------------------------------------------------------


def _report(path: Path, ranks: dict[str, list[int]]) -> None:
    n = len(next(iter(ranks.values())))
    path.write_text(json.dumps({
        "queries": [{"i": i, "qtype": "q_content", "target_id": i, "text": f"q{i}"}
                    for i in range(n)],
        "outcomes": {k: [{"rank": r, "expanded": False, "ms": 1.0} for r in v]
                     for k, v in ranks.items()},
    }), encoding="utf-8")


def _run(tmp_path, probe_ranks, holdout_ranks):
    p, h, o = tmp_path / "p.json", tmp_path / "h.json", tmp_path / "d.json"
    _report(p, probe_ranks)
    _report(h, holdout_ranks)
    import sys
    old = sys.argv
    sys.argv = ["gate_v2_disposition.py", "--probe", str(p), "--holdout", str(h),
                "--out", str(o), "--bootstrap", "400"]
    try:
        gvd.main()
    finally:
        sys.argv = old
    return json.loads(o.read_text(encoding="utf-8"))


def test_end_to_end_reverts_when_only_the_benefit_bar_clears(tmp_path):
    """The shape of the real run, in miniature."""
    res = _run(
        tmp_path,
        # probe set: v2 still costs 6 of 20 their top-5 slot
        {"A": [1] * 20, "A_gatedctx": [99] * 20, "A_gatedctx_v2": [1] * 14 + [99] * 6},
        # holdout: v2 wins 5 of 40 and loses none
        {"A": [1] * 35 + [99] * 5, "A_gatedctx": [1] * 40, "A_gatedctx_v2": [1] * 40},
    )
    assert res["gate_a"]["passed"] is False
    assert res["gate_b"]["passed"] is True
    assert res["disposition"]["action"] == "revert_to_1_1_0_ungated"
    assert res["disposition"]["default_config"] == "content + graph + decay"
    # v1 is carried on both sets, so the file answers "worse than what?"
    assert res["v1_for_comparison"]["probe"]["recall@5_pp"] == -100.0
    assert set(res["v1_for_comparison"]) == {"probe", "holdout"}


def test_a_report_without_the_v2_rung_is_fatal_rather_than_silent(tmp_path):
    with pytest.raises(SystemExit, match="A_gatedctx_v2 was not run"):
        _run(tmp_path, {"A": [1, 1], "A_gatedctx": [1, 1]},
             {"A": [1, 1], "A_gatedctx_v2": [1, 1]})


def test_v1_is_omitted_rather_than_faked_when_a_report_lacks_it(tmp_path):
    res = _run(tmp_path, {"A": [1] * 8, "A_gatedctx_v2": [1] * 8},
               {"A": [1] * 8, "A_gatedctx": [1] * 8, "A_gatedctx_v2": [1] * 8})
    assert set(res["v1_for_comparison"]) == {"holdout"}
