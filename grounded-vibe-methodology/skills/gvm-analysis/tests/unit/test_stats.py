"""Tests for `_shared/stats.py` — P3-C01.

Covers the tier dispatcher (ADR-204), robust stats / classical stats /
distribution check (ADR-203), and bootstrap_ci (ADR-202 + AN-11).

Spec refs: TC-AN-10-01..03, TC-AN-11-01..03 [PROPERTY], TC-AN-12-01..06,
TC-AN-13-01.
"""

from __future__ import annotations

import math
import warnings

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings, strategies as st
from scipy import stats as scipy_stats


# ---------------------------------------------------------------------------
# Tier enum and dispatcher (ADR-204, TC-AN-12-01..06)
# ---------------------------------------------------------------------------


def test_tier_enum_values_are_canonical_strings() -> None:
    """The tier string values are the findings.json schema contract (ADR-201)."""
    from _shared import stats

    assert stats.Tier.N_LT_10.value == "n<10"
    assert stats.Tier.N_10_29.value == "n=10-29"
    assert stats.Tier.N_30_99.value == "n=30-99"
    assert stats.Tier.N_100_PLUS.value == "n=100+"
    assert stats.Tier.N_1000_PLUS.value == "n>=1000"
    assert stats.Tier.N_10000_PLUS.value == "n>=10000"


def test_tier_zero() -> None:
    from _shared import stats

    assert stats.tier(0) is stats.Tier.N_LT_10


def test_tier_nine_is_lt_10() -> None:
    """TC-AN-12-01: n=9 below threshold."""
    from _shared import stats

    assert stats.tier(9) is stats.Tier.N_LT_10


def test_tier_ten_enters_robust_tier() -> None:
    """TC-AN-12-02: n=10 boundary."""
    from _shared import stats

    assert stats.tier(10) is stats.Tier.N_10_29


def test_tier_twentynine_last_robust_only() -> None:
    """TC-AN-12-03: n=29 upper boundary of robust-only tier."""
    from _shared import stats

    assert stats.tier(29) is stats.Tier.N_10_29


def test_tier_thirty_unlocks_bootstrap() -> None:
    """TC-AN-12-04: n=30 boundary for bootstrap CI tier."""
    from _shared import stats

    assert stats.tier(30) is stats.Tier.N_30_99


def test_tier_ninetynine_last_cautious_ci() -> None:
    from _shared import stats

    assert stats.tier(99) is stats.Tier.N_30_99


def test_tier_hundred_full_distribution_checks() -> None:
    from _shared import stats

    assert stats.tier(100) is stats.Tier.N_100_PLUS


def test_tier_ninenine_nine_below_multivariate() -> None:
    """TC-AN-12-05: n=999 just below multivariate threshold."""
    from _shared import stats

    assert stats.tier(999) is stats.Tier.N_100_PLUS


def test_tier_thousand_unlocks_multivariate() -> None:
    """TC-AN-12-06: n=1000 unlocks IsolationForest + LOF."""
    from _shared import stats

    assert stats.tier(1000) is stats.Tier.N_1000_PLUS


def test_tier_ten_thousand_sampling_tier() -> None:
    """TC-AN-12-07 tier side: n=10000 enters sampling tier."""
    from _shared import stats

    assert stats.tier(10000) is stats.Tier.N_10000_PLUS


def test_tier_rejects_negative() -> None:
    from _shared import stats

    with pytest.raises(ValueError):
        stats.tier(-1)


# ---------------------------------------------------------------------------
# Robust stats (ADR-203, TC-AN-10-01)
# ---------------------------------------------------------------------------


def test_robust_stats_returns_expected_keys() -> None:
    from _shared import stats

    result = stats.robust_stats([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    assert set(result.keys()) == {"median", "mad", "iqr", "q1", "q3", "count"}


def test_robust_stats_median_matches_numpy() -> None:
    from _shared import stats

    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    result = stats.robust_stats(values)
    assert result["median"] == pytest.approx(np.median(values))


def test_robust_stats_iqr_and_quartiles_match_numpy() -> None:
    """Lock the quartile definition: numpy linear interpolation."""
    from _shared import stats

    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    result = stats.robust_stats(values)
    q1 = float(np.quantile(values, 0.25))
    q3 = float(np.quantile(values, 0.75))
    assert result["q1"] == pytest.approx(q1)
    assert result["q3"] == pytest.approx(q3)
    assert result["iqr"] == pytest.approx(q3 - q1)


def test_robust_stats_mad_uses_scale_normal() -> None:
    """Iglewicz & Hoaglin: MAD is scaled for consistency with SD under normality."""
    from _shared import stats

    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    result = stats.robust_stats(values)
    expected = scipy_stats.median_abs_deviation(values, scale="normal")
    assert result["mad"] == pytest.approx(expected)


def test_robust_stats_drops_nan() -> None:
    from _shared import stats

    result = stats.robust_stats([1.0, 2.0, np.nan, 3.0, 4.0, 5.0])
    expected = stats.robust_stats([1.0, 2.0, 3.0, 4.0, 5.0])
    assert result == expected


def test_robust_stats_count_reflects_cleaned_length() -> None:
    from _shared import stats

    result = stats.robust_stats([1.0, np.nan, 2.0, np.nan, 3.0])
    assert result["count"] == 3


def test_robust_stats_all_nan_raises() -> None:
    from _shared import stats

    with pytest.raises(ValueError):
        stats.robust_stats([np.nan, np.nan, np.nan])


def test_robust_stats_returns_python_floats() -> None:
    """Boundary hygiene: JSON-clean types at the API boundary."""
    from _shared import stats

    result = stats.robust_stats([1.0, 2.0, 3.0, 4.0, 5.0])
    for key in ("median", "mad", "iqr", "q1", "q3"):
        assert type(result[key]) is float
    assert type(result["count"]) is int


# ---------------------------------------------------------------------------
# Classical stats
# ---------------------------------------------------------------------------


def test_classical_stats_returns_expected_keys() -> None:
    from _shared import stats

    result = stats.classical_stats([1.0, 2.0, 3.0, 4.0, 5.0])
    assert set(result.keys()) == {"mean", "sd", "count"}


def test_classical_stats_mean_matches_numpy() -> None:
    from _shared import stats

    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    result = stats.classical_stats(values)
    assert result["mean"] == pytest.approx(np.mean(values))


def test_classical_stats_sd_uses_ddof_1() -> None:
    """Sample SD (ddof=1), not population SD."""
    from _shared import stats

    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    result = stats.classical_stats(values)
    assert result["sd"] == pytest.approx(np.std(values, ddof=1))


def test_classical_stats_drops_nan() -> None:
    from _shared import stats

    result = stats.classical_stats([1.0, 2.0, np.nan, 3.0])
    expected = stats.classical_stats([1.0, 2.0, 3.0])
    assert result == expected


def test_classical_stats_returns_python_floats() -> None:
    from _shared import stats

    result = stats.classical_stats([1.0, 2.0, 3.0, 4.0, 5.0])
    assert type(result["mean"]) is float
    assert type(result["sd"]) is float


# ---------------------------------------------------------------------------
# Distribution check (ADR-203)
# ---------------------------------------------------------------------------


def test_distribution_check_normal_path() -> None:
    from _shared import stats

    rng = np.random.default_rng(42)
    values = rng.normal(size=200)
    result = stats.distribution_check(values)
    assert result["test"] == "shapiro"
    assert result["is_normal"] is True
    assert result["p_value"] > 0.05


def test_distribution_check_skewed_path() -> None:
    from _shared import stats

    rng = np.random.default_rng(42)
    values = rng.exponential(size=200)
    result = stats.distribution_check(values)
    assert result["test"] == "shapiro"
    assert result["is_normal"] is False


def test_distribution_check_below_shapiro_min_returns_none() -> None:
    """n<8 is below Shapiro-Wilk's minimum — return a well-formed skip result."""
    from _shared import stats

    result = stats.distribution_check([1.0, 2.0, 3.0, 4.0, 5.0])
    assert result["test"] == "none"
    assert result["is_normal"] is False
    assert result["p_value"] is None
    assert math.isnan(result["statistic"])


def test_distribution_check_boundary_n7_still_none() -> None:
    """Boundary: n=7 is still below the Shapiro-Wilk minimum."""
    from _shared import stats

    result = stats.distribution_check([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0])
    assert result["test"] == "none"


def test_distribution_check_boundary_n8_enters_shapiro() -> None:
    """Boundary: n=8 is the first size Shapiro-Wilk accepts."""
    from _shared import stats

    rng = np.random.default_rng(42)
    result = stats.distribution_check(rng.normal(size=8))
    assert result["test"] == "shapiro"


def test_distribution_check_boundary_n4999_still_shapiro() -> None:
    """Boundary: n=4999 is the last sample size using Shapiro-Wilk."""
    from _shared import stats

    rng = np.random.default_rng(42)
    result = stats.distribution_check(rng.normal(size=4999))
    assert result["test"] == "shapiro"


def test_distribution_check_large_n_switches_to_anderson() -> None:
    from _shared import stats

    rng = np.random.default_rng(42)
    values = rng.normal(size=5000)
    result = stats.distribution_check(values)
    assert result["test"] == "anderson"
    assert result["is_normal"] is True
    # SciPy 1.17+ exposes an interpolated p-value via method='interpolate';
    # the legacy `critical_values` field is going away in 1.19. A normal
    # sample passes when pvalue > alpha (default 0.05).
    assert isinstance(result["p_value"], float)
    assert result["p_value"] > 0.05


def test_distribution_check_anderson_skewed() -> None:
    from _shared import stats

    rng = np.random.default_rng(42)
    values = rng.exponential(size=5000)
    result = stats.distribution_check(values)
    assert result["test"] == "anderson"
    assert result["is_normal"] is False


def test_distribution_check_returns_expected_keys() -> None:
    from _shared import stats

    result = stats.distribution_check([1.0, 2.0, 3.0, 4.0, 5.0])
    assert set(result.keys()) == {"test", "statistic", "p_value", "is_normal"}


def test_distribution_check_drops_nan() -> None:
    from _shared import stats

    rng = np.random.default_rng(42)
    values = rng.normal(size=200).tolist()
    values_with_nan = values[:50] + [np.nan] + values[50:]
    clean_result = stats.distribution_check(values)
    dirty_result = stats.distribution_check(values_with_nan)
    assert clean_result["test"] == dirty_result["test"]
    assert clean_result["is_normal"] == dirty_result["is_normal"]


# ---------------------------------------------------------------------------
# Bootstrap CI (ADR-202, AN-11, TC-AN-11-01..03)
# ---------------------------------------------------------------------------


def test_bootstrap_ci_returns_tuple_of_python_floats() -> None:
    """TC-AN-11-01 shape: tuple[float, float]."""
    from _shared import stats

    rng = np.random.default_rng(42)
    result = stats.bootstrap_ci(
        [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
        np.median,
        rng=rng,
    )
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert type(result[0]) is float
    assert type(result[1]) is float
    low, high = result
    assert low <= high


def test_bootstrap_ci_accepts_single_sample_list() -> None:
    """Regression guard for ADR-202 CRITICAL-T11.

    scipy.stats.bootstrap requires the data argument to be a tuple of
    samples — passing a bare sequence raises TypeError. Our wrapper must
    tuple-wrap the input internally.
    """
    from _shared import stats

    rng = np.random.default_rng(42)
    stats.bootstrap_ci([1.0, 2.0, 3.0, 4.0, 5.0], np.median, rng=rng)


def test_bootstrap_ci_reproducible_same_seed() -> None:
    """TC-AN-11-02: same seed + same data + same statistic → identical CI."""
    from _shared import stats

    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]

    rng1 = np.random.default_rng(42)
    ci1 = stats.bootstrap_ci(values, np.median, rng=rng1)

    rng2 = np.random.default_rng(42)
    ci2 = stats.bootstrap_ci(values, np.median, rng=rng2)

    assert ci1 == ci2


def test_bootstrap_ci_different_seeds_produce_different_cis() -> None:
    from _shared import stats

    rng = np.random.default_rng(42)
    values = rng.normal(size=100).tolist()

    ci1 = stats.bootstrap_ci(values, np.median, rng=np.random.default_rng(1))
    ci2 = stats.bootstrap_ci(values, np.median, rng=np.random.default_rng(2))
    assert ci1 != ci2


def test_bootstrap_ci_from_subseed_int_reproducible() -> None:
    """Parallel-worker pattern: construct a fresh Generator from a sub-seed
    int; two workers with the same sub-seed get the same CI."""
    from _shared import stats

    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    sub_seed = 12345
    ci1 = stats.bootstrap_ci(values, np.median, rng=np.random.default_rng(sub_seed))
    ci2 = stats.bootstrap_ci(values, np.median, rng=np.random.default_rng(sub_seed))
    assert ci1 == ci2


def test_bootstrap_ci_handles_all_equal_values() -> None:
    """Boundary: zero-variance input. scipy emits a DegenerateDataWarning
    but must return a valid (equal) interval."""
    from _shared import stats

    rng = np.random.default_rng(42)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        low, high = stats.bootstrap_ci([5.0] * 30, np.median, rng=rng, n_iter=200)
    assert low == pytest.approx(5.0)
    assert high == pytest.approx(5.0)


def test_bootstrap_ci_default_iterations_from_constants() -> None:
    """n_iter and confidence defaults are sourced from `_shared/constants.py`."""
    from _shared import constants, stats

    kwdefaults = stats.bootstrap_ci.__kwdefaults__
    assert kwdefaults["n_iter"] == constants.BOOTSTRAP_N_ITER
    assert kwdefaults["confidence"] == constants.BOOTSTRAP_CONFIDENCE
    # Sanity: calling without n_iter/confidence still returns a tuple.
    rng = np.random.default_rng(42)
    values = list(np.random.default_rng(0).normal(size=100))
    ci = stats.bootstrap_ci(values, np.median, rng=rng)
    assert isinstance(ci, tuple)


@given(
    data=st.lists(
        st.floats(
            allow_nan=False,
            allow_infinity=False,
            min_value=-1e6,
            max_value=1e6,
        ),
        min_size=30,
        max_size=120,
    ),
    seed=st.integers(min_value=0, max_value=2**31 - 2),
)
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_bootstrap_ci_round_trip_property(data, seed) -> None:
    """TC-AN-11-03 [PROPERTY]: same data + same seed → identical CI."""
    from _shared import stats

    # Guard against scipy-rejecting inputs (all-equal → DegenerateDataWarning).
    if len(set(data)) < 2:
        return
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ci1 = stats.bootstrap_ci(
            data, np.median, rng=np.random.default_rng(seed), n_iter=200
        )
        ci2 = stats.bootstrap_ci(
            data, np.median, rng=np.random.default_rng(seed), n_iter=200
        )
    assert ci1 == ci2
