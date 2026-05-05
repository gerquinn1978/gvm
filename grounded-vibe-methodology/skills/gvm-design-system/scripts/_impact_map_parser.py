"""Parser for `impact-map.md` per cross-cutting ADR-005 and discovery ADR-302.

Public surface: :func:`load_impact_map`, :func:`serialise`,
:func:`validate_referential_integrity`, :class:`ImpactMap`, :class:`Goal`,
:class:`Actor`, :class:`Impact`, :class:`Deliverable`, :class:`ChangelogEntry`,
:class:`ImpactMapParseError`.

Schema-version handling is delegated to :mod:`_schema`. This module enforces
IM-2 (no implicit parent) via foreign-key checks only. IM-3 (Goal ambiguity
scan) is owned by P10-C03; IM-5 (changelog-per-revision) is owned by P10-C08.

Markdown column header → dataclass field mapping:
    Goals:        ID, Statement, Metric, Target, Deadline
                  → id, statement, metric, target, deadline
    Actors:       ID, Goal-ID, Name, Description
                  → id, goal_id, name, description
    Impacts:      ID, Actor-ID, Behavioural change, Direction
                  → id, actor_id, behavioural_change, direction
    Deliverables: ID, Impact-ID, Title, Type
                  → id, impact_id, title, type
    Changelog:    Date, Change, Rationale
                  → date, change, rationale
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from _schema import load_with_schema

GOALS_COLUMNS = ["ID", "Statement", "Metric", "Target", "Deadline"]
ACTORS_COLUMNS = ["ID", "Goal-ID", "Name", "Description"]
IMPACTS_COLUMNS = ["ID", "Actor-ID", "Behavioural change", "Direction"]
DELIVERABLES_COLUMNS = ["ID", "Impact-ID", "Title", "Type"]
DELIVERABLES_COLUMNS_WITH_RISKS = DELIVERABLES_COLUMNS + ["risks"]
CHANGELOG_COLUMNS = ["Date", "Change", "Rationale"]

# Discovery ADR-310 / RA-6: optional risks column on Deliverables. Codes are
# the initials of the four risk types in `_risk_validator.REQUIRED_SECTIONS`
# (Value, Usability, Feasibility, Viability — Va disambiguates from Value).
RISK_CODES_ORDER = ("V", "U", "F", "Va")
_VALID_RISK_CODES = frozenset(RISK_CODES_ORDER)

ID_PATTERNS = {
    "Goals": re.compile(r"^G-\d+$"),
    "Actors": re.compile(r"^A-\d+$"),
    "Impacts": re.compile(r"^I-\d+$"),
    "Deliverables": re.compile(r"^D-\d+$"),
}


class ImpactMapParseError(Exception):
    """Raised when impact-map.md body / table / row / FK is malformed."""


@dataclass(frozen=True)
class Goal:
    id: str
    statement: str
    metric: str
    target: str
    deadline: str


@dataclass(frozen=True)
class Actor:
    id: str
    goal_id: str
    name: str
    description: str


@dataclass(frozen=True)
class Impact:
    id: str
    actor_id: str
    behavioural_change: str
    direction: str


@dataclass(frozen=True)
class Deliverable:
    id: str
    impact_id: str
    title: str
    type: str
    risks: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ChangelogEntry:
    date: str
    change: str
    rationale: str


@dataclass(frozen=True)
class ImpactMap:
    goals: tuple[Goal, ...]
    actors: tuple[Actor, ...]
    impacts: tuple[Impact, ...]
    deliverables: tuple[Deliverable, ...]
    changelog: tuple[ChangelogEntry, ...]


# --- Public API ---


def load_impact_map(path: str | os.PathLike[str]) -> ImpactMap:
    artefact = load_with_schema(path, "impact_map")
    im = _parse_body(artefact.body, Path(path))
    validate_referential_integrity(im)
    return im


def serialise(im: ImpactMap) -> str:
    _assert_serialisable(im)
    out: list[str] = ["---", "schema_version: 1", "---", "# Impact Map", ""]
    out.append("## Goals")
    out.append(_table_row(GOALS_COLUMNS))
    out.append(_separator(GOALS_COLUMNS))
    for g in im.goals:
        out.append(_table_row([g.id, g.statement, g.metric, g.target, g.deadline]))
    out.append("")

    out.append("## Actors")
    out.append(_table_row(ACTORS_COLUMNS))
    out.append(_separator(ACTORS_COLUMNS))
    for a in im.actors:
        out.append(_table_row([a.id, a.goal_id, a.name, a.description]))
    out.append("")

    out.append("## Impacts")
    out.append(_table_row(IMPACTS_COLUMNS))
    out.append(_separator(IMPACTS_COLUMNS))
    for i in im.impacts:
        out.append(_table_row([i.id, i.actor_id, i.behavioural_change, i.direction]))
    out.append("")

    # ADR-310: emit the optional `risks` column only if at least one
    # deliverable carries risks. Back-compat: legacy 4-column maps keep their
    # 4-column rendering on round-trip.
    has_risks = any(d.risks for d in im.deliverables)
    deliv_columns = (
        DELIVERABLES_COLUMNS_WITH_RISKS if has_risks else DELIVERABLES_COLUMNS
    )
    out.append("## Deliverables")
    out.append(_table_row(deliv_columns))
    out.append(_separator(deliv_columns))
    for d in im.deliverables:
        row = [d.id, d.impact_id, d.title, d.type]
        if has_risks:
            row.append(_render_risks(d.risks))
        out.append(_table_row(row))

    if im.changelog:
        out.append("")
        out.append("## Changelog")
        out.append(_table_row(CHANGELOG_COLUMNS))
        out.append(_separator(CHANGELOG_COLUMNS))
        for c in im.changelog:
            out.append(_table_row([c.date, c.change, c.rationale]))

    return "\n".join(out) + "\n"


def validate_referential_integrity(im: ImpactMap) -> None:
    goal_ids = {g.id for g in im.goals}
    actor_ids = {a.id for a in im.actors}
    impact_ids = {i.id for i in im.impacts}

    for a in im.actors:
        if a.goal_id not in goal_ids:
            raise ImpactMapParseError(
                f"Actors[{a.id}] references unknown goal {a.goal_id}"
            )
    for i in im.impacts:
        if i.actor_id not in actor_ids:
            raise ImpactMapParseError(
                f"Impacts[{i.id}] references unknown actor {i.actor_id}"
            )
    for d in im.deliverables:
        if d.impact_id not in impact_ids:
            raise ImpactMapParseError(
                f"Deliverables[{d.id}] references unknown impact {d.impact_id}"
            )


# --- Internals ---


def _render_risks(risks: frozenset[str]) -> str:
    """Render a Deliverable's risks as ``"V, F"`` in canonical V/U/F/Va order.

    Defensive: if the caller has somehow constructed a Deliverable with a
    risk code outside ``_VALID_RISK_CODES`` (the parser path forbids it, but
    direct dataclass construction doesn't), refuse rather than emit a
    malformed cell. This keeps :func:`serialise` honest for callers who
    bypass :func:`load_impact_map`.
    """
    if not risks:
        return ""
    bad = sorted(c for c in risks if c not in _VALID_RISK_CODES)
    if bad:
        raise ImpactMapParseError(
            f"cannot serialise risks {bad!r}; valid codes are {list(RISK_CODES_ORDER)!r}"
        )
    return ", ".join(c for c in RISK_CODES_ORDER if c in risks)


def _table_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def _separator(columns: list[str]) -> str:
    return "|" + "|".join(["---"] * len(columns)) + "|"


def _assert_serialisable(im: ImpactMap) -> None:
    rows: list[tuple[str, str, str]] = []
    for g in im.goals:
        rows += [
            ("Goals", g.id, v) for v in (g.statement, g.metric, g.target, g.deadline)
        ]
    for a in im.actors:
        rows += [("Actors", a.id, v) for v in (a.goal_id, a.name, a.description)]
    for i in im.impacts:
        rows += [
            ("Impacts", i.id, v)
            for v in (i.actor_id, i.behavioural_change, i.direction)
        ]
    for d in im.deliverables:
        rows += [("Deliverables", d.id, v) for v in (d.impact_id, d.title, d.type)]
    for c in im.changelog:
        rows += [("Changelog", c.date, v) for v in (c.change, c.rationale)]
    for table, row_id, value in rows:
        if "|" in value or "\n" in value:
            raise ImpactMapParseError(
                f"cannot serialise: {table}[{row_id}] field contains '|' or newline ({value!r})"
            )


def _parse_body(body: str, path: Path) -> ImpactMap:
    lines = body.splitlines()

    if not any(line.strip() == "# Impact Map" for line in lines):
        raise ImpactMapParseError(f"{path}: missing '# Impact Map' heading in body")

    sections = _split_sections(lines)

    for required in ("Goals", "Actors", "Impacts", "Deliverables"):
        if required not in sections:
            raise ImpactMapParseError(
                f"{path}: missing required section '## {required}'"
            )

    goals_rows = _parse_table(sections["Goals"], GOALS_COLUMNS, "Goals", path)
    actors_rows = _parse_table(sections["Actors"], ACTORS_COLUMNS, "Actors", path)
    impacts_rows = _parse_table(sections["Impacts"], IMPACTS_COLUMNS, "Impacts", path)
    # Deliverables table accepts an optional 5th `risks` column (ADR-310).
    # Detect by reading the actual header row before strict-matching.
    delivs_columns = _detect_deliverables_columns(sections["Deliverables"], path)
    delivs_rows = _parse_table(
        sections["Deliverables"], delivs_columns, "Deliverables", path
    )

    goals = tuple(_to_goal(r, path) for r in goals_rows)
    actors = tuple(_to_actor(r, path) for r in actors_rows)
    impacts = tuple(_to_impact(r, path) for r in impacts_rows)
    deliverables = tuple(_to_deliverable(r, path) for r in delivs_rows)

    if "Changelog" in sections:
        cl_rows = _parse_table(
            sections["Changelog"],
            CHANGELOG_COLUMNS,
            "Changelog",
            path,
            allow_empty=True,
        )
        changelog = tuple(
            ChangelogEntry(date=r[0], change=r[1], rationale=r[2]) for r in cl_rows
        )
    else:
        changelog = ()

    _check_unique_ids(goals, "Goals")
    _check_unique_ids(actors, "Actors")
    _check_unique_ids(impacts, "Impacts")
    _check_unique_ids(deliverables, "Deliverables")

    return ImpactMap(
        goals=goals,
        actors=actors,
        impacts=impacts,
        deliverables=deliverables,
        changelog=changelog,
    )


def _split_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current_name: str | None = None
    current_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            if current_name is not None:
                sections[current_name] = current_lines
            current_name = stripped[3:].strip()
            current_lines = []
        elif current_name is not None:
            current_lines.append(line)
    if current_name is not None:
        sections[current_name] = current_lines
    return sections


def _parse_table(
    section_lines: list[str],
    expected_columns: list[str],
    section_name: str,
    path: Path,
    *,
    allow_empty: bool = False,
) -> list[list[str]]:
    header_idx = None
    for i, line in enumerate(section_lines):
        if line.lstrip().startswith("|"):
            header_idx = i
            break
    if header_idx is None:
        raise ImpactMapParseError(
            f"{path}: section '## {section_name}' has no markdown table"
        )

    headers = _split_row(section_lines[header_idx])
    if headers != expected_columns:
        raise ImpactMapParseError(
            f"{path}: section '## {section_name}' header columns {headers!r} "
            f"do not match expected {expected_columns!r}"
        )

    if header_idx + 1 >= len(section_lines) or not _is_separator_row(
        section_lines[header_idx + 1]
    ):
        raise ImpactMapParseError(
            f"{path}: section '## {section_name}' missing '|---|' separator row"
        )

    rows: list[list[str]] = []
    for raw in section_lines[header_idx + 2 :]:
        if not raw.strip():
            continue
        if not raw.lstrip().startswith("|"):
            break
        cells = _split_row(raw)
        if len(cells) != len(expected_columns):
            raise ImpactMapParseError(
                f"{path}: section '## {section_name}' row has {len(cells)} columns, "
                f"expected {len(expected_columns)}"
            )
        rows.append(cells)

    if not rows and not allow_empty:
        raise ImpactMapParseError(
            f"{path}: section '## {section_name}' has no rows (at least 1 required)"
        )

    return rows


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


def _check_id(value: str, table: str) -> None:
    if not ID_PATTERNS[table].match(value):
        raise ImpactMapParseError(
            f"{table}: ID {value!r} does not match required format"
        )


def _check_unique_ids(rows: tuple, table: str) -> None:
    seen: set[str] = set()
    for row in rows:
        if row.id in seen:
            raise ImpactMapParseError(f"{table}: duplicate ID {row.id!r}")
        seen.add(row.id)


def _to_goal(cells: list[str], path: Path) -> Goal:
    _check_id(cells[0], "Goals")
    return Goal(
        id=cells[0],
        statement=cells[1],
        metric=cells[2],
        target=cells[3],
        deadline=cells[4],
    )


def _to_actor(cells: list[str], path: Path) -> Actor:
    _check_id(cells[0], "Actors")
    return Actor(
        id=cells[0],
        goal_id=cells[1],
        name=cells[2],
        description=cells[3],
    )


def _to_impact(cells: list[str], path: Path) -> Impact:
    _check_id(cells[0], "Impacts")
    return Impact(
        id=cells[0],
        actor_id=cells[1],
        behavioural_change=cells[2],
        direction=cells[3],
    )


def _detect_deliverables_columns(section_lines: list[str], path: Path) -> list[str]:
    """Return ``DELIVERABLES_COLUMNS`` (4) or ``DELIVERABLES_COLUMNS_WITH_RISKS`` (5)
    based on the actual table header. Strict header match — no other shapes
    are accepted."""
    for line in section_lines:
        if line.lstrip().startswith("|"):
            headers = _split_row(line)
            if headers == DELIVERABLES_COLUMNS:
                return DELIVERABLES_COLUMNS
            if headers == DELIVERABLES_COLUMNS_WITH_RISKS:
                return DELIVERABLES_COLUMNS_WITH_RISKS
            raise ImpactMapParseError(
                f"{path}: section '## Deliverables' header columns {headers!r} "
                f"do not match {DELIVERABLES_COLUMNS!r} or "
                f"{DELIVERABLES_COLUMNS_WITH_RISKS!r}"
            )
    raise ImpactMapParseError(
        f"{path}: section '## Deliverables' has no markdown table"
    )


def _parse_risks_cell(cell: str, deliverable_id: str) -> frozenset[str]:
    if not cell.strip():
        return frozenset()
    codes = [c.strip() for c in cell.split(",") if c.strip()]
    bad = [c for c in codes if c not in _VALID_RISK_CODES]
    if bad:
        raise ImpactMapParseError(
            f"Deliverables[{deliverable_id}] has unknown risk code(s) {bad!r}; "
            f"valid codes are {list(RISK_CODES_ORDER)!r}"
        )
    return frozenset(codes)


def _to_deliverable(cells: list[str], path: Path) -> Deliverable:
    _check_id(cells[0], "Deliverables")
    risks = _parse_risks_cell(cells[4], cells[0]) if len(cells) == 5 else frozenset()
    return Deliverable(
        id=cells[0],
        impact_id=cells[1],
        title=cells[2],
        type=cells[3],
        risks=risks,
    )
