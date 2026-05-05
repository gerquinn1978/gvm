"""Aggregation wiring (P20-C01).

Asserts that ``analyse.main`` invokes ``_shared.aggregation.aggregate``
when given multiple ``--input`` flags — the wiring gap surfaced by the
post-v2.0.0 audit (same Bohrbug class as the chart-wiring gap closed in
P19).

Five assertions:

1. ``test_two_file_concat_produces_single_findings`` — two CSV inputs
   with overlapping columns + ``--aggregation-strategy concat`` (the
   default) produce one ``findings.json`` whose column entries include
   ``__source_file__`` (the per-row provenance column added by
   ``aggregation.aggregate``).
2. ``test_provenance_records_every_input_file`` — ``provenance.input_files``
   carries one entry per supplied ``--input`` flag, each with its own
   SHA-256.
3. ``test_single_input_unchanged`` — single-file invocation produces
   findings byte-equivalent (modulo timestamp / lib_versions) to the
   pre-P20 single-input path. Backward compatibility.
4. ``test_per_file_strategy_refused`` — ``--aggregation-strategy per_file``
   is rejected by argparse before main runs (the engine is single-frame;
   per_file / comparative are orchestration-layer concerns).
5. ``test_sheet_flag_forwards_to_io_load`` — ``--sheet`` flag is
   accepted; with a single CSV input (no sheets) the flag is benign;
   the contract is that the value reaches ``io.load`` via kwarg.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


def _build_two_file_fixture(tmp_path: Path) -> tuple[Path, Path]:
    """Two CSVs with overlapping numeric columns. Concat produces a
    frame with both rows; the engine sees enough numeric content to
    populate per-column stats."""
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    pd.DataFrame(
        {
            "score": [1.0, 2.0, 3.0, 4.0, 5.0],
            "label": ["x", "y", "z", "x", "y"],
        }
    ).to_csv(a, index=False)
    pd.DataFrame(
        {
            "score": [10.0, 20.0, 30.0, 40.0, 50.0],
            "label": ["p", "q", "r", "p", "q"],
        }
    ).to_csv(b, index=False)
    return a, b


def _run_engine(tmp_path: Path, *args: str) -> dict:
    import analyse
    from _shared import findings

    out = tmp_path / "out"
    rc = analyse.main(
        list(args) + ["--output-dir", str(out), "--mode", "explore", "--seed", "42"]
    )
    assert rc == 0, "analyse.main failed"
    return findings.read_findings(out / "findings.json")


def test_two_file_concat_produces_single_findings(tmp_path: Path) -> None:
    """Two-file concat produces one findings.json with __source_file__
    visible as a column entry."""
    a, b = _build_two_file_fixture(tmp_path)

    data = _run_engine(tmp_path, "--input", str(a), "--input", str(b))

    column_names = {c.get("name") for c in data["columns"]}
    assert "__source_file__" in column_names, (
        f"concat aggregation did not add __source_file__ column; "
        f"found columns: {sorted(column_names)}"
    )
    assert "score" in column_names
    assert "label" in column_names


def test_provenance_records_every_input_file(tmp_path: Path) -> None:
    """provenance.input_files has one entry per --input flag."""
    a, b = _build_two_file_fixture(tmp_path)

    data = _run_engine(tmp_path, "--input", str(a), "--input", str(b))

    input_files = data["provenance"]["input_files"]
    assert len(input_files) == 2, (
        f"expected 2 input_files entries, got {len(input_files)}"
    )

    paths = {entry["path"] for entry in input_files}
    assert str(a) in paths, f"input a missing from provenance.input_files: {paths}"
    assert str(b) in paths, f"input b missing from provenance.input_files: {paths}"

    sha_a = next(e["sha256"] for e in input_files if e["path"] == str(a))
    sha_b = next(e["sha256"] for e in input_files if e["path"] == str(b))
    assert sha_a != sha_b, "two distinct files produced the same SHA-256"
    assert len(sha_a) == 64 and len(sha_b) == 64, "SHA-256 not hex-64"


def test_single_input_unchanged(tmp_path: Path) -> None:
    """Single-file invocation: all P15-era keys present, single
    input_files entry, no __source_file__ column. Backward
    compatibility — pre-P20 callers see no behaviour change."""
    a, _ = _build_two_file_fixture(tmp_path)

    data = _run_engine(tmp_path, "--input", str(a))

    column_names = {c.get("name") for c in data["columns"]}
    assert "__source_file__" not in column_names, (
        "single-input path should not produce __source_file__ column "
        "(that column is added only by aggregation.aggregate)"
    )
    assert {"score", "label"}.issubset(column_names)
    assert len(data["provenance"]["input_files"]) == 1


def test_per_file_strategy_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """argparse choices=['concat'] rejects per_file / comparative. The
    engine is single-frame; the dict-returning strategies are out of
    scope for P20-C01."""
    import analyse

    a, b = _build_two_file_fixture(tmp_path)
    out = tmp_path / "out"

    with pytest.raises(SystemExit) as exc_info:
        analyse.main(
            [
                "--input",
                str(a),
                "--input",
                str(b),
                "--output-dir",
                str(out),
                "--mode",
                "explore",
                "--aggregation-strategy",
                "per_file",
            ]
        )
    # argparse exits with 2 on invalid arguments
    assert exc_info.value.code == 2

    err = capsys.readouterr().err
    assert "per_file" in err.lower() or "invalid choice" in err.lower(), err


def test_sheet_with_multi_input_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """--sheet alongside multiple --input files is refused with exit 2.
    The aggregation pipeline loads each file via the default sheet;
    silently discarding --sheet here would analyse the wrong sheet on
    every file with no provenance warning. Fail loud."""
    import analyse

    a, b = _build_two_file_fixture(tmp_path)
    out = tmp_path / "out"

    rc = analyse.main(
        [
            "--input",
            str(a),
            "--input",
            str(b),
            "--output-dir",
            str(out),
            "--mode",
            "explore",
            "--sheet",
            "Sheet1",
        ]
    )
    assert rc == 2, f"expected exit 2 on --sheet + multi-input, got {rc}"

    err = capsys.readouterr().err
    assert "--sheet" in err and "multi" in err.lower(), err


def test_sheet_flag_forwards_to_io_load(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--sheet flag forwards into io.load via kwarg. Verified by spying
    on io.load and asserting the kwarg reached it."""
    import analyse
    from _shared import io as io_module

    a, _ = _build_two_file_fixture(tmp_path)
    out = tmp_path / "out"

    captured: dict[str, object] = {}
    real_load = io_module.load

    def _spy(path, sheet=None, **kwargs):
        captured["sheet"] = sheet
        captured["path"] = path
        return real_load(path, sheet=sheet, **kwargs)

    monkeypatch.setattr(io_module, "load", _spy)
    # analyse imports io_module via `from _shared import io as io_module`,
    # so patch the binding in analyse's namespace too.
    monkeypatch.setattr(analyse, "io_module", io_module)

    rc = analyse.main(
        [
            "--input",
            str(a),
            "--output-dir",
            str(out),
            "--mode",
            "explore",
            "--seed",
            "42",
            "--sheet",
            "Sheet2",
        ]
    )
    assert rc == 0
    assert captured.get("sheet") == "Sheet2", (
        f"--sheet flag did not forward to io.load; captured={captured}"
    )
