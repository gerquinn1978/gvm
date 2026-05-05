"""Tests for `_im_tags.parse_impact_deliverable_tag` (discovery ADR-304)."""

from __future__ import annotations

from pathlib import Path

from _im_tags import parse_impact_deliverable_tag


def test_single_deliverable():
    assert parse_impact_deliverable_tag("[impact-deliverable: D-3]") == ["D-3"]


def test_multiple_comma_separated_with_spaces():
    assert parse_impact_deliverable_tag("[impact-deliverable: D-3, D-7]") == [
        "D-3",
        "D-7",
    ]


def test_multiple_comma_separated_no_spaces():
    assert parse_impact_deliverable_tag("[impact-deliverable: D-3,D-7]") == [
        "D-3",
        "D-7",
    ]


def test_multiple_extra_whitespace():
    assert parse_impact_deliverable_tag("[impact-deliverable:  D-3 ,  D-7  ]") == [
        "D-3",
        "D-7",
    ]


def test_priority_line_context():
    line = "**RE-1 (Must) [impact-deliverable: D-1]:** the system shall foo."
    assert parse_impact_deliverable_tag(line) == ["D-1"]


def test_no_tag_returns_empty():
    assert parse_impact_deliverable_tag("**RE-1 (Must):** plain requirement.") == []


def test_empty_bracket_returns_empty():
    assert parse_impact_deliverable_tag("[impact-deliverable: ]") == []


def test_wrong_prefix_returns_empty():
    assert parse_impact_deliverable_tag("[impact-deliverable: X-3]") == []


def test_lowercase_d_returns_empty():
    assert parse_impact_deliverable_tag("[impact-deliverable: d-3]") == []


def test_three_deliverables():
    assert parse_impact_deliverable_tag("[impact-deliverable: D-1, D-2, D-3]") == [
        "D-1",
        "D-2",
        "D-3",
    ]


def test_first_tag_only_when_multiple_on_one_line():
    line = "[impact-deliverable: D-1] and [impact-deliverable: D-2]"
    assert parse_impact_deliverable_tag(line) == ["D-1"]


def test_two_digit_deliverable_id():
    assert parse_impact_deliverable_tag("[impact-deliverable: D-42]") == ["D-42"]


# --- Shared rule 25 grep test (TC-PP-9-01) ---


SHARED_RULES_PATH = (
    Path(__file__).resolve().parents[1] / "references" / "shared-rules.md"
)


def test_shared_rule_25_literal_present():
    text = SHARED_RULES_PATH.read_text(encoding="utf-8")
    assert "25. **No silent skip, defer, or stub.**" in text


def test_shared_rule_25_three_options_present():
    text = SHARED_RULES_PATH.read_text(encoding="utf-8")
    assert '"Implement now"' in text
    assert '"Defer and record as surfaced requirement"' in text
    assert '"Leave as stub and record in handover / STUBS.md"' in text
