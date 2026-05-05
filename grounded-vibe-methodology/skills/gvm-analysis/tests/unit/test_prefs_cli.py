"""Tests for ``scripts/prefs_cli.py`` (ADR-104 / P5-C04).

Thin CLI wrapper around ``_shared.prefs.load`` and ``.save``. Maps failure
classes to deterministic exit codes so SKILL.md step 6 can branch without
parsing stderr (same pattern as ``_patch_questions.py``).

Exit codes:
  0 — success
  1 — I/O failure (permissions, cross-volume, disk)
  2 — validation (PreferencesValidationError)
  3 — migration refused (PreferencesMigrationError — newer-version file)
  4 — malformed YAML (MalformedFileError kind=malformed_yaml)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Generator

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "prefs_cli.py"


@pytest.fixture(autouse=True)
def _script_on_syspath() -> Generator[None, None, None]:
    scripts = str(SCRIPT_PATH.parent)
    added = scripts not in sys.path
    if added:
        sys.path.insert(0, scripts)
    try:
        yield
    finally:
        if added and scripts in sys.path:
            sys.path.remove(scripts)


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )


# ---------------------------------------------------------------------------
# Helper / module-level invariants
# ---------------------------------------------------------------------------


def test_script_exists() -> None:
    assert SCRIPT_PATH.exists(), f"prefs_cli.py must exist at {SCRIPT_PATH}"


def test_exit_codes_are_defined() -> None:
    import prefs_cli

    assert prefs_cli.EXIT_OK == 0
    assert prefs_cli.EXIT_IO == 1
    assert prefs_cli.EXIT_VALIDATION == 2
    assert prefs_cli.EXIT_MIGRATION == 3
    assert prefs_cli.EXIT_MALFORMED_YAML == 4


# ---------------------------------------------------------------------------
# `load` subcommand
# ---------------------------------------------------------------------------


def test_load_missing_file_returns_defaults(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.yaml"
    result = _run_cli("load", "--path", str(missing))
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "prefs" in payload
    assert "warnings" in payload
    assert payload["prefs"]["version"] >= 1
    assert isinstance(payload["warnings"], list)
    assert payload["warnings"] == []
    # Defaults include every schema key:
    for key in (
        "headline_count",
        "data_quality_checks",
        "outlier_methods",
        "trend_alpha",
    ):
        assert key in payload["prefs"]


def test_load_valid_prefs_file_roundtrips(tmp_path: Path) -> None:
    import yaml
    import _shared.prefs as prefs_mod

    path = tmp_path / "preferences.yaml"
    payload = dict(prefs_mod.DEFAULTS)
    payload["headline_count"] = 7
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")

    result = _run_cli("load", "--path", str(path))
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert out["prefs"]["headline_count"] == 7


def test_load_versionless_file_is_migrated_and_rewritten(
    tmp_path: Path,
) -> None:
    # AN-44: no version key → treat as v1 AND rewrite the file with
    # version: 1 so the next run sees it explicitly.
    path = tmp_path / "preferences.yaml"
    path.write_text("headline_count: 5\n", encoding="utf-8")

    result = _run_cli("load", "--path", str(path))
    assert result.returncode == 0, result.stderr
    # File is rewritten with version.
    assert "version" in path.read_text(encoding="utf-8")


def test_load_malformed_yaml_exits_4(tmp_path: Path) -> None:
    path = tmp_path / "preferences.yaml"
    path.write_text("headline_count: [unclosed\n", encoding="utf-8")

    result = _run_cli("load", "--path", str(path))
    assert result.returncode == 4, (
        f"expected exit 4 for malformed YAML, got {result.returncode}; "
        f"stderr={result.stderr!r}"
    )
    assert "ERROR" in result.stderr


def test_load_future_version_exits_3(tmp_path: Path) -> None:
    import _shared.prefs as prefs_mod

    path = tmp_path / "preferences.yaml"
    path.write_text(
        f"version: {prefs_mod.CURRENT_VERSION + 99}\nheadline_count: 5\n",
        encoding="utf-8",
    )

    result = _run_cli("load", "--path", str(path))
    assert result.returncode == 3, result.stderr
    assert "ERROR" in result.stderr


def test_load_out_of_range_exits_2(tmp_path: Path) -> None:
    # headline_count must be in [3, 10]; 99 is outside.
    import _shared.prefs as prefs_mod

    path = tmp_path / "preferences.yaml"
    path.write_text(
        f"version: {prefs_mod.CURRENT_VERSION}\nheadline_count: 99\n",
        encoding="utf-8",
    )

    result = _run_cli("load", "--path", str(path))
    assert result.returncode == 2, result.stderr
    assert "ERROR" in result.stderr


# ---------------------------------------------------------------------------
# `save` subcommand
# ---------------------------------------------------------------------------


def test_save_writes_valid_prefs(tmp_path: Path) -> None:
    import _shared.prefs as prefs_mod

    path = tmp_path / "preferences.yaml"
    prefs = dict(prefs_mod.DEFAULTS)
    prefs["headline_count"] = 8

    result = _run_cli("save", "--path", str(path), "--prefs-json", json.dumps(prefs))
    assert result.returncode == 0, result.stderr
    # Round-trip: reload via the same CLI and confirm the written value.
    reload_result = _run_cli("load", "--path", str(path))
    assert reload_result.returncode == 0
    assert json.loads(reload_result.stdout)["prefs"]["headline_count"] == 8


def test_save_rejects_invalid_prefs_exit_2(tmp_path: Path) -> None:
    import _shared.prefs as prefs_mod

    path = tmp_path / "preferences.yaml"
    prefs = dict(prefs_mod.DEFAULTS)
    prefs["headline_count"] = 1  # below floor 3
    result = _run_cli("save", "--path", str(path), "--prefs-json", json.dumps(prefs))
    assert result.returncode == 2, result.stderr
    assert "ERROR" in result.stderr
    assert not path.exists(), (
        "file must not exist when validation fails — save() is gated before "
        "any byte hits disk"
    )


def test_save_io_failure_exits_1(tmp_path: Path) -> None:
    import _shared.prefs as prefs_mod

    # Parent exists but is read-only — save() must fail at write time with
    # exit 1 (I/O), not exit 2 (validation).
    ro_dir = tmp_path / "readonly"
    ro_dir.mkdir()
    path = ro_dir / "preferences.yaml"
    try:
        ro_dir.chmod(0o500)  # r-x only; write forbidden
        prefs = dict(prefs_mod.DEFAULTS)
        result = _run_cli(
            "save", "--path", str(path), "--prefs-json", json.dumps(prefs)
        )
        # mkdir(exist_ok=True) on the read-only dir returns 0 (dir exists),
        # so the failure surfaces at the tmp write inside save().
        assert result.returncode == 1, (
            f"expected I/O exit 1 on read-only parent, got {result.returncode}; "
            f"stderr={result.stderr!r}"
        )
        assert "ERROR" in result.stderr
    finally:
        # Restore so pytest can clean up tmp_path.
        ro_dir.chmod(0o700)


def test_save_rejects_malformed_prefs_json(tmp_path: Path) -> None:
    path = tmp_path / "preferences.yaml"
    result = _run_cli("save", "--path", str(path), "--prefs-json", "{not json")
    assert result.returncode == 2, result.stderr
    assert "ERROR" in result.stderr
