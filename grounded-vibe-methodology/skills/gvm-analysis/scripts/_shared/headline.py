"""Headline-finding selection (ADR-211).

``select(df, findings, *, k_default=5, prefs)`` enumerates candidate
findings across six sources (outliers, missingness, time-series regime
shifts, drivers, comparison divergence, and — implicit — column-level
data-quality surfaces), scores each by
``severity × affected_row_fraction × (1 + recency_bonus)``, and returns
the top-K entries matching the ADR-201 ``headline_findings`` schema.

Two defences run on every composed ``title`` / ``summary``:

* **Privacy scan** against the categorical-value corpus — non-null
  ``object|string|category`` column values, case-insensitive
  word-boundary match (P22-C01: replaced substring containment to fix
  defect S6.1 where short categorical codes false-positived on
  engine-composed prose). Any hit raises
  :class:`PrivacyBoundaryViolation`.
* **Jargon scan** against :data:`_shared.methodology.JARGON_FORBIDDEN` —
  any case-insensitive substring hit raises :class:`JargonError`.

ADR-211 post-R5 MED-R6-D-8 describes a column-name component of the
privacy corpus. That component is NOT enforced here: engine-composed
titles legitimately reference column names, and the upstream
anonymisation pipeline tokenises sensitive column names before findings
reach this layer. If the anonymiser fails, the value-token scan below
catches the same leakage via the values that have the sensitive name
embedded. A future hardening pass may reinstate a column-name scan
conditionally on ``provenance.anonymised_input_detected``; the
parameter remains in the scan signature so the enforcement hook is
discoverable.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from _shared.diagnostics import JargonError, PrivacyBoundaryViolation
from _shared.methodology import JARGON_FORBIDDEN

__all__ = ["select"]


# ADR-211 defaults
_K_MIN = 3
_K_MAX = 10
_K_DEFAULT = 5
_RECENCY_BONUS = 0.5

_SEVERITY = {
    "outlier_high": 3.0,
    "outlier_review": 2.0,
    "missingness": 2.5,
    "regime_shift": 2.5,
    "driver_high": 3.0,
    "driver_review": 1.5,
    "comparison": 2.0,
}

# Missingness labels that qualify for headline selection
_MISSINGNESS_ELIGIBLE = {"MAR", "possibly MNAR"}

# Plain-language mapping so composed titles don't contain jargon tokens.
_MISSINGNESS_PLAIN = {
    "MAR": "structured",
    "possibly MNAR": "potentially non-random",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def select(
    df: pd.DataFrame,
    findings: dict,
    *,
    k_default: int = _K_DEFAULT,
    prefs: dict | None = None,
) -> list[dict]:
    """Return up to K headline-finding entries per ADR-211.

    ``findings`` is the partially-populated findings.json dict — it must
    contain at least the candidate sources (``outliers``, ``columns``,
    ``time_series``, ``drivers``, ``comparison``) that this function
    reads. ``drillthroughs`` may or may not be populated; when absent,
    ``drillthrough_id`` defaults to ``None``.
    """
    prefs = prefs or {}
    k = _clamp_k(prefs.get("headline_count", k_default))
    n_rows = max(1, len(df)) if df is not None else 1

    candidates: list[dict] = []
    candidates.extend(_candidates_outliers(findings, n_rows))
    candidates.extend(_candidates_missingness(findings))
    candidates.extend(_candidates_time_series(findings, n_rows))
    candidates.extend(_candidates_drivers(findings))
    candidates.extend(_candidates_comparison(findings, n_rows))

    # P21-C01: empty-headlines fallback. When no candidate source
    # produced a finding (clean data, no missingness, no anomalies),
    # surface 1-3 descriptive observations so the headline section is
    # never empty. Honest reporting per Doumont — describe the dataset's
    # shape, do not interpret its quality. Suppressed when any real
    # candidate exists; the fallback is a floor, not a ceiling.
    if not candidates:
        candidates.extend(_candidates_clean_data_summary(findings, df))

    # Deterministic ranking: by impact desc, id asc as stable tiebreak.
    ranked = sorted(candidates, key=lambda c: (-c["impact"], c["id"]))

    privacy_corpus = _build_privacy_corpus(df)
    column_names = list(df.columns) if df is not None else []

    drillthrough_index = _index_drillthroughs(findings)

    out: list[dict] = []
    for cand in ranked[:k]:
        title = cand["title"]
        summary = cand["summary"]
        _privacy_scan(title, privacy_corpus, column_names, cand["id"], "title")
        _privacy_scan(summary, privacy_corpus, column_names, cand["id"], "summary")
        _jargon_scan(title, cand["id"], "title")
        _jargon_scan(summary, cand["id"], "summary")
        out.append(
            {
                "id": cand["id"],
                "title": title,
                "summary": summary,
                "kind": cand["kind"],
                "drillthrough_id": drillthrough_index.get(
                    (cand["kind"], cand.get("lookup_key"))
                ),
                # Pass-through so P6-C02 can populate via candidate hints.
                "methodology_ref": cand.get("methodology_ref"),
            }
        )
    return out


# ---------------------------------------------------------------------------
# Candidate extraction
# ---------------------------------------------------------------------------


def _candidates_outliers(findings: dict, n_rows: int) -> list[dict]:
    out = []
    outliers = findings.get("outliers") or {}
    matrix = outliers.get("agreement_matrix") or []
    # ADR-211 affected_row_fraction for outliers:
    #   count of agreement_matrix rows for the column / n_rows.
    # Compute per-column counts once so every candidate for that column
    # carries the same fraction.
    per_column_counts: dict[str, int] = {}
    for entry in matrix:
        col = str(entry.get("column", ""))
        per_column_counts[col] = per_column_counts.get(col, 0) + 1

    for entry in matrix:
        label = entry.get("confidence") or entry.get("label")
        if label == "high":
            severity = _SEVERITY["outlier_high"]
            label_text = "high-agreement"
        elif label == "review":
            severity = _SEVERITY["outlier_review"]
            label_text = "review"
        else:
            continue
        row_index = int(entry["row_index"])
        column = str(entry["column"])
        frac = per_column_counts.get(column, 1) / n_rows
        cand_id = f"outlier:{column}:{row_index}"
        n_methods = len(entry.get("methods", []))
        out.append(
            {
                "id": cand_id,
                "title": f"{column}: {label_text} unusual value at row {row_index}",
                "summary": f"flagged by {n_methods} detection methods",
                "kind": "outlier",
                "impact": severity * frac,
                "lookup_key": (row_index, column),
            }
        )
    return out


def _candidates_missingness(findings: dict) -> list[dict]:
    out = []
    for col in findings.get("columns") or []:
        mc = col.get("missingness_classification")
        if not mc or mc.get("label") not in _MISSINGNESS_ELIGIBLE:
            continue
        completeness = float(col.get("completeness_pct") or 100.0)
        frac = max(0.0, min(1.0, 1.0 - completeness / 100.0))
        name = str(col["name"])
        label = mc["label"]
        # Label may be "MAR" / "possibly MNAR" — these are jargon per
        # JARGON_FORBIDDEN. Map to plain-language equivalents for the
        # composed title (mirrors NFR-4 jargon policy).
        label_text = _MISSINGNESS_PLAIN.get(label, "structured")
        out.append(
            {
                "id": f"missingness:{name}",
                "title": f"{name}: values missing in a {label_text} pattern",
                "summary": (
                    f"{100.0 - completeness:.1f}% of values missing; "
                    f"classification confidence {mc.get('confidence', 'medium')}"
                ),
                "kind": "data_quality",
                "impact": _SEVERITY["missingness"] * frac,
                "lookup_key": name,
            }
        )
    return out


def _candidates_time_series(findings: dict, n_rows: int) -> list[dict]:
    out = []
    ts_block = findings.get("time_series")
    if not ts_block:
        return out
    column = str(
        ts_block.get("value_column") or ts_block.get("time_column") or "series"
    )
    shifts = [
        e
        for e in (ts_block.get("multi_window_outliers") or [])
        if e.get("label") == "regime_shift"
    ]
    # ADR-211: affected_row_fraction = shift_count / n_rows for ALL shifts
    # in this column (time_series block is single-column).
    frac = len(shifts) / n_rows if n_rows > 0 else 0.0
    for entry in shifts:
        row_index = int(entry["row_index"])
        windows = entry.get("windows") or []
        recency = _RECENCY_BONUS if "recent_n" in windows else 0.0
        out.append(
            {
                "id": f"regime_shift:{column}:{row_index}",
                "title": f"{column}: regime shift at row {row_index}",
                "summary": f"value flips across windows {', '.join(windows)}",
                "kind": "time_series",
                "impact": _SEVERITY["regime_shift"] * frac * (1 + recency),
                "lookup_key": (row_index, column),
            }
        )
    return out


def _candidates_drivers(findings: dict) -> list[dict]:
    out = []
    drivers_block = findings.get("drivers")
    if not drivers_block:
        return out
    target = str(drivers_block.get("target") or "target")
    for entry in drivers_block.get("agreement") or []:
        label = entry.get("label")
        if label == "high-confidence":
            severity = _SEVERITY["driver_high"]
            label_text = "high-confidence"
        elif label == "review":
            severity = _SEVERITY["driver_review"]
            label_text = "review"
        else:
            continue
        feature = str(entry["feature"])
        n_agree = len(entry.get("in_top_k", []))
        out.append(
            {
                "id": f"driver:{feature}",
                "title": f"{feature} is a {label_text} driver of {target}",
                "summary": f"agreement across {n_agree} of 3 ranking methods",
                "kind": "driver",
                "impact": severity * 1.0,
                "lookup_key": feature,
            }
        )
    return out


def _candidates_clean_data_summary(
    findings: dict, df: pd.DataFrame | None
) -> list[dict]:
    """Fallback candidate source — fires only when every other source
    returned [] (orchestrated by `select`). Emits 1-3 descriptive
    observations about the dataset's shape so the headline section is
    never empty for clean data.

    The content is factual, not interpretative — we say what the data
    is, not how it feels. ``impact: 0.0`` is intentional: any real
    finding from another source outranks the fallback in `select`'s
    rank step.

    Returns ``[]`` when ``findings["columns"]`` is missing or empty —
    we cannot summarise without column metadata, and inventing it from
    ``df.columns`` alone would bypass the schema contract.
    """
    columns = findings.get("columns") or []
    if not columns:
        return []

    n_rows = max(1, len(df)) if df is not None else 1
    n_cols = len(columns)

    out: list[dict] = []

    # Always emit the dataset-shape summary.
    out.append(
        {
            "id": "dataset:summary",
            "kind": "dataset_summary",
            "title": f"Dataset: {n_rows} rows × {n_cols} columns",
            "summary": (
                f"The input has {n_rows} rows across {n_cols} columns. "
                "No threshold-firing anomalies were found in the per-column, "
                "outlier, time-series, drivers, or comparison checks."
            ),
            "impact": 0.0,
            "methodology_ref": None,
            "lookup_key": None,
        }
    )

    # Completeness summary — only when every column is at least 99%
    # complete. Below that threshold, claiming "all columns complete"
    # would misrepresent the data.
    completeness_pcts = [
        c.get("completeness_pct")
        for c in columns
        if isinstance(c.get("completeness_pct"), (int, float))
    ]
    if completeness_pcts and min(completeness_pcts) >= 99.0:
        min_pct = min(completeness_pcts)
        out.append(
            {
                "id": "dataset:completeness",
                "kind": "completeness_summary",
                "title": f"Every column is at least {min_pct:.1f}% non-null",
                "summary": (
                    f"All {n_cols} columns carry at least {min_pct:.1f}% non-null "
                    "values; missingness checks did not surface any pattern."
                ),
                "impact": 0.0,
                "methodology_ref": None,
                "lookup_key": None,
            }
        )

    # Schema summary — only when ≥2 dtype categories present. A
    # single-dtype dataset gets no useful schema headline.
    n_numeric = 0
    n_categorical = 0
    n_time = 0
    for c in columns:
        dtype = str(c.get("dtype", "")).lower()
        if "datetime" in dtype:
            n_time += 1
        elif any(t in dtype for t in ("int", "float", "number")):
            n_numeric += 1
        else:
            n_categorical += 1
    nonzero_categories = sum(1 for n in (n_numeric, n_categorical, n_time) if n > 0)
    if nonzero_categories >= 2:
        parts = []
        if n_numeric:
            parts.append(f"{n_numeric} numeric")
        if n_categorical:
            parts.append(f"{n_categorical} categorical")
        if n_time:
            parts.append(f"{n_time} time")
        out.append(
            {
                "id": "dataset:schema",
                "kind": "schema_summary",
                "title": f"Column mix: {', '.join(parts)}",
                "summary": (
                    f"The {n_cols} columns split as {', '.join(parts)} by dtype."
                ),
                "impact": 0.0,
                "methodology_ref": None,
                "lookup_key": None,
            }
        )

    return out


def _candidates_comparison(findings: dict, n_rows: int) -> list[dict]:
    out = []
    cmp_block = findings.get("comparison")
    if not cmp_block:
        return out
    diverging_entries = cmp_block.get("file_vs_file_outliers") or []
    if not diverging_entries:
        return out
    # P21-C03 review fix: comparison.compute emits one entry per
    # (row, column) divergence, so a single row diverging on K columns
    # contributes K entries. Deduplicate by row_index_actual so the
    # headline's "N rows differ" count matches the title's row-level
    # framing and the impact fraction is row-scaled (not column-scaled).
    unique_rows = {entry.get("row_index_actual") for entry in diverging_entries}
    n_unique = len(unique_rows)
    frac = min(1.0, n_unique / max(1, n_rows))
    row_word = "row" if n_unique == 1 else "rows"
    out.append(
        {
            "id": "comparison:divergence",
            "title": "actual vs baseline: rows diverge",
            "summary": f"{n_unique} {row_word} differ between actual and baseline",
            "kind": "comparison",
            "impact": _SEVERITY["comparison"] * frac,
            "lookup_key": None,
        }
    )
    return out


# ---------------------------------------------------------------------------
# K clamp
# ---------------------------------------------------------------------------


def _clamp_k(requested: int | None) -> int:
    if requested is None:
        return _K_DEFAULT
    try:
        val = int(requested)
    except (TypeError, ValueError):
        return _K_DEFAULT
    return max(_K_MIN, min(_K_MAX, val))


# ---------------------------------------------------------------------------
# Privacy + jargon scans
# ---------------------------------------------------------------------------


def _build_privacy_corpus(df: pd.DataFrame | None) -> list[str]:
    if df is None or len(df) == 0:
        return []
    tokens: set[str] = set()
    for col in df.select_dtypes(include=["object", "string", "category"]).columns:
        for v in df[col].dropna().unique():
            s = str(v).strip().lower()
            if s:
                tokens.add(s)
    return list(tokens)


def _privacy_scan(
    text: str, corpus: list[str], column_names: list[str], cand_id: str, field: str
) -> None:
    """Raise :class:`PrivacyBoundaryViolation` if ``text`` contains a raw
    row-value token as a standalone word.

    The scan is case-insensitive **word-boundary** matching (P22-C01,
    defect S6.1 fix). Each corpus token T must appear in ``text`` such
    that the character immediately before T is non-word (or start of
    string) AND the character immediately after T is non-word (or end
    of string). Implemented as
    ``re.search(r"(?<!\\w)" + re.escape(T) + r"(?!\\w)", text, re.IGNORECASE)``.

    The pre-P22 implementation used substring containment (``token in
    lower``), which silently emptied the headline section on every
    real-world dataset that had short categorical codes (sex M/F,
    yes/no Y/N, blood type A/B/O, agree/disagree A/D). The corpus
    contained lowercase 1-char tokens; the engine's own composed
    candidate titles ("price: high-agreement unusual value at row 35")
    contained those substrings inside English words; the scan raised;
    ``analyse.main`` caught the exception; headlines stayed empty.
    Word-boundary matching preserves the privacy guarantee — multi-
    char values like ``"alice"`` still trip when isolated by punctuation
    or whitespace — without the false-positive class.

    The (?<!\\w) / (?!\\w) lookarounds are uniform across all token
    lengths. They handle tokens whose own boundary chars are non-word
    (e.g. ``"a$b"``, ``"x*y"``) where ``\\b`` would behave inconsistently.

    The ``column_names`` parameter is retained in the signature for
    ADR-211 post-R5 MED-R6-D-8 traceability but unused inside the
    function — engine-composed titles legitimately reference column
    names, and upstream anonymisation tokenises sensitive column names
    before findings reach this layer.
    """
    _ = column_names  # retained in signature for ADR-211 traceability
    for token in corpus:
        if not token:
            continue
        pattern = re.compile(r"(?<!\w)" + re.escape(token) + r"(?!\w)", re.IGNORECASE)
        if pattern.search(text):
            raise PrivacyBoundaryViolation(token, f"headline[{cand_id}].{field}")


def _jargon_scan(text: str, cand_id: str, field: str) -> None:
    lower = text.lower()
    for term in JARGON_FORBIDDEN:
        if term in lower:
            raise JargonError(term, f"headline[{cand_id}].{field}")


# ---------------------------------------------------------------------------
# Drillthrough index
# ---------------------------------------------------------------------------


def _index_drillthroughs(findings: dict) -> dict[tuple, Any]:
    """Map ``(kind, lookup_key) -> drillthrough_id`` for later assignment."""
    index: dict[tuple, Any] = {}
    for dt in findings.get("drillthroughs") or []:
        kind = dt.get("kind")
        data = dt.get("data") or {}
        if kind == "outlier":
            key = (int(data.get("row_index", -1)), str(data.get("column", "")))
            index[("outlier", key)] = dt["id"]
            # ADR-211: a time_series regime-shift headline uses the same
            # (row_index, column) lookup key; an outlier-kind drillthrough
            # is a legitimate target.
            index[("time_series", key)] = dt["id"]
        elif kind == "driver":
            index[("driver", str(data.get("feature", "")))] = dt["id"]
        elif kind == "column":
            col = str(data.get("column_name", ""))
            index[("data_quality", col)] = dt["id"]
            index[("time_series", col)] = dt["id"]
            # ADR-211 comparison: drillthrough is kind=column, keyed by col.
            index[("comparison", col)] = dt["id"]
        elif kind == "comparison":
            index[("comparison", None)] = dt["id"]
    return index
