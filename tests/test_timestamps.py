"""Timestamp unit detection.

This is the highest-value test file in the project. The design originally
specified only the WebKit conversion; applying it to a Netscape export silently
maps every bookmark to 1601-01-01, which destroys the episodic facet without
raising anything. These tests pin both units and the failure mode.
"""

from __future__ import annotations

import datetime as dt

from facetmark.importers import timestamps as T

# Real values taken from a genuine Chrome HTML export.
REAL_UNIX_S = [1646877833, 1646926493, 1690391875, 1785588594]
# Equivalent magnitudes for Chromium's JSON store.
REAL_WEBKIT_US = [13300000000000000, 13350000000000000, 13400000000000000]


def _year(ts: int) -> int:
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).year


class TestClassifyOne:
    def test_ten_digit_values_are_unix_seconds(self):
        for v in REAL_UNIX_S:
            assert T.classify_one(v) == "unix_s"

    def test_seventeen_digit_values_are_webkit_microseconds(self):
        for v in REAL_WEBKIT_US:
            assert T.classify_one(v) == "webkit_us"

    def test_thirteen_digit_values_are_unix_milliseconds(self):
        assert T.classify_one(1690391875000) == "unix_ms"

    def test_zero_and_negative_are_rejected(self):
        assert T.classify_one(0) is None
        assert T.classify_one(-5) is None

    def test_implausibly_small_value_is_rejected(self):
        # 1970-01-02 is older than the 1990 floor and is not a real bookmark date.
        assert T.classify_one(100_000) is None


class TestTheBugThisModuleExistsFor:
    def test_webkit_formula_on_unix_seconds_lands_on_1601(self):
        """The exact failure the design would have shipped."""
        wrong = [T.convert(v, "webkit_us") for v in REAL_UNIX_S]
        assert all(_year(w) == 1601 for w in wrong)
        # ...and it is silent: no exception, just uniformly wrong data.
        assert all(isinstance(w, int) for w in wrong)

    def test_detection_prevents_it(self):
        converted, unit = T.convert_all([float(v) for v in REAL_UNIX_S])
        assert unit == "unix_s"
        assert [_year(c) for c in converted] == [2022, 2022, 2023, 2026]

    def test_unix_formula_on_webkit_values_is_also_rejected(self):
        # Treating WebKit microseconds as seconds gives year ~421 million.
        assert T.classify_one(REAL_WEBKIT_US[0]) != "unix_s"


class TestConvertAll:
    def test_majority_vote_ignores_a_single_corrupt_value(self):
        vals = [*[float(v) for v in REAL_UNIX_S], 1.0]
        converted, unit = T.convert_all(vals)
        assert unit == "unix_s"
        # The corrupt value is dropped rather than reinterpreted.
        assert converted[-1] is None

    def test_none_and_zero_become_none(self):
        converted, unit = T.convert_all([1690391875.0, None, 0.0])
        assert unit == "unix_s"
        assert converted[1] is None and converted[2] is None

    def test_all_missing_returns_no_unit(self):
        converted, unit = T.convert_all([None, None])
        assert unit is None
        assert converted == [None, None]

    def test_webkit_round_trip_is_exact(self):
        for v in REAL_WEBKIT_US:
            unix = T.convert(v, "webkit_us")
            back = (unix + T.WEBKIT_EPOCH_OFFSET) * 1_000_000
            assert back == v

    def test_offset_constant(self):
        assert T.WEBKIT_EPOCH_OFFSET == 11_644_473_600
        # 1601-01-01 in WebKit terms is exactly -offset in Unix terms.
        assert T.convert(0, "webkit_us") == -T.WEBKIT_EPOCH_OFFSET

    def test_mixed_units_use_per_value_fallback(self):
        # A file where most rows are Unix seconds but one is WebKit.
        vals = [*[float(v) for v in REAL_UNIX_S], float(REAL_WEBKIT_US[0])]
        converted, unit = T.convert_all(vals)
        assert unit == "unix_s"
        assert converted[-1] is not None
        assert _year(converted[-1]) == 2022
