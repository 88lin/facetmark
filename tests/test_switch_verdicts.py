"""Tests for the pre-registered switch verdict rule.

``scripts/`` is not a package, so the module is loaded by path, the same way
``test_gen_queries.py`` does it.

What is tested is the part that decides an outcome: Holm's step-down (including
the stop after the first failure to reject), the three conditions a switch has
to meet, the extra stratified condition the two gated rungs carry, and the
rebuild of per-query judgements from a report -- because a silent mismatch
there would compute a verdict on the wrong pairing.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "switch_verdicts.py"


def _load():
    spec = importlib.util.spec_from_file_location("switch_verdicts_under_test", _PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


sv = _load()


def report(ranks: dict[str, list[int]], qtypes: list[str] | None = None) -> dict:
    n = len(next(iter(ranks.values())))
    qtypes = qtypes or ["q_content"] * n
    return {
        "queries": [{"i": i, "qtype": qtypes[i], "target_id": i, "note": "", "text": f"q{i}"}
                    for i in range(n)],
        "outcomes": {k: [{"rank": r, "expanded": False, "ms": 1.0} for r in v]
                     for k, v in ranks.items()},
    }


class TestRebuildingJudgementsFromAReport:
    def test_ranks_become_outcomes_in_query_order(self):
        outs = sv.outcomes(report({"A": [1, 0, 7]}), "A")
        assert [o.rank for o in outs] == [1, 0, 7]
        assert [o.hit5 for o in outs] == [1, 0, 0]

    def test_a_missing_rung_says_what_the_report_does_have(self):
        with pytest.raises(SystemExit, match="C_notri"):
            sv.outcomes(report({"A": [1], "C_notri": [1]}), "C_max")

    def test_a_length_mismatch_is_refused_rather_than_zipped_short(self):
        rep = report({"A": [1, 2, 3]})
        rep["outcomes"]["A"] = rep["outcomes"]["A"][:2]
        with pytest.raises(SystemExit, match="2 outcomes for 3 queries"):
            sv.outcomes(rep, "A")


class TestHolmStepDown:
    def test_the_smallest_p_faces_the_strictest_threshold(self):
        out = sv.holm({"a": 0.001, "b": 0.02, "c": 0.30})
        assert out["a"]["holm_threshold"] == pytest.approx(0.05 / 3, abs=1e-5)
        assert out["b"]["holm_threshold"] == pytest.approx(0.05 / 2, abs=1e-5)
        assert out["c"]["holm_threshold"] == pytest.approx(0.05, abs=1e-5)
        assert out["a"]["rank_in_family"] == 1 and out["c"]["rank_in_family"] == 3

    def test_rejection_stops_at_the_smallest_p_that_fails(self):
        """c clears 0.05 on its own. Holm does not let it, because a did not clear 0.0167."""
        out = sv.holm({"a": 0.03, "b": 0.031, "c": 0.032})
        assert [out[k]["significant"] for k in "abc"] == [False, False, False]

    def test_a_clear_winner_does_not_drag_the_rest_in_with_it(self):
        out = sv.holm({"a": 0.0001, "b": 0.30})
        assert out["a"]["significant"] is True
        assert out["b"]["significant"] is False

    def test_six_switches_at_five_percent_each_is_the_thing_being_prevented(self):
        out = sv.holm(dict.fromkeys("abcdef", 0.04))
        assert not any(v["significant"] for v in out.values())


class TestTheVerdictRule:
    def _row(self, pp: float, ci: list[float]) -> dict:
        return {"recall@5_pp": pp, "ci95_pp": ci}

    def _sig(self, ok: bool) -> dict:
        return {"significant": ok, "p": 0.001, "holm_threshold": 0.0083}

    def test_all_three_conditions_together(self):
        v = sv.verdict(self._row(4.0, [1.2, 6.8]), self._sig(True), gated=False, strata=None)
        assert v["supported"] and not v["failed"]

    def test_a_positive_estimate_whose_interval_touches_zero_is_not_a_win(self):
        v = sv.verdict(self._row(4.0, [-0.4, 8.1]), self._sig(True), gated=False, strata=None)
        assert not v["supported"] and "CI95 includes zero" in v["failed"]

    def test_a_losing_interval_is_not_described_as_touching_zero(self):
        """CI[-9.58, -2.27] excludes zero -- on the losing side.

        The verdict was right and the sentence was wrong: the first real run
        printed "CI95 includes zero" under four intervals that lay entirely
        below it. The threshold is untouched; only the wording changed.
        """
        v = sv.verdict(self._row(-5.84, [-9.58, -2.27]), self._sig(True),
                       gated=False, strata=None)
        assert not v["supported"]
        assert "CI95 lies below zero" in v["failed"]
        assert "CI95 includes zero" not in v["failed"]

    def test_significance_alone_is_not_a_win(self):
        v = sv.verdict(self._row(-3.0, [-6.0, -0.5]), self._sig(True), gated=False, strata=None)
        assert not v["supported"]
        assert "point estimate is not positive" in v["failed"]

    def test_an_uncorrected_p_does_not_carry_the_verdict(self):
        v = sv.verdict(self._row(4.0, [1.2, 6.8]), self._sig(False), gated=False, strata=None)
        assert not v["supported"] and "Holm threshold" in v["failed"][0]


class TestTheGateCarriesAStratifiedRequirement:
    strata_good = {
        "q_content": {"ci95_pp": [-2.0, 2.5]},
        "q_episodic": {"ci95_pp": [3.0, 12.0]},
        "q_vague": {"ci95_pp": [-1.0, 1.0]},
    }

    def test_the_gate_must_stop_the_content_regression_and_keep_the_episodic_gain(self):
        row = {"recall@5_pp": 3.0, "ci95_pp": [0.5, 5.5]}
        v = sv.verdict(row, {"significant": True, "p": 0.001, "holm_threshold": 0.01},
                       gated=True, strata=self.strata_good)
        assert v["supported"]

    def test_a_still_credible_content_regression_fails_the_gate(self):
        strata = {**self.strata_good, "q_content": {"ci95_pp": [-9.0, -2.0]}}
        row = {"recall@5_pp": 3.0, "ci95_pp": [0.5, 5.5]}
        v = sv.verdict(row, {"significant": True, "p": 0.001, "holm_threshold": 0.01},
                       gated=True, strata=strata)
        assert not v["supported"]
        assert any("q_content" in r for r in v["failed"])

    def test_an_episodic_gain_that_went_away_fails_the_gate(self):
        strata = {**self.strata_good, "q_episodic": {"ci95_pp": [-1.0, 6.0]}}
        row = {"recall@5_pp": 3.0, "ci95_pp": [0.5, 5.5]}
        v = sv.verdict(row, {"significant": True, "p": 0.001, "holm_threshold": 0.01},
                       gated=True, strata=strata)
        assert not v["supported"]
        assert any("q_episodic" in r for r in v["failed"])


class TestHowSmallAnEffectCouldHaveBeenSeen:
    def test_more_disagreement_means_less_sensitivity(self):
        assert sv.detectable_pp(90, 620) > sv.detectable_pp(20, 620)

    def test_a_bigger_query_set_means_more_sensitivity(self):
        assert sv.detectable_pp(50, 620) < sv.detectable_pp(50, 479)

    def test_two_identical_rungs_have_no_detectable_effect_rather_than_zero(self):
        import math
        assert math.isnan(sv.detectable_pp(0, 620))
