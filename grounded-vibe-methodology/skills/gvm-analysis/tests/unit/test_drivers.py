"""Unit tests for `_shared/drivers.py` (ADR-207)."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from _shared import drivers
from _shared.diagnostics import ColumnNotFoundError, ZeroVarianceTargetError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_linear_df(n: int = 200, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    x1 = rng.normal(0, 1, size=n)
    x2 = rng.normal(0, 1, size=n)
    x3 = rng.normal(0, 1, size=n)
    x4 = rng.normal(0, 1, size=n)
    noise = rng.normal(0, 0.1, size=n)
    y = 0.9 * x1 + 0.05 * x2 + 0.03 * x3 + 0.02 * x4 + noise
    return pd.DataFrame({"x1": x1, "x2": x2, "x3": x3, "x4": x4, "y": y})


# ---------------------------------------------------------------------------
# Guard tests (TC-AN-23-07, TC-AN-23-06)
# ---------------------------------------------------------------------------


def test_tc_an_23_07_missing_target_raises_column_not_found():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    with pytest.raises(ColumnNotFoundError) as exc:
        drivers.decompose(df, target="y", rng_seed=42)
    assert exc.value.column == "y"
    assert set(exc.value.known_columns) == {"a", "b"}


def test_tc_an_23_06_zero_variance_target_raises():
    df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0], "y": [7.0] * 5})
    with pytest.raises(ZeroVarianceTargetError) as exc:
        drivers.decompose(df, target="y", rng_seed=42)
    assert exc.value.target == "y"


# ---------------------------------------------------------------------------
# K computation (TC-AN-23-04b)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "num_features,expected_k",
    [(5, 5), (10, 5), (50, 5), (100, 10), (500, 50)],
)
def test_tc_an_23_04b_k_boundaries(num_features: int, expected_k: int):
    assert drivers._compute_k(num_features) == expected_k


# ---------------------------------------------------------------------------
# Shape + schema (TC-AN-23-01)
# ---------------------------------------------------------------------------


def test_tc_an_23_01_all_three_methods_run():
    df = _make_linear_df()
    result = drivers.decompose(df, target="y", rng_seed=42)

    assert result["target"] == "y"
    assert result["K"] == 5
    assert result["K_rule"] == "max(5, ceil(0.10 * num_features))"
    assert isinstance(result["causation_disclaimer"], str)
    assert "associat" in result["causation_disclaimer"].lower()

    mr = result["method_results"]
    assert set(mr.keys()) == {
        "variance_decomposition",
        "partial_correlation",
        "rf_importance",
        "shap",
    }
    assert mr["shap"] is None

    for entry in mr["variance_decomposition"]:
        assert set(entry.keys()) == {"feature", "rank", "variance_explained"}
        assert isinstance(entry["variance_explained"], float)
    for entry in mr["partial_correlation"]:
        assert set(entry.keys()) == {"feature", "rank", "coefficient", "ci_95"}
        assert len(entry["ci_95"]) == 2
    for entry in mr["rf_importance"]:
        assert set(entry.keys()) == {
            "feature",
            "rank",
            "importance_mean",
            "importance_ci_95",
        }
        assert len(entry["importance_ci_95"]) == 2


def test_ranks_are_one_indexed_and_sorted():
    df = _make_linear_df()
    result = drivers.decompose(df, target="y", rng_seed=42)
    for key in ("variance_decomposition", "partial_correlation", "rf_importance"):
        ranks = [e["rank"] for e in result["method_results"][key]]
        assert ranks == list(range(1, len(ranks) + 1))


# ---------------------------------------------------------------------------
# Agreement labels (TC-AN-23-02, TC-AN-23-03)
# ---------------------------------------------------------------------------


def test_tc_an_23_02_dominant_feature_is_high_confidence():
    df = _make_linear_df()
    result = drivers.decompose(df, target="y", rng_seed=42)
    by_feature = {a["feature"]: a for a in result["agreement"]}
    assert by_feature["x1"]["label"] == "high-confidence"
    assert set(by_feature["x1"]["in_top_k"]) == {
        "variance_decomposition",
        "partial_correlation",
        "rf_importance",
    }


def test_agreement_label_mapping():
    assert drivers._label_for(3) == "high-confidence"
    assert drivers._label_for(2) == "review"
    assert drivers._label_for(1) == "low-confidence"
    assert drivers._label_for(0) == "not-reported"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_same_seed_same_output():
    df = _make_linear_df()
    r1 = drivers.decompose(df, target="y", rng_seed=42)
    r2 = drivers.decompose(df, target="y", rng_seed=42)
    # Ranks are the deterministic artifact consumers rely on
    assert [e["feature"] for e in r1["method_results"]["rf_importance"]] == [
        e["feature"] for e in r2["method_results"]["rf_importance"]
    ]
    assert [e["feature"] for e in r1["method_results"]["variance_decomposition"]] == [
        e["feature"] for e in r2["method_results"]["variance_decomposition"]
    ]


# ---------------------------------------------------------------------------
# High-cardinality categorical dropped
# ---------------------------------------------------------------------------


def test_high_cardinality_categorical_dropped():
    rng = np.random.default_rng(0)
    n = 60
    big_cat = [f"cat_{i}" for i in range(n)]  # cardinality 60 > 20
    x1 = rng.normal(0, 1, size=n)
    y = 0.9 * x1 + rng.normal(0, 0.1, size=n)
    df = pd.DataFrame({"x1": x1, "big_cat": big_cat, "y": y})
    result = drivers.decompose(df, target="y", rng_seed=42)
    features = {
        e["feature"] for e in result["method_results"]["variance_decomposition"]
    }
    assert "big_cat" not in features
    assert "x1" in features
    assert "big_cat" in result.get("dropped_features", [])


# ---------------------------------------------------------------------------
# Low-cardinality categorical handled (one-hot)
# ---------------------------------------------------------------------------


def test_low_cardinality_categorical_included():
    rng = np.random.default_rng(0)
    n = 120
    cat = rng.choice(["a", "b", "c"], size=n)
    x1 = rng.normal(0, 1, size=n)
    y = 0.8 * x1 + rng.normal(0, 0.1, size=n)
    df = pd.DataFrame({"x1": x1, "cat": cat, "y": y})
    result = drivers.decompose(df, target="y", rng_seed=42)
    features = {
        e["feature"] for e in result["method_results"]["variance_decomposition"]
    }
    assert "x1" in features
    assert "cat" in features


# ---------------------------------------------------------------------------
# Constants pinned
# ---------------------------------------------------------------------------


def test_module_constants():
    assert drivers._DRIVER_K_FLOOR == 5
    assert drivers._DRIVER_K_FRACTION == 0.10
    assert drivers._PARTIAL_CORR_BOOTSTRAP_N == 200
    assert drivers._RF_N_ESTIMATORS == 200
    assert drivers._RF_PERM_N_REPEATS == 100
    assert drivers._ONEHOT_MAX_CARDINALITY == 20


# ---------------------------------------------------------------------------
# Variance-explained is in [0,1]
# ---------------------------------------------------------------------------


def test_variance_explained_is_bounded():
    df = _make_linear_df()
    result = drivers.decompose(df, target="y", rng_seed=42)
    for entry in result["method_results"]["variance_decomposition"]:
        ve = entry["variance_explained"]
        assert 0.0 <= ve <= 1.0
        assert not math.isnan(ve)


# ---------------------------------------------------------------------------
# Partial-correlation CI order
# ---------------------------------------------------------------------------


def test_partial_correlation_ci_ordered():
    df = _make_linear_df()
    result = drivers.decompose(df, target="y", rng_seed=42)
    for entry in result["method_results"]["partial_correlation"]:
        lo, hi = entry["ci_95"]
        assert lo <= hi


# ---------------------------------------------------------------------------
# RF importance CI order and shape
# ---------------------------------------------------------------------------


def test_rf_importance_ci_ordered():
    df = _make_linear_df()
    result = drivers.decompose(df, target="y", rng_seed=42)
    for entry in result["method_results"]["rf_importance"]:
        lo, hi = entry["importance_ci_95"]
        assert lo <= hi


# ---------------------------------------------------------------------------
# Top-K agreement counts
# ---------------------------------------------------------------------------


def test_agreement_has_every_original_feature():
    df = _make_linear_df()
    result = drivers.decompose(df, target="y", rng_seed=42)
    agreement_features = {a["feature"] for a in result["agreement"]}
    assert {"x1", "x2", "x3", "x4"}.issubset(agreement_features)
    for a in result["agreement"]:
        assert a["label"] in {
            "high-confidence",
            "review",
            "low-confidence",
            "not-reported",
        }
        assert a["methodology_ref"] is None


# ---------------------------------------------------------------------------
# NaN in target dropped before variance check
# ---------------------------------------------------------------------------


def test_nan_target_rows_dropped():
    df = _make_linear_df(n=100)
    df.loc[::10, "y"] = np.nan  # 10 rows
    result = drivers.decompose(df, target="y", rng_seed=42)
    assert result["K"] == 5
    # Should still run all three methods
    assert len(result["method_results"]["rf_importance"]) >= 4


# ---------------------------------------------------------------------------
# TC-AN-23-03 review label — integration-level test
# ---------------------------------------------------------------------------


def test_tc_an_23_03_secondary_feature_review_label():
    """Construct a dataset with 10 features (K=5) where some noise features
    land in exactly 2 of 3 top-K sets (the `review` label)."""
    rng = np.random.default_rng(7)
    n = 500
    # 10 features; K = max(5, ceil(0.10 * 10)) = 5. One signal column
    # dominates; the rest are pure noise. Different methods will fill
    # remaining top-5 slots inconsistently, producing the `review` label
    # for at least one noise feature.
    x = {f"x{i}": rng.normal(0, 1, n) for i in range(1, 11)}
    y = 0.9 * x["x1"] + rng.normal(0, 0.1, n)
    df = pd.DataFrame({**x, "y": y})
    result = drivers.decompose(df, target="y", rng_seed=42)
    assert result["K"] == 5
    labels = {a["feature"]: a["label"] for a in result["agreement"]}
    # x1 is the dominant signal — should be high-confidence
    assert labels["x1"] == "high-confidence"
    # With 10 features and K=5, the `review` bucket is very likely to be
    # occupied by at least one feature whose top-5 appearance is
    # method-specific.
    emitted = set(labels.values())
    assert "review" in emitted


# ---------------------------------------------------------------------------
# ADR-202 sub_seeds pre-derivation contract
# ---------------------------------------------------------------------------


def test_sub_seeds_override_takes_precedence_over_rng_seed():
    df = _make_linear_df()
    custom = {
        "drivers_rf": 123,
        "drivers_rf_perm": 456,
        "drivers_partial_corr": 789,
    }
    # Two runs with the same sub_seeds but different rng_seed produce
    # identical rankings — sub_seeds dominate.
    r1 = drivers.decompose(df, target="y", rng_seed=1, sub_seeds=custom)
    r2 = drivers.decompose(df, target="y", rng_seed=99, sub_seeds=custom)
    assert [e["feature"] for e in r1["method_results"]["rf_importance"]] == [
        e["feature"] for e in r2["method_results"]["rf_importance"]
    ]


def test_sub_seeds_missing_key_raises_key_error():
    df = _make_linear_df()
    incomplete = {"drivers_rf": 1}
    with pytest.raises(KeyError):
        drivers.decompose(df, target="y", rng_seed=42, sub_seeds=incomplete)


# ---------------------------------------------------------------------------
# SHAP path — exception guard returns None with warning
# ---------------------------------------------------------------------------


def test_shap_value_error_returns_none_with_warning(monkeypatch):
    import importlib

    try:
        shap = importlib.import_module("shap")
    except ImportError:
        pytest.skip("shap not installed")

    def _raise(*args, **kwargs):
        raise ValueError("Model type not yet supported")

    monkeypatch.setattr(shap, "TreeExplainer", _raise)
    df = _make_linear_df()
    result = drivers.decompose(df, target="y", rng_seed=42, run_shap=True)
    assert result["method_results"]["shap"] is None
    assert any("SHAP skipped" in w for w in result["shap_warnings"])


def test_shap_output_shape_when_available():
    import importlib.util

    if importlib.util.find_spec("shap") is None:
        pytest.skip("shap not installed")
    df = _make_linear_df(n=100)
    result = drivers.decompose(df, target="y", rng_seed=42, run_shap=True)
    shap_rows = result["method_results"]["shap"]
    if shap_rows is None:
        pytest.skip("shap call skipped for this RF configuration")
    for entry in shap_rows:
        assert set(entry.keys()) == {"feature", "mean_abs_shap"}
        assert isinstance(entry["mean_abs_shap"], float)
    # Sorted descending
    vals = [e["mean_abs_shap"] for e in shap_rows]
    assert vals == sorted(vals, reverse=True)
