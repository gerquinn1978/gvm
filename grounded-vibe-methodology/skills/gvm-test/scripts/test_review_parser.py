"""Tests for `_review_parser.load` (VV-4(a) feeder)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


SCRIPTS_DIR = Path(__file__).resolve().parent


@pytest.fixture(autouse=True)
def _isolate_module():
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        yield
    finally:
        try:
            sys.path.remove(str(SCRIPTS_DIR))
        except ValueError:
            pass
        sys.modules.pop("_review_parser", None)


def _write_ndjson(path: Path, records: list[dict]) -> None:
    lines = [json.dumps(r) for r in records]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def test_empty_file_passes(tmp_path: Path) -> None:
    import _review_parser as rp

    target = tmp_path / "code-review-001.findings.json"
    target.write_text("", encoding="utf-8")
    status, evidence = rp.load(target)
    assert status == "PASS"
    assert "no Panel E findings" in evidence


def test_critical_finding_fails(tmp_path: Path) -> None:
    import _review_parser as rp

    target = tmp_path / "code-review-002.findings.json"
    _write_ndjson(target, [
        {"severity": "Critical", "issue": "broken", "violation_type": "unregistered"},
        {"severity": "Important", "issue": "minor", "violation_type": "expired"},
    ])
    status, evidence = rp.load(target)
    assert status == "FAIL"
    assert "1 Critical" in evidence
    assert "of 2 total" in evidence


def test_no_critical_passes(tmp_path: Path) -> None:
    import _review_parser as rp

    target = tmp_path / "code-review-003.findings.json"
    _write_ndjson(target, [
        {"severity": "Important", "issue": "x", "violation_type": "unregistered"},
        {"severity": "Minor", "issue": "y", "violation_type": "namespace_violation"},
    ])
    status, evidence = rp.load(target)
    assert status == "PASS"
    assert "2 Panel E finding" in evidence
    assert "0 Critical" in evidence


def test_blank_lines_ignored(tmp_path: Path) -> None:
    import _review_parser as rp

    target = tmp_path / "code-review-004.findings.json"
    target.write_text(
        '\n{"severity": "Critical", "issue": "x"}\n\n\n',
        encoding="utf-8",
    )
    status, _ = rp.load(target)
    assert status == "FAIL"
