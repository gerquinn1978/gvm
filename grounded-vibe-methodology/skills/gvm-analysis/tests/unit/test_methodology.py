"""Tests for methodology registry (P6-C02 — TC-AN-13-02, TC-AN-13-03).

TDD: these tests were written BEFORE the implementation was added to
_shared/methodology.py.  Every assertion below should initially fail with
ImportError or AttributeError, then turn green once methodology.py is
extended.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Registry key list (must match the 16 keys specified in P6-C02)
# ---------------------------------------------------------------------------
REQUIRED_KEYS = [
    "spearman",
    "pearson",
    "bootstrap_ci",
    "ci_suppressed_small_n",
    "iqr_outlier",
    "mad_outlier",
    "iforest_outlier",
    "lof_outlier",
    "stl_seasonality",
    "mann_kendall_trend",
    "shap_drivers",
    "variance_decomposition",
    "partial_correlation",
    "linear_forecast",
    "arima_forecast",
    "exp_smoothing_forecast",
]

REQUIRED_FIELDS = {
    "key",
    "display_name",
    "parameters",
    "expert_citation",
    "appendix_text",
}

# ---------------------------------------------------------------------------
# Minimal prefs dict sufficient for parameter rendering tests
# ---------------------------------------------------------------------------
BASE_PREFS = {
    "bootstrap_n_iter": 1000,
    "bootstrap_confidence": 0.95,
    "outlier_iqr_k": 1.5,
    "outlier_mad_threshold": 3.5,
    "trend_alpha": 0.05,
    "seasonal_strength_threshold": 0.6,
    "driver_k_floor": 5,
    "driver_k_fraction": 0.10,
}


# ---------------------------------------------------------------------------
# 1. Regression: JARGON_FORBIDDEN still importable (P4-C06 deliverable)
# ---------------------------------------------------------------------------
def test_jargon_forbidden_still_importable():
    from _shared.methodology import JARGON_FORBIDDEN

    assert isinstance(JARGON_FORBIDDEN, frozenset)
    assert "bootstrap" in JARGON_FORBIDDEN


# ---------------------------------------------------------------------------
# 2. UnknownMethodError is importable
# ---------------------------------------------------------------------------
def test_unknown_method_error_importable():
    from _shared.methodology import UnknownMethodError

    assert issubclass(UnknownMethodError, Exception)


# ---------------------------------------------------------------------------
# 3. METHODOLOGY_REGISTRY is importable and is a dict
# ---------------------------------------------------------------------------
def test_methodology_registry_is_dict():
    from _shared.methodology import METHODOLOGY_REGISTRY

    assert isinstance(METHODOLOGY_REGISTRY, dict)


# ---------------------------------------------------------------------------
# 4. TC-AN-13-02 — every required key is present in METHODOLOGY_REGISTRY
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("key", REQUIRED_KEYS)
def test_required_key_present(key):
    from _shared.methodology import METHODOLOGY_REGISTRY

    assert key in METHODOLOGY_REGISTRY, f"Missing registry key: {key!r}"


# ---------------------------------------------------------------------------
# 5. Every entry has all 5 required fields
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("key", REQUIRED_KEYS)
def test_entry_has_all_fields(key):
    from _shared.methodology import METHODOLOGY_REGISTRY

    entry = METHODOLOGY_REGISTRY[key]
    missing = REQUIRED_FIELDS - set(entry.keys())
    assert not missing, f"Entry {key!r} missing fields: {missing}"


# ---------------------------------------------------------------------------
# 6. Every entry's 'key' field matches the registry key
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("key", REQUIRED_KEYS)
def test_entry_key_field_matches_registry_key(key):
    from _shared.methodology import METHODOLOGY_REGISTRY

    assert METHODOLOGY_REGISTRY[key]["key"] == key


# ---------------------------------------------------------------------------
# 7. build_registry(prefs) returns dict with all required keys
# ---------------------------------------------------------------------------
def test_build_registry_returns_dict_with_all_keys():
    from _shared.methodology import build_registry

    reg = build_registry(BASE_PREFS)
    for key in REQUIRED_KEYS:
        assert key in reg, f"build_registry missing key: {key!r}"


# ---------------------------------------------------------------------------
# 8. TC-AN-13-03 — dynamic parameter rendering: bootstrap_ci changes
#    when prefs["bootstrap_n_iter"] changes
# ---------------------------------------------------------------------------
def test_build_registry_dynamic_bootstrap_ci():
    from _shared.methodology import build_registry

    prefs_500 = {**BASE_PREFS, "bootstrap_n_iter": 500}
    prefs_2000 = {**BASE_PREFS, "bootstrap_n_iter": 2000}

    reg_500 = build_registry(prefs_500)
    reg_2000 = build_registry(prefs_2000)

    params_500 = reg_500["bootstrap_ci"]["parameters"]
    params_2000 = reg_2000["bootstrap_ci"]["parameters"]

    assert "500" in params_500, f"Expected '500' in parameters: {params_500!r}"
    assert "2000" in params_2000, f"Expected '2000' in parameters: {params_2000!r}"
    assert params_500 != params_2000


# ---------------------------------------------------------------------------
# 9. lookup() — happy path returns entry dict
# ---------------------------------------------------------------------------
def test_lookup_returns_entry():
    from _shared.methodology import lookup

    entry = lookup("spearman", BASE_PREFS)
    assert isinstance(entry, dict)
    assert entry["key"] == "spearman"


# ---------------------------------------------------------------------------
# 10. lookup() — unknown key raises UnknownMethodError (loud failure)
# ---------------------------------------------------------------------------
def test_lookup_unknown_key_raises():
    from _shared.methodology import UnknownMethodError, lookup

    with pytest.raises(UnknownMethodError):
        lookup("unknown_method_xyz", BASE_PREFS)


# ---------------------------------------------------------------------------
# 11. aggregate_appendix() — deduplication
# ---------------------------------------------------------------------------
def test_aggregate_appendix_deduplicates():
    from _shared.methodology import aggregate_appendix

    result = aggregate_appendix(
        ["spearman", "spearman", "mann_kendall_trend"], BASE_PREFS
    )
    keys = [e["key"] for e in result]
    assert len(keys) == 2
    assert len(set(keys)) == 2  # no duplicates


# ---------------------------------------------------------------------------
# 12. aggregate_appendix() — sorted alphabetically by display_name
# ---------------------------------------------------------------------------
def test_aggregate_appendix_sorted_by_display_name():
    from _shared.methodology import aggregate_appendix

    result = aggregate_appendix(
        ["mann_kendall_trend", "spearman", "pearson"], BASE_PREFS
    )
    display_names = [e["display_name"] for e in result]
    assert display_names == sorted(display_names), f"Not sorted: {display_names}"


# ---------------------------------------------------------------------------
# 13. aggregate_appendix() — returns list[dict]
# ---------------------------------------------------------------------------
def test_aggregate_appendix_returns_list_of_dicts():
    from _shared.methodology import aggregate_appendix

    result = aggregate_appendix(["spearman"], BASE_PREFS)
    assert isinstance(result, list)
    assert all(isinstance(e, dict) for e in result)


# ---------------------------------------------------------------------------
# 14. ADR-306b — ci_suppressed_small_n has exact expert citation
# ---------------------------------------------------------------------------
def test_ci_suppressed_small_n_expert_citation():
    from _shared.methodology import METHODOLOGY_REGISTRY

    entry = METHODOLOGY_REGISTRY["ci_suppressed_small_n"]
    # ADR-306b verbatim citation
    assert "Harrell" in entry["expert_citation"]
    assert "bootstrap" in entry["expert_citation"].lower()


# ---------------------------------------------------------------------------
# 15. ADR-306b — ci_suppressed_small_n appendix_text references n < 30 and AN-12
# ---------------------------------------------------------------------------
def test_ci_suppressed_small_n_appendix_text():
    from _shared.methodology import METHODOLOGY_REGISTRY

    entry = METHODOLOGY_REGISTRY["ci_suppressed_small_n"]
    text = entry["appendix_text"]
    assert "30" in text, "appendix_text must reference n < 30"
    assert "AN-12" in text, "appendix_text must reference AN-12"


# ---------------------------------------------------------------------------
# 16. No entry has a blank/None field
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("key", REQUIRED_KEYS)
def test_no_blank_fields(key):
    from _shared.methodology import METHODOLOGY_REGISTRY

    entry = METHODOLOGY_REGISTRY[key]
    for field in REQUIRED_FIELDS:
        value = entry.get(field, "")
        assert value, f"Entry {key!r} has blank/None {field!r}"


# ---------------------------------------------------------------------------
# 17. build_registry returns dict[str, dict] (no non-dict values)
# ---------------------------------------------------------------------------
def test_build_registry_values_are_dicts():
    from _shared.methodology import build_registry

    reg = build_registry(BASE_PREFS)
    for k, v in reg.items():
        assert isinstance(v, dict), f"build_registry[{k!r}] is not a dict"


# ---------------------------------------------------------------------------
# 18. aggregate_appendix with empty input returns empty list
# ---------------------------------------------------------------------------
def test_aggregate_appendix_empty():
    from _shared.methodology import aggregate_appendix

    result = aggregate_appendix([], BASE_PREFS)
    assert result == []


# ---------------------------------------------------------------------------
# 19. aggregate_appendix raises UnknownMethodError for unknown key
#     (defensive programming — no silent fallback to KeyError)
# ---------------------------------------------------------------------------
def test_aggregate_appendix_raises_for_unknown_key():
    from _shared.methodology import UnknownMethodError, aggregate_appendix

    with pytest.raises(UnknownMethodError):
        aggregate_appendix(["spearman", "totally_unknown_method"], BASE_PREFS)
