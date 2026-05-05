"""Tests for _refresh_css.py developer tool (P6-C02).

TDD: these tests were written BEFORE _refresh_css.py existed. They should
initially fail with FileNotFoundError, then pass once the script is written.

All tests use tmp_path and GVM_TUFTE_HTML_REFERENCE env-var override so no
file outside the worktree is required.
"""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCRIPT_PATH = Path(__file__).parents[2] / "scripts" / "_refresh_css.py"

SAMPLE_CSS = """\
body {
    font-family: et-book, Georgia, serif;
    background-color: #fffff8;
    color: #111;
}

.sidenote {
    float: right;
    clear: right;
    width: 18vw;
    font-size: 0.8rem;
}
"""

SAMPLE_MD_TEMPLATE = """\
# Tufte HTML Reference

Some introductory prose.

```css
{css}
```

More prose after the block.
"""


def make_fixture_md(tmp_path: Path, css: str = SAMPLE_CSS) -> Path:
    """Write a synthetic tufte-html-reference.md with a css block."""
    md_file = tmp_path / "tufte-html-reference.md"
    md_file.write_text(SAMPLE_MD_TEMPLATE.format(css=css), encoding="utf-8")
    return md_file


def run_refresh(
    fixture_md: Path,
    output_dir: Path,
    *,
    extra_env: dict | None = None,
) -> subprocess.CompletedProcess:
    """Run _refresh_css.py with the fixture env-var override."""
    env = {**os.environ, "GVM_TUFTE_HTML_REFERENCE": str(fixture_md)}
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        env=env,
        capture_output=True,
        text=True,
        cwd=str(output_dir),
    )


# ---------------------------------------------------------------------------
# 1. Script exists and is executable
# ---------------------------------------------------------------------------
def test_script_exists():
    assert SCRIPT_PATH.exists(), f"_refresh_css.py not found at {SCRIPT_PATH}"


def test_script_is_executable():
    mode = SCRIPT_PATH.stat().st_mode
    assert mode & stat.S_IXUSR, "_refresh_css.py is not user-executable"


# ---------------------------------------------------------------------------
# 2. Extracts CSS block and writes _css.html.j2 with provenance header
# ---------------------------------------------------------------------------
def test_extracts_css_and_writes_template(tmp_path):
    fixture_md = make_fixture_md(tmp_path)
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    result = run_refresh(fixture_md, tmp_path)
    assert result.returncode == 0, f"Script failed: {result.stderr}"

    output_file = templates_dir / "_css.html.j2"
    assert output_file.exists(), "_css.html.j2 was not created"

    content = output_file.read_text(encoding="utf-8")
    assert "<style>" in content
    assert "</style>" in content
    assert SAMPLE_CSS.strip() in content


# ---------------------------------------------------------------------------
# 3. Provenance comment is present and contains sha256
# ---------------------------------------------------------------------------
def test_provenance_comment_present(tmp_path):
    fixture_md = make_fixture_md(tmp_path)
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    result = run_refresh(fixture_md, tmp_path)
    assert result.returncode == 0, f"Script failed: {result.stderr}"

    content = (templates_dir / "_css.html.j2").read_text(encoding="utf-8")
    assert "<!-- Source:" in content
    assert "sha256:" in content
    assert "tufte-html-reference.md" in content


# ---------------------------------------------------------------------------
# 4. Provenance sha256 matches the fixture file content
# ---------------------------------------------------------------------------
def test_provenance_sha256_matches_file(tmp_path):
    fixture_md = make_fixture_md(tmp_path)
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    result = run_refresh(fixture_md, tmp_path)
    assert result.returncode == 0, f"Script failed: {result.stderr}"

    expected_sha = hashlib.sha256(fixture_md.read_bytes()).hexdigest()
    content = (templates_dir / "_css.html.j2").read_text(encoding="utf-8")
    assert expected_sha in content, (
        f"Expected sha256 {expected_sha!r} not found in provenance header"
    )


# ---------------------------------------------------------------------------
# 5. Malformed fixture (no css block) → non-zero exit with stderr diagnostic
# ---------------------------------------------------------------------------
def test_malformed_fixture_exits_nonzero(tmp_path):
    bad_md = tmp_path / "bad.md"
    bad_md.write_text("# No CSS block here\n\nJust plain text.\n", encoding="utf-8")
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    result = run_refresh(bad_md, tmp_path)
    assert result.returncode != 0, "Expected non-zero exit for malformed input"
    assert result.stderr.strip(), "Expected stderr diagnostic for malformed input"


# ---------------------------------------------------------------------------
# 6. GVM_TUFTE_HTML_REFERENCE env-var override is respected
# ---------------------------------------------------------------------------
def test_env_var_override_respected(tmp_path):
    """Demonstrate that a different path via env var is used."""
    css_a = "body { color: red; }\n"
    css_b = "body { color: blue; }\n"

    fixture_a = tmp_path / "ref_a.md"
    fixture_a.write_text(SAMPLE_MD_TEMPLATE.format(css=css_a), encoding="utf-8")
    fixture_b = tmp_path / "ref_b.md"
    fixture_b.write_text(SAMPLE_MD_TEMPLATE.format(css=css_b), encoding="utf-8")

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    # Run with fixture_a first
    result = run_refresh(fixture_a, tmp_path)
    assert result.returncode == 0
    content_a = (templates_dir / "_css.html.j2").read_text(encoding="utf-8")

    # Run with fixture_b, overriding
    result = run_refresh(fixture_b, tmp_path)
    assert result.returncode == 0
    content_b = (templates_dir / "_css.html.j2").read_text(encoding="utf-8")

    assert "red" in content_a
    assert "blue" in content_b
    assert content_a != content_b


# ---------------------------------------------------------------------------
# 7. Missing reference file → non-zero exit with stderr diagnostic
# ---------------------------------------------------------------------------
def test_missing_reference_file_exits_nonzero(tmp_path):
    missing = tmp_path / "nonexistent.md"
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    result = run_refresh(missing, tmp_path)
    assert result.returncode != 0
    assert result.stderr.strip()
