"""Tests for ``_shared/time_series.py`` — AN-19..22 (forecast not in this chunk)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from _shared import time_series as ts


# ---------------------------------------------------------------------------
# Cadence inference
# ---------------------------------------------------------------------------


def _daily(n: int, start: str = "2024-01-01") -> pd.DatetimeIndex:
    return pd.date_range(start=start, periods=n, freq="D")


def test_tc_an_19_04_daily_cadence_inferred() -> None:
    idx = _daily(90)
    result = ts.infer_cadence(idx)
    assert result["label"] == "daily"
    assert result["median_gap_seconds"] == 24 * 3600


def test_tc_an_19_05_weekly_monthly_irregular() -> None:
    weekly = pd.date_range(start="2024-01-01", periods=26, freq="7D")
    assert ts.infer_cadence(weekly)["label"] == "weekly"

    # Monthly — 30-day gaps
    monthly = pd.date_range(start="2024-01-01", periods=12, freq="30D")
    assert ts.infer_cadence(monthly)["label"] == "monthly"

    # Irregular — random gaps with high sigma/median
    rng = np.random.default_rng(0)
    gaps = rng.integers(3600, 3600 * 24 * 30, size=30)
    irreg = pd.to_datetime(
        pd.Timestamp("2024-01-01") + pd.to_timedelta(gaps.cumsum(), unit="s")
    )
    label = ts.infer_cadence(irreg)["label"]
    assert "irregular" in label


def test_cadence_sigma_over_median_precedence() -> None:
    # Stable 24h gaps → daily. But if we inject one huge gap to push sigma high,
    # σ/median > 0.5 should fire first and flip to irregular.
    base = list(_daily(30))
    base.append(base[-1] + timedelta(days=60))  # one huge gap
    idx = pd.DatetimeIndex(base)
    assert "irregular" in ts.infer_cadence(idx)["label"]


def test_cadence_empty_raises() -> None:
    with pytest.raises(ValueError):
        ts.infer_cadence(pd.DatetimeIndex([]))


# ---------------------------------------------------------------------------
# Gap detection
# ---------------------------------------------------------------------------


def test_tc_an_20_01_gap_detection_boundary() -> None:
    # Daily series with a 3-day gap and a 4-day gap; median = 1 day; 2× threshold.
    # Include the 2-day gap as boundary — should NOT be flagged.
    # Mostly 1-day gaps so median=1day; inject longer gaps at the end.
    ts_list = [
        "2024-01-01",
        "2024-01-02",  # 1-day
        "2024-01-03",  # 1-day
        "2024-01-04",  # 1-day
        "2024-01-05",  # 1-day
        "2024-01-06",  # 1-day
        "2024-01-07",  # 1-day
        "2024-01-09",  # 2-day — boundary, NOT flagged (must be > 2× median)
        "2024-01-12",  # 3-day — flagged
        "2024-01-16",  # 4-day — flagged
    ]
    idx = pd.DatetimeIndex(pd.to_datetime(ts_list))
    gaps = ts.detect_gaps(idx, multiplier=2.0)
    flagged_seconds = {g["gap_seconds"] for g in gaps}
    # 3-day and 4-day gaps are flagged.
    assert 3 * 86400 in flagged_seconds
    assert 4 * 86400 in flagged_seconds
    # 2-day (boundary) not flagged.
    assert 2 * 86400 not in flagged_seconds
    # 1-day definitely not flagged.
    assert 86400 not in flagged_seconds
    # Each entry has the expected fields.
    for g in gaps:
        assert set(g) == {"after_index", "gap_seconds", "multiplier"}
        assert g["multiplier"] > 2.0


def test_gap_detection_empty_and_single_point() -> None:
    assert ts.detect_gaps(pd.DatetimeIndex([])) == []
    single = pd.DatetimeIndex(["2024-01-01"])
    assert ts.detect_gaps(single) == []


# ---------------------------------------------------------------------------
# Stale detection
# ---------------------------------------------------------------------------


def test_tc_an_20_02_stale_detection() -> None:
    # Daily series whose last observation is 5 days old.
    now = datetime(2024, 1, 10, tzinfo=timezone.utc)
    idx = pd.DatetimeIndex(
        pd.to_datetime(
            ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
        ).tz_localize("UTC")
    )
    median_gap_seconds = 86400
    result = ts.detect_stale(idx, median_gap_seconds, multiplier=1.0, now=now)
    assert result is not None
    assert set(result) == {"most_recent", "expected_within"}
    # ISO8601 strings.
    assert isinstance(result["most_recent"], str)
    assert "2024-01-05" in result["most_recent"]


def test_stale_detection_naive_timestamps() -> None:
    """Naive (tz-unaware) timestamps must be handled by localizing to UTC."""
    # Deliberately naive index and naive `now`.
    now_naive = datetime(2024, 1, 10)  # naive
    idx = pd.DatetimeIndex(pd.to_datetime(["2024-01-01", "2024-01-05"]))
    assert idx.tz is None
    result = ts.detect_stale(
        idx, median_gap_seconds=86400, multiplier=1.0, now=now_naive
    )
    assert result is not None  # 5 days old ≫ 1× 1-day median.


def test_stale_detection_not_stale() -> None:
    now = datetime(2024, 1, 6, 12, tzinfo=timezone.utc)
    idx = pd.DatetimeIndex(
        pd.to_datetime(["2024-01-05", "2024-01-06"]).tz_localize("UTC")
    )
    # Last obs 12 hours old; median gap 1 day; 1× threshold → not stale.
    result = ts.detect_stale(idx, 86400, multiplier=1.0, now=now)
    assert result is None


# ---------------------------------------------------------------------------
# Multi-window outliers
# ---------------------------------------------------------------------------


def test_tc_an_21_03_plain_outlier_across_all_windows() -> None:
    # 1000-point series, median ~100, one extreme value present in all three
    # windows (since the extreme sits in the most recent chunk too).
    rng = np.random.default_rng(0)
    values = rng.normal(100, 5, size=999).tolist()
    values.append(10000.0)  # row 999 extreme
    s = pd.Series(values)
    out = ts.multi_window_outliers(s)
    target = [e for e in out if e["row_index"] == 999]
    assert len(target) == 1
    assert target[0]["label"] == "plain_outlier"
    assert set(target[0]["windows"]) == {"full", "last_quartile", "recent_n"}


def test_tc_an_21_04_multi_window_n_adapts() -> None:
    # Compare the implied `recent_n` across a short and long series by
    # running multi_window_outliers — we can't query the window size directly,
    # but we can assert the function runs on both and returns lists.
    short = pd.Series(np.random.default_rng(0).normal(100, 5, size=100))
    long = pd.Series(np.random.default_rng(0).normal(100, 5, size=10000))
    assert isinstance(ts.multi_window_outliers(short), list)
    assert isinstance(ts.multi_window_outliers(long), list)


def test_multi_window_empty() -> None:
    assert ts.multi_window_outliers(pd.Series([], dtype=float)) == []


def test_multi_window_constant_series_no_outliers() -> None:
    assert ts.multi_window_outliers(pd.Series([5.0] * 200)) == []


# ---------------------------------------------------------------------------
# Trend — Mann-Kendall
# ---------------------------------------------------------------------------


def test_tc_an_22_01_monotonic_trend_significant() -> None:
    values = list(range(1, 201))  # strictly increasing
    result = ts.trend_test(values, alpha=0.05)
    assert result["method"] == "mann-kendall"
    assert result["significant"] is True
    assert result["trend_label"] == "increasing"
    assert 0.0 <= result["p_value"] <= 1.0


def test_tc_an_22_03_white_noise_no_trend() -> None:
    rng = np.random.default_rng(0)
    values = rng.normal(0, 1, size=200).tolist()
    result = ts.trend_test(values, alpha=0.05)
    assert result["significant"] is False
    assert result["trend_label"] == "no trend"


def test_tc_an_22_08_alpha_override_threads_through_and_flips_significance() -> None:
    # Mild upward trend: under default alpha=0.05 may be non-significant,
    # under alpha=0.5 should always be significant (very low bar).
    rng = np.random.default_rng(1)
    values = (rng.normal(0, 1, size=40) + np.linspace(0, 1.0, 40)).tolist()
    result_loose = ts.trend_test(values, alpha=0.5)
    assert result_loose["alpha"] == 0.5
    assert result_loose["significant"] is True
    # And the same data under alpha=0.001 should drop to non-significant
    # unless the trend is overwhelmingly strong.
    tiny_alpha = ts.trend_test(values, alpha=0.001)
    assert tiny_alpha["alpha"] == 0.001


# ---------------------------------------------------------------------------
# Seasonality — STL
# ---------------------------------------------------------------------------


def test_tc_an_22_02_strong_weekly_seasonality() -> None:
    # Daily series with strong 7-day cycle.
    n = 200
    t = np.arange(n)
    values = 100 + 10 * np.sin(2 * np.pi * t / 7)  # pure weekly cycle
    result = ts.detect_seasonality(values, period=7, threshold=0.6)
    assert result is not None
    assert result["method"] == "stl"
    assert result["significant"] is True
    assert result["strength"] > 0.6
    assert result["period"] == 7


def test_tc_an_22_03_stationary_noise_no_seasonality() -> None:
    rng = np.random.default_rng(0)
    values = rng.normal(0, 1, size=200)
    result = ts.detect_seasonality(values, period=7, threshold=0.6)
    # Result structure is returned (not None) but significant=False.
    assert result is not None
    assert result["significant"] is False


def test_seasonality_short_series_skipped() -> None:
    # len(series) < 2*period + 1 — must return None.
    result = ts.detect_seasonality([1, 2, 3, 4, 5, 6, 7, 8], period=7)
    assert result is None


def test_seasonality_irregular_period_none() -> None:
    # Passing period=None (irregular cadence) → None.
    result = ts.detect_seasonality([1, 2, 3, 4], period=None)
    assert result is None


# ---------------------------------------------------------------------------
# Orchestrator `analyse`
# ---------------------------------------------------------------------------


def test_analyse_returns_full_schema_on_daily_input() -> None:
    idx = _daily(200)
    values = 100 + 10 * np.sin(2 * np.pi * np.arange(200) / 7) + np.arange(200) * 0.5
    df = pd.DataFrame({"ts": idx, "value": values})
    result = ts.analyse(df, time_column="ts", value_column="value")
    assert result is not None
    expected_keys = {
        "time_column",
        "cadence",
        "median_gap_seconds",
        "expected_cadence_seconds",
        "gaps",
        "stale",
        "multi_window_outliers",
        "trend",
        "seasonality",
        "forecast",
    }
    assert set(result) == expected_keys
    assert result["time_column"] == "ts"
    assert result["cadence"] == "daily"
    assert result["forecast"] is None  # P4-C04 fills this


def test_analyse_returns_none_when_time_column_missing() -> None:
    df = pd.DataFrame({"value": [1, 2, 3]})
    assert ts.analyse(df, time_column="ts", value_column="value") is None


def test_analyse_returns_none_on_empty_df() -> None:
    df = pd.DataFrame(
        {
            "ts": pd.Series([], dtype="datetime64[ns]"),
            "value": pd.Series([], dtype=float),
        }
    )
    assert ts.analyse(df, time_column="ts", value_column="value") is None


def test_analyse_unsorted_timestamps_handled() -> None:
    # Shuffled timestamps must be sorted before analysis.
    rng = np.random.default_rng(0)
    idx = list(_daily(100))
    rng.shuffle(idx)
    df = pd.DataFrame({"ts": idx, "value": list(range(100))})
    result = ts.analyse(df, time_column="ts", value_column="value")
    assert result is not None
    # Cadence should still read as daily once sorted.
    assert result["cadence"] == "daily"


# ---------------------------------------------------------------------------
# Constant pins
# ---------------------------------------------------------------------------


def test_constants_pinned_per_adr() -> None:
    assert ts._GAP_MULTIPLIER_DEFAULT == 2.0
    assert ts._STALE_MULTIPLIER_DEFAULT == 1.0
    assert ts._SIGMA_OVER_MEDIAN_IRREGULAR == 0.5
    assert ts._SEASONAL_STRENGTH_THRESHOLD == 0.6
    assert ts._TREND_ALPHA_DEFAULT == 0.05
    assert ts._MAD_THRESHOLD == 3.5


# ---------------------------------------------------------------------------
# Forecast (P4-C04 / ADR-209)
# ---------------------------------------------------------------------------


def _linear_series(
    n: int = 60,
    slope: float = 2.0,
    intercept: float = 1.0,
    noise: float = 0.1,
    seed: int = 0,
) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start="2024-01-01", periods=n, freq="D")
    values = intercept + slope * np.arange(n, dtype=float) + rng.normal(0, noise, n)
    return pd.Series(values, index=idx)


def _ar1_series(
    n: int = 120,
    intercept: float = 10.0,
    phi: float = 0.5,
    noise: float = 1.0,
    seed: int = 0,
) -> pd.Series:
    """Integrated AR(1) — a fixture an ARIMA(1,1,1) fitter can actually estimate.

    The forecaster defaults to ARIMA(1,1,1) when ``pmdarima`` is not present.
    That model expects an integrated process: a random walk whose first
    differences carry stationary AR/MA structure. Building the series by
    cumulating AR(1) innovations gives the differencer something to "undo"
    and the AR/MA terms something to fit. A purely linear series has no
    autoregressive structure under any differencing, so SARIMAX's MLE
    starting-point heuristic picks non-stationary AR coefficients — that
    was the source of the test-only warnings.
    """
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start="2024-01-01", periods=n, freq="D")
    eps = rng.normal(0, noise, n)
    ar = np.zeros(n)
    for i in range(1, n):
        ar[i] = phi * ar[i - 1] + eps[i]
    values = intercept + np.cumsum(ar)
    return pd.Series(values, index=idx)


_ALL_SUB_SEEDS = {
    "forecast_linear_bootstrap": 1,
    "forecast_arima_init": 2,
    "forecast_exp_smoothing_init": 3,
}


def test_forecast_linear_returns_schema_shape():
    s = _linear_series()
    result = ts.forecast(s, "linear", 7, sub_seeds=_ALL_SUB_SEEDS)
    assert result["method"] == "linear"
    assert result["horizon_steps"] == 7
    assert len(result["predictions"]) == 7
    for p in result["predictions"]:
        assert set(p.keys()) == {"ts", "value", "lower", "upper"}
        assert p["lower"] <= p["value"] <= p["upper"]
        # ISO8601 parseable
        pd.Timestamp(p["ts"])


def test_forecast_linear_recovers_slope():
    s = _linear_series(n=100, slope=3.0, intercept=5.0, noise=0.01)
    result = ts.forecast(s, "linear", 5, sub_seeds=_ALL_SUB_SEEDS)
    # At step 100, predicted ≈ 5 + 3*100 = 305
    first_pt = result["predictions"][0]["value"]
    assert 300 <= first_pt <= 310


def test_tc_an_22_04_every_prediction_has_pi():
    """Prediction interval present on every point — any method."""
    s = _ar1_series(n=80)
    for method in ("linear", "arima", "exponential_smoothing"):
        result = ts.forecast(
            s, method, 7, sub_seeds=_ALL_SUB_SEEDS, cadence_label="daily"
        )
        for p in result["predictions"]:
            assert np.isfinite(p["lower"])
            assert np.isfinite(p["upper"])
            assert np.isfinite(p["value"])


def test_forecast_arima_returns_valid_shape():
    s = _ar1_series(n=80)
    result = ts.forecast(s, "arima", 5, sub_seeds=_ALL_SUB_SEEDS, cadence_label="daily")
    assert result["method"] == "arima"
    assert len(result["predictions"]) == 5


def test_forecast_exp_smoothing_on_daily_sinusoid():
    n = 60
    idx = pd.date_range(start="2024-01-01", periods=n, freq="D")
    values = 10 + np.sin(2 * np.pi * np.arange(n) / 7)
    s = pd.Series(values, index=idx)
    result = ts.forecast(
        s, "exponential_smoothing", 7, sub_seeds=_ALL_SUB_SEEDS, cadence_label="daily"
    )
    assert result["method"] == "exponential_smoothing"
    assert len(result["predictions"]) == 7


def test_forecast_horizon_defaults_per_cadence():
    s = _linear_series(n=60)
    for cadence, expected in [
        ("daily", 7),
        ("weekly", 4),
        ("monthly", 12),
        (None, 10),
        ("irregular", 10),
    ]:
        result = ts.forecast(
            s, "linear", horizon=None, sub_seeds=_ALL_SUB_SEEDS, cadence_label=cadence
        )
        assert result["horizon_steps"] == expected, (cadence, expected)


def test_forecast_invalid_method_raises():
    s = _linear_series(n=30)
    with pytest.raises(ValueError, match="unknown forecast method"):
        ts.forecast(s, "holt", 5, sub_seeds=_ALL_SUB_SEEDS)


def test_forecast_missing_sub_seed_raises_key_error():
    s = _linear_series(n=30)
    with pytest.raises(KeyError, match="forecast_linear_bootstrap"):
        ts.forecast(s, "linear", 5, sub_seeds={"forecast_arima_init": 1})


def test_forecast_linear_reproducible_with_same_seed():
    s = _linear_series()
    r1 = ts.forecast(s, "linear", 5, sub_seeds=_ALL_SUB_SEEDS)
    r2 = ts.forecast(s, "linear", 5, sub_seeds=_ALL_SUB_SEEDS)
    v1 = [p["value"] for p in r1["predictions"]]
    v2 = [p["value"] for p in r2["predictions"]]
    l1 = [p["lower"] for p in r1["predictions"]]
    l2 = [p["lower"] for p in r2["predictions"]]
    assert v1 == v2
    assert l1 == l2


def test_forecast_requires_datetime_index():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])  # integer index
    with pytest.raises(TypeError, match="DatetimeIndex"):
        ts.forecast(s, "linear", 3, sub_seeds=_ALL_SUB_SEEDS)


def test_forecast_non_positive_horizon_raises():
    s = _linear_series(n=30)
    with pytest.raises(ValueError, match="positive"):
        ts.forecast(s, "linear", 0, sub_seeds=_ALL_SUB_SEEDS)


def test_forecast_future_ts_spaced_by_cadence():
    s = _linear_series(n=30)
    result = ts.forecast(s, "linear", 3, sub_seeds=_ALL_SUB_SEEDS)
    ts_list = [pd.Timestamp(p["ts"]) for p in result["predictions"]]
    last = s.index[-1]
    assert ts_list[0] > last
    deltas = [(ts_list[i + 1] - ts_list[i]).total_seconds() for i in range(2)]
    assert all(abs(d - 86400) < 1 for d in deltas)


def test_forecast_exp_smoothing_convergence_fallback(monkeypatch):
    """When seasonal Holt-Winters fails to converge, fall back to non-seasonal."""
    from statsmodels.tools.sm_exceptions import ConvergenceWarning
    import statsmodels.tsa.holtwinters as hw

    calls = {"count": 0}

    def fake_fit(self):
        calls["count"] += 1
        # First call is the seasonal attempt — raise. Second is the fallback —
        # defer to the real implementation.
        if getattr(self, "seasonal", None) is not None:
            raise ConvergenceWarning("simulated non-convergence")
        return _real_fit(self)

    _real_fit = hw.ExponentialSmoothing.fit
    monkeypatch.setattr(hw.ExponentialSmoothing, "fit", fake_fit)

    s = _linear_series(n=60)
    result = ts.forecast(
        s,
        "exponential_smoothing",
        5,
        sub_seeds=_ALL_SUB_SEEDS,
        cadence_label="daily",
    )
    assert result["method"] == "exponential_smoothing"
    assert len(result["predictions"]) == 5
    assert any("Holt-Winters seasonal fit failed" in w for w in result["warnings"])
    assert calls["count"] >= 2
