"""Parser for `test/explore-NNN.md` per exploratory ADR-206.

Frontmatter `schema_version: 1`. Five H2 sections in order:
``## Charter``, ``## Session Log``, ``## Defects``, ``## Observations``,
``## Overall Assessment``.

Charter contains a fenced YAML block (scalar keys → ints/strings). Defects are
``### D-N: <title>`` blocks with labelled lines (Severity, Tour, Given, When,
Then, Reproduction, optional Stub-path). Observations are ``### O-N: <title>``
blocks with the same shape minus Severity, with a ``**Note:**`` final field.

`Stub-path` (markdown header) maps to `stub_path` (dataclass field). When a
STUBS.md path is provided, ``in_stub_path`` is True iff the defect's stub_path
matches a STUBS.md entry; otherwise False.

Public surface: :func:`load_explore`, :class:`ExploreReport`,
:class:`ExploreDefect`, :class:`ObservationEntry`, :class:`ExploreParseError`.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from _schema import SchemaTooNewError
from _stubs_parser import load_stubs

CURRENT_EXPLORE_SCHEMA = 1
REQUIRED_SECTIONS = (
    "Charter",
    "Session Log",
    "Defects",
    "Observations",
    "Overall Assessment",
)
DEFECT_SEVERITIES = {"Critical", "Important", "Minor"}
DEFECT_HEADING_RE = re.compile(r"^###\s+(D-\d+):\s+(.+?)\s*$")
OBSERVATION_HEADING_RE = re.compile(r"^###\s+(O-\d+):\s+(.+?)\s*$")
LABELLED_FIELD_RE = re.compile(
    r"^\*\*(?P<label>[A-Za-z][A-Za-z\- ]*?):?\*\*\s*(?P<rest>.*)$"
)


class ExploreParseError(Exception):
    """Raised when explore-NNN.md body or block is malformed."""


@dataclass(frozen=True)
class ExploreDefect:
    id: str
    severity: str  # "Critical" | "Important" | "Minor"
    tour: str
    title: str
    given: str
    when: str
    then: str
    reproduction: str
    stub_path: str | None
    in_stub_path: bool


@dataclass(frozen=True)
class ObservationEntry:
    id: str
    title: str
    given: str
    when: str
    then: str
    note: str


@dataclass(frozen=True)
class ExploreReport:
    schema_version: int
    session_id: str
    runner: str | None
    charter: dict = field(default_factory=dict)
    defects: tuple[ExploreDefect, ...] = ()
    observations: tuple[ObservationEntry, ...] = ()


# --- Public API ---


def load_explore(
    report_path: str | os.PathLike[str],
    stubs_path: str | os.PathLike[str] | None = None,
) -> ExploreReport:
    p = Path(report_path)
    text = p.read_text(encoding="utf-8")
    schema_version, body = _split_frontmatter(text, p)

    if schema_version > CURRENT_EXPLORE_SCHEMA:
        raise SchemaTooNewError(
            f"{p}: explore schema_version={schema_version}, "
            f"highest known is {CURRENT_EXPLORE_SCHEMA}"
        )

    sections = _split_sections(body, p)

    charter = _parse_charter(sections["Charter"], p)
    session_id = _require_str(charter, "session_id", p)
    runner_raw = _require_str(charter, "runner", p)
    runner: str | None = None if runner_raw == "unassigned" else runner_raw

    defects = _parse_defects(sections["Defects"], p)
    observations = _parse_observations(sections["Observations"], p)

    if stubs_path is not None:
        stub_paths = {e.path for e in load_stubs(stubs_path)}
        defects = tuple(
            _with_in_stub_path(d, d.stub_path is not None and d.stub_path in stub_paths)
            for d in defects
        )

    return ExploreReport(
        schema_version=schema_version,
        session_id=session_id,
        runner=runner,
        charter=charter,
        defects=defects,
        observations=observations,
    )


# --- Frontmatter ---


def _split_frontmatter(text: str, path: Path) -> tuple[int, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ExploreParseError(f"{path}: file must start with '---' frontmatter")
    closing = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closing = i
            break
    if closing is None:
        raise ExploreParseError(f"{path}: frontmatter '---' terminator not found")
    fm = _parse_scalar_yaml("\n".join(lines[1:closing]), path)
    body = "\n".join(lines[closing + 1 :])
    if "schema_version" not in fm:
        raise ExploreParseError(f"{path}: frontmatter missing 'schema_version'")
    sv = fm["schema_version"]
    if not isinstance(sv, int) or isinstance(sv, bool):
        raise ExploreParseError(f"{path}: 'schema_version' must be int, got {sv!r}")
    return sv, body


def _parse_scalar_yaml(raw: str, path: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ExploreParseError(f"{path}: malformed YAML line: {raw_line!r}")
        key, _, value = line.partition(":")
        out[key.strip()] = _coerce_scalar(value.strip())
    return out


def _coerce_scalar(value: str) -> Any:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        return value


# --- Sections ---


def _split_sections(body: str, path: Path) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    buf: list[str] = []
    for line in body.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("## "):
            if current is not None:
                sections[current] = buf
            current = stripped[3:].strip()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = buf

    for required in REQUIRED_SECTIONS:
        if required not in sections:
            raise ExploreParseError(f"{path}: missing required '## {required}' section")
    return sections


# --- Charter ---


def _parse_charter(lines: list[str], path: Path) -> dict[str, Any]:
    in_block = False
    yaml_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            if not in_block:
                in_block = True
                continue
            break
        if in_block:
            yaml_lines.append(line)
    if not yaml_lines:
        raise ExploreParseError(f"{path}: Charter section has no fenced YAML block")
    return _parse_scalar_yaml("\n".join(yaml_lines), path)


def _require_str(charter: dict[str, Any], key: str, path: Path) -> str:
    if key not in charter:
        raise ExploreParseError(f"{path}: charter missing required key {key!r}")
    val = charter[key]
    if not isinstance(val, str) or not val:
        raise ExploreParseError(
            f"{path}: charter {key!r} must be non-empty string, got {val!r}"
        )
    return val


# --- Defect / Observation parsing ---


def _split_blocks(
    lines: list[str], heading_re: re.Pattern[str]
) -> list[tuple[str, str, list[str]]]:
    """Return list of (id, title, body_lines) for each ### block."""
    blocks: list[tuple[str, str, list[str]]] = []
    current: tuple[str, str, list[str]] | None = None
    for line in lines:
        m = heading_re.match(line)
        if m:
            if current is not None:
                blocks.append(current)
            current = (m.group(1), m.group(2), [])
        elif current is not None:
            current[2].append(line)
    if current is not None:
        blocks.append(current)
    return blocks


def _parse_labelled_fields(body: list[str]) -> dict[str, str]:
    """Parse labelled lines like ``**Severity:** Important`` and multi-line
    ``**Reproduction:**`` blocks. Lines after a label without a new label are
    appended to the previous label's value.
    """
    fields: dict[str, list[str]] = {}
    current_label: str | None = None
    for line in body:
        m = LABELLED_FIELD_RE.match(line.strip())
        if m:
            label = m.group("label").strip()
            rest = m.group("rest").strip()
            current_label = label
            fields.setdefault(label, [])
            if rest:
                fields[label].append(rest)
        elif current_label is not None:
            stripped = line.strip()
            if stripped:
                fields[current_label].append(stripped)
    return {k: "\n".join(v).strip() for k, v in fields.items()}


def _parse_defects(lines: list[str], path: Path) -> tuple[ExploreDefect, ...]:
    blocks = _split_blocks(lines, DEFECT_HEADING_RE)
    defects: list[ExploreDefect] = []
    for did, title, body in blocks:
        fields = _parse_labelled_fields(body)
        for required in ("Severity", "Tour", "Given", "When", "Then", "Reproduction"):
            if required not in fields or not fields[required]:
                raise ExploreParseError(
                    f"{path}: defect {did}: missing required field {required!r}"
                )
        severity = fields["Severity"]
        if severity not in DEFECT_SEVERITIES:
            raise ExploreParseError(
                f"{path}: defect {did}: severity {severity!r} not in {sorted(DEFECT_SEVERITIES)}"
            )
        stub_path = fields.get("Stub-path") or None
        defects.append(
            ExploreDefect(
                id=did,
                severity=severity,
                tour=fields["Tour"],
                title=title,
                given=fields["Given"],
                when=fields["When"],
                then=fields["Then"],
                reproduction=fields["Reproduction"],
                stub_path=stub_path,
                in_stub_path=False,
            )
        )
    return tuple(defects)


def _parse_observations(lines: list[str], path: Path) -> tuple[ObservationEntry, ...]:
    blocks = _split_blocks(lines, OBSERVATION_HEADING_RE)
    obs: list[ObservationEntry] = []
    for oid, title, body in blocks:
        fields = _parse_labelled_fields(body)
        for required in ("Tour", "Given", "When", "Then"):
            if required not in fields or not fields[required]:
                raise ExploreParseError(
                    f"{path}: observation {oid}: missing required field {required!r}"
                )
        obs.append(
            ObservationEntry(
                id=oid,
                title=title,
                given=fields["Given"],
                when=fields["When"],
                then=fields["Then"],
                note=fields.get("Note", ""),
            )
        )
    return tuple(obs)


def _with_in_stub_path(d: ExploreDefect, in_stub: bool) -> ExploreDefect:
    return ExploreDefect(
        id=d.id,
        severity=d.severity,
        tour=d.tour,
        title=d.title,
        given=d.given,
        when=d.when,
        then=d.then,
        reproduction=d.reproduction,
        stub_path=d.stub_path,
        in_stub_path=in_stub,
    )
