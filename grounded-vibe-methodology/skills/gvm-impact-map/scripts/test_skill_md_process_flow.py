"""Tests for P10-C04 — `/gvm-impact-map` process flow elicitation contract.

Pin the AskUserQuestion-driven elicitation surface that the LLM agent
running this skill must follow. These are substring/section assertions;
they do not lock down exact wording.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_SKILL = Path(__file__).resolve().parent.parent / "SKILL.md"


def _section(text: str, header: str) -> str:
    """Return the body between ``## {header}`` (or ``### {header}``) and
    the next same-level header. Raises if the section is absent."""
    pattern = rf"(^|\n)(#{{2,3}})\s+{re.escape(header)}\s*\n"
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


def test_scaffold_note_removed(skill_text: str):
    """The 'Scaffold note (P10-C01)' admonition is no longer accurate
    once P10-C04 ships the elicitation flow."""
    assert "Scaffold note (P10-C01)" not in skill_text


def test_phase_1_uses_askuserquestion(skill_text: str):
    body = _section(skill_text, "Phase 1 — Discovery")
    assert "AskUserQuestion" in body


def test_phase_2_uses_askuserquestion(skill_text: str):
    body = _section(skill_text, "Phase 2 — Actors")
    assert "AskUserQuestion" in body


def test_phase_3_uses_askuserquestion(skill_text: str):
    body = _section(skill_text, "Phase 3 — Impacts")
    assert "AskUserQuestion" in body


def test_phase_4_uses_askuserquestion(skill_text: str):
    body = _section(skill_text, "Phase 4 — Deliverables")
    assert "AskUserQuestion" in body


def test_phase_5_invokes_full_check(skill_text: str):
    body = _section(skill_text, "Phase 5 — Validation")
    assert "_validator.full_check" in body


def test_phase_6_writes_paired_artefacts(skill_text: str):
    body = _section(skill_text, "Phase 6 — Approval")
    assert "impact-map.md" in body
    assert "impact-map.html" in body


def test_phase_6_changelog_appended(skill_text: str):
    body = _section(skill_text, "Phase 6 — Approval")
    assert "Changelog" in body


def test_deliverable_type_enum_present(skill_text: str):
    body = _section(skill_text, "Phase 4 — Deliverables")
    for kind in ("feature", "content", "process", "tool"):
        assert kind in body, f"Deliverable Type enum missing {kind!r}"


def test_actor_cardinality_warning_present(skill_text: str):
    body = _section(skill_text, "Phase 2 — Actors")
    # The skill warns above 5 but does not refuse.
    assert "5" in body
    assert "warn" in body.lower() or "warning" in body.lower()


def test_phase_5_loops_until_clean(skill_text: str):
    """Validation failure must loop back, not abort."""
    body = _section(skill_text, "Phase 5 — Validation")
    # Either explicit "loop", "until clean", or "repeat" is acceptable.
    assert any(token in body.lower() for token in ("loop", "until clean", "repeat"))


def test_phase_5_documents_tuple_return(skill_text: str):
    """The return-shape contract `(impact_map, errors)` must be named in
    Phase 5 so the agent does not assume `impact_map` is always populated."""
    body = _section(skill_text, "Phase 5 — Validation")
    assert "(impact_map, errors)" in body


def test_phase_5_handles_impact_map_none(skill_text: str):
    """Phase 5 must explain the parse-failure branch where impact_map is None."""
    body = _section(skill_text, "Phase 5 — Validation")
    assert "None" in body


def test_phase_6_references_tufte_shell(skill_text: str):
    """The Tufte CSS shell path must appear in Phase 6 so the HTML render
    is not silently inconsistent with the rest of the GVM artefact suite."""
    body = _section(skill_text, "Phase 6 — Approval")
    assert "tufte-html-reference" in body


def test_phase_1_elicits_metric_and_target(skill_text: str):
    """A Goal without Metric and Target is unmeasurable; the elicitation
    must require both before drafting the row (independent reviewer
    catch — without this, the ambiguity scan passes vacuously on a
    Statement-only goal)."""
    body = _section(skill_text, "Phase 1 — Discovery")
    assert "Metric" in body and "Target" in body
