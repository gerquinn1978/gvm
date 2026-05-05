"""Schema-versioning helper for cross-cutting Markdown artefacts (ADR-007).

Every cross-cutting GVM artefact (STUBS.md, impact-map.md, boundaries.md,
risks/risk-assessment.md, calibration.md, .gvm-track2-adopted) carries a
`schema_version: <int>` in YAML frontmatter. This module loads the file,
verifies the version is one this code can read, and returns a frozen
:class:`LoadedArtefact`. Migrations across versions are explicit, never silent.

This module knows nothing about the body shape of any specific artefact —
parsers in P7-C02..P7-C06 own that responsibility.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CURRENT_SCHEMA_VERSIONS: dict[str, int] = {
    "stubs": 1,
    "impact_map": 1,
    "boundaries": 1,
    "risk_assessment": 1,
    "calibration": 1,
    "gvm_track2_adopted": 1,
}


class SchemaError(Exception):
    """Base for all schema-helper failures."""


class MissingFrontmatterError(SchemaError):
    """Artefact does not start with a `---` line, or frontmatter is unterminated."""


class MissingSchemaVersionError(SchemaError):
    """Frontmatter is present but `schema_version` is missing or not an int."""


class UnknownArtefactError(SchemaError):
    """Caller asked for an artefact name not in :data:`CURRENT_SCHEMA_VERSIONS`."""


class SchemaTooNewError(SchemaError):
    """File's schema_version is newer than this code knows how to read."""


@dataclass(frozen=True)
class LoadedArtefact:
    schema_version: int
    body: str
    frontmatter: dict[str, Any] = field(default_factory=dict)


def load_with_schema(path: str | os.PathLike[str], artefact: str) -> LoadedArtefact:
    """Load *path* and verify its schema_version is readable for *artefact*.

    Older schema_versions are accepted (consumers handle migration explicitly
    per ADR-007). Newer versions raise :class:`SchemaTooNewError`.
    """
    if artefact not in CURRENT_SCHEMA_VERSIONS:
        raise UnknownArtefactError(
            f"unknown artefact {artefact!r}; "
            f"known artefacts: {sorted(CURRENT_SCHEMA_VERSIONS)}"
        )

    p = Path(path)
    text = p.read_text(encoding="utf-8")

    frontmatter, body = _split_frontmatter(text, p)
    schema_version = _extract_schema_version(frontmatter, p)

    known = CURRENT_SCHEMA_VERSIONS[artefact]
    if schema_version > known:
        raise SchemaTooNewError(
            f"{p}: artefact {artefact!r} has schema_version={schema_version}, "
            f"highest known is {known}; bump the helper and ship a migration"
        )

    return LoadedArtefact(
        schema_version=schema_version,
        body=body,
        frontmatter=frontmatter,
    )


def _split_frontmatter(text: str, path: Path) -> tuple[dict[str, Any], str]:
    lines = text.splitlines(keepends=False)
    if not lines or lines[0].strip() != "---":
        raise MissingFrontmatterError(f"{path}: file must start with '---' frontmatter")

    closing_index: int | None = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closing_index = i
            break
    if closing_index is None:
        raise MissingFrontmatterError(f"{path}: frontmatter '---' terminator not found")

    raw_fm = "\n".join(lines[1:closing_index])
    body = "\n".join(lines[closing_index + 1 :])
    return _parse_frontmatter(raw_fm, path), body


def _parse_frontmatter(raw: str, path: Path) -> dict[str, Any]:
    """Parse a *minimal* `key: value` YAML subset.

    The helper deliberately avoids a YAML dependency: cross-cutting artefacts
    keep frontmatter simple (scalar keys → ints or strings). Quoted strings are
    handled (single or double quotes); unquoted values are parsed as int when
    possible, else stripped string. Lines without a colon raise.
    """
    fm: dict[str, Any] = {}
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise MissingFrontmatterError(
                f"{path}: malformed frontmatter line: {raw_line!r}"
            )
        key, _, value = line.partition(":")
        fm[key.strip()] = _coerce_scalar(value.strip())
    return fm


def _coerce_scalar(value: str) -> Any:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        return value


def _extract_schema_version(frontmatter: dict[str, Any], path: Path) -> int:
    if "schema_version" not in frontmatter:
        raise MissingSchemaVersionError(
            f"{path}: frontmatter missing 'schema_version' key"
        )
    raw = frontmatter.pop("schema_version")
    if not isinstance(raw, int) or isinstance(raw, bool):
        raise MissingSchemaVersionError(
            f"{path}: 'schema_version' must be int, got {type(raw).__name__} ({raw!r})"
        )
    return raw
