"""SKILL.md scaffold tests for `/gvm-explore-test` (P11-C06).

Covers TC-ET-1-01 (file exists at canonical path) and TC-ET-1-02 (pipeline
position string). The user-guide.html test is deferred to P13-C09 which
delivers the user guides; this chunk only asserts the SKILL.md contract.
"""

from __future__ import annotations

from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parents[1]
SKILL_MD = SKILL_DIR / "SKILL.md"


@pytest.fixture(scope="module")
def skill_text() -> str:
    return SKILL_MD.read_text(encoding="utf-8")


def test_skill_md_exists():
    """TC-ET-1-01: `/gvm-explore-test/SKILL.md` exists."""
    assert SKILL_MD.exists(), f"missing: {SKILL_MD}"


def test_pipeline_position_string(skill_text):
    """TC-ET-1-02: SKILL.md names "after `/gvm-test`, before `/gvm-doc-write`"."""
    assert "after `/gvm-test`, before `/gvm-doc-write`" in skill_text


def test_canonical_six_sections_present_in_order(skill_text):
    """ADR-201 / cross-cutting ADR-001 — six-section template, in order."""
    expected = [
        "## Overview",
        "## Hard Gates",
        "## Expert Panel",
        "## Process Flow",
        "## Phase Details",
        "## Key Rules",
    ]
    last_idx = -1
    for heading in expected:
        idx = skill_text.find(heading)
        assert idx != -1, f"missing section: {heading}"
        assert idx > last_idx, f"section out of order: {heading}"
        last_idx = idx


def test_skill_references_charter_validator(skill_text):
    """The SKILL.md must reference the charter validator (`_charter.load`)
    so the Phase 1 charter-validation gate has a concrete implementation."""
    assert "_charter" in skill_text


def test_skill_names_charter_yml_path_format(skill_text):
    """ADR-202 — charter file path is `test/explore-NNN.charter.yml` with
    NNN zero-padded to three digits."""
    assert "test/explore-NNN.charter.yml" in skill_text


def test_skill_names_downstream_chunks(skill_text):
    """Forward-references to P11-C07/08/09/10 establish the build sequence
    for downstream readers — they must be present and called out as
    upcoming, not silently assumed."""
    for chunk in ("P11-C07", "P11-C08", "P11-C09", "P11-C10"):
        assert chunk in skill_text, f"missing forward-reference: {chunk}"
