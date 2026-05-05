"""Tests for `_retrofit` (P12-C06 — EBT-6 retrofit mode).

Test plan mirrors build/prompts/P12-C06.md §Test Plan.
"""

from __future__ import annotations

import dataclasses
import subprocess
import sys
from pathlib import Path

import pytest

from _retrofit import scan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(p: Path, text: str) -> Path:
    p.write_text(text, encoding="utf-8")
    return p


def _req_file(tmp_path: Path, body: str) -> Path:
    return _write(tmp_path / "requirements.md", body)


def _tc_file(tmp_path: Path, body: str) -> Path:
    return _write(tmp_path / "test-cases.md", body)


# A complete EBT example block for RE-1 (Input + MUST contain + MUST NOT contain).
_RE1_EBT_BLOCK = (
    "## TC-RE-1-01: covers RE-1 [EXAMPLE]\n"
    "Input: sample-input\n"
    "Then the output MUST contain: ok\n"
    "And the output MUST NOT contain: bad\n"
    "[Requirement: RE-1] [Priority: MUST]\n"
)


# ---------------------------------------------------------------------------
# Test 1 — basic two-requirement coverage
# ---------------------------------------------------------------------------


def test_one_must_covered_one_uncovered_yields_one_candidate(tmp_path: Path) -> None:
    req = _req_file(
        tmp_path,
        "**RE-1 (Must)** The system shall accept a valid request.\n"
        "**RE-2 (Must)** The system shall return a result for given query.\n",
    )
    tc = _tc_file(tmp_path, _RE1_EBT_BLOCK)

    report = scan(tc, req)

    assert report.total_must_requirements == 2
    assert report.requirements_already_covered == 1
    assert len(report.candidates) == 1
    assert report.candidates[0].requirement_id == "RE-2"


# ---------------------------------------------------------------------------
# Test 2 — SHOULD requirements are skipped
# ---------------------------------------------------------------------------


def test_should_requirement_with_no_test_is_not_a_candidate(tmp_path: Path) -> None:
    req = _req_file(
        tmp_path,
        "**RE-1 (Should)** The system should support a nice-to-have.\n",
    )
    tc = _tc_file(tmp_path, "")

    report = scan(tc, req)

    assert report.total_must_requirements == 0
    assert report.candidates == ()


# ---------------------------------------------------------------------------
# Test 3 — empty requirements file
# ---------------------------------------------------------------------------


def test_empty_requirements_yields_empty_report(tmp_path: Path) -> None:
    req = _req_file(tmp_path, "")
    tc = _tc_file(tmp_path, "")

    report = scan(tc, req)

    assert report.total_must_requirements == 0
    assert report.requirements_already_covered == 0
    assert report.candidates == ()


# ---------------------------------------------------------------------------
# Test 4 — empty test-cases means every MUST is a candidate
# ---------------------------------------------------------------------------


def test_empty_test_cases_yields_candidate_per_must(tmp_path: Path) -> None:
    req = _req_file(
        tmp_path,
        "**RE-1 (Must)** The system shall do A.\n"
        "**RE-2 (Must)** The system shall do B.\n"
        "**RE-3 (Should)** The system should do C.\n",
    )
    tc = _tc_file(tmp_path, "")

    report = scan(tc, req)

    assert report.total_must_requirements == 2
    assert report.requirements_already_covered == 0
    assert {c.requirement_id for c in report.candidates} == {"RE-1", "RE-2"}


# ---------------------------------------------------------------------------
# Test 5 — negative-assertion strategies
# ---------------------------------------------------------------------------


def test_negative_strategy_explicit_must_not_in_requirement(tmp_path: Path) -> None:
    req = _req_file(
        tmp_path,
        '**RE-1 (Must)** The output MUST NOT contain "secret-token".\n',
    )
    tc = _tc_file(tmp_path, "")

    report = scan(tc, req)

    assert len(report.candidates) == 1
    cand = report.candidates[0]
    assert "secret-token" in cand.suggested_negative
    assert "explicit" in cand.rationale.lower()


def test_negative_strategy_antonym_pair_accept_reject(tmp_path: Path) -> None:
    req = _req_file(
        tmp_path,
        "**RE-1 (Must)** The system shall accept the request.\n",
    )
    tc = _tc_file(tmp_path, "")

    report = scan(tc, req)

    assert len(report.candidates) == 1
    cand = report.candidates[0]
    assert cand.suggested_positive.lower().strip() == "accept"
    assert cand.suggested_negative.lower().strip() == "reject"
    assert "antonym" in cand.rationale.lower()


def test_negative_strategy_fallback_when_no_antonym(tmp_path: Path) -> None:
    req = _req_file(
        tmp_path,
        "**RE-1 (Must)** The system shall produce frobnication.\n",
    )
    tc = _tc_file(tmp_path, "")

    report = scan(tc, req)

    cand = report.candidates[0]
    assert cand.suggested_negative == "<TBD: counterexample value to add>"


# ---------------------------------------------------------------------------
# Test 6 — input extraction
# ---------------------------------------------------------------------------


def test_input_extraction_quoted_literal(tmp_path: Path) -> None:
    req = _req_file(
        tmp_path,
        '**RE-1 (Must)** The system shall handle "New York" as a city name.\n',
    )
    tc = _tc_file(tmp_path, "")

    cand = scan(tc, req).candidates[0]
    assert cand.suggested_input == '"New York"'


def test_input_extraction_for_cue(tmp_path: Path) -> None:
    req = _req_file(
        tmp_path,
        "**RE-1 (Must)** The system shall compute totals for budget items.\n",
    )
    tc = _tc_file(tmp_path, "")

    cand = scan(tc, req).candidates[0]
    assert "budget" in cand.suggested_input.lower()


def test_input_extraction_fallback(tmp_path: Path) -> None:
    req = _req_file(
        tmp_path,
        "**RE-1 (Must)** The output shall be deterministic.\n",
    )
    tc = _tc_file(tmp_path, "")

    cand = scan(tc, req).candidates[0]
    assert cand.suggested_input == "<TBD: practitioner-supplied>"


# ---------------------------------------------------------------------------
# Test 7 — draft_block ADR-502 shape
# ---------------------------------------------------------------------------


def test_draft_block_has_adr_502_shape(tmp_path: Path) -> None:
    req = _req_file(
        tmp_path,
        "**RE-1 (Must)** The system shall accept a request.\n",
    )
    tc = _tc_file(tmp_path, "")

    cand = scan(tc, req).candidates[0]
    block = cand.draft_block
    for token in (
        "[EXAMPLE]",
        "Input:",
        "MUST contain",
        "MUST NOT contain",
        "[Requirement:",
        "[Trace: not-yet-traced]",
    ):
        assert token in block, f"expected {token!r} in draft_block:\n{block}"


# ---------------------------------------------------------------------------
# Test 8 — Path | str at boundary
# ---------------------------------------------------------------------------


def test_path_or_str_accepted_at_boundary(tmp_path: Path) -> None:
    req = _req_file(tmp_path, "**RE-1 (Must)** shall accept input.\n")
    tc = _tc_file(tmp_path, "")

    r1 = scan(str(tc), str(req))
    r2 = scan(tc, req)

    assert r1.total_must_requirements == r2.total_must_requirements == 1
    assert len(r1.candidates) == len(r2.candidates) == 1


# ---------------------------------------------------------------------------
# Test 9 — frozen dataclasses
# ---------------------------------------------------------------------------


def test_dataclasses_are_frozen(tmp_path: Path) -> None:
    req = _req_file(tmp_path, "**RE-1 (Must)** shall accept input.\n")
    tc = _tc_file(tmp_path, "")

    report = scan(tc, req)
    cand = report.candidates[0]

    with pytest.raises(dataclasses.FrozenInstanceError):
        cand.requirement_id = "X"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        report.total_must_requirements = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Test 10 — CLI entry
# ---------------------------------------------------------------------------


def test_cli_runs_and_exits_zero(tmp_path: Path) -> None:
    req = _req_file(
        tmp_path,
        "**RE-1 (Must)** The system shall accept input.\n"
        "**RE-2 (Must)** The system shall reject bad input.\n",
    )
    tc = _tc_file(tmp_path, _RE1_EBT_BLOCK)

    scripts_dir = Path(__file__).resolve().parent
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "_retrofit",
            "--requirements",
            str(req),
            "--test-cases",
            str(tc),
        ],
        cwd=str(scripts_dir),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    # Some signal that the report was printed:
    assert "candidate" in result.stdout.lower()
