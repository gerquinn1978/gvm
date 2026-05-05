#!/usr/bin/env python3
"""Pre-analysis anonymisation script (anonymisation-pipeline ADR-401/402/403).

P14-C02 (originally P7-C02 in the gvm-analysis impl-guide; renumbered to
avoid clashing with the GVM plugin v2.0.0 build's audit trail).

Standalone CLI: tokenises the user-named categorical columns of a tabular
input file, writes an anonymised copy in the same format alongside a
chain-of-custody mapping CSV. The script is deliberately external to
``/gvm-analysis`` so the LLM is never in the chain of custody (ADR-401).

Exit codes
----------
* ``0`` — anonymised file + mapping CSV written.
* ``1`` — diagnosed user error (risky path, numeric column, TOK_ collision,
  unknown column, malformed config). Diagnostic emitted to stderr.
* ``2`` — unexpected internal error (uncaught exception).

The CLI exposes :func:`main(argv)` for in-process testing — pass
``argv=None`` to use ``sys.argv[1:]``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

import pandas as pd
import yaml

from _shared import io as io_module
from _shared import mapping as mapping_module
from _shared import path_check
from _shared.diagnostics import (
    ColumnNotFoundError,
    MalformedFileError,
    RiskyMappingPathError,
    _format_block,
    format_diagnostic,
)
from _shared.tokens import TOK_PREFIX, make_token


class MalformedConfigError(Exception):
    """Raised for ``--config`` YAML schema violations.

    Carries a pre-rendered diagnostic block built via
    :func:`_shared.diagnostics._format_block` so the message printed on
    stderr matches the canonical ERROR / What-went-wrong / What-to-try
    format used by every other diagnosed user error in the pipeline
    (anonymisation-pipeline ADR-404 prose).
    """

    def __init__(self, path: Path, summary: str, what: str, try_: str) -> None:
        self.path = path
        super().__init__(_format_block(summary=summary, what=what, try_=try_))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Tokenise categorical columns of a tabular file. Writes an "
            "anonymised copy + mapping CSV. Numeric columns pass through "
            "unchanged."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Input file (csv/tsv/xlsx/xls/parquet/json/jsonl).",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output path for the anonymised copy. Same suffix as --input.",
    )
    parser.add_argument(
        "--mapping-out",
        required=True,
        type=Path,
        help="Path for the mapping CSV (column,original_value,token).",
    )
    parser.add_argument(
        "--cols",
        default=None,
        type=lambda s: [c.strip() for c in s.split(",") if c.strip()],
        help=(
            "Comma-separated categorical column names to anonymise. "
            "Overridden by --config if both supplied."
        ),
    )
    parser.add_argument(
        "--config",
        default=None,
        type=Path,
        help=(
            "YAML file with 'columns:' list. If given, takes precedence over --cols."
        ),
    )
    parser.add_argument(
        "--i-accept-the-risk",
        action="store_true",
        help="Bypass --mapping-out path-risk validation (ADR-404).",
    )
    parser.add_argument(
        "--allow-tok-prefix",
        action="store_true",
        help=(
            "Permit input cells that already contain 'TOK_'. Default is to "
            "refuse — the de-anonymisation step would match them too."
        ),
    )
    parser.add_argument(
        "--claude-settings-path",
        default=None,
        type=Path,
        help=(
            "Path to .claude/settings.json for additionalDirectories lookup. "
            "Defaults to ~/.claude/settings.json. Test-injectable."
        ),
    )
    return parser


def _load_columns_from_config(config_path: Path) -> list[str]:
    """Parse a YAML config and extract the ``columns:`` list.

    Raises :class:`MalformedFileError` (kind=parser_error) on missing key,
    wrong type, or unparseable YAML — routed through ``format_diagnostic``
    for consistent output.
    """
    try:
        text = config_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise MalformedFileError(
            config_path, row=None, col=None, kind="parser_error"
        ) from None
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        raise MalformedFileError(
            config_path, row=None, col=None, kind="parser_error"
        ) from None
    if not isinstance(data, dict) or "columns" not in data:
        raise MalformedConfigError(
            path=config_path,
            summary=f"config {config_path}: missing required 'columns:' key.",
            what=(
                "The --config YAML must declare a top-level 'columns:' list "
                "naming the categorical columns to anonymise."
            ),
            try_=(
                "Add a 'columns:' block to the YAML, e.g.:\n"
                "  columns:\n"
                "    - department\n"
                "    - employee_name"
            ),
        )
    columns = data["columns"]
    if not isinstance(columns, list) or not all(isinstance(c, str) for c in columns):
        raise MalformedConfigError(
            path=config_path,
            summary=f"config {config_path}: 'columns:' must be a list of strings.",
            what=(
                "Found 'columns:' but the value is not a list of strings — "
                "one of the entries is a non-string type or the value is "
                "scalar."
            ),
            try_=(
                "Quote each column name as a string under a YAML list, e.g.:\n"
                "  columns:\n"
                "    - 'department'\n"
                "    - 'employee_name'"
            ),
        )
    return [str(c) for c in columns]


def _check_columns_exist(df: pd.DataFrame, columns: list[str]) -> None:
    """Raise :class:`ColumnNotFoundError` for the first unknown column."""
    known = list(df.columns)
    for col in columns:
        if col not in known:
            raise ColumnNotFoundError(col, known)


def _check_columns_categorical(df: pd.DataFrame, columns: list[str]) -> None:
    """Refuse numeric or temporal columns per ADR-402.

    Numeric values are the analytical target — tokenising them would
    break the analysis. The check covers:

    * standard NumPy numeric dtypes (int*/uint*/float*/complex*) — flagged
      by ``is_numeric_dtype``;
    * pandas nullable extension dtypes (``Int64``, ``Float64``, ``UInt32``,
      etc.) — flagged by the same call (``is_numeric_dtype`` returns True
      for nullable arithmetic types in pandas ≥ 1.0);
    * datetime / timedelta columns — flagged by ``is_datetime64_any_dtype``
      and ``is_timedelta64_dtype``. Tokenising a date would break time-
      series analyses just as silently as tokenising a number.
    """
    for col in columns:
        series = df[col]
        if (
            pd.api.types.is_numeric_dtype(series)
            or pd.api.types.is_datetime64_any_dtype(series)
            or pd.api.types.is_timedelta64_dtype(series)
        ):
            raise ValueError(
                f"refusing to anonymise non-categorical column '{col}' "
                f"(dtype={series.dtype}): numeric/temporal values pass "
                "through unchanged (ADR-402). Pass only categorical "
                "(string/object/category dtype) columns to --cols."
            )


def _scan_for_tok_prefix(df: pd.DataFrame) -> list[tuple[str, int, str]]:
    """Return ``[(column, row_index, value)]`` for every cell containing TOK_PREFIX.

    String-cast each cell so we catch values stored as object dtype
    holding mixed types. Empty list = no collisions.
    """
    hits: list[tuple[str, int, str]] = []
    for col in df.columns:
        series = df[col].astype("string")
        mask = series.fillna("").str.contains(TOK_PREFIX, regex=False)
        for idx in series.index[mask]:
            hits.append((col, int(idx), str(series.loc[idx])))
    return hits


def _tokenise_column(df: pd.DataFrame, col: str) -> list[tuple[str, str, str]]:
    """Replace ``df[col]`` with column-prefixed tokens; return mapping rows.

    Preserves first-occurrence order for stability (TC-AN-36-04). NaN
    cells are left as NaN — they have no original value to tokenise.
    """
    unique_values = df[col].dropna().drop_duplicates().tolist()
    total = len(unique_values)
    value_to_token: dict[str, str] = {}
    rows: list[tuple[str, str, str]] = []
    for idx, value in enumerate(unique_values, start=1):
        token = make_token(col, idx, total=total)
        value_to_token[value] = token
        rows.append((col, str(value), token))

    df[col] = df[col].map(lambda v: value_to_token.get(v, v) if pd.notna(v) else v)
    return rows


def _write_dataframe(df: pd.DataFrame, path: Path) -> None:
    """Write ``df`` to ``path`` matching the suffix.

    Mirrors the loader dispatch in ``_shared/io.py``; pandas writers are
    used directly (the project does not have a shared writer module).
    """
    suffix = path.suffix.lower().lstrip(".")
    path.parent.mkdir(parents=True, exist_ok=True)
    if suffix == "csv":
        df.to_csv(path, index=False)
    elif suffix == "tsv":
        df.to_csv(path, sep="\t", index=False)
    elif suffix == "parquet":
        df.to_parquet(path, index=False)
    elif suffix in {"xlsx", "xls"}:
        df.to_excel(path, index=False)
    elif suffix == "json":
        df.to_json(path, orient="records")
    elif suffix == "jsonl":
        df.to_json(path, orient="records", lines=True)
    else:
        raise ValueError(
            f"unsupported output extension: .{suffix} "
            "(supported: csv, tsv, parquet, xlsx, xls, json, jsonl)"
        )


def _resolve_columns(args: argparse.Namespace) -> list[str]:
    """Pick column list from --config (precedence) or --cols.

    Raises ``ValueError`` if neither is supplied — argparse cannot enforce
    "one of two" without a custom group, and we want the diagnostic
    routed through stderr like every other user error.
    """
    if args.config is not None:
        return _load_columns_from_config(args.config)
    if args.cols:
        return args.cols
    raise ValueError(
        "no columns specified — supply --cols col1,col2,... or --config "
        "config.yaml with a 'columns:' list."
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        columns = _resolve_columns(args)
    except MalformedConfigError as exc:
        # Pre-rendered structured diagnostic (ERROR / What / What-to-try).
        print(str(exc), file=sys.stderr)
        return 1
    except MalformedFileError as exc:
        print(format_diagnostic(exc), file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    try:
        path_check.validate(
            args.mapping_out,
            accept_risk=args.i_accept_the_risk,
            claude_settings_path=args.claude_settings_path,
        )
    except RiskyMappingPathError as exc:
        print(format_diagnostic(exc), file=sys.stderr)
        return 1

    try:
        df = io_module.load(args.input)
    except (FileNotFoundError, ValueError, MalformedFileError) as exc:
        if isinstance(exc, MalformedFileError):
            print(format_diagnostic(exc), file=sys.stderr)
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    try:
        _check_columns_exist(df, columns)
    except ColumnNotFoundError as exc:
        print(format_diagnostic(exc), file=sys.stderr)
        return 1

    try:
        _check_columns_categorical(df, columns)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    hits = _scan_for_tok_prefix(df)
    if hits:
        first_col, first_row, first_value = hits[0]
        if not args.allow_tok_prefix:
            print(
                f"ERROR: input contains 'TOK_' prefix at column "
                f"'{first_col}' row {first_row} (value: {first_value!r}); "
                f"{len(hits)} cell(s) total. The de-anonymisation step is "
                "a regex find-replace and would match these too. Pass "
                "--allow-tok-prefix if you have audited the risk.",
                file=sys.stderr,
            )
            return 1
        print(
            f"WARNING: --allow-tok-prefix set; {len(hits)} cell(s) already "
            f"contain 'TOK_' (first at column '{first_col}' row {first_row}: "
            f"{first_value!r}). De-anonymisation may produce unexpected "
            "results.",
            file=sys.stderr,
        )

    mapping_rows: list[tuple[str, str, str]] = []
    for col in columns:
        mapping_rows.extend(_tokenise_column(df, col))

    # Pre-create both parent directories before any write so permission
    # errors fail fast — surface them BEFORE the anonymised file is
    # written, not between the two writes.
    args.mapping_out.parent.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Spec flow steps 7→8 (anonymisation-pipeline ADR-402, lines 199-205):
    # write the anonymised dataframe first, then the mapping CSV. Rerun
    # is deterministic (TC-AN-36-04) so a failure between these two
    # writes is recoverable; the reverse order would leave a mapping
    # orphaned with no anonymised counterpart (Anderson:
    # chain-of-custody clarity).
    _write_dataframe(df, args.output)
    mapping_module.write(args.mapping_out, mapping_rows)

    print(
        f"anonymised {len(columns)} column(s), {len(mapping_rows)} unique "
        f"value(s); output: {args.output}; mapping: {args.mapping_out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
