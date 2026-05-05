"""Tests for _property_detection.py — TC-EBT-7 emission heuristic.

11-case test plan per spec ADR-507 / P12-C04 test plan.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from _property_detection import (
    PropertyDetectionParseError,
    PropertyHeuristic,
    load_property_detection,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCRIPTS_DIR = Path(__file__).resolve().parent
REFERENCES_DIR = SCRIPTS_DIR.parent / "references"
HEURISTIC_FILE = REFERENCES_DIR / "property-detection.md"


# ---------------------------------------------------------------------------
# TC-1  Load the actual file → 5 categories, specific keywords present
# ---------------------------------------------------------------------------

def test_load_actual_file_five_categories():
    h = load_property_detection(HEURISTIC_FILE)
    assert len(h.categories) == 5, f"expected 5 categories, got {len(h.categories)}"
    for name in ("idempotence", "round_trip", "ordering", "algebraic", "constraint_preservation"):
        assert name in h.categories, f"category '{name}' missing"


def test_load_actual_file_specific_keywords():
    h = load_property_detection(HEURISTIC_FILE)
    assert "normalise" in h.categories["idempotence"]
    assert "encode" in h.categories["round_trip"]
    assert "sort" in h.categories["ordering"]
    assert "commutative" in h.categories["algebraic"]
    assert "filter" in h.categories["constraint_preservation"]


def test_load_actual_file_min_three_keywords_per_category():
    h = load_property_detection(HEURISTIC_FILE)
    for name, kws in h.categories.items():
        assert len(kws) >= 3, f"category '{name}' has fewer than 3 keywords: {kws}"


# ---------------------------------------------------------------------------
# TC-2  Single idempotence match
# ---------------------------------------------------------------------------

def test_matches_idempotence_only():
    h = load_property_detection(HEURISTIC_FILE)
    result = h.matches("the system shall normalise input strings")
    assert result == ("idempotence",)


# ---------------------------------------------------------------------------
# TC-3  Single round_trip match
# ---------------------------------------------------------------------------

def test_matches_round_trip_only():
    h = load_property_detection(HEURISTIC_FILE)
    result = h.matches("encode and decode JSON")
    assert result == ("round_trip",)


# ---------------------------------------------------------------------------
# TC-4  Single ordering match (keyword 'sort' present)
# ---------------------------------------------------------------------------

def test_matches_ordering_with_sort():
    h = load_property_detection(HEURISTIC_FILE)
    result = h.matches("sort the results in ascending order")
    assert "ordering" in result
    # Category appears once, not per-keyword
    assert result.count("ordering") == 1


# ---------------------------------------------------------------------------
# TC-5  No match → empty tuple
# ---------------------------------------------------------------------------

def test_matches_no_relevant_text():
    h = load_property_detection(HEURISTIC_FILE)
    result = h.matches("nothing relevant")
    assert result == ()


# ---------------------------------------------------------------------------
# TC-6  Case-insensitive: FORMAT triggers idempotence
# ---------------------------------------------------------------------------

def test_matches_case_insensitive():
    h = load_property_detection(HEURISTIC_FILE)
    result = h.matches("FORMAT THIS STRING")
    assert result == ("idempotence",)


# ---------------------------------------------------------------------------
# TC-7  Multi-category: encode → round_trip; sort → ordering; file order
# ---------------------------------------------------------------------------

def test_matches_multi_category_file_order():
    h = load_property_detection(HEURISTIC_FILE)
    result = h.matches("encode then sort")
    assert "round_trip" in result
    assert "ordering" in result
    # File order: round_trip (## 2) comes before ordering (## 3)
    assert result.index("round_trip") < result.index("ordering")


# ---------------------------------------------------------------------------
# TC-8  Malformed: keyword line before any ## heading
# ---------------------------------------------------------------------------

def test_parse_error_keyword_before_heading(tmp_path: Path):
    bad_file = tmp_path / "bad.md"
    bad_file.write_text("# Title\norphan keyword\n## idempotence\nnormalise\n")
    with pytest.raises(PropertyDetectionParseError, match="keyword line before"):
        load_property_detection(bad_file)


# ---------------------------------------------------------------------------
# TC-9  Malformed: duplicate category name
# ---------------------------------------------------------------------------

def test_parse_error_duplicate_category(tmp_path: Path):
    bad_file = tmp_path / "dup.md"
    bad_file.write_text(
        "## idempotence\nnormalise\n## idempotence\nformat\n"
    )
    with pytest.raises(PropertyDetectionParseError, match="duplicate"):
        load_property_detection(bad_file)


# ---------------------------------------------------------------------------
# TC-10  Path | str | None accepted
# ---------------------------------------------------------------------------

def test_accepts_path_object():
    h = load_property_detection(HEURISTIC_FILE)
    assert isinstance(h, PropertyHeuristic)


def test_accepts_str_path():
    h = load_property_detection(str(HEURISTIC_FILE))
    assert isinstance(h, PropertyHeuristic)


def test_accepts_none_uses_default():
    # None should resolve without error (may raise FileNotFoundError only if
    # neither default location exists; in the test environment at least the
    # repo path resolves via walk-up from _property_detection.py)
    h = load_property_detection(None)
    assert isinstance(h, PropertyHeuristic)


# ---------------------------------------------------------------------------
# TC-11  PropertyHeuristic is frozen (dataclass frozen=True)
# ---------------------------------------------------------------------------

def test_property_heuristic_is_frozen():
    h = load_property_detection(HEURISTIC_FILE)
    with pytest.raises((dataclasses.FrozenInstanceError, TypeError, AttributeError)):
        h.categories = {}  # type: ignore[misc]


def test_categories_value_is_immutable():
    """categories values must be immutable (MappingProxyType or equivalent)."""
    h = load_property_detection(HEURISTIC_FILE)
    # MappingProxyType doesn't support item assignment
    with pytest.raises((TypeError, AttributeError)):
        h.categories["new_cat"] = ("kw",)  # type: ignore[index]
