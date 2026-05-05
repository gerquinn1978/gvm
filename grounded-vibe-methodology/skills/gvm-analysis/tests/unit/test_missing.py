"""Tests for ``_shared/missing.py`` — ADR-206 / AN-15 (TC-AN-15-01..05)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from _shared import missing


# ---------------------------------------------------------------------------
# completeness()
# ---------------------------------------------------------------------------


def test_completeness_shape() -> None:
    df = pd.DataFrame({"a": [1, 2, 3, None, 5]})
    result = missing.completeness(df, "a")
    assert set(result) == {"n_total", "n_non_null", "completeness_pct"}
    assert result["n_total"] == 5
    assert result["n_non_null"] == 4
    assert result["completeness_pct"] == pytest.approx(80.0)


def test_completeness_types_are_python_native() -> None:
    df = pd.DataFrame({"a": [1, None]})
    r = missing.completeness(df, "a")
    assert isinstance(r["n_total"], int) and not isinstance(r["n_total"], np.integer)
    assert isinstance(r["n_non_null"], int) and not isinstance(
        r["n_non_null"], np.integer
    )
    assert isinstance(r["completeness_pct"], float)


def test_completeness_all_null() -> None:
    df = pd.DataFrame({"a": [None, None, None]})
    r = missing.completeness(df, "a")
    assert r["n_total"] == 3
    assert r["n_non_null"] == 0
    assert r["completeness_pct"] == 0.0


def test_completeness_empty_dataframe() -> None:
    df = pd.DataFrame({"a": []}, dtype="float64")
    r = missing.completeness(df, "a")
    assert r["n_total"] == 0
    assert r["n_non_null"] == 0
    assert r["completeness_pct"] == 0.0


# ---------------------------------------------------------------------------
# classify() — sample-size guard (boundary tests first)
# ---------------------------------------------------------------------------


def test_classify_boundary_n_total_29_is_indeterminate() -> None:
    """Guard: n_total < 30 triggers 'indeterminate' even with enough missing."""
    n = 29
    rng = np.random.default_rng(42)
    vals = rng.normal(size=n)
    mask = rng.random(n) < 0.3  # ~8-9 missing, passes n_missing>=5
    vals[mask] = np.nan
    df = pd.DataFrame({"x": vals, "other": rng.normal(size=n)})
    r = missing.classify(df, "x")
    assert r["label"] == "indeterminate"
    assert "sample too small" in r["basis"]
    assert r["confidence"] == "low"


def test_classify_boundary_n_total_30_enters_tests() -> None:
    """Guard: n_total = 30 passes (enters classification logic)."""
    n = 30
    rng = np.random.default_rng(42)
    vals = rng.normal(size=n)
    mask = np.zeros(n, dtype=bool)
    mask[rng.integers(0, n, size=8)] = True  # ensure n_missing >= 5
    vals[mask] = np.nan
    df = pd.DataFrame({"x": vals, "other": rng.normal(size=n)})
    r = missing.classify(df, "x")
    # Fixture: n_total=30, n_missing>=5 — both size-guard branches pass, so
    # the classifier MUST NOT return indeterminate (any label is fine).
    assert r["label"] != "indeterminate"


def test_classify_boundary_n_missing_4_is_indeterminate() -> None:
    n = 200
    rng = np.random.default_rng(42)
    vals = rng.normal(size=n)
    vals[[0, 1, 2, 3]] = np.nan  # exactly 4 missing
    df = pd.DataFrame({"x": vals, "other": rng.normal(size=n)})
    r = missing.classify(df, "x")
    assert r["label"] == "indeterminate"
    assert "sample too small" in r["basis"]


def test_classify_boundary_n_missing_5_enters_tests() -> None:
    n = 200
    rng = np.random.default_rng(42)
    vals = rng.normal(size=n)
    vals[[0, 1, 2, 3, 4]] = np.nan  # exactly 5 missing
    df = pd.DataFrame({"x": vals, "other": rng.normal(size=n)})
    r = missing.classify(df, "x")
    # With random missingness uncorrelated with anything, expect MCAR.
    assert r["label"] in {"MCAR", "MAR", "possibly MNAR"}


# ---------------------------------------------------------------------------
# TC-AN-15-05 — indeterminate at small sample
# ---------------------------------------------------------------------------


def test_tc_an_15_05_indeterminate_small_file() -> None:
    rng = np.random.default_rng(0)
    n = 12
    vals = rng.normal(size=n)
    vals[[0, 3, 7]] = np.nan  # 3 missing — triggers n_missing<5 guard
    df = pd.DataFrame({"score": vals, "other": rng.normal(size=n)})
    r = missing.classify(df, "score")
    assert r["label"] == "indeterminate"
    assert "sample too small" in r["basis"]


# ---------------------------------------------------------------------------
# TC-AN-15-01 — MCAR signal
# ---------------------------------------------------------------------------


def test_tc_an_15_01_mcar_random_missingness() -> None:
    rng = np.random.default_rng(42)
    n = 200
    vals = rng.normal(size=n)
    mask = rng.random(n) < 0.05
    # ensure at least 5 missing
    if mask.sum() < 5:
        mask[:5] = True
    vals[mask] = np.nan
    df = pd.DataFrame(
        {
            "score": vals,
            "numeric_unrelated": rng.normal(size=n),
            "cat_unrelated": rng.choice(["a", "b", "c"], size=n),
        }
    )
    r = missing.classify(df, "score")
    assert r["label"] == "MCAR"
    assert "no significant correlation" in r["basis"]
    assert r["confidence"] == "medium"


# ---------------------------------------------------------------------------
# TC-AN-15-02 — MAR on a categorical column
# ---------------------------------------------------------------------------


def test_tc_an_15_02_mar_on_categorical() -> None:
    rng = np.random.default_rng(7)
    n = 200
    department = rng.choice(["intern", "staff", "manager"], size=n, p=[0.3, 0.5, 0.2])
    salary = rng.normal(loc=50000, scale=10000, size=n)
    salary[department == "intern"] = np.nan
    df = pd.DataFrame({"salary": salary, "department": department})
    r = missing.classify(df, "salary")
    assert r["label"] == "MAR"
    assert "correlates with department" in r["basis"]
    assert r["confidence"] == "high"


def test_tc_an_15_02_mar_on_binary_uses_phi() -> None:
    """Binary other-column uses φ; basis names the statistic."""
    rng = np.random.default_rng(3)
    n = 200
    flag = rng.choice([0, 1], size=n, p=[0.6, 0.4])
    vals = rng.normal(size=n).astype(float)
    # Make missingness strongly correlated with flag==1
    vals[flag == 1] = np.nan
    df = pd.DataFrame({"x": vals, "flag": flag})
    r = missing.classify(df, "x")
    assert r["label"] == "MAR"
    # Implementation emits ASCII "phi" — do not tolerate an unexpected
    # Unicode rename slipping through (would break renderer parsing).
    assert "phi" in r["basis"]


def test_classify_mar_on_numeric_uses_point_biserial() -> None:
    rng = np.random.default_rng(5)
    n = 200
    driver = rng.normal(size=n)
    vals = rng.normal(size=n)
    # Missingness strongly correlated with driver being high
    vals[driver > 0.5] = np.nan
    df = pd.DataFrame({"x": vals, "driver": driver})
    r = missing.classify(df, "x")
    assert r["label"] == "MAR"
    assert "driver" in r["basis"]


# ---------------------------------------------------------------------------
# MAR on time/order
# ---------------------------------------------------------------------------


def test_classify_mar_on_row_order() -> None:
    """Missingness that drifts monotonically with row index → MAR time/order."""
    rng = np.random.default_rng(11)
    n = 200
    vals = rng.normal(size=n).astype(float)
    # Rising missingness probability along row order
    for i in range(n):
        if rng.random() < (i / n):
            vals[i] = np.nan
    df = pd.DataFrame({"x": vals, "unrelated": rng.normal(size=n)})
    r = missing.classify(df, "x")
    assert r["label"] == "MAR"
    assert "row order" in r["basis"] or "time" in r["basis"]


# ---------------------------------------------------------------------------
# TC-AN-15-03 — possibly MNAR
# ---------------------------------------------------------------------------


def test_tc_an_15_03_possibly_mnar_skewed_tail() -> None:
    rng = np.random.default_rng(0)
    n = 300
    # Lognormal(sigma=3) is heavy-tailed enough to clear the |mean-median|≥2·IQR
    # bar in ADR-206 step 4 (spec's chosen threshold). A plain exponential does
    # not — its mean/median/IQR ratio is fixed and too mild.
    vals = rng.lognormal(mean=0.0, sigma=3.0, size=n)
    # Random missingness uncorrelated with row order / other columns —
    # so MAR tests fail and MNAR skew rule fires.
    mask = rng.random(n) < 0.08
    if mask.sum() < 5:
        mask[:5] = True
    vals[mask] = np.nan
    df = pd.DataFrame({"income": vals, "noise": rng.normal(size=n)})
    r = missing.classify(df, "income")
    assert r["label"] == "possibly MNAR"
    assert "skewed" in r["basis"]
    assert r["confidence"] == "medium"


# ---------------------------------------------------------------------------
# Degenerate cases
# ---------------------------------------------------------------------------


def test_classify_all_null_is_indeterminate() -> None:
    df = pd.DataFrame({"x": [None] * 50, "other": list(range(50))})
    r = missing.classify(df, "x")
    assert r["label"] == "indeterminate"
    assert "entirely null" in r["basis"]


def test_classify_zero_missing_is_mcar() -> None:
    """No missing values → trivially MCAR (nothing to classify)."""
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"x": rng.normal(size=100), "other": rng.normal(size=100)})
    r = missing.classify(df, "x")
    # Zero missingness with n_total >= 30 passes the guard but has n_missing = 0.
    # Spec does not require a specific label here, but consumers skip classify()
    # when missing==0. Our contract: return MCAR with a clear basis.
    assert r["label"] == "MCAR"


def test_classify_basis_includes_statistic_value_for_mar() -> None:
    """MAR basis must include the numeric statistic value."""
    rng = np.random.default_rng(3)
    n = 200
    flag = rng.choice([0, 1], size=n, p=[0.6, 0.4])
    vals = rng.normal(size=n).astype(float)
    vals[flag == 1] = np.nan
    df = pd.DataFrame({"x": vals, "flag": flag})
    r = missing.classify(df, "x")
    # basis should contain a numeric token like "0.8" or "1.0"
    import re

    assert re.search(r"\d\.\d", r["basis"]) is not None


def test_classify_rng_optional() -> None:
    """Classifier signature accepts optional rng kwarg for API symmetry."""
    df = pd.DataFrame({"x": [1.0, None, 3.0] * 40, "o": list(range(120))})
    r1 = missing.classify(df, "x")
    r2 = missing.classify(df, "x", rng=np.random.default_rng(0))
    assert r1["label"] == r2["label"]
