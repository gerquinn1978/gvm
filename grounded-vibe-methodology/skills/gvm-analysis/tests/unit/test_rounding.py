"""Tests for ``_shared/rounding.py`` — AN-18 (TC-AN-18-01/02)."""

from __future__ import annotations

import pandas as pd
import pytest

from _shared import rounding


# ---------------------------------------------------------------------------
# Contract shape
# ---------------------------------------------------------------------------


def test_signal_shape() -> None:
    s = pd.Series([100, 200, 300, 400, 500] * 20)
    result = rounding.suspicious_rounding(s)
    assert result is not None
    assert set(result) == {"fraction_round", "note"}
    assert isinstance(result["fraction_round"], float)
    assert 0.0 <= result["fraction_round"] <= 1.0
    assert isinstance(result["note"], str) and result["note"]


# ---------------------------------------------------------------------------
# TC-AN-18-01 — suspicious rounding fired on 80% ending in "00"
# ---------------------------------------------------------------------------


def test_tc_an_18_01_suspicious_80pct_rounds() -> None:
    values = [100, 200, 300, 500, 1000, 1500, 2500, 3500] * 10 + [17, 23] * 10
    s = pd.Series(values)
    result = rounding.suspicious_rounding(s)
    assert result is not None
    assert result["fraction_round"] == pytest.approx(0.8)
    assert "80%" in result["note"]
    assert "00" in result["note"]


# ---------------------------------------------------------------------------
# TC-AN-18-02 — natural distribution not flagged
# ---------------------------------------------------------------------------


def test_tc_an_18_02_uniform_last_digits_not_flagged() -> None:
    import numpy as np

    rng = np.random.default_rng(0)
    values = rng.integers(1, 1000, size=500).tolist()
    s = pd.Series(values)
    result = rounding.suspicious_rounding(s)
    # Uniform last-digit distribution should produce ~1% rounding fraction
    # (1/100 end in "00"). Threshold is 50%, so no flag.
    assert result is None


# ---------------------------------------------------------------------------
# Boundary tests
# ---------------------------------------------------------------------------


def test_boundary_50pct_fires() -> None:
    """Exactly 50% ending in 00 hits threshold (>= 0.5)."""
    values = [100, 200, 300, 400, 500] * 10 + [11, 23, 47, 59, 71] * 10
    s = pd.Series(values)
    result = rounding.suspicious_rounding(s)
    assert result is not None
    assert result["fraction_round"] == pytest.approx(0.5)


def test_boundary_just_below_threshold_does_not_fire() -> None:
    """49% ending in 00 is below the 50% threshold — no flag."""
    values = (
        [100, 200, 300, 400] * 10
        + [400, 500] * 5
        + [11, 23, 47, 59, 71] * 10
        + [83] * 1
    )
    s = pd.Series(values)
    result = rounding.suspicious_rounding(s)
    # 49/99 ≈ 49.5% — below 50% threshold.
    assert result is None


# ---------------------------------------------------------------------------
# Degenerate inputs
# ---------------------------------------------------------------------------


def test_non_numeric_returns_none() -> None:
    s = pd.Series(["a", "b", "c"])
    assert rounding.suspicious_rounding(s) is None


def test_empty_series_returns_none() -> None:
    s = pd.Series([], dtype="float64")
    assert rounding.suspicious_rounding(s) is None


def test_all_null_returns_none() -> None:
    s = pd.Series([None, None, None], dtype="float64")
    assert rounding.suspicious_rounding(s) is None


def test_float_column_uses_integer_part() -> None:
    """Floats: check integer part's last two digits (100.0 → ends in 00)."""
    values = [100.0, 200.0, 300.0, 400.0, 500.0] * 10 + [11.5, 23.7] * 10
    s = pd.Series(values)
    result = rounding.suspicious_rounding(s)
    assert result is not None
    assert result["fraction_round"] == pytest.approx(50 / 70)
