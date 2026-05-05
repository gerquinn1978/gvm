"""Parser for `STUBS.md` per cross-cutting ADR-004 and honesty-triad ADR-101.

Public surface: :func:`load_stubs`, :func:`serialise`, :func:`check_expiry`,
:func:`validate_plan`, :class:`StubEntry`, :class:`StubsParseError`.

Schema-version handling is delegated to :mod:`_schema` — this module never
re-implements frontmatter or version checks. File-existence of stub paths is
NOT enforced here; the HS-1 chunk-handover gate in `/gvm-build` performs that
check (per honesty-triad ADR-101 path-existence note).

Markdown column header → dataclass field mapping:
    Path                  → path
    Reason                → reason
    Real-provider Plan    → real_provider_plan
    Owner                 → owner
    Expiry                → expiry  (parsed as datetime.date)
    Requirement           → requirement  (optional; requirements.md ID)
"""

from __future__ import annotations

import datetime as dt
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from _schema import load_with_schema

REQUIRED_COLUMNS = ["Path", "Reason", "Real-provider Plan", "Owner", "Expiry"]
OPTIONAL_COLUMNS = ["Requirement"]
EXPECTED_COLUMNS = REQUIRED_COLUMNS  # back-compat alias for callers
PATH_PREFIXES = ("stubs/", "walking-skeleton/stubs/")
MIN_REASON_LEN = 10
UNKNOWN_PLAN = "unknown"


class StubsParseError(Exception):
    """Raised when STUBS.md body / table / row is malformed."""


class DuplicatePathError(Exception):
    """Raised by :func:`append` when an entry's Path already exists."""

    def __init__(self, path: str) -> None:
        super().__init__(f"STUBS.md already contains an entry for path {path!r}")
        self.path = path


@dataclass(frozen=True)
class StubEntry:
    path: str
    reason: str
    real_provider_plan: str
    owner: str
    expiry: dt.date
    requirement: str | None = None


# --- Public API ---


def load_stubs(path: str | os.PathLike[str]) -> list[StubEntry]:
    artefact = load_with_schema(path, "stubs")
    return _parse_body(artefact.body, Path(path))


def serialise(entries: Iterable[StubEntry]) -> str:
    materialised = list(entries)
    include_requirement = any(e.requirement for e in materialised)
    columns = list(REQUIRED_COLUMNS) + (["Requirement"] if include_requirement else [])
    out: list[str] = ["---", "schema_version: 1", "---", "# Stubs", ""]
    out.append("| " + " | ".join(columns) + " |")
    out.append("|" + "|".join(["---"] * len(columns)) + "|")
    for e in materialised:
        _assert_serialisable(e)
        cells = [
            e.path,
            e.reason,
            e.real_provider_plan,
            e.owner,
            e.expiry.isoformat(),
        ]
        if include_requirement:
            cells.append(e.requirement or "")
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


def check_expiry(stubs: Iterable[StubEntry], today: dt.date) -> list[StubEntry]:
    """Return stubs whose expiry is strictly before *today*.

    Boundary: today == expiry → not expired (CI passes on the expiry day).
    """
    return [s for s in stubs if s.expiry < today]


def validate_plan(plan: str) -> bool:
    """HS-7 plan validity: True for concrete identifiers, False for ``"unknown"`` or empty."""
    if plan == UNKNOWN_PLAN:
        return False
    return bool(plan.strip())


def vv4_f_status(entries: Iterable[StubEntry]) -> tuple[str, str]:
    """HS-7 → VV-4(f) producer (honesty-triad ADR-101 + ADR-105 decision table).

    Walks ``entries`` once, returning the ``(status, evidence)`` tuple the
    verdict evaluator (``gvm_verdict.VerdictInputs.vv4_f``) consumes.

    - empty input → ``("NA", "no stubs registered")``
    - all plans concrete → ``("PASS", "no unknown plan")``
    - any plan unknown/empty → ``("FAIL", "real-provider plan: unknown (paths)")``
    """
    materialised = list(entries)
    if not materialised:
        return ("NA", "no stubs registered")
    bad = [e.path for e in materialised if not validate_plan(e.real_provider_plan)]
    if bad:
        return ("FAIL", f"real-provider plan: unknown ({', '.join(bad)})")
    return ("PASS", "no unknown plan")


def append(path: str | os.PathLike[str], entry: StubEntry) -> None:
    """Append *entry* to ``STUBS.md`` at *path* atomically.

    Validates the entry, refuses duplicate ``Path`` values, and writes via
    tmp + rename so a partial write never overwrites the original (per
    honesty-triad spec, ADR-101 family).

    Raises:
        FileNotFoundError: if ``path`` does not exist.
        DuplicatePathError: if an existing entry has the same ``Path``.
        StubsParseError: if *entry* contains pipe or newline characters.
    """
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"STUBS.md not found at {target}")

    _assert_serialisable(entry)
    _assert_appendable(entry)

    existing = load_stubs(target)
    if any(e.path == entry.path for e in existing):
        raise DuplicatePathError(entry.path)

    new_text = serialise([*existing, entry])

    parent = target.parent
    fd, tmp_name = tempfile.mkstemp(
        prefix=target.name + ".", suffix=".tmp", dir=str(parent)
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(new_text)
        os.replace(tmp_path, target)
    except BaseException:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


# --- Internals ---


def _assert_appendable(e: StubEntry) -> None:
    """Mirror the row-load validation: any constraint `_row_to_entry`
    enforces on parsed rows must hold for new entries too. Otherwise
    `append` writes a row that cannot be re-loaded."""
    if not any(e.path.startswith(p) for p in PATH_PREFIXES):
        raise StubsParseError(
            f"path {e.path!r} must start with one of {PATH_PREFIXES}"
        )
    if len(e.reason) < MIN_REASON_LEN:
        raise StubsParseError(
            f"reason must be ≥ {MIN_REASON_LEN} chars, got {e.reason!r}"
        )
    if not e.real_provider_plan:
        raise StubsParseError("real_provider_plan must be non-empty")
    if not e.owner:
        raise StubsParseError("owner must be non-empty")


def _assert_serialisable(e: StubEntry) -> None:
    fields = [
        ("path", e.path),
        ("reason", e.reason),
        ("real_provider_plan", e.real_provider_plan),
        ("owner", e.owner),
    ]
    if e.requirement is not None:
        fields.append(("requirement", e.requirement))
    for field_name, value in fields:
        if "|" in value or "\n" in value:
            raise StubsParseError(
                f"cannot serialise: field {field_name!r} contains '|' or newline ({value!r})"
            )


def _parse_body(body: str, path: Path) -> list[StubEntry]:
    lines = body.splitlines()

    if not any(line.strip() == "# Stubs" for line in lines):
        raise StubsParseError(f"{path}: missing '# Stubs' heading in body")

    header_idx = _find_table_header(lines)
    if header_idx is None:
        raise StubsParseError(f"{path}: no markdown table found after '# Stubs'")

    headers = _split_row(lines[header_idx])
    if headers != REQUIRED_COLUMNS and headers != REQUIRED_COLUMNS + OPTIONAL_COLUMNS:
        raise StubsParseError(
            f"{path}: table header columns {headers!r} do not match required "
            f"{REQUIRED_COLUMNS!r} (with optional trailing {OPTIONAL_COLUMNS!r})"
        )
    has_requirement_column = len(headers) == len(REQUIRED_COLUMNS) + 1

    if header_idx + 1 >= len(lines) or not _is_separator_row(lines[header_idx + 1]):
        raise StubsParseError(f"{path}: table header missing '|---|' separator row")

    expected_cell_count = len(headers)
    entries: list[StubEntry] = []
    for n, raw in enumerate(lines[header_idx + 2 :], start=header_idx + 3):
        if not raw.strip():
            continue
        if not raw.lstrip().startswith("|"):
            break
        cells = _split_row(raw)
        if len(cells) != expected_cell_count:
            raise StubsParseError(
                f"{path}: row at line {n} has {len(cells)} columns, expected {expected_cell_count}"
            )
        entries.append(_row_to_entry(cells, path, n, has_requirement_column))

    return entries


def _find_table_header(lines: list[str]) -> int | None:
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("| Path "):
            return i
    return None


def _is_separator_row(line: str) -> bool:
    cells = _split_row(line)
    return all(set(c.strip()) <= {"-", ":"} and "-" in c for c in cells)


def _split_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _row_to_entry(
    cells: list[str], path: Path, line_no: int, has_requirement_column: bool
) -> StubEntry:
    if has_requirement_column:
        raw_path, reason, plan, owner, expiry_str, requirement_raw = cells
        requirement: str | None = requirement_raw or None
    else:
        raw_path, reason, plan, owner, expiry_str = cells
        requirement = None

    if not any(raw_path.startswith(prefix) for prefix in PATH_PREFIXES):
        raise StubsParseError(
            f"{path}:{line_no}: path {raw_path!r} must start with {PATH_PREFIXES}"
        )

    if len(reason) < MIN_REASON_LEN:
        raise StubsParseError(
            f"{path}:{line_no}: reason must be ≥ {MIN_REASON_LEN} chars, got {reason!r}"
        )

    if not plan:
        raise StubsParseError(f"{path}:{line_no}: real-provider plan must be non-empty")

    if not owner:
        raise StubsParseError(f"{path}:{line_no}: owner must be non-empty")

    try:
        expiry = dt.date.fromisoformat(expiry_str)
    except ValueError as exc:
        raise StubsParseError(
            f"{path}:{line_no}: expiry {expiry_str!r} is not ISO-8601 (YYYY-MM-DD): {exc}"
        ) from exc

    return StubEntry(
        path=raw_path,
        reason=reason,
        real_provider_plan=plan,
        owner=owner,
        expiry=expiry,
        requirement=requirement,
    )
