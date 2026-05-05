"""Suspicious-rounding detection (P3-C03, AN-18).

Flags numeric columns whose integer part ends in ``00`` for an unusually
high fraction of rows — a signal of human data entry or post-hoc rounding,
not an error. The output populates ADR-201's ``columns[*].rounding_signal``
field.

A uniform last-digit distribution produces ~1% of values ending in ``00``.
A threshold of 50% gives generous headroom above that baseline while still
catching obvious rounding patterns (TC-AN-18-01 uses 80%).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = ["suspicious_rounding"]


_ROUND_FRACTION_THRESHOLD = 0.5


def suspicious_rounding(series: pd.Series) -> dict | None:
    """Return ``{"fraction_round", "note"}`` if >= 50% of integer parts end in ``00``.

    ``None`` for empty / all-null / non-numeric series — the caller treats
    ``None`` as "no signal", matching the ADR-201 ``rounding_signal: null``
    shape.
    """
    if not pd.api.types.is_numeric_dtype(series):
        return None
    non_null = series.dropna()
    if non_null.empty:
        return None
    # Round toward zero to an int, then check the last two digits.
    integer_part = non_null.to_numpy(dtype=float).astype(np.int64)
    ends_in_00 = (integer_part % 100) == 0
    fraction = float(ends_in_00.sum()) / len(integer_part)
    if fraction < _ROUND_FRACTION_THRESHOLD:
        return None
    return {
        "fraction_round": fraction,
        "note": f"suspicious rounding — {fraction * 100:.0f}% values end in 00",
    }
