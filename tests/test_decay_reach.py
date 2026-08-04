"""Can the shipped decay layer ever fire?

``apply_decay`` is unit-tested in ``test_search.py`` with hand-written scores --
1.0, 0.9, 0.8 -- and it behaves correctly on them. Reciprocal rank fusion cannot
produce those numbers. The scores the *pipeline* hands it are bounded by
``sum_f w_f / (k + 1)``, and for a one-facet config that ceiling is
``1 / 61 = 0.0164``, which is below the shipped ``decay_rescue_threshold`` of
0.02.

So the rescue valve -- written to fire when the hot layer has nothing to offer
-- fires on every query instead, and the demotion it guards is unreachable.
That matters because :data:`~facetmark.search.pipeline.FULL` is a one-facet
config *and* is the default profile whenever a real API key is configured.

These tests pin the defect rather than paper over it. Raising the threshold or
lowering ``rrf_k`` would change the default ranking for every query, which this
project does not do without a query set and a pre-registered criterion; see
``ROADMAP.md``. When that experiment is run, these tests are the ones that have
to flip.
"""

from __future__ import annotations

import pytest

from facetmark.config import Settings
from facetmark.search import apply_decay, rrf
from facetmark.search.pipeline import ALL_CONFIGS, DEFAULT_FACET_WEIGHTS, FULL, FUSED


def _ceiling(facets, k: int) -> float:
    """Highest score RRF can hand out: every facet ranks the document first."""
    return sum(DEFAULT_FACET_WEIGHTS.get(f, 1.0) for f in facets) / (k + 1)


class TestTheCeilingIsBelowTheValve:
    def test_one_unit_weight_facet_tops_out_below_the_rescue_threshold(self):
        s = Settings(api_key="x")
        top = rrf({"content": [7, 8, 9]}, k=s.rrf_k)[0].score
        assert top == pytest.approx(1.0 / 61)
        assert top == pytest.approx(0.016393, abs=1e-6)
        assert top < s.decay_rescue_threshold

    def test_the_default_profile_is_a_one_facet_config(self):
        assert FULL.facets == frozenset({"content"})
        assert FULL.decay is True

    def test_so_the_default_profile_can_never_demote_anything(self):
        s = Settings(api_key="x")
        # The best case for the demotion: the hot layer's top document is the
        # single highest-scoring thing RRF can emit, and a cold document sits
        # right behind it.
        top = 1.0 / (s.rrf_k + 1)
        scored = [(1, top), (2, 0.9 * top)]
        out, info = apply_decay(
            scored, {2}, factor=s.decay_factor,
            rescue_threshold=s.decay_rescue_threshold,
        )
        assert info.rescued is True
        assert info.demoted == 0
        assert out == scored                      # bit-identical passthrough

    def test_the_four_facet_profile_can_reach_the_valve(self):
        # Not every config is affected -- FUSED clears the threshold on two
        # facets, which is why this is a reach problem and not a broken
        # threshold.
        s = Settings()
        assert _ceiling(FUSED.facets, s.rrf_k) > s.decay_rescue_threshold
        two = _ceiling({"content", "lex_tri"}, s.rrf_k)
        assert two == pytest.approx(1.7 / 61)
        assert two > s.decay_rescue_threshold

    def test_the_reach_gap_is_recorded_for_every_config_that_decays(self):
        s = Settings()
        decaying = {n: c for n, c in ALL_CONFIGS.items() if c.decay}
        assert set(decaying) == {"full", "fused"}
        unreachable = {
            n for n, c in decaying.items()
            if _ceiling(c.facets, s.rrf_k) < s.decay_rescue_threshold
        }
        # If this set ever shrinks, the finding has been fixed and the module
        # docstring above needs rewriting.
        assert unreachable == {"full"}
