"""Tests for HS-1 chunk-handover gate (honesty-triad ADR-101).

Covers TC-HS-1-01 (registered stub accepted) and TC-HS-1-02 (unregistered stub
rejected) plus edge cases: empty list, non-stub paths, missing STUBS.md,
walking-skeleton namespace, frozen-error contract, and the no-disk-for-files
guarantee from ADR-101.
"""

from __future__ import annotations

import datetime as dt
import sys
from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path

import pytest

# This skill's scripts dir is on sys.path so `_hs1_check` imports cleanly. The
# module itself adds gvm-design-system/scripts (for `_stubs_parser`).
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _hs1_check import UnregisteredStubError, check  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_STUBS_HEADER = (
    "---\nschema_version: 1\n---\n# Stubs\n\n"
    "| Path | Reason | Real-provider Plan | Owner | Expiry |\n"
    "|---|---|---|---|---|\n"
)


def _write_stubs(tmp_path: Path, rows: list[tuple[str, str, str, str, str]]) -> Path:
    body = _STUBS_HEADER + "".join(
        f"| {p} | {r} | {plan} | {o} | {e} |\n" for p, r, plan, o, e in rows
    )
    out = tmp_path / "STUBS.md"
    out.write_text(body, encoding="utf-8")
    return out


def _row(path: str) -> tuple[str, str, str, str, str]:
    expiry = (dt.date.today() + dt.timedelta(days=30)).isoformat()
    return (
        path,
        "placeholder until real provider wired",
        "Replace with real provider",
        "alice",
        expiry,
    )


# ---------------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------------


def test_empty_file_list_passes(tmp_path: Path):
    stubs = _write_stubs(tmp_path, [])
    assert check([], stubs) == []


def test_non_stub_path_ignored(tmp_path: Path):
    stubs = _write_stubs(tmp_path, [])
    assert check(["src/foo.py", "tests/test_bar.py", "README.md"], stubs) == []


def test_registered_stub_passes(tmp_path: Path):
    """TC-HS-1-01: registered stub accepted."""
    stubs = _write_stubs(tmp_path, [_row("stubs/mock_provider.py")])
    assert check(["stubs/mock_provider.py"], stubs) == []


def test_unregistered_stub_returns_error(tmp_path: Path):
    """TC-HS-1-02: unregistered stub rejected, error names the offending path."""
    stubs = _write_stubs(tmp_path, [])
    result = check(["stubs/new_stub.py"], stubs)
    assert len(result) == 1
    assert result[0].path == "stubs/new_stub.py"


def test_walking_skeleton_namespace_recognised(tmp_path: Path):
    stubs = _write_stubs(tmp_path, [_row("walking-skeleton/stubs/ws_provider.py")])
    assert check(["walking-skeleton/stubs/ws_provider.py"], stubs) == []
    # And unregistered version is flagged
    assert check(["walking-skeleton/stubs/other.py"], stubs) == [
        UnregisteredStubError(path="walking-skeleton/stubs/other.py")
    ]


def test_multiple_unregistered_one_error_each(tmp_path: Path):
    stubs = _write_stubs(tmp_path, [_row("stubs/registered.py")])
    files = [
        "stubs/registered.py",
        "stubs/missing_a.py",
        "src/normal.py",
        "stubs/missing_b.py",
    ]
    result = check(files, stubs)
    paths = sorted(e.path for e in result)
    assert paths == ["stubs/missing_a.py", "stubs/missing_b.py"]


def test_missing_stubs_md_treats_as_no_registrations(tmp_path: Path):
    stubs = tmp_path / "DOES_NOT_EXIST.md"
    result = check(["stubs/anything.py"], stubs)
    assert result == [UnregisteredStubError(path="stubs/anything.py")]


def test_missing_stubs_md_with_no_stub_files_passes(tmp_path: Path):
    stubs = tmp_path / "DOES_NOT_EXIST.md"
    assert check(["src/regular.py"], stubs) == []


def test_returned_errors_are_frozen_dataclass(tmp_path: Path):
    stubs = _write_stubs(tmp_path, [])
    result = check(["stubs/x.py"], stubs)
    assert is_dataclass(result[0])
    with pytest.raises((FrozenInstanceError, AttributeError)):
        result[0].path = "mutated"  # type: ignore[misc]


def test_check_does_not_touch_disk_for_files(tmp_path: Path, monkeypatch):
    """ADR-101: the script's only disk read is `stubs_path`. The file list
    must not be probed (no os.path.exists / Path.exists on file entries)."""
    stubs = _write_stubs(tmp_path, [_row("stubs/registered.py")])
    real_exists = Path.exists
    seen: list[str] = []

    def spy_exists(self):
        seen.append(str(self))
        return real_exists(self)

    monkeypatch.setattr(Path, "exists", spy_exists)
    check(["stubs/registered.py", "stubs/unregistered.py", "src/foo.py"], stubs)
    # Only the stubs_path may be probed. None of the file-list entries.
    file_list_paths = {"stubs/registered.py", "stubs/unregistered.py", "src/foo.py"}
    leaked = [s for s in seen if any(s.endswith(f) for f in file_list_paths)]
    assert leaked == [], f"_hs1_check probed disk for file entries: {leaked}"


def test_does_not_invoke_subprocess(monkeypatch, tmp_path: Path):
    """ADR-101: no git invocation. Subprocess use is forbidden."""
    import subprocess

    def boom(*a, **k):
        raise AssertionError("_hs1_check must not invoke subprocess (no git)")

    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(subprocess, "Popen", boom)
    monkeypatch.setattr(subprocess, "check_call", boom)
    monkeypatch.setattr(subprocess, "check_output", boom)
    stubs = _write_stubs(tmp_path, [_row("stubs/x.py")])
    check(["stubs/x.py", "src/y.py"], stubs)


def test_input_files_list_not_mutated(tmp_path: Path):
    stubs = _write_stubs(tmp_path, [])
    files = ["stubs/a.py", "src/b.py"]
    snapshot = list(files)
    check(files, stubs)
    assert files == snapshot
