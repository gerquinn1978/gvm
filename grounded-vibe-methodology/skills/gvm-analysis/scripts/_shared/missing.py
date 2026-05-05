"""Per-column completeness and Rubin missing-data classification (P3-C02).

Implements ADR-206 (classification with explicit basis) and AN-15 (TC-AN-15-01..05).
This module is stateless and numeric-only — it consumes a ``pandas.DataFrame``
already loaded by ``_shared/io.py`` and returns the structures assembled by
the pipeline into the ``columns[*].missingness_classification`` field of
``findings.json`` (ADR-201 §Schema).

The classifier never raises on data-shape issues: sample-size guards and an
all-null guard produce ``indeterminate`` labels with a plain-language basis
so the renderer can surface uncertainty instead of failing silently.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from scipy.stats.contingency import association as cramer_association

__all__ = ["classify", "completeness"]


# Sample-size guards (ADR-206 step 1).
_MIN_MISSING_FOR_TESTS = 5
_MIN_TOTAL_FOR_TESTS = 30

# Correlation thresholds (ADR-206 steps 2 and 3).
_MAR_COLUMN_THRESHOLD = 0.4
_MAR_ORDER_THRESHOLD = 0.3

# MNAR skew rule (ADR-206 step 4).
_MNAR_IQR_MULTIPLIER = 2.0
# Minimum non-null sample size for a stable IQR estimate. ADR-206 does not
# pin this explicitly; 20 observations give a reasonable quartile estimate
# while still allowing the MNAR skew check to fire on moderately-missing
# columns.
_MNAR_MIN_OBSERVED = 20


def completeness(df: pd.DataFrame, column: str) -> dict:
    """Return per-column completeness fields for ADR-201 ``columns[*]``.

    ``completeness_pct`` is ``100 * n_non_null / n_total`` and defaults to
    ``0.0`` for an empty frame so the JSON stays numeric at the boundary.
    """
    series = df[column]
    n_total = int(series.size)
    n_non_null = int(series.notna().sum())
    if n_total == 0:
        pct = 0.0
    else:
        pct = 100.0 * n_non_null / n_total
    return {
        "n_total": n_total,
        "n_non_null": n_non_null,
        "completeness_pct": float(pct),
    }


def classify(
    df: pd.DataFrame,
    column: str,
    *,
    rng: np.random.Generator | None = None,  # noqa: ARG001 — kept for API symmetry with stats.bootstrap_ci
) -> dict:
    """Classify missingness for ``df[column]`` per ADR-206.

    Returns a dict with ``label`` ∈ {MCAR, MAR, possibly MNAR, indeterminate},
    ``basis`` (plain-language explanation naming the statistic and correlate
    where applicable), and ``confidence`` ∈ {high, medium, low}.
    """
    series = df[column]
    n_total = int(series.size)
    mask = series.isna()
    n_missing = int(mask.sum())

    # --- Degenerate + sample-size guards (ADR-206 step 1) ---
    if n_total - n_missing == 0:
        return {
            "label": "indeterminate",
            "basis": "column is entirely null",
            "confidence": "low",
        }
    if n_missing == 0:
        return {
            "label": "MCAR",
            "basis": "no missing values in column",
            "confidence": "medium",
        }
    if n_missing < _MIN_MISSING_FOR_TESTS or n_total < _MIN_TOTAL_FOR_TESTS:
        return {
            "label": "indeterminate",
            "basis": "sample too small to test for MAR/MNAR signals",
            "confidence": "low",
        }

    mask_arr = mask.to_numpy().astype(int)

    # --- Step 2: MAR against other columns ---
    mar_result = _test_mar_against_columns(df, column, mask_arr)
    if mar_result is not None:
        return mar_result

    # --- Step 3: MAR against row order ---
    rho_order = _spearman_safe(mask_arr, np.arange(n_total))
    if abs(rho_order) >= _MAR_ORDER_THRESHOLD:
        return {
            "label": "MAR",
            "basis": f"missingness correlates with row order at Spearman rho = {rho_order:.2f}",
            "confidence": "high",
        }

    # --- Step 4: MNAR skew check ---
    observed = series.dropna().to_numpy(dtype=float)
    mnar = _test_mnar_skew(observed)
    if mnar is not None:
        return mnar

    # --- Step 5: MCAR fallback ---
    return {
        "label": "MCAR",
        "basis": "no significant correlation with other columns or row order",
        "confidence": "medium",
    }


def _test_mar_against_columns(
    df: pd.DataFrame, target_column: str, mask: np.ndarray
) -> dict | None:
    """Return a MAR classification dict or None if no column exceeds threshold.

    Picks the strongest correlate across all other columns and names it in
    the basis string. Thresholds and per-type statistics follow ADR-206.
    """
    best: tuple[float, str, str] | None = None  # (abs_value, column, basis)
    for other in df.columns:
        if other == target_column:
            continue
        series = df[other]
        stat_value, stat_name = _association(mask, series)
        if stat_value is None or math.isnan(stat_value):
            continue
        if abs(stat_value) >= _MAR_COLUMN_THRESHOLD:
            basis = (
                f"missingness correlates with {other} at {stat_name} = {stat_value:.2f}"
            )
            candidate = (abs(stat_value), other, basis)
            if best is None or candidate[0] > best[0]:
                best = candidate
    if best is None:
        return None
    return {"label": "MAR", "basis": best[2], "confidence": "high"}


def _association(mask: np.ndarray, other: pd.Series) -> tuple[float | None, str]:
    """Compute the appropriate association between the missingness mask and ``other``.

    Dispatches on ``other``'s dtype:
    - Numeric continuous → point-biserial
    - Ordinal (pandas CategoricalDtype with ``ordered=True``) → Spearman ρ
    - Categorical with ≤2 unique values → φ
    - Categorical with 3+ unique values → Cramér's V

    Returns ``(value, statistic_name)`` or ``(None, "")`` when the statistic
    is undefined (e.g., the other column is constant or all-NaN).
    """
    # Drop rows where ``other`` itself is NaN — correlations on NaN propagate.
    valid = other.notna().to_numpy()
    if valid.sum() < _MIN_MISSING_FOR_TESTS:
        return None, ""
    other_valid = other[valid]
    mask_valid = mask[valid]

    # Ordinal check (must precede the generic categorical branch).
    if isinstance(other_valid.dtype, pd.CategoricalDtype) and other_valid.dtype.ordered:
        codes = other_valid.cat.codes.to_numpy()
        return _spearman_safe(mask_valid, codes), "Spearman rho"

    # Binary-valued columns use φ regardless of storage dtype — a 0/1 int
    # column carries no continuous information and the point-biserial
    # statistic degenerates to φ anyway. Checking unique count before the
    # numeric branch keeps the basis string ("phi") consistent with ADR-206.
    unique_nonnull = other_valid.dropna().unique()
    if len(unique_nonnull) == 2:
        phi = _phi_coefficient(mask_valid, other_valid.to_numpy())
        if phi is None or math.isnan(phi):
            return None, ""
        return phi, "phi"

    if pd.api.types.is_numeric_dtype(other_valid):
        arr = other_valid.to_numpy(dtype=float)
        if np.nanstd(arr) == 0:
            return None, ""
        try:
            result = scipy_stats.pointbiserialr(mask_valid, arr)
        except (ValueError, ZeroDivisionError):
            return None, ""
        value = float(result.statistic)
        if math.isnan(value):
            return None, ""
        return value, "point-biserial r"

    # Categorical / string / object with 3+ levels.
    n_levels = len(unique_nonnull)
    if n_levels < 2:
        return None, ""
    # Multi-level categorical → Cramér's V.
    table = pd.crosstab(pd.Series(mask_valid), other_valid.reset_index(drop=True))
    if table.shape[0] < 2 or table.shape[1] < 2:
        return None, ""
    try:
        v = float(cramer_association(table.to_numpy(), method="cramer"))
    except (ValueError, ZeroDivisionError):
        return None, ""
    if math.isnan(v):
        return None, ""
    return v, "Cramer's V"


def _phi_coefficient(mask: np.ndarray, other: np.ndarray) -> float | None:
    """Compute φ for two binary vectors (equivalent to Matthews coefficient).

    ``other`` may be any 2-level array (numeric, string, categorical); its two
    distinct values are mapped to 0/1.
    """
    uniques = pd.unique(other)
    if len(uniques) != 2:
        return None
    other_bin = (other == uniques[1]).astype(int)
    n11 = int(((mask == 1) & (other_bin == 1)).sum())
    n10 = int(((mask == 1) & (other_bin == 0)).sum())
    n01 = int(((mask == 0) & (other_bin == 1)).sum())
    n00 = int(((mask == 0) & (other_bin == 0)).sum())
    denom_sq = (n11 + n10) * (n11 + n01) * (n00 + n10) * (n00 + n01)
    if denom_sq == 0:
        return None
    return (n11 * n00 - n10 * n01) / math.sqrt(denom_sq)


def _spearman_safe(a: np.ndarray, b: np.ndarray) -> float:
    """Spearman ρ returning ``0.0`` on constant input instead of NaN."""
    if np.std(a) == 0 or np.std(b) == 0:
        return 0.0
    try:
        result = scipy_stats.spearmanr(a, b)
    except (ValueError, ZeroDivisionError):
        return 0.0
    value = float(result.statistic)
    return 0.0 if math.isnan(value) else value


def _test_mnar_skew(observed: np.ndarray) -> dict | None:
    """Apply ADR-206 step 4: |mean − median| ≥ 2 × IQR ⇒ possibly MNAR.

    ``observed`` is the non-null array. An IQR of zero or an empty slice
    returns None (no MNAR signal — the fallback branch will apply MCAR).
    """
    if observed.size < _MNAR_MIN_OBSERVED:
        return None
    q1 = float(np.quantile(observed, 0.25))
    q3 = float(np.quantile(observed, 0.75))
    iqr = q3 - q1
    if iqr == 0:
        return None
    median = float(np.median(observed))
    mean = float(np.mean(observed))
    if abs(mean - median) < _MNAR_IQR_MULTIPLIER * iqr:
        return None
    tail = "upper" if mean > median else "lower"
    return {
        "label": "possibly MNAR",
        "basis": (
            f"missingness skewed toward {tail} of observed-value distribution "
            f"(|mean - median| = {abs(mean - median):.2f}, IQR = {iqr:.2f})"
        ),
        "confidence": "medium",
    }
