"""Tests for HS-3 startup loader (honesty-triad ADR-102).

Covers TC-HS-3-01 (warning emitted for active registered stub),
TC-HS-3-02 (silent on no registered stubs), and TC-HS-3-04 (warning is
unconditional — not suppressible by env vars). Also pins the today == expiry
boundary (still active per strict `<` semantics) and the missing/parse-error
silence contract.
"""

from __future__ import annotations

import datetime as dt
import io
import re
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _stubs_runtime import warn_if_active  # noqa: E402

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


def test_active_stub_emits_warning(tmp_path: Path):
    """TC-HS-3-01: registered active stub → STUB ACTIVE line on stderr."""
    stubs = _write(tmp_path, [("stubs/mock_provider.py", "2026-06-01")])
    stream = io.StringIO()
    n = warn_if_active(stubs, today=dt.date(2026, 4, 25), stream=stream)
    assert n == 1
    assert "STUB ACTIVE: mock_provider — expires 2026-06-01" in stream.getvalue()


def test_no_registered_stubs_silent(tmp_path: Path):
    """TC-HS-3-02: empty registry → no STUB ACTIVE line."""
    stubs = _write(tmp_path, [])
    stream = io.StringIO()
    n = warn_if_active(stubs, today=dt.date(2026, 4, 25), stream=stream)
    assert n == 0
    assert "STUB ACTIVE" not in stream.getvalue()


def test_missing_stubs_md_silent(tmp_path: Path):
    """Missing STUBS.md → silent (returns 0, no raise)."""
    stream = io.StringIO()
    n = warn_if_active(
        tmp_path / "MISSING.md", today=dt.date(2026, 4, 25), stream=stream
    )
    assert n == 0
    assert stream.getvalue() == ""


def test_expired_stub_not_warned(tmp_path: Path):
    """An entry whose expiry is in the past is no longer 'active'."""
    stubs = _write(tmp_path, [("stubs/old.py", "2026-04-01")])
    stream = io.StringIO()
    n = warn_if_active(stubs, today=dt.date(2026, 4, 25), stream=stream)
    assert n == 0
    assert "STUB ACTIVE" not in stream.getvalue()


def test_today_equal_expiry_still_active(tmp_path: Path):
    """Strict `<` boundary: today == expiry → still active (last day)."""
    stubs = _write(tmp_path, [("stubs/edge.py", "2026-04-25")])
    stream = io.StringIO()
    n = warn_if_active(stubs, today=dt.date(2026, 4, 25), stream=stream)
    assert n == 1
    assert "STUB ACTIVE: edge — expires 2026-04-25" in stream.getvalue()


def test_multiple_active_stubs_each_warned(tmp_path: Path):
    stubs = _write(
        tmp_path,
        [
            ("stubs/a.py", "2026-06-01"),
            ("stubs/b.py", "2026-07-01"),
            ("stubs/expired.py", "2026-04-01"),
        ],
    )
    stream = io.StringIO()
    n = warn_if_active(stubs, today=dt.date(2026, 4, 25), stream=stream)
    assert n == 2
    out = stream.getvalue()
    assert "STUB ACTIVE: a — expires 2026-06-01" in out
    assert "STUB ACTIVE: b — expires 2026-07-01" in out
    assert "expired" not in out


def test_walking_skeleton_namespace_uses_stem(tmp_path: Path):
    """`<name>` is the path stem regardless of namespace prefix."""
    stubs = _write(tmp_path, [("walking-skeleton/stubs/router.py", "2026-06-01")])
    stream = io.StringIO()
    warn_if_active(stubs, today=dt.date(2026, 4, 25), stream=stream)
    assert "STUB ACTIVE: router — expires 2026-06-01" in stream.getvalue()


def test_parse_error_silent(tmp_path: Path):
    """A malformed STUBS.md must not crash the runtime warning helper."""
    bad = tmp_path / "STUBS.md"
    bad.write_text(
        _HEADER + "| stubs/x.py | r | p | o | not-a-date |\n", encoding="utf-8"
    )
    stream = io.StringIO()
    n = warn_if_active(bad, today=dt.date(2026, 4, 25), stream=stream)
    assert n == 0


def test_unconditional_under_suppressing_env(tmp_path: Path, monkeypatch):
    """TC-HS-3-04: env vars that normally suppress warnings do not silence this."""
    for var in ("STUB_WARNINGS", "NO_WARNINGS", "PYTHONWARNINGS"):
        monkeypatch.setenv(var, "0" if var == "STUB_WARNINGS" else "ignore")
    stubs = _write(tmp_path, [("stubs/mock_provider.py", "2026-06-01")])
    stream = io.StringIO()
    n = warn_if_active(stubs, today=dt.date(2026, 4, 25), stream=stream)
    assert n == 1
    assert "STUB ACTIVE: mock_provider" in stream.getvalue()


def test_default_stream_is_stderr(tmp_path: Path, capsys):
    """When stream is omitted, output goes to sys.stderr (not stdout)."""
    stubs = _write(tmp_path, [("stubs/mock_provider.py", "2026-06-01")])
    warn_if_active(stubs, today=dt.date(2026, 4, 25))
    captured = capsys.readouterr()
    assert "STUB ACTIVE: mock_provider" in captured.err
    assert captured.out == ""


def test_provenance_comment_present():
    """ADR-102: helper carries `# Source: gvm_stubs vN.M (sha256: ...)` header."""
    src = (_SCRIPTS / "_stubs_runtime.py").read_text(encoding="utf-8")
    pattern = re.compile(
        r"^# Source: gvm_stubs v\d+\.\d+ \(sha256: [^)]+\)$", re.MULTILINE
    )
    assert pattern.search(src), "missing provenance comment per ADR-102"
