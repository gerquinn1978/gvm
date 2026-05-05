"""Tests for HS-4 marker validator (honesty-triad ADR-103).

Covers TC-HS-4-01 (HTML data-stub-active), TC-HS-4-02 (JSON top-level
_stub_active), TC-HS-4-03 (CLI stderr diagnostic). Each format is checked
in both directions: marker required when stub_active=True, marker forbidden
when stub_active=False.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _hs4_validator import HS4MarkerError, assert_marker_consistent  # noqa: E402


# --- HTML --------------------------------------------------------------


def test_html_active_marked_passes():
    html = "<html><body><main data-stub-active>...</main></body></html>"
    assert_marker_consistent(html, stub_active=True, format="html")


def test_html_active_unmarked_raises():
    html = "<html><body><main>...</main></body></html>"
    with pytest.raises(HS4MarkerError, match="missing"):
        assert_marker_consistent(html, stub_active=True, format="html")


def test_html_inactive_marked_raises():
    html = "<html><body><main data-stub-active>...</main></body></html>"
    with pytest.raises(HS4MarkerError, match="present"):
        assert_marker_consistent(html, stub_active=False, format="html")


def test_html_inactive_unmarked_passes():
    html = "<html><body><main>...</main></body></html>"
    assert_marker_consistent(html, stub_active=False, format="html")


def test_html_marker_with_attribute_value_accepted():
    html = '<main data-stub-active="true" class="x">...</main>'
    assert_marker_consistent(html, stub_active=True, format="html")


# --- JSON --------------------------------------------------------------


def test_json_dict_active_marked_passes():
    assert_marker_consistent({"_stub_active": True, "data": []}, True, "json")


def test_json_dict_active_unmarked_raises():
    with pytest.raises(HS4MarkerError, match="missing"):
        assert_marker_consistent({"data": []}, True, "json")


def test_json_dict_inactive_marked_raises():
    with pytest.raises(HS4MarkerError, match="present"):
        assert_marker_consistent({"_stub_active": True, "data": []}, False, "json")


def test_json_dict_inactive_unmarked_passes():
    assert_marker_consistent({"data": []}, False, "json")


def test_json_string_input_parsed():
    s = json.dumps({"_stub_active": True, "x": 1})
    assert_marker_consistent(s, True, "json")


def test_json_explicit_false_treated_as_unmarked():
    """`_stub_active: false` is not a marker (only true counts)."""
    with pytest.raises(HS4MarkerError, match="missing"):
        assert_marker_consistent({"_stub_active": False}, True, "json")


# --- CLI ---------------------------------------------------------------


def test_cli_active_with_stub_active_line_passes():
    err = "running...\nSTUB ACTIVE: mock — expires 2026-06-01\n"
    assert_marker_consistent(err, True, "cli")


def test_cli_active_with_stub_data_label_passes():
    err = "rendered output [stub data]\n"
    assert_marker_consistent(err, True, "cli")


def test_cli_active_unmarked_raises():
    with pytest.raises(HS4MarkerError, match="missing"):
        assert_marker_consistent("normal output\n", True, "cli")


def test_cli_inactive_marked_raises():
    with pytest.raises(HS4MarkerError, match="present"):
        assert_marker_consistent("STUB ACTIVE: x — expires 2099-01-01\n", False, "cli")


def test_cli_inactive_unmarked_passes():
    assert_marker_consistent("clean output\n", False, "cli")


# --- Format validation -------------------------------------------------


def test_unknown_format_raises_value_error():
    with pytest.raises(ValueError):
        assert_marker_consistent("x", True, "xml")  # type: ignore[arg-type]


def test_hs4_marker_error_is_assertion_error():
    """HS4MarkerError must inherit from AssertionError so pytest.raises(AssertionError) catches it."""
    assert issubclass(HS4MarkerError, AssertionError)
