"""Time-series analysis (AN-19..22 / ADR-208, ADR-209).

Cadence inference, gap/stale detection, multi-window regime-shift outliers,
Mann-Kendall trend test (pymannkendall), STL seasonal-strength detection
(statsmodels), and forecast methods — linear / ARIMA / exponential-smoothing
— with ADR-201 prediction-interval output.

Public API:

- ``infer_cadence(timestamps)`` — label + median gap + dispersion.
- ``detect_gaps(timestamps, multiplier)`` — gaps above multiplier × median.
- ``detect_stale(timestamps, median_gap_seconds, multiplier, now)`` — whether
  the most-recent observation is older than ``multiplier × median_gap``.
- ``multi_window_outliers(series)`` — per-value regime-shift / plain-outlier
  labelling across full / last-quartile / most-recent-N windows.
- ``trend_test(values, alpha)`` — Mann-Kendall trend block.
- ``detect_seasonality(values, period, threshold)`` — STL seasonal-strength.
- ``analyse(df, time_column, *, value_column, prefs)`` — orchestrator that
  returns the ADR-201 ``time_series`` block in full (forecast always
  ``None``).

Constants mirror the ADR-208 defaults; all are user-overridable via prefs
(AN-32..34) from the caller's side — this module reads its own defaults.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pymannkendall as pmk
from statsmodels.tsa.seasonal import STL

__all__ = [
    "infer_cadence",
    "detect_gaps",
    "detect_stale",
    "multi_window_outliers",
    "trend_test",
    "detect_seasonality",
    "analyse",
    "forecast",
]


# ---- Constants (ADR-208 defaults) ------------------------------------------

_GAP_MULTIPLIER_DEFAULT = 2.0
_STALE_MULTIPLIER_DEFAULT = 1.0
_SIGMA_OVER_MEDIAN_IRREGULAR = 0.5
_SEASONAL_STRENGTH_THRESHOLD = 0.6
_TREND_ALPHA_DEFAULT = 0.05
_MAD_THRESHOLD = 3.5
_MAD_SCALE = 0.6745
_RECENT_N_FLOOR = 20
_RECENT_N_DIVISOR = 100

_CADENCE_TO_STL_PERIOD = {
    "daily": 7,
    "weekly": 52,
    "monthly": 12,
}

# Forecast constants (ADR-209)
_FORECAST_BOOTSTRAP_N = 500
_FORECAST_PI_LO = 0.025
_FORECAST_PI_HI = 0.975
_HORIZON_DAILY = 7
_HORIZON_WEEKLY = 4
_HORIZON_MONTHLY = 12
_HORIZON_DEFAULT = 10

_ARIMA_DEFAULT_ORDER = (1, 1, 1)

_CADENCE_TO_ES_PERIOD = {
    "daily": 7,
    "weekly": 52,
    "monthly": 12,
}

_VALID_FORECAST_METHODS = ("linear", "arima", "exponential_smoothing")


# ---- Cadence inference -----------------------------------------------------


def infer_cadence(timestamps: pd.DatetimeIndex) -> dict:
    """Return ``{label, median_gap_seconds, sigma_over_median, expected_cadence_seconds}``.

    Decision order (ADR-208): σ/median > 0.5 ⇒ irregular; else classify by
    median gap into daily / weekly / monthly / irregular-with-detail.
    """
    if len(timestamps) < 2:
        raise ValueError("infer_cadence requires at least 2 timestamps")
    sorted_ts = timestamps.sort_values()
    diffs = sorted_ts.to_series().diff().dt.total_seconds().dropna().to_numpy()
    median_gap = float(np.median(diffs))
    sigma = float(np.std(diffs))
    sigma_over_median = sigma / median_gap if median_gap > 0 else float("inf")

    if sigma_over_median > _SIGMA_OVER_MEDIAN_IRREGULAR:
        label = f"irregular (cadence ~{round(median_gap / 86400, 1)} days)"
    else:
        hours = median_gap / 3600
        days = hours / 24
        if 18 <= hours <= 30:
            label = "daily"
        elif 5 <= days <= 9:
            label = "weekly"
        elif 25 <= days <= 35:
            label = "monthly"
        else:
            label = f"irregular (cadence ~{round(days, 1)} days)"

    return {
        "label": label,
        "median_gap_seconds": int(median_gap),
        "sigma_over_median": round(sigma_over_median, 4),
        "expected_cadence_seconds": int(median_gap),
    }


# ---- Gap / stale detection -------------------------------------------------


def detect_gaps(
    timestamps: pd.DatetimeIndex,
    multiplier: float = _GAP_MULTIPLIER_DEFAULT,
) -> list[dict]:
    """Return entries for gaps strictly greater than ``multiplier × median_gap``."""
    if len(timestamps) < 2:
        return []
    sorted_ts = timestamps.sort_values()
    diffs = sorted_ts.to_series().diff().dt.total_seconds().dropna().to_numpy()
    median_gap = float(np.median(diffs))
    if median_gap <= 0:
        return []
    threshold = multiplier * median_gap
    out = []
    for i, g in enumerate(diffs):
        if g > threshold:
            out.append(
                {
                    "after_index": int(i),
                    "gap_seconds": int(g),
                    "multiplier": round(float(g) / median_gap, 3),
                }
            )
    return out


def detect_stale(
    timestamps: pd.DatetimeIndex,
    median_gap_seconds: float,
    multiplier: float = _STALE_MULTIPLIER_DEFAULT,
    now: datetime | None = None,
) -> dict | None:
    """Return a stale-marker dict if the last timestamp is older than
    ``multiplier × median_gap_seconds``; else ``None``."""
    if len(timestamps) == 0:
        return None
    most_recent = timestamps.max()
    reference = now or datetime.now(timezone.utc)
    # Align timezone awareness. pandas Timestamp → datetime.
    if most_recent.tzinfo is None:
        most_recent = most_recent.tz_localize("UTC")
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    age_seconds = (reference - most_recent.to_pydatetime()).total_seconds()
    # Strict > matches the gap-detection rule (ADR-208 TC-AN-20-01):
    # flag only when the age strictly exceeds the threshold. `<=` here
    # means "not stale" for age == threshold, which is the correct boundary.
    if age_seconds <= multiplier * median_gap_seconds:
        return None
    expected_within = most_recent + timedelta(seconds=multiplier * median_gap_seconds)
    return {
        "most_recent": most_recent.isoformat(),
        "expected_within": expected_within.isoformat(),
    }


# ---- Multi-window outliers -------------------------------------------------


def multi_window_outliers(
    series: pd.Series,
    *,
    recent_n: int | None = None,
) -> list[dict]:
    """Flag values as ``plain_outlier`` or ``regime_shift`` across three windows.

    Windows: full series, last quartile, most recent N (default
    ``max(20, len // 100)``). MAD modified z-score > 3.5 per window.
    """
    if series.empty:
        return []
    n = len(series)
    if recent_n is None:
        recent_n = max(_RECENT_N_FLOOR, n // _RECENT_N_DIVISOR)
    recent_n = min(recent_n, n)

    full_mask = _mad_mask(series)
    q_start = max(0, int(n * 0.75))
    quartile_mask = _mask_over_window(series, q_start, n)
    recent_start = max(0, n - recent_n)
    recent_mask = _mask_over_window(series, recent_start, n)

    out = []
    for pos, (idx, value) in enumerate(series.items()):
        flagged_in = []
        if full_mask[pos]:
            flagged_in.append("full")
        if quartile_mask[pos]:
            flagged_in.append("last_quartile")
        if recent_mask[pos]:
            flagged_in.append("recent_n")
        if not flagged_in:
            continue
        label = "plain_outlier" if len(flagged_in) == 3 else "regime_shift"
        out.append(
            {
                "row_index": int(idx),
                "value": float(value),
                "windows": flagged_in,
                "label": label,
            }
        )
    return out


def _mad_mask(series: pd.Series) -> np.ndarray:
    """Return a boolean mask: True where modified z-score > 3.5."""
    arr = series.to_numpy(dtype=float)
    med = float(np.median(arr))
    mad = float(np.median(np.abs(arr - med)))
    if mad == 0:
        return np.zeros(len(arr), dtype=bool)
    z = _MAD_SCALE * (arr - med) / mad
    return np.abs(z) > _MAD_THRESHOLD


def _mask_over_window(series: pd.Series, start: int, end: int) -> np.ndarray:
    """Compute MAD mask using stats from rows [start, end) but return the
    mask aligned to every row of the full series."""
    arr = series.to_numpy(dtype=float)
    window = arr[start:end]
    if len(window) == 0:
        return np.zeros(len(arr), dtype=bool)
    med = float(np.median(window))
    mad = float(np.median(np.abs(window - med)))
    if mad == 0:
        return np.zeros(len(arr), dtype=bool)
    z = _MAD_SCALE * (arr - med) / mad
    # A value is flagged in this window only if it *lies in* the window AND
    # its z-score (computed from the window's stats) exceeds threshold.
    in_window = np.zeros(len(arr), dtype=bool)
    in_window[start:end] = True
    return in_window & (np.abs(z) > _MAD_THRESHOLD)


# ---- Trend (Mann-Kendall) --------------------------------------------------


def trend_test(values, alpha: float = _TREND_ALPHA_DEFAULT) -> dict:
    """Mann-Kendall trend test via ``pymannkendall.original_test``."""
    arr = np.asarray(values, dtype=float)
    # pymannkendall requires at least a handful of observations.
    if arr.size < 4:
        return {
            "method": "mann-kendall",
            "alpha": alpha,
            "p_value": 1.0,
            "significant": False,
            "trend_label": "no trend",
        }
    result = pmk.original_test(arr, alpha=alpha)
    return {
        "method": "mann-kendall",
        "alpha": alpha,
        "p_value": float(result.p),
        "significant": bool(result.h),
        "trend_label": str(result.trend),
    }


# ---- Seasonality (STL) -----------------------------------------------------


def detect_seasonality(
    values,
    period: int | None,
    threshold: float = _SEASONAL_STRENGTH_THRESHOLD,
) -> dict | None:
    """STL seasonal-strength. Returns ``None`` for irregular cadence
    (``period is None``) or short series."""
    if period is None:
        return None
    arr = np.asarray(values, dtype=float)
    # Short-series guard (ADR-208 post-R4 CRITICAL-T13).
    if arr.size < 2 * period + 1:
        return None
    stl = STL(arr, period=period).fit()
    seasonal = stl.seasonal
    resid = stl.resid
    var_resid = float(np.var(resid))
    var_combined = float(np.var(seasonal + resid))
    if var_combined == 0:
        strength = 0.0
    else:
        strength = max(0.0, 1.0 - var_resid / var_combined)
    return {
        "method": "stl",
        "strength": round(float(strength), 4),
        "threshold": threshold,
        "significant": strength > threshold,
        "period": period,
    }


# ---- Orchestrator ----------------------------------------------------------


def analyse(
    df: pd.DataFrame,
    time_column: str,
    *,
    value_column: str | None = None,
    prefs: dict | None = None,
) -> dict | None:
    """Assemble the full ADR-201 ``time_series`` block. Returns ``None`` on
    empty input, missing time column, or fewer than 2 observations."""
    if time_column not in df.columns:
        return None
    if df.empty:
        return None
    # Ensure datetime dtype; attempt parse if object/string.
    time_series = pd.to_datetime(df[time_column], errors="coerce")
    mask = time_series.notna()
    if mask.sum() < 2:
        return None
    sorted_df = df.loc[mask].assign(_ts=time_series[mask]).sort_values("_ts")
    idx = pd.DatetimeIndex(sorted_df["_ts"])

    cadence = infer_cadence(idx)
    # Map irregular-with-detail labels back to the schema's 4-vocab.
    schema_cadence = (
        cadence["label"]
        if cadence["label"] in ("daily", "weekly", "monthly")
        else "irregular"
    )

    gap_mult = (prefs or {}).get("gap_multiplier", _GAP_MULTIPLIER_DEFAULT)
    stale_mult = (prefs or {}).get("stale_multiplier", _STALE_MULTIPLIER_DEFAULT)
    gaps = detect_gaps(idx, multiplier=gap_mult)
    stale = detect_stale(
        idx,
        cadence["median_gap_seconds"],
        multiplier=stale_mult,
    )

    # Value column — if supplied, run multi-window + trend + seasonality.
    alpha = (prefs or {}).get("trend_alpha", _TREND_ALPHA_DEFAULT)
    window_outliers: list[dict] = []
    trend = {
        "method": "mann-kendall",
        "alpha": alpha,
        "p_value": 1.0,
        "significant": False,
        "trend_label": "no trend",
    }
    seasonality: dict | None = None
    if value_column and value_column in sorted_df.columns:
        values_series = pd.to_numeric(sorted_df[value_column], errors="coerce").dropna()
        if not values_series.empty:
            window_outliers = multi_window_outliers(values_series)
            trend = trend_test(values_series.to_numpy(dtype=float), alpha=alpha)
            period = _CADENCE_TO_STL_PERIOD.get(schema_cadence)
            strength_threshold = (prefs or {}).get(
                "seasonal_strength_threshold", _SEASONAL_STRENGTH_THRESHOLD
            )
            seasonality = detect_seasonality(
                values_series.to_numpy(dtype=float),
                period=period,
                threshold=strength_threshold,
            )

    return {
        "time_column": time_column,
        "cadence": schema_cadence,
        "median_gap_seconds": cadence["median_gap_seconds"],
        "expected_cadence_seconds": cadence["expected_cadence_seconds"],
        "gaps": gaps,
        "stale": stale,
        "multi_window_outliers": window_outliers,
        "trend": trend,
        "seasonality": seasonality,
        "forecast": None,
    }


# ---- Forecast (ADR-209) ----------------------------------------------------


def _horizon_default_for_cadence(cadence_label: str | None) -> int:
    """Return the default horizon per ADR-209 cadence table."""
    if cadence_label == "daily":
        return _HORIZON_DAILY
    if cadence_label == "weekly":
        return _HORIZON_WEEKLY
    if cadence_label == "monthly":
        return _HORIZON_MONTHLY
    return _HORIZON_DEFAULT


def _require_sub_seed(sub_seeds: dict, key: str) -> int:
    try:
        return int(sub_seeds[key])
    except KeyError as exc:
        raise KeyError(
            f"sub_seeds missing required key {key!r}; expected keys from "
            "provenance.sub_seeds (see ADR-202)."
        ) from exc


def _future_timestamps(index: pd.DatetimeIndex, horizon: int) -> pd.DatetimeIndex:
    """Project ``horizon`` future timestamps spaced by the median gap of ``index``."""
    if len(index) < 2:
        raise ValueError("need at least 2 timestamps to project future cadence")
    sorted_idx = index.sort_values()
    gaps = sorted_idx.to_series().diff().dt.total_seconds().dropna().to_numpy()
    median_gap = float(np.median(gaps))
    last = sorted_idx[-1]
    delta = timedelta(seconds=median_gap)
    return pd.DatetimeIndex([last + delta * (i + 1) for i in range(horizon)])


def _bootstrap_pi_from_residuals(
    point: np.ndarray, residuals: np.ndarray, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    """Generate (lower, upper) PI arrays via residual bootstrap.

    Efron: resample the residual series with replacement and add to the
    point forecasts; the 2.5 / 97.5 percentiles of the resampled forecasts
    are the prediction-interval bounds.
    """
    h = point.shape[0]
    if residuals.size == 0:
        return point.copy(), point.copy()
    draws = rng.choice(residuals, size=(_FORECAST_BOOTSTRAP_N, h), replace=True)
    samples = point[np.newaxis, :] + draws  # shape (B, h)
    lower = np.quantile(samples, _FORECAST_PI_LO, axis=0)
    upper = np.quantile(samples, _FORECAST_PI_HI, axis=0)
    # Ensure the point forecast sits inside the PI — heavily skewed residuals
    # can push both bounds to one side of `point`, which violates the
    # documented lower ≤ value ≤ upper renderer contract.
    lower = np.minimum(lower, point)
    upper = np.maximum(upper, point)
    return lower, upper


def _forecast_linear(
    values: np.ndarray, horizon: int, seed: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = values.shape[0]
    x = np.arange(n, dtype=float)
    slope, intercept = np.polyfit(x, values, 1)
    fitted = slope * x + intercept
    residuals = values - fitted
    future_x = np.arange(n, n + horizon, dtype=float)
    point = slope * future_x + intercept
    rng = np.random.default_rng(seed)
    lower, upper = _bootstrap_pi_from_residuals(point, residuals, rng)
    return point, lower, upper


def _forecast_arima(
    values: np.ndarray, horizon: int, seed: int, warnings_out: list[str]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    from statsmodels.tsa.arima.model import ARIMA

    try:
        import pmdarima  # type: ignore

        auto = pmdarima.auto_arima(values, seasonal=False, suppress_warnings=True)
        order = auto.order
    except ImportError:
        order = _ARIMA_DEFAULT_ORDER
        warnings_out.append(
            "pmdarima not installed — used default ARIMA(1,1,1) order; "
            "install pmdarima for auto-order selection."
        )

    # statsmodels ARIMA optimiser may consume numpy's legacy global RNG
    # for start-parameter jitter. Re-seed immediately before `.fit()` so
    # repeated / interleaved calls are reproducible; do NOT leave stale
    # global state between methods.
    np.random.seed(seed)  # noqa: NPY002 — statsmodels requires the global RNG
    model = ARIMA(values, order=order).fit()
    fc = model.get_forecast(steps=horizon)
    point = np.asarray(fc.predicted_mean, dtype=float)
    # Select lower/upper by column label when a DataFrame is returned (newer
    # statsmodels); fall back to positional when the API yields an ndarray.
    ci_obj = fc.conf_int(alpha=0.05)
    if isinstance(ci_obj, pd.DataFrame):
        lower_col = next(
            (c for c in ci_obj.columns if str(c).lower().startswith("lower")),
            ci_obj.columns[0],
        )
        upper_col = next(
            (c for c in ci_obj.columns if str(c).lower().startswith("upper")),
            ci_obj.columns[1],
        )
        lower = np.asarray(ci_obj[lower_col], dtype=float)
        upper = np.asarray(ci_obj[upper_col], dtype=float)
    else:
        ci_arr = np.asarray(ci_obj, dtype=float)
        lower = ci_arr[:, 0]
        upper = ci_arr[:, 1]
    return point, lower, upper


def _forecast_exp_smoothing(
    values: np.ndarray,
    horizon: int,
    seed: int,
    cadence_label: str | None,
    warnings_out: list[str],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    import warnings as _warnings

    from statsmodels.tools.sm_exceptions import ConvergenceWarning
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    period = _CADENCE_TO_ES_PERIOD.get(cadence_label or "")

    fit_seasonal = period is not None and values.shape[0] >= 2 * period
    model = None
    if fit_seasonal:
        # Re-seed immediately before the fit so the fallback path below
        # cannot inherit partial RNG consumption from the failed attempt.
        np.random.seed(seed)  # noqa: NPY002 — statsmodels optimiser may use global RNG
        try:
            with _warnings.catch_warnings():
                _warnings.simplefilter("error", ConvergenceWarning)
                model = ExponentialSmoothing(
                    values,
                    trend="add",
                    damped_trend=False,
                    seasonal="add",
                    seasonal_periods=period,
                ).fit()
        except (ConvergenceWarning, ValueError, np.linalg.LinAlgError) as exc:
            warnings_out.append(
                f"Holt-Winters seasonal fit failed ({type(exc).__name__}); "
                "falling back to non-seasonal trend-only."
            )
            model = None
    if model is None:
        np.random.seed(seed)  # noqa: NPY002 — independent, deterministic start for the fallback
        model = ExponentialSmoothing(
            values, trend="add", damped_trend=False, seasonal=None
        ).fit()

    point = np.asarray(model.forecast(steps=horizon), dtype=float)
    # PI via residual bootstrap (statsmodels PI API varies across configs).
    fitted = np.asarray(model.fittedvalues, dtype=float)
    residuals = values - fitted
    # Drop any non-finite residuals (ES fit may leave NaNs on the first few obs)
    residuals = residuals[np.isfinite(residuals)]
    rng = np.random.default_rng(seed)
    lower, upper = _bootstrap_pi_from_residuals(point, residuals, rng)
    return point, lower, upper


def forecast(
    series: pd.Series,
    method: str,
    horizon: int | None = None,
    *,
    sub_seeds: dict[str, int],
    cadence_label: str | None = None,
) -> dict:
    """Produce an ADR-201 ``forecast`` block for ``series``.

    ``series`` must have a sorted ``DatetimeIndex``. ``method`` is one of
    ``linear`` / ``arima`` / ``exponential_smoothing``. ``horizon`` defaults
    to the ADR-209 table (7 daily / 4 weekly / 12 monthly / 10 other).
    ``sub_seeds`` is caller-supplied per ADR-202 / ADR-209 (the forecast
    pass MUST NOT re-derive sub-seeds — see the ``--forecast-only``
    reproducibility rule).
    """
    if method not in _VALID_FORECAST_METHODS:
        raise ValueError(
            f"unknown forecast method {method!r}; expected one of "
            f"{_VALID_FORECAST_METHODS}"
        )
    if not isinstance(series.index, pd.DatetimeIndex):
        raise TypeError("series.index must be a DatetimeIndex for forecast")
    if series.empty:
        raise ValueError("series is empty — cannot forecast")

    values = series.astype(float).to_numpy()
    if horizon is None:
        horizon = _horizon_default_for_cadence(cadence_label)
    if horizon <= 0:
        raise ValueError(f"horizon must be positive, got {horizon}")

    future_ts = _future_timestamps(series.index, horizon)
    warnings_out: list[str] = []

    if method == "linear":
        seed = _require_sub_seed(sub_seeds, "forecast_linear_bootstrap")
        point, lower, upper = _forecast_linear(values, horizon, seed)
    elif method == "arima":
        seed = _require_sub_seed(sub_seeds, "forecast_arima_init")
        point, lower, upper = _forecast_arima(values, horizon, seed, warnings_out)
    else:  # exponential_smoothing
        seed = _require_sub_seed(sub_seeds, "forecast_exp_smoothing_init")
        point, lower, upper = _forecast_exp_smoothing(
            values, horizon, seed, cadence_label, warnings_out
        )

    predictions = []
    for i in range(horizon):
        predictions.append(
            {
                "ts": future_ts[i].isoformat(),
                "value": float(point[i]),
                "lower": float(lower[i]),
                "upper": float(upper[i]),
            }
        )

    return {
        "method": method,
        "horizon_steps": horizon,
        "predictions": predictions,
        "warnings": warnings_out,
    }
