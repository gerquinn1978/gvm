"""Keyword presence tests for `/gvm-test-cases` SKILL.md (P12-C05).

TC-PP-1-01: SKILL.md mentions every helper, tag, ADR, and literal that
Phase 12 wired in. The SKILL.md is the contract Claude follows when
generating test cases — keyword drift breaks the runtime behaviour
silently because the assistant simply stops invoking the helper.

TC-EBT-7-01..02: the property-detection heuristic — the gate Phase 2
uses to decide [PROPERTY] emission — fires on a property-shaped
requirement and stays silent on a non-property one. These confirm the
signal Claude follows in Phase 2 (the integrated emission path itself
is the LLM executing SKILL.md; the heuristic gate is what we can lock).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SKILL_MD = HERE.parent / "SKILL.md"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from _property_detection import load_property_detection  # noqa: E402


REQUIRED_KEYWORDS: tuple[str, ...] = (
    "_ebt_validator",
    "_ebt_contract_lint",
    "_trace_resolver",
    "[EXAMPLE]",
    "[CONTRACT]",
    "[COLLABORATION]",
    "[PROPERTY]",
    "[Trace:",
    "EBT-1",
    "ADR-501",
    "ADR-502",
    "ADR-503",
    "ADR-504",
    "ADR-505",
    "ADR-506",
    "ADR-507",
    "ADR-508",
    "_retrofit",
    "EBT-6",
    ".ebt-boundaries",
    "MUST contain",
    "MUST NOT contain",
)


@pytest.fixture(scope="module")
def skill_text() -> str:
    return SKILL_MD.read_text(encoding="utf-8")


@pytest.mark.parametrize("kw", REQUIRED_KEYWORDS)
def test_skill_md_contains_keyword(skill_text: str, kw: str) -> None:
    assert kw in skill_text, f"SKILL.md missing required keyword: {kw!r}"


def test_skill_md_references_property_detection_artefact(skill_text: str) -> None:
    """Either the module import name or the heuristic file name must appear."""
    assert (
        "_property_detection" in skill_text or "property-detection.md" in skill_text
    ), "SKILL.md must reference the property-detection module or heuristic file"


def test_skill_md_frontmatter_present(skill_text: str) -> None:
    lines = skill_text.splitlines()
    assert lines[0].strip() == "---", "SKILL.md must start with frontmatter"
    # Closing --- within the first 50 lines.
    assert any(line.strip() == "---" for line in lines[1:50]), (
        "SKILL.md frontmatter must close within the first 50 lines"
    )


def test_property_detection_signals_idempotence() -> None:
    """TC-EBT-7-01: a normalise-shaped requirement triggers `idempotence`."""
    heuristic = load_property_detection()
    matches = heuristic.matches("the system shall normalise input strings")
    assert "idempotence" in matches, f"Expected 'idempotence' in matches; got {matches}"


def test_property_detection_silent_on_nonproperty() -> None:
    """TC-EBT-7-02: a UI-display requirement does NOT trigger any category."""
    heuristic = load_property_detection()
    matches = heuristic.matches(
        "the system shall display the dashboard for logged-in users"
    )
    assert matches == (), f"Expected no property match; got {matches}"
