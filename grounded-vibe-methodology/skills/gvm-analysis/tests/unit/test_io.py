"""Tests for `_shared/io.py` — file loading, encryption refusal, dep check (P2-C01).

Covers requirements AN-2 (format acceptance), AN-5 (dependency detection),
AN-42 (encrypted refusal), AN-43 (formula columns: cached values + formula
strings). Multi-sheet aggregation and multi-file strategies are delegated to
``aggregation.py`` (P2-C01b) and explicitly excluded here — ``io.load`` on a
multi-sheet xlsx without ``sheet=`` must raise ``ValueError`` directing the
caller to ``aggregation.py``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


# --- TC-AN-2-01: multi-format acceptance ------------------------------------


def test_load_csv_returns_dataframe(
    csv_fixture: Path, sample_frame: pd.DataFrame
) -> None:
    from _shared import io

    frame = io.load(csv_fixture)
    pd.testing.assert_frame_equal(
        frame.reset_index(drop=True), sample_frame.reset_index(drop=True)
    )


def test_load_tsv_returns_dataframe(
    tsv_fixture: Path, sample_frame: pd.DataFrame
) -> None:
    from _shared import io

    frame = io.load(tsv_fixture)
    pd.testing.assert_frame_equal(
        frame.reset_index(drop=True), sample_frame.reset_index(drop=True)
    )


def test_load_parquet_returns_dataframe(
    parquet_fixture: Path, sample_frame: pd.DataFrame
) -> None:
    from _shared import io

    frame = io.load(parquet_fixture)
    pd.testing.assert_frame_equal(
        frame.reset_index(drop=True), sample_frame.reset_index(drop=True)
    )


def test_load_json_returns_dataframe(
    json_fixture: Path, sample_frame: pd.DataFrame
) -> None:
    from _shared import io

    frame = io.load(json_fixture)
    # Column order from to_json/read_json may differ; compare by value.
    assert set(frame.columns) == set(sample_frame.columns)
    assert len(frame) == len(sample_frame)


def test_load_jsonl_returns_dataframe(
    jsonl_fixture: Path, sample_frame: pd.DataFrame
) -> None:
    from _shared import io

    frame = io.load(jsonl_fixture)
    assert set(frame.columns) == set(sample_frame.columns)
    assert len(frame) == len(sample_frame)


def test_load_xlsx_single_sheet(
    xlsx_single_sheet_fixture: Path, sample_frame: pd.DataFrame
) -> None:
    from _shared import io

    frame = io.load(xlsx_single_sheet_fixture)
    pd.testing.assert_frame_equal(
        frame.reset_index(drop=True), sample_frame.reset_index(drop=True)
    )


def test_load_accepts_string_path(
    csv_fixture: Path, sample_frame: pd.DataFrame
) -> None:
    """load accepts str paths identically to Path objects."""
    from _shared import io

    frame = io.load(str(csv_fixture))
    pd.testing.assert_frame_equal(
        frame.reset_index(drop=True), sample_frame.reset_index(drop=True)
    )


# --- TC-AN-2-03: unsupported extension --------------------------------------


def test_load_unsupported_extension_raises_valueerror(tmp_path: Path) -> None:
    from _shared import io

    bad = tmp_path / "report.pdf"
    bad.write_bytes(b"%PDF-1.4 fake")
    with pytest.raises(ValueError) as exc:
        io.load(bad)
    msg = str(exc.value)
    assert "report.pdf" in msg
    # Every supported extension must appear in the diagnostic so the user
    # can recover without reading the source.
    for ext in ("xlsx", "xls", "csv", "tsv", "parquet", "json", "jsonl"):
        assert ext in msg


# --- TC-AN-2-04: xlsx with only a header row --------------------------------


def test_load_empty_xlsx_raises_malformed_with_kind(
    xlsx_empty_sheet_fixture: Path,
) -> None:
    from _shared import diagnostics, io

    with pytest.raises(diagnostics.MalformedFileError) as exc:
        io.load(xlsx_empty_sheet_fixture)
    assert exc.value.kind == "no_data_rows"
    assert exc.value.path == str(xlsx_empty_sheet_fixture)


# --- Multi-sheet handling (delegated to aggregation.py per ADR-007) ---------


def test_load_multi_sheet_without_sheet_raises_value_error(
    xlsx_multi_sheet_fixture: Path,
) -> None:
    """Multi-sheet xlsx without sheet= directs caller to aggregation.py.

    The diagnostic must mention ``aggregation`` so the caller can wire the
    next step without reading source. This guards the ADR-007 SRP split
    against drift — P2-C01b consumers rely on this hand-off contract.
    """
    from _shared import io

    with pytest.raises(ValueError) as exc:
        io.load(xlsx_multi_sheet_fixture)
    msg = str(exc.value).lower()
    assert "aggregation" in msg


def test_load_multi_sheet_with_explicit_sheet_loads_that_sheet(
    xlsx_multi_sheet_fixture: Path,
) -> None:
    from _shared import io

    frame = io.load(xlsx_multi_sheet_fixture, sheet="Q2")
    assert list(frame["id"]) == [4, 5, 6]


def test_load_multi_sheet_with_missing_sheet_raises_value_error(
    xlsx_multi_sheet_fixture: Path,
) -> None:
    """Missing sheet name surfaces the available sheet list in the diagnostic."""
    from _shared import io

    with pytest.raises(ValueError) as exc:
        io.load(xlsx_multi_sheet_fixture, sheet="Q99")
    msg = str(exc.value)
    assert "Q99" in msg
    for name in ("Q1", "Q2", "Q3"):
        assert name in msg


# --- TC-AN-42-01 / 02: encrypted xlsx refusal -------------------------------


def test_load_encrypted_xlsx_raises_encrypted_error_with_path(
    encrypted_xlsx_fixture: Path,
) -> None:
    from _shared import diagnostics, io

    with pytest.raises(diagnostics.EncryptedFileError) as exc:
        io.load(encrypted_xlsx_fixture)
    assert str(encrypted_xlsx_fixture) in str(exc.value)


# --- TC-AN-43-01 / 02 / 03: formula columns ---------------------------------


def test_load_returns_cached_values_from_formula_column(
    xlsx_formula_cached_values_fixture: Path,
) -> None:
    """TC-AN-43-01: load returns cached numeric, not formula string."""
    from _shared import io

    frame = io.load(xlsx_formula_cached_values_fixture)
    assert list(frame["total"]) == [10, 12]


def test_extract_formulas_returns_formula_strings(
    xlsx_formula_cached_values_fixture: Path,
) -> None:
    """TC-AN-43-02: extract_formulas returns {column, formula} entries."""
    from _shared import io

    formulas = io.extract_formulas(xlsx_formula_cached_values_fixture)
    assert {"column": "total", "formula": "=A2*B2"} in formulas


def test_extract_formulas_on_uncached_file_still_returns_formulas(
    xlsx_formula_uncached_values_fixture: Path,
) -> None:
    """TC-AN-43-03: formula recorded even when xlsx cached value is null."""
    from _shared import io

    formulas = io.extract_formulas(xlsx_formula_uncached_values_fixture)
    assert {"column": "total", "formula": "=A2*B2"} in formulas


def test_load_on_uncached_formula_returns_null_for_formula_cells(
    xlsx_formula_uncached_values_fixture: Path,
) -> None:
    """TC-AN-43-03: when no cached value exists, load returns null (NaN)."""
    from _shared import io

    frame = io.load(xlsx_formula_uncached_values_fixture)
    assert frame["total"].isna().all()


def test_extract_formulas_non_xlsx_returns_empty_list(csv_fixture: Path) -> None:
    """extract_formulas is xlsx-specific; other formats return []."""
    from _shared import io

    assert io.extract_formulas(csv_fixture) == []


# --- TC-AN-5-01 / 02: dependency check --------------------------------------


def test_check_dependencies_all_present_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from _shared import io

    # All deps currently installed → empty list. We do NOT monkeypatch here;
    # this test locks in the "happy path" so a future regression to
    # "returns None" or "raises on success" fails loudly.
    assert io.check_dependencies() == []


def test_check_dependencies_missing_one_reports_that_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-AN-5-01: pandas missing → ['pandas'] in canonical order."""
    import importlib.util as _stdlib_util

    from _shared import io

    real_find_spec = _stdlib_util.find_spec

    def fake_spec_finder(name: str) -> object | None:
        if name == "pandas":
            return None
        return real_find_spec(name)

    monkeypatch.setattr(io, "_spec_finder", fake_spec_finder)
    assert io.check_dependencies() == ["pandas"]


def test_check_dependencies_missing_multiple_returns_all(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-AN-5-02: pandas AND scipy missing → both listed, in canonical order."""
    import importlib.util as _stdlib_util

    from _shared import io

    missing_set = {"pandas", "scipy"}
    real_find_spec = _stdlib_util.find_spec

    def fake_spec_finder(name: str) -> object | None:
        if name in missing_set:
            return None
        return real_find_spec(name)

    monkeypatch.setattr(io, "_spec_finder", fake_spec_finder)
    result = io.check_dependencies()
    assert result == ["pandas", "scipy"], (
        "check_dependencies must preserve canonical order so diagnostic "
        "output is stable across invocations"
    )


def test_check_dependencies_uses_importable_names_not_pip_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """scikit-learn is importable as 'sklearn' — that's what we check and report.

    Orchestration (P5-C01) maps importable names back to pip names for the
    install command; io.check_dependencies is deliberately lower-level.
    """
    import importlib.util as _stdlib_util

    from _shared import io

    real_find_spec = _stdlib_util.find_spec

    def fake_spec_finder(name: str) -> object | None:
        if name == "sklearn":
            return None
        return real_find_spec(name)

    monkeypatch.setattr(io, "_spec_finder", fake_spec_finder)
    assert io.check_dependencies() == ["sklearn"]


# --- extract_formulas refuses encrypted files (review fix, F1) ---------------


def test_extract_formulas_on_encrypted_xlsx_raises_encrypted_error(
    encrypted_xlsx_fixture: Path,
) -> None:
    """AN-42 refusal applies to the formula-extraction path too.

    A consumer (provenance.py, P2-C03) would otherwise get a raw
    ``zipfile.BadZipFile`` when the provenance pass handled an encrypted
    file — bypassing the AN-42 contract.
    """
    from _shared import diagnostics, io

    with pytest.raises(diagnostics.EncryptedFileError):
        io.extract_formulas(encrypted_xlsx_fixture)


# --- CSV parser errors map to MalformedFileError (review fix, F6) ------------


def test_load_truncated_csv_raises_malformed_file_error(tmp_path: Path) -> None:
    """Cross-cutting line 891: truncated CSV → MalformedFileError.

    Without this mapping the orchestration layer gets a pandas-specific
    exception leak instead of the promised structured error. pandas is
    lenient about rows with fewer-than-header fields (it NaN-pads), so we
    exercise the ParserError path via an unterminated quoted string — the
    most definitive trigger for a C-parser tokenization failure.
    """
    from _shared import diagnostics, io

    bad_csv = tmp_path / "truncated.csv"
    bad_csv.write_text('"unclosed,b\n1,2\n', encoding="utf-8")
    with pytest.raises(diagnostics.MalformedFileError) as exc:
        io.load(bad_csv)
    assert exc.value.kind == "parser_error"


def test_load_empty_csv_raises_malformed_file_error(tmp_path: Path) -> None:
    from _shared import diagnostics, io

    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(diagnostics.MalformedFileError) as exc:
        io.load(empty)
    assert exc.value.kind == "no_data_rows"


def test_load_malformed_json_raises_malformed_file_error(tmp_path: Path) -> None:
    from _shared import diagnostics, io

    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(diagnostics.MalformedFileError) as exc:
        io.load(bad)
    assert exc.value.kind == "parser_error"


# --- .xls without xlrd produces a structured diagnostic (review fix, F7) -----


def test_load_xls_without_xlrd_raises_xls_engine_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """xlrd is optional. Without it, .xls support fails LOUDLY with the
    diagnostic ``kind`` needed to guide users to ``pip install xlrd``.
    """
    import importlib.util as _stdlib_util

    from _shared import diagnostics, io

    real_find_spec = _stdlib_util.find_spec

    def fake_spec_finder(name: str) -> object | None:
        if name == "xlrd":
            return None
        return real_find_spec(name)

    monkeypatch.setattr(io, "_spec_finder", fake_spec_finder)

    # Body content is irrelevant — the xls_engine_missing check runs before
    # any parser is invoked.
    xls_path = tmp_path / "legacy.xls"
    xls_path.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 128)
    with pytest.raises(diagnostics.MalformedFileError) as exc:
        io.load(xls_path)
    assert exc.value.kind == "xls_engine_missing"


# --- File-not-found / permission ---------------------------------------------


def test_load_missing_file_raises_file_not_found(tmp_path: Path) -> None:
    from _shared import io

    with pytest.raises(FileNotFoundError):
        io.load(tmp_path / "no-such-file.csv")
