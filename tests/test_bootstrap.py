"""Bootstrap CI + delta-significance tests (GitHub issue #1)."""

from __future__ import annotations

import pytest

from src.bootstrap import bootstrap_ci, delta_significance


class TestBootstrapCI:
    def test_ci_covers_true_mean(self):
        # 200 Bernoulli draws at p=0.7 — the bootstrap CI must contain ~0.7.
        values = [1.0] * 140 + [0.0] * 60
        ci = bootstrap_ci(values, seed=7)
        assert ci is not None
        assert ci["lo"] <= 0.7 <= ci["hi"]
        assert 0 <= ci["lo"] <= ci["hi"] <= 1
        assert ci["n"] == 200
        assert ci["method"] == "percentile-bootstrap"
        assert ci["seed"] == 7

    def test_small_sample_gets_wide_ci(self):
        values = [1.0, 1.0, 0.0, 1.0]
        ci = bootstrap_ci(values, seed=1)
        assert ci is not None
        # n=4 honest width: much wider than a 4-doc Wilson would claim falsely.
        assert ci["half"] >= 0.1

    def test_all_same_values_ci_is_point(self):
        ci = bootstrap_ci([0.9, 0.9, 0.9, 0.9], seed=1)
        assert ci["lo"] == 0.9 and ci["hi"] == 0.9

    def test_single_value_returns_none(self):
        assert bootstrap_ci([0.8]) is None
        assert bootstrap_ci([]) is None

    def test_deterministic_given_seed(self):
        a = bootstrap_ci([1.0, 0.0, 1.0, 0.5, 0.8], seed=42)
        b = bootstrap_ci([1.0, 0.0, 1.0, 0.5, 0.8], seed=42)
        assert a == b

    def test_booleans_and_nones_are_cleaned(self):
        ci = bootstrap_ci([True, False, True, None, "x", 1.0], seed=3)
        assert ci["n"] == 4  # True/False/True/1.0


class TestDeltaSignificance:
    def test_clear_win_is_significant(self):
        a = [0.0] * 20
        b = [1.0] * 20
        ds = delta_significance(a, b, seed=5)
        assert ds["significant"] is True
        assert ds["ci_lo"] > 0

    def test_small_sample_overlap_not_significant(self):
        # 5-doc runs with a ~10pp gap: CI must span zero.
        a = [1.0, 1.0, 1.0, 1.0, 0.0]
        b = [1.0, 1.0, 1.0, 0.0, 0.0]
        ds = delta_significance(a, b, seed=5)
        assert ds["significant"] is False
        assert ds["ci_lo"] <= 0 <= ds["ci_hi"]

    def test_insufficient_data_returns_none(self):
        assert delta_significance([0.8], [1.0, 1.0]) is None

    def test_components(self):
        ds = delta_significance([0.0] * 20, [1.0] * 20, seed=9)
        assert ds["n_a"] == 20 and ds["n_b"] == 20
        assert ds["delta"] == pytest.approx(1.0, abs=0.001)
