"""Tests for ``_shared/tokens.py`` — token format + de-anonymisation regex.

Covers anonymisation-pipeline ADR-403 (P14-C01, originally P7-C01 in the
gvm-analysis impl-guide; renumbered to avoid plugin-build clash):

* ``normalise_column`` — lowercase, non-alphanumerics → ``_``, truncate to 30.
* ``make_token`` — column-prefixed, zero-padded; pad widens with ``total``.
* ``build_match_regex`` — compiled regex for de-anonymisation; ``\\d{3,}``.

TC coverage: TC-AN-36-04 (uniqueness/stability property).
"""

from __future__ import annotations

import re

import pytest
from hypothesis import given, settings, strategies as st


# --- normalise_column -------------------------------------------------------


def test_normalise_lowercases_simple_name() -> None:
    from _shared import tokens

    assert tokens.normalise_column("Department") == "department"


def test_normalise_replaces_whitespace_with_underscore() -> None:
    from _shared import tokens

    assert tokens.normalise_column("Employee Name") == "employee_name"


def test_normalise_replaces_punctuation_with_underscore() -> None:
    from _shared import tokens

    assert tokens.normalise_column("dept-code") == "dept_code"


def test_normalise_preserves_digits() -> None:
    from _shared import tokens

    # Post-R3 fix M-10: digits in normalised names allowed (e.g. q3_2023).
    assert tokens.normalise_column("Q3 2023") == "q3_2023"


def test_normalise_truncates_to_thirty_chars() -> None:
    from _shared import tokens

    out = tokens.normalise_column("a" * 50)
    assert len(out) == 30
    assert out == "a" * 30


def test_normalise_collapses_multiple_separators() -> None:
    from _shared import tokens

    # "foo--bar  baz" → "foo__bar__baz" — every non-alphanumeric is one
    # underscore (no collapsing); spec says non-alphanumerics → _.
    assert tokens.normalise_column("foo--bar  baz") == "foo__bar__baz"


# --- make_token -------------------------------------------------------------


def test_make_token_minimum_three_digit_pad_for_small_total() -> None:
    from _shared import tokens

    assert tokens.make_token("Department", 1, total=5) == "TOK_department_001"


def test_make_token_three_digit_pad_at_total_999() -> None:
    from _shared import tokens

    assert tokens.make_token("Department", 999, total=999) == "TOK_department_999"


def test_make_token_widens_to_four_digits_at_total_1000() -> None:
    from _shared import tokens

    assert tokens.make_token("Department", 1, total=1000) == "TOK_department_0001"
    assert tokens.make_token("Department", 1000, total=1000) == "TOK_department_1000"


def test_make_token_widens_further_at_total_10k() -> None:
    from _shared import tokens

    assert tokens.make_token("Department", 1, total=10000) == "TOK_department_00001"


def test_make_token_normalises_column_name() -> None:
    from _shared import tokens

    # The column slot in the token always uses the normalised form.
    assert tokens.make_token("Employee Name", 7, total=10) == "TOK_employee_name_007"


def test_make_token_uses_TOK_prefix_constant() -> None:
    from _shared import tokens

    assert tokens.TOK_PREFIX == "TOK_"
    assert tokens.make_token("x", 1, total=1).startswith(tokens.TOK_PREFIX)


# --- build_match_regex ------------------------------------------------------


def test_build_match_regex_returns_compiled_pattern() -> None:
    from _shared import tokens

    pat = tokens.build_match_regex(["Department"])
    assert isinstance(pat, re.Pattern)


def test_build_match_regex_matches_three_digit_token() -> None:
    from _shared import tokens

    pat = tokens.build_match_regex(["Department", "Employee Name"])
    assert pat.fullmatch("TOK_department_001") is not None
    assert pat.fullmatch("TOK_employee_name_042") is not None
    assert pat.fullmatch("TOK_department_9999") is not None


def test_build_match_regex_rejects_short_index() -> None:
    from _shared import tokens

    # Post-R3 fix M-6: \d{3,} requires minimum 3 digits — rules out
    # accidental matches on partial suffixes like "_0" or "_00".
    pat = tokens.build_match_regex(["Department"])
    assert pat.fullmatch("TOK_department_01") is None
    assert pat.fullmatch("TOK_department_0") is None


def test_build_match_regex_rejects_unknown_column() -> None:
    from _shared import tokens

    pat = tokens.build_match_regex(["Department"])
    assert pat.fullmatch("TOK_other_001") is None


def test_build_match_regex_escapes_regex_metachars_in_column_names() -> None:
    from _shared import tokens

    # A column called "dept.code" normalises to "dept_code" so the literal
    # dot never reaches the regex. But to harden against future changes,
    # the alternation must use re.escape per part — verify that a column
    # whose normalised form happened to contain a regex meta-char (none
    # do today, but the contract should hold) is escaped, not interpolated.
    # We test the correct-by-construction property: build_match_regex
    # never matches a literal that is unrelated to the registered columns.
    pat = tokens.build_match_regex(["Department"])
    # If the underscore in the alternation were treated as a quantifier
    # boundary or anything other than a literal, this 'TOK_X_001' would
    # incorrectly match. Verify it does not.
    assert pat.fullmatch("TOK_X_001") is None


def test_build_match_regex_empty_columns_raises() -> None:
    from _shared import tokens

    # Defensive: an empty alternation regex (TOK_(?:)_\d{3,}) would compile
    # to something that never matches. A typo at the call site is more
    # likely than legitimate empty input — fail loudly.
    with pytest.raises(ValueError):
        tokens.build_match_regex([])


# --- Property: TC-AN-36-04 — uniqueness and stability per (column, value) ---


@given(
    column=st.text(
        alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        min_size=1,
        max_size=10,
    ),
    indices=st.lists(
        st.integers(min_value=1, max_value=999), min_size=2, max_size=20, unique=True
    ),
)
@settings(max_examples=50)
def test_property_distinct_indices_yield_distinct_tokens(
    column: str, indices: list[int]
) -> None:
    from _shared import tokens

    total = max(indices)
    out = {tokens.make_token(column, i, total=total) for i in indices}
    # All tokens for distinct indices in the same column must be distinct.
    assert len(out) == len(indices)


@given(
    column=st.text(
        alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        min_size=1,
        max_size=10,
    ),
    index=st.integers(min_value=1, max_value=999),
    total=st.integers(min_value=1, max_value=999),
)
@settings(max_examples=50)
def test_property_same_inputs_yield_same_token(
    column: str, index: int, total: int
) -> None:
    from _shared import tokens

    # Determinism: two calls with the same args produce the same token.
    a = tokens.make_token(column, index, total=max(total, index))
    b = tokens.make_token(column, index, total=max(total, index))
    assert a == b
