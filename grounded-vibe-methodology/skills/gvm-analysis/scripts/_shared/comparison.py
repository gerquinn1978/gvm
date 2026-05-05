"""File-vs-file comparison for validate mode (P21-C03, ADR-201).

Closes defect 3b from the post-v2.0.0 gates-skipped diagnosis: validate
mode runs to exit 0 with ``--baseline-file`` but ``findings.comparison``
was never populated, so ``_candidates_comparison`` in ``headline.select``
always returned ``[]`` and the user saw no baseline-divergence headline.

Public surface:

* :func:`compute` — produce the ``findings.comparison`` block matching the
  spec shape declared in ``analysis-engine.md`` lines 119–125.

Returns ``None`` when no shared columns exist between the two frames
(degenerate case — there is nothing to compare). Otherwise returns a
dict with ``shared_columns`` populated, per-numeric-column distribution
deltas in ``per_file_differences``, and (when row counts match)
row-level divergences in ``file_vs_file_outliers``.

Row-pairing strategy: when ``len(actual_df) == len(baseline_df)`` we
pair rows by index and flag rows where any shared numeric column differs
from baseline by more than ``_OUTLIER_SIGMA_THRESHOLD`` × the column's
actual-frame std deviation. When sizes differ, ``file_vs_file_outliers``
is empty (no key column in the schema; row pairing is undefined).
``per_file_differences`` populates regardless of row-count match.

Out of scope (per P21-C03): row-key-based pairing. The schema's
``row_index_baseline: int|null`` allows a future enhancement that pairs
by user-supplied key column and leaves the index null when no key match.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

__all__ = ["compute"]

# Outlier threshold for row-vs-row divergence: rows whose value differs
# from the paired baseline row by more than this many actual-frame std
# deviations are flagged as divergent. Magic-number caveat documented in
# the build prompt; 2.0 is a defensible "materially different" threshold
# matching the engine's IQR/MAD outlier convention scale.
_OUTLIER_SIGMA_THRESHOLD: float = 2.0


def compute(
    actual_df: pd.DataFrame,
    baseline_df: pd.DataFrame,
    *,
    actual_file: str = "",
    baseline_file: str = "",
) -> dict[str, Any] | None:
    """Return the ADR-201 ``findings.comparison`` block, or ``None`` when
    the two frames share no columns or either is empty.

    Parameters
    ----------
    actual_df, baseline_df
        The two frames to compare. Column intersection drives
        ``shared_columns``; numeric subset drives ``per_file_differences``;
        index pairing (when row counts match) drives
        ``file_vs_file_outliers``.
    actual_file, baseline_file
        Optional path strings recorded in the output dict for downstream
        display. Pass the source paths from ``analyse.main``.
    """
    if actual_df is None or baseline_df is None:
        return None
    if len(actual_df.columns) == 0 or len(baseline_df.columns) == 0:
        return None
    if len(actual_df) == 0 or len(baseline_df) == 0:
        return None

    # Shared columns in actual-frame order (deterministic).
    shared_set = set(baseline_df.columns)
    shared_columns: list[str] = [str(c) for c in actual_df.columns if c in shared_set]
    if not shared_columns:
        return None

    per_file_differences: list[dict[str, Any]] = []
    for col in shared_columns:
        a_series = actual_df[col]
        b_series = baseline_df[col]
        if not (
            pd.api.types.is_numeric_dtype(a_series)
            and pd.api.types.is_numeric_dtype(b_series)
        ):
            # Non-numeric or dtype mismatch — skip from per-column diffs.
            # Still listed in shared_columns so the user knows the column
            # exists in both files.
            continue

        a_summary = _summarise(a_series)
        b_summary = _summarise(b_series)
        if a_summary is None or b_summary is None:
            continue

        per_file_differences.append(
            {
                "column": col,
                "actual_summary": a_summary,
                "baseline_summary": b_summary,
                "delta": {
                    "mean_change": a_summary["mean"] - b_summary["mean"],
                    "std_change": a_summary["std"] - b_summary["std"],
                    "range_shift": (a_summary["max"] - a_summary["min"])
                    - (b_summary["max"] - b_summary["min"]),
                },
            }
        )

    # Row-level outliers: only when row counts match.
    file_vs_file_outliers: list[dict[str, Any]] = []
    if len(actual_df) == len(baseline_df):
        file_vs_file_outliers = _row_divergences(actual_df, baseline_df, shared_columns)

    return {
        "actual_file": actual_file,
        "baseline_file": baseline_file,
        "shared_columns": shared_columns,
        "per_file_differences": per_file_differences,
        "file_vs_file_outliers": file_vs_file_outliers,
    }


def _summarise(series: pd.Series) -> dict[str, Any] | None:
    """Return a 6-key summary dict for a numeric series, or None if the
    series has no non-null numeric values to summarise."""
    non_null = series.dropna()
    if len(non_null) == 0:
        return None
    return {
        "n": int(len(non_null)),
        "mean": float(non_null.mean()),
        "median": float(non_null.median()),
        "std": float(non_null.std()) if len(non_null) > 1 else 0.0,
        "min": float(non_null.min()),
        "max": float(non_null.max()),
    }


def _row_divergences(
    actual_df: pd.DataFrame,
    baseline_df: pd.DataFrame,
    shared_columns: list[str],
) -> list[dict[str, Any]]:
    """Pair rows by index and flag rows where any shared numeric column
    differs from baseline by more than `_OUTLIER_SIGMA_THRESHOLD` ×
    the column's actual-frame std. Returns one entry per (row, column)
    divergence so a single row with multiple divergent columns produces
    multiple entries.

    Caller must verify ``len(actual_df) == len(baseline_df)`` before
    invoking. Rows are paired by positional index (0, 1, 2, ...), not
    by DataFrame index labels, to avoid surprises when callers reset
    or shift indices.
    """
    out: list[dict[str, Any]] = []
    actual_reset = actual_df.reset_index(drop=True)
    baseline_reset = baseline_df.reset_index(drop=True)

    for col in shared_columns:
        a_series = actual_reset[col]
        b_series = baseline_reset[col]
        if not (
            pd.api.types.is_numeric_dtype(a_series)
            and pd.api.types.is_numeric_dtype(b_series)
        ):
            continue
        a_std = float(a_series.dropna().std()) if a_series.dropna().size > 1 else 0.0
        if a_std == 0.0:
            # No variation in actual — any row-level divergence is
            # categorically different but not statistically scaled.
            # Skip — the per_file_differences delta surface still
            # records the change.
            continue

        threshold = _OUTLIER_SIGMA_THRESHOLD * a_std
        for i in range(len(a_series)):
            a_val = a_series.iloc[i]
            b_val = b_series.iloc[i]
            if pd.isna(a_val) or pd.isna(b_val):
                continue
            if abs(float(a_val) - float(b_val)) > threshold:
                out.append(
                    {
                        "row_index_actual": int(i),
                        "row_index_baseline": int(i),
                        "column": col,
                        "actual_value": float(a_val),
                        "baseline_value": float(b_val),
                    }
                )
    return out
