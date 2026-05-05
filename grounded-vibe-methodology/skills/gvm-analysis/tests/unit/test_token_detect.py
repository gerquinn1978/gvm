"""Unit tests for ``_shared/token_detect.py`` (anonymisation-pipeline ADR-406).

Test cases TC-AN-40-01, TC-AN-40-02. P14-C04.
"""

from __future__ import annotations

import pandas as pd

from _shared import token_detect as td


# ---------------------------------------------------------------------------
# 1. Empty / zero-row dataframes
# ---------------------------------------------------------------------------


def test_empty_dataframe_returns_no_detection_no_warnings() -> None:
    result = td.detect(pd.DataFrame())
    assert result.anonymised_input_detected is False
    assert result.anonymised_columns == ()
    assert result.warnings == ()


def test_dataframe_with_zero_rows_emits_all_null_warnings() -> None:
    """A column that exists but has zero non-null values is treated the
    same as 'entirely null' — the n_non_null=0 guard fires before any
    threshold logic. Warning fires per column."""
    df = pd.DataFrame(
        {"a": pd.Series([], dtype="object"), "b": pd.Series([], dtype="object")}
    )
    result = td.detect(df)
    assert result.anonymised_input_detected is False
    assert result.anonymised_columns == ()
    assert len(result.warnings) == 2
    assert "column 'a' is entirely null" in result.warnings[0]
    assert "column 'b' is entirely null" in result.warnings[1]


# ---------------------------------------------------------------------------
# 2. TC-AN-40-01: anonymised columns flagged
# ---------------------------------------------------------------------------


def test_fully_anonymised_column_flagged() -> None:
    df = pd.DataFrame(
        {
            "department": [
                "TOK_department_001",
                "TOK_department_002",
                "TOK_department_001",
                "TOK_department_003",
                "TOK_department_002",
            ]
        }
    )
    result = td.detect(df)
    assert result.anonymised_input_detected is True
    assert result.anonymised_columns == ("department",)
    assert result.warnings == ()


def test_at_threshold_exactly_flagged() -> None:
    """Threshold is `>=` (inclusive). 8/10 = 0.8 must flag."""
    values = ["TOK_x_001"] * 8 + ["raw_a", "raw_b"]
    df = pd.DataFrame({"x": values})
    result = td.detect(df)
    assert result.anonymised_columns == ("x",)


def test_below_threshold_not_flagged() -> None:
    """7/10 = 0.7 < 0.8 must NOT flag."""
    values = ["TOK_x_001"] * 7 + ["raw_a", "raw_b", "raw_c"]
    df = pd.DataFrame({"x": values})
    result = td.detect(df)
    assert result.anonymised_columns == ()
    assert result.anonymised_input_detected is False


# ---------------------------------------------------------------------------
# 3. Regex shape — TC-AN-40-02 false-positive guards
# ---------------------------------------------------------------------------


def test_normalised_column_name_with_digits_matched() -> None:
    """ADR-406 M-10: `[a-z0-9_]+` allows digits in the column slot."""
    df = pd.DataFrame({"q3_2023": ["TOK_q3_2023_001", "TOK_q3_2023_002"]})
    result = td.detect(df)
    assert result.anonymised_columns == ("q3_2023",)


def test_short_index_below_3_digits_not_matched() -> None:
    """ADR-406 M-6: minimum 3-digit index. Two-digit suffix must NOT match."""
    df = pd.DataFrame({"x": ["TOK_dept_99", "TOK_dept_88", "TOK_dept_77"]})
    result = td.detect(df)
    assert result.anonymised_columns == ()


def test_partial_string_not_matched() -> None:
    """The regex is anchored with `^…$` — substring matches are false positives."""
    df = pd.DataFrame({"x": ["prefix TOK_dept_001 suffix"] * 5})
    result = td.detect(df)
    assert result.anonymised_columns == ()


def test_uppercase_in_token_not_matched() -> None:
    """Regex is `[a-z0-9_]+`; uppercase in the column slot must not match."""
    df = pd.DataFrame({"x": ["TOK_Dept_001", "TOK_DEPT_002"]})
    result = td.detect(df)
    assert result.anonymised_columns == ()


def test_non_anonymised_input_does_not_trigger_note() -> None:
    """TC-AN-40-02: ordinary categorical / numeric data → no detection."""
    df = pd.DataFrame(
        {
            "name": ["Alice", "Bob", "Carol"],
            "age": [30, 40, 50],
            "city": ["London", "Paris", "Berlin"],
        }
    )
    result = td.detect(df)
    assert result.anonymised_input_detected is False
    assert result.anonymised_columns == ()
    assert result.warnings == ()


# ---------------------------------------------------------------------------
# 4. Null handling
# ---------------------------------------------------------------------------


def test_all_null_column_skipped_with_warning() -> None:
    df = pd.DataFrame({"x": [None, None, None]})
    result = td.detect(df)
    assert result.anonymised_columns == ()
    assert len(result.warnings) == 1
    assert (
        result.warnings[0]
        == "column 'x' is entirely null — token-pattern detection skipped"
    )


def test_partial_null_counted_against_non_null_only() -> None:
    """Only the non-null cells contribute to the ratio."""
    df = pd.DataFrame({"x": ["TOK_dept_001", "TOK_dept_002", None, None]})
    result = td.detect(df)
    assert result.anonymised_columns == ("x",)
    assert result.warnings == ()


# ---------------------------------------------------------------------------
# 5. Mixed columns + ordering
# ---------------------------------------------------------------------------


def test_mixed_columns_only_anonymised_flagged() -> None:
    df = pd.DataFrame(
        {
            "tokenised": ["TOK_t_001", "TOK_t_002", "TOK_t_003"],
            "numeric": [1, 2, 3],
            "partly": ["TOK_p_001", "raw_a", "raw_b"],
        }
    )
    result = td.detect(df)
    assert result.anonymised_columns == ("tokenised",)


def test_columns_returned_in_input_order() -> None:
    df = pd.DataFrame(
        {
            "alpha": ["TOK_alpha_001", "TOK_alpha_002"],
            "beta": ["TOK_beta_001", "TOK_beta_002"],
            "gamma": ["TOK_gamma_001", "TOK_gamma_002"],
        }
    )
    result = td.detect(df)
    assert result.anonymised_columns == ("alpha", "beta", "gamma")


def test_warnings_returned_in_input_order() -> None:
    df = pd.DataFrame(
        {
            "first": [None, None],
            "second": [None, None],
            "third": [None, None],
        }
    )
    result = td.detect(df)
    assert "'first'" in result.warnings[0]
    assert "'second'" in result.warnings[1]
    assert "'third'" in result.warnings[2]


# ---------------------------------------------------------------------------
# 6. Non-mutation
# ---------------------------------------------------------------------------


def test_detection_does_not_mutate_input_frame() -> None:
    df = pd.DataFrame(
        {
            "x": ["TOK_x_001", "TOK_x_002"],
            "y": [10, 20],
        }
    )
    snapshot = df.copy(deep=True)
    td.detect(df)
    pd.testing.assert_frame_equal(df, snapshot)


# ---------------------------------------------------------------------------
# 7. Property: flag aligns with columns list
# ---------------------------------------------------------------------------


def test_anonymised_input_detected_flag_aligns_with_columns_list() -> None:
    df_yes = pd.DataFrame({"x": ["TOK_x_001", "TOK_x_002"]})
    df_no = pd.DataFrame({"x": ["a", "b"]})
    yes = td.detect(df_yes)
    no = td.detect(df_no)
    assert yes.anonymised_input_detected == bool(yes.anonymised_columns)
    assert no.anonymised_input_detected == bool(no.anonymised_columns)


# ---------------------------------------------------------------------------
# 8. Constants regression guards
# ---------------------------------------------------------------------------


def test_pattern_constant_value() -> None:
    """Build the expected pattern from TOK_PREFIX so the test honours the
    single-source-of-truth principle the implementation enforces — a
    rename of TOK_PREFIX would propagate here, not silently diverge."""
    import re as _re

    from _shared.tokens import TOK_PREFIX

    expected = rf"^{_re.escape(TOK_PREFIX)}[a-z0-9_]+_\d{{3,}}$"
    assert td.PATTERN.pattern == expected


def test_threshold_constant_value() -> None:
    assert td.THRESHOLD == 0.8


# ---------------------------------------------------------------------------
# 9. Non-string dtypes
# ---------------------------------------------------------------------------


def test_int_column_returns_no_match() -> None:
    df = pd.DataFrame({"x": [1, 2, 3, 4, 5]})
    result = td.detect(df)
    assert result.anonymised_columns == ()
    assert result.warnings == ()


def test_float_column_returns_no_match() -> None:
    df = pd.DataFrame({"x": [1.5, 2.5, 3.5]})
    result = td.detect(df)
    assert result.anonymised_columns == ()


# ---------------------------------------------------------------------------
# 10. TOK_PREFIX shared with tokens.py
# ---------------------------------------------------------------------------


def test_pattern_uses_canonical_tok_prefix() -> None:
    """Brooks: single source of truth — the prefix in the regex must match
    `_shared.tokens.TOK_PREFIX`."""
    from _shared.tokens import TOK_PREFIX

    assert td.PATTERN.pattern.startswith(f"^{TOK_PREFIX}")
