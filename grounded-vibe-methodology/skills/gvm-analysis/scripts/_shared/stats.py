"""Numeric primitives for the analysis engine (P3-C01).

Implements ADR-203 (robust-first statistics), ADR-204 (sample-size tier
dispatcher), and the bootstrap CI wrapper specified in ADR-202. This module
is numeric-only: no I/O, no provenance assembly, no findings-JSON shaping.
Callers in ``_shared/`` engine modules (missing, outliers, drivers, …) and
in the orchestration layer (``analyse.py``) assemble the higher-level
pipeline around these primitives.

Key invariants:

* Every public entry cleans NaN via :func:`_clean` before computing.
* :func:`bootstrap_ci` wraps the single sample as ``(values,)`` and reads
  ``result.confidence_interval.low/high`` — failing to do either produces
  the runtime errors documented in ADR-202 CRITICAL-T11.
* Return types at the JSON boundary are Python ``float`` / ``int`` /
  ``tuple`` — numpy scalar types propagate to ``json.dumps`` otherwise.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from enum import Enum
from typing import Any

import numpy as np
from numpy.typing import ArrayLike
from scipy import stats as scipy_stats

from _shared import constants

__all__ = [
    "Tier",
    "tier",
    "robust_stats",
    "classical_stats",
    "distribution_check",
    "bootstrap_ci",
]


# Below this n, scipy.stats.shapiro raises or is meaningless. We return a
# "test skipped" result instead of raising so callers can treat the
# distribution check as optional.
_SHAPIRO_MIN_N = 8

# Above this n, Shapiro-Wilk's p-value becomes unreliable (scipy warns). We
# switch to Anderson-Darling, which scales with large n.
_ANDERSON_THRESHOLD = 5000


class Tier(str, Enum):
    """Sample-size tier from ADR-204.

    The string values are the canonical ADR-201 ``tier`` field values that
    appear in ``findings.json``. Renderers and downstream consumers
    dispatch on these strings — do NOT rename them.
    """

    N_LT_10 = "n<10"
    N_10_29 = "n=10-29"
    N_30_99 = "n=30-99"
    N_100_PLUS = "n=100+"
    N_1000_PLUS = "n>=1000"
    N_10000_PLUS = "n>=10000"


def tier(n: int) -> Tier:
    """Return the sample-size tier for ``n`` (ADR-204).

    Every report section reads the tier from ``findings.json`` and switches
    behaviour accordingly. This dispatcher is the single point of truth
    for the threshold values.
    """
    if n < 0:
        raise ValueError(f"sample size cannot be negative: {n}")
    if n < 10:
        return Tier.N_LT_10
    if n < 30:
        return Tier.N_10_29
    if n < 100:
        return Tier.N_30_99
    if n < 1000:
        return Tier.N_100_PLUS
    if n < 10000:
        return Tier.N_1000_PLUS
    return Tier.N_10000_PLUS


def _clean(values: ArrayLike) -> np.ndarray:
    """Coerce to ``np.ndarray[float64]`` and drop NaN in one place.

    The engine feeds mixed-dtype columns (int, float, object with numeric
    coercion done upstream) so we force float64 once at the boundary and
    strip NaN consistently. Downstream routines never need to re-check for
    NaN as long as they use this helper.
    """
    arr = np.asarray(values, dtype=np.float64)
    cleaned = arr[~np.isnan(arr)]
    if cleaned.size == 0:
        raise ValueError("input contains no non-NaN values")
    return cleaned


def robust_stats(values: ArrayLike) -> dict[str, float]:
    """Return median, MAD (normal-scaled), IQR, Q1, Q3, count (ADR-203).

    MAD uses ``scale="normal"`` (1.4826× factor) so it is a consistent
    estimator of the population SD under normality — Iglewicz & Hoaglin's
    modified z-score (used by the downstream outlier detector) depends on
    this scaling. Callers that want "raw" MAD should not use this
    function.
    """
    arr = _clean(values)
    q1 = float(np.quantile(arr, 0.25))
    q3 = float(np.quantile(arr, 0.75))
    return {
        "median": float(np.median(arr)),
        "mad": float(scipy_stats.median_abs_deviation(arr, scale="normal")),
        "iqr": float(q3 - q1),
        "q1": q1,
        "q3": q3,
        "count": int(arr.size),
    }


def classical_stats(values: ArrayLike) -> dict[str, float]:
    """Return mean and sample SD (``ddof=1``) plus count.

    Callers MUST gate this behind :func:`distribution_check` — classical
    stats are only meaningful when the input passes a normality test
    (ADR-203).
    """
    arr = _clean(values)
    return {
        "mean": float(np.mean(arr)),
        "sd": float(np.std(arr, ddof=1)),
        "count": int(arr.size),
    }


def distribution_check(values: ArrayLike, *, alpha: float = 0.05) -> dict[str, Any]:
    """Test ``values`` for normality at level ``alpha`` (ADR-203).

    Returns a dict with ``test``, ``statistic``, ``p_value`` and
    ``is_normal``. Dispatches by sample size:

    * n < :data:`_SHAPIRO_MIN_N` → ``test="none"``, ``is_normal=False``,
      ``statistic=NaN``, ``p_value=None`` (skip, do not raise).
    * n < :data:`_ANDERSON_THRESHOLD` → Shapiro-Wilk. ``is_normal =
      p_value > alpha``.
    * n ≥ :data:`_ANDERSON_THRESHOLD` → Anderson-Darling via SciPy's
      ``method='interpolate'`` API (added in 1.17, default behaviour in
      1.19): the result exposes ``pvalue`` interpolated from scipy's
      pre-calculated critical-value tables. ``is_normal = pvalue > alpha``.
    """
    arr = _clean(values)
    if arr.size < _SHAPIRO_MIN_N:
        return {
            "test": "none",
            "statistic": float("nan"),
            "p_value": None,
            "is_normal": False,
        }
    if arr.size < _ANDERSON_THRESHOLD:
        result = scipy_stats.shapiro(arr)
        return {
            "test": "shapiro",
            "statistic": float(result.statistic),
            "p_value": float(result.pvalue),
            "is_normal": bool(result.pvalue > alpha),
        }
    # Anderson-Darling via the SciPy 1.17+ `method='interpolate'` API. The
    # legacy result.critical_values field will be removed in SciPy 1.19; the
    # interpolated p-value is the modern equivalent of the critical-value
    # comparison and is mathematically consistent with it at the same alpha.
    result = scipy_stats.anderson(arr, dist="norm", method="interpolate")
    return {
        "test": "anderson",
        "statistic": float(result.statistic),
        "p_value": float(result.pvalue),
        "is_normal": bool(result.pvalue > alpha),
    }


def bootstrap_ci(
    values: ArrayLike,
    statistic: Callable[..., Any],
    *,
    rng: np.random.Generator,
    n_iter: int = constants.BOOTSTRAP_N_ITER,
    confidence: float = constants.BOOTSTRAP_CONFIDENCE,
) -> tuple[float, float]:
    """BCa bootstrap CI for ``statistic(values)`` (ADR-202, AN-11).

    Same input + same ``rng`` seed → byte-identical interval (ASR-3). The
    call shape is verbatim from ADR-202 — the data argument is wrapped as
    ``(values,)`` (scipy requires a sequence of samples), ``method="BCa"``,
    and the return unpacks ``confidence_interval.low`` /
    ``confidence_interval.high`` with a Python ``float`` cast so the pair
    is JSON-safe at the boundary.

    Passes through a :class:`numpy.random.Generator` — parallel workers
    construct their own Generator from an int sub-seed
    (``provenance.derive_sub_seeds``) rather than sharing a parent
    Generator across processes (Generators are not picklable).
    """
    arr = _clean(values)
    result = scipy_stats.bootstrap(
        (arr,),
        statistic,
        n_resamples=n_iter,
        confidence_level=confidence,
        method="BCa",
        random_state=rng,
    )
    ci = result.confidence_interval
    low = float(ci.low)
    high = float(ci.high)
    # Zero-variance inputs can produce NaN CIs in BCa. Collapse to the
    # degenerate interval [point, point] so downstream JSON serialisation
    # does not have to special-case NaN. Precondition: ``statistic`` must
    # be defined on a constant-array input (``np.median``, ``np.mean``,
    # ``np.std`` all are). Statistics undefined on constant input (ratio-
    # of-deviations, coefficient-of-variation) MUST NOT be called through
    # this helper on degenerate data — gate at the caller.
    if math.isnan(low) or math.isnan(high):
        point = float(statistic(arr))
        return (point, point)
    return (low, high)
