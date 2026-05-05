"""Keyword presence test for `/gvm-test` SKILL.md (partial TC-PP-1-01).

The full PP-1 verifier (P13-C03) scans every affected SKILL.md across the
plugin tree. This chunk-level test covers the gvm-test side specifically:
the new verdict-evaluation step must reference each of the protocol
keywords that PP-1 mandates for this skill.
"""

from __future__ import annotations

from pathlib import Path

import pytest

SKILL_MD = Path(__file__).resolve().parents[1] / "SKILL.md"


@pytest.fixture(scope="module")
def skill_text() -> str:
    return SKILL_MD.read_text(encoding="utf-8")


REQUIRED_KEYWORDS = (
    "three-verdict taxonomy",
    "Ship-ready",
    "Demo-ready",
    "Not shippable",
    "gvm_verdict.evaluate",
    "VV-6",
    "_calibration_parser",
)


@pytest.mark.parametrize("keyword", REQUIRED_KEYWORDS)
def test_skill_md_contains_keyword(skill_text: str, keyword: str):
    assert keyword in skill_text, (
        f"PP-1 keyword {keyword!r} missing from gvm-test/SKILL.md"
    )


def test_verdict_evaluation_step_named(skill_text: str):
    # The new step must be discoverable as a heading or bulleted step name.
    assert (
        "Evaluate verdict" in skill_text
        or "EVALUATE VERDICT" in skill_text
        or "VERDICT EVALUATION" in skill_text
    )


def test_retrofit_call_sequence_named(skill_text: str):
    # The retrofit's two-function API surface should both be named so a
    # reader can locate the call sequence.
    assert "plan_retrofit" in skill_text
    assert "apply_retrofit" in skill_text


def test_review_parser_referenced(skill_text: str):
    # Per ADR-106 the evaluator consumes _review_parser output.
    assert "_review_parser" in skill_text
