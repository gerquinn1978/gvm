"""Mapping CSV reader/writer.

Anonymisation-pipeline ADR-405 (P14-C01, originally P7-C01 in the
gvm-analysis impl-guide; renumbered to avoid plugin-build clash).

The mapping CSV is the user's chain-of-custody artefact; values are stored
raw (unescaped). Any HTML-escaping is :mod:`de_anonymise.py`'s job at
substitution time (post-design-review fix M-12). Loaded :class:`MappingData`
records are frozen so downstream consumers cannot mutate the canonical
mapping in-place.

Public API
----------

* :class:`MappingData` — frozen triple ``(token_to_value, columns, rows)``.
  Post-R4 fix CRITICAL-T5: previous return type ``dict[token, value]``
  discarded ``columns`` that :func:`tokens.build_match_regex` needs.
* :func:`load(path)` — read a mapping CSV; raises
  :class:`_shared.diagnostics.MalformedFileError` on missing file or
  wrong/missing header.
* :func:`write(path, rows)` — write a mapping CSV; emits the canonical
  ``column,original_value,token`` header followed by the supplied rows.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from _shared.diagnostics import MalformedFileError

_HEADER: tuple[str, str, str] = ("column", "original_value", "token")


@dataclass(frozen=True)
class MappingData:
    """Frozen record of a loaded mapping CSV.

    ``token_to_value`` powers de-anonymisation substitution. ``columns``
    is the deduplicated, insertion-order-preserved list of column names —
    consumed by :func:`tokens.build_match_regex`. ``rows`` is the raw
    ordered list of rows (each a dict keyed by the canonical header)
    preserved so reviewers can diff the loaded view against the file.

    ``frozen=True`` blocks field reassignment (e.g. ``data.columns = []``).
    The contained collections are deliberately exposed as the standard
    ``dict`` / ``list`` types so callers can iterate them naturally;
    callers MUST NOT mutate them in place. If you need a defensive copy,
    write one at the call site.
    """

    token_to_value: dict[str, str]
    columns: list[str]
    rows: list[dict[str, str]] = field(default_factory=list)


def write(path: Path, rows: list[tuple[str, str, str]]) -> None:
    """Write the mapping CSV at ``path``.

    Each row in ``rows`` is the triple ``(column, original_value, token)``.
    Uses ``csv.QUOTE_MINIMAL`` so simple values are written unquoted (the
    spec example), and values containing commas / quotes / newlines are
    quoted automatically.
    """
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(_HEADER)
        for row in rows:
            writer.writerow(row)


def load(path: Path) -> MappingData:
    """Read the mapping CSV at ``path``.

    Raises :class:`MalformedFileError` if the file does not exist, has no
    header, or has the wrong header. The malformation ``kind`` is
    ``"parser_error"`` so :func:`format_diagnostic` renders the standard
    encoding/delimiter/quoting guidance.
    """
    if not path.exists():
        raise MalformedFileError(path, row=None, col=None, kind="parser_error")

    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        try:
            header = next(reader)
        except StopIteration:
            raise MalformedFileError(
                path, row=None, col=None, kind="parser_error"
            ) from None
        if tuple(header) != _HEADER:
            raise MalformedFileError(path, row=1, col=None, kind="parser_error")

        token_to_value: dict[str, str] = {}
        columns: list[str] = []
        rows: list[dict[str, str]] = []
        seen_columns: set[str] = set()
        for row_index, row in enumerate(reader, start=2):
            if len(row) != 3:
                raise MalformedFileError(
                    path, row=row_index, col=None, kind="parser_error"
                )
            column, original_value, token = row
            token_to_value[token] = original_value
            if column not in seen_columns:
                seen_columns.add(column)
                columns.append(column)
            rows.append(
                {
                    "column": column,
                    "original_value": original_value,
                    "token": token,
                }
            )

    return MappingData(token_to_value=token_to_value, columns=columns, rows=rows)
