"""Release-gate verifier: seven cross-cutting checks per ADR-609.

These complement `_verify_pp1.py` (which covers SKILL.md keyword propagation).
Each check is a small pure function returning a list of `Failure` records;
the aggregator `verify(plugin_root, repo_root)` collects them.

CLI:
    python -m _verify_pp_cross_cutting [--plugin-root P] [--repo-root R]

Defaults:
    --plugin-root  ~/.claude/skills/gvm-design-system
    --repo-root    Path.cwd()

Exit code 0 if all seven checks pass; 1 otherwise.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Hard-coded tables (single source of truth — tests re-import these).
# ---------------------------------------------------------------------------

PP6_REQUIRED_SECTIONS: tuple[str, ...] = (
    "## STUBS.md",
    "## impact-map.md",
    "## risks/risk-assessment.md",
    "## boundaries.md",
    "## test/explore-NNN.md",
    "## reviews/build-checks.md",
    "## .gvm-track2-adopted",
)

PP5_GUIDE_HEADINGS: dict[str, str] = {
    "gvm-build": "Working with STUBS.md",
    "gvm-test": "Verdict Vocabulary",
    "gvm-code-review": "Panel E",
    "gvm-requirements": "IM-4",
    "gvm-test-cases": "EBT-1",
}

NEW_SKILL_GUIDES: tuple[str, ...] = (
    "gvm-impact-map",
    "gvm-walking-skeleton",
    "gvm-explore-test",
)

RULE_25_LITERAL = "25. **No silent skip, defer, or stub.**"

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
TAG_SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


@dataclass(frozen=True)
class Failure:
    check_id: int
    message: str

    def __str__(self) -> str:
        return f"check {self.check_id}: {self.message}"


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def check_shared_rule_25(plugin_root: Path) -> list[Failure]:
    p = plugin_root / "references" / "shared-rules.md"
    if not p.exists():
        return [Failure(1, f"shared-rules.md not found at {p}")]
    if RULE_25_LITERAL not in p.read_text(encoding="utf-8"):
        return [
            Failure(
                1,
                f"shared-rules.md missing literal {RULE_25_LITERAL!r}",
            )
        ]
    return []


def check_pipeline_contracts_sections(plugin_root: Path) -> list[Failure]:
    p = plugin_root / "references" / "pipeline-contracts.md"
    if not p.exists():
        return [Failure(2, f"pipeline-contracts.md not found at {p}")]
    text = p.read_text(encoding="utf-8")
    failures: list[Failure] = []
    for heading in PP6_REQUIRED_SECTIONS:
        # Heading must appear at start-of-line (an actual H2, not prose).
        if not re.search(rf"^{re.escape(heading)}\s*$", text, re.MULTILINE):
            failures.append(
                Failure(
                    2,
                    f"pipeline-contracts.md missing H2 heading {heading!r}",
                )
            )
    return failures


def check_pp5_user_guides(skills_root: Path) -> list[Failure]:
    failures: list[Failure] = []
    for skill, heading in PP5_GUIDE_HEADINGS.items():
        guide = skills_root / skill / "docs" / "user-guide.html"
        if not guide.exists():
            failures.append(
                Failure(3, f"PP-5 user guide not found at {guide}")
            )
            continue
        if heading not in guide.read_text(encoding="utf-8"):
            failures.append(
                Failure(
                    3,
                    f"{skill}/docs/user-guide.html missing heading {heading!r}",
                )
            )
    return failures


def check_new_skill_guides(skills_root: Path) -> list[Failure]:
    failures: list[Failure] = []
    for skill in NEW_SKILL_GUIDES:
        guide = skills_root / skill / "docs" / "user-guide.html"
        if not guide.exists():
            failures.append(
                Failure(4, f"new-skill user guide not found: {guide}")
            )
    return failures


def _parse_semver(s: str) -> Optional[tuple[int, int, int]]:
    m = SEMVER_RE.match(s)
    return (int(m[1]), int(m[2]), int(m[3])) if m else None


def _latest_tag_semver(repo_root: Path) -> Optional[tuple[int, int, int]]:
    """Return semver of the most recent annotated/lightweight tag, or None.

    A repo with no tags returns None — caller treats as "no baseline; any
    valid semver passes."
    """
    try:
        out = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "tag",
                "--list",
                "--sort=-version:refname",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    for line in out.stdout.splitlines():
        m = TAG_SEMVER_RE.match(line.strip())
        if m:
            return (int(m[1]), int(m[2]), int(m[3]))
    return None


def check_version_file(plugin_root: Path, repo_root: Path) -> list[Failure]:
    p = plugin_root / "VERSION"
    if not p.exists():
        return [Failure(5, f"VERSION not found at {p}")]
    raw = p.read_text(encoding="utf-8")
    if not raw.strip():
        return [Failure(5, "VERSION is empty")]
    # Strip a single trailing newline only — extra lines are a contract violation.
    body = raw[:-1] if raw.endswith("\n") else raw
    if "\n" in body:
        return [Failure(5, "VERSION must contain exactly one line")]
    parsed = _parse_semver(body.strip())
    if parsed is None:
        return [Failure(5, f"VERSION line {body.strip()!r} is not valid semver")]
    tag = _latest_tag_semver(repo_root)
    if tag is not None and parsed <= tag:
        return [
            Failure(
                5,
                f"VERSION {body.strip()} must be strictly greater than "
                f"latest tag {tag[0]}.{tag[1]}.{tag[2]}",
            )
        ]
    return []


def check_releases_h1_matches_version(plugin_root: Path) -> list[Failure]:
    p = plugin_root / "RELEASES.md"
    version_file = plugin_root / "VERSION"
    if not version_file.exists():
        # Already reported by check_version_file; do not double-report here.
        return []
    version_lines = version_file.read_text(encoding="utf-8").strip().splitlines()
    if not version_lines:
        # Empty VERSION — check_version_file owns the failure report.
        return []
    version = version_lines[0]
    if not p.exists():
        return [Failure(6, f"RELEASES.md not found at {p}")]
    text = p.read_text(encoding="utf-8")
    expected = f"# v{version}"
    # Anchor end-of-line / whitespace, not `\b`. A word boundary would falsely
    # match `# v1.4.0-rc1` when VERSION is `1.4.0` (prerelease leaks through
    # the gate and the release ships without a final release-notes entry).
    if not re.search(rf"^{re.escape(expected)}(?:\s|$)", text, re.MULTILINE):
        return [
            Failure(
                6,
                f"RELEASES.md missing H1 entry matching VERSION ({expected!r})",
            )
        ]
    return []


def _git_head(repo_root: Path) -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return out.stdout.strip() or None


def check_release_notes_reference_head(
    plugin_root: Path, repo_root: Path
) -> list[Failure]:
    p = plugin_root / "RELEASES.md"
    if not p.exists():
        return []  # already reported by check 6
    head = _git_head(repo_root)
    if head is None:
        return [Failure(7, f"could not resolve git HEAD in {repo_root}")]
    text = p.read_text(encoding="utf-8")
    # Allow short-hash references (≥ 7 chars) per common convention.
    if head not in text and head[:7] not in text:
        return [
            Failure(
                7,
                f"RELEASES.md does not reference current HEAD commit ({head[:12]})",
            )
        ]
    return []


# ---------------------------------------------------------------------------
# Aggregator + CLI
# ---------------------------------------------------------------------------


def verify(
    plugin_root: Path,
    repo_root: Path,
    skills_root: Optional[Path] = None,
) -> list[Failure]:
    """Aggregate all seven cross-cutting checks.

    `plugin_root` points at the `gvm-design-system` skill (where references/,
    VERSION, RELEASES.md live). `skills_root` points at the parent skills/
    directory (where sibling skill folders live). They are distinct because
    the live deployment layout has skills as siblings under
    `~/.claude/skills/`, not as children of `gvm-design-system`. When
    `skills_root` is None it defaults to `plugin_root.parent`.
    """
    if skills_root is None:
        skills_root = plugin_root.parent
    failures: list[Failure] = []
    failures.extend(check_shared_rule_25(plugin_root))
    failures.extend(check_pipeline_contracts_sections(plugin_root))
    failures.extend(check_pp5_user_guides(skills_root))
    failures.extend(check_new_skill_guides(skills_root))
    failures.extend(check_version_file(plugin_root, repo_root))
    failures.extend(check_releases_h1_matches_version(plugin_root))
    failures.extend(check_release_notes_reference_head(plugin_root, repo_root))
    return failures


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="_verify_pp_cross_cutting")
    parser.add_argument(
        "--plugin-root",
        type=Path,
        default=Path.home() / ".claude" / "skills" / "gvm-design-system",
        help="Path to the gvm-design-system skill root (default: ~/.claude/skills/gvm-design-system).",
    )
    parser.add_argument(
        "--skills-root",
        type=Path,
        default=None,
        help="Path to the parent skills/ directory containing sibling skill folders "
        "(default: plugin-root's parent — i.e. ~/.claude/skills/).",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Path to the git working tree (default: cwd).",
    )
    args = parser.parse_args(argv[1:])

    failures = verify(args.plugin_root, args.repo_root, args.skills_root)
    if not failures:
        sys.stdout.write(
            "PP cross-cutting PASS — all 7 release-gate checks succeeded\n"
        )
        return 0

    sys.stderr.write(
        f"PP cross-cutting FAIL — {len(failures)} failure(s):\n"
    )
    for f in failures:
        sys.stderr.write(f"  - {f}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
