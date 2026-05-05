"""Shared pytest fixtures for /gvm-analysis unit tests.

Fixtures live as code (not binary blobs) wherever possible, so the fixture
intent stays visible in the repo. The encrypted-xlsx fixture synthesises a
CFBF/OLE-magic byte sequence (what a real encrypted xlsx is at the byte
level) rather than invoking a decryption library to produce one — we
deliberately depend on no cryptography tooling in tests so the same
refusal contract is exercised on every machine.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def sample_frame() -> pd.DataFrame:
    """A tiny deterministic frame reused across format tests."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3],
            "category": ["a", "b", "a"],
            "amount": [10.5, 20.0, 30.25],
        }
    )


@pytest.fixture
def csv_fixture(tmp_path: Path, sample_frame: pd.DataFrame) -> Path:
    path = tmp_path / "tiny.csv"
    sample_frame.to_csv(path, index=False)
    return path


@pytest.fixture
def tsv_fixture(tmp_path: Path, sample_frame: pd.DataFrame) -> Path:
    path = tmp_path / "tiny.tsv"
    sample_frame.to_csv(path, index=False, sep="\t")
    return path


@pytest.fixture
def parquet_fixture(tmp_path: Path, sample_frame: pd.DataFrame) -> Path:
    path = tmp_path / "tiny.parquet"
    sample_frame.to_parquet(path, index=False)
    return path


@pytest.fixture
def json_fixture(tmp_path: Path, sample_frame: pd.DataFrame) -> Path:
    path = tmp_path / "tiny.json"
    sample_frame.to_json(path, orient="records")
    return path


@pytest.fixture
def jsonl_fixture(tmp_path: Path, sample_frame: pd.DataFrame) -> Path:
    path = tmp_path / "tiny.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for row in sample_frame.to_dict(orient="records"):
            fh.write(json.dumps(row) + "\n")
    return path


@pytest.fixture
def xlsx_single_sheet_fixture(tmp_path: Path, sample_frame: pd.DataFrame) -> Path:
    path = tmp_path / "single.xlsx"
    sample_frame.to_excel(path, index=False, sheet_name="Sheet1")
    return path


@pytest.fixture
def xlsx_multi_sheet_fixture(tmp_path: Path, sample_frame: pd.DataFrame) -> Path:
    path = tmp_path / "multi.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        sample_frame.to_excel(writer, index=False, sheet_name="Q1")
        sample_frame.assign(id=[4, 5, 6]).to_excel(writer, index=False, sheet_name="Q2")
        sample_frame.assign(id=[7, 8, 9]).to_excel(writer, index=False, sheet_name="Q3")
    return path


@pytest.fixture
def xlsx_empty_sheet_fixture(tmp_path: Path) -> Path:
    """xlsx whose only sheet has a header row but no data rows (TC-AN-2-04)."""
    path = tmp_path / "empty.xlsx"
    pd.DataFrame(columns=["id", "category", "amount"]).to_excel(
        path, index=False, sheet_name="Sheet1"
    )
    return path


def _build_formula_xlsx(path: Path, *, cache_present: bool) -> None:
    """Write an xlsx whose ``total`` column carries formulas and, optionally,
    pre-populated ``<v>`` cached values.

    openpyxl never evaluates formulas, so the only way to produce a fixture
    where ``data_only=True`` reads a cached numeric value is to inject the
    ``<v>`` tag into the sheet XML directly. openpyxl also omits None cells
    entirely from the sheet XML, so the fixture first writes numeric
    placeholders (``-999999``) and then substitutes those cells with the
    target formula (+ optional cached value) in the archive. When
    ``cache_present`` is False the formula cell has no ``<v>`` tag so the
    cached read returns None — exercising the TC-AN-43-03
    "never-evaluated" codepath.
    """
    import io as _io
    import zipfile
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["a", "b", "total"])
    ws.append([2, 5, -999999])
    ws.append([3, 4, -999998])
    wb.save(path)

    with zipfile.ZipFile(path, "r") as zf:
        sheet_xml = zf.read("xl/worksheets/sheet1.xml").decode("utf-8")

    if cache_present:
        c2_replacement = '<c r="C2"><f>A2*B2</f><v>10</v></c>'
        c3_replacement = '<c r="C3"><f>A3*B3</f><v>12</v></c>'
    else:
        c2_replacement = '<c r="C2"><f>A2*B2</f></c>'
        c3_replacement = '<c r="C3"><f>A3*B3</f></c>'

    sheet_xml = sheet_xml.replace(
        '<c r="C2" t="n"><v>-999999</v></c>', c2_replacement
    ).replace('<c r="C3" t="n"><v>-999998</v></c>', c3_replacement)

    assert "<f>A2*B2</f>" in sheet_xml, (
        "formula fixture injection failed; inspect the openpyxl xlsx output "
        "format — the <c> cell tag format may have changed"
    )

    out_buffer = _io.BytesIO()
    with zipfile.ZipFile(path, "r") as zf_in:
        with zipfile.ZipFile(out_buffer, "w", zipfile.ZIP_DEFLATED) as zf_out:
            for item in zf_in.infolist():
                data = zf_in.read(item.filename)
                if item.filename == "xl/worksheets/sheet1.xml":
                    data = sheet_xml.encode("utf-8")
                zf_out.writestr(item, data)
    path.write_bytes(out_buffer.getvalue())


@pytest.fixture
def xlsx_formula_cached_values_fixture(tmp_path: Path) -> Path:
    """xlsx with formulas AND pre-populated <v> cached values.

    Represents the common case: a file previously opened and saved in
    Excel (TC-AN-43-01 / TC-AN-43-02).
    """
    path = tmp_path / "formulas_cached.xlsx"
    _build_formula_xlsx(path, cache_present=True)
    return path


@pytest.fixture
def xlsx_formula_uncached_values_fixture(tmp_path: Path) -> Path:
    """xlsx with formulas but no <v> cached value tags.

    Represents a programmatically-created file whose formulas have never
    been evaluated by Excel (TC-AN-43-03).
    """
    path = tmp_path / "formulas_uncached.xlsx"
    _build_formula_xlsx(path, cache_present=False)
    return path


@pytest.fixture
def encrypted_xlsx_fixture(tmp_path: Path) -> Path:
    """CFBF/OLE-structured xlsx equivalent to a password-protected file.

    A real encrypted xlsx is a Compound File Binary Format (CFBF / OLE)
    container, not a zip archive — that is why openpyxl raises
    ``zipfile.BadZipFile`` when it tries to unzip one. For TC-AN-42-01 the
    only thing the loader MUST detect is the OLE magic header; the
    subsequent bytes are irrelevant to the encryption-refusal contract. We
    write the canonical 8-byte OLE magic followed by padding so the file is
    byte-indistinguishable from a real encrypted xlsx at the level the
    loader inspects.
    """
    path = tmp_path / "encrypted.xlsx"
    ole_magic = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    path.write_bytes(ole_magic + b"\x00" * 504)
    return path
