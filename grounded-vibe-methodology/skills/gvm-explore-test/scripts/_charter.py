"""Charter loader/validator for `/gvm-explore-test` (P11-C06).

Implements ADR-202: charter is a YAML-frontmatter document. The skill writes
a stub the practitioner fills in; on "Ready" the skill calls `load(path)`
which validates every required field and either returns a `Charter` or
raises `CharterError(field, reason)` naming the offending field.

The schema is the source-of-truth in ADR-202; field names here are locked.
Downstream chunks (P11-C07 defect intake, P11-C08 report writer) import
`Charter` and `CharterError` — do not rename.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

Tour = Literal["feature", "data", "money", "interruption", "configuration"]

_ALLOWED_TOURS: tuple[str, ...] = (
    "feature",
    "data",
    "money",
    "interruption",
    "configuration",
)
_ALLOWED_TIMEBOXES: tuple[int, ...] = (30, 60, 90)
_SESSION_ID_PATTERN = re.compile(r"^explore-\d{3}$")


@dataclass(frozen=True)
class Charter:
    """Validated charter. Field order and names match ADR-202 verbatim."""

    schema_version: int
    session_id: str
    mission: str
    timebox_minutes: int
    target: tuple[str, ...]
    tour: Tour
    runner: str


class CharterError(Exception):
    """Validation failure. Carries the offending field name and a reason."""

    def __init__(self, field: str, reason: str) -> None:
        super().__init__(f"charter field {field!r}: {reason}")
        self.field = field
        self.reason = reason


def load(path: Path) -> Charter:
    """Read frontmatter YAML at `path`, validate every ADR-202 rule, return a
    `Charter`. Raises `CharterError(field, reason)` on any violation."""
    if not path.exists():
        raise CharterError("path", f"charter file does not exist: {path}")

    text = path.read_text(encoding="utf-8")
    data = _extract_frontmatter(text)

    schema_version = _require(data, "schema_version", int)
    if schema_version != 1:
        raise CharterError(
            "schema_version",
            f"unsupported schema version {schema_version}; this validator handles version 1",
        )
    session_id = _require_session_id(data)
    mission = _require_nonempty_str(data, "mission")
    timebox_minutes = _require_timebox(data)
    target = _require_target_list(data)
    tour = _require_tour(data)
    runner = _require_runner(data)

    return Charter(
        schema_version=schema_version,
        session_id=session_id,
        mission=mission,
        timebox_minutes=timebox_minutes,
        target=target,
        tour=tour,
        runner=runner,
    )


# ----------------------------------------------------------------- frontmatter


def _extract_frontmatter(text: str) -> dict:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise CharterError("frontmatter", "missing leading '---' marker")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise CharterError("frontmatter", "missing closing '---' marker") from exc
    block = "\n".join(lines[1:end])
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError as exc:
        raise CharterError("frontmatter", f"invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise CharterError("frontmatter", "expected a mapping at top level")
    return data


# ----------------------------------------------------------------- per-field


def _require(data: dict, field: str, expected_type: type):
    if field not in data:
        raise CharterError(field, "missing required field")
    value = data[field]
    if not isinstance(value, expected_type) or isinstance(value, bool):
        raise CharterError(
            field, f"expected {expected_type.__name__}, got {type(value).__name__}"
        )
    return value


def _require_nonempty_str(data: dict, field: str) -> str:
    value = _require(data, field, str)
    if not value.strip():
        raise CharterError(field, "must be non-empty")
    return value


def _require_session_id(data: dict) -> str:
    value = _require(data, "session_id", str)
    if not _SESSION_ID_PATTERN.fullmatch(value):
        raise CharterError(
            "session_id",
            f"must match 'explore-NNN' with three-digit zero-padded NNN; got {value!r}",
        )
    return value


def _require_timebox(data: dict) -> int:
    value = _require(data, "timebox_minutes", int)
    if value not in _ALLOWED_TIMEBOXES:
        raise CharterError(
            "timebox_minutes",
            f"must be one of {_ALLOWED_TIMEBOXES}; got {value}",
        )
    return value


def _require_target_list(data: dict) -> tuple[str, ...]:
    if "target" not in data:
        raise CharterError("target", "missing required field")
    value = data["target"]
    if not isinstance(value, list):
        raise CharterError(
            "target", f"expected list of strings, got {type(value).__name__}"
        )
    if not value:
        raise CharterError("target", "must contain at least one entry")
    for i, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise CharterError("target", f"entry {i} must be a non-empty string")
    return tuple(value)


def _require_tour(data: dict) -> Tour:
    if "tour" not in data:
        raise CharterError(
            "tour",
            f"missing required field; allowed values: {', '.join(_ALLOWED_TOURS)}",
        )
    value = data["tour"]
    if not isinstance(value, str):
        raise CharterError(
            "tour",
            f"must be a string (one of: {', '.join(_ALLOWED_TOURS)}); got {type(value).__name__}",
        )
    normalised = value.strip().lower()
    if normalised not in _ALLOWED_TOURS:
        raise CharterError(
            "tour",
            f"must be one of: {', '.join(_ALLOWED_TOURS)} (case-insensitive bare word); got {value!r}",
        )
    return normalised  # type: ignore[return-value]


def _require_runner(data: dict) -> str:
    return _require_nonempty_str(data, "runner")
