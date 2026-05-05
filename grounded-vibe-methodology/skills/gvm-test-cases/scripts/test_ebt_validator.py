"""Tests for `_ebt_validator.py` — EBT-1 audit validator (ADR-501).

Test plan covers 10 cases per the P12-C01 build prompt:
  1. Two MUST reqs; one with EBT, one without → coverage_gaps for the one without.
  2. MUST req with no test → missing="any-test".
  3. MUST req with Input+positive but no negative → missing="negative-assertion".
  4. SHOULD req with no test → NOT in coverage_gaps (MUST-only mandate).
  5. Empty requirements file → total_requirements==0, coverage_gaps==[].
  6. Empty test-cases file → every MUST req gets missing="any-test".
  7. Path|str accepted at entry signature.
  8. Frozen dataclasses (FrozenInstanceError on mutation attempt).
  9. Heuristic edge: lowercase "should contain"+"should not contain"+"Input:" → example-based.
  10. Hypothesis property: example-based iff all three flags (input, pos, neg) are True.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from _ebt_validator import AuditReport, CoverageGap, LintViolation, audit

# ---------------------------------------------------------------------------
# Helpers — construct fixture files
# ---------------------------------------------------------------------------

_REQ_MUST_RE1 = "**RE-1 (MUST):** The system shall return a result.\n"
_REQ_MUST_RE2 = "**RE-2 (MUST):** The system shall validate input.\n"
_REQ_SHOULD_RE3 = "**RE-3 (SHOULD):** The system should log events.\n"

_TC_EBT_RE1 = (
    "## TC-1\n"
    "[Requirement: RE-1]\n"
    "Input: foo=bar\n"
    "Output MUST contain 'result'\n"
    "Output MUST NOT contain 'error'\n"
)

_TC_SHAPE_ONLY_RE2 = (
    "## TC-2\n"
    "[Requirement: RE-2]\n"
    "Given a request with foo=bar\n"
    "Then something happens\n"
)


def _write(tmp_path: Path, filename: str, content: str) -> Path:
    p = tmp_path / filename
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# TC-1: Two MUST reqs; RE-1 fully EBT-covered, RE-2 only shape-test
# ---------------------------------------------------------------------------


def test_tc1_two_must_reqs_one_covered_one_not(tmp_path: Path) -> None:
    reqs = _write(tmp_path, "requirements.md", _REQ_MUST_RE1 + _REQ_MUST_RE2)
    tests = _write(tmp_path, "test-cases.md", _TC_EBT_RE1 + "\n" + _TC_SHAPE_ONLY_RE2)

    report = audit(tests, reqs)

    assert report.total_requirements == 2
    assert report.total_tests == 2
    assert len(report.coverage_gaps) == 1
    gap = report.coverage_gaps[0]
    assert gap.requirement_id == "RE-2"
    assert gap.priority == "MUST"
    assert gap.missing == "example-test"


# ---------------------------------------------------------------------------
# TC-2: MUST req with no test at all → missing="any-test"
# ---------------------------------------------------------------------------


def test_tc2_must_req_no_test(tmp_path: Path) -> None:
    reqs = _write(tmp_path, "requirements.md", _REQ_MUST_RE1)
    tests = _write(tmp_path, "test-cases.md", "")

    report = audit(tests, reqs)

    assert len(report.coverage_gaps) == 1
    assert report.coverage_gaps[0].requirement_id == "RE-1"
    assert report.coverage_gaps[0].missing == "any-test"


# ---------------------------------------------------------------------------
# TC-3: MUST req with Input + positive but missing negative → missing="negative-assertion"
# ---------------------------------------------------------------------------


def test_tc3_missing_negative_assertion(tmp_path: Path) -> None:
    tc_no_neg = (
        "## TC-3\n[Requirement: RE-1]\nInput: foo=bar\nOutput MUST contain 'result'\n"
    )
    reqs = _write(tmp_path, "requirements.md", _REQ_MUST_RE1)
    tests = _write(tmp_path, "test-cases.md", tc_no_neg)

    report = audit(tests, reqs)

    assert len(report.coverage_gaps) == 1
    gap = report.coverage_gaps[0]
    assert gap.requirement_id == "RE-1"
    assert gap.missing == "negative-assertion"


# ---------------------------------------------------------------------------
# TC-4: SHOULD req with no test — must NOT appear in coverage_gaps
# ---------------------------------------------------------------------------


def test_tc4_should_req_excluded(tmp_path: Path) -> None:
    reqs = _write(tmp_path, "requirements.md", _REQ_SHOULD_RE3)
    tests = _write(tmp_path, "test-cases.md", "")

    report = audit(tests, reqs)

    assert report.coverage_gaps == ()
    assert report.total_requirements == 1


# ---------------------------------------------------------------------------
# TC-5: Empty requirements file
# ---------------------------------------------------------------------------


def test_tc5_empty_requirements(tmp_path: Path) -> None:
    reqs = _write(tmp_path, "requirements.md", "")
    tests = _write(tmp_path, "test-cases.md", "")

    report = audit(tests, reqs)

    assert report.total_requirements == 0
    assert report.total_tests == 0
    assert report.coverage_gaps == ()


# ---------------------------------------------------------------------------
# TC-6: Empty test-cases file — every MUST req gets missing="any-test"
# ---------------------------------------------------------------------------


def test_tc6_empty_tests_all_must_gapped(tmp_path: Path) -> None:
    reqs = _write(
        tmp_path, "requirements.md", _REQ_MUST_RE1 + _REQ_MUST_RE2 + _REQ_SHOULD_RE3
    )
    tests = _write(tmp_path, "test-cases.md", "")

    report = audit(tests, reqs)

    must_gaps = [g for g in report.coverage_gaps if g.missing == "any-test"]
    assert len(must_gaps) == 2
    assert {g.requirement_id for g in must_gaps} == {"RE-1", "RE-2"}
    # SHOULD req must not appear
    assert all(g.requirement_id != "RE-3" for g in report.coverage_gaps)


# ---------------------------------------------------------------------------
# TC-7: Path | str accepted at entry signature
# ---------------------------------------------------------------------------


def test_tc7_accepts_str_paths(tmp_path: Path) -> None:
    reqs = _write(tmp_path, "requirements.md", _REQ_MUST_RE1)
    tests = _write(tmp_path, "test-cases.md", _TC_EBT_RE1)

    # Pass as str rather than Path
    report = audit(str(tests), str(reqs))

    assert isinstance(report, AuditReport)
    assert report.coverage_gaps == ()


# ---------------------------------------------------------------------------
# TC-8: Frozen dataclasses raise FrozenInstanceError on mutation
# ---------------------------------------------------------------------------


def test_tc8_frozen_dataclasses() -> None:
    gap = CoverageGap(
        requirement_id="RE-1",
        priority="MUST",
        missing="example-test",
        detail="no EBT",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        gap.requirement_id = "RE-2"  # type: ignore[misc]

    report = AuditReport(
        total_requirements=0,
        total_tests=0,
        coverage_gaps=(),
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        report.total_requirements = 1  # type: ignore[misc]

    lint = LintViolation(
        test_id="TC-1",
        file_line="test-cases.md:10",
        kind="rainsberger",
        detail="too many assertions",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        lint.test_id = "TC-2"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TC-9: Heuristic edge — lowercase "should contain" + "should not contain"
# ---------------------------------------------------------------------------


def test_tc9_lowercase_variants_count_as_ebt(tmp_path: Path) -> None:
    tc_lowercase = (
        "## TC-9\n"
        "[Requirement: RE-1]\n"
        "Input: widget_id=42\n"
        "Response should contain 'widget'\n"
        "Response should not contain 'error'\n"
    )
    reqs = _write(tmp_path, "requirements.md", _REQ_MUST_RE1)
    tests = _write(tmp_path, "test-cases.md", tc_lowercase)

    report = audit(tests, reqs)

    assert report.coverage_gaps == (), (
        "Lowercase 'should contain'/'should not contain' must satisfy EBT shape"
    )


# ---------------------------------------------------------------------------
# TC-10: Hypothesis property — example-based iff all three flags are True
# ---------------------------------------------------------------------------


def _build_block(req_id: str, has_input: bool, has_pos: bool, has_neg: bool) -> str:
    lines = [f"## TC-prop\n[Requirement: {req_id}]\n"]
    if has_input:
        lines.append("Input: x=1\n")
    if has_pos:
        lines.append("Output MUST contain 'ok'\n")
    if has_neg:
        lines.append("Output MUST NOT contain 'fail'\n")
    return "".join(lines)


@given(
    has_input=st.booleans(),
    has_pos=st.booleans(),
    has_neg=st.booleans(),
)
@settings(max_examples=80)
def test_tc10_hypothesis_ebt_iff_all_three(
    has_input: bool,
    has_pos: bool,
    has_neg: bool,
) -> None:
    import tempfile

    req_id = "RE-1"
    block = _build_block(req_id, has_input, has_pos, has_neg)
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        reqs = _write(td_path, "requirements.md", f"**{req_id} (MUST):** test req\n")
        tests = _write(td_path, "test-cases.md", block)

        report = audit(tests, reqs)

    all_three = has_input and has_pos and has_neg
    if all_three:
        assert report.coverage_gaps == (), (
            f"All three flags set but got gap: {report.coverage_gaps}"
        )
    else:
        assert len(report.coverage_gaps) == 1, (
            f"Not all three flags but no gap: has_input={has_input}, "
            f"has_pos={has_pos}, has_neg={has_neg}"
        )
