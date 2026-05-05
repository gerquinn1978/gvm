"""Tests for the Panel-E findings JSON sidecar serialiser (P8-C09).

Per honesty-triad ADR-104 and cross-cutting `code-review-NNN.html` schema:
the serialiser writes a JSON sidecar `code-review/code-review-NNN.findings.json`
in NDJSON form (one JSON object per line) with the 9-field PanelEFinding shape,
alongside the human-readable HTML.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from _findings_serialiser import (
    EmptyReviewNumberError,
    FindingsSerialiserError,
    MissingDirectoryError,
    PanelEFinding,
    find_next_review_number,
    serialise_findings,
)


def _f(**overrides) -> PanelEFinding:
    base = {
        "expert": "Hunt & Thomas",
        "severity": "Critical",
        "file_line": "src/api.py:42",
        "issue": "Function returns hard-coded data",
        "spec_reference": "ADR-104",
        "fix": "Replace with real provider",
        "violation_type": "unregistered",
        "symbol": "fetch_market_data",
        "signature": "abc123def456",
    }
    base.update(overrides)
    return PanelEFinding(**base)


# --- PanelEFinding shape ----------------------------------------------------


def test_panel_e_finding_has_nine_fields():
    f = _f()
    # ADR-104 9-field contract
    fields = {
        "expert",
        "severity",
        "file_line",
        "issue",
        "spec_reference",
        "fix",
        "violation_type",
        "symbol",
        "signature",
    }
    assert set(f.__dataclass_fields__.keys()) == fields


def test_panel_e_finding_is_frozen():
    f = _f()
    # Frozen dataclass mutation raises FrozenInstanceError, which subclasses
    # AttributeError. Pin the contract with AttributeError for cross-version
    # compatibility (3.10 raises bare AttributeError; 3.11+ raises
    # FrozenInstanceError, still an AttributeError subclass).
    with pytest.raises(AttributeError):
        f.severity = "Minor"  # type: ignore[misc]


# --- find_next_review_number ------------------------------------------------


def test_find_next_review_number_empty_dir_returns_001(tmp_path: Path):
    code_review = tmp_path / "code-review"
    code_review.mkdir()
    assert find_next_review_number(code_review) == "001"


def test_find_next_review_number_increments_from_html(tmp_path: Path):
    code_review = tmp_path / "code-review"
    code_review.mkdir()
    (code_review / "code-review-003.html").write_text("ok")
    assert find_next_review_number(code_review) == "004"


def test_find_next_review_number_increments_from_json(tmp_path: Path):
    code_review = tmp_path / "code-review"
    code_review.mkdir()
    (code_review / "code-review-007.findings.json").write_text("")
    assert find_next_review_number(code_review) == "008"


def test_find_next_review_number_uses_max_across_kinds(tmp_path: Path):
    code_review = tmp_path / "code-review"
    code_review.mkdir()
    (code_review / "code-review-005.html").write_text("ok")
    (code_review / "code-review-002.findings.json").write_text("")
    (code_review / "code-review-009.html").write_text("ok")
    assert find_next_review_number(code_review) == "010"


def test_find_next_review_number_ignores_unrelated_files(tmp_path: Path):
    code_review = tmp_path / "code-review"
    code_review.mkdir()
    (code_review / "README.md").write_text("notes")
    (code_review / "code-review-bad.html").write_text("ok")
    assert find_next_review_number(code_review) == "001"


def test_find_next_review_number_missing_dir_raises(tmp_path: Path):
    with pytest.raises(MissingDirectoryError):
        find_next_review_number(tmp_path / "does-not-exist")


def test_find_next_review_number_999_exhausted_raises(tmp_path: Path):
    code_review = tmp_path / "code-review"
    code_review.mkdir()
    (code_review / "code-review-999.html").write_text("ok")
    with pytest.raises(EmptyReviewNumberError):
        find_next_review_number(code_review)


# --- serialise_findings -----------------------------------------------------


def test_serialise_findings_writes_one_json_per_line(tmp_path: Path):
    out = tmp_path / "code-review-001.findings.json"
    findings = [
        _f(symbol="alpha", signature="111"),
        _f(symbol="beta", signature="222"),
        _f(symbol="gamma", signature="333"),
    ]
    serialise_findings(findings, out)

    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    objs = [json.loads(line) for line in lines]
    assert [o["symbol"] for o in objs] == ["alpha", "beta", "gamma"]


def test_serialise_findings_round_trip_preserves_all_fields(tmp_path: Path):
    out = tmp_path / "code-review-001.findings.json"
    f = _f()
    serialise_findings([f], out)
    obj = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    for field in f.__dataclass_fields__:
        assert obj[field] == getattr(f, field)


def test_serialise_findings_empty_list_writes_empty_file(tmp_path: Path):
    out = tmp_path / "code-review-001.findings.json"
    serialise_findings([], out)
    assert out.exists()
    assert out.read_text(encoding="utf-8") == ""


def test_serialise_findings_overwrites_existing(tmp_path: Path):
    out = tmp_path / "code-review-001.findings.json"
    out.write_text("stale content\n", encoding="utf-8")
    serialise_findings([_f(symbol="fresh", signature="abc")], out)
    line = out.read_text(encoding="utf-8").splitlines()[0]
    assert json.loads(line)["symbol"] == "fresh"


def test_serialise_findings_uses_atomic_tmp_rename(tmp_path: Path):
    out = tmp_path / "code-review-001.findings.json"
    serialise_findings([_f()], out)
    # The .tmp file must not linger on success.
    assert not (out.with_suffix(out.suffix + ".tmp")).exists()


def test_serialise_findings_missing_parent_dir_raises(tmp_path: Path):
    out = tmp_path / "absent-dir" / "code-review-001.findings.json"
    with pytest.raises(FindingsSerialiserError):
        serialise_findings([_f()], out)


def test_serialise_findings_lines_are_newline_terminated(tmp_path: Path):
    out = tmp_path / "code-review-001.findings.json"
    serialise_findings([_f(symbol="a"), _f(symbol="b")], out)
    text = out.read_text(encoding="utf-8")
    # NDJSON: each record ends with \n; final byte is therefore \n.
    assert text.endswith("\n")
    assert text.count("\n") == 2


def test_serialise_findings_utf8_explicit(tmp_path: Path):
    out = tmp_path / "code-review-001.findings.json"
    f = _f(issue="non-ASCII: café résumé naïve")
    serialise_findings([f], out)
    obj = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    assert obj["issue"] == "non-ASCII: café résumé naïve"


def test_serialise_findings_cleans_tmp_on_replace_failure(tmp_path: Path, monkeypatch):
    """I-1 regression: if os.replace fails, the .tmp file must be unlinked."""
    out = tmp_path / "code-review-001.findings.json"
    import _findings_serialiser as fs

    def boom(*args, **kwargs):
        raise OSError("simulated cross-device replace failure")

    monkeypatch.setattr(fs.os, "replace", boom)
    with pytest.raises(OSError):
        serialise_findings([_f()], out)

    tmp = out.with_name(out.name + ".tmp")
    assert not tmp.exists(), "stale .tmp file left behind after os.replace failure"
    assert not out.exists(), "target file should not exist after failed replace"


def test_find_next_review_number_permission_error_wrapped(tmp_path: Path, monkeypatch):
    """I-2 regression: PermissionError on iterdir() must surface as
    MissingDirectoryError so callers catching FindingsSerialiserError are not
    bypassed by a raw OSError."""
    code_review = tmp_path / "code-review"
    code_review.mkdir()

    real_iterdir = Path.iterdir

    def deny(self):
        if self == code_review:
            raise PermissionError("simulated denied access")
        return real_iterdir(self)

    monkeypatch.setattr(Path, "iterdir", deny)
    with pytest.raises(MissingDirectoryError):
        find_next_review_number(code_review)


def test_serialise_findings_preserves_order(tmp_path: Path):
    out = tmp_path / "code-review-001.findings.json"
    findings = [_f(symbol=str(i), signature=f"{i:012}") for i in range(5)]
    serialise_findings(findings, out)
    objs = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert [o["symbol"] for o in objs] == [str(i) for i in range(5)]
