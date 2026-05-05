"""Unit tests for ``_shared/headline.py`` (ADR-211, TC-AN-46)."""

from __future__ import annotations

import pandas as pd
import pytest

from _shared import headline
from _shared.diagnostics import JargonError, PrivacyBoundaryViolation


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _make_findings_12_candidates() -> tuple[pd.DataFrame, dict]:
    """Synthesise a findings dict with 12 candidates across kinds."""
    n = 1000
    df = pd.DataFrame({f"col_{i:03d}": list(range(n)) for i in range(10)})

    findings = {
        "outliers": {
            "agreement_matrix": [
                {
                    "row_index": 100,
                    "column": "col_001",
                    "methods": ["iqr", "mad", "iforest"],
                    "confidence": "high",
                },
                {
                    "row_index": 200,
                    "column": "col_002",
                    "methods": ["iqr", "mad"],
                    "confidence": "review",
                },
                {
                    "row_index": 300,
                    "column": "col_003",
                    "methods": ["iqr", "mad", "iforest"],
                    "confidence": "high",
                },
            ]
        },
        "columns": [
            {
                "name": "col_004",
                "completeness_pct": 70.0,
                "missingness_classification": {
                    "label": "MAR",
                    "confidence": "high",
                },
            },
            {
                "name": "col_005",
                "completeness_pct": 40.0,
                "missingness_classification": {
                    "label": "possibly MNAR",
                    "confidence": "medium",
                },
            },
        ],
        "time_series": {
            "time_column": "col_006",
            "value_column": "col_006",
            "multi_window_outliers": [
                {
                    "row_index": 999,
                    "label": "regime_shift",
                    "windows": ["full", "last_quartile", "recent_n"],
                },
                {
                    "row_index": 500,
                    "label": "regime_shift",
                    "windows": ["full", "last_quartile"],
                },
            ],
        },
        "drivers": {
            "target": "col_000",
            "agreement": [
                {
                    "feature": "col_007",
                    "label": "high-confidence",
                    "in_top_k": [
                        "variance_decomposition",
                        "partial_correlation",
                        "rf_importance",
                    ],
                },
                {
                    "feature": "col_008",
                    "label": "review",
                    "in_top_k": ["variance_decomposition", "partial_correlation"],
                },
                {
                    "feature": "col_009",
                    "label": "high-confidence",
                    "in_top_k": [
                        "variance_decomposition",
                        "partial_correlation",
                        "rf_importance",
                    ],
                },
            ],
        },
        "comparison": {
            "file_vs_file_outliers": [
                {"row_index_actual": 10, "column": "col_001"},
                {"row_index_actual": 20, "column": "col_002"},
                {"row_index_actual": 30, "column": "col_003"},
            ],
        },
    }
    return df, findings


# ---------------------------------------------------------------------------
# TC-AN-46-01 — top-K by impact, deterministic, unique ids
# ---------------------------------------------------------------------------


def test_tc_an_46_01_top_k_by_impact_deterministic():
    df, findings = _make_findings_12_candidates()
    result = headline.select(df, findings, k_default=5, prefs={})
    assert len(result) == 5
    # Descending impact — 2 high-confidence drivers (impact 3.0) lead.
    # Check by asserting the driver entries appear first.
    first_two_kinds = [r["kind"] for r in result[:2]]
    assert first_two_kinds.count("driver") == 2
    # Unique ids
    ids = [r["id"] for r in result]
    assert len(set(ids)) == len(ids)
    # Deterministic
    result2 = headline.select(df, findings, k_default=5, prefs={})
    assert [r["id"] for r in result] == [r["id"] for r in result2]


def test_tc_an_46_01_entries_match_adr_201_schema():
    df, findings = _make_findings_12_candidates()
    result = headline.select(df, findings, k_default=5, prefs={})
    required = {"id", "title", "summary", "kind", "drillthrough_id", "methodology_ref"}
    for r in result:
        assert set(r.keys()) == required
        assert r["methodology_ref"] is None
        assert r["kind"] in {
            "data_quality",
            "distribution",
            "outlier",
            "driver",
            "time_series",
            "comparison",
        }


# ---------------------------------------------------------------------------
# TC-AN-46-02 — K clamp [3, 10]
# ---------------------------------------------------------------------------


def test_tc_an_46_02_lower_clamp_to_three():
    df, findings = _make_findings_12_candidates()
    result = headline.select(df, findings, k_default=5, prefs={"headline_count": 1})
    assert len(result) == 3


def test_tc_an_46_02_upper_clamp_to_ten():
    df, findings = _make_findings_12_candidates()
    result = headline.select(df, findings, k_default=5, prefs={"headline_count": 100})
    # Candidate pool is ~12; K clamps to 10.
    assert len(result) == 10


def test_clamp_k_direct():
    """Direct unit test for the clamp — independent of candidate pool size."""
    assert headline._clamp_k(100) == 10
    assert headline._clamp_k(11) == 10
    assert headline._clamp_k(10) == 10
    assert headline._clamp_k(5) == 5
    assert headline._clamp_k(3) == 3
    assert headline._clamp_k(2) == 3
    assert headline._clamp_k(-5) == 3
    assert headline._clamp_k(None) == 5


def test_k_default_used_when_pref_missing():
    df, findings = _make_findings_12_candidates()
    result = headline.select(df, findings, k_default=5, prefs=None)
    assert len(result) == 5


def test_invalid_headline_count_pref_falls_back_to_default():
    df, findings = _make_findings_12_candidates()
    result = headline.select(df, findings, k_default=5, prefs={"headline_count": "abc"})
    assert len(result) == 5


# ---------------------------------------------------------------------------
# Empty findings
# ---------------------------------------------------------------------------


def test_empty_findings_returns_empty_list():
    df = pd.DataFrame({"a": [1, 2, 3]})
    assert headline.select(df, {}, k_default=5, prefs={}) == []


# ---------------------------------------------------------------------------
# Privacy boundary
# ---------------------------------------------------------------------------


def test_privacy_violation_raises(monkeypatch):
    # A DataFrame with a sensitive categorical value "Alice".
    df = pd.DataFrame({"name": ["Alice", "Bob", "Carol"], "score": [1, 2, 3]})
    findings = {
        "columns": [
            {
                "name": "name",
                "completeness_pct": 80.0,
                "missingness_classification": {
                    "label": "MAR",
                    "confidence": "high",
                },
            }
        ]
    }

    # Intentionally build a headline that mentions "Alice" — this simulates
    # a broken composition. The scan must detect and raise.
    # Replace the candidate extractor so the synthetic title contains the
    # offending value.
    def fake_candidates_missingness(findings_arg):
        return [
            {
                "id": "missingness:name",
                "title": "name: value 'Alice' often missing",  # contains raw value
                "summary": "20% missing",
                "kind": "data_quality",
                "impact": 1.0,
                "lookup_key": "name",
            }
        ]

    monkeypatch.setattr(
        headline, "_candidates_missingness", fake_candidates_missingness
    )
    with pytest.raises(PrivacyBoundaryViolation):
        headline.select(df, findings, k_default=5, prefs={})


# ---------------------------------------------------------------------------
# Jargon scan
# ---------------------------------------------------------------------------


def test_jargon_term_in_title_raises(monkeypatch):
    df = pd.DataFrame({"x": [1, 2, 3]})
    findings = {"drivers": {"target": "y", "agreement": []}}

    def fake_cand(_findings):
        return [
            {
                "id": "driver:x",
                "title": "Shapiro-Wilk rejected normality of x",  # forbidden
                "summary": "p < 0.05",
                "kind": "driver",
                "impact": 2.0,
                "lookup_key": "x",
            }
        ]

    monkeypatch.setattr(headline, "_candidates_drivers", fake_cand)
    with pytest.raises(JargonError):
        headline.select(df, findings, k_default=5, prefs={})


def test_jargon_case_insensitive(monkeypatch):
    df = pd.DataFrame({"x": [1, 2, 3]})
    findings = {"drivers": {"target": "y", "agreement": []}}

    def fake_cand(_findings):
        return [
            {
                "id": "driver:x",
                "title": "ARIMA forecast for x",
                "summary": "trend model",
                "kind": "driver",
                "impact": 2.0,
                "lookup_key": "x",
            }
        ]

    monkeypatch.setattr(headline, "_candidates_drivers", fake_cand)
    with pytest.raises(JargonError):
        headline.select(df, findings, k_default=5, prefs={})


# ---------------------------------------------------------------------------
# Severity ordering
# ---------------------------------------------------------------------------


def test_high_confidence_driver_outranks_review_driver():
    df = pd.DataFrame({f"col_{i:02d}": [1, 2, 3] for i in range(3)})
    findings = {
        "drivers": {
            "target": "col_00",
            "agreement": [
                {
                    "feature": "col_01",
                    "label": "review",
                    "in_top_k": ["variance_decomposition", "partial_correlation"],
                },
                {
                    "feature": "col_02",
                    "label": "high-confidence",
                    "in_top_k": [
                        "variance_decomposition",
                        "partial_correlation",
                        "rf_importance",
                    ],
                },
            ],
        }
    }
    result = headline.select(df, findings, k_default=5, prefs={})
    assert len(result) == 2
    assert result[0]["id"] == "driver:col_02"  # high-confidence first
    assert result[1]["id"] == "driver:col_01"


# ---------------------------------------------------------------------------
# Stable tiebreak
# ---------------------------------------------------------------------------


def test_tiebreak_by_id_alphabetical():
    df = pd.DataFrame({f"col_{i:02d}": [1] * 10 for i in range(5)})
    findings = {
        "drivers": {
            "target": "col_00",
            "agreement": [
                {
                    "feature": "col_04",
                    "label": "high-confidence",
                    "in_top_k": [
                        "variance_decomposition",
                        "partial_correlation",
                        "rf_importance",
                    ],
                },
                {
                    "feature": "col_01",
                    "label": "high-confidence",
                    "in_top_k": [
                        "variance_decomposition",
                        "partial_correlation",
                        "rf_importance",
                    ],
                },
                {
                    "feature": "col_02",
                    "label": "high-confidence",
                    "in_top_k": [
                        "variance_decomposition",
                        "partial_correlation",
                        "rf_importance",
                    ],
                },
            ],
        }
    }
    result = headline.select(df, findings, k_default=5, prefs={})
    # All equal impact → alphabetical by id
    assert [r["id"] for r in result] == [
        "driver:col_01",
        "driver:col_02",
        "driver:col_04",
    ]


# ---------------------------------------------------------------------------
# Drillthrough linkage
# ---------------------------------------------------------------------------


def test_drillthrough_id_populated_when_present():
    df = pd.DataFrame({"col_01": [1, 2, 3]})
    findings = {
        "drivers": {
            "target": "y",
            "agreement": [
                {
                    "feature": "col_01",
                    "label": "high-confidence",
                    "in_top_k": [
                        "variance_decomposition",
                        "partial_correlation",
                        "rf_importance",
                    ],
                }
            ],
        },
        "drillthroughs": [
            {"id": "dt_001", "kind": "driver", "data": {"feature": "col_01"}},
        ],
    }
    result = headline.select(df, findings, k_default=5, prefs={})
    assert result[0]["drillthrough_id"] == "dt_001"


def test_drillthrough_id_data_quality_kind():
    df = pd.DataFrame({"col_01": [1, 2, 3]})
    findings = {
        "columns": [
            {
                "name": "col_01",
                "completeness_pct": 50.0,
                "missingness_classification": {
                    "label": "MAR",
                    "confidence": "high",
                },
            }
        ],
        "drillthroughs": [
            {"id": "dt_col", "kind": "column", "data": {"column_name": "col_01"}},
        ],
    }
    result = headline.select(df, findings, k_default=5, prefs={})
    assert result[0]["kind"] == "data_quality"
    assert result[0]["drillthrough_id"] == "dt_col"


def test_drillthrough_id_time_series_kind_via_outlier_drillthrough():
    df = pd.DataFrame({"col_01": range(100)})
    findings = {
        "time_series": {
            "time_column": "col_01",
            "value_column": "col_01",
            "multi_window_outliers": [
                {
                    "row_index": 99,
                    "label": "regime_shift",
                    "windows": ["full", "last_quartile", "recent_n"],
                }
            ],
        },
        "drillthroughs": [
            {
                "id": "dt_ts",
                "kind": "outlier",
                "data": {"row_index": 99, "column": "col_01"},
            },
        ],
    }
    result = headline.select(df, findings, k_default=5, prefs={})
    assert result[0]["kind"] == "time_series"
    assert result[0]["drillthrough_id"] == "dt_ts"


def test_drillthrough_id_null_when_absent():
    df = pd.DataFrame({"col_01": [1, 2, 3]})
    findings = {
        "drivers": {
            "target": "y",
            "agreement": [
                {
                    "feature": "col_01",
                    "label": "high-confidence",
                    "in_top_k": [
                        "variance_decomposition",
                        "partial_correlation",
                        "rf_importance",
                    ],
                }
            ],
        },
    }
    result = headline.select(df, findings, k_default=5, prefs={})
    assert result[0]["drillthrough_id"] is None


# ---------------------------------------------------------------------------
# Recency bonus
# ---------------------------------------------------------------------------


def test_recency_bonus_lifts_recent_regime_shift_above_non_recent():
    n = 100
    df = pd.DataFrame({"col_01": range(n)})
    findings = {
        "time_series": {
            "time_column": "col_01",
            "value_column": "col_01",
            "multi_window_outliers": [
                {
                    "row_index": 50,
                    "label": "regime_shift",
                    "windows": ["full"],
                },
                {
                    "row_index": 99,
                    "label": "regime_shift",
                    "windows": ["full", "last_quartile", "recent_n"],
                },
            ],
        }
    }
    result = headline.select(df, findings, k_default=5, prefs={})
    # Recent one (row 99) should come first
    assert result[0]["id"] == "regime_shift:col_01:99"


# ---------------------------------------------------------------------------
# Constants pinned
# ---------------------------------------------------------------------------


def test_constants():
    assert headline._K_MIN == 3
    assert headline._K_MAX == 10
    assert headline._K_DEFAULT == 5
    assert headline._RECENCY_BONUS == 0.5


# ---------------------------------------------------------------------------
# Privacy-scan word-boundary hardening (P22-C01 — defect S6.1 fix)
# ---------------------------------------------------------------------------


def test_privacy_scan_short_token_does_not_match_substring_of_word():
    """Defect S6.1 regression: a 1-char categorical value 'a' must not
    trip on the engine's own composed prose like 'high-agreement'.
    Pre-fix, substring containment raised; post-fix, word-boundary
    matching skips this case."""
    headline._privacy_scan(
        "price: high-agreement unusual value at row 35",
        corpus=["a", "b", "c"],
        column_names=["price"],
        cand_id="outlier:price:35",
        field="title",
    )
    # No exception → pass.


def test_privacy_scan_standalone_short_token_still_trips():
    """A 1-char token that appears as a standalone word still trips —
    e.g. 'M' surrounded by punctuation in 'flag: M, F, M, F'. The
    boundary rule preserves the privacy guarantee for genuine leaks."""
    with pytest.raises(headline.PrivacyBoundaryViolation):
        headline._privacy_scan(
            "flag: M, F, M",
            corpus=["m"],
            column_names=["flag"],
            cand_id="x",
            field="title",
        )


def test_privacy_scan_multi_char_value_still_trips_with_punctuation_boundary():
    """Existing behaviour preserved: 'Alice' in 'value 'Alice' often missing'
    still trips. Apostrophes and spaces are non-word characters so the
    boundary lookarounds match."""
    with pytest.raises(headline.PrivacyBoundaryViolation):
        headline._privacy_scan(
            "value 'Alice' often missing",
            corpus=["alice"],
            column_names=["name"],
            cand_id="x",
            field="title",
        )


def test_privacy_scan_token_inside_longer_word_does_not_trip():
    """Token 'ab' must not match 'lab' — 'ab' inside a word has a word
    char before it, failing the negative lookbehind."""
    headline._privacy_scan(
        "lab results stable",
        corpus=["ab"],
        column_names=["x"],
        cand_id="x",
        field="title",
    )


def test_privacy_scan_case_insensitive_preserved():
    """Case-insensitive matching is preserved by the new regex via
    re.IGNORECASE."""
    with pytest.raises(headline.PrivacyBoundaryViolation):
        headline._privacy_scan(
            "Found ALICE in the data",
            corpus=["alice"],
            column_names=["name"],
            cand_id="x",
            field="title",
        )


def test_privacy_scan_regex_metacharacters_in_token_are_escaped():
    """A token containing regex-special characters ('.', '*', '+', etc.)
    must be matched literally, not interpreted as a regex pattern."""
    # Token "a.b" must match literal "a.b", not "axb".
    with pytest.raises(headline.PrivacyBoundaryViolation):
        headline._privacy_scan(
            "found a.b in the row",
            corpus=["a.b"],
            column_names=["x"],
            cand_id="x",
            field="title",
        )
    # Token "a.b" must NOT match "axb" (would happen if '.' were treated as regex).
    headline._privacy_scan(
        "found axb in the row",
        corpus=["a.b"],
        column_names=["x"],
        cand_id="x",
        field="title",
    )


def test_privacy_scan_empty_token_skipped():
    """An empty-string token in the corpus is skipped (prevents the
    pathological case where every text trivially matches)."""
    headline._privacy_scan(
        "any text here",
        corpus=["", "alice"],
        column_names=["x"],
        cand_id="x",
        field="title",
    )
    # No exception (alice not in text).


def test_select_does_not_raise_when_short_categorical_codes_collide_with_prose():
    """End-to-end regression for defect S6.1: a fixture with single-letter
    category column ({'A','B','C'}) and an outlier candidate produces a
    non-empty headlines list. Pre-fix this path raised
    PrivacyBoundaryViolation inside the engine and was silently caught,
    leaving headlines empty."""
    df = pd.DataFrame(
        {
            "price": [1.0, 2.0, 3.0, 100.0, 4.0],
            "category": ["A", "B", "C", "A", "B"],
        }
    )
    findings = {
        "outliers": {
            "agreement_matrix": [
                {
                    "row_index": 3,
                    "column": "price",
                    "methods": ["iqr", "mad", "iforest"],
                    "confidence": "high",
                },
            ]
        },
        "columns": [
            {"name": "price", "completeness_pct": 100.0, "dtype": "float64"},
            {"name": "category", "completeness_pct": 100.0, "dtype": "object"},
        ],
    }
    result = headline.select(df, findings, k_default=5, prefs={})
    assert result, "headline.select silently returned empty on S6.1 fixture"
    assert any(h["kind"] == "outlier" for h in result), result


# ---------------------------------------------------------------------------
# Empty-headlines fallback (P21-C01)
# ---------------------------------------------------------------------------


def _clean_findings(df: pd.DataFrame, completeness: float = 100.0) -> dict:
    """findings shape for a dataset with column metadata but zero
    anomalies — every candidate source returns []. Used to drive the
    fallback path."""
    columns = []
    for name in df.columns:
        columns.append(
            {
                "name": str(name),
                "dtype": str(df[name].dtype),
                "n_total": int(len(df)),
                "n_non_null": int(df[name].notna().sum()),
                "completeness_pct": completeness,
                "missingness_classification": None,
                "stats": None,
            }
        )
    return {
        "columns": columns,
        "outliers": {"agreement_matrix": []},
        "time_series": None,
        "drivers": None,
        "comparison": None,
    }


def test_clean_dataset_produces_dataset_summary_headline():
    """When no anomaly candidates fire, the fallback emits at least a
    `dataset_summary` headline so the report is never empty."""
    df = pd.DataFrame(
        {
            "score": [1, 2, 3, 4, 5] * 20,
            "rating": [3, 4, 5, 4, 3] * 20,
            "category": ["alpha", "bravo", "charlie", "alpha", "bravo"] * 20,
        }
    )
    result = headline.select(df, _clean_findings(df), k_default=5, prefs={})

    assert result, "fallback did not fire — clean data produced empty headlines"
    summary_entries = [e for e in result if e["kind"] == "dataset_summary"]
    assert len(summary_entries) == 1, result
    title = summary_entries[0]["title"]
    assert "100" in title or "rows" in title.lower(), title
    assert "3" in title or "columns" in title.lower(), title


def test_fallback_is_suppressed_when_real_candidates_exist():
    """Real findings outrank the fallback. When even one threshold-firing
    candidate exists, no `dataset_summary` headline appears."""
    df, findings = _make_findings_12_candidates()
    result = headline.select(df, findings, k_default=5, prefs={})

    summary_entries = [e for e in result if e["kind"] == "dataset_summary"]
    assert summary_entries == [], (
        f"fallback fired when real candidates exist: {summary_entries}"
    )


def test_fallback_completeness_summary_when_all_columns_full():
    """When every column is ≥99% complete, the fallback adds a
    completeness-summary headline."""
    df = pd.DataFrame({"a": list(range(50)), "b": list(range(50))})
    result = headline.select(df, _clean_findings(df), k_default=5, prefs={})

    completeness_entries = [e for e in result if e["kind"] == "completeness_summary"]
    assert len(completeness_entries) == 1, result


def test_fallback_completeness_summary_suppressed_when_columns_have_gaps():
    """If any column drops below the 99% threshold, no completeness
    summary — emitting "all columns complete" would be a lie."""
    df = pd.DataFrame({"a": list(range(50)), "b": list(range(50))})
    findings = _clean_findings(df, completeness=80.0)
    result = headline.select(df, findings, k_default=5, prefs={})

    completeness_entries = [e for e in result if e["kind"] == "completeness_summary"]
    assert completeness_entries == [], (
        "fallback claimed full completeness on 80%-complete data"
    )


def test_fallback_schema_summary_when_dtypes_diverse():
    """When ≥2 dtype categories present, schema_summary surfaces."""
    df = pd.DataFrame(
        {
            "n": [1.0, 2.0, 3.0],
            "s": ["alpha", "bravo", "charlie"],
        }
    )
    result = headline.select(df, _clean_findings(df), k_default=5, prefs={})

    schema_entries = [e for e in result if e["kind"] == "schema_summary"]
    assert len(schema_entries) == 1, result


def test_fallback_schema_summary_suppressed_when_single_dtype():
    """Single-dtype dataset → no schema-summary entry; the headline
    would be uninformative."""
    df = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
    result = headline.select(df, _clean_findings(df), k_default=5, prefs={})

    schema_entries = [e for e in result if e["kind"] == "schema_summary"]
    assert schema_entries == []


def test_fallback_jargon_scan_runs_over_summary_content(monkeypatch):
    """Fallback-emitted titles/summaries go through the same jargon
    scanner the rest of the pipeline uses. Adding a forbidden term to
    the scanner's set must surface the violation."""
    df = pd.DataFrame({"a": [1, 2, 3]})
    monkeypatch.setattr(
        headline,
        "JARGON_FORBIDDEN",
        frozenset({"dataset"}),  # Used in fallback titles.
    )
    with pytest.raises(headline.JargonError):
        headline.select(df, _clean_findings(df), k_default=5, prefs={})


def test_fallback_does_not_fire_on_genuinely_empty_findings():
    """`select(df, {}, ...)` with no `columns` key must still return
    [] — the fallback needs column metadata to compute its content,
    and inventing it from `df.columns` alone would bypass the schema
    contract that `findings.columns` establishes."""
    df = pd.DataFrame({"a": [1, 2, 3]})
    result = headline.select(df, {}, k_default=5, prefs={})
    assert result == []


def test_fallback_titles_avoid_interpretative_language():
    """Doumont: factual, not interpretative. The fallback content must
    not contain 'great', 'clean', 'excellent', 'no issues', or similar
    confidence-baiting phrases. We report what is, not how it feels."""
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["alpha", "bravo", "charlie"]})
    result = headline.select(df, _clean_findings(df), k_default=5, prefs={})

    blocklist = {"great", "excellent", "clean", "no issues", "looks good"}
    for entry in result:
        text = (entry["title"] + " " + entry["summary"]).lower()
        for term in blocklist:
            assert term not in text, (
                f"fallback content contains interpretative term {term!r}: {text}"
            )
