"""Exact-row and fuzzy near-duplicate detection (P3-C04, AN-16).

Two orthogonal kinds of duplicate surface in real-world data:

1. **Exact-row duplicates** — two rows identical on every column. Almost always
   an ingestion or export artefact (double-click export, re-run of a pipeline).
2. **Near duplicates** on a high-cardinality key column — "Acme Corp",
   "ACME Corp.", "Acme Corporation " — spelling / formatting variants of the
   same real-world entity. Requires fuzzy matching; we use rapidfuzz's
   ``WRatio`` scorer (Levenshtein-based, handles case and whitespace well).

Public API:

- ``find_exact(df)`` → list of ``{row_indices, n_duplicates}``
- ``find_near(series, key_column, threshold=0.85)`` → list of
  ``{key_column, cluster, similarity}``
- ``auto_detect_key(df)`` → the highest-cardinality string column with
  unique-ratio ≥ 0.8, or ``None``.

All functions return empty lists / ``None`` for empty input — never raise.
"""

from __future__ import annotations

import pandas as pd
from rapidfuzz import fuzz
from rapidfuzz.process import cdist
from rapidfuzz.utils import default_process

__all__ = ["find_exact", "find_near", "auto_detect_key"]


# ---- Thresholds ------------------------------------------------------------

_DEFAULT_NEAR_THRESHOLD = 0.85
_THRESHOLD_MIN = 0.5
_THRESHOLD_MAX = 1.0
_AUTO_KEY_UNIQUE_RATIO = 0.8


# ---- Public API ------------------------------------------------------------


def find_exact(df: pd.DataFrame) -> list[dict]:
    """Return groups of fully-identical rows.

    Each group: ``{"row_indices": [int, ...], "n_duplicates": int}`` where
    ``n_duplicates`` is the group size (≥ 2).
    """
    if df.empty:
        return []
    # duplicated(keep=False) flags every row that appears more than once.
    dup_mask = df.duplicated(keep=False)
    if not dup_mask.any():
        return []
    dup_rows = df[dup_mask]
    # Group by the full row content — use every column.
    groups = dup_rows.groupby(list(df.columns), dropna=False, sort=False)
    out: list[dict] = []
    for _, idx in groups.groups.items():
        indices = [int(i) for i in idx]
        if len(indices) < 2:
            continue
        out.append({"row_indices": sorted(indices), "n_duplicates": len(indices)})
    # Deterministic order: by first row_index.
    out.sort(key=lambda g: g["row_indices"][0])
    return out


def find_near(
    series: pd.Series,
    key_column: str,
    *,
    threshold: float = _DEFAULT_NEAR_THRESHOLD,
) -> list[dict]:
    """Return clusters of near-duplicate values in ``series``.

    Uses rapidfuzz ``WRatio`` (0-100) normalised to ``0.0..1.0``. Clusters
    are connected components of the similarity graph whose edges satisfy
    ``similarity >= threshold``.
    """
    if not (_THRESHOLD_MIN <= threshold <= _THRESHOLD_MAX):
        raise ValueError(
            f"threshold must be in [{_THRESHOLD_MIN}, {_THRESHOLD_MAX}], got {threshold}"
        )
    if series.empty:
        return []
    # Preserve the original row indices; drop nulls for comparison.
    non_null = series.dropna()
    if len(non_null) < 2:
        return []
    values = [str(v) for v in non_null.tolist()]
    indices = [int(i) for i in non_null.index.tolist()]

    # Pairwise similarity matrix (0-100). O(n^2); adequate up to a few thousand
    # unique strings — upstream sampling kicks in at n >= 10k rows (AN-12).
    # default_process lowercases, strips punctuation, collapses whitespace —
    # essential for catching "ACME Corp" ≡ "Acme Corp." ≡ "acme corp".
    matrix = cdist(values, values, scorer=fuzz.WRatio, processor=default_process)
    threshold_pct = threshold * 100.0

    # Connected components via BFS on the adjacency (similarity >= threshold).
    n = len(values)
    visited = [False] * n
    clusters_by_pos: list[list[int]] = []
    for start in range(n):
        if visited[start]:
            continue
        visited[start] = True
        stack = [start]
        component = [start]
        while stack:
            i = stack.pop()
            for j in range(n):
                if visited[j] or j == i:
                    continue
                if matrix[i, j] >= threshold_pct:
                    visited[j] = True
                    component.append(j)
                    stack.append(j)
        if len(component) >= 2:
            clusters_by_pos.append(component)

    out: list[dict] = []
    for comp in clusters_by_pos:
        # Similarity reported for the cluster = minimum pairwise similarity
        # within it (honest worst-bond rather than average).
        pairwise = [matrix[i, j] for i in comp for j in comp if j > i]
        min_sim = float(min(pairwise)) / 100.0 if pairwise else 1.0
        cluster_members = [
            {"row_index": indices[pos], "value": values[pos]} for pos in comp
        ]
        cluster_members.sort(key=lambda m: m["row_index"])
        out.append(
            {
                "key_column": key_column,
                "cluster": cluster_members,
                "similarity": round(min_sim, 4),
            }
        )
    # Deterministic: order clusters by smallest row_index.
    out.sort(key=lambda c: c["cluster"][0]["row_index"])
    return out


def summarise(df: pd.DataFrame) -> dict:
    """Privacy-safe ADR-201 ``duplicates`` block (P17-C01, NFR-1).

    Returns ``{"exact": [...], "near": [...]}`` carrying aggregates only
    — row indices, group sizes, similarity scores, and the auto-detected
    key column name. **No cell values.** ``find_exact`` is privacy-safe
    by construction (returns row_indices + counts); ``find_near`` is
    not (returns the matched string as ``cluster[].value``), so this
    summariser projects each near cluster down to its non-value fields
    before returning. The two underlying functions stay available for
    in-engine consumers operating inside the same trust boundary; the
    public summariser is the JSON-boundary contract.
    """
    exact = find_exact(df)
    near: list[dict] = []
    key = auto_detect_key(df)
    if key is not None:
        clusters = find_near(df[key], key)
        for c in clusters:
            members = c.get("cluster") or []
            near.append(
                {
                    "key_column": c.get("key_column"),
                    "row_indices": sorted(int(m["row_index"]) for m in members),
                    "n_members": len(members),
                    "similarity": c.get("similarity"),
                }
            )
    return {"exact": exact, "near": near}


def auto_detect_key(df: pd.DataFrame) -> str | None:
    """Pick the highest-cardinality string column, unique-ratio ≥ 0.8.

    Returns the column name, or ``None`` if no column qualifies.
    """
    if df.empty:
        return None
    best_col: str | None = None
    best_cardinality = -1
    for col in df.columns:
        series = df[col]
        if not (
            pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)
        ):
            continue
        non_null = series.dropna()
        if non_null.empty:
            continue
        unique_count = int(non_null.nunique())
        # Denominator is the full column length (including nulls) — a 90%-null
        # column with 10 unique values is not a viable near-duplicate key.
        unique_ratio = unique_count / len(series)
        if unique_ratio < _AUTO_KEY_UNIQUE_RATIO:
            continue
        if unique_count > best_cardinality:
            best_cardinality = unique_count
            best_col = str(col)
    return best_col
