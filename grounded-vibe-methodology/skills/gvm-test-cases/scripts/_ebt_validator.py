"""EBT-1 audit validator for /gvm-test-cases Phase 4 (ADR-501).

Heuristic rules (verbatim from spec, so downstream readers understand
borderline classifications):

Requirements file (Markdown):
  Each requirement is a bold-prefixed line matching:
    r"^\\*\\*([A-Z]+-\\d+)\\s*\\(([^)]+)\\)"
  Priority is normalised: Must/MUST/must → MUST; Should → SHOULD;
  Could → COULD; Won't/Wont → WONT; unknown → MUST (fail-closed).

Test-cases file (Markdown):
  Blocks are separated by blank lines or by a new "## TC-" heading.
  A block references a requirement when it contains "[Requirement: RE-N]".
  A block is example-based when it contains ALL of:
    1. A line starting with "Input:" (literal prefix, non-empty after).
    2. A line containing "MUST contain" (case-sensitive) OR
       "should contain" (case-insensitive).
    3. A line containing "MUST NOT contain" (case-sensitive) OR
       "should not contain" (case-insensitive).

Public surface: audit(), parse_requirements(), AuditReport, CoverageGap,
LintViolation. All helpers are module-private (prefixed _).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public dataclasses (spec API contract — field names are frozen by spec)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CoverageGap:
    requirement_id: str
    priority: Literal["MUST", "SHOULD", "COULD", "WONT"]
    missing: Literal["any-test", "example-test", "negative-assertion"]
    detail: str


@dataclass(frozen=True)
class LintViolation:
    """Structurally-duplicated dataclass — canonical definition is in
    `gvm-design-system/scripts/_ebt_contract_lint.py`.

    The duplication is intentional and structural, not a TODO. `_ebt_validator`
    is shipped with `gvm-test-cases`; `_ebt_contract_lint` is shipped with
    `gvm-design-system`. Cross-skill imports are not reliable at module load
    time (each skill's `scripts/` dir is added to sys.path independently by its
    own conftest), so importing `LintViolation` from `_ebt_contract_lint` here
    would break stand-alone imports of this module. Fields are kept field-for-
    field identical with the canonical definition; `test_ebt_validator` asserts
    structural equivalence to catch drift.
    """

    test_id: str
    file_line: str
    kind: Literal["rainsberger", "metz"]
    detail: str


@dataclass(frozen=True)
class AuditReport:
    """Result of an EBT-1 audit pass.

    `coverage_gaps` is empty when every MUST requirement has at least one
    example-based test. `rainsberger_violations` and `metz_violations` are
    `()` from `audit()` itself; `/gvm-test-cases` Phase 4 calls
    `_ebt_contract_lint.lint()` separately and constructs a populated
    `AuditReport` via `dataclasses.replace(report, rainsberger_violations=...,
    metz_violations=...)`. All three collections are tuples so the frozen
    dataclass guarantees true immutability — list-with-frozen would freeze
    the reference but not the contents.
    """

    total_requirements: int
    total_tests: int
    coverage_gaps: tuple[CoverageGap, ...]
    rainsberger_violations: tuple[LintViolation, ...] = ()
    metz_violations: tuple[LintViolation, ...] = ()


# ---------------------------------------------------------------------------
# Requirements parsing
# ---------------------------------------------------------------------------

_REQ_RE = re.compile(r"^\*\*([A-Z]+-\d+)\s*\(([^)]+)\)")

_PRIORITY_MAP: dict[str, Literal["MUST", "SHOULD", "COULD", "WONT"]] = {
    "must": "MUST",
    "should": "SHOULD",
    "could": "COULD",
    "wont": "WONT",
    "won't": "WONT",
}


def _normalise_priority(
    req_id: str, raw: str
) -> Literal["MUST", "SHOULD", "COULD", "WONT"]:
    normalised = _PRIORITY_MAP.get(raw.lower().rstrip("'"))
    if normalised is None:
        _log.warning(
            "Unknown priority %r for %s — defaulting to MUST (fail-closed)", raw, req_id
        )
        return "MUST"
    return normalised


def parse_requirements(
    text: str,
) -> list[tuple[str, Literal["MUST", "SHOULD", "COULD", "WONT"]]]:
    """Return list of (requirement_id, priority) for each recognised requirement.

    Public entry point so cross-module callers (e.g. `_retrofit`) do not need
    to reach across the module-private boundary.
    """
    results: list[tuple[str, Literal["MUST", "SHOULD", "COULD", "WONT"]]] = []
    for line in text.splitlines():
        m = _REQ_RE.match(line.strip())
        if m:
            req_id = m.group(1)
            priority = _normalise_priority(req_id, m.group(2))
            results.append((req_id, priority))
    return results


# ---------------------------------------------------------------------------
# Test-case parsing
# ---------------------------------------------------------------------------

_TC_HEADING_RE = re.compile(r"^##\s+TC-")


def _split_blocks(text: str) -> list[list[str]]:
    """Split test-cases text into blocks of non-empty lines.

    A new block starts at a blank line or at a line matching a TC heading.
    Returns only non-empty blocks.
    """
    blocks: list[list[str]] = []
    current: list[str] = []

    for line in text.splitlines():
        if _TC_HEADING_RE.match(line):
            # TC heading always starts a new block
            if current:
                blocks.append(current)
            current = [line]
        elif line.strip() == "":
            if current:
                blocks.append(current)
                current = []
        else:
            current.append(line)

    if current:
        blocks.append(current)

    return [b for b in blocks if b]


_REQ_REF_RE = re.compile(r"\[Requirement:\s*([A-Z]+-\d+)\]")

# Positive-assertion patterns (spec: "MUST contain" case-sensitive OR
# "should contain" case-insensitive)
_POS_MUST = "MUST contain"
_NEG_MUST = "MUST NOT contain"


def _block_requirement_id(block: list[str]) -> str | None:
    """Return the first requirement ID referenced in the block, or None."""
    for line in block:
        m = _REQ_REF_RE.search(line)
        if m:
            return m.group(1)
    return None


def _block_has_input(block: list[str]) -> bool:
    return any(
        line.lstrip().startswith("Input:") and len(line.strip()) > 6 for line in block
    )


def _block_has_positive(block: list[str]) -> bool:
    # "should not contain" is a superstring of "should contain"; check the negative form
    # first and strip it before looking for the positive variant, so a block with
    # only "should not contain" is not mistakenly classified as having a positive.
    joined = "\n".join(block)
    if _POS_MUST in joined:
        return True
    # Remove "should not contain" occurrences before checking for "should contain"
    stripped_lower = joined.lower().replace("should not contain", "")
    return "should contain" in stripped_lower


def _block_has_negative(block: list[str]) -> bool:
    joined = "\n".join(block)
    return _NEG_MUST in joined or "should not contain" in joined.lower()


def _block_is_ebt(block: list[str]) -> bool:
    """Return True iff the block satisfies the example-based test shape."""
    return (
        _block_has_input(block)
        and _block_has_positive(block)
        and _block_has_negative(block)
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def audit(
    test_cases_path: Path | str,
    requirements_path: Path | str,
) -> AuditReport:
    """Audit MUST-priority requirements for example-based test coverage.

    Parameters
    ----------
    test_cases_path:
        Path to the Markdown test-cases file (e.g. ``test-cases/test-cases.md``).
    requirements_path:
        Path to the Markdown requirements file (e.g. ``requirements/requirements.md``).

    Returns
    -------
    AuditReport
        ``coverage_gaps`` is empty when every MUST requirement has at least
        one example-based test. ``rainsberger_violations`` and
        ``metz_violations`` are always ``()`` from this entry point — the
        Phase 4 caller invokes ``_ebt_contract_lint.lint()`` separately and
        composes a populated report via ``dataclasses.replace(report, ...)``.
    """
    # Coerce at the boundary (Ramalho — Path | str, coerce once)
    tc_path = Path(test_cases_path)
    req_path = Path(requirements_path)

    req_text = req_path.read_text(encoding="utf-8")
    tc_text = tc_path.read_text(encoding="utf-8")

    requirements = parse_requirements(req_text)
    blocks = _split_blocks(tc_text)

    # Build index: req_id → list[block]
    req_blocks: dict[str, list[list[str]]] = {req_id: [] for req_id, _ in requirements}
    total_tests = 0
    for block in blocks:
        ref_id = _block_requirement_id(block)
        if ref_id is not None:
            total_tests += 1
            if ref_id in req_blocks:
                req_blocks[ref_id].append(block)

    # Determine coverage gaps for MUST requirements only
    coverage_gaps: list[CoverageGap] = []
    for req_id, priority in requirements:
        if priority != "MUST":
            continue

        tests_for_req = req_blocks.get(req_id, [])

        if not tests_for_req:
            coverage_gaps.append(
                CoverageGap(
                    requirement_id=req_id,
                    priority=priority,
                    missing="any-test",
                    detail=f"{req_id} has no test cases referencing it.",
                )
            )
            continue

        ebt_tests = [b for b in tests_for_req if _block_is_ebt(b)]
        if ebt_tests:
            # Fully covered — no gap
            continue

        # Determine the closest-miss gap type
        has_input_any = any(_block_has_input(b) for b in tests_for_req)
        has_pos_any = any(_block_has_positive(b) for b in tests_for_req)

        if has_input_any and has_pos_any:
            # Has input + positive but no negative anywhere
            missing: Literal[
                "any-test", "example-test", "negative-assertion"
            ] = "negative-assertion"
            detail = f"{req_id} has tests with Input and positive assertion but no negative assertion."
        else:
            missing = "example-test"
            detail = f"{req_id} has tests but none match the example-based shape (Input + positive + negative)."

        coverage_gaps.append(
            CoverageGap(
                requirement_id=req_id,
                priority=priority,
                missing=missing,
                detail=detail,
            )
        )

    return AuditReport(
        total_requirements=len(requirements),
        total_tests=total_tests,
        coverage_gaps=tuple(coverage_gaps),
    )
