"""Parser for `boundaries.md` per cross-cutting ADR-005 + walking-skeleton ADR-403.

Public surface: :func:`load_boundaries`, :func:`serialise`, :class:`Boundary`,
:class:`Boundaries`, :class:`ChangelogEntry`, :class:`BoundariesParseError`,
:class:`MalformedRowError`, :class:`DivergenceMissingError`.

Schema-version handling delegated to :mod:`_schema`. Markdown column headers
match dataclass field names exactly (snake_case) per ADR-403 — no translation
layer.

Cross-field invariant: when ``real_call_status == "wired_sandbox"``,
``production_sandbox_divergence`` MUST be non-empty AND not the literal
``"n/a"``; otherwise it MUST be exactly ``"n/a"``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from _schema import load_with_schema

EXPECTED_COLUMNS = [
    "name",
    "type",
    "chosen_provider",
    "real_call_status",
    "test_credentials_location",
    "cost_model",
    "sla_notes",
    "production_sandbox_divergence",
]
TYPE_ENUM = {
    "http_api",
    "database",
    "filesystem",
    "sdk",
    "queue",
    "email",
    "sms",
    "other",
}
STATUS_ENUM = {"wired", "wired_sandbox", "deferred_stub"}
NA = "n/a"
CHANGELOG_COLUMNS = ["Date", "Change", "Rationale"]
REQUIRED_NON_EMPTY = (
    "name",
    "type",
    "chosen_provider",
    "real_call_status",
    "test_credentials_location",
    "cost_model",
    "sla_notes",
)


class BoundariesParseError(Exception):
    """Base for boundaries parser errors."""


class MalformedRowError(BoundariesParseError):
    """Structural / enum / cross-field error other than divergence-missing."""


class DivergenceMissingError(BoundariesParseError):
    """Raised when a wired_sandbox row has divergence == 'n/a' or empty."""

    def __init__(self, boundary_name: str) -> None:
        super().__init__(
            f"Boundary {boundary_name!r}: real_call_status is 'wired_sandbox' but "
            f"production_sandbox_divergence is empty or 'n/a' — divergence note required"
        )
        self._boundary_name = boundary_name

    @property
    def boundary_name(self) -> str:
        return self._boundary_name


@dataclass(frozen=True)
class Boundary:
    name: str
    type: str
    chosen_provider: str
    real_call_status: str
    test_credentials_location: str
    cost_model: str
    sla_notes: str
    production_sandbox_divergence: str


@dataclass(frozen=True)
class ChangelogEntry:
    date: str
    change: str
    rationale: str


@dataclass(frozen=True)
class Boundaries:
    schema_version: int
    rows: tuple[Boundary, ...]
    changelog: tuple[ChangelogEntry, ...]


# --- Public API ---


def load_boundaries(path: str | os.PathLike[str]) -> Boundaries:
    artefact = load_with_schema(path, "boundaries")
    return _parse_body(artefact.body, Path(path), artefact.schema_version)


def serialise(b: Boundaries) -> str:
    _assert_serialisable(b)
    out: list[str] = [
        "---",
        f"schema_version: {b.schema_version}",
        "---",
        "# Boundaries",
        "",
    ]
    out.append("| " + " | ".join(EXPECTED_COLUMNS) + " |")
    out.append("|" + "|".join(["---"] * len(EXPECTED_COLUMNS)) + "|")
    for r in b.rows:
        out.append(
            "| "
            + " | ".join(
                [
                    r.name,
                    r.type,
                    r.chosen_provider,
                    r.real_call_status,
                    r.test_credentials_location,
                    r.cost_model,
                    r.sla_notes,
                    r.production_sandbox_divergence,
                ]
            )
            + " |"
        )
    if b.changelog:
        out.append("")
        out.append("## Changelog")
        out.append("| " + " | ".join(CHANGELOG_COLUMNS) + " |")
        out.append("|" + "|".join(["---"] * len(CHANGELOG_COLUMNS)) + "|")
        for c in b.changelog:
            out.append(f"| {c.date} | {c.change} | {c.rationale} |")
    return "\n".join(out) + "\n"


# --- Internals ---


def _assert_serialisable(b: Boundaries) -> None:
    for r in b.rows:
        for field_name in EXPECTED_COLUMNS:
            value = getattr(r, field_name)
            if "|" in value or "\n" in value:
                raise MalformedRowError(
                    f"cannot serialise: row {r.name!r} field {field_name!r} contains '|' or newline ({value!r})"
                )
    for c in b.changelog:
        for v in (c.date, c.change, c.rationale):
            if "|" in v or "\n" in v:
                raise MalformedRowError(
                    f"cannot serialise: changelog field contains '|' or newline ({v!r})"
                )


def _parse_body(body: str, path: Path, schema_version: int) -> Boundaries:
    lines = body.splitlines()

    if not any(line.strip() == "# Boundaries" for line in lines):
        raise MalformedRowError(f"{path}: missing '# Boundaries' heading in body")

    main_table_start = None
    changelog_start = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if main_table_start is None and stripped.startswith("| name "):
            main_table_start = i
        elif stripped == "## Changelog":
            changelog_start = i

    if main_table_start is None:
        raise MalformedRowError(f"{path}: no boundaries table found")

    main_end = changelog_start if changelog_start is not None else len(lines)
    rows = _parse_main_table(lines[main_table_start:main_end], path)

    changelog: tuple[ChangelogEntry, ...] = ()
    if changelog_start is not None:
        changelog = _parse_changelog(lines[changelog_start + 1 :], path)

    _check_unique_names(rows)
    return Boundaries(schema_version=schema_version, rows=rows, changelog=changelog)


def _parse_main_table(lines: list[str], path: Path) -> tuple[Boundary, ...]:
    headers = _split_row(lines[0])
    if headers != EXPECTED_COLUMNS:
        raise MalformedRowError(
            f"{path}: boundaries table header columns {headers!r} do not match expected {EXPECTED_COLUMNS!r}"
        )
    if len(lines) < 2 or not _is_separator_row(lines[1]):
        raise MalformedRowError(
            f"{path}: boundaries table missing '|---|' separator row"
        )

    rows: list[Boundary] = []
    for raw in lines[2:]:
        if not raw.strip():
            continue
        if not raw.lstrip().startswith("|"):
            break
        cells = _split_row(raw)
        if len(cells) != len(EXPECTED_COLUMNS):
            raise MalformedRowError(
                f"{path}: boundaries row has {len(cells)} columns, expected {len(EXPECTED_COLUMNS)}"
            )
        rows.append(_row_to_boundary(cells, path))
    return tuple(rows)


def _row_to_boundary(cells: list[str], path: Path) -> Boundary:
    record = dict(zip(EXPECTED_COLUMNS, cells))

    for field_name in REQUIRED_NON_EMPTY:
        if not record[field_name]:
            raise MalformedRowError(
                f"{path}: row {record.get('name', '?')!r} field {field_name!r} is empty"
            )

    if record["type"] not in TYPE_ENUM:
        raise MalformedRowError(
            f"{path}: row {record['name']!r} has invalid type {record['type']!r} "
            f"(expected one of {sorted(TYPE_ENUM)})"
        )
    if record["real_call_status"] not in STATUS_ENUM:
        raise MalformedRowError(
            f"{path}: row {record['name']!r} has invalid real_call_status "
            f"{record['real_call_status']!r} (expected one of {sorted(STATUS_ENUM)})"
        )

    divergence = record["production_sandbox_divergence"]
    if record["real_call_status"] == "wired_sandbox":
        if divergence == NA or divergence == "":
            raise DivergenceMissingError(record["name"])
    else:
        if divergence != NA:
            raise MalformedRowError(
                f"{path}: row {record['name']!r} has real_call_status "
                f"{record['real_call_status']!r} but production_sandbox_divergence "
                f"{divergence!r} — must be 'n/a' for non-sandbox rows"
            )

    return Boundary(**record)


def _parse_changelog(lines: list[str], path: Path) -> tuple[ChangelogEntry, ...]:
    header_idx = None
    for i, line in enumerate(lines):
        if line.lstrip().startswith("| Date "):
            header_idx = i
            break
    if header_idx is None:
        raise MalformedRowError(f"{path}: '## Changelog' present but no table found")

    headers = _split_row(lines[header_idx])
    if headers != CHANGELOG_COLUMNS:
        raise MalformedRowError(
            f"{path}: changelog header {headers!r} does not match {CHANGELOG_COLUMNS!r}"
        )
    if header_idx + 1 >= len(lines) or not _is_separator_row(lines[header_idx + 1]):
        raise MalformedRowError(f"{path}: changelog missing separator row")

    entries: list[ChangelogEntry] = []
    for raw in lines[header_idx + 2 :]:
        if not raw.strip():
            continue
        if not raw.lstrip().startswith("|"):
            break
        cells = _split_row(raw)
        if len(cells) != len(CHANGELOG_COLUMNS):
            raise MalformedRowError(f"{path}: changelog row has wrong column count")
        entries.append(
            ChangelogEntry(date=cells[0], change=cells[1], rationale=cells[2])
        )
    return tuple(entries)


def _check_unique_names(rows: tuple[Boundary, ...]) -> None:
    seen: set[str] = set()
    for r in rows:
        if r.name in seen:
            raise MalformedRowError(f"duplicate boundary name: {r.name!r}")
        seen.add(r.name)


def _is_separator_row(line: str) -> bool:
    cells = _split_row(line)
    return bool(cells) and all(set(c.strip()) <= {"-", ":"} and "-" in c for c in cells)


def _split_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]
