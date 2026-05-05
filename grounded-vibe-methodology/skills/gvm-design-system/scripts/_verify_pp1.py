"""Release-gate verifier: every PP-1 affected SKILL.md has its protocol keywords.

Per pipeline-propagation ADR-601, five skills' SKILL.md files must each
contain a hard-coded list of keywords proving the PP-1 propagation edits
landed. This script greps each file and reports any missing keyword.

Usage (CLI):
    python -m _verify_pp1 [--skills-dir PATH]

Default --skills-dir is ~/.claude/skills/ (the live plugin tree).
Tests pass a fixture tmp_path.

Exit code 0 if every file has every keyword; 1 otherwise (with stderr listing).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


SKILL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "gvm-build": ("STUBS.md", "HS-1", "retroactive"),
    "gvm-test": (
        "Ship-ready",
        "Demo-ready",
        "Not shippable",
        "VV-2",
        "VV-3",
        "VV-4",
    ),
    "gvm-code-review": ("Panel E", "Stub Detection", "SD-1"),
    "gvm-requirements": ("IM-4", "RA-3", "impact-deliverable"),
    "gvm-test-cases": ("EBT-1", "[EXAMPLE]", "[CONTRACT]", "[COLLABORATION]"),
}


@dataclass(frozen=True)
class Failure:
    skill: str
    keyword: Optional[str]  # None == file missing
    path: Path

    def __str__(self) -> str:
        if self.keyword is None:
            return f"{self.skill}/SKILL.md: file not found at {self.path}"
        return f"{self.skill}/SKILL.md: missing keyword {self.keyword!r}"


def verify(skills_dir: Path) -> list[Failure]:
    """Return a list of failures; empty list == pass."""
    failures: list[Failure] = []
    for skill, keywords in SKILL_KEYWORDS.items():
        skill_md = skills_dir / skill / "SKILL.md"
        if not skill_md.exists():
            failures.append(Failure(skill=skill, keyword=None, path=skill_md))
            continue
        text = skill_md.read_text(encoding="utf-8")
        for kw in keywords:
            if kw not in text:
                failures.append(Failure(skill=skill, keyword=kw, path=skill_md))
    return failures


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="_verify_pp1")
    parser.add_argument(
        "--skills-dir",
        type=Path,
        default=Path.home() / ".claude" / "skills",
        help="Path to the plugin's skills/ directory (default: ~/.claude/skills/).",
    )
    args = parser.parse_args(argv[1:])

    failures = verify(args.skills_dir)
    if not failures:
        sys.stdout.write(
            f"PP-1 PASS — all {len(SKILL_KEYWORDS)} SKILL.md files have all keywords\n"
        )
        return 0

    sys.stderr.write(f"PP-1 FAIL — {len(failures)} missing keyword(s):\n")
    for f in failures:
        sys.stderr.write(f"  - {f}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
