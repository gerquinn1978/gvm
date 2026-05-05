"""Tests for ``_shared/type_drift.py`` — AN-17 (TC-AN-17-01..04)."""

from __future__ import annotations

import pandas as pd

from _shared import type_drift


# ---------------------------------------------------------------------------
# Contract shape (Brooks / ADR-201)
# ---------------------------------------------------------------------------


def test_check_returns_none_on_clean_numeric() -> None:
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0] * 20)
    assert type_drift.check(s, "amount") is None


def test_check_signal_shape_keys() -> None:
    s = pd.Series(["100", "250.50", "300", "400.25"] * 10)
    result = type_drift.check(s, "amount")
    assert result is not None
    assert set(result) == {"kind", "examples", "recommendation"}
    assert isinstance(result["kind"], str) and result["kind"]
    assert isinstance(result["examples"], list)
    assert all(isinstance(e, str) for e in result["examples"])
    assert isinstance(result["recommendation"], str) and result["recommendation"]


def test_examples_capped_at_three() -> None:
    s = pd.Series([f"{i}.{i}" for i in range(100)])
    result = type_drift.check(s, "amount")
    assert result is not None
    assert len(result["examples"]) <= 3


# ---------------------------------------------------------------------------
# TC-AN-17-01 — numeric stored as string
# ---------------------------------------------------------------------------


def test_tc_an_17_01_numbers_as_strings() -> None:
    s = pd.Series(["100", "250.50", "300", "400.25"] * 10)
    result = type_drift.check(s, "amount")
    assert result is not None
    assert result["kind"] == "numeric stored as string"
    assert "parse" in result["recommendation"].lower()


def test_numbers_as_strings_boundary_95pct_fires() -> None:
    # 95 numeric, 5 text = exactly 95% → fires (>= 95%).
    values = ["1"] * 95 + ["abc"] * 5
    s = pd.Series(values)
    result = type_drift.check(s, "x")
    assert result is not None and result["kind"] == "numeric stored as string"


def test_numbers_as_strings_boundary_94pct_does_not_fire_as_numeric() -> None:
    # 94 numeric, 6 text = below threshold → NOT classified as numbers-as-strings.
    # Expected: mixed types instead.
    values = ["1"] * 94 + ["abcxyz"] * 6
    s = pd.Series(values)
    result = type_drift.check(s, "x")
    assert result is None or result["kind"] != "numeric stored as string"


# ---------------------------------------------------------------------------
# TC-AN-17-02 — Excel serial dates
# ---------------------------------------------------------------------------


def test_tc_an_17_02_excel_serial_dates_on_date_named_column() -> None:
    s = pd.Series([40000, 42000, 44000, 45000, 46000] * 10)
    result = type_drift.check(s, "created_at")
    assert result is not None
    assert result["kind"] == "possibly Excel serial date stored as int"


def test_excel_serial_dates_requires_date_named_column() -> None:
    # Same int range but non-date column name → not flagged as Excel serial.
    s = pd.Series([40000, 42000, 44000, 45000, 46000] * 10)
    result = type_drift.check(s, "count")
    assert (
        result is None or result["kind"] != "possibly Excel serial date stored as int"
    )


def test_excel_serial_boundary_39999_does_not_fire() -> None:
    s = pd.Series([39999, 39998, 39997, 39996, 39995] * 10)
    result = type_drift.check(s, "created_at")
    assert (
        result is None or result["kind"] != "possibly Excel serial date stored as int"
    )


def test_excel_serial_boundary_50000_fires() -> None:
    s = pd.Series([40000, 45000, 50000, 48000, 47000] * 10)
    result = type_drift.check(s, "created_at")
    assert result is not None
    assert result["kind"] == "possibly Excel serial date stored as int"


def test_excel_serial_boundary_50001_does_not_fire() -> None:
    s = pd.Series([50001, 50002, 50003, 50004, 50005] * 10)
    result = type_drift.check(s, "created_at")
    assert (
        result is None or result["kind"] != "possibly Excel serial date stored as int"
    )


# ---------------------------------------------------------------------------
# TC-AN-17-03 — mixed types
# ---------------------------------------------------------------------------


def test_tc_an_17_03_mixed_types() -> None:
    values = (
        ["100", "250.50", "300"] * 8  # numeric strings
        + ["2024-01-01", "2024-02-15", "2024-03-30"] * 8  # date strings
        + ["hello world", "free text here", "some commentary"] * 8  # free text
    )
    s = pd.Series(values)
    result = type_drift.check(s, "col")
    assert result is not None
    assert result["kind"] == "mixed types"


def test_mixed_types_not_fired_on_single_type() -> None:
    s = pd.Series(["hello"] * 30)
    result = type_drift.check(s, "col")
    # Could be None (no drift) or something else — but NOT "mixed types".
    assert result is None or result["kind"] != "mixed types"


# ---------------------------------------------------------------------------
# TC-AN-17-04 — mojibake
# ---------------------------------------------------------------------------


def test_tc_an_17_04_mojibake() -> None:
    values = ["cafÃ©", "naÃ¯ve", "rÃ©sumÃ©", "clean text", "another clean"] * 10
    s = pd.Series(values)
    result = type_drift.check(s, "notes")
    assert result is not None
    assert result["kind"] == "encoding artefact (mojibake)"
    assert (
        "encoding" in result["recommendation"].lower()
        or "reload" in result["recommendation"].lower()
    )


def test_mojibake_examples_contain_offender() -> None:
    s = pd.Series(["cafÃ©"] + ["ok"] * 29)
    result = type_drift.check(s, "notes")
    assert result is not None
    assert any("Ã" in e for e in result["examples"])


def test_clean_unicode_not_mojibake() -> None:
    s = pd.Series(["café", "naïve", "résumé"] * 10)
    result = type_drift.check(s, "notes")
    assert result is None or result["kind"] != "encoding artefact (mojibake)"


# ---------------------------------------------------------------------------
# Degenerate inputs
# ---------------------------------------------------------------------------


def test_check_all_null_returns_none() -> None:
    s = pd.Series([None] * 20)
    assert type_drift.check(s, "col") is None


def test_check_empty_series_returns_none() -> None:
    s = pd.Series([], dtype="object")
    assert type_drift.check(s, "col") is None


def test_check_clean_datetime_series_returns_none() -> None:
    s = pd.Series(pd.date_range("2024-01-01", periods=30))
    assert type_drift.check(s, "created_at") is None
