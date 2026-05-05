"""Tests for ``_shared/outliers.py`` — AN-14 (TC-AN-14-01..05)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from _shared import outliers


def _rng(seed: int = 0) -> np.random.Generator:
    return np.random.default_rng(seed)


# ---------------------------------------------------------------------------
# Contract shape
# ---------------------------------------------------------------------------


def test_detect_returns_top_level_keys() -> None:
    df = pd.DataFrame({"x": list(range(50))})
    result = outliers.detect(df, rng=_rng())
    assert set(result) == {"by_method", "agreement_matrix", "agreement_summary"}
    assert set(result["by_method"]) == {
        "iqr",
        "mad",
        "isolation_forest",
        "local_outlier_factor",
    }
    assert set(result["agreement_summary"]) == {"high", "review", "low"}


def test_detect_empty_df_returns_empty_schema() -> None:
    result = outliers.detect(pd.DataFrame(), rng=_rng())
    assert result["by_method"]["iqr"] == []
    assert result["by_method"]["mad"] == []
    assert result["by_method"]["isolation_forest"] is None
    assert result["by_method"]["local_outlier_factor"] is None
    assert result["agreement_matrix"] == []
    assert result["agreement_summary"] == {"high": 0, "review": 0, "low": 0}


def test_detect_no_numeric_columns_returns_empty() -> None:
    df = pd.DataFrame({"name": ["a", "b", "c"] * 10})
    result = outliers.detect(df, rng=_rng())
    assert result["by_method"]["iqr"] == []
    assert result["by_method"]["mad"] == []


# ---------------------------------------------------------------------------
# TC-AN-14-01 — 50× median outlier flagged by all four methods at n=1000
# ---------------------------------------------------------------------------


def test_tc_an_14_01_50x_median_flagged_by_all_four() -> None:
    rng = _rng(42)
    base = rng.normal(100, 10, size=999).tolist()
    # One extreme value 50× the median (median ≈ 100 → injected = 5000)
    values = base + [5000.0]
    df = pd.DataFrame({"amount": values})
    result = outliers.detect(df, rng=_rng(42))

    # Extreme row is index 999.
    assert len(df) == 1000
    iqr_hits = {r["row_index"] for r in result["by_method"]["iqr"]}
    mad_hits = {r["row_index"] for r in result["by_method"]["mad"]}
    iso_hits = {r["row_index"] for r in result["by_method"]["isolation_forest"]}
    lof_hits = {r["row_index"] for r in result["by_method"]["local_outlier_factor"]}
    assert 999 in iqr_hits
    assert 999 in mad_hits
    assert 999 in iso_hits
    assert 999 in lof_hits

    # Agreement matrix should mark row 999 high-confidence (all 4 methods).
    am_entry = next(e for e in result["agreement_matrix"] if e["row_index"] == 999)
    assert am_entry["confidence"] == "high"
    assert set(am_entry["methods"]) == {
        "iqr",
        "mad",
        "isolation_forest",
        "local_outlier_factor",
    }
    assert result["agreement_summary"]["high"] >= 1


# ---------------------------------------------------------------------------
# TC-AN-14-03 — low-confidence when only one method flags
# ---------------------------------------------------------------------------


def test_tc_an_14_03_single_method_low_confidence_label() -> None:
    """Any (row,column) flagged by exactly one method carries label `low`.

    Doesn't assume a specific value triggers a specific method — asserts the
    invariant across the whole matrix.
    """
    rng = _rng(7)
    values = rng.normal(100, 5, size=1000).tolist()
    # Two values: one extreme (all methods), one borderline (likely 1 method).
    values[500] = 115.0
    values[750] = 5000.0
    df = pd.DataFrame({"x": values})
    result = outliers.detect(df, rng=_rng(7))
    am = result["agreement_matrix"]
    assert len(am) > 0
    # Invariant: every single-method entry has confidence == "low".
    single_method = [e for e in am if len(e["methods"]) == 1]
    assert len(single_method) > 0, "fixture should produce ≥1 single-method flag"
    for entry in single_method:
        assert entry["confidence"] == "low"


# ---------------------------------------------------------------------------
# TC-AN-14-05 — n=999 does NOT run multivariate methods
# ---------------------------------------------------------------------------


def test_tc_an_14_05_n_999_skips_multivariate() -> None:
    rng = _rng(0)
    values = rng.normal(100, 10, size=999).tolist()
    df = pd.DataFrame({"x": values})
    result = outliers.detect(df, rng=_rng(0))
    assert result["by_method"]["isolation_forest"] is None
    assert result["by_method"]["local_outlier_factor"] is None


def test_multivariate_null_when_no_column_reaches_threshold() -> None:
    """1200 rows but every column is >50% null → non-null count <1000 per col
    → multivariate methods never run → schema values must be null, not []."""
    rng = _rng(0)
    vals = rng.normal(100, 10, size=400).tolist()
    padded = vals + [None] * 800  # 400 non-null, 800 null; len = 1200
    df = pd.DataFrame({"x": padded})
    result = outliers.detect(df, rng=_rng(0))
    assert result["by_method"]["isolation_forest"] is None
    assert result["by_method"]["local_outlier_factor"] is None


def test_n_1000_boundary_runs_multivariate() -> None:
    rng = _rng(0)
    values = rng.normal(100, 10, size=999).tolist() + [5000.0]
    df = pd.DataFrame({"x": values})
    result = outliers.detect(df, rng=_rng(0))
    assert isinstance(result["by_method"]["isolation_forest"], list)
    assert isinstance(result["by_method"]["local_outlier_factor"], list)


# ---------------------------------------------------------------------------
# IQR / MAD semantics
# ---------------------------------------------------------------------------


def test_iqr_entry_shape() -> None:
    values = [1, 2, 2, 3, 3, 3, 4, 4, 100] * 10
    df = pd.DataFrame({"x": values})
    result = outliers.detect(df, rng=_rng())
    iqr = result["by_method"]["iqr"]
    assert len(iqr) > 0
    entry = iqr[0]
    assert set(entry) == {"row_index", "column", "value", "z_iqr"}
    assert entry["column"] == "x"
    assert isinstance(entry["z_iqr"], float)
    assert entry["z_iqr"] > 0.0  # signed distance beyond fence


def test_mad_zero_safe() -> None:
    # All values identical → MAD = 0. Must not divide by zero.
    df = pd.DataFrame({"x": [5.0] * 100})
    result = outliers.detect(df, rng=_rng())
    assert result["by_method"]["mad"] == []


def test_iqr_k_1_5_constant() -> None:
    # k = 1.5 per ADR-205.
    assert outliers._IQR_K == 1.5


def test_mad_threshold_3_5() -> None:
    assert outliers._MAD_THRESHOLD == 3.5


# ---------------------------------------------------------------------------
# Agreement matrix determinism + ordering
# ---------------------------------------------------------------------------


def test_same_seed_same_iforest_flags() -> None:
    rng = _rng(42)
    values = rng.normal(100, 10, size=999).tolist() + [5000.0, 6000.0]
    df = pd.DataFrame({"x": values})
    r1 = outliers.detect(df, rng=_rng(99))
    r2 = outliers.detect(df, rng=_rng(99))
    assert r1["by_method"]["isolation_forest"] == r2["by_method"]["isolation_forest"]


def test_agreement_summary_sums_correctly() -> None:
    rng = _rng(1)
    values = rng.normal(100, 10, size=999).tolist() + [5000.0]
    df = pd.DataFrame({"x": values})
    result = outliers.detect(df, rng=_rng(1))
    summary = result["agreement_summary"]
    assert summary["high"] + summary["review"] + summary["low"] == len(
        result["agreement_matrix"]
    )


def test_agreement_matrix_entries_have_methodology_ref_field() -> None:
    df = pd.DataFrame({"x": [1.0] * 50 + [1000.0]})
    result = outliers.detect(df, rng=_rng())
    for entry in result["agreement_matrix"]:
        assert "methodology_ref" in entry


def test_non_numeric_columns_ignored() -> None:
    df = pd.DataFrame({"n": [1, 2, 3, 4, 5, 100] * 20, "cat": ["a", "b", "c"] * 40})
    result = outliers.detect(df, rng=_rng())
    # Only the numeric column surfaces in per-method lists.
    for entry in result["by_method"]["iqr"]:
        assert entry["column"] == "n"


def test_detect_invalid_rng_type_raises() -> None:
    df = pd.DataFrame({"x": [1, 2, 3]})
    with pytest.raises(TypeError):
        outliers.detect(df, rng="not-a-generator")  # type: ignore[arg-type]
