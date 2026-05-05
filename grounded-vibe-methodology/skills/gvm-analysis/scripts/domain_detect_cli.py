#!/usr/bin/env python3
"""CLI front-end for :mod:`_shared.domain_detect` (ADR-105).

Reads only the HEADER row of each input file and emits the three-key JSON
contract specified in ADR-105:

    { "matched": str|null, "signals": [str], "candidate_domain": str|null }

Used by the orchestration layer via subprocess. CLI (not
``python3 -c``) so CWD / PYTHONPATH semantics are explicit.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from _shared import domain_detect


_DEFAULT_INDUSTRY_DIR = (
    Path.home() / ".claude" / "skills" / "gvm-design-system" / "references" / "industry"
)


def _read_header_columns(path: Path) -> list[str]:
    """Return the column names of ``path`` without reading row data.

    Supports CSV, TSV, Parquet, and Excel via pandas. Only the header is
    read — no row values flow through this function.
    """
    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv"}:
        sep = "\t" if suffix == ".tsv" else ","
        return pd.read_csv(path, sep=sep, nrows=0).columns.tolist()
    if suffix == ".parquet":
        import pyarrow.parquet as pq

        return list(pq.read_schema(path).names)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path, nrows=0).columns.tolist()
    raise ValueError(f"unsupported input format: {path.suffix}")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect a GVM industry domain from input-file column names."
    )
    parser.add_argument(
        "--input",
        action="append",
        required=True,
        help="Path to an input file (CSV / TSV / Parquet / XLSX). Repeatable.",
    )
    parser.add_argument(
        "--industry-dir",
        default=str(_DEFAULT_INDUSTRY_DIR),
        help=(
            "Directory of industry-frontmatter .md files "
            f"(default: {_DEFAULT_INDUSTRY_DIR})"
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    all_columns: list[str] = []
    for entry in args.input:
        path = Path(entry)
        if not path.exists():
            print(f"ERROR: input not found: {path}", file=sys.stderr)
            return 2
        try:
            all_columns.extend(_read_header_columns(path))
        except Exception as exc:  # noqa: BLE001 — CLI boundary
            print(f"ERROR: failed to read header of {path}: {exc}", file=sys.stderr)
            return 2

    result = domain_detect.detect(all_columns, industry_dir=Path(args.industry_dir))
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
