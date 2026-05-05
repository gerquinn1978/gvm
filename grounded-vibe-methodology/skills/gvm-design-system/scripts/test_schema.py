"""Tests for `_schema.py` — the cross-cutting schema-versioning helper (ADR-007).

These tests also serve as the base test pattern for downstream parser chunks
(P7-C02..P7-C06): use `tmp_path`, `pytest.mark.parametrize`, and
`pytest.raises(..., match=...)`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from _schema import (
    CURRENT_SCHEMA_VERSIONS,
    LoadedArtefact,
    MissingFrontmatterError,
    MissingSchemaVersionError,
    SchemaError,
    SchemaTooNewError,
    UnknownArtefactError,
    load_with_schema,
)


def _write(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


# --- Registry contents ---


def test_registry_has_expected_artefacts():
    assert set(CURRENT_SCHEMA_VERSIONS) == {
        "stubs",
        "impact_map",
        "boundaries",
        "risk_assessment",
        "calibration",
        "gvm_track2_adopted",
    }
    for name, version in CURRENT_SCHEMA_VERSIONS.items():
        assert isinstance(version, int) and version >= 1, name


# --- Happy path ---


def test_loads_valid_artefact_returning_loaded_artefact(tmp_path):
    f = _write(
        tmp_path / "stubs.md",
        "---\nschema_version: 1\nowner: alice\n---\n# Stubs\n\nbody here\n",
    )
    result = load_with_schema(f, "stubs")
    assert isinstance(result, LoadedArtefact)
    assert result.schema_version == 1
    assert result.frontmatter == {"owner": "alice"}
    assert result.body.startswith("# Stubs")
    assert "schema_version" not in result.body
    assert "---" not in result.body.splitlines()[0]


def test_accepts_path_as_string(tmp_path):
    f = _write(tmp_path / "x.md", "---\nschema_version: 1\n---\nbody\n")
    result = load_with_schema(str(f), "stubs")
    assert result.schema_version == 1


def test_loaded_artefact_is_frozen(tmp_path):
    f = _write(tmp_path / "x.md", "---\nschema_version: 1\n---\nbody\n")
    result = load_with_schema(f, "stubs")
    with pytest.raises((AttributeError, Exception)):
        result.schema_version = 2  # type: ignore[misc]


# --- Forward compatibility: older versions accepted ---


def test_older_schema_version_is_accepted(tmp_path):
    # Bump the registry mentally: pretend stubs is v1; any older (none yet) would still pass.
    # We simulate by asserting equal-to-current is accepted (the only "older or equal" case at v1).
    f = _write(tmp_path / "x.md", "---\nschema_version: 1\n---\nbody\n")
    result = load_with_schema(f, "stubs")
    assert result.schema_version == 1


# --- Failure modes ---


def test_missing_frontmatter_raises(tmp_path):
    f = _write(tmp_path / "x.md", "# No frontmatter here\n")
    with pytest.raises(MissingFrontmatterError, match=str(f)):
        load_with_schema(f, "stubs")


def test_missing_schema_version_raises(tmp_path):
    f = _write(tmp_path / "x.md", "---\nowner: alice\n---\nbody\n")
    with pytest.raises(MissingSchemaVersionError, match="schema_version"):
        load_with_schema(f, "stubs")


def test_non_int_schema_version_raises(tmp_path):
    f = _write(tmp_path / "x.md", '---\nschema_version: "one"\n---\nbody\n')
    with pytest.raises(MissingSchemaVersionError, match="int"):
        load_with_schema(f, "stubs")


def test_unknown_artefact_raises(tmp_path):
    f = _write(tmp_path / "x.md", "---\nschema_version: 1\n---\nbody\n")
    with pytest.raises(UnknownArtefactError, match="not_a_real_artefact"):
        load_with_schema(f, "not_a_real_artefact")


def test_schema_too_new_raises_with_versions_in_message(tmp_path):
    f = _write(tmp_path / "x.md", "---\nschema_version: 99\n---\nbody\n")
    with pytest.raises(SchemaTooNewError) as exc:
        load_with_schema(f, "stubs")
    msg = str(exc.value)
    assert "stubs" in msg
    assert "99" in msg
    assert str(CURRENT_SCHEMA_VERSIONS["stubs"]) in msg


def test_specific_errors_subclass_schema_error():
    for cls in (
        MissingFrontmatterError,
        MissingSchemaVersionError,
        UnknownArtefactError,
        SchemaTooNewError,
    ):
        assert issubclass(cls, SchemaError)


# --- Frontmatter terminator handling ---


def test_unterminated_frontmatter_raises(tmp_path):
    f = _write(tmp_path / "x.md", "---\nschema_version: 1\nbody never terminated\n")
    with pytest.raises(MissingFrontmatterError):
        load_with_schema(f, "stubs")


@pytest.mark.parametrize(
    "body, expected_error",
    [
        ("", MissingFrontmatterError),
        ("---\n---\nbody\n", MissingSchemaVersionError),
    ],
)
def test_failure_matrix(tmp_path, body, expected_error):
    f = _write(tmp_path / "x.md", body)
    with pytest.raises(expected_error):
        load_with_schema(f, "stubs")
