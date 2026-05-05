"""Driver decomposition (ADR-207).

Implements ``decompose(df, target, *, rng_seed, run_shap=False)`` which ranks
features by their statistical association with ``target`` using three
methods — single-feature OLS R² (variance decomposition), Spearman partial
correlation with bootstrap CI, and Random-Forest permutation importance with
percentile CI — and assigns a top-K agreement label per feature. SHAP is
optional and informational (never enters the agreement vote).

This module enforces two fail-fast guards before any computation:

* :class:`ColumnNotFoundError` if ``target`` is not a column.
* :class:`ZeroVarianceTargetError` if ``target`` has zero variance after NaN
  drop.

Reproducibility flows from ``rng_seed`` through pre-derived sub-seeds for RF
fit, RF permutation, and partial-correlation bootstrap (per ADR-202).
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression

from _shared.diagnostics import ColumnNotFoundError, ZeroVarianceTargetError


# Module constants (ADR-207 defaults)
_DRIVER_K_FLOOR = 5
_DRIVER_K_FRACTION = 0.10
_PARTIAL_CORR_BOOTSTRAP_N = 200
_RF_N_ESTIMATORS = 200
_RF_PERM_N_REPEATS = 100
_ONEHOT_MAX_CARDINALITY = 20
_CI_LOW = 0.025
_CI_HIGH = 0.975

_CAUSATION_DISCLAIMER = (
    "These rankings reflect statistical associations between features and "
    "the target, not causal relationships. A high-ranked driver is "
    "correlated with the target conditional on the other features in the "
    "analysis. Establishing causation requires interventional studies that "
    "are out of scope for this report (Gelman, Data Analysis Using "
    "Regression and Multilevel/Hierarchical Models)."
)

_K_RULE = "max(5, ceil(0.10 * num_features))"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def decompose(
    df: pd.DataFrame,
    target: str,
    *,
    rng_seed: int,
    sub_seeds: dict[str, int] | None = None,
    run_shap: bool = False,
) -> dict[str, Any]:
    """Run the three-method driver decomposition for ``target``.

    Returns the ADR-201 ``drivers`` block (minus ``methodology_ref`` which
    the methodology registry populates downstream).

    ``sub_seeds`` is optional: when supplied (per ADR-202 pre-derivation),
    the caller passes the already-derived ``drivers_rf``, ``drivers_rf_perm``,
    and ``drivers_partial_corr`` integers and these are used verbatim. When
    omitted, sub-seeds are derived locally from ``rng_seed`` in a fixed
    order — this is a reproducible fallback for standalone callers (tests,
    ad-hoc scripts). The orchestrator (analyse.py) SHOULD pass pre-derived
    values so the provenance-recorded sub-seeds match what is actually used.
    """

    if target not in df.columns:
        raise ColumnNotFoundError(target, tuple(df.columns))

    y_full = df[target]
    mask = y_full.notna()
    df_clean = df.loc[mask].reset_index(drop=True)
    y = df_clean[target].astype(float).to_numpy()

    if y.size == 0 or float(np.var(y)) == 0.0:
        raise ZeroVarianceTargetError(target)

    feature_cols = [c for c in df_clean.columns if c != target]
    dropped_features: list[str] = []

    # Identify feature types
    kept_features: list[str] = []
    for col in feature_cols:
        series = df_clean[col]
        if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(
            series
        ):
            kept_features.append(col)
        else:
            # Treat everything else as categorical
            cardinality = series.nunique(dropna=True)
            if cardinality <= _ONEHOT_MAX_CARDINALITY:
                kept_features.append(col)
            else:
                dropped_features.append(col)

    num_features = len(kept_features)
    K = _compute_k(num_features)

    # Resolve sub-seeds: caller-supplied values take precedence (ADR-202),
    # otherwise derive locally from the master seed for standalone callers.
    if sub_seeds is not None:
        try:
            seeds = {
                "drivers_rf": int(sub_seeds["drivers_rf"]),
                "drivers_rf_perm": int(sub_seeds["drivers_rf_perm"]),
                "drivers_partial_corr": int(sub_seeds["drivers_partial_corr"]),
            }
        except KeyError as exc:
            raise KeyError(
                f"sub_seeds missing required key: {exc}. Expected keys: "
                "drivers_rf, drivers_rf_perm, drivers_partial_corr."
            ) from exc
    else:
        rng = np.random.default_rng(rng_seed)
        seeds = {
            "drivers_rf": int(rng.integers(0, 2**31 - 1)),
            "drivers_rf_perm": int(rng.integers(0, 2**31 - 1)),
            "drivers_partial_corr": int(rng.integers(0, 2**31 - 1)),
        }

    # Build feature matrices
    X_ols_dict = _build_feature_matrix(df_clean, kept_features, drop_first=True)
    X_full_dict = _build_feature_matrix(df_clean, kept_features, drop_first=False)

    # ----- Variance decomposition: per-feature OLS R² -----
    variance_rows = _variance_decomposition(X_ols_dict, y)

    # ----- Partial correlation (Spearman) -----
    partial_rows = _partial_correlation(
        X_full_dict, y, seed=seeds["drivers_partial_corr"]
    )

    # ----- RF importance via permutation -----
    rf_rows, rf_model, X_rf_flat, rf_feature_owners = _rf_importance(
        X_full_dict,
        y,
        seed_fit=seeds["drivers_rf"],
        seed_perm=seeds["drivers_rf_perm"],
    )

    # ----- SHAP (optional) -----
    shap_rows: list[dict[str, Any]] | None = None
    shap_warnings: list[str] = []
    if run_shap:
        shap_rows, shap_warnings = _shap_values(rf_model, X_rf_flat, rf_feature_owners)

    # ----- Agreement (top-K across 3 methods) -----
    agreement = _build_agreement(
        features=kept_features,
        variance_rows=variance_rows,
        partial_rows=partial_rows,
        rf_rows=rf_rows,
        K=K,
    )

    return {
        "target": target,
        "K": K,
        "K_rule": _K_RULE,
        "causation_disclaimer": _CAUSATION_DISCLAIMER,
        "method_results": {
            "variance_decomposition": variance_rows,
            "partial_correlation": partial_rows,
            "rf_importance": rf_rows,
            "shap": shap_rows,
        },
        "agreement": agreement,
        "dropped_features": dropped_features,
        "shap_warnings": shap_warnings,
    }


# ---------------------------------------------------------------------------
# K and label helpers
# ---------------------------------------------------------------------------


def _compute_k(num_features: int) -> int:
    return max(_DRIVER_K_FLOOR, math.ceil(_DRIVER_K_FRACTION * num_features))


def _label_for(agreement_count: int) -> str:
    if agreement_count == 3:
        return "high-confidence"
    if agreement_count == 2:
        return "review"
    if agreement_count == 1:
        return "low-confidence"
    return "not-reported"


# ---------------------------------------------------------------------------
# Feature-matrix construction
# ---------------------------------------------------------------------------


def _build_feature_matrix(
    df: pd.DataFrame,
    features: list[str],
    *,
    drop_first: bool,
) -> dict[str, np.ndarray]:
    """Return ``{feature_name: 2-D ndarray (n, n_cols)}`` per original feature.

    Numeric features map to an (n, 1) column. Categorical features (cardinality
    ≤ _ONEHOT_MAX_CARDINALITY) one-hot expand with ``pd.get_dummies(drop_first=...)``.
    """
    out: dict[str, np.ndarray] = {}
    for col in features:
        series = df[col]
        if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(
            series
        ):
            values = series.astype(float).fillna(series.astype(float).mean()).to_numpy()
            out[col] = values.reshape(-1, 1)
        else:
            dummies = pd.get_dummies(series.astype(str), drop_first=drop_first)
            out[col] = dummies.to_numpy(dtype=float)
    return out


def _concat_features(matrix: dict[str, np.ndarray]) -> tuple[np.ndarray, list[str]]:
    """Flatten the per-feature matrix into a single (n, total_cols) array.

    Returns ``(X, owners)`` where ``owners[i]`` is the ORIGINAL feature name
    that column ``i`` belongs to — used to sum importances back to the
    original feature for one-hot-encoded categoricals.
    """
    if not matrix:
        return np.empty((0, 0)), []
    blocks: list[np.ndarray] = []
    owners: list[str] = []
    for feat, arr in matrix.items():
        blocks.append(arr)
        owners.extend([feat] * arr.shape[1])
    X = np.hstack(blocks) if blocks else np.empty((0, 0))
    return X, owners


# ---------------------------------------------------------------------------
# Variance decomposition: per-feature OLS R²
# ---------------------------------------------------------------------------


def _variance_decomposition(
    matrix: dict[str, np.ndarray], y: np.ndarray
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if y.size < 2 or float(np.var(y)) == 0.0:
        return rows
    for feat, X_feat in matrix.items():
        if X_feat.size == 0 or X_feat.shape[0] != y.shape[0]:
            r2 = 0.0
        else:
            # Guard degenerate feature (constant column after encoding)
            if np.all(np.var(X_feat, axis=0) == 0):
                r2 = 0.0
            else:
                model = LinearRegression().fit(X_feat, y)
                r2 = float(model.score(X_feat, y))
                # R² can be negative for poorly-fit models; ADR-201 requires [0,1]
                if r2 < 0.0:
                    r2 = 0.0
        rows.append({"feature": feat, "variance_explained": r2})

    rows.sort(key=lambda r: r["variance_explained"], reverse=True)
    for i, r in enumerate(rows, start=1):
        r["rank"] = i
    # Re-order keys to canonical {feature, rank, variance_explained}
    return [
        {
            "feature": r["feature"],
            "rank": r["rank"],
            "variance_explained": r["variance_explained"],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Spearman partial correlation with bootstrap CI
# ---------------------------------------------------------------------------


def _spearman_partial_one(
    target_rank: np.ndarray,
    x_rank: np.ndarray,
    others_rank: np.ndarray,
) -> float:
    """Return the Spearman partial correlation of ``x`` with target,
    controlling for ``others`` (all inputs are already rank-transformed).
    """
    if others_rank.size == 0:
        # No controls — reduces to plain Spearman correlation
        return _safe_pearson(x_rank, target_rank)
    # Residualise x and y on others (pre-rank-transformed)
    # sklearn.LinearRegression handles the intercept for us.
    x_resid = x_rank - LinearRegression().fit(others_rank, x_rank).predict(others_rank)
    y_resid = target_rank - LinearRegression().fit(others_rank, target_rank).predict(
        others_rank
    )
    return _safe_pearson(x_resid, y_resid)


def _safe_pearson(a: np.ndarray, b: np.ndarray) -> float:
    if a.size < 2:
        return 0.0
    sa = float(np.std(a))
    sb = float(np.std(b))
    if sa == 0.0 or sb == 0.0:
        return 0.0
    corr = float(np.corrcoef(a, b)[0, 1])
    if math.isnan(corr):
        return 0.0
    return corr


def _partial_correlation(
    matrix: dict[str, np.ndarray], y: np.ndarray, *, seed: int
) -> list[dict[str, Any]]:
    # Flatten to a single X matrix; each feature owns ≥ 1 column.
    X, owners = _concat_features(matrix)
    if X.size == 0:
        return []
    # Rank-transform once (Spearman = Pearson on ranks)
    X_rank = np.apply_along_axis(rankdata, 0, X).astype(float)
    y_rank = rankdata(y).astype(float)

    # Per-original-feature partial correlation
    feature_to_cols: dict[str, list[int]] = {}
    for i, owner in enumerate(owners):
        feature_to_cols.setdefault(owner, []).append(i)

    rows: list[dict[str, Any]] = []
    feature_order = list(feature_to_cols.keys())

    # Pre-sample bootstrap indices from the seeded RNG for determinism
    rng = np.random.default_rng(seed)
    n = X.shape[0]
    boot_indices = [
        rng.integers(0, n, size=n) for _ in range(_PARTIAL_CORR_BOOTSTRAP_N)
    ]

    for feat in feature_order:
        cols = feature_to_cols[feat]
        x_cols = X_rank[:, cols]
        other_cols_idx = [j for j in range(X_rank.shape[1]) if j not in set(cols)]
        others = X_rank[:, other_cols_idx]

        # For multi-column features (one-hot), aggregate by taking max |corr|
        # across the one-hot columns — a common convention for categorical
        # feature strength.
        def _coef_for_indices(idx: np.ndarray) -> float:
            best = 0.0
            y_sel = y_rank[idx]
            others_sel = others[idx]
            for k in range(x_cols.shape[1]):
                c = _spearman_partial_one(y_sel, x_cols[idx, k], others_sel)
                if abs(c) > abs(best):
                    best = c
            return best

        point = _coef_for_indices(np.arange(n))
        boots = np.array([_coef_for_indices(idx) for idx in boot_indices])
        ci_lo = float(np.quantile(boots, _CI_LOW))
        ci_hi = float(np.quantile(boots, _CI_HIGH))
        rows.append(
            {
                "feature": feat,
                "coefficient": float(point),
                "ci_95": [ci_lo, ci_hi],
            }
        )

    rows.sort(key=lambda r: abs(r["coefficient"]), reverse=True)
    for i, r in enumerate(rows, start=1):
        r["rank"] = i
    return [
        {
            "feature": r["feature"],
            "rank": r["rank"],
            "coefficient": r["coefficient"],
            "ci_95": r["ci_95"],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# RF permutation importance
# ---------------------------------------------------------------------------


def _rf_importance(
    matrix: dict[str, np.ndarray],
    y: np.ndarray,
    *,
    seed_fit: int,
    seed_perm: int,
) -> tuple[list[dict[str, Any]], RandomForestRegressor, np.ndarray, list[str]]:
    X, owners = _concat_features(matrix)
    if X.size == 0:
        rf_empty = RandomForestRegressor(
            n_estimators=_RF_N_ESTIMATORS, random_state=seed_fit
        )
        return [], rf_empty, X, owners

    rf = RandomForestRegressor(n_estimators=_RF_N_ESTIMATORS, random_state=seed_fit)
    rf.fit(X, y)
    perm = permutation_importance(
        rf, X, y, n_repeats=_RF_PERM_N_REPEATS, random_state=seed_perm
    )
    # perm.importances has shape [n_features, n_repeats].
    # Per-column CI is NOT computed here: after summing to the original
    # feature, the CI is derived from the summed per-repeat vector — that
    # is the CI that makes it into findings.json.
    per_col = [
        {
            "owner": owners[i],
            "importances": perm.importances[i],  # length n_repeats
        }
        for i in range(len(owners))
    ]

    # Sum importances back to the ORIGINAL feature (one-hot-encoded columns
    # collapse to their parent categorical). ADR-207 specifies summing the
    # importances across the repeats-per-column before computing the CI.
    by_feature: dict[str, np.ndarray] = {}
    for entry in per_col:
        arr = entry["importances"]
        if entry["owner"] in by_feature:
            by_feature[entry["owner"]] = by_feature[entry["owner"]] + arr
        else:
            by_feature[entry["owner"]] = arr.copy()

    rows: list[dict[str, Any]] = []
    for feat, importances in by_feature.items():
        mean = float(np.mean(importances))
        lo = float(np.quantile(importances, _CI_LOW))
        hi = float(np.quantile(importances, _CI_HIGH))
        rows.append(
            {
                "feature": feat,
                "importance_mean": mean,
                "importance_ci_95": [lo, hi],
            }
        )

    rows.sort(key=lambda r: r["importance_mean"], reverse=True)
    for i, r in enumerate(rows, start=1):
        r["rank"] = i
    return (
        [
            {
                "feature": r["feature"],
                "rank": r["rank"],
                "importance_mean": r["importance_mean"],
                "importance_ci_95": r["importance_ci_95"],
            }
            for r in rows
        ],
        rf,
        X,
        owners,
    )


# ---------------------------------------------------------------------------
# SHAP (optional)
# ---------------------------------------------------------------------------


def _shap_values(
    rf: RandomForestRegressor,
    X: np.ndarray,
    owners: list[str],
) -> tuple[list[dict[str, Any]] | None, list[str]]:
    """Return SHAP per-feature mean(|shap|) list, or None on failure."""
    warnings: list[str] = []
    try:
        import shap  # type: ignore
    except ImportError as exc:
        warnings.append(f"SHAP skipped: shap not installed ({exc})")
        return None, warnings

    try:
        explainer = shap.TreeExplainer(rf, feature_perturbation="tree_path_dependent")
        shap_values = explainer.shap_values(X)
    except (ValueError, TypeError) as exc:
        warnings.append(f"SHAP skipped: {exc}")
        return None, warnings

    per_col = np.abs(shap_values).mean(axis=0)
    by_feature: dict[str, float] = {}
    for i, owner in enumerate(owners):
        by_feature[owner] = by_feature.get(owner, 0.0) + float(per_col[i])

    rows = [{"feature": feat, "mean_abs_shap": val} for feat, val in by_feature.items()]
    rows.sort(key=lambda r: r["mean_abs_shap"], reverse=True)
    return rows, warnings


# ---------------------------------------------------------------------------
# Agreement vector
# ---------------------------------------------------------------------------


def _build_agreement(
    *,
    features: list[str],
    variance_rows: list[dict[str, Any]],
    partial_rows: list[dict[str, Any]],
    rf_rows: list[dict[str, Any]],
    K: int,
) -> list[dict[str, Any]]:
    def _top_k(rows: list[dict[str, Any]]) -> set[str]:
        return {r["feature"] for r in rows[:K]}

    variance_top = _top_k(variance_rows)
    partial_top = _top_k(partial_rows)
    rf_top = _top_k(rf_rows)

    agreement: list[dict[str, Any]] = []
    for feat in features:
        in_top = []
        if feat in variance_top:
            in_top.append("variance_decomposition")
        if feat in partial_top:
            in_top.append("partial_correlation")
        if feat in rf_top:
            in_top.append("rf_importance")
        agreement.append(
            {
                "feature": feat,
                "in_top_k": in_top,
                "label": _label_for(len(in_top)),
                "methodology_ref": None,
            }
        )
    return agreement
