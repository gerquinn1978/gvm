"""Multi-method outlier detection (P4-C01, AN-14 / ADR-205).

Four methods flag anomalous values at the (row, column) level. The agreement
matrix reports every flagged cell with the set of methods that flagged it and
a confidence label derived from that set size.

| Method                  | When it runs | Expert basis                   |
|-------------------------|--------------|--------------------------------|
| IQR fence (k = 1.5)     | always       | Tukey, EDA                     |
| Modified z / MAD (3.5)  | always       | Iglewicz & Hoaglin             |
| IsolationForest         | n ≥ 1000     | Liu, Ting, Zhou                |
| LocalOutlierFactor      | n ≥ 1000     | Breunig, Kriegel, Ng, Sander   |

**Per-column application of IForest/LOF.** ADR-205 says "jointly on numeric
columns" but TC-AN-14-01's BDD expects a single extreme value to be flagged
by all four methods at the (row, column) level — which is only consistent
with per-column application. This chunk runs IForest/LOF per column (each
column becomes a 1-feature 2D matrix). The joint-multivariate interpretation
would require a separate entry in the schema for row-level anomalies; it is
not present in ADR-201. Surfaced as an ambiguity for `/gvm-requirements`.

**Not in this chunk:** n ≥ 100k subsampling (ADR-205 post-R4 MEDIUM-T55).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import median_abs_deviation
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor

__all__ = ["detect"]


# ---- Thresholds (named per ADR-205) ---------------------------------------

_IQR_K = 1.5
_MAD_THRESHOLD = 3.5
_MULTIVARIATE_MIN_N = 1000
_IFOREST_N_ESTIMATORS = 100
_LOF_N_NEIGHBORS = 20
_MAD_SCALE = 0.6745  # Iglewicz & Hoaglin modified-z numerator constant.


_EMPTY_RESULT = {
    "by_method": {
        "iqr": [],
        "mad": [],
        "isolation_forest": None,
        "local_outlier_factor": None,
    },
    "agreement_matrix": [],
    "agreement_summary": {"high": 0, "review": 0, "low": 0},
}


def detect(df: pd.DataFrame, *, rng: np.random.Generator) -> dict:
    """Run all applicable outlier methods on every numeric column.

    Returns an ADR-201 ``outliers`` block. Non-numeric columns are ignored.
    Empty input produces the empty schema.
    """
    if not isinstance(rng, np.random.Generator):
        raise TypeError(f"rng must be numpy.random.Generator, got {type(rng).__name__}")
    if df.empty:
        return _empty()

    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not numeric_cols:
        return _empty()

    iqr_hits: list[dict] = []
    mad_hits: list[dict] = []
    iforest_hits: list[dict] = []
    lof_hits: list[dict] = []
    multivariate_ran = False

    for col in numeric_cols:
        series = df[col]
        non_null = series.dropna()
        if non_null.empty:
            continue

        iqr_hits.extend(_iqr_outliers(non_null, col))
        mad_hits.extend(_mad_outliers(non_null, col))

        if len(non_null) >= _MULTIVARIATE_MIN_N:
            iforest_hits.extend(_iforest_outliers(non_null, col, rng))
            lof_hits.extend(_lof_outliers(non_null, col))
            multivariate_ran = True

    by_method = {
        "iqr": _sorted_hits(iqr_hits),
        "mad": _sorted_hits(mad_hits),
        # `null` means "not applicable at this sample size"; `[]` means
        # "ran and found nothing". Keep them distinguishable — a consumer
        # using `is None` to detect skipped methods must not see `[]`.
        "isolation_forest": _sorted_hits(iforest_hits) if multivariate_ran else None,
        "local_outlier_factor": _sorted_hits(lof_hits) if multivariate_ran else None,
    }
    matrix, summary = _build_agreement(by_method)
    return {
        "by_method": by_method,
        "agreement_matrix": matrix,
        "agreement_summary": summary,
    }


# ---- Per-method helpers ----------------------------------------------------


def _iqr_outliers(series: pd.Series, column: str) -> list[dict]:
    q1 = float(series.quantile(0.25))
    q3 = float(series.quantile(0.75))
    iqr = q3 - q1
    if iqr == 0:
        return []
    low = q1 - _IQR_K * iqr
    high = q3 + _IQR_K * iqr
    out = []
    for idx, value in series.items():
        v = float(value)
        if v < low:
            z = (low - v) / iqr
        elif v > high:
            z = (v - high) / iqr
        else:
            continue
        out.append(
            {
                "row_index": int(idx),
                "column": column,
                "value": v,
                "z_iqr": float(z),
            }
        )
    return out


def _mad_outliers(series: pd.Series, column: str) -> list[dict]:
    arr = series.to_numpy(dtype=float)
    med = float(np.median(arr))
    mad = float(median_abs_deviation(arr, scale=1.0))
    if mad == 0:
        return []
    modified_z = _MAD_SCALE * (arr - med) / mad
    mask = np.abs(modified_z) > _MAD_THRESHOLD
    hits = []
    for pos, flag in enumerate(mask):
        if not flag:
            continue
        idx = int(series.index[pos])
        hits.append(
            {
                "row_index": idx,
                "column": column,
                "value": float(arr[pos]),
                "z_iqr": float(modified_z[pos]),
            }
        )
    return hits


def _iforest_outliers(
    series: pd.Series, column: str, rng: np.random.Generator
) -> list[dict]:
    X = series.to_numpy(dtype=float).reshape(-1, 1)
    model = IsolationForest(
        n_estimators=_IFOREST_N_ESTIMATORS,
        contamination="auto",
        random_state=int(rng.integers(0, 2**31 - 1)),
    )
    labels = model.fit_predict(X)
    return _labels_to_hits(labels, series, column)


def _lof_outliers(series: pd.Series, column: str) -> list[dict]:
    n = len(series)
    # LOF requires n_neighbors < n_samples.
    n_neighbors = min(_LOF_N_NEIGHBORS, max(2, n - 1))
    X = series.to_numpy(dtype=float).reshape(-1, 1)
    model = LocalOutlierFactor(n_neighbors=n_neighbors, contamination="auto")
    labels = model.fit_predict(X)
    return _labels_to_hits(labels, series, column)


def _labels_to_hits(labels: np.ndarray, series: pd.Series, column: str) -> list[dict]:
    out = []
    arr = series.to_numpy(dtype=float)
    for pos, label in enumerate(labels):
        if label != -1:
            continue
        out.append(
            {
                "row_index": int(series.index[pos]),
                "column": column,
                "value": float(arr[pos]),
                "z_iqr": 0.0,
            }
        )
    return out


# ---- Agreement matrix ------------------------------------------------------


def _build_agreement(
    by_method: dict[str, list[dict] | None],
) -> tuple[list[dict], dict[str, int]]:
    # Map (row_index, column) → {method: value}.
    flags: dict[tuple[int, str], dict[str, object]] = {}
    methods_available = [name for name, hits in by_method.items() if hits is not None]
    for method_name in methods_available:
        hits = by_method[method_name]
        assert hits is not None  # narrowed above
        for hit in hits:
            key = (hit["row_index"], hit["column"])
            entry = flags.setdefault(
                key,
                {"value": hit["value"], "methods": []},
            )
            entry["methods"].append(method_name)  # type: ignore[union-attr]

    all_methods = len(methods_available)  # 2 when n<1000, 4 when n>=1000

    matrix = []
    summary = {"high": 0, "review": 0, "low": 0}
    for (row_index, column), entry in flags.items():
        n_methods = len(entry["methods"])  # type: ignore[arg-type]
        if n_methods == all_methods:
            confidence = "high"
        elif n_methods == 1:
            confidence = "low"
        else:
            confidence = "review"
        matrix.append(
            {
                "row_index": row_index,
                "column": column,
                "value": entry["value"],
                "methods": sorted(entry["methods"]),  # type: ignore[arg-type]
                "confidence": confidence,
                "methodology_ref": None,
            }
        )
        summary[confidence] += 1
    matrix.sort(key=lambda e: (e["row_index"], e["column"]))
    return matrix, summary


def _sorted_hits(hits: list[dict]) -> list[dict]:
    return sorted(hits, key=lambda h: (h["row_index"], h["column"]))


def _empty() -> dict:
    import copy

    return copy.deepcopy(_EMPTY_RESULT)
