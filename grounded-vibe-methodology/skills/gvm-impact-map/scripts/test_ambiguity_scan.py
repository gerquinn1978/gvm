"""Tests for IM-3 Goal ambiguity scan (discovery ADR-303).

Covers TC-IM-3-01..04 and the project-extension merge semantics
(`.gvm-impact-map.allowlist` / `.gvm-impact-map.denylist`).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# `_validator` already wires `_impact_map_parser.Goal` onto sys.path.
from _ambiguity_scan import (  # noqa: E402
    load_denylist,
    scan_goal,
    tokenize,
)
from _impact_map_parser import Goal  # noqa: E402
from _validator import ValidationError, full_check  # noqa: E402

_DEFAULT = _HERE.parent / "references" / "ambiguity-indicators.md"


def _write_default(path: Path) -> None:
    path.write_text(
        "# header comment\nlaunch\nimprove\nenable\nsupport\n\n# trailing\n",
        encoding="utf-8",
    )


# ---- tokenize -----------------------------------------------------------


def test_tokenize_lowercases_and_splits_on_punctuation():
    assert tokenize("Launch the mobile-app, please!") == [
        "launch",
        "the",
        "mobile",
        "app",
        "please",
    ]


# ---- load_denylist ------------------------------------------------------


def test_load_denylist_default_only(tmp_path: Path):
    default = tmp_path / "amb.md"
    _write_default(default)
    out = load_denylist(default, project_root=None)
    assert out == frozenset({"launch", "improve", "enable", "support"})


def test_load_denylist_skips_comments_and_blanks(tmp_path: Path):
    default = tmp_path / "amb.md"
    default.write_text("# c1\n\nlaunch\n  \n# c2\nimprove\n", encoding="utf-8")
    assert load_denylist(default, project_root=None) == frozenset({"launch", "improve"})


def test_load_denylist_with_project_denylist_addition(tmp_path: Path):
    default = tmp_path / "amb.md"
    _write_default(default)
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / ".gvm-impact-map.denylist").write_text("# extra\nfoo\nbar\n")
    out = load_denylist(default, project_root=proj)
    assert {"foo", "bar"}.issubset(out)
    assert "launch" in out


def test_load_denylist_with_project_allowlist_subtraction(tmp_path: Path):
    default = tmp_path / "amb.md"
    _write_default(default)
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / ".gvm-impact-map.allowlist").write_text("support\n")
    out = load_denylist(default, project_root=proj)
    assert "support" not in out
    assert "launch" in out


def test_load_denylist_missing_project_files_not_an_error(tmp_path: Path):
    default = tmp_path / "amb.md"
    _write_default(default)
    out = load_denylist(default, project_root=tmp_path / "does-not-exist")
    assert out == frozenset({"launch", "improve", "enable", "support"})


def test_load_denylist_default_file_missing_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_denylist(tmp_path / "missing.md", project_root=None)


def test_load_denylist_is_case_insensitive(tmp_path: Path):
    default = tmp_path / "amb.md"
    default.write_text("LAUNCH\nImprove\n", encoding="utf-8")
    out = load_denylist(default, project_root=None)
    assert out == frozenset({"launch", "improve"})


# ---- scan_goal ----------------------------------------------------------


def _goal(statement: str, metric: str = "", target: str = "") -> Goal:
    return Goal(
        id="G-1",
        statement=statement,
        metric=metric,
        target=target,
        deadline="2026-12-31",
    )


_DEFAULT_DL = frozenset(
    {
        "launch",
        "improve",
        "enable",
        "support",
        "deploy",
        "build",
        "create",
        "add",
    }
)


def test_tc_im_3_01_measurable_goal_accepted():
    g = _goal(
        "increase weekly active users by 20% within 6 months",
        metric="WAU",
        target="20%",
    )
    assert scan_goal(g, _DEFAULT_DL) == []


def test_tc_im_3_02_aspirational_goal_rejected_naming_launch():
    g = _goal("launch the mobile app")
    errors = scan_goal(g, _DEFAULT_DL)
    assert len(errors) == 1
    assert errors[0].code == "IM-3"
    assert "launch" in errors[0].message
    assert "G-1" in errors[0].message


@pytest.mark.parametrize(
    "statement,word",
    [
        ("improve performance", "improve"),
        ("enable users", "enable"),
        ("support SSO", "support"),
    ],
)
def test_tc_im_3_03_each_indicator_word_caught(statement: str, word: str):
    errors = scan_goal(_goal(statement), _DEFAULT_DL)
    assert len(errors) == 1
    assert word in errors[0].message


@pytest.mark.parametrize(
    "statement,word",
    [
        ("deploy the API", "deploy"),
        ("build the dashboard", "build"),
        ("create user profiles", "create"),
        ("add reporting", "add"),
    ],
)
def test_tc_im_3_04_additional_verbs_caught(statement: str, word: str):
    errors = scan_goal(_goal(statement), _DEFAULT_DL)
    assert len(errors) == 1
    assert word in errors[0].message


def test_numeric_in_target_field_does_not_rescue_hit_in_statement():
    """ADR-303 strict reading: the numeric must be on the SAME LINE as the
    denylist hit. Combined text joins fields with newlines; a numeric in
    `target` is on a different line from a hit in `statement`, so the hit
    is NOT quantified."""
    g = _goal(
        "improve onboarding", metric="time-to-first-action", target="from 8m to 3m"
    )
    errors = scan_goal(g, _DEFAULT_DL)
    assert len(errors) == 1
    assert "improve" in errors[0].message


def test_numeric_same_line_as_match_passes_in_statement():
    g = _goal("improve onboarding from 8m to 3m")
    assert scan_goal(g, _DEFAULT_DL) == []


def test_multiple_denylist_hits_all_named():
    g = _goal("launch and deploy")
    errors = scan_goal(g, _DEFAULT_DL)
    msgs = " ".join(e.message for e in errors)
    assert "launch" in msgs and "deploy" in msgs


# ---- full_check integration --------------------------------------------


_HEADER = (
    "---\nschema_version: 1\n---\n# Impact Map\n\n"
    "## Goals\n"
    "| ID | Statement | Metric | Target | Deadline |\n"
    "|---|---|---|---|---|\n"
)


def _write_map(tmp_path: Path, goal_row: str) -> Path:
    body = (
        _HEADER
        + goal_row
        + "\n## Actors\n| ID | Goal-ID | Name | Description |\n|---|---|---|---|\n"
        + "| A-1 | G-1 | Buyer | The buyer |\n\n"
        + "## Impacts\n| ID | Actor-ID | Behavioural change | Direction |\n|---|---|---|---|\n"
        + "| I-1 | A-1 | Sees offers | up |\n\n"
        + "## Deliverables\n| ID | Impact-ID | Title | Type |\n|---|---|---|---|\n"
        + "| D-1 | I-1 | Offers list | feature |\n"
    )
    out = tmp_path / "impact-map.md"
    out.write_text(body, encoding="utf-8")
    return out


def test_full_check_clean_goal_passes(tmp_path: Path):
    path = _write_map(
        tmp_path,
        "| G-1 | increase WAU by 20% in 6 months | WAU | 20% | 2026-12-31 |\n",
    )
    impact_map, errors = full_check(path)
    assert errors == []
    assert impact_map is not None


def test_full_check_aspirational_goal_emits_im3(tmp_path: Path):
    path = _write_map(
        tmp_path,
        "| G-1 | launch the mobile app | downloads | many | 2026-12-31 |\n",
    )
    impact_map, errors = full_check(path)
    assert impact_map is None
    assert any(e.code == "IM-3" and "launch" in e.message for e in errors)


def test_full_check_runs_im2_then_im3(tmp_path: Path):
    """IM-2 errors are surfaced first, then IM-3. Use a file that fails both:
    an orphan Actor (IM-2) and an aspirational Goal (IM-3)."""
    body = (
        _HEADER
        + "| G-1 | launch the mobile app | downloads | many | 2026-12-31 |\n\n"
        + "## Actors\n| ID | Goal-ID | Name | Description |\n|---|---|---|---|\n"
        + "| A-1 | G-1 | Buyer | The buyer |\n"
        + "| A-2 | G-1 | Orphan | Has no Impacts |\n\n"
        + "## Impacts\n| ID | Actor-ID | Behavioural change | Direction |\n|---|---|---|---|\n"
        + "| I-1 | A-1 | Sees offers | up |\n\n"
        + "## Deliverables\n| ID | Impact-ID | Title | Type |\n|---|---|---|---|\n"
        + "| D-1 | I-1 | Offers list | feature |\n"
    )
    path = tmp_path / "impact-map.md"
    path.write_text(body, encoding="utf-8")
    _, errors = full_check(path)
    codes = [e.code for e in errors]
    assert "IM-2" in codes and "IM-3" in codes
    assert codes.index("IM-2") < codes.index("IM-3")


def test_validation_error_dataclass_shape():
    e = ValidationError(code="IM-3", message="x")
    assert e.code == "IM-3" and e.message == "x"


def test_live_default_denylist_loads_twenty_words():
    """End-to-end: the shipped references file parses to 20 verbs."""
    out = load_denylist(_DEFAULT, project_root=None)
    assert len(out) == 20
    assert {"launch", "improve", "enable", "support"}.issubset(out)
