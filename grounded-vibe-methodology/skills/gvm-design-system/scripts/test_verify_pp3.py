"""Tests for `_verify_pp3.sh` (pipeline-propagation ADR-603, TC-PP-3-01..02)."""

from __future__ import annotations

import subprocess
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parent / "_verify_pp3.sh"
PROJECT_ROOT = Path(__file__).resolve().parents[4]
LIVE_PLUGIN_TREE = PROJECT_ROOT / "grounded-vibe-methodology" / "skills"


def _run(scan_dir: Path, *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), str(scan_dir)],
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
    )


def test_clean_tree_returns_zero(tmp_path: Path):
    (tmp_path / "ok.md").write_text("Ship-ready means the build is verified.\n")
    result = _run(tmp_path, cwd=tmp_path)
    assert result.returncode == 0, result.stderr


def test_pass_with_gaps_literal_fails(tmp_path: Path):
    (tmp_path / "bad.md").write_text("verdict: Pass with gaps\n")
    result = _run(tmp_path, cwd=tmp_path)
    assert result.returncode == 1
    assert (
        "Pass with gaps" in result.stderr or "pass with gaps" in result.stderr.lower()
    )


def test_pass_dash_with_dash_gaps_variant_fails(tmp_path: Path):
    (tmp_path / "bad.md").write_text("Pass-with-gaps\n")
    result = _run(tmp_path, cwd=tmp_path)
    assert result.returncode == 1


def test_passing_with_caveats_variant_fails(tmp_path: Path):
    (tmp_path / "bad.md").write_text("the run was passing with caveats\n")
    result = _run(tmp_path, cwd=tmp_path)
    assert result.returncode == 1


def test_passing_with_gaps_variant_fails(tmp_path: Path):
    (tmp_path / "bad.md").write_text("passing with gaps overall\n")
    result = _run(tmp_path, cwd=tmp_path)
    assert result.returncode == 1


def test_case_insensitive_lowercase_match_fails(tmp_path: Path):
    (tmp_path / "bad.md").write_text("pass with gaps\n")
    result = _run(tmp_path, cwd=tmp_path)
    assert result.returncode == 1


def test_allowlist_drops_matched_path(tmp_path: Path):
    (tmp_path / "legitimate.md").write_text("v0 verdict: Pass with gaps maps to None\n")
    (tmp_path / ".pp3-allowlist").write_text("legitimate.md\n")
    result = _run(tmp_path, cwd=tmp_path)
    assert result.returncode == 0, result.stderr


def test_allowlist_comments_ignored(tmp_path: Path):
    (tmp_path / "bad.md").write_text("Pass with gaps\n")
    (tmp_path / ".pp3-allowlist").write_text(
        "# this comment should not match anything\n"
    )
    result = _run(tmp_path, cwd=tmp_path)
    assert result.returncode == 1


def test_allowlist_blank_lines_ignored(tmp_path: Path):
    (tmp_path / "bad.md").write_text("Pass with gaps\n")
    (tmp_path / ".pp3-allowlist").write_text("\n\n\n")
    result = _run(tmp_path, cwd=tmp_path)
    assert result.returncode == 1


def test_failure_output_to_stderr_includes_path_line(tmp_path: Path):
    target = tmp_path / "report.md"
    target.write_text("Pass with gaps\n")
    result = _run(tmp_path, cwd=tmp_path)
    assert result.returncode == 1
    assert "report.md" in result.stderr


def test_real_plugin_tree_passes():
    """End-to-end gate: project tree + project .pp3-allowlist produces zero hits."""
    result = _run(LIVE_PLUGIN_TREE, cwd=PROJECT_ROOT)
    assert result.returncode == 0, (
        f"PP-3 grep found surviving variants in the project tree:\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
