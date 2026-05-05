"""Keyword presence test for `/gvm-walking-skeleton` SKILL.md (R24 CR-5).

Locks the gate-ID and ADR cross-references in the frontmatter and body to
the canonical forms used in code/tests. Pre-fix the frontmatter said
``VV-3(d) sandbox-divergence check`` where every other surface uses
``VV-4(d)``; same line said ``HS-5 namespace per ADR-104`` where every
other surface uses ``HS-1`` and ``ADR-407``. This test lights up if any
of those drift back.

Pattern matches the BC-candidate from R21→R24: every SKILL.md frontmatter
and gate-ID reference must be exercised by a parser/keyword test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

SKILL_MD = Path(__file__).resolve().parents[1] / "SKILL.md"


@pytest.fixture(scope="module")
def skill_text() -> str:
    return SKILL_MD.read_text(encoding="utf-8")


def test_frontmatter_uses_vv4d_not_vv3d(skill_text: str) -> None:
    """Frontmatter description names the explore-test gate as VV-4(d).
    VV-3(d) is the sandbox-divergence criterion — a different gate."""
    # Read just the frontmatter block (between the first two --- markers).
    lines = skill_text.splitlines()
    assert lines[0].strip() == "---", "SKILL.md must start with frontmatter"
    end = lines.index("---", 1)
    frontmatter = "\n".join(lines[1 : end])
    assert "VV-4(d)" in frontmatter, "VV-4(d) must appear in frontmatter description"
    assert "VV-3(d)" not in frontmatter, (
        "VV-3(d) must not appear in frontmatter (R24 CR-5 — it routes "
        "agents to the wrong criterion row of the verdict table)"
    )


def test_stub_namespace_uses_hs1_not_hs5(skill_text: str) -> None:
    """Stub-namespace rules cross-reference HS-1 (the deferred-stub gate),
    not HS-5. HS-5 is a different gate ID in the honesty-triad family."""
    assert "HS-1" in skill_text, "HS-1 must appear in walking-skeleton SKILL.md"
    assert "HS-5" not in skill_text, (
        "HS-5 must not appear (R24 I-7 — drift from HS-1)"
    )


def test_adr_407_referenced_for_stub_namespace(skill_text: str) -> None:
    """The stub-namespace authority is ADR-407, not ADR-104."""
    assert "ADR-407" in skill_text
    assert "ADR-104" not in skill_text, (
        "ADR-104 must not appear in walking-skeleton SKILL.md (R24 I-8 — "
        "drift from ADR-407, the actual stub-namespace authority)"
    )


def test_ws5_red_skeleton_refusal_present(skill_text: str) -> None:
    """WS-5 is the primary downstream contract for the walking-skeleton skill
    (red-skeleton refusal hook in /gvm-build). Lock the routing string so a
    future edit cannot silently rename or drop it (R25 M-2 — the symmetric
    regression of the R24 CR-5 VV-3/VV-4 drift)."""
    assert "WS-5" in skill_text, (
        "WS-5 must appear in walking-skeleton SKILL.md — it is the primary "
        "gate ID for the red-skeleton refusal contract that /gvm-build keys "
        "off. Removing or renaming WS-5 here breaks downstream routing."
    )
