"""Live-tree PP-7 test (TC-PP-7-01) for VERSION + RELEASES.md release artefacts.

Per pipeline-propagation ADR-607 the plugin ships with a `VERSION` file and a
`RELEASES.md` file. ADR-609 checks 5/6/7 (`check_version_file`,
`check_releases_h1_matches_version`, `check_release_notes_reference_head`)
encode the structural contract. Fixture-level tests live in
`test_verify_pp_cross_cutting.py`; this file adds a single end-to-end test
against the LIVE plugin tree, so the release artefacts cannot ship in a state
that satisfies the unit tests but breaks against the real repo.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import _verify_pp_cross_cutting as v


PROJECT_ROOT = Path(__file__).resolve().parents[4]
PLUGIN_ROOT = PROJECT_ROOT / "grounded-vibe-methodology" / "skills" / "gvm-design-system"


def test_real_plugin_tree_release_artefacts_present():
    """ADR-609 checks 5/6/7 pass against the live plugin tree."""
    failures = v.verify(PLUGIN_ROOT, PROJECT_ROOT)
    release_failures = [f for f in failures if f.check_id in (5, 6, 7)]
    assert release_failures == [], (
        "PP-7 release artefacts incomplete or invalid:\n"
        + "\n".join(f"  - {f}" for f in release_failures)
    )


def test_version_file_is_strictly_one_semver_line():
    """VERSION must be exactly one line containing a valid semver."""
    version_path = PLUGIN_ROOT / "VERSION"
    assert version_path.exists(), f"VERSION missing at {version_path}"
    raw = version_path.read_text(encoding="utf-8")
    body = raw[:-1] if raw.endswith("\n") else raw
    assert "\n" not in body, "VERSION must contain exactly one line"
    assert v.SEMVER_RE.match(body.strip()), (
        f"VERSION line {body.strip()!r} is not valid semver (X.Y.Z)"
    )


def test_releases_md_h1_matches_version():
    """RELEASES.md first H1 must read `# v<VERSION>` followed by ws/EOL."""
    import re
    version_lines = (PLUGIN_ROOT / "VERSION").read_text(encoding="utf-8").strip().splitlines()
    assert version_lines, "VERSION file is empty"
    version = version_lines[0]
    releases = (PLUGIN_ROOT / "RELEASES.md").read_text(encoding="utf-8")
    expected = f"# v{version}"
    assert re.search(rf"^{re.escape(expected)}(?:\s|$)", releases, re.MULTILINE), (
        f"RELEASES.md missing H1 entry matching VERSION ({expected!r})"
    )


def test_releases_md_references_current_head():
    """RELEASES.md must reference current git HEAD (full SHA or 7-char short)."""
    out = subprocess.run(
        ["git", "-C", str(PROJECT_ROOT), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    )
    head = out.stdout.strip()
    text = (PLUGIN_ROOT / "RELEASES.md").read_text(encoding="utf-8")
    assert head in text or head[:7] in text, (
        f"RELEASES.md does not reference current HEAD commit ({head[:12]})"
    )
