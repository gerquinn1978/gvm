"""Keyword presence test for `/gvm-build` SKILL.md (partial TC-PP-1-01).

The full PP-1 verifier (P13-C03) scans every affected SKILL.md across the
plugin tree. This chunk-level test covers the gvm-build side specifically:
the SKILL.md must reference each of the protocol keywords pipeline-propagation
ADR-601 mandates for this skill — and "retroactive" must be bound to the HS-6
audit-hook context, not the unrelated Rule 17 mention about handover edits.
"""

from __future__ import annotations

from pathlib import Path

import pytest

SKILL_MD = Path(__file__).resolve().parents[1] / "SKILL.md"

REQUIRED_KEYWORDS = ("STUBS.md", "HS-1", "retroactive", "WS-5", "red skeleton")


@pytest.fixture(scope="module")
def skill_text() -> str:
    return SKILL_MD.read_text(encoding="utf-8")


@pytest.mark.parametrize("keyword", REQUIRED_KEYWORDS)
def test_skill_md_contains_keyword(skill_text: str, keyword: str):
    assert keyword in skill_text, (
        f"PP-1 keyword {keyword!r} missing from gvm-build/SKILL.md"
    )


def test_retroactive_bound_to_hs6_context(skill_text: str):
    """HS-6 retroactive audit reference must exist — not just the unrelated
    Rule 17 'retroactively change P1-C04's handover' mention.

    Proximity rule: at least one occurrence of "retroactive" sits within 5
    lines of an "HS-6" mention. Without this, the keyword is structurally
    present but semantically empty for PP-1's purpose.
    """
    lines = skill_text.splitlines()
    hs6_line_idxs = [i for i, line in enumerate(lines) if "HS-6" in line]
    retro_line_idxs = [i for i, line in enumerate(lines) if "retroactive" in line]
    assert hs6_line_idxs, "expected at least one HS-6 reference in gvm-build/SKILL.md"
    assert retro_line_idxs, "expected at least one 'retroactive' reference"
    paired = any(abs(h - r) <= 5 for h in hs6_line_idxs for r in retro_line_idxs)
    assert paired, (
        "PP-1 requires 'retroactive' to appear near an HS-6 mention "
        "(HS-6 retroactive-audit hook). The standalone Rule 17 mention does "
        "not satisfy ADR-601."
    )


def test_ws5_bound_to_red_skeleton_context(skill_text: str):
    """WS-5 hook block must mention both 'WS-5' and 'red skeleton' close
    together. A future edit that removes the WS-5 SKELETON STATUS GATE block
    while leaving 'WS-5' elsewhere (e.g. in unrelated commentary) must fail.
    """
    lines = skill_text.splitlines()
    ws5_idxs = [i for i, line in enumerate(lines) if "WS-5" in line]
    red_idxs = [i for i, line in enumerate(lines) if "red skeleton" in line.lower()]
    assert ws5_idxs, "expected at least one WS-5 reference in gvm-build/SKILL.md"
    assert red_idxs, "expected at least one 'red skeleton' reference"
    paired = any(abs(w - r) <= 10 for w in ws5_idxs for r in red_idxs)
    assert paired, (
        "WS-5 hook requires 'WS-5' to appear near 'red skeleton' "
        "(walking-skeleton ADR-406). The block must remain present."
    )
