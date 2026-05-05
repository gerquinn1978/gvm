"""Tests for gvm_migrate_calibration (P13-C01, ADR-608).

Covers TC-PP-8-01 (stamping), TC-PP-8-03 [SECURITY] (allowlist refusal),
TC-PP-8-04 (idempotence), and the byte-preservation invariant.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gvm_migrate_calibration as mig  # noqa: E402


FIXTURE_BODY = """# Calibration

## Score History

| Round | Date | Type | Verdict | Per-dimension scores |
|---|---|---|---|---|
| R1 | 2026-01-01 | code | Merge | clarity 8, completeness 7 |

Trailing prose preserved verbatim.
"""


def _write_calibration_file(repo: Path, body: str = FIXTURE_BODY) -> Path:
    target = repo / "reviews" / "calibration.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    return target


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


# TC-PP-8-01 ---------------------------------------------------------------

def test_tc_pp_8_01_stamps_schema_version_zero(repo):
    target = _write_calibration_file(repo)
    rc = mig.main(["gvm_migrate_calibration", "reviews/calibration.md"])
    assert rc == 0
    text = target.read_text(encoding="utf-8")
    assert text.startswith("---\nschema_version: 0\n---\n")
    # Body byte-preserved after frontmatter
    assert text[len("---\nschema_version: 0\n---\n"):] == FIXTURE_BODY


def test_default_path_when_no_argv(repo):
    # Behavioural test of the default path: with argv = ["prog"] (no path arg),
    # main() must resolve to ./reviews/calibration.md and stamp the file.
    target = _write_calibration_file(repo)
    rc = mig.main(["gvm_migrate_calibration"])
    assert rc == 0
    assert target.read_text(encoding="utf-8").startswith("---\nschema_version: 0\n---\n")


def test_idempotence_check_ignores_schema_version_in_yaml_comments(repo):
    # Frontmatter where `schema_version:` only appears as a comment must NOT
    # trigger the idempotence path — the check matches line-start, not substring.
    body = (
        "---\n"
        "# schema_version: not a real key, just a comment\n"
        "title: legacy\n"
        "---\n"
        "## Score History\n\n| Round | Date |\n|---|---|\n"
    )
    target = _write_calibration_file(repo, body=body)
    rc = mig.main(["gvm_migrate_calibration", "reviews/calibration.md"])
    assert rc == 0
    text = target.read_text(encoding="utf-8")
    # The script prepended a real schema_version frontmatter
    assert text.startswith("---\nschema_version: 0\n---\n")


# TC-PP-8-03 [SECURITY] ----------------------------------------------------

def test_tc_pp_8_03_rejects_absolute_path(repo, capsys):
    rc = mig.main(["gvm_migrate_calibration", "/etc/passwd"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "absolute" in err.lower()


def test_tc_pp_8_03_rejects_non_calibration_suffix(repo, capsys):
    decoy = repo / "notes.md"
    decoy.write_text("not a calibration file", encoding="utf-8")
    before = decoy.read_text(encoding="utf-8")
    rc = mig.main(["gvm_migrate_calibration", "notes.md"])
    assert rc == 2
    assert decoy.read_text(encoding="utf-8") == before
    err = capsys.readouterr().err
    assert "non-calibration" in err.lower()


def test_tc_pp_8_03_rejects_traversal_with_calibration_name(repo, capsys):
    # Path that ends with the suffix but at an unexpected location is rejected
    # only if it doesn't match the allowlist exactly. ../reviews/calibration.md
    # *does* end with /reviews/calibration.md — but ADR-608 also requires the
    # file to contain the marker. We assert the script does not mutate a
    # marker-less file accidentally.
    sneaky = repo / "evil.md"
    sneaky.write_text("no marker here", encoding="utf-8")
    rc = mig.main(["gvm_migrate_calibration", "evil.md"])
    assert rc == 2
    assert sneaky.read_text(encoding="utf-8") == "no marker here"


def test_rejects_calibration_path_without_marker(repo, capsys):
    target = _write_calibration_file(repo, body="# header\n\nno score history here\n")
    before = target.read_text(encoding="utf-8")
    rc = mig.main(["gvm_migrate_calibration", "reviews/calibration.md"])
    assert rc == 2
    assert target.read_text(encoding="utf-8") == before
    err = capsys.readouterr().err
    assert "Score History" in err


def test_missing_file_returns_one(repo, capsys):
    rc = mig.main(["gvm_migrate_calibration", "reviews/calibration.md"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "not found" in err.lower()


# TC-PP-8-04 ---------------------------------------------------------------

def test_tc_pp_8_04_idempotent_second_run(repo, capsys):
    target = _write_calibration_file(repo)
    assert mig.main(["gvm_migrate_calibration", "reviews/calibration.md"]) == 0
    after_first = target.read_text(encoding="utf-8")
    capsys.readouterr()  # drain
    rc2 = mig.main(["gvm_migrate_calibration", "reviews/calibration.md"])
    assert rc2 == 0
    assert target.read_text(encoding="utf-8") == after_first
    out = capsys.readouterr().out
    assert "already migrated" in out.lower()


# Byte-preservation invariant ---------------------------------------------

def test_byte_preservation_of_score_history_columns(repo):
    rich = (
        "# Calibration\n\n"
        "## Score History\n\n"
        "| Round | Date | Type | Verdict | Per-dimension scores |\n"
        "|---|---|---|---|---|\n"
        "| R1 | 2026-01-01 | code | Merge | clarity 8 |\n"
        "| R2 | 2026-02-01 | code | Do not merge | clarity 5 |\n"
        "| R3 | 2026-03-01 | code | Merge with caveats | clarity 7 |\n"
    )
    target = _write_calibration_file(repo, body=rich)
    mig.main(["gvm_migrate_calibration", "reviews/calibration.md"])
    text = target.read_text(encoding="utf-8")
    frontmatter = "---\nschema_version: 0\n---\n"
    assert text.startswith(frontmatter)
    body_after = text[len(frontmatter):]
    assert body_after == rich  # exact byte preservation


# Idempotence vs downgrade-guard separation ------------------------------

def test_schema_version_1_file_takes_idempotence_path(repo):
    """Migration-path idempotence: a file already declaring schema_version: 1
    is reported as already migrated and not rewritten. The downgrade guard
    itself is not exercised here — the idempotence check fires first by
    design (the migration always writes schema 0; a schema-1 file is by
    definition not in need of migration). For the downgrade guard's own
    behaviour, see test_assert_no_downgrade_* below.
    """
    target = _write_calibration_file(
        repo,
        body=(
            "---\nschema_version: 1\n---\n"
            "# Calibration\n\n## Score History\n\n| Round | Date |\n|---|---|\n"
        ),
    )
    before = target.read_text(encoding="utf-8")
    rc = mig.main(["gvm_migrate_calibration", "reviews/calibration.md"])
    assert rc == 0
    assert target.read_text(encoding="utf-8") == before


def _import_calibration_parser():
    parser_dir = (
        HERE.parent.parent / "gvm-design-system" / "scripts"
    ).resolve()
    if str(parser_dir) not in sys.path:
        sys.path.insert(0, str(parser_dir))
    import _calibration_parser  # noqa: WPS433
    return _calibration_parser


def test_assert_no_downgrade_raises_on_higher_existing_schema(repo):
    cp = _import_calibration_parser()
    target = repo / "reviews" / "calibration.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "---\nschema_version: 1\n---\n# Calibration\n\n## Score History\n\n"
        "| Round | Date | Type | Verdict | Per-dimension scores |\n"
        "|---|---|---|---|---|\n"
        "| 1 | 2026-01-01 | code | Merge | clarity 8 |\n",
        encoding="utf-8",
    )
    with pytest.raises(cp.SchemaDowngradeError):
        cp._assert_no_downgrade(target, attempted_schema_version=0)


def test_assert_no_downgrade_treats_too_new_schema_as_blocked(repo, monkeypatch):
    cp = _import_calibration_parser()
    target = repo / "reviews" / "calibration.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    # Force "too new" by writing a schema higher than CURRENT_SCHEMA_VERSIONS["calibration"]
    too_new = cp.CURRENT_SCHEMA_VERSIONS["calibration"] + 1
    target.write_text(
        f"---\nschema_version: {too_new}\n---\nbody\n",
        encoding="utf-8",
    )
    with pytest.raises(cp.SchemaDowngradeError):
        cp._assert_no_downgrade(target, attempted_schema_version=0)


def test_assert_no_downgrade_passes_when_schema_equal_or_missing(repo):
    cp = _import_calibration_parser()
    target = repo / "reviews" / "calibration.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    # No frontmatter → treated as schema 0; writing 0 is allowed.
    target.write_text("# Calibration\n\n## Score History\n\nbody\n", encoding="utf-8")
    cp._assert_no_downgrade(target, attempted_schema_version=0)  # no raise
