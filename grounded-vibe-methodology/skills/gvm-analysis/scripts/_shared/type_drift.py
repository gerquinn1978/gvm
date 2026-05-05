"""Type-drift and encoding-artefact detection (P3-C03, AN-17).

Per-column detector that dispatches across four drift kinds and returns a
single ADR-201 ``type_drift`` signal on the first match:

- ``numeric stored as string`` — object/string column that parses >= 95%
  numeric.
- ``possibly Excel serial date stored as int`` — int column whose values
  all fall in 40000..50000 AND whose column name hints at a date.
- ``encoding artefact (mojibake)`` — string column containing UTF-8-as-
  Latin-1 telltale bigrams (``Ã©``, ``Â£`` …).
- ``mixed types`` — object column with >= 2 content classes each >= 5% of
  non-null rows (numeric-string, date-string, free-text).

Detectors never raise: all-null, empty, or exotic input returns ``None``.
"""

from __future__ import annotations

import re

import pandas as pd

__all__ = ["check"]


# ---- Thresholds ------------------------------------------------------------

_NUMERIC_STRING_FRACTION = 0.95
_EXCEL_SERIAL_MIN = 40000
_EXCEL_SERIAL_MAX = 50000
_DATE_NAME_RE = re.compile(
    r"(date|time|created|updated|timestamp|\bdt\b)", re.IGNORECASE
)
_MIXED_TYPE_MIN_FRACTION = 0.05
_EXAMPLES_CAP = 3

# Telltale bigrams from UTF-8 bytes rendered under a Latin-1 decoder. The
# ``Ã`` prefix covers the common 2-byte range (U+0080..U+00FF) and ``Â``
# covers pure Latin-1 supplementary glyphs (£, §, °, …).
_MOJIBAKE_BIGRAMS = (
    "Ã©",
    "Ã¨",
    "Ã¢",
    "Ã¤",
    "Ã«",
    "Ã¯",
    "Ã´",
    "Ã¶",
    "Ã¼",
    "Ã±",
    "Ã§",
    "Ã ",
    "Â£",
    "Â§",
    "Â°",
    "Â©",
    "Â®",
    "Â¥",
)

# Date-string classifier pattern — deliberately narrow so we only claim
# "date-like" on obvious ISO and slashed forms.
_DATE_STRING_RE = re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}(\s|T|$)")


# ---- Public entry ----------------------------------------------------------


def check(series: pd.Series, column_name: str) -> dict | None:
    """Return the first matching type-drift signal for ``series``, or None.

    Dispatch order (first match wins):

    1. numbers-as-strings (object/string dtype)
    2. Excel serial dates (integer dtype + date-hinting column name)
    3. mojibake (object/string dtype)
    4. mixed types (object/string dtype)
    """
    non_null = series.dropna()
    if non_null.empty:
        return None

    # 1. Numbers-as-strings — only on object/string columns.
    if _is_stringy(series):
        result = _numbers_as_strings(non_null)
        if result is not None:
            return result

    # 2. Excel serial dates — integer dtype only.
    if pd.api.types.is_integer_dtype(series):
        result = _excel_serial_dates(non_null, column_name)
        if result is not None:
            return result

    # 3. Mojibake — before mixed-types so a mojibake-contaminated free-text
    #    column surfaces the encoding story, not a generic "mixed" label.
    if _is_stringy(series):
        result = _mojibake(non_null)
        if result is not None:
            return result

    # 4. Mixed types.
    if _is_stringy(series):
        result = _mixed_types(non_null)
        if result is not None:
            return result

    return None


# ---- Private helpers -------------------------------------------------------


def _is_stringy(series: pd.Series) -> bool:
    """Object or pandas StringDtype — both plausible string containers."""
    return pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)


def _numbers_as_strings(non_null: pd.Series) -> dict | None:
    """Fire if >= 95% of non-null entries parse as finite numbers."""
    as_str = non_null.astype(str)
    parsed = pd.to_numeric(as_str, errors="coerce")
    numeric_fraction = float(parsed.notna().sum()) / len(non_null)
    if numeric_fraction < _NUMERIC_STRING_FRACTION:
        return None
    examples = _sample_strings(as_str[parsed.notna()])
    return {
        "kind": "numeric stored as string",
        "examples": examples,
        "recommendation": (
            "Parse the column as numeric (e.g. ``pd.to_numeric``) before "
            "running statistics."
        ),
    }


def _excel_serial_dates(non_null: pd.Series, column_name: str) -> dict | None:
    """Fire if all ints in [40000, 50000] AND column name hints at a date."""
    if not _DATE_NAME_RE.search(column_name):
        return None
    if not ((non_null >= _EXCEL_SERIAL_MIN) & (non_null <= _EXCEL_SERIAL_MAX)).all():
        return None
    # Convert a sample to Excel epoch (1899-12-30) to show what the values
    # would represent — Doumont: the "what to try" step is clearer when the
    # reader sees the implied dates.
    epoch = pd.Timestamp("1899-12-30")
    examples = [
        f"{int(v)} → {(epoch + pd.Timedelta(days=int(v))).date().isoformat()}"
        for v in non_null.head(_EXAMPLES_CAP)
    ]
    return {
        "kind": "possibly Excel serial date stored as int",
        "examples": examples,
        "recommendation": (
            "If these are dates, reload with ``pd.to_datetime(col, origin="
            "'1899-12-30', unit='D')`` or re-export the source sheet with "
            "cells formatted as dates."
        ),
    }


def _mojibake(non_null: pd.Series) -> dict | None:
    """Fire on any non-null entry containing a telltale bigram."""
    as_str = non_null.astype(str)
    mask = as_str.apply(lambda v: any(b in v for b in _MOJIBAKE_BIGRAMS))
    if not mask.any():
        return None
    examples = _sample_strings(as_str[mask])
    return {
        "kind": "encoding artefact (mojibake)",
        "examples": examples,
        "recommendation": (
            "Reload the file with the correct encoding (typically UTF-8 or "
            "CP-1252) — the current values suggest UTF-8 bytes were decoded "
            "as Latin-1."
        ),
    }


def _mixed_types(non_null: pd.Series) -> dict | None:
    """Fire if >= 2 content classes each cover >= 5% of non-null rows.

    Classes: numeric-string, date-string, free-text.
    """
    as_str = non_null.astype(str)
    total = len(as_str)
    numeric_mask = pd.to_numeric(as_str, errors="coerce").notna()
    date_mask = as_str.apply(lambda v: bool(_DATE_STRING_RE.match(v))) & ~numeric_mask
    free_mask = ~(numeric_mask | date_mask)

    classes = {
        "numeric-string": float(numeric_mask.sum()) / total,
        "date-string": float(date_mask.sum()) / total,
        "free-text": float(free_mask.sum()) / total,
    }
    significant = {k: v for k, v in classes.items() if v >= _MIXED_TYPE_MIN_FRACTION}
    if len(significant) < 2:
        return None
    pct_parts = [f"{k}: {v:.0%}" for k, v in significant.items()]
    examples = _sample_strings(as_str, cap=_EXAMPLES_CAP)
    return {
        "kind": "mixed types",
        "examples": examples,
        "recommendation": (
            "Split or normalise the column — rows contain "
            + ", ".join(pct_parts)
            + ". Decide the intended type and coerce with ``pd.to_numeric`` "
            "or ``pd.to_datetime`` after filtering the non-matching rows."
        ),
    }


def _sample_strings(values: pd.Series, cap: int = _EXAMPLES_CAP) -> list[str]:
    """Stable, bounded string sample for the ``examples`` list."""
    unique = values.drop_duplicates().head(cap)
    return [str(v) for v in unique]
