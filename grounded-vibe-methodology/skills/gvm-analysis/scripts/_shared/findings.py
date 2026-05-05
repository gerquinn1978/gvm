"""Schema validator, skeleton builder, and atomic I/O for ``findings.json``.

Single source of truth for the inter-process contract between the analysis
engine and the renderer (cross-cutting ADR-006; full schema in analysis-engine
ADR-201). Breaking schema changes bump :data:`CURRENT_SCHEMA_VERSION`; the
renderer fails clearly on a mismatch.

Scope for P1-C02 (tracer bullet): top-level structural validation and a safe
write protocol. Field-level deep validation arrives in downstream chunks as
each section is populated. Helper ``patch_comprehension_questions`` lands in
P5-C01b.
"""

from __future__ import annotations

import errno
import json
import os
import re
from pathlib import Path
from typing import Any

from _shared.diagnostics import JargonError, ReferentialIntegrityError
from _shared.methodology import JARGON_FORBIDDEN

CURRENT_SCHEMA_VERSION: int = 1

# ADR-109: comprehension_questions has exactly three objects with exactly
# these three string fields. Single source of truth — tests and the wrapper
# import these constants.
COMPREHENSION_QUESTION_COUNT: int = 3
COMPREHENSION_QUESTION_FIELDS: tuple[str, ...] = (
    "question",
    "answer",
    "supporting_finding_id",
)

_REQUIRED_TOP_LEVEL: frozenset[str] = frozenset(
    {
        "schema_version",
        "provenance",
        "columns",
        "outliers",
        "duplicates",
        "time_series",
        "drivers",
        "headline_findings",
        "comprehension_questions",
        "drillthroughs",
    }
)


class SchemaValidationError(ValueError):
    """Raised when a ``findings.json`` document fails schema validation.

    Messages include enough context (expected value, actual value, missing key
    names) that the user-facing diagnostic layer (``_shared/diagnostics.py``,
    P2-C04) can format them into the ERROR/What/What-to-try block without
    additional parsing.
    """


class CrossVolumeWriteError(OSError):
    """Raised when ``write_atomic`` cannot rename across filesystems (EXDEV).

    ADR-209 (post-R3 Edit 3) requires this catch so the diagnostic layer can
    tell the user their ``--output-dir`` sits on a different volume from the
    temporary file and suggest an in-volume output location.
    """


def build_empty_findings(*, provenance: dict[str, Any]) -> dict[str, Any]:
    """Return a schema-valid empty ``findings`` document.

    Downstream phases populate fields in place. The empty skeleton validates
    cleanly against :func:`validate` so the tracer-bullet path (P1-C03 writes
    empty findings; P1-C04 reads them) works end-to-end before any analytical
    content exists.
    """
    return {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "provenance": dict(provenance),
        "columns": [],
        "outliers": {
            "by_method": {
                "iqr": [],
                "mad": [],
                "isolation_forest": None,
                "local_outlier_factor": None,
            },
            "agreement_matrix": [],
            "agreement_summary": {"high": 0, "review": 0, "low": 0},
        },
        "duplicates": {"exact": [], "near": []},
        "time_series": None,
        "drivers": None,
        "headline_findings": [],
        "comprehension_questions": [],
        "drillthroughs": [],
    }


_CHART_PATH_PREFIX: str = "charts/"


def _validate_chart_path(value: Any, location: str) -> None:
    """Validate a single optional chart-path field (P19-C01).

    ``None`` passes (chart paths are optional). Any non-null value must be a
    string that is a relative POSIX path rooted at ``charts/``: no leading
    slash, no Windows drive letter, no backslashes, no ``..`` traversal.
    """
    if value is None:
        return
    if not isinstance(value, str):
        raise SchemaValidationError(
            f"{location} must be a string or null, got {type(value).__name__}"
        )
    if "\\" in value:
        raise SchemaValidationError(
            f"{location} chart path must use POSIX separators "
            f"(no backslash); got {value!r}"
        )
    if os.path.isabs(value) or (len(value) >= 2 and value[1] == ":"):
        raise SchemaValidationError(
            f"{location} chart path must be relative (no leading '/' or "
            f"drive letter); got {value!r}"
        )
    if not value.startswith(_CHART_PATH_PREFIX):
        raise SchemaValidationError(
            f"{location} chart path must start with {_CHART_PATH_PREFIX!r}; "
            f"got {value!r}"
        )
    parts = value.split("/")
    if any(part in ("..", ".") for part in parts):
        raise SchemaValidationError(
            f"{location} chart path must not contain '..' or '.' segments; "
            f"got {value!r}"
        )


def _scan_chart_paths(data: dict[str, Any]) -> None:
    """Walk known optional chart-path locations and validate each (P19-C01).

    Locations scanned:
      - ``columns[].charts.{histogram,boxplot}``
      - ``outliers.by_method.{iqr,mad,isolation_forest,local_outlier_factor}[].chart``
      - ``drivers.entries[].partial_dependence_chart``
      - ``time_series.charts.{line,decomposition}``

    Entries that lack a ``charts`` block (or ``chart`` field) are skipped —
    every chart path is optional. Deeper per-field validation of non-chart
    content is the responsibility of the chunks that populate it.
    """
    columns = data.get("columns")
    if isinstance(columns, list):
        for i, col in enumerate(columns):
            if not isinstance(col, dict):
                continue
            charts = col.get("charts")
            if charts is None:
                continue
            if not isinstance(charts, dict):
                raise SchemaValidationError(
                    f"columns[{i}].charts must be a dict or null, "
                    f"got {type(charts).__name__}"
                )
            for kind in ("histogram", "boxplot"):
                _validate_chart_path(charts.get(kind), f"columns[{i}].charts.{kind}")

    outliers = data.get("outliers")
    if isinstance(outliers, dict):
        by_method = outliers.get("by_method")
        if isinstance(by_method, dict):
            for method, entries in by_method.items():
                if entries is None:
                    continue
                if not isinstance(entries, list):
                    raise SchemaValidationError(
                        f"outliers.by_method.{method} must be a list or null, "
                        f"got {type(entries).__name__}"
                    )
                for j, entry in enumerate(entries):
                    if isinstance(entry, dict) and "chart" in entry:
                        _validate_chart_path(
                            entry.get("chart"),
                            f"outliers.by_method.{method}[{j}].chart",
                        )

    drivers = data.get("drivers")
    if isinstance(drivers, dict):
        entries = drivers.get("entries")
        if isinstance(entries, list):
            for k, entry in enumerate(entries):
                if isinstance(entry, dict) and "partial_dependence_chart" in entry:
                    _validate_chart_path(
                        entry.get("partial_dependence_chart"),
                        f"drivers.entries[{k}].partial_dependence_chart",
                    )

    time_series = data.get("time_series")
    if isinstance(time_series, dict):
        ts_charts = time_series.get("charts")
        if ts_charts is not None:
            if not isinstance(ts_charts, dict):
                raise SchemaValidationError(
                    f"time_series.charts must be a dict or null, "
                    f"got {type(ts_charts).__name__}"
                )
            for kind in ("line", "decomposition"):
                _validate_chart_path(ts_charts.get(kind), f"time_series.charts.{kind}")


def validate(data: Any) -> None:
    """Validate ``data`` against schema v1. Raise :class:`SchemaValidationError` on failure.

    P1-C02 checks: input is a dict; ``schema_version`` equals the current
    version; every required top-level key is present. P19-C01 adds optional
    chart-path validation: any non-null path under columns / outliers /
    drivers / time_series must be a relative POSIX path rooted at ``charts/``.
    Deeper per-field checks are added by downstream chunks as they populate
    their sections.
    """
    if not isinstance(data, dict):
        raise SchemaValidationError(
            f"findings must be a dict, got {type(data).__name__}"
        )

    actual_version = data.get("schema_version")
    if actual_version != CURRENT_SCHEMA_VERSION:
        raise SchemaValidationError(
            f"findings.json::schema_version is {actual_version!r}; "
            f"this engine supports schema_version {CURRENT_SCHEMA_VERSION}."
        )

    missing = _REQUIRED_TOP_LEVEL - set(data.keys())
    if missing:
        raise SchemaValidationError(
            f"findings.json missing required top-level keys: {sorted(missing)}"
        )

    _scan_chart_paths(data)


def read_findings(path: Path | str) -> dict[str, Any]:
    """Load ``findings.json`` from ``path`` and validate before returning.

    Returns a schema-valid dict. Raises :class:`SchemaValidationError` if the
    file contents do not match schema v1; the standard :class:`OSError` /
    :class:`json.JSONDecodeError` chain propagates on read or parse failure.
    """
    path = Path(path)
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    validate(data)
    return data


def write_atomic(path: Path | str, data: dict[str, Any]) -> None:
    """Atomically write ``data`` to ``path`` after schema validation.

    Protocol (ADR-209): write to a sibling ``.tmp`` file, validate the result,
    then :func:`os.replace` to the target. If validation fails the target is
    untouched; the ``.tmp`` is a debug artefact that callers MAY clean up.

    The ``.tmp`` path is constructed via ``path.parent / (path.name + ".tmp")``
    to avoid :class:`ValueError` on multi-dot suffixes (post-R3 CRITICAL-2).
    """
    path = Path(path)
    tmp = path.parent / (path.name + ".tmp")
    tmp.write_text(
        json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    try:
        validate(json.loads(tmp.read_text(encoding="utf-8")))
    except SchemaValidationError:
        # Leave .tmp for inspection per ADR-209; never touch the target.
        raise
    try:
        os.replace(tmp, path)
    except OSError as exc:
        if exc.errno == errno.EXDEV:
            raise CrossVolumeWriteError(
                exc.errno,
                (
                    f"cannot rename {tmp} to {path}: source and target are on "
                    "different filesystems. Use an --output-dir on the same "
                    "volume as the temporary file."
                ),
            ) from exc
        raise


def _validate_questions_shape(questions: Any) -> None:
    """Raise :class:`SchemaValidationError` if ``questions`` fails ADR-109 shape rules."""
    if not isinstance(questions, list):
        raise SchemaValidationError(
            f"comprehension_questions must be a list, got {type(questions).__name__}"
        )
    if len(questions) != COMPREHENSION_QUESTION_COUNT:
        raise SchemaValidationError(
            f"comprehension_questions must contain exactly "
            f"{COMPREHENSION_QUESTION_COUNT} entries; got {len(questions)}"
        )
    required = set(COMPREHENSION_QUESTION_FIELDS)
    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            raise SchemaValidationError(
                f"comprehension_questions[{i}] must be a dict, got {type(q).__name__}"
            )
        actual = set(q.keys())
        missing = required - actual
        extra = actual - required
        if missing:
            raise SchemaValidationError(
                f"comprehension_questions[{i}] missing field(s): {sorted(missing)}"
            )
        if extra:
            raise SchemaValidationError(
                f"comprehension_questions[{i}] has unexpected field(s): {sorted(extra)}"
            )
        for field in COMPREHENSION_QUESTION_FIELDS:
            if not isinstance(q[field], str):
                raise SchemaValidationError(
                    f"comprehension_questions[{i}].{field} must be a string, "
                    f"got {type(q[field]).__name__}"
                )


def _scan_jargon(text: str, location: str) -> None:
    """Raise :class:`JargonError` on the first word-boundary hit against JARGON_FORBIDDEN."""
    lower = text.lower()
    for term in JARGON_FORBIDDEN:
        if re.search(rf"\b{re.escape(term)}\b", lower):
            raise JargonError(term=term, location=location)


def patch_comprehension_questions(
    findings_path: Path | str,
    questions: list[dict[str, str]],
) -> None:
    """Patch ``findings.json::comprehension_questions`` per ADR-109.

    Validates that ``questions`` has the canonical shape, that every
    ``supporting_finding_id`` resolves to an existing
    ``headline_findings[].id``, and that no question or answer contains a
    term from :data:`_shared.methodology.JARGON_FORBIDDEN`. On success,
    atomically replaces the comprehension-questions block and writes the
    patched document via :func:`write_atomic`.

    Raises:
        SchemaValidationError: shape violation (count / missing field / wrong type).
        ReferentialIntegrityError: ``supporting_finding_id`` absent from headline_findings.
        JargonError: a forbidden jargon term appears in a question or answer.
    """
    _validate_questions_shape(questions)

    findings = read_findings(findings_path)

    try:
        known_ids = {f["id"] for f in findings["headline_findings"]}
    except (KeyError, TypeError) as exc:
        raise SchemaValidationError(
            f"findings.headline_findings malformed: expected list of dicts "
            f"with an 'id' field ({exc})"
        ) from exc
    for i, q in enumerate(questions):
        supporting = q["supporting_finding_id"]
        if supporting not in known_ids:
            raise ReferentialIntegrityError(
                reference=supporting, kind="headline_findings.id"
            )
        _scan_jargon(q["question"], f"comprehension_questions[{i}].question")
        _scan_jargon(q["answer"], f"comprehension_questions[{i}].answer")

    findings["comprehension_questions"] = list(questions)
    write_atomic(findings_path, findings)
