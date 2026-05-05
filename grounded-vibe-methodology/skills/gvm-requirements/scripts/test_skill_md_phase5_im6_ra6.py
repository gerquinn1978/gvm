"""Tests for P10-C09 — Phase 5 IM-6 + RA-6 hooks in `/gvm-requirements` SKILL.md."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_SKILL = Path(__file__).resolve().parent.parent / "SKILL.md"


def _section(text: str, header: str) -> str:
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


def test_phase_5_mentions_im6_helper(skill_text: str):
    body = _section(skill_text, "Phase 5 — Finalize")
    assert "_im6_check.persona_actor_coupling" in body


def test_phase_5_mentions_ra6_helpers(skill_text: str):
    body = _section(skill_text, "Phase 5 — Finalize")
    assert "_ra6_trace.risks_for_deliverable" in body or "risks_for_deliverable" in body
    assert "render_risks_cell" in body


def test_phase_5_mentions_related_risks_column(skill_text: str):
    body = _section(skill_text, "Phase 5 — Finalize")
    assert "Related Risks" in body


def test_phase_5_im6_is_non_blocking(skill_text: str):
    body = _section(skill_text, "Phase 5 — Finalize")
    assert (
        "non-blocking" in body.lower()
        or "advisory" in body.lower()
        or "flagged for review" in body.lower()
    )


def test_phase_5_ra6_uses_im_tags_parser(skill_text: str):
    body = _section(skill_text, "Phase 5 — Finalize")
    assert "parse_impact_deliverable_tag" in body
