"""Tests for `_shared/aggregation.py` — multi-sheet + multi-file (P2-C01b).

Covers AN-3 (three aggregation strategies: concat / per_file / comparative)
and the multi-sheet load primitive. TC-AN-3-01 (the AskUserQuestion prompt)
is orchestration (P5-*) — not tested here. TC-AN-3-03 (HTML section
structure) is renderer (P6-C04c) — this chunk only produces the data shapes
that renderer consumes.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


# --- load_sheets ------------------------------------------------------------


def test_load_sheets_returns_dict_per_sheet(xlsx_multi_sheet_fixture: Path) -> None:
    """Multi-sheet xlsx → one entry per sheet, each a non-empty frame."""
    from _shared import aggregation

    sheets = aggregation.load_sheets(xlsx_multi_sheet_fixture)
    assert set(sheets.keys()) == {"Q1", "Q2", "Q3"}
    for frame in sheets.values():
        assert len(frame) > 0


def test_load_sheets_single_sheet_returns_single_element_dict(
    xlsx_single_sheet_fixture: Path,
) -> None:
    from _shared import aggregation

    sheets = aggregation.load_sheets(xlsx_single_sheet_fixture)
    assert len(sheets) == 1


def test_load_sheets_on_encrypted_xlsx_raises_encrypted_error(
    encrypted_xlsx_fixture: Path,
) -> None:
    """The AN-42 contract propagates through aggregation — encrypted xlsx
    is refused on this path just as on io.load directly.
    """
    from _shared import aggregation, diagnostics

    with pytest.raises(diagnostics.EncryptedFileError):
        aggregation.load_sheets(encrypted_xlsx_fixture)


def test_load_sheets_accepts_string_path(xlsx_multi_sheet_fixture: Path) -> None:
    from _shared import aggregation

    sheets = aggregation.load_sheets(str(xlsx_multi_sheet_fixture))
    assert len(sheets) == 3


# --- aggregate: concat strategy ---------------------------------------------


def test_aggregate_concat_returns_dataframe_with_source_column(
    tmp_path: Path,
) -> None:
    from _shared import aggregation

    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    pd.DataFrame({"id": [1, 2], "val": [10, 20]}).to_csv(a, index=False)
    pd.DataFrame({"id": [3, 4], "val": [30, 40]}).to_csv(b, index=False)

    frame = aggregation.aggregate([a, b], "concat")
    assert isinstance(frame, pd.DataFrame)
    assert "__source_file__" in frame.columns
    assert len(frame) == 4
    assert set(frame["__source_file__"]) == {"a", "b"}


def test_aggregate_concat_keeps_only_shared_columns(tmp_path: Path) -> None:
    """Inner-join semantics: columns present in only one frame are dropped."""
    from _shared import aggregation

    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    pd.DataFrame({"id": [1, 2], "val": [10, 20], "extra_a": [100, 200]}).to_csv(
        a, index=False
    )
    pd.DataFrame({"id": [3, 4], "val": [30, 40], "extra_b": [300, 400]}).to_csv(
        b, index=False
    )

    frame = aggregation.aggregate([a, b], "concat")
    assert "extra_a" not in frame.columns
    assert "extra_b" not in frame.columns
    assert "id" in frame.columns
    assert "val" in frame.columns


def test_aggregate_concat_no_common_columns_raises_valueerror(tmp_path: Path) -> None:
    """TC-AN-3-02: no column overlap surfaces both column lists."""
    from _shared import aggregation

    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    pd.DataFrame({"alpha": [1, 2]}).to_csv(a, index=False)
    pd.DataFrame({"beta": [3, 4]}).to_csv(b, index=False)

    with pytest.raises(ValueError) as exc:
        aggregation.aggregate([a, b], "concat")
    msg = str(exc.value)
    assert "alpha" in msg
    assert "beta" in msg


def test_aggregate_concat_single_file_returns_frame_with_source_column(
    tmp_path: Path,
) -> None:
    from _shared import aggregation

    a = tmp_path / "a.csv"
    pd.DataFrame({"id": [1, 2]}).to_csv(a, index=False)

    frame = aggregation.aggregate([a], "concat")
    assert isinstance(frame, pd.DataFrame)
    assert list(frame["__source_file__"]) == ["a", "a"]


# --- aggregate: per_file strategy -------------------------------------------


def test_aggregate_per_file_returns_dict_keyed_by_file_stem(tmp_path: Path) -> None:
    from _shared import aggregation

    a = tmp_path / "trades_jan.csv"
    b = tmp_path / "trades_feb.csv"
    pd.DataFrame({"id": [1], "val": [10]}).to_csv(a, index=False)
    pd.DataFrame({"id": [2], "val_different": [20]}).to_csv(b, index=False)

    result = aggregation.aggregate([a, b], "per_file")
    assert isinstance(result, dict)
    assert set(result.keys()) == {"trades_jan", "trades_feb"}
    # Each frame preserves its NATIVE columns (no intersection).
    assert "val" in result["trades_jan"].columns
    assert "val_different" in result["trades_feb"].columns


# --- aggregate: comparative strategy ----------------------------------------


def test_aggregate_comparative_keeps_only_intersection_columns(tmp_path: Path) -> None:
    """Each frame retains only the shared columns for file-vs-file delta work.

    Column order MUST follow the first frame — downstream diffs depend on
    deterministic ordering. Asserting list equality (not set equality) locks
    this contract in against refactors that would drop the ordering
    guarantee and produce unstable renderer output.
    """
    from _shared import aggregation

    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    pd.DataFrame({"id": [1, 2], "shared": [10, 20], "only_a": [100, 200]}).to_csv(
        a, index=False
    )
    pd.DataFrame({"shared": [30, 40], "id": [3, 4], "only_b": [300, 400]}).to_csv(
        b, index=False
    )

    result = aggregation.aggregate([a, b], "comparative")
    assert isinstance(result, dict)
    assert set(result.keys()) == {"a", "b"}
    # First-frame order is ["id", "shared"] — the second frame's native
    # ["shared", "id"] ordering must NOT leak through.
    for frame in result.values():
        assert list(frame.columns) == ["id", "shared"]


def test_aggregate_concat_preserves_first_frame_column_order(tmp_path: Path) -> None:
    """concat output places shared columns in first-frame order; the
    ``__source_file__`` column appears after them.
    """
    from _shared import aggregation

    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    pd.DataFrame({"id": [1], "val": [10]}).to_csv(a, index=False)
    pd.DataFrame({"val": [20], "id": [2]}).to_csv(b, index=False)

    frame = aggregation.aggregate([a, b], "concat")
    # Shared columns in first-frame order, then __source_file__.
    assert list(frame.columns) == ["id", "val", "__source_file__"]


def test_aggregate_comparative_no_common_columns_raises_valueerror(
    tmp_path: Path,
) -> None:
    from _shared import aggregation

    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    pd.DataFrame({"alpha": [1]}).to_csv(a, index=False)
    pd.DataFrame({"beta": [2]}).to_csv(b, index=False)

    with pytest.raises(ValueError):
        aggregation.aggregate([a, b], "comparative")


# --- error paths ------------------------------------------------------------


def test_aggregate_unknown_strategy_raises_valueerror(tmp_path: Path) -> None:
    from _shared import aggregation

    a = tmp_path / "a.csv"
    pd.DataFrame({"id": [1]}).to_csv(a, index=False)

    with pytest.raises(ValueError) as exc:
        aggregation.aggregate([a], "unknown")
    msg = str(exc.value)
    assert "unknown" in msg
    for supported in ("concat", "per_file", "comparative"):
        assert supported in msg


def test_aggregate_empty_paths_raises_valueerror() -> None:
    from _shared import aggregation

    with pytest.raises(ValueError) as exc:
        aggregation.aggregate([], "concat")
    assert "no input files" in str(exc.value).lower()


def test_aggregate_accepts_string_paths(tmp_path: Path) -> None:
    """str paths work identically to Path objects, matching io.load's contract."""
    from _shared import aggregation

    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    pd.DataFrame({"id": [1]}).to_csv(a, index=False)
    pd.DataFrame({"id": [2]}).to_csv(b, index=False)

    frame = aggregation.aggregate([str(a), str(b)], "concat")
    assert isinstance(frame, pd.DataFrame)
    assert len(frame) == 2
