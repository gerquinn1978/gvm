"""Tests for HS-2 expiry CI helper (cross-cutting ADR-008).

Covers TC-HS-2-01 (boundary today < expiry passes), TC-HS-2-02 (today > expiry
fails and names the entry), and TC-HS-2-03 (non-ISO expiry surfaces as a parse
error). Also pins the today == expiry boundary (NOT expired — strict less-than)
and the missing-STUBS.md error path.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _expiry_check import run  # noqa: E402

_HEADER = (
    "---\nschema_version: 1\n---\n# Stubs\n\n"
    "| Path | Reason | Real-provider Plan | Owner | Expiry |\n"
    "|---|---|---|---|---|\n"
)


def _write(tmp_path: Path, rows: list[tuple[str, str]]) -> Path:
    body = _HEADER + "".join(
        f"| {p} | placeholder until real provider wired "
        f"| Replace with real provider | alice | {expiry} |\n"
        for p, expiry in rows
    )
    out = tmp_path / "STUBS.md"
    out.write_text(body, encoding="utf-8")
    return out


def test_today_before_expiry_passes(tmp_path: Path):
    """TC-HS-2-01 boundary: today < expiry → exit 0."""
    stubs = _write(tmp_path, [("stubs/a.py", "2026-04-23")])
    code, msg = run(stubs, today=dt.date(2026, 4, 22))
    assert code == 0
    assert msg == ""


def test_today_equal_expiry_passes(tmp_path: Path):
    """Strict `<` boundary: today == expiry → not expired (CI passes on the
    expiry day itself, per `_stubs_parser.check_expiry`)."""
    stubs = _write(tmp_path, [("stubs/a.py", "2026-04-22")])
    code, _ = run(stubs, today=dt.date(2026, 4, 22))
    assert code == 0


def test_today_after_expiry_fails(tmp_path: Path):
    """TC-HS-2-02: today > expiry → exit 1 with the path named in stderr."""
    stubs = _write(tmp_path, [("stubs/a.py", "2026-04-21")])
    code, msg = run(stubs, today=dt.date(2026, 4, 22))
    assert code == 1
    assert "stubs/a.py" in msg


def test_multiple_expired_all_named(tmp_path: Path):
    stubs = _write(
        tmp_path,
        [
            ("stubs/old1.py", "2026-04-20"),
            ("stubs/fresh.py", "2027-01-01"),
            ("stubs/old2.py", "2026-04-19"),
        ],
    )
    code, msg = run(stubs, today=dt.date(2026, 4, 22))
    assert code == 1
    assert "stubs/old1.py" in msg
    assert "stubs/old2.py" in msg
    assert "stubs/fresh.py" not in msg


def test_non_iso_expiry_surfaces_as_parse_error(tmp_path: Path):
    """TC-HS-2-03: non-ISO-8601 expiry → parse error, exit 1 with message."""
    body = (
        _HEADER
        + "| stubs/a.py | placeholder until real provider wired "
        + "| Replace with real provider | alice | 22/04/2026 |\n"
    )
    stubs = tmp_path / "STUBS.md"
    stubs.write_text(body, encoding="utf-8")
    code, msg = run(stubs, today=dt.date(2026, 4, 22))
    assert code == 1
    assert msg, "stderr message must be non-empty on parse failure"


def test_missing_stubs_md_returns_clear_message(tmp_path: Path):
    code, msg = run(tmp_path / "MISSING.md", today=dt.date(2026, 4, 22))
    assert code == 1
    assert "STUBS.md" in msg or "not found" in msg.lower()


def test_run_today_defaults_to_today(tmp_path: Path):
    """When today is omitted, the helper uses date.today()."""
    far_future = (dt.date.today() + dt.timedelta(days=365)).isoformat()
    stubs = _write(tmp_path, [("stubs/a.py", far_future)])
    code, _ = run(stubs)
    assert code == 0


def test_empty_stubs_passes(tmp_path: Path):
    stubs = _write(tmp_path, [])
    code, msg = run(stubs, today=dt.date(2026, 4, 22))
    assert code == 0
    assert msg == ""


def test_cli_entry_point_runs(tmp_path: Path, monkeypatch, capsys):
    """The `__main__` shim exits with the helper's code and prints msg to
    stderr."""
    stubs = _write(tmp_path, [("stubs/a.py", "2026-04-21")])
    monkeypatch.setattr(sys, "argv", ["_expiry_check.py", str(stubs)])

    import _expiry_check

    monkeypatch.setattr(_expiry_check, "_today", lambda: dt.date(2026, 4, 22))

    with pytest.raises(SystemExit) as exc:
        _expiry_check.main()
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "stubs/a.py" in captured.err


def test_cli_entry_point_exit_zero_on_clean(tmp_path: Path, monkeypatch, capsys):
    """The exit-0 path through main() — no expired stubs, empty stderr.

    HS-2 contracts the CI shim to "exit 0 on pass, exit 1 on any expired
    stub". The exit-1 path is covered above; this test pins the exit-0 path
    so a regression flipping main() to always exit non-zero is caught.
    """
    stubs = _write(tmp_path, [("stubs/a.py", "2099-01-01")])
    monkeypatch.setattr(sys, "argv", ["_expiry_check.py", str(stubs)])

    import _expiry_check

    monkeypatch.setattr(_expiry_check, "_today", lambda: dt.date(2026, 4, 22))

    with pytest.raises(SystemExit) as exc:
        _expiry_check.main()
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert captured.err == ""
