"""Tests for P10-C07 — RA-3 Phase 0 + Phase 5 gates in `/gvm-requirements` SKILL.md.

Pin the wording contract that the agent reads at runtime: the validator
script name, the four risk section names, the loop-until-clean pattern,
and the practitioner option set per error class.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_SKILL = Path(__file__).resolve().parent.parent / "SKILL.md"


def _section(text: str, header: str) -> str:
    """Return the body between ``### {header}`` (or ``## {header}``) and the
    next same-level header. Raises if the section is absent."""
    pattern = rf"(^|\n)(#{{2,3}})\s+{re.escape(header)}\b[^\n]*\n"
    m = re.search(pattern, text)
    if m is None:
        raise AssertionError(f"section {header!r} not found")
    level = m.group(2)
    start = m.end()
    end_re = rf"\n{level}\s+\S"
    end_m = re.search(end_re, text[start:])
    return text[start:] if end_m is None else text[start : start + end_m.start()]


@pytest.fixture(scope="module")
def skill_text() -> str:
    return _SKILL.read_text(encoding="utf-8")


def test_phase_0_invokes_risk_validator(skill_text: str):
    # Phase 0 lives in the Process Flow block; we check the whole document
    # to avoid coupling to whether the bootstrap is a separate phase header.
    assert "_risk_validator.full_check" in skill_text


def test_phase_0_template_option_present(skill_text: str):
    """The bootstrap RA-1 gate must offer a 'create template' option."""
    body = _section(skill_text, "Phase 0 — Bootstrap & RA-1 prerequisite")
    assert "template" in body.lower()


def test_phase_5_ra3_gate_present(skill_text: str):
    body = _section(skill_text, "Phase 5 — Finalize")
    assert "_risk_validator.full_check" in body
    assert "RA-3" in body


def test_phase_5_loops_until_clean(skill_text: str):
    body = _section(skill_text, "Phase 5 — Finalize")
    assert any(
        token in body.lower() for token in ("loop", "until clean", "until empty")
    )


def test_phase_5_documents_tuple_return(skill_text: str):
    body = _section(skill_text, "Phase 5 — Finalize")
    assert "(risk_assessment, errors)" in body


def test_phase_5_lists_practitioner_options(skill_text: str):
    body = _section(skill_text, "Phase 5 — Finalize")
    lower = body.lower()
    assert "accepted-unknown" in lower
    assert "edit" in lower
    assert ("skip" in lower) or ("downgrade" in lower)


def test_phase_0_continue_without_is_discouraged(skill_text: str):
    body = _section(skill_text, "Phase 0 — Bootstrap & RA-1 prerequisite")
    assert "NOT RECOMMENDED" in body or "not recommended" in body.lower()


def test_four_risk_section_names_present(skill_text: str):
    for name in ("Value Risk", "Usability Risk", "Feasibility Risk", "Viability Risk"):
        assert name in skill_text, f"section name {name!r} missing from SKILL.md"
