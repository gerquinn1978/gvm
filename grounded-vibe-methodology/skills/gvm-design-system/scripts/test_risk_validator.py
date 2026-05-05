"""Tests for P10-C06 — `_risk_validator.full_check` (discovery ADR-306, ADR-307, ADR-308).

Pin the contract that `risks/risk-assessment.md` must satisfy:
- RA-1: file exists; four sections in order (Value, Usability, Feasibility, Viability)
- RA-2: ≥ 1 paragraph + ≥ 50 words per non-accepted-unknown section
- RA-3: no bare `unknown`; `*accepted-unknown*` is structurally rigid
        (rationale + validator + review-date with `>= today` enforcement)
- RA-4: ≥ 1 `questioner:` token per prose section (case-insensitive name,
        trailing colon required); `Validator:` synonymy applies only inside
        accepted-unknown sections.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _risk_validator import (  # noqa: E402
    RiskAssessment,
    RiskValidationError,
    full_check,
)

TODAY = date(2026, 4, 25)
FUTURE = "2026-12-31"
PAST = "2024-01-01"

WORDS_50 = " ".join(["word"] * 60) + "."
QUESTIONER_TAIL = " questioner: self (pending external review by Dr X)"


def _section_prose(words: int = 60, with_questioner: bool = True) -> str:
    body = " ".join(["risk"] * words) + "."
    if with_questioner:
        body += QUESTIONER_TAIL
    return body


def _write_risk_file(
    tmp_path: Path,
    sections: dict[str, str] | None = None,
    schema_version: int = 1,
    section_order: list[str] | None = None,
) -> Path:
    sections = (
        sections
        if sections is not None
        else {
            "Value Risk": _section_prose(),
            "Usability Risk": _section_prose(),
            "Feasibility Risk": _section_prose(),
            "Viability Risk": _section_prose(),
        }
    )
    order = section_order if section_order is not None else list(sections.keys())
    parts = [
        "---",
        f"schema_version: {schema_version}",
        "---",
        "# Risk Assessment",
        "",
    ]
    for name in order:
        parts.append(f"## {name}")
        parts.append(sections[name])
        parts.append("")
    p = tmp_path / "risk-assessment.md"
    p.write_text("\n".join(parts), encoding="utf-8")
    return p


# --- RA-1 ---


def test_tc_ra_1_01_four_sections_in_order_pass(tmp_path: Path):
    p = _write_risk_file(tmp_path)
    ra, errors = full_check(p, today=TODAY)
    assert errors == []
    assert isinstance(ra, RiskAssessment)
    assert ra.value and ra.usability and ra.feasibility and ra.viability


def test_tc_ra_1_02_missing_file_blocks(tmp_path: Path):
    missing = tmp_path / "risk-assessment.md"
    ra, errors = full_check(missing, today=TODAY)
    assert ra is None
    assert len(errors) == 1
    assert errors[0].code == "RA-1"


def test_sections_out_of_order_blocks(tmp_path: Path):
    p = _write_risk_file(
        tmp_path,
        section_order=[
            "Usability Risk",
            "Value Risk",
            "Feasibility Risk",
            "Viability Risk",
        ],
    )
    ra, errors = full_check(p, today=TODAY)
    assert any(e.code == "RA-1" for e in errors)


def test_missing_section_blocks(tmp_path: Path):
    sections = {
        "Value Risk": _section_prose(),
        "Usability Risk": _section_prose(),
        "Feasibility Risk": _section_prose(),
    }
    p = _write_risk_file(
        tmp_path, sections=sections, section_order=list(sections.keys())
    )
    ra, errors = full_check(p, today=TODAY)
    assert any(e.code == "RA-1" for e in errors)


# --- RA-2 ---


def test_tc_ra_2_01_well_formed_passes(tmp_path: Path):
    p = _write_risk_file(tmp_path)
    _, errors = full_check(p, today=TODAY)
    assert [e for e in errors if e.code == "RA-2"] == []


def test_tc_ra_2_02_empty_section_blocks(tmp_path: Path):
    sections = {
        "Value Risk": _section_prose(),
        "Usability Risk": _section_prose(),
        "Feasibility Risk": "",
        "Viability Risk": _section_prose(),
    }
    p = _write_risk_file(tmp_path, sections=sections)
    _, errors = full_check(p, today=TODAY)
    assert any(e.code == "RA-2" and e.section == "Feasibility Risk" for e in errors)


def test_tc_ra_2_03_short_paragraph_blocks(tmp_path: Path):
    """Spec TC-RA-2-03: an 8-word section fails RA-2 with `got: 8`. The
    spec example carries no questioner tail, so the test mirrors that
    shape exactly."""
    sections = {
        "Value Risk": "Risk is low; users will likely tolerate it.",
        "Usability Risk": _section_prose(),
        "Feasibility Risk": _section_prose(),
        "Viability Risk": _section_prose(),
    }
    p = _write_risk_file(tmp_path, sections=sections)
    _, errors = full_check(p, today=TODAY)
    matches = [e for e in errors if e.code == "RA-2" and e.section == "Value Risk"]
    assert matches, "expected RA-2 below-floor error for Value Risk"
    assert "got: 8" in matches[0].message


# --- RA-3 ---


def test_tc_ra_3_01_bare_unknown_blocks(tmp_path: Path):
    sections = {
        "Value Risk": "unknown",
        "Usability Risk": _section_prose(),
        "Feasibility Risk": _section_prose(),
        "Viability Risk": _section_prose(),
    }
    p = _write_risk_file(tmp_path, sections=sections)
    _, errors = full_check(p, today=TODAY)
    assert any(e.code == "RA-3" and e.section == "Value Risk" for e in errors)


def test_tc_ra_3_02_accepted_unknown_well_formed_passes(tmp_path: Path):
    accepted = (
        "*accepted-unknown*\n"
        "Rationale: Subscription pricing not validated; defer until ten paying users.\n"
        "Validator: External advisor (TBD)\n"
        f"Review date: {FUTURE}"
    )
    sections = {
        "Value Risk": _section_prose(),
        "Usability Risk": _section_prose(),
        "Feasibility Risk": _section_prose(),
        "Viability Risk": accepted,
    }
    p = _write_risk_file(tmp_path, sections=sections)
    _, errors = full_check(p, today=TODAY)
    assert [e for e in errors if e.section == "Viability Risk"] == []


def test_tc_ra_3_04_past_review_date_blocks(tmp_path: Path):
    accepted = (
        "*accepted-unknown*\n"
        "Rationale: Pricing not validated.\n"
        "Validator: External advisor.\n"
        f"Review date: {PAST}"
    )
    sections = {
        "Value Risk": _section_prose(),
        "Usability Risk": _section_prose(),
        "Feasibility Risk": _section_prose(),
        "Viability Risk": accepted,
    }
    p = _write_risk_file(tmp_path, sections=sections)
    _, errors = full_check(p, today=TODAY)
    matches = [e for e in errors if e.code == "RA-3" and e.section == "Viability Risk"]
    assert matches, "expected RA-3 stale acceptance"
    assert "stale" in matches[0].message.lower() or PAST in matches[0].message


def test_tc_ra_3_05_today_review_date_passes(tmp_path: Path):
    accepted = (
        "*accepted-unknown*\n"
        "Rationale: Will revisit at next review.\n"
        "Validator: Dr X.\n"
        f"Review date: {TODAY.isoformat()}"
    )
    sections = {
        "Value Risk": _section_prose(),
        "Usability Risk": _section_prose(),
        "Feasibility Risk": _section_prose(),
        "Viability Risk": accepted,
    }
    p = _write_risk_file(tmp_path, sections=sections)
    _, errors = full_check(p, today=TODAY)
    assert [e for e in errors if e.section == "Viability Risk"] == []


def test_accepted_unknown_missing_rationale_blocks(tmp_path: Path):
    accepted = (
        f"*accepted-unknown*\nValidator: External advisor.\nReview date: {FUTURE}"
    )
    sections = {
        "Value Risk": _section_prose(),
        "Usability Risk": _section_prose(),
        "Feasibility Risk": _section_prose(),
        "Viability Risk": accepted,
    }
    p = _write_risk_file(tmp_path, sections=sections)
    _, errors = full_check(p, today=TODAY)
    assert any(
        e.code == "RA-3" and e.section == "Viability Risk" and "Rationale" in e.message
        for e in errors
    )


def test_accepted_unknown_malformed_date_blocks(tmp_path: Path):
    accepted = (
        "*accepted-unknown*\n"
        "Rationale: Pricing not validated.\n"
        "Validator: Dr X.\n"
        "Review date: 2026/12/31"  # wrong format (slashes)
    )
    sections = {
        "Value Risk": _section_prose(),
        "Usability Risk": _section_prose(),
        "Feasibility Risk": _section_prose(),
        "Viability Risk": accepted,
    }
    p = _write_risk_file(tmp_path, sections=sections)
    _, errors = full_check(p, today=TODAY)
    assert any(e.code == "RA-3" and e.section == "Viability Risk" for e in errors)


# --- RA-4 ---


def test_tc_ra_4_01_questioner_tail_passes(tmp_path: Path):
    p = _write_risk_file(tmp_path)
    _, errors = full_check(p, today=TODAY)
    assert [e for e in errors if e.code == "RA-4"] == []


def test_tc_ra_4_02_no_questioner_blocks(tmp_path: Path):
    sections = {
        "Value Risk": _section_prose(with_questioner=False),
        "Usability Risk": _section_prose(),
        "Feasibility Risk": _section_prose(),
        "Viability Risk": _section_prose(),
    }
    p = _write_risk_file(tmp_path, sections=sections)
    _, errors = full_check(p, today=TODAY)
    assert any(e.code == "RA-4" and e.section == "Value Risk" for e in errors)


def test_tc_ra_4_03_validator_synonym_in_accepted_unknown_passes(tmp_path: Path):
    accepted = (
        "*accepted-unknown*\n"
        "Rationale: Pricing not validated.\n"
        "Validator: external advisor\n"
        f"Review date: {FUTURE}"
    )
    sections = {
        "Value Risk": _section_prose(),
        "Usability Risk": _section_prose(),
        "Feasibility Risk": _section_prose(),
        "Viability Risk": accepted,
    }
    p = _write_risk_file(tmp_path, sections=sections)
    _, errors = full_check(p, today=TODAY)
    assert [e for e in errors if e.section == "Viability Risk"] == []


@pytest.mark.parametrize(
    "tail,expect_pass",
    [
        (" questioners: self", False),  # plural → fails
        (" questioner self", False),  # missing colon → fails
        (" Questioner: self (capitalised)", True),  # case-insensitive name → passes
    ],
)
def test_tc_ra_4_04_questioner_near_misses(
    tmp_path: Path, tail: str, expect_pass: bool
):
    body = " ".join(["risk"] * 60) + "." + tail
    sections = {
        "Value Risk": body,
        "Usability Risk": _section_prose(),
        "Feasibility Risk": _section_prose(),
        "Viability Risk": _section_prose(),
    }
    p = _write_risk_file(tmp_path, sections=sections)
    _, errors = full_check(p, today=TODAY)
    ra4 = [e for e in errors if e.code == "RA-4" and e.section == "Value Risk"]
    if expect_pass:
        assert ra4 == [], f"tail={tail!r} should pass"
    else:
        assert ra4, f"tail={tail!r} should fail RA-4"


# --- Schema / sentinel / never raises ---


def test_missing_frontmatter_returns_sentinel(tmp_path: Path):
    p = tmp_path / "risk-assessment.md"
    p.write_text("# no frontmatter\n## Value Risk\n...\n", encoding="utf-8")
    ra, errors = full_check(p, today=TODAY)
    assert ra is None
    assert len(errors) == 1
    assert errors[0].code == "RA-1"


def test_full_check_never_raises_on_binary(tmp_path: Path):
    p = tmp_path / "risk-assessment.md"
    p.write_bytes(b"\x00\x01\x02\xff\xfe garbage")
    # Should not raise; should return a sentinel.
    ra, errors = full_check(p, today=TODAY)
    assert ra is None
    assert errors


def test_risk_assessment_is_frozen():
    ra = RiskAssessment(value="a", usability="b", feasibility="c", viability="d")
    # FrozenInstanceError is a subclass of AttributeError; tightening the catch
    # to AttributeError catches the regression of `frozen=True` being removed
    # without over-specifying the exception class.
    with pytest.raises(AttributeError):
        ra.value = "x"  # type: ignore[misc]


def test_risk_validation_error_is_frozen():
    err = RiskValidationError(code="RA-1", section="-", message="x")
    with pytest.raises(AttributeError):
        err.code = "RA-2"  # type: ignore[misc]


def test_extra_section_header_does_not_fold_into_preceding_section(tmp_path: Path):
    """Critical fix from independent review: a non-required `## Notes`
    section between two required sections must not be slurped into the
    preceding section's body. Otherwise its words inflate RA-2 word count
    and a `questioner:` token in `## Notes` would falsely satisfy RA-4
    for the preceding section."""
    body = (
        "---\nschema_version: 1\n---\n"
        "# Risk Assessment\n\n"
        "## Value Risk\n"
        "Risk is low; users will likely tolerate it.\n"  # 8 words — too short
        "\n"
        "## Notes\n" + " ".join(["padding"] * 60) + ". questioner: not real\n\n"
        # 60 long words + a questioner token. Without the fix this body folds
        # into Value Risk and would push it over 50 words AND match RA-4.
        "## Usability Risk\n" + _section_prose() + "\n\n"
        "## Feasibility Risk\n" + _section_prose() + "\n\n"
        "## Viability Risk\n" + _section_prose() + "\n"
    )
    p = tmp_path / "risk-assessment.md"
    p.write_text(body, encoding="utf-8")
    _, errors = full_check(p, today=TODAY)
    # Value Risk must still be flagged as below the 50-word floor.
    assert any(
        e.code == "RA-2" and e.section == "Value Risk" and "got: 8" in e.message
        for e in errors
    )


def test_unknown_with_trailing_period_is_not_ra3(tmp_path: Path):
    """Document the exact-match boundary: `unknown.` (with punctuation) is
    NOT treated as bare-unknown. It hits the RA-2 floor instead. If a future
    practitioner reports this as confusing, widen `_first_non_empty` matching
    — but right now the strict match is intentional and pinned here."""
    sections = {
        "Value Risk": "unknown.",
        "Usability Risk": _section_prose(),
        "Feasibility Risk": _section_prose(),
        "Viability Risk": _section_prose(),
    }
    p = _write_risk_file(tmp_path, sections=sections)
    _, errors = full_check(p, today=TODAY)
    # Not RA-3.
    assert not any(e.code == "RA-3" and e.section == "Value Risk" for e in errors)
    # Hits RA-2 instead.
    assert any(e.code == "RA-2" and e.section == "Value Risk" for e in errors)


def test_header_with_extra_text_does_not_match(tmp_path: Path):
    """`## Value Risk extra text` is NOT recognised as Value Risk — the
    section name must be exact. Asserting this pins the regex from
    accidentally relaxing in future."""
    body = (
        "---\nschema_version: 1\n---\n"
        "# Risk Assessment\n\n"
        "## Value Risk extra text\n"  # not a recognised header
        + _section_prose()
        + "\n\n"
        "## Usability Risk\n" + _section_prose() + "\n\n"
        "## Feasibility Risk\n" + _section_prose() + "\n\n"
        "## Viability Risk\n" + _section_prose() + "\n"
    )
    p = tmp_path / "risk-assessment.md"
    p.write_text(body, encoding="utf-8")
    ra, errors = full_check(p, today=TODAY)
    # RA-1 missing-section error for Value Risk.
    assert ra is None
    assert any(e.code == "RA-1" and e.section == "Value Risk" for e in errors), (
        f"expected RA-1 missing Value Risk, got {errors}"
    )
