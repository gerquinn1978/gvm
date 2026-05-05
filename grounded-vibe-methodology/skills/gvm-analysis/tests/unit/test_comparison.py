"""Tests for `_shared.comparison.compute` (P21-C03).

Computes the `findings.comparison` block per spec ADR analysis-engine.md
lines 119–125. Closes defect 3b from the gates-skipped diagnosis: validate
mode runs to exit 0 with a baseline file but `findings.comparison` was
never populated, so `_candidates_comparison` always returned [].

Eight tests cover the contract:

1. Identical frames produce zero deltas, empty outliers list.
2. Shifted column produces non-empty `file_vs_file_outliers`.
3. Different row counts → empty `file_vs_file_outliers`, populated
   `per_file_differences` (column-level deltas without row pairing).
4. No shared columns → returns None.
5. Non-numeric shared columns are listed in `shared_columns` but
   excluded from `per_file_differences`.
6. Schema shape regression — every returned dict matches the spec keys.
7. NaN values are dropped before summary stats.
8. Empty actual or baseline → returns None.
"""

from __future__ import annotations

import pandas as pd
import pytest

from _shared import comparison


def test_identical_frames_have_zero_deltas_and_no_outliers() -> None:
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0], "b": [10.0, 20.0, 30.0, 40.0]})
    result = comparison.compute(df, df.copy())

    assert result is not None
    assert set(result["shared_columns"]) == {"a", "b"}
    assert result["file_vs_file_outliers"] == []
    for diff in result["per_file_differences"]:
        delta = diff["delta"]
        assert delta["mean_change"] == 0.0
        assert delta["std_change"] == 0.0


def test_shifted_column_produces_outliers() -> None:
    actual = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]})
    # Same distribution, but row index 4 is shifted by ~10σ.
    baseline = actual.copy()
    baseline.loc[4, "x"] = 100.0
    # Baseline differs from actual at row 4 by an enormous margin → flagged.
    result = comparison.compute(actual, baseline)

    assert result is not None
    outliers = result["file_vs_file_outliers"]
    assert outliers, "expected at least one row to flag as divergent"
    assert any(o["row_index_actual"] == 4 for o in outliers), outliers


def test_different_row_counts_skip_row_pairing() -> None:
    actual = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0]})
    baseline = pd.DataFrame({"a": [1.0, 2.0]})  # different size — no pairing.

    result = comparison.compute(actual, baseline)
    assert result is not None
    assert result["file_vs_file_outliers"] == []
    # per_file_differences still populates — column-level summary works without row pairing.
    assert result["per_file_differences"], (
        "per_file_differences should populate even when row counts differ"
    )


def test_no_shared_columns_returns_none() -> None:
    actual = pd.DataFrame({"a": [1.0]})
    baseline = pd.DataFrame({"b": [1.0]})
    assert comparison.compute(actual, baseline) is None


def test_non_numeric_shared_columns_excluded_from_diffs() -> None:
    actual = pd.DataFrame({"n": [1.0, 2.0, 3.0], "s": ["x", "y", "z"]})
    baseline = pd.DataFrame({"n": [1.0, 2.0, 3.0], "s": ["x", "y", "z"]})

    result = comparison.compute(actual, baseline)
    assert result is not None
    # Both columns are shared, but only the numeric one should produce a delta entry.
    assert "n" in result["shared_columns"]
    assert "s" in result["shared_columns"]
    diff_columns = {d["column"] for d in result["per_file_differences"]}
    assert diff_columns == {"n"}


def test_returned_schema_matches_spec_keys() -> None:
    actual = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
    baseline = pd.DataFrame({"a": [1.5, 2.5, 3.5]})
    result = comparison.compute(actual, baseline)

    assert result is not None
    assert set(result.keys()) == {
        "actual_file",
        "baseline_file",
        "shared_columns",
        "per_file_differences",
        "file_vs_file_outliers",
    }
    if result["per_file_differences"]:
        diff = result["per_file_differences"][0]
        assert set(diff.keys()) == {
            "column",
            "actual_summary",
            "baseline_summary",
            "delta",
        }
        for summary_key in ("actual_summary", "baseline_summary"):
            assert set(diff[summary_key].keys()) == {
                "n",
                "mean",
                "median",
                "std",
                "min",
                "max",
            }


def test_nan_values_dropped_before_summary() -> None:
    """NaN should not contaminate mean/std. Compare actual=[1,2,3,NaN]
    vs baseline=[1,2,3,4] — actual.mean = 2.0 (over 3 non-null), not 1.5
    over 4 with NaN treated as 0."""
    actual = pd.DataFrame({"a": [1.0, 2.0, 3.0, float("nan")]})
    baseline = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0]})

    result = comparison.compute(actual, baseline)
    assert result is not None
    diff = result["per_file_differences"][0]
    assert diff["actual_summary"]["mean"] == pytest.approx(2.0)
    assert diff["actual_summary"]["n"] == 3
    assert diff["baseline_summary"]["n"] == 4


def test_empty_input_returns_none() -> None:
    """Defensive: empty DataFrames degrade to None rather than raising."""
    assert comparison.compute(pd.DataFrame(), pd.DataFrame({"a": [1]})) is None
    assert comparison.compute(pd.DataFrame({"a": [1]}), pd.DataFrame()) is None
