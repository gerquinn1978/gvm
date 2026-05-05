"""Tests for ``_shared/path_check.py`` — mapping-path risk validator.

Anonymisation-pipeline ADR-404 / AN-38 (P14-C01, originally P7-C01 in the
gvm-analysis impl-guide; renumbered to avoid plugin-build clash).

Covers TC-AN-38-01 (risky path warns + refuses without --i-accept-the-risk)
and TC-AN-38-02 (safe external path accepted silently).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# --- TC-AN-38-01: risky path raises with diagnostic --------------------------


def test_validate_refuses_path_inside_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from _shared import path_check
    from _shared.diagnostics import RiskyMappingPathError

    monkeypatch.chdir(tmp_path)
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"permissions": {"additionalDirectories": []}}))

    risky = tmp_path / "mapping.csv"
    with pytest.raises(RiskyMappingPathError) as exc:
        path_check.validate(risky, accept_risk=False, claude_settings_path=settings)

    msg = str(exc.value)
    assert str(risky.resolve()) in msg
    # Diagnostic must list at least one alternative (ADR-404 prose).
    assert "~/.private" in msg or ".private" in msg


def test_validate_refuses_path_inside_additional_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from _shared import path_check
    from _shared.diagnostics import RiskyMappingPathError

    # cwd is some unrelated dir.
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    extra = tmp_path / "extra"
    extra.mkdir()
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps({"permissions": {"additionalDirectories": [str(extra)]}})
    )

    risky = extra / "mapping.csv"
    with pytest.raises(RiskyMappingPathError):
        path_check.validate(risky, accept_risk=False, claude_settings_path=settings)


# --- TC-AN-38-02: safe external path accepted silently -----------------------


def test_validate_accepts_safe_external_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from _shared import path_check

    # cwd inside tmp_path/cwd, additionalDirectories empty, target under
    # tmp_path/safe — outside both scopes. Spec-compliant alternative
    # (~/.private/gvm-mappings/...) follows the same logic.
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    safe = tmp_path / "safe" / "mapping.csv"
    safe.parent.mkdir()
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"permissions": {"additionalDirectories": []}}))

    # Returns None silently — no warning, no exception.
    assert (
        path_check.validate(safe, accept_risk=False, claude_settings_path=settings)
        is None
    )


# --- accept_risk bypass ------------------------------------------------------


def test_validate_accept_risk_bypasses_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from _shared import path_check

    monkeypatch.chdir(tmp_path)
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"permissions": {"additionalDirectories": []}}))

    risky = tmp_path / "mapping.csv"
    # accept_risk=True returns silently even for an in-cwd path.
    assert (
        path_check.validate(risky, accept_risk=True, claude_settings_path=settings)
        is None
    )


# --- missing or malformed settings -------------------------------------------


def test_validate_missing_settings_file_treated_as_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from _shared import path_check

    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    # settings.json does not exist — additionalDirectories defaults to empty.
    safe = tmp_path / "safe" / "mapping.csv"
    safe.parent.mkdir()
    missing_settings = tmp_path / "no_such_settings.json"
    assert (
        path_check.validate(
            safe, accept_risk=False, claude_settings_path=missing_settings
        )
        is None
    )


def test_validate_malformed_settings_propagates_diagnostic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from _shared import path_check
    from _shared.diagnostics import MalformedFileError

    monkeypatch.chdir(tmp_path)
    settings = tmp_path / "settings.json"
    settings.write_text("{not valid json")

    safe = tmp_path / "safe" / "mapping.csv"
    safe.parent.mkdir()
    with pytest.raises(MalformedFileError):
        path_check.validate(safe, accept_risk=False, claude_settings_path=settings)


# --- default settings path is platform-correct -------------------------------


def test_validate_default_settings_path_is_under_dot_claude(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When no claude_settings_path is provided, the default must point at
    ``~/.claude/settings.json`` — but the test must not actually read the
    real user's settings file. Inject HOME via monkeypatch so the lookup
    resolves under tmp_path.
    """
    from _shared import path_check

    fake_home = tmp_path / "home"
    fake_home.mkdir()
    (fake_home / ".claude").mkdir()
    settings = fake_home / ".claude" / "settings.json"
    settings.write_text(json.dumps({"permissions": {"additionalDirectories": []}}))

    monkeypatch.setenv("HOME", str(fake_home))
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    safe = tmp_path / "safe" / "mapping.csv"
    safe.parent.mkdir()
    # No claude_settings_path → default → fake_home/.claude/settings.json.
    assert path_check.validate(safe, accept_risk=False) is None


# --- diagnostic completeness (ADR-404 prose) ---------------------------------


def test_diagnostic_names_path_and_alternatives(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from _shared import path_check
    from _shared.diagnostics import RiskyMappingPathError

    monkeypatch.chdir(tmp_path)
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"permissions": {"additionalDirectories": []}}))

    risky = tmp_path / "mapping.csv"
    with pytest.raises(RiskyMappingPathError) as exc:
        path_check.validate(risky, accept_risk=False, claude_settings_path=settings)

    msg = str(exc.value)
    # Per ADR-404, the diagnostic must:
    # 1. Name the offending path verbatim.
    assert str(risky.resolve()) in msg
    # 2. Reference --i-accept-the-risk as the opt-in.
    assert "i-accept-the-risk" in msg.lower()
    # 3. Suggest at least one concrete alternative location.
    assert ".private" in msg or "ExternalSSD" in msg or "external" in msg.lower()
