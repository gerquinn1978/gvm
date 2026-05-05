"""Panel-E findings JSON sidecar serialiser (P8-C09).

Writes `code-review/code-review-NNN.findings.json` (NDJSON, one JSON object per
line) alongside the human-readable `code-review-NNN.html`. The 9-field
`PanelEFinding` shape is honesty-triad ADR-104 verbatim; the JSON sidecar is
the mechanical-consumption surface read by `/gvm-test`'s `_review_parser` for
VV-4(a). This module owns serialisation only — `signature` is computed by the
caller via `_sd5_promotion.compute_signature(...)`.

Atomic write: write to `<path>.tmp`, then `os.replace`. On any failure during
write or replace, the `.tmp` file is unlinked so stale partials never accumulate.
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

Severity = Literal["Critical", "Important", "Minor", "Suggestion"]
ViolationType = Literal["unregistered", "expired", "namespace_violation"]

_FILENAME_PREFIX = "code-review-"
_HTML_SUFFIX = ".html"
_JSON_SUFFIX = ".findings.json"
_NNN_WIDTH = 3
_MAX_NNN = 999


class FindingsSerialiserError(Exception):
    """Base class for findings-serialiser errors."""


class MissingDirectoryError(FindingsSerialiserError):
    """Raised when the code-review directory does not exist."""


class EmptyReviewNumberError(FindingsSerialiserError):
    """Raised when NNN is exhausted (existing 999, no slot left)."""


@dataclass(frozen=True)
class PanelEFinding:
    expert: str
    severity: Severity
    file_line: str
    issue: str
    spec_reference: str
    fix: str
    violation_type: ViolationType
    symbol: str
    signature: str


def find_next_review_number(code_review_dir: Path) -> str:
    """Return the next zero-padded three-digit NNN for the directory.

    Scans both `code-review-NNN.html` and `code-review-NNN.findings.json`
    filenames; returns the highest existing NNN + 1. Returns "001" if no
    matching files exist. Raises `EmptyReviewNumberError` once 999 is reached.
    """

    if not code_review_dir.is_dir():
        raise MissingDirectoryError(
            f"code-review directory does not exist: {code_review_dir}"
        )

    try:
        entries = list(code_review_dir.iterdir())
    except OSError as exc:
        raise MissingDirectoryError(
            f"cannot read code-review directory: {code_review_dir}: {exc}"
        ) from exc

    highest = 0
    for entry in entries:
        if not entry.is_file():
            continue
        name = entry.name
        if not name.startswith(_FILENAME_PREFIX):
            continue
        if name.endswith(_HTML_SUFFIX):
            digits = name[len(_FILENAME_PREFIX) : -len(_HTML_SUFFIX)]
        elif name.endswith(_JSON_SUFFIX):
            digits = name[len(_FILENAME_PREFIX) : -len(_JSON_SUFFIX)]
        else:
            continue
        if len(digits) != _NNN_WIDTH or not digits.isdigit():
            continue
        n = int(digits)
        if n > highest:
            highest = n

    next_n = highest + 1
    if next_n > _MAX_NNN:
        raise EmptyReviewNumberError(
            f"NNN exhausted at {_MAX_NNN}: no slot remaining in {code_review_dir}"
        )
    return str(next_n).zfill(_NNN_WIDTH)


def serialise_findings(findings: Sequence[PanelEFinding], path: Path) -> None:
    """Write findings as NDJSON (one JSON object per line) at `path`.

    Atomic: write to `<path>.tmp`, then `os.replace` over the target. UTF-8
    explicit. Empty `findings` writes a zero-byte file (downstream parsers
    treat this as "no findings"). Raises `FindingsSerialiserError` if the
    parent directory is missing.
    """

    parent = path.parent
    if not parent.is_dir():
        raise FindingsSerialiserError(f"parent directory does not exist: {parent}")

    tmp_path = path.with_name(path.name + ".tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as fh:
            for f in findings:
                fh.write(json.dumps(asdict(f), ensure_ascii=False))
                fh.write("\n")
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
