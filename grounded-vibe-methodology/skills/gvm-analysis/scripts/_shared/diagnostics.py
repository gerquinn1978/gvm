"""Shared exception classes and diagnostic helpers for /gvm-analysis.

P2-C01 bootstraps this module with the two classes raised by
``_shared/io.py``: :class:`EncryptedFileError` and :class:`MalformedFileError`.
P2-C04 extends it with the remainder of the cross-cutting exception hierarchy
(cross-cutting.md §Error Handling Conventions lines 266–272) and the
:func:`format_diagnostic` helper that renders the canonical
ERROR / What went wrong / What to try block.

:func:`format_diagnostic` is a pure string-producing function. It does NOT
write to stderr and does NOT call :func:`sys.exit` — wiring it to those is
the entry-point orchestrator's responsibility (P5-C02). This separation
keeps the helper testable and usable from subprocess-diagnostic contexts.
"""

from __future__ import annotations

import textwrap
from collections.abc import Sequence


# --- Exception classes -----------------------------------------------------


class EncryptedFileError(Exception):
    """Raised when a file is password-protected or otherwise unreadable.

    AN-42 / cross-cutting Error Handling Conventions: the skill refuses
    encrypted xlsx files with a clear diagnostic pointing to the specific
    file. Callers MUST NOT prompt for a password or invoke any decryption
    library — refusal is the only safe action at this boundary.
    """

    def __init__(self, path: str | object) -> None:
        self.path = str(path)
        super().__init__(f"encrypted or unreadable file: {self.path}")


class MalformedFileError(Exception):
    """Raised when a file is readable but its structure is invalid.

    ``row`` / ``col`` are optional — some malformation modes (empty sheet,
    corrupt xlsx) have no specific cell location. ``kind`` is a short tag
    that :func:`format_diagnostic` dispatches on to produce
    situation-specific guidance.
    """

    def __init__(
        self,
        path: str | object,
        *,
        row: int | None,
        col: int | None,
        kind: str,
    ) -> None:
        self.path = str(path)
        self.row = row
        self.col = col
        self.kind = kind
        where = ""
        if row is not None:
            where = f" at row {row}"
            if col is not None:
                where += f", col {col}"
        super().__init__(f"malformed file ({kind}){where}: {self.path}")


class ColumnNotFoundError(Exception):
    """Raised when a requested column is not in the loaded DataFrame.

    ``known_columns`` is included so the diagnostic can surface the
    candidates the user actually has — typos are the common cause.
    """

    def __init__(self, column: str, known_columns: Sequence[str]) -> None:
        self.column = column
        self.known_columns = tuple(known_columns)
        super().__init__(f"column not found: {column!r}")


class ZeroVarianceTargetError(Exception):
    """Raised when a driver-analysis target has zero variance.

    All values in the target column are identical, so decomposition would
    produce meaningless results. ``_shared/stats.py`` raises this at the
    entry to the drivers pipeline.
    """

    def __init__(self, target: str) -> None:
        self.target = target
        super().__init__(f"target column has zero variance: {target!r}")


class PrivacyBoundaryViolation(Exception):
    """Raised when composed narrative text contains a raw data-row token.

    ASR-1 privacy boundary: findings carry aggregates, not row values.
    ``_shared/headline.select()`` scans every composed title/summary
    against the engine's categorical-value corpus and raises this on a
    match. The run aborts — raw data MUST NOT reach findings.json.

    The diagnostic formatter deliberately does NOT render ``token`` — that
    would re-leak the raw value into stderr. ``context`` identifies the
    offending field so the engineer can investigate without re-exposing
    the data.
    """

    def __init__(self, token: str, context: str) -> None:
        self.token = token
        self.context = context
        super().__init__(f"privacy boundary violation at {context}")


class DependencyError(Exception):
    """Raised by ``scripts/_check_deps.py`` when a required dep fails.

    ``reason`` is a short tag: ``"missing"``, ``"below version floor"``,
    ``"api mismatch"``, etc. ``required`` / ``found`` are optional — the
    "missing" branch has nothing to report for ``found``.
    """

    def __init__(
        self,
        package: str,
        reason: str,
        *,
        required: str | None = None,
        found: str | None = None,
    ) -> None:
        self.package = package
        self.reason = reason
        self.required = required
        self.found = found
        super().__init__(f"dependency error: {package} ({reason})")


class JargonError(Exception):
    """Raised by ``_shared/findings.py::patch_comprehension_questions()``.

    ADR-210 forbids rendered findings from containing a configured jargon
    vocabulary. ``location`` is a JSONPath-ish string pointing at the
    offending field.
    """

    def __init__(self, term: str, location: str) -> None:
        self.term = term
        self.location = location
        super().__init__(f"jargon term {term!r} at {location}")


class RiskyMappingPathError(Exception):
    """Raised when ``--mapping-out`` for ``anonymise.py`` lies inside
    Claude's typical scope and ``--i-accept-the-risk`` was not supplied.

    Anonymisation-pipeline ADR-404 / AN-38: the validator fails closed by
    default. ``path`` is the resolved path the user supplied; ``scopes``
    is the list of scope directories that flagged it. The exception
    message is a fully-formed diagnostic per ADR-404 prose — the caller
    can surface ``str(exc)`` directly to stderr without re-formatting.
    """

    def __init__(self, path: str | object, scopes: list[str]) -> None:
        self.path = str(path)
        self.scopes = list(scopes)
        super().__init__(_format_risky_path_diagnostic(self.path, self.scopes))


class ReferentialIntegrityError(Exception):
    """Raised when a finding references a non-existent entity.

    ADR-109 / ``patch_comprehension_questions()``: a comprehension
    question that references an unknown column id or dangling finding id
    breaks the report's internal links.
    """

    def __init__(self, reference: str, kind: str) -> None:
        self.reference = reference
        self.kind = kind
        super().__init__(f"referential integrity error ({kind}): {reference!r}")


# --- Diagnostic formatting -------------------------------------------------


_MALFORMED_KIND_TEMPLATES: dict[str, dict[str, str]] = {
    "no_data_rows": {
        "summary": "file has no data rows",
        "what": "The file parsed but contains no usable data rows (headers only, or an entirely empty sheet).",
        "try": "Open the file and confirm it actually contains data below the header row.",
    },
    "corrupt_xlsx": {
        "summary": "xlsx file is structurally corrupt",
        "what": "openpyxl could not read the workbook structure. The file may be truncated or damaged.",
        "try": "Re-save or re-export the file from Excel, or request a fresh copy from the source.",
    },
    "corrupt_xls": {
        "summary": "legacy .xls file is corrupt",
        "what": "xlrd could not parse the legacy .xls workbook. Legacy xls files are often fragile.",
        "try": "Re-save the file as .xlsx from Excel, or request a fresh copy from the source.",
    },
    "parser_error": {
        "summary": "could not parse the file contents",
        "what": "pandas could not parse the file — likely an encoding, delimiter, or quoting problem.",
        "try": "Check the encoding (UTF-8 is expected), the delimiter, and that any quoted fields are properly closed.",
    },
    "xls_engine_missing": {
        "summary": "legacy .xls support requires the xlrd engine",
        "what": "Reading legacy .xls requires the xlrd package (pinned <2.0). It is not installed in this environment.",
        "try": "Convert the file to .xlsx and re-run, or install xlrd<2.0 if you need legacy .xls support.",
    },
    "malformed_yaml": {
        "summary": "YAML file is malformed",
        "what": "The YAML could not be parsed, or parsed to something other than a mapping. Preferences files must be a top-level mapping.",
        "try": "Check indentation, quoting, and that the top-level structure is key/value pairs (not a list or scalar).",
    },
}


def _format_risky_path_diagnostic(path: str, scopes: list[str]) -> str:
    """Render the ADR-404 ERROR/What/What-to-try block for a risky mapping path.

    Names the offending path, lists the scopes that flagged it, and offers
    concrete alternatives — including ``--i-accept-the-risk`` for the
    explicit opt-in. McConnell: defensive programming with clear message.
    """
    scope_lines = "\n".join(f"  - {s}" for s in scopes) if scopes else "  - (none)"
    return _format_block(
        summary=f"mapping path is inside Claude's typical scope: {path}",
        what=(
            f"The mapping file you specified is at:\n"
            f"  {path}\n\n"
            f"This path lies inside one of the scopes Claude Code can read:\n"
            f"{scope_lines}\n\n"
            "If Claude or any GVM skill reads this file, the anonymisation "
            "is broken — the LLM gains the original sensitive values."
        ),
        try_=(
            "Choose a path outside Claude's reachable scope, for example:\n"
            "  ~/.private/gvm-mappings/<project>/<date>.csv\n"
            "  /Volumes/ExternalSSD/mappings/...\n"
            "  a separate user account with no Claude Code installed\n\n"
            "Or pass --i-accept-the-risk if you have audited that no Claude "
            "session will ever read this file."
        ),
    )


def _format_block(summary: str, what: str, try_: str) -> str:
    """Assemble the canonical three-block diagnostic string."""
    body = "\n".join(
        [
            f"ERROR: {summary}",
            "",
            "What went wrong:",
            textwrap.indent(what, "  "),
            "",
            "What to try:",
            textwrap.indent(try_, "  "),
        ]
    )
    return body


def _format_encrypted(exc: EncryptedFileError) -> str:
    return _format_block(
        summary=f"encrypted or password-protected file: {exc.path}",
        what=(
            f"{exc.path} appears to be password-protected or otherwise "
            "encrypted. The skill refuses encrypted files by design — it "
            "does not prompt for passwords."
        ),
        try_=(
            "Remove the password from the file in Excel (File → Info → "
            "Protect Workbook → Encrypt with Password → clear) and save a "
            "new copy, then re-run the analysis."
        ),
    )


def _format_malformed(exc: MalformedFileError) -> str:
    template = _MALFORMED_KIND_TEMPLATES.get(exc.kind)
    where = ""
    if exc.row is not None:
        where = f" at row {exc.row}"
        if exc.col is not None:
            where += f", col {exc.col}"

    if template is None:
        summary = f"malformed file ({exc.kind}): {exc.path}{where}"
        what = f"{exc.path} failed to parse. Malformation kind: {exc.kind!r}."
        try_ = (
            "Confirm the file is valid for its format, re-export a fresh "
            "copy if possible, and re-run."
        )
    else:
        summary = f"{template['summary']}: {exc.path}{where}"
        what = f"{exc.path}{where}: {template['what']}"
        try_ = template["try"]

    return _format_block(summary=summary, what=what, try_=try_)


def _format_column_not_found(exc: ColumnNotFoundError) -> str:
    known = ", ".join(repr(c) for c in exc.known_columns) or "(none)"
    return _format_block(
        summary=f"column not found: {exc.column!r}",
        what=(
            f"The column {exc.column!r} was referenced but does not exist "
            f"in the loaded data. Known columns: {known}."
        ),
        try_=(
            "Check the column name for typos and confirm it matches the "
            "header row in the input file exactly (case-sensitive)."
        ),
    )


def _format_zero_variance(exc: ZeroVarianceTargetError) -> str:
    return _format_block(
        summary=f"target column has zero variance: {exc.target!r}",
        what=(
            f"Every value in {exc.target!r} is identical. Driver analysis "
            "cannot decompose variance when there is none to decompose."
        ),
        try_=(
            "Pick a different target column, or filter the data to a "
            "subset where the target actually varies."
        ),
    )


def _format_privacy_violation(exc: PrivacyBoundaryViolation) -> str:
    # Deliberately do NOT include exc.token — re-rendering the leaked value
    # into stderr would defeat the abort. Surface only the location.
    return _format_block(
        summary=f"privacy boundary violation at {exc.context}",
        what=(
            f"A composed narrative string at {exc.context} contained a "
            "raw data-row token from the input. Findings must carry "
            "aggregates, not row values (ASR-1). The run aborted before "
            "any output was written."
        ),
        try_=(
            "This is an engine bug, not a user problem. Report the "
            "context string to the maintainers; the raw token itself is "
            "redacted from this diagnostic on purpose."
        ),
    )


def _format_dependency(exc: DependencyError) -> str:
    # Only surface version metadata that was actually provided — "required
    # any" would mislead users into searching for a constraint that does
    # not exist.
    parts = []
    if exc.required is not None:
        parts.append(f"required {exc.required}")
    if exc.found is not None:
        parts.append(f"found {exc.found}")
    version_suffix = f" ({', '.join(parts)})" if parts else ""

    if exc.reason == "missing":
        what = (
            f"The required package {exc.package!r} is missing from the "
            "current Python environment."
        )
        try_ = (
            f"Install it: `pip install {exc.package}`. If you use a "
            "project-managed environment, install via your project tool "
            "(uv, poetry, etc.)."
        )
    else:
        what = (
            f"Dependency check failed for {exc.package!r}: "
            f"{exc.reason}{version_suffix}."
        )
        try_ = (
            f"Upgrade or reinstall {exc.package}: "
            f"`pip install --upgrade {exc.package}`."
        )

    return _format_block(
        summary=f"dependency error: {exc.package} ({exc.reason})",
        what=what,
        try_=try_,
    )


def _format_jargon(exc: JargonError) -> str:
    return _format_block(
        summary=f"jargon term rejected: {exc.term!r}",
        what=(
            f"The term {exc.term!r} appears at {exc.location}, but is "
            "on the jargon-forbidden list for rendered findings."
        ),
        try_=(
            "Rephrase the field using plain language, or update the "
            "jargon-forbidden list if the term is in fact acceptable."
        ),
    )


def _format_referential_integrity(exc: ReferentialIntegrityError) -> str:
    return _format_block(
        summary=f"referential integrity error ({exc.kind}): {exc.reference!r}",
        what=(
            f"A finding references {exc.reference!r} ({exc.kind}), which "
            "does not exist in the output. Internal cross-references must "
            "resolve before rendering."
        ),
        try_=(
            "Regenerate findings with a clean cache. If the error "
            "persists, report the reference and kind to the maintainers."
        ),
    )


def _format_schema_validation(exc: Exception) -> str:
    """Formatter for ``SchemaValidationError`` from ``_shared/findings.py``.

    Surfaces the validator's message (which names the offending key / field
    / count) verbatim — the message is already user-facing by design (see
    ``SchemaValidationError`` docstring).
    """
    return _format_block(
        summary=f"findings validation failed: {exc}",
        what=(
            f"A findings document or comprehension-questions payload failed "
            f"structural validation: {exc}"
        ),
        try_=(
            "Regenerate the offending document from the engine, or correct "
            "the wrapper input so it matches the expected shape."
        ),
    )


def _format_unknown(exc: Exception) -> str:
    """Fallback for unfamiliar exception types.

    NFR-3 forbids Python tracebacks from reaching the user. An unfamiliar
    exception still gets a canonical diagnostic — with ``str(exc)`` preserved
    so we do not drop information.
    """
    return _format_block(
        summary=f"internal error: {type(exc).__name__}",
        what=(
            f"An unexpected error occurred: {exc}. This is likely an "
            "engine-internal issue rather than a problem with the input."
        ),
        try_=(
            "Re-run with --verbose for a full traceback, and report the "
            "error to the maintainers if it persists."
        ),
    )


def format_diagnostic(exc: Exception) -> str:
    """Render ``exc`` as the canonical ERROR/What/What-to-try string.

    Pure function: returns a string. Does NOT write to stderr and does NOT
    call :func:`sys.exit`. The entry-point orchestrator wires the return
    value to stderr and sets the process exit code.

    For :class:`MalformedFileError`, dispatches further on ``exc.kind`` via
    :data:`_MALFORMED_KIND_TEMPLATES`. Unknown kinds fall through to a
    generic malformed-file diagnostic so the helper never raises on a new
    kind added upstream.

    For exception types not in this module, renders a generic diagnostic
    that preserves ``str(exc)`` — NFR-3 forbids tracebacks reaching users.
    """
    if isinstance(exc, EncryptedFileError):
        return _format_encrypted(exc)
    if isinstance(exc, MalformedFileError):
        return _format_malformed(exc)
    if isinstance(exc, ColumnNotFoundError):
        return _format_column_not_found(exc)
    if isinstance(exc, ZeroVarianceTargetError):
        return _format_zero_variance(exc)
    if isinstance(exc, PrivacyBoundaryViolation):
        return _format_privacy_violation(exc)
    if isinstance(exc, DependencyError):
        return _format_dependency(exc)
    if isinstance(exc, JargonError):
        return _format_jargon(exc)
    if isinstance(exc, ReferentialIntegrityError):
        return _format_referential_integrity(exc)
    if isinstance(exc, RiskyMappingPathError):
        # The exception message is already a fully-formed diagnostic block.
        return str(exc)
    # Check SchemaValidationError by class name to avoid circular import
    # (``_shared/findings.py`` imports from this module).
    if type(exc).__name__ == "SchemaValidationError":
        return _format_schema_validation(exc)
    return _format_unknown(exc)
