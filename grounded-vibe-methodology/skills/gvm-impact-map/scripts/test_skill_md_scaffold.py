"""P10-C01 smoke test: /gvm-impact-map SKILL.md scaffold loads with the
canonical six sections (cross-cutting ADR-001, discovery ADR-301)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

SKILL_MD = Path(__file__).resolve().parents[1] / "SKILL.md"
USER_GUIDE = Path(__file__).resolve().parents[1] / "docs" / "user-guide.html"

# Canonical six-section template per cross-cutting ADR-001. The order is part
# of the contract — downstream tooling (and human readers) rely on it.
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
    # Frontmatter is opened and closed by `---` on its own line. Claude Code's
    # skill loader requires `name:` and `description:` fields inside.
    assert text.startswith("---\n"), "SKILL.md must start with frontmatter"
    end = text.find("\n---\n", 4)
    assert end != -1, "SKILL.md frontmatter must be closed with `---`"
    front = text[4:end]
    assert re.search(r"^name:\s*gvm-impact-map\s*$", front, re.MULTILINE), (
        "frontmatter must declare name: gvm-impact-map"
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


def test_user_guide_html_exists() -> None:
    text = _read(USER_GUIDE)
    # Skeleton requirement: must be valid-ish HTML and reference the skill.
    assert "<html" in text.lower()
    assert "gvm-impact-map" in text
