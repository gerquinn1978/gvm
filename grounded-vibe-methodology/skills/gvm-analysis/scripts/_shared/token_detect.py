"""AN-40 token-pattern detection (anonymisation-pipeline ADR-406).

P14-C04 (originally P7-C04 in the gvm-analysis impl-guide; renumbered).

Detection runs after file loading: each column of the loaded DataFrame is
scanned for the canonical token regex ``^TOK_[a-z0-9_]+_\\d{3,}$``. A
column is flagged as already anonymised when at least :data:`THRESHOLD`
of its non-null values match.

The result is purely informational — surfaced into
``findings.json::provenance.anonymised_input_detected`` and
``provenance.anonymised_columns`` by the engine wiring (P15-C01). This
module never calls the anonymisation pipeline scripts and never mutates
the input frame (Anderson: chain of custody — read-only inspection).

Public API
----------

* :data:`PATTERN` — compiled token regex; single source of truth for the
  detection shape.
* :data:`THRESHOLD` — minimum match ratio to flag a column (``0.8``).
* :class:`DetectionResult` — frozen ``(anonymised_input_detected,
  anonymised_columns, warnings)``.
* :func:`detect(df)` — scan every column and return a
  :class:`DetectionResult`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from _shared.tokens import TOK_PREFIX

# Canonical AN-40 token regex (anonymisation-pipeline ADR-406):
# - ``^…$``        anchored full-cell match
# - ``[a-z0-9_]+`` normalised column slot (digits allowed per M-10)
# - ``\d{3,}``     three-digit minimum producer's zero-padding (M-6)
PATTERN: re.Pattern[str] = re.compile(rf"^{re.escape(TOK_PREFIX)}[a-z0-9_]+_\d{{3,}}$")

THRESHOLD: float = 0.8


@dataclass(frozen=True)
class DetectionResult:
    """Outcome of :func:`detect` for one DataFrame.

    ``anonymised_input_detected`` is ``True`` iff at least one column was
    flagged. ``anonymised_columns`` lists those column names in input
    order. ``warnings`` carries the all-null skip messages (one per
    skipped column, in input order).
    """

    anonymised_input_detected: bool
    # Tuples (not lists) so this dataclass is immutable at construction.
    # The engine boundary in ``analyse._build_provenance`` converts to
    # list when serialising into the findings.json provenance dict —
    # the immutability guarantee holds for the in-memory dataclass, not
    # for the JSON payload (which must be a JSON array regardless).
    anonymised_columns: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def _match_ratio(series: pd.Series) -> float:
    """Return the fraction of non-null values matching :data:`PATTERN`.

    Caller MUST guard against ``n_non_null == 0`` before calling — this
    helper assumes there is at least one non-null cell.
    """
    non_null = series.dropna().astype(str)
    matches = sum(1 for value in non_null if PATTERN.fullmatch(value))
    return matches / len(non_null)


def detect(df: pd.DataFrame) -> DetectionResult:
    """Scan every column of ``df`` for the AN-40 token pattern.

    For each column:

    * If ``n_non_null == 0`` (empty or entirely null), skip with a
      ``provenance.warnings``-style message.
    * Otherwise, flag the column when ``matches / n_non_null >= THRESHOLD``.

    The input frame is not mutated. Columns are processed in their input
    order; ``anonymised_columns`` and ``warnings`` preserve that order.
    """
    anonymised_columns: list[str] = []
    warnings: list[str] = []

    for column in df.columns:
        series = df[column]
        n_non_null = int(series.notna().sum())
        if n_non_null == 0:
            warnings.append(
                f"column '{column}' is entirely null — token-pattern detection skipped"
            )
            continue
        if _match_ratio(series) >= THRESHOLD:
            anonymised_columns.append(str(column))

    return DetectionResult(
        anonymised_input_detected=bool(anonymised_columns),
        anonymised_columns=tuple(anonymised_columns),
        warnings=tuple(warnings),
    )
