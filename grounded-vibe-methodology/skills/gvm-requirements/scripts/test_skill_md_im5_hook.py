"""Tests for P10-C08 — IM-5 Phase 2 hook in `/gvm-requirements` SKILL.md."""

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


def test_phase_2_mentions_im5_handler(skill_text: str):
    body = _section(skill_text, "Phase 2 — Seed-and-Branch Elicitation")
    assert "_im5_handler.classify_intent" in body


def test_phase_2_mentions_atomic_append_failure_path(skill_text: str):
    body = _section(skill_text, "Phase 2 — Seed-and-Branch Elicitation")
    assert "do not reference" in body.lower()


def test_phase_2_mentions_resume_previous_turn(skill_text: str):
    body = _section(skill_text, "Phase 2 — Seed-and-Branch Elicitation")
    assert "resume" in body.lower()
