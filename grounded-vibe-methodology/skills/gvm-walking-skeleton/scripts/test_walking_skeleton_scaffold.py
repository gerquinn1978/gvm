"""P11-C01 smoke test: /gvm-walking-skeleton SKILL.md scaffold loads with the
canonical six sections (cross-cutting ADR-001, walking-skeleton ADR-401)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

SKILL_MD = Path(__file__).resolve().parents[1] / "SKILL.md"

REQUIRED_SECTIONS: tuple[str, ...] = (
    "Overview",
    "Hard Gates",
    "Expert Panel",
    "Process Flow",
    "Phase Details",
    "Key Rules",
)


def _read(path: Path) -> str:
    if not path.exists():
        pytest.fail(f"missing required file: {path}")
    return path.read_text(encoding="utf-8")


def test_skill_md_exists_with_frontmatter() -> None:
    text = _read(SKILL_MD)
    assert text.startswith("---\n"), "SKILL.md must start with frontmatter"
    end = text.find("\n---\n", 4)
    assert end != -1, "SKILL.md frontmatter must be closed with `---`"
    front = text[4:end]
    assert re.search(r"^name:\s*gvm-walking-skeleton\s*$", front, re.MULTILINE), (
        "frontmatter must declare name: gvm-walking-skeleton"
    )
    assert re.search(r"^description:\s*\S", front, re.MULTILINE), (
        "frontmatter must declare a non-empty description"
    )


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_skill_md_contains_section(section: str) -> None:
    text = _read(SKILL_MD)
    pattern = rf"^##\s+{re.escape(section)}\s*$"
    assert re.search(pattern, text, re.MULTILINE), (
        f"SKILL.md missing required H2 section: {section}"
    )


def test_skill_md_section_order() -> None:
    text = _read(SKILL_MD)
    positions: list[int] = []
    for section in REQUIRED_SECTIONS:
        match = re.search(rf"^##\s+{re.escape(section)}\s*$", text, re.MULTILINE)
        assert match is not None, f"missing section: {section}"
        positions.append(match.start())
    assert positions == sorted(positions), (
        "sections must appear in canonical order: " + " → ".join(REQUIRED_SECTIONS)
    )


def test_skill_md_references_pipeline_position() -> None:
    text = _read(SKILL_MD)
    assert "Pipeline position:" in text, (
        "SKILL.md must declare its pipeline position (cross-cutting convention)"
    )


def test_skill_md_loads_shared_rules() -> None:
    text = _read(SKILL_MD)
    assert "shared-rules.md" in text, (
        "SKILL.md must reference loading shared-rules.md (shared rule 17)"
    )
