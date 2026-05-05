"""Tests for ADR-109 comprehension-question bridge (P5-C01b).

Covers:
- ``_shared.findings.patch_comprehension_questions`` helper (in-process)
- ``scripts/_patch_questions.py`` CLI wrapper (subprocess)
- TC-NFR-4-01 / 01b / 01c (question count, field shape, jargon scan)
- TC-NFR-4-02 (referential integrity to headline_findings[].id)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from _shared.diagnostics import (
    JargonError,
    ReferentialIntegrityError,
)
from _shared.findings import (
    SchemaValidationError,
    build_empty_findings,
    patch_comprehension_questions,
    read_findings,
    write_atomic,
)

SKILL_ROOT = Path(__file__).resolve().parents[2]
WRAPPER = SKILL_ROOT / "scripts" / "_patch_questions.py"


# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------


def _provenance() -> dict[str, Any]:
    return {
        "input_sha256": "0" * 64,
        "library_versions": {},
        "timestamp": "2026-04-20T00:00:00Z",
        "rng_seed": 42,
        "preferences_hash": "x",
    }


def _headlines() -> list[dict[str, Any]]:
    return [
        {
            "id": "h-outlier-01",
            "title": "col_a contains unusually high values",
            "summary": "5 rows flagged by 3 methods.",
            "kind": "outlier",
            "drillthrough_id": None,
            "methodology_ref": None,
        },
        {
            "id": "h-missing-02",
            "title": "col_b has 20% missing values",
            "summary": "Missingness pattern looks structured.",
            "kind": "data_quality",
            "drillthrough_id": None,
            "methodology_ref": None,
        },
        {
            "id": "h-driver-03",
            "title": "col_c is the top driver of col_target",
            "summary": "Agreement across 3 of 3 ranking methods.",
            "kind": "driver",
            "drillthrough_id": None,
            "methodology_ref": None,
        },
    ]


@pytest.fixture
def findings_path(tmp_path: Path) -> Path:
    data = build_empty_findings(provenance=_provenance())
    data["headline_findings"] = _headlines()
    path = tmp_path / "findings.json"
    write_atomic(path, data)
    return path


def _valid_three() -> list[dict[str, str]]:
    return [
        {
            "question": "Why does col_a have unusual high values?",
            "answer": "A few rows have extreme readings; those rows are flagged.",
            "supporting_finding_id": "h-outlier-01",
        },
        {
            "question": "Why is col_b missing for one in five rows?",
            "answer": "The pattern is structured, not random.",
            "supporting_finding_id": "h-missing-02",
        },
        {
            "question": "What most influences col_target?",
            "answer": "col_c has the strongest agreement among three ranking methods.",
            "supporting_finding_id": "h-driver-03",
        },
    ]


# ---------------------------------------------------------------------------
# Helper: happy path
# ---------------------------------------------------------------------------


def test_patch_success_writes_questions(findings_path: Path) -> None:
    patch_comprehension_questions(findings_path, _valid_three())
    data = read_findings(findings_path)
    assert len(data["comprehension_questions"]) == 3
    assert data["comprehension_questions"][0]["supporting_finding_id"] == "h-outlier-01"


def test_patch_accepts_str_path(findings_path: Path) -> None:
    patch_comprehension_questions(str(findings_path), _valid_three())
    assert read_findings(findings_path)["comprehension_questions"]


def test_patch_round_trip_preserves_other_fields(findings_path: Path) -> None:
    before = read_findings(findings_path)
    patch_comprehension_questions(findings_path, _valid_three())
    after = read_findings(findings_path)
    for key in ("provenance", "headline_findings", "columns", "outliers"):
        assert before[key] == after[key], f"patch clobbered {key}"


# ---------------------------------------------------------------------------
# Helper: shape validation (TC-NFR-4-01 / 01b / 01c)
# ---------------------------------------------------------------------------


def test_patch_rejects_too_few_questions(findings_path: Path) -> None:
    with pytest.raises(SchemaValidationError, match="exactly 3"):
        patch_comprehension_questions(findings_path, _valid_three()[:2])


def test_patch_rejects_too_many_questions(findings_path: Path) -> None:
    with pytest.raises(SchemaValidationError, match="exactly 3"):
        patch_comprehension_questions(
            findings_path, _valid_three() + [_valid_three()[0]]
        )


def test_patch_rejects_non_list(findings_path: Path) -> None:
    with pytest.raises(SchemaValidationError, match="list"):
        patch_comprehension_questions(findings_path, {"bogus": "shape"})  # type: ignore[arg-type]


def test_patch_rejects_missing_field(findings_path: Path) -> None:
    qs = _valid_three()
    del qs[1]["answer"]
    with pytest.raises(SchemaValidationError, match="answer"):
        patch_comprehension_questions(findings_path, qs)


def test_patch_rejects_non_string_field(findings_path: Path) -> None:
    qs = _valid_three()
    qs[0]["question"] = 42  # type: ignore[assignment]
    with pytest.raises(SchemaValidationError, match="question"):
        patch_comprehension_questions(findings_path, qs)


def test_patch_rejects_extra_field(findings_path: Path) -> None:
    qs = _valid_three()
    qs[0]["extra"] = "nope"
    with pytest.raises(SchemaValidationError):
        patch_comprehension_questions(findings_path, qs)


# ---------------------------------------------------------------------------
# Helper: referential integrity (TC-NFR-4-02)
# ---------------------------------------------------------------------------


def test_patch_rejects_unknown_supporting_id(findings_path: Path) -> None:
    qs = _valid_three()
    qs[1]["supporting_finding_id"] = "h-nonexistent-99"
    with pytest.raises(ReferentialIntegrityError) as exc_info:
        patch_comprehension_questions(findings_path, qs)
    assert exc_info.value.reference == "h-nonexistent-99"
    assert exc_info.value.kind == "headline_findings.id"


# ---------------------------------------------------------------------------
# Helper: jargon scan (TC-NFR-4-01c)
# ---------------------------------------------------------------------------


def test_patch_rejects_jargon_in_question(findings_path: Path) -> None:
    qs = _valid_three()
    qs[0]["question"] = "Did Shapiro-Wilk reject the distribution?"
    with pytest.raises(JargonError) as exc_info:
        patch_comprehension_questions(findings_path, qs)
    assert exc_info.value.term == "shapiro-wilk"
    assert "comprehension_questions[0].question" in exc_info.value.location


def test_patch_rejects_jargon_in_answer(findings_path: Path) -> None:
    qs = _valid_three()
    qs[2]["answer"] = "The ARIMA model suggested a trend."
    with pytest.raises(JargonError) as exc_info:
        patch_comprehension_questions(findings_path, qs)
    assert exc_info.value.term == "arima"
    assert "comprehension_questions[2].answer" in exc_info.value.location


def test_patch_word_boundary_allows_summary(findings_path: Path) -> None:
    """'summary' contains 'mar' as a substring; word-boundary scan must allow it."""
    qs = _valid_three()
    qs[0]["answer"] = "See the summary above for details."
    patch_comprehension_questions(findings_path, qs)  # must not raise


# ---------------------------------------------------------------------------
# Wrapper: CLI subprocess tests
# ---------------------------------------------------------------------------


def _run_wrapper(findings: Path, questions: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        str(SKILL_ROOT / "scripts") + os.pathsep + env.get("PYTHONPATH", "")
    )
    return subprocess.run(
        [
            sys.executable,
            str(WRAPPER),
            "--findings",
            str(findings),
            "--questions",
            str(questions),
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(SKILL_ROOT),
        check=False,
    )


def _write_questions(path: Path, questions: Any) -> Path:
    path.write_text(json.dumps(questions), encoding="utf-8")
    return path


def test_wrapper_success_deletes_temp_file(findings_path: Path, tmp_path: Path) -> None:
    qpath = _write_questions(tmp_path / "qs.tmp.json", _valid_three())
    proc = _run_wrapper(findings_path, qpath)
    assert proc.returncode == 0, proc.stderr
    assert not qpath.exists(), "temp file must be deleted on success"
    data = read_findings(findings_path)
    assert len(data["comprehension_questions"]) == 3


def test_wrapper_nonexistent_findings(tmp_path: Path) -> None:
    qpath = _write_questions(tmp_path / "qs.tmp.json", _valid_three())
    fake = tmp_path / "does-not-exist.json"
    proc = _run_wrapper(fake, qpath)
    assert proc.returncode == 2, proc.stderr
    assert qpath.exists(), "temp file must be preserved on failure"


def test_wrapper_nonexistent_questions(findings_path: Path, tmp_path: Path) -> None:
    fake = tmp_path / "no-such-questions.json"
    proc = _run_wrapper(findings_path, fake)
    assert proc.returncode == 2, proc.stderr


def test_wrapper_malformed_questions_json(findings_path: Path, tmp_path: Path) -> None:
    qpath = tmp_path / "qs.tmp.json"
    qpath.write_text("{not valid json", encoding="utf-8")
    proc = _run_wrapper(findings_path, qpath)
    assert proc.returncode == 2, proc.stderr
    assert qpath.exists()


def test_wrapper_wrong_question_count(findings_path: Path, tmp_path: Path) -> None:
    qpath = _write_questions(tmp_path / "qs.tmp.json", _valid_three()[:2])
    proc = _run_wrapper(findings_path, qpath)
    assert proc.returncode == 2, proc.stderr
    assert qpath.exists(), "temp file preserved for debugging"


def test_wrapper_missing_field(findings_path: Path, tmp_path: Path) -> None:
    qs = _valid_three()
    del qs[0]["answer"]
    qpath = _write_questions(tmp_path / "qs.tmp.json", qs)
    proc = _run_wrapper(findings_path, qpath)
    assert proc.returncode == 2


def test_wrapper_referential_integrity(findings_path: Path, tmp_path: Path) -> None:
    qs = _valid_three()
    qs[1]["supporting_finding_id"] = "h-gone-99"
    qpath = _write_questions(tmp_path / "qs.tmp.json", qs)
    proc = _run_wrapper(findings_path, qpath)
    assert proc.returncode == 3, proc.stderr
    assert "referential integrity" in proc.stderr.lower()
    assert qpath.exists()


def test_wrapper_jargon(findings_path: Path, tmp_path: Path) -> None:
    qs = _valid_three()
    qs[0]["answer"] = "The MCAR test was applied."
    qpath = _write_questions(tmp_path / "qs.tmp.json", qs)
    proc = _run_wrapper(findings_path, qpath)
    assert proc.returncode == 4, proc.stderr
    assert "jargon" in proc.stderr.lower()
    assert qpath.exists()


def test_helper_malformed_headline_missing_id(findings_path: Path) -> None:
    """A headline dict missing ``id`` must produce SchemaValidationError, not KeyError."""
    data = read_findings(findings_path)
    data["headline_findings"][0] = {"title": "no id field"}  # malformed
    write_atomic(findings_path, data)
    with pytest.raises(SchemaValidationError, match="headline_findings"):
        patch_comprehension_questions(findings_path, _valid_three())


def test_wrapper_findings_is_directory(tmp_path: Path) -> None:
    """Passing a directory as --findings must exit 2 (structural), not 1 (I/O)."""
    qpath = _write_questions(tmp_path / "qs.tmp.json", _valid_three())
    # Use tmp_path itself as a directory masquerading as a findings path.
    proc = _run_wrapper(tmp_path, qpath)
    assert proc.returncode == 2, proc.stderr


def test_wrapper_schema_error_uses_dedicated_formatter(
    findings_path: Path, tmp_path: Path
) -> None:
    """SchemaValidationError must not fall through to _format_unknown."""
    qpath = _write_questions(tmp_path / "qs.tmp.json", _valid_three()[:2])
    proc = _run_wrapper(findings_path, qpath)
    assert proc.returncode == 2, proc.stderr
    # Dedicated formatter opens with "findings validation failed"; _format_unknown
    # opens with "internal error".
    assert "internal error" not in proc.stderr.lower(), proc.stderr
    assert "validation failed" in proc.stderr.lower()


def test_wrapper_exit_code_constants_unique() -> None:
    # Import by subprocess-free path so the wrapper module is exercised.
    sys.path.insert(0, str(SKILL_ROOT / "scripts"))
    try:
        import _patch_questions as mod  # type: ignore[import-not-found]
    finally:
        sys.path.pop(0)
    codes = {
        mod.EXIT_OK,
        mod.EXIT_STRUCTURE,
        mod.EXIT_REFERENTIAL,
        mod.EXIT_JARGON,
        mod.EXIT_PRIVACY,
        mod.EXIT_IO,
    }
    assert len(codes) == 6, "exit codes must be unique"
    assert mod.EXIT_OK == 0
    assert mod.EXIT_STRUCTURE == 2
    assert mod.EXIT_REFERENTIAL == 3
    assert mod.EXIT_JARGON == 4
    assert mod.EXIT_PRIVACY == 5
    assert mod.EXIT_IO == 1
