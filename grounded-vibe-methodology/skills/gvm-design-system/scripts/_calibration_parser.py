"""Parser for `reviews/calibration.md` per pipeline-propagation ADR-604.

Dual-mode: schema 0 (pre-Track-P, no frontmatter OR `schema_version: 0`,
5-column score history, no Recurring Findings) and schema 1 (frontmatter
`schema_version: 1`, 6-column score history with `verdict_under_schema`,
optional Recurring Findings).

Public surface: :func:`load_calibration`, :func:`serialise`,
:func:`write_calibration`, :func:`map_v0_to_v1`, :class:`Calibration`,
:class:`ScoreHistoryRow`, :class:`RecurringFinding`, :class:`Verdict`,
:class:`CalibrationParseError`, :class:`UnknownVerdictError`,
:class:`SchemaDowngradeError`.
"""

from __future__ import annotations

import enum
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from _schema import (
    CURRENT_SCHEMA_VERSIONS,
    MissingFrontmatterError,
    MissingSchemaVersionError,
    SchemaTooNewError,
    load_with_schema,
)

V0_SCORE_COLUMNS = ["Round", "Date", "Type", "Verdict", "Per-dimension scores"]
V1_SCORE_COLUMNS = [
    "Round",
    "Date",
    "Type",
    "Verdict",
    "verdict_under_schema",
    "Per-dimension scores",
]
RECURRING_COLUMNS = ["Signature", "First Round", "Last Round", "Severity History"]


class Verdict(enum.Enum):
    SHIP_READY = "Ship-ready"
    DEMO_READY = "Demo-ready"
    NOT_SHIPPABLE = "Not shippable"


class CalibrationParseError(Exception):
    """Base for calibration parser errors."""


class UnknownVerdictError(CalibrationParseError):
    """Raised by map_v0_to_v1 when verdict text is not recognized."""

    def __init__(self, text: str) -> None:
        super().__init__(f"unknown v0 verdict text: {text!r}")
        self._text = text

    @property
    def text(self) -> str:
        return self._text


class SchemaDowngradeError(CalibrationParseError):
    """Raised by write_calibration when new schema_version < existing."""


@dataclass(frozen=True)
class ScoreHistoryRow:
    round: int
    date: str
    type: str
    verdict: str
    verdict_under_schema: int | None
    per_dimension_scores: str


@dataclass(frozen=True)
class RecurringFinding:
    signature: str
    first_round: int
    last_round: int
    severity_history: str


@dataclass(frozen=True)
class Calibration:
    schema_version: int
    score_history: tuple[ScoreHistoryRow, ...]
    recurring_findings: tuple[RecurringFinding, ...]
    trailing_body: str


# --- Public API ---


def map_v0_to_v1(verdict_text: str) -> Verdict | None:
    table: dict[str, Verdict | None] = {
        "Pass": Verdict.SHIP_READY,
        "Pass with gaps": None,
        "Do not release": Verdict.NOT_SHIPPABLE,
    }
    if verdict_text in table:
        return table[verdict_text]
    raise UnknownVerdictError(verdict_text)


def load_calibration(path: str | os.PathLike[str]) -> Calibration:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return _parse_body(text, schema_version=0, path=p)

    try:
        artefact = load_with_schema(p, "calibration")
    except MissingFrontmatterError:
        return _parse_body(text, schema_version=0, path=p)

    return _parse_body(artefact.body, schema_version=artefact.schema_version, path=p)


def serialise(c: Calibration) -> str:
    out: list[str] = []
    if c.schema_version >= 0:
        out.append("---")
        out.append(f"schema_version: {c.schema_version}")
        out.append("---")
    out.append("# Calibration")
    out.append("")
    out.append("## Score History")
    out.append("")

    if c.schema_version == 0:
        cols = V0_SCORE_COLUMNS
    else:
        cols = V1_SCORE_COLUMNS
    out.append("| " + " | ".join(cols) + " |")
    out.append("|" + "|".join(["---"] * len(cols)) + "|")
    for row in c.score_history:
        if c.schema_version == 0:
            cells = [
                str(row.round),
                row.date,
                row.type,
                row.verdict,
                row.per_dimension_scores,
            ]
        else:
            assert row.verdict_under_schema is not None, (
                "v1 row must carry verdict_under_schema"
            )
            cells = [
                str(row.round),
                row.date,
                row.type,
                row.verdict,
                str(row.verdict_under_schema),
                row.per_dimension_scores,
            ]
        out.append("| " + " | ".join(cells) + " |")

    if c.schema_version == 1:
        out.append("")
        out.append("## Recurring Findings")
        out.append("")
        out.append("| " + " | ".join(RECURRING_COLUMNS) + " |")
        out.append("|" + "|".join(["---"] * len(RECURRING_COLUMNS)) + "|")
        for f in c.recurring_findings:
            out.append(
                f"| {f.signature} | {f.first_round} | {f.last_round} | {f.severity_history} |"
            )

    if c.trailing_body:
        out.append("")
        out.append(c.trailing_body.rstrip("\n"))

    return "\n".join(out) + "\n"


def _assert_no_downgrade(
    path: str | os.PathLike[str], attempted_schema_version: int
) -> None:
    """Raise SchemaDowngradeError if writing `attempted_schema_version` to `path`
    would lower the file's existing schema_version. Single source of truth for
    the monotonicity guard (cross-cutting ADR-111). Called by `write_calibration`
    and by the one-time `gvm_migrate_calibration` script (ADR-608).

    Inspects only the frontmatter — does not fully parse the body. The migration
    script needs this guard against legacy files whose body shape may not match
    the current schema, so a full parse is the wrong tool here.
    """
    p = Path(path)
    if not p.exists():
        return
    text = p.read_text(encoding="utf-8")
    if not text.startswith("---"):
        existing_schema = 0
    else:
        try:
            artefact = load_with_schema(p, "calibration")
        except (MissingFrontmatterError, MissingSchemaVersionError):
            # Frontmatter present but no `schema_version:` key — treat as
            # unmigrated (schema 0). The migration's idempotence check has
            # already filtered files whose frontmatter actually declares a
            # schema_version.
            existing_schema = 0
        except SchemaTooNewError as exc:
            # File was written by a newer version. Any future schema is, by
            # definition, higher than `attempted_schema_version` (which the
            # migration always sets to 0, and `write_calibration` clamps to
            # the current schema). Refuse the write rather than silently
            # downgrading.
            raise SchemaDowngradeError(
                f"refusing to write schema_version {attempted_schema_version}: "
                f"existing file is from a newer schema ({exc})"
            ) from exc
        else:
            existing_schema = artefact.schema_version
    if attempted_schema_version < existing_schema:
        raise SchemaDowngradeError(
            f"refusing to write schema_version {attempted_schema_version} over existing "
            f"schema_version {existing_schema}"
        )


def write_calibration(path: str | os.PathLike[str], c: Calibration) -> None:
    p = Path(path)
    _assert_no_downgrade(p, c.schema_version)
    text = serialise(c)
    parent = p.parent if p.parent != Path("") else Path(".")
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        delete=False,
        dir=parent,
        prefix=p.name + ".",
        suffix=".tmp",
    ) as tmp:
        tmp.write(text)
        tmp_path = Path(tmp.name)
    tmp_path.replace(p)


# --- Internals ---


def _parse_body(text: str, schema_version: int, path: Path) -> Calibration:
    if schema_version > CURRENT_SCHEMA_VERSIONS["calibration"]:
        raise SchemaTooNewError(
            f"calibration schema_version {schema_version} > known max "
            f"{CURRENT_SCHEMA_VERSIONS['calibration']}"
        )

    body = _strip_frontmatter(text)
    sections = _split_sections(body.splitlines())

    if "Score History" not in sections:
        raise CalibrationParseError(f"{path}: missing '## Score History' section")

    if schema_version == 0:
        score_columns = V0_SCORE_COLUMNS
    else:
        score_columns = V1_SCORE_COLUMNS

    score_rows = _parse_table(
        sections["Score History"],
        score_columns,
        "Score History",
        path,
        allow_empty=True,
    )
    score_history = tuple(
        _to_score_row(cells, schema_version, path) for cells in score_rows
    )

    recurring: tuple[RecurringFinding, ...] = ()
    if schema_version == 1 and "Recurring Findings" in sections:
        rec_rows = _parse_table(
            sections["Recurring Findings"],
            RECURRING_COLUMNS,
            "Recurring Findings",
            path,
            allow_empty=True,
        )
        recurring = tuple(
            RecurringFinding(
                signature=r[0],
                first_round=_parse_int(r[1], "First Round", path),
                last_round=_parse_int(r[2], "Last Round", path),
                severity_history=r[3],
            )
            for r in rec_rows
        )

    trailing_body = _trailing_body(sections, schema_version)

    return Calibration(
        schema_version=schema_version,
        score_history=score_history,
        recurring_findings=recurring,
        trailing_body=trailing_body,
    )


def _strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\n") != "---":
        return text
    for i in range(1, len(lines)):
        if lines[i].rstrip("\n") == "---":
            return "".join(lines[i + 1 :])
    return text


def _split_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    buf: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            if current is not None:
                sections[current] = buf
            current = stripped[3:].strip()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = buf
    return sections


def _trailing_body(sections: dict[str, list[str]], schema_version: int) -> str:
    parsed = {"Score History"}
    if schema_version == 1:
        parsed.add("Recurring Findings")
    parts: list[str] = []
    for name, lines in sections.items():
        if name in parsed:
            continue
        parts.append(f"## {name}")
        parts.extend(lines)
    return "\n".join(parts).strip("\n")


def _parse_table(
    section_lines: list[str],
    expected_columns: list[str],
    section_name: str,
    path: Path,
    *,
    allow_empty: bool,
) -> list[list[str]]:
    header_idx = None
    for i, line in enumerate(section_lines):
        if line.lstrip().startswith("|"):
            header_idx = i
            break
    if header_idx is None:
        if allow_empty:
            return []
        raise CalibrationParseError(
            f"{path}: section '{section_name}' has no markdown table"
        )

    headers = _split_row(section_lines[header_idx])
    if headers != expected_columns:
        raise CalibrationParseError(
            f"{path}: section '{section_name}' header columns {headers!r} "
            f"do not match expected {expected_columns!r}"
        )
    if header_idx + 1 >= len(section_lines) or not _is_separator_row(
        section_lines[header_idx + 1]
    ):
        raise CalibrationParseError(
            f"{path}: section '{section_name}' missing '|---|' separator row"
        )

    rows: list[list[str]] = []
    for raw in section_lines[header_idx + 2 :]:
        if not raw.strip():
            continue
        if not raw.lstrip().startswith("|"):
            break
        cells = _split_row(raw)
        if len(cells) != len(expected_columns):
            raise CalibrationParseError(
                f"{path}: section '{section_name}' row has {len(cells)} columns, "
                f"expected {len(expected_columns)}"
            )
        rows.append(cells)
    return rows


def _to_score_row(cells: list[str], schema_version: int, path: Path) -> ScoreHistoryRow:
    if schema_version == 0:
        round_s, date, type_, verdict, scores = cells
        return ScoreHistoryRow(
            round=_parse_int(round_s, "Round", path),
            date=date,
            type=type_,
            verdict=verdict,
            verdict_under_schema=None,
            per_dimension_scores=scores,
        )
    round_s, date, type_, verdict, vus, scores = cells
    return ScoreHistoryRow(
        round=_parse_int(round_s, "Round", path),
        date=date,
        type=type_,
        verdict=verdict,
        verdict_under_schema=_parse_int(vus, "verdict_under_schema", path),
        per_dimension_scores=scores,
    )


def _parse_int(value: str, field_name: str, path: Path) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise CalibrationParseError(
            f"{path}: field {field_name!r} value {value!r} is not an integer"
        ) from exc


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
