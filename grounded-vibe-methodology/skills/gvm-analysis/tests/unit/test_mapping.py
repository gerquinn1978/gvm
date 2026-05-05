"""Tests for ``_shared/mapping.py`` — mapping-CSV reader/writer.

Anonymisation-pipeline ADR-405 + post-R4 fix CRITICAL-T5 expanded
``MappingData`` shape: ``(token_to_value, columns, rows)`` so
``de_anonymise.py`` can build the column-specific regex in one pass.
"""

from __future__ import annotations

from pathlib import Path

import pytest


# --- write + load round-trip ------------------------------------------------


def test_write_and_load_round_trip(tmp_path: Path) -> None:
    from _shared import mapping

    out = tmp_path / "mapping.csv"
    rows = [
        ("dept", "Engineering", "TOK_dept_001"),
        ("dept", "Sales", "TOK_dept_002"),
        ("employee_name", "Alice Smith", "TOK_employee_name_001"),
    ]
    mapping.write(out, rows)

    data = mapping.load(out)
    assert data.token_to_value == {
        "TOK_dept_001": "Engineering",
        "TOK_dept_002": "Sales",
        "TOK_employee_name_001": "Alice Smith",
    }
    assert data.columns == ["dept", "employee_name"]
    assert data.rows == [
        {"column": "dept", "original_value": "Engineering", "token": "TOK_dept_001"},
        {"column": "dept", "original_value": "Sales", "token": "TOK_dept_002"},
        {
            "column": "employee_name",
            "original_value": "Alice Smith",
            "token": "TOK_employee_name_001",
        },
    ]


def test_write_emits_canonical_header(tmp_path: Path) -> None:
    from _shared import mapping

    out = tmp_path / "mapping.csv"
    mapping.write(out, [("dept", "Eng", "TOK_dept_001")])
    text = out.read_text(encoding="utf-8")
    first_line = text.splitlines()[0]
    assert first_line == "column,original_value,token"


def test_load_dedupes_columns_preserving_first_appearance_order(
    tmp_path: Path,
) -> None:
    from _shared import mapping

    out = tmp_path / "mapping.csv"
    out.write_text(
        "column,original_value,token\n"
        "dept,Eng,TOK_dept_001\n"
        "name,Alice,TOK_name_001\n"
        "dept,Sales,TOK_dept_002\n"
        "name,Bob,TOK_name_002\n",
        encoding="utf-8",
    )
    data = mapping.load(out)
    # 'dept' appears first in the CSV, so it's first in columns.
    assert data.columns == ["dept", "name"]


def test_load_preserves_raw_html_special_chars(tmp_path: Path) -> None:
    from _shared import mapping

    # ADR-405 / post-design-review M-12: the CSV stores values raw. Any
    # HTML-escaping is the de_anonymise.py job, not the mapping module's.
    out = tmp_path / "mapping.csv"
    out.write_text(
        "column,original_value,token\n"
        'company,"AT&T",TOK_company_001\n'
        'company,"<script>",TOK_company_002\n',
        encoding="utf-8",
    )
    data = mapping.load(out)
    assert data.token_to_value["TOK_company_001"] == "AT&T"
    assert data.token_to_value["TOK_company_002"] == "<script>"


def test_load_missing_file_raises_malformed_file_error(tmp_path: Path) -> None:
    from _shared import mapping
    from _shared.diagnostics import MalformedFileError

    out = tmp_path / "does_not_exist.csv"
    with pytest.raises(MalformedFileError) as exc:
        mapping.load(out)
    assert str(out) in str(exc.value)


def test_load_data_only_no_canonical_header_raises_malformed_file_error(
    tmp_path: Path,
) -> None:
    from _shared import mapping
    from _shared.diagnostics import MalformedFileError

    # File has data but the first row is not the canonical header — exercises
    # the wrong-header path in load() (the data row is read as a header
    # candidate and rejected).
    out = tmp_path / "no_header.csv"
    out.write_text("dept,Eng,TOK_dept_001\n", encoding="utf-8")
    with pytest.raises(MalformedFileError):
        mapping.load(out)


def test_load_empty_file_raises_malformed_file_error(tmp_path: Path) -> None:
    from _shared import mapping
    from _shared.diagnostics import MalformedFileError

    # Truly empty file — exercises the StopIteration → MalformedFileError
    # branch (csv.reader yields nothing on a zero-byte file).
    out = tmp_path / "empty.csv"
    out.write_text("", encoding="utf-8")
    with pytest.raises(MalformedFileError):
        mapping.load(out)


def test_load_wrong_header_raises_malformed_file_error(tmp_path: Path) -> None:
    from _shared import mapping
    from _shared.diagnostics import MalformedFileError

    out = tmp_path / "wrong_header.csv"
    out.write_text(
        "col,orig,tok\ndept,Eng,TOK_dept_001\n",
        encoding="utf-8",
    )
    with pytest.raises(MalformedFileError):
        mapping.load(out)


def test_mapping_data_is_frozen(tmp_path: Path) -> None:
    from _shared import mapping

    out = tmp_path / "mapping.csv"
    mapping.write(out, [("dept", "Eng", "TOK_dept_001")])
    data = mapping.load(out)
    # Chain-of-custody artefact — the loaded record should be immutable so
    # downstream consumers cannot mutate the canonical mapping in-place.
    with pytest.raises((AttributeError, Exception)):
        data.columns = ["mutated"]  # type: ignore[misc]
