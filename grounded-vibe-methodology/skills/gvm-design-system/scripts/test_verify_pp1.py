"""Tests for `_verify_pp1.py` — PP-1 SKILL.md keyword check (TC-PP-1-01).

Per pipeline-propagation ADR-601, every affected SKILL.md must contain a
hard-coded list of protocol keywords. The verifier greps each file and
reports any missing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import _verify_pp1 as v


def _build_skill(skills_dir: Path, name: str, body: str) -> Path:
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(body, encoding="utf-8")
    return skill_md


def _all_pass_fixture(tmp_path: Path) -> Path:
    """Build a skills/ tree where every SKILL.md contains every required keyword."""
    skills = tmp_path / "skills"
    for skill, keywords in v.SKILL_KEYWORDS.items():
        body = "# " + skill + "\n\n" + "\n".join(keywords) + "\n"
        _build_skill(skills, skill, body)
    return skills


def test_keyword_table_covers_five_skills():
    # Per ADR-601 the affected SKILL.md count is exactly 5.
    assert set(v.SKILL_KEYWORDS) == {
        "gvm-build",
        "gvm-test",
        "gvm-code-review",
        "gvm-requirements",
        "gvm-test-cases",
    }


def test_keyword_table_matches_adr_601():
    # Hard-coded per ADR-601 table — drift in either direction is a regression.
    assert v.SKILL_KEYWORDS["gvm-build"] == ("STUBS.md", "HS-1", "retroactive")
    assert v.SKILL_KEYWORDS["gvm-test"] == (
        "Ship-ready",
        "Demo-ready",
        "Not shippable",
        "VV-2",
        "VV-3",
        "VV-4",
    )
    assert v.SKILL_KEYWORDS["gvm-code-review"] == ("Panel E", "Stub Detection", "SD-1")
    assert v.SKILL_KEYWORDS["gvm-requirements"] == (
        "IM-4",
        "RA-3",
        "impact-deliverable",
    )
    assert v.SKILL_KEYWORDS["gvm-test-cases"] == (
        "EBT-1",
        "[EXAMPLE]",
        "[CONTRACT]",
        "[COLLABORATION]",
    )


def test_verify_returns_empty_when_all_keywords_present(tmp_path: Path):
    skills = _all_pass_fixture(tmp_path)
    assert v.verify(skills) == []


def test_verify_reports_missing_keyword(tmp_path: Path):
    skills = _all_pass_fixture(tmp_path)
    # Knock one keyword out of gvm-build/SKILL.md
    skill_md = skills / "gvm-build" / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8").replace("HS-1", "")
    skill_md.write_text(text, encoding="utf-8")

    failures = v.verify(skills)
    assert len(failures) == 1
    f = failures[0]
    assert f.skill == "gvm-build"
    assert f.keyword == "HS-1"
    assert "HS-1" in str(f)
    assert "gvm-build" in str(f)


def test_verify_reports_missing_skill_file(tmp_path: Path):
    skills = _all_pass_fixture(tmp_path)
    # Delete one SKILL.md outright
    (skills / "gvm-test" / "SKILL.md").unlink()

    failures = v.verify(skills)
    assert any(
        f.skill == "gvm-test" and f.keyword is None for f in failures
    ), "missing-file case should produce a failure with keyword=None"


def test_verify_reports_every_missing_keyword(tmp_path: Path):
    """A SKILL.md missing N keywords produces N failures — not one summary."""
    skills = _all_pass_fixture(tmp_path)
    # Wipe gvm-code-review's keywords
    (skills / "gvm-code-review" / "SKILL.md").write_text(
        "# gvm-code-review\n", encoding="utf-8"
    )
    failures = [f for f in v.verify(skills) if f.skill == "gvm-code-review"]
    expected = set(v.SKILL_KEYWORDS["gvm-code-review"])
    assert {f.keyword for f in failures} == expected


def test_main_returns_zero_on_pass(tmp_path: Path, capsys: pytest.CaptureFixture):
    skills = _all_pass_fixture(tmp_path)
    rc = v.main(["prog", "--skills-dir", str(skills)])
    assert rc == 0


def test_main_returns_nonzero_on_failure(tmp_path: Path, capsys: pytest.CaptureFixture):
    skills = _all_pass_fixture(tmp_path)
    (skills / "gvm-build" / "SKILL.md").write_text("# bare\n", encoding="utf-8")
    rc = v.main(["prog", "--skills-dir", str(skills)])
    assert rc == 1
    err = capsys.readouterr().err
    # All three keywords for gvm-build should appear in the error report
    assert "STUBS.md" in err
    assert "HS-1" in err
    assert "retroactive" in err
