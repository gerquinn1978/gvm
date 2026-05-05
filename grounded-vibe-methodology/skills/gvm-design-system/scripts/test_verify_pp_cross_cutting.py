"""Tests for `_verify_pp_cross_cutting.py` (TC-PP-7-02 — seven release-gate checks).

Per pipeline-propagation ADR-609 the verifier performs seven independent
checks against fixture inputs (`plugin_root`) and the surrounding git
working tree (`repo_root`). Each check has at least one pass + one fail
fixture; the table-driven `verify` aggregates failures.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import _verify_pp_cross_cutting as v


# ---------------------------------------------------------------------------
# Helpers — fixture builders
# ---------------------------------------------------------------------------


def _init_git_repo(repo_root: Path, *, head_msg: str = "initial commit") -> str:
    """Initialise a git repo, create one commit, return the HEAD hash."""
    subprocess.run(["git", "init", "-q", str(repo_root)], check=True)
    subprocess.run(
        ["git", "-C", str(repo_root), "config", "user.email", "test@example"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "config", "user.name", "Test"], check=True
    )
    (repo_root / "README.md").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo_root), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(repo_root), "commit", "-q", "-m", head_msg], check=True
    )
    out = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return out.stdout.strip()


def _build_passing_fixture(tmp_path: Path) -> tuple[Path, Path, str]:
    """Build a plugin tree + repo where every cross-cutting check passes.

    Returns (plugin_root, repo_root, head_hash).
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    head = _init_git_repo(repo_root)
    # Tag a baseline so VERSION > tag works.
    subprocess.run(
        ["git", "-C", str(repo_root), "tag", "v1.0.0"], check=True
    )

    # Live layout: plugin_root is a sibling of the other skill directories,
    # all under skills/. So skills_root == plugin_root.parent.
    skills_root = repo_root / "skills"
    plugin_root = skills_root / "gvm-design-system"
    refs = plugin_root / "references"
    refs.mkdir(parents=True)

    # Check 1 — shared-rules.md with rule 25
    (refs / "shared-rules.md").write_text(
        "# Shared rules\n\n25. **No silent skip, defer, or stub.**\n\n"
        "Body of rule 25 ...\n",
        encoding="utf-8",
    )
    # Check 2 — pipeline-contracts.md with seven H2 sections
    (refs / "pipeline-contracts.md").write_text(
        "# Pipeline contracts\n\n"
        "## STUBS.md\n\nbody\n\n"
        "## impact-map.md\n\nbody\n\n"
        "## risks/risk-assessment.md\n\nbody\n\n"
        "## boundaries.md\n\nbody\n\n"
        "## test/explore-NNN.md\n\nbody\n\n"
        "## reviews/build-checks.md\n\nbody\n\n"
        "## .gvm-track2-adopted\n\nbody\n",
        encoding="utf-8",
    )
    # Check 3 — five PP-5 user guides
    pp5_skills_headings = [
        ("gvm-build", "Working with STUBS.md"),
        ("gvm-test", "Verdict Vocabulary"),
        ("gvm-code-review", "Panel E"),
        ("gvm-requirements", "IM-4"),
        ("gvm-test-cases", "EBT-1"),
    ]
    skills = skills_root
    for skill, heading in pp5_skills_headings:
        d = skills / skill / "docs"
        d.mkdir(parents=True)
        (d / "user-guide.html").write_text(
            f"<html><body><h2>{heading}</h2></body></html>\n",
            encoding="utf-8",
        )
    # Check 4 — three new-skill user guides
    for skill in ("gvm-impact-map", "gvm-walking-skeleton", "gvm-explore-test"):
        d = skills / skill / "docs"
        d.mkdir(parents=True)
        (d / "user-guide.html").write_text(
            f"<html><body><h1>{skill}</h1></body></html>\n",
            encoding="utf-8",
        )
    # Check 5 — VERSION
    (plugin_root / "VERSION").write_text("1.4.0\n", encoding="utf-8")
    # Check 6 + 7 — RELEASES.md with H1 matching VERSION + commit hash
    (plugin_root / "RELEASES.md").write_text(
        f"# v1.4.0\n\nrelease notes\nrequirements doc commit: {head}\n",
        encoding="utf-8",
    )

    return plugin_root, repo_root, head


# ---------------------------------------------------------------------------
# Pass case
# ---------------------------------------------------------------------------


def test_passing_fixture_yields_no_failures(tmp_path: Path):
    plugin_root, repo_root, _ = _build_passing_fixture(tmp_path)
    failures = v.verify(plugin_root, repo_root)
    assert failures == [], f"unexpected failures: {failures}"


def test_main_returns_zero_on_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture
):
    plugin_root, repo_root, _ = _build_passing_fixture(tmp_path)
    rc = v.main(
        ["prog", "--plugin-root", str(plugin_root), "--repo-root", str(repo_root)]
    )
    assert rc == 0


# ---------------------------------------------------------------------------
# Per-check failure cases
# ---------------------------------------------------------------------------


def test_check1_missing_rule_25(tmp_path: Path):
    plugin_root, repo_root, _ = _build_passing_fixture(tmp_path)
    (plugin_root / "references" / "shared-rules.md").write_text(
        "# Shared rules\n\n(rule 25 not present)\n", encoding="utf-8"
    )
    failures = v.verify(plugin_root, repo_root)
    assert any(f.check_id == 1 for f in failures)


def test_check1_missing_shared_rules_file(tmp_path: Path):
    plugin_root, repo_root, _ = _build_passing_fixture(tmp_path)
    (plugin_root / "references" / "shared-rules.md").unlink()
    failures = v.verify(plugin_root, repo_root)
    assert any(f.check_id == 1 and "not found" in f.message for f in failures)


def test_check2_missing_pipeline_contract_section(tmp_path: Path):
    plugin_root, repo_root, _ = _build_passing_fixture(tmp_path)
    pc = plugin_root / "references" / "pipeline-contracts.md"
    text = pc.read_text(encoding="utf-8").replace("## boundaries.md\n", "")
    pc.write_text(text, encoding="utf-8")
    failures = [f for f in v.verify(plugin_root, repo_root) if f.check_id == 2]
    assert len(failures) == 1
    assert "boundaries.md" in failures[0].message


def test_check2_reports_each_missing_section_individually(tmp_path: Path):
    plugin_root, repo_root, _ = _build_passing_fixture(tmp_path)
    (plugin_root / "references" / "pipeline-contracts.md").write_text(
        "# empty\n", encoding="utf-8"
    )
    failures = [f for f in v.verify(plugin_root, repo_root) if f.check_id == 2]
    # All seven sections missing → seven failures.
    assert len(failures) == 7


def test_check3_missing_pp5_heading(tmp_path: Path):
    plugin_root, repo_root, _ = _build_passing_fixture(tmp_path)
    skills_root = plugin_root.parent
    guide = skills_root / "gvm-test" / "docs" / "user-guide.html"
    guide.write_text("<html><body>no heading</body></html>\n", encoding="utf-8")
    failures = [f for f in v.verify(plugin_root, repo_root) if f.check_id == 3]
    assert len(failures) == 1
    assert "Verdict Vocabulary" in failures[0].message


def test_check4_missing_new_skill_guide(tmp_path: Path):
    plugin_root, repo_root, _ = _build_passing_fixture(tmp_path)
    skills_root = plugin_root.parent
    (skills_root / "gvm-impact-map" / "docs" / "user-guide.html").unlink()
    failures = [f for f in v.verify(plugin_root, repo_root) if f.check_id == 4]
    assert len(failures) == 1
    assert "gvm-impact-map" in failures[0].message


def test_check5_missing_version(tmp_path: Path):
    plugin_root, repo_root, _ = _build_passing_fixture(tmp_path)
    (plugin_root / "VERSION").unlink()
    failures = [f for f in v.verify(plugin_root, repo_root) if f.check_id == 5]
    assert len(failures) == 1


def test_check5_invalid_semver(tmp_path: Path):
    plugin_root, repo_root, _ = _build_passing_fixture(tmp_path)
    (plugin_root / "VERSION").write_text("not-a-semver\n", encoding="utf-8")
    failures = [f for f in v.verify(plugin_root, repo_root) if f.check_id == 5]
    assert any("semver" in f.message.lower() for f in failures)


def test_check5_multiline_version(tmp_path: Path):
    plugin_root, repo_root, _ = _build_passing_fixture(tmp_path)
    (plugin_root / "VERSION").write_text("1.4.0\nextra-line\n", encoding="utf-8")
    failures = [f for f in v.verify(plugin_root, repo_root) if f.check_id == 5]
    assert any("exactly one line" in f.message for f in failures)


def test_check5_version_not_greater_than_tag(tmp_path: Path):
    plugin_root, repo_root, _ = _build_passing_fixture(tmp_path)
    # Most recent tag is v1.0.0; VERSION must be strictly greater. Set to equal.
    (plugin_root / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    failures = [f for f in v.verify(plugin_root, repo_root) if f.check_id == 5]
    assert any("greater" in f.message.lower() for f in failures)


def test_check5_passes_when_no_tags_yet(tmp_path: Path):
    """First-ever release: no git tags exist yet. VERSION just needs to parse."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    head = _init_git_repo(repo_root)  # no tags
    # Live layout: plugin_root is a sibling of the other skill directories,
    # all under skills/. So skills_root == plugin_root.parent.
    skills_root = repo_root / "skills"
    plugin_root = skills_root / "gvm-design-system"
    refs = plugin_root / "references"
    refs.mkdir(parents=True)
    # Build minimal passing fixture for the OTHER checks
    (refs / "shared-rules.md").write_text(
        "25. **No silent skip, defer, or stub.**\n", encoding="utf-8"
    )
    (refs / "pipeline-contracts.md").write_text(
        "## STUBS.md\n## impact-map.md\n## risks/risk-assessment.md\n"
        "## boundaries.md\n## test/explore-NNN.md\n"
        "## reviews/build-checks.md\n## .gvm-track2-adopted\n",
        encoding="utf-8",
    )
    pp5 = [
        ("gvm-build", "Working with STUBS.md"),
        ("gvm-test", "Verdict Vocabulary"),
        ("gvm-code-review", "Panel E"),
        ("gvm-requirements", "IM-4"),
        ("gvm-test-cases", "EBT-1"),
    ]
    skills = skills_root
    for s, h in pp5:
        d = skills / s / "docs"
        d.mkdir(parents=True)
        (d / "user-guide.html").write_text(
            f"<h2>{h}</h2>", encoding="utf-8"
        )
    for s in ("gvm-impact-map", "gvm-walking-skeleton", "gvm-explore-test"):
        d = skills / s / "docs"
        d.mkdir(parents=True)
        (d / "user-guide.html").write_text("<h1/>", encoding="utf-8")
    (plugin_root / "VERSION").write_text("0.1.0\n", encoding="utf-8")
    (plugin_root / "RELEASES.md").write_text(
        f"# v0.1.0\n\nseed: {head}\n", encoding="utf-8"
    )

    failures = [f for f in v.verify(plugin_root, repo_root) if f.check_id == 5]
    assert failures == []


def test_check5_and_6_handle_empty_version_file(tmp_path: Path):
    """An empty VERSION file must surface as a check-5 failure, not crash check 6
    with an IndexError. Check 6 must defer to check 5 rather than reading
    `splitlines()[0]` on an empty list (review pass-1 finding)."""
    plugin_root, repo_root, _ = _build_passing_fixture(tmp_path)
    (plugin_root / "VERSION").write_text("", encoding="utf-8")
    failures = v.verify(plugin_root, repo_root)
    # Should not raise; check 5 reports the failure; check 6 stays silent.
    check5 = [f for f in failures if f.check_id == 5]
    check6 = [f for f in failures if f.check_id == 6]
    assert len(check5) >= 1
    assert check6 == []


def test_check6_prerelease_does_not_satisfy_final_version(tmp_path: Path):
    """`# v1.4.0-rc1` MUST NOT satisfy a VERSION of `1.4.0`. The H1 anchor must
    require end-of-line or whitespace, not a word boundary — a `\\b` regex
    falsely matches the prerelease and lets a release ship without a final
    release-notes entry (review pass-2 finding)."""
    plugin_root, repo_root, head = _build_passing_fixture(tmp_path)
    (plugin_root / "RELEASES.md").write_text(
        f"# v1.4.0-rc1\n\nrelease-candidate notes\nrequirements doc commit: {head}\n",
        encoding="utf-8",
    )
    failures = [f for f in v.verify(plugin_root, repo_root) if f.check_id == 6]
    assert len(failures) == 1


def test_check6_missing_releases_h1(tmp_path: Path):
    plugin_root, repo_root, _ = _build_passing_fixture(tmp_path)
    (plugin_root / "RELEASES.md").write_text(
        "# v0.0.1\n\nold notes\n", encoding="utf-8"
    )
    failures = [f for f in v.verify(plugin_root, repo_root) if f.check_id == 6]
    assert len(failures) == 1
    assert "v1.4.0" in failures[0].message


def test_check6_missing_releases_file(tmp_path: Path):
    plugin_root, repo_root, _ = _build_passing_fixture(tmp_path)
    (plugin_root / "RELEASES.md").unlink()
    failures = [f for f in v.verify(plugin_root, repo_root) if f.check_id == 6]
    assert len(failures) == 1


def test_check7_release_notes_missing_head_hash(tmp_path: Path):
    plugin_root, repo_root, head = _build_passing_fixture(tmp_path)
    # Replace HEAD ref with a different hex string of the same length
    fake = "0" * len(head)
    text = (plugin_root / "RELEASES.md").read_text(encoding="utf-8")
    (plugin_root / "RELEASES.md").write_text(
        text.replace(head, fake), encoding="utf-8"
    )
    failures = [f for f in v.verify(plugin_root, repo_root) if f.check_id == 7]
    assert len(failures) == 1


# ---------------------------------------------------------------------------
# Module-level constants: tests can re-import the canonical tables (DRY).
# ---------------------------------------------------------------------------


def test_pp6_sections_table_matches_adr_609():
    assert v.PP6_REQUIRED_SECTIONS == (
        "## STUBS.md",
        "## impact-map.md",
        "## risks/risk-assessment.md",
        "## boundaries.md",
        "## test/explore-NNN.md",
        "## reviews/build-checks.md",
        "## .gvm-track2-adopted",
    )


def test_pp5_headings_table_covers_five_skills():
    assert set(v.PP5_GUIDE_HEADINGS) == {
        "gvm-build",
        "gvm-test",
        "gvm-code-review",
        "gvm-requirements",
        "gvm-test-cases",
    }


def test_new_skills_table_covers_three_skills():
    assert set(v.NEW_SKILL_GUIDES) == {
        "gvm-impact-map",
        "gvm-walking-skeleton",
        "gvm-explore-test",
    }
