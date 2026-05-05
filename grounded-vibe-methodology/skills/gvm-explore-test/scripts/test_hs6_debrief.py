"""Tests for HS-6 retroactive registration helper (P11-C11).

Covers TC-HS-6-01 (gvm-analysis cohort: three pre-existing stubs registered
in a single batch) and TC-HS-6-02 (single surfaced stub appended; duplicate
on re-call surfaced as skipped, not crashed).
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pytest

from _hs6_debrief import RegistrationResult, register_discovered_stubs

# _hs6_debrief inserted gvm-design-system/scripts onto sys.path on import.
from _stubs_parser import StubEntry, load_stubs, serialise  # noqa: E402


# ----------------------------------------------------------- helpers


def _stub(
    path: str,
    reason: str = "placeholder reason text long",
    plan: str = "real provider plan",
    owner: str = "gerard",
    expiry: dt.date = dt.date(2099, 12, 31),
) -> StubEntry:
    return StubEntry(
        path=path,
        reason=reason,
        real_provider_plan=plan,
        owner=owner,
        expiry=expiry,
    )


def _init_stubs(tmp_path: Path) -> Path:
    p = tmp_path / "STUBS.md"
    p.write_text(serialise([]), encoding="utf-8")
    return p


# ----------------------------------------------------------- TC-HS-6-01


def test_retroactive_cohort_registers_three_gvm_analysis_stubs(tmp_path):
    """gvm-analysis cohort: --forecast-only, _PALETTE, _STUB_COMPREHENSION_QUESTIONS."""
    stubs_path = _init_stubs(tmp_path)
    cohort = [
        _stub(
            path="stubs/forecast_only.py",
            reason="--forecast-only flag bypasses real analysis pipeline",
        ),
        _stub(
            path="stubs/palette.py",
            reason="_PALETTE constant is a placeholder for real colour scheme",
        ),
        _stub(
            path="stubs/comprehension_questions.py",
            reason="_STUB_COMPREHENSION_QUESTIONS placeholder for real question bank",
        ),
    ]
    result = register_discovered_stubs(stubs_path, cohort)

    assert isinstance(result, RegistrationResult)
    assert len(result.appended) == 3
    assert result.skipped_duplicates == ()

    loaded = load_stubs(stubs_path)
    paths = [e.path for e in loaded]
    assert paths == [
        "stubs/forecast_only.py",
        "stubs/palette.py",
        "stubs/comprehension_questions.py",
    ]


# ----------------------------------------------------------- TC-HS-6-02


def test_single_stub_appended_on_debrief(tmp_path):
    stubs_path = _init_stubs(tmp_path)
    result = register_discovered_stubs(stubs_path, [_stub(path="stubs/found.py")])
    assert len(result.appended) == 1
    assert result.skipped_duplicates == ()
    paths = [e.path for e in load_stubs(stubs_path)]
    assert paths == ["stubs/found.py"]


def test_duplicate_path_recorded_as_skipped_not_raised(tmp_path):
    """Re-invocation with a path already in STUBS.md surfaces in result."""
    stubs_path = _init_stubs(tmp_path)
    register_discovered_stubs(stubs_path, [_stub(path="stubs/dup.py")])
    result = register_discovered_stubs(
        stubs_path,
        [_stub(path="stubs/dup.py", reason="different reason text exists")],
    )
    assert result.appended == ()
    assert result.skipped_duplicates == ("stubs/dup.py",)
    # original entry preserved
    loaded = load_stubs(stubs_path)
    assert len(loaded) == 1
    assert "placeholder reason text long" in loaded[0].reason


def test_partial_batch_some_new_some_duplicate(tmp_path):
    stubs_path = _init_stubs(tmp_path)
    register_discovered_stubs(stubs_path, [_stub(path="stubs/existing.py")])
    result = register_discovered_stubs(
        stubs_path,
        [
            _stub(path="stubs/existing.py", reason="duplicate of existing entry"),
            _stub(path="stubs/new1.py"),
            _stub(path="stubs/new2.py"),
        ],
    )
    assert [e.path for e in result.appended] == ["stubs/new1.py", "stubs/new2.py"]
    assert result.skipped_duplicates == ("stubs/existing.py",)
    paths = [e.path for e in load_stubs(stubs_path)]
    assert paths == ["stubs/existing.py", "stubs/new1.py", "stubs/new2.py"]


# ----------------------------------------------------------- edge cases


def test_empty_entries_is_noop(tmp_path):
    stubs_path = _init_stubs(tmp_path)
    before = stubs_path.read_text(encoding="utf-8")
    result = register_discovered_stubs(stubs_path, [])
    assert result.appended == ()
    assert result.skipped_duplicates == ()
    assert stubs_path.read_text(encoding="utf-8") == before


def test_missing_stubs_file_propagates_filenotfound(tmp_path):
    missing = tmp_path / "no-such-STUBS.md"
    with pytest.raises(FileNotFoundError):
        register_discovered_stubs(missing, [_stub(path="stubs/x.py")])


def test_malformed_entry_propagates(tmp_path):
    """Pipe character in field → StubsParseError propagates (not caught)."""
    stubs_path = _init_stubs(tmp_path)
    bad = _stub(path="stubs/bad.py", reason="reason with | pipe in it")
    from _stubs_parser import StubsParseError

    with pytest.raises(StubsParseError):
        register_discovered_stubs(stubs_path, [bad])


# ----------------------------------------------------------- return type


def test_result_is_frozen_dataclass(tmp_path):
    stubs_path = _init_stubs(tmp_path)
    result = register_discovered_stubs(stubs_path, [_stub(path="stubs/x.py")])
    with pytest.raises(Exception):
        result.appended = ()  # type: ignore[misc]


# ----------------------------------------------------------- sanity: import path


def test_design_system_scripts_on_sys_path():
    """The debrief module must put gvm-design-system/scripts on sys.path
    so its callers can import _stubs_parser without environment plumbing."""
    scripts_dir = (
        Path(__file__).resolve().parents[2] / "gvm-design-system" / "scripts"
    )
    assert str(scripts_dir) in sys.path
