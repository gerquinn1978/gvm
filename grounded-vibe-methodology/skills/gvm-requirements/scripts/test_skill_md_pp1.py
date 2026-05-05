"""Substring-contract tests for PP-1 (pipeline-propagation ADR-601, TC-PP-1-01).

`gvm-requirements/SKILL.md` is one of the five SKILL.md files PP-1 names. The
release-gate verifier (`_verify_pp1.py`) greps for these keywords; this test
pins the contract at the source so a future edit cannot drop a keyword
silently.

Also pins the helper references introduced across Phase 10 — the SKILL.md
must continue to invoke each of `_im4_check.check`, `_im5_handler.classify_intent`,
`_im6_check.persona_actor_coupling`, `_ra6_trace`, and `_risk_validator.full_check`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_SKILL_MD = Path(__file__).resolve().parent.parent / "SKILL.md"


@pytest.fixture(scope="module")
def skill_md_text() -> str:
    return _SKILL_MD.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "keyword,reason",
    [
        ("IM-4", "ADR-601 PP-1 grep keyword — IM-4 refusal must be referenced"),
        ("RA-3", "ADR-601 PP-1 grep keyword — RA-3 block must be referenced"),
        (
            "impact-deliverable",
            "ADR-601 PP-1 grep keyword — impact-deliverable tag (spelled per ADR-601 line 59, no brackets)",
        ),
    ],
)
def test_pp1_keyword_present(skill_md_text: str, keyword: str, reason: str):
    assert keyword in skill_md_text, f"PP-1 keyword '{keyword}' missing — {reason}"


@pytest.mark.parametrize(
    "helper",
    [
        "_im4_check",
        "_im5_handler",
        "_im6_check",
        "_ra6_trace",
        "_risk_validator",
    ],
)
def test_phase_10_helper_referenced(skill_md_text: str, helper: str):
    assert helper in skill_md_text, (
        f"Phase 10 helper '{helper}' must be referenced in SKILL.md so the "
        "skill executes the gate it documents."
    )


_STEP_LINE_RE = re.compile(r"^(\d+)\.\s+(.*)$")


def _phase_5_steps(text: str) -> list[tuple[int, str]]:
    """Parse the Phase 5 numbered list. Returns (number, step-title) pairs.

    Walks from `### Phase 5 — Finalize` to the next `### ` heading,
    matching only top-level `N. <title>` lines (no leading whitespace).
    Strips bold markers and stops at the first em-dash, period, or colon
    so the title is the bare step name.
    """
    start = text.index("### Phase 5 — Finalize")
    # Skip past the heading line so the terminator match doesn't snag it.
    after_heading = text.index("\n", start) + 1
    end_match = re.search(r"^##\s", text[after_heading:], re.MULTILINE)
    section = (
        text[after_heading : after_heading + end_match.start()]
        if end_match
        else text[after_heading:]
    )
    steps: list[tuple[int, str]] = []
    for line in section.splitlines():
        m = _STEP_LINE_RE.match(line)
        if m is None:
            continue
        n = int(m.group(1))
        rest = m.group(2).strip()
        # Strip leading and trailing `**` bold markers so titles compare cleanly.
        if rest.startswith("**"):
            close = rest.find("**", 2)
            title = rest[2:close] if close != -1 else rest[2:]
        else:
            # Trim at first em-dash / period / colon for steps without bold.
            for sep in (" — ", ". ", ": "):
                if sep in rest:
                    rest = rest.split(sep, 1)[0]
                    break
            title = rest
        steps.append((n, title.strip()))
    return steps


def test_phase_5_step_5_actually_is_generate_index(skill_md_text: str):
    """Structural invariant: the IM-4 gate's cross-reference says
    "step 5 (Generate the requirements index table)", and step 5 in the
    Phase 5 numbered list MUST actually start with that title.

    Pinning the cross-reference string alone (e.g. `"step 5 (Generate...)" in text`)
    is a tautology that passes whenever any future edit reorders Phase 5 but
    forgets to update the cross-reference. This test parses the numbered list
    and asserts step 5 IS the index-generation step.
    """
    steps = dict(_phase_5_steps(skill_md_text))
    assert 5 in steps, f"Phase 5 has no step 5; found {sorted(steps)}"
    assert steps[5].startswith("Generate the requirements index table"), (
        f"Phase 5 step 5 must be index generation; found: {steps[5]!r}"
    )


def test_im4_cross_reference_points_at_index_generation_step(skill_md_text: str):
    """The IM-4 gate paragraph's `step N (Generate...)` cross-reference must
    name the same step number that actually contains index generation. This
    is the consolidation invariant P10-C10 enforces.
    """
    steps = dict(_phase_5_steps(skill_md_text))
    index_step = next(
        n
        for n, t in steps.items()
        if t.startswith("Generate the requirements index table")
    )
    cross_ref = f"step {index_step} (Generate the requirements index table)"
    assert cross_ref in skill_md_text, (
        f"IM-4 gate must cross-reference {cross_ref!r}; found stale cross-reference"
    )
