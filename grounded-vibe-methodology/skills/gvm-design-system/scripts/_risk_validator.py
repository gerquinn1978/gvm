"""Shared risk-assessment validator (discovery ADR-306, ADR-307, ADR-308).

Validates `risks/risk-assessment.md` for the four MUST gates:

- **RA-1** — file exists; the four sections (Value Risk, Usability Risk,
  Feasibility Risk, Viability Risk) appear in order, all present.
- **RA-2** — each non-`*accepted-unknown*` section has ≥ 50 words of prose.
- **RA-3** — no section may be the bare word ``unknown``. The
  ``*accepted-unknown*`` form is structurally rigid: first non-empty line is
  ``*accepted-unknown*``; followed by ``Rationale:``, ``Validator:``, and
  ``Review date:`` lines (any order). The ``Review date:`` value is ISO-8601
  and must be ``>= today`` (equality permitted).
- **RA-4** — each prose section contains at least one ``questioner:`` token
  (case-insensitive on the token name; trailing ASCII colon required).
  ``Validator:`` is accepted as a synonym only inside accepted-unknown
  sections (per ADR-307 mutual exclusion).

Public surface: :class:`RiskAssessment`, :class:`RiskValidationError`,
:func:`full_check`. ``full_check`` never raises.

Per cross-cutting ADR-002 the validator lives in
``gvm-design-system/scripts/`` so both ``/gvm-requirements`` (Phase 0 +
Phase 5) and ``/gvm-test`` (VV-2(b), VV-4(c)) can import it.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from _schema import load_with_schema

REQUIRED_SECTIONS: tuple[str, ...] = (
    "Value Risk",
    "Usability Risk",
    "Feasibility Risk",
    "Viability Risk",
)

_HEADER_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_ACCEPTED_UNKNOWN_RE = re.compile(r"^\s*\*accepted-unknown\*\s*$", re.IGNORECASE)
_RATIONALE_RE = re.compile(r"^\s*rationale\s*:", re.IGNORECASE)
_VALIDATOR_RE = re.compile(r"^\s*validator\s*:", re.IGNORECASE)
_REVIEW_DATE_RE = re.compile(r"^\s*review\s+date\s*:\s*(\S+)", re.IGNORECASE)
_QUESTIONER_RE = re.compile(r"\bquestioner\s*:", re.IGNORECASE)
_VALIDATOR_TOKEN_RE = re.compile(r"\bvalidator\s*:", re.IGNORECASE)
_WORD_RE = re.compile(r"[A-Za-z]+(?:['\u2019][A-Za-z]+)?")
_MIN_WORDS = 50


@dataclass(frozen=True)
class RiskValidationError:
    code: str
    section: str
    message: str


@dataclass(frozen=True)
class RiskAssessment:
    value: str
    usability: str
    feasibility: str
    viability: str


def full_check(
    path: str | os.PathLike[str],
    *,
    today: date | None = None,
) -> tuple[RiskAssessment | None, list[RiskValidationError]]:
    """Validate the risk-assessment file. Never raises.

    Returns ``(risk_assessment, errors)``. Pass condition: ``len(errors) == 0``.
    On schema/IO failure, ``risk_assessment`` is ``None`` and a single
    sentinel error is returned with ``code == "RA-1"`` and ``section == "-"``.
    """
    today = today or date.today()
    p = Path(path)
    if not p.exists():
        return None, [
            RiskValidationError(
                code="RA-1",
                section="-",
                message=f"risk-assessment.md missing at {p}",
            )
        ]

    try:
        artefact = load_with_schema(p, "risk_assessment")
    except Exception as exc:  # noqa: BLE001 — last-resort: never raise
        return None, [
            RiskValidationError(
                code="RA-1",
                section="-",
                message=f"could not load {p}: {exc}",
            )
        ]

    sections, ra1_errors = _split_into_sections(artefact.body)
    if ra1_errors:
        return None, ra1_errors

    errors: list[RiskValidationError] = []
    for name in REQUIRED_SECTIONS:
        body = sections[name]
        first_non_empty = _first_non_empty_line(body)

        if _ACCEPTED_UNKNOWN_RE.match(first_non_empty or ""):
            errors.extend(_check_accepted_unknown(name, body, today))
            continue

        if first_non_empty is not None and first_non_empty.strip().lower() == "unknown":
            errors.append(
                RiskValidationError(
                    code="RA-3",
                    section=name,
                    message=f"{name} prose is the bare word 'unknown' — "
                    f"either evaluate the risk or use the *accepted-unknown* form",
                )
            )
            continue

        # RA-2 word-count floor
        word_count = len(_WORD_RE.findall(body))
        if word_count < _MIN_WORDS:
            errors.append(
                RiskValidationError(
                    code="RA-2",
                    section=name,
                    message=f"{name} below 50-word floor (got: {word_count})",
                )
            )
            continue

        # RA-4 questioner-token check (only on prose sections, not accepted-unknown)
        if not _QUESTIONER_RE.search(body):
            errors.append(
                RiskValidationError(
                    code="RA-4",
                    section=name,
                    message=f"{name} questioner: token missing",
                )
            )

    risk_assessment = RiskAssessment(
        value=sections["Value Risk"],
        usability=sections["Usability Risk"],
        feasibility=sections["Feasibility Risk"],
        viability=sections["Viability Risk"],
    )
    return risk_assessment, errors


def _split_into_sections(
    body: str,
) -> tuple[dict[str, str], list[RiskValidationError]]:
    """Return ``({section_name: section_body}, errors)``.

    On RA-1 failure (missing or out-of-order sections), returns
    ``({}, [errors])`` so the caller can short-circuit.
    """
    matches = list(_HEADER_RE.finditer(body))
    found_names = [m.group(1).strip() for m in matches]

    # Filter to only required-section headers; report missing/out-of-order.
    required_set = set(REQUIRED_SECTIONS)
    relevant = [(m, n) for m, n in zip(matches, found_names) if n in required_set]

    seen = [n for _, n in relevant]
    missing = [n for n in REQUIRED_SECTIONS if n not in seen]
    if missing:
        return (
            {},
            [
                RiskValidationError(
                    code="RA-1",
                    section=name,
                    message=f"required section '{name}' is missing",
                )
                for name in missing
            ],
        )

    if seen != list(REQUIRED_SECTIONS):
        return (
            {},
            [
                RiskValidationError(
                    code="RA-1",
                    section="-",
                    message=(
                        f"sections out of order: expected {list(REQUIRED_SECTIONS)}, "
                        f"got {seen}"
                    ),
                )
            ],
        )

    # Body of section i ends at the next header of ANY level/name, not just
    # the next required header. Otherwise an extra `## Notes` section between
    # two required sections silently folds into the preceding one and inflates
    # its word count + questioner search (independent reviewer catch).
    all_header_starts = [m.start() for m in matches]
    sections: dict[str, str] = {}
    for m, name in relevant:
        start = m.end()
        next_starts = [s for s in all_header_starts if s > m.start()]
        end = next_starts[0] if next_starts else len(body)
        sections[name] = body[start:end].strip()
    return sections, []


def _first_non_empty_line(body: str) -> str | None:
    for line in body.splitlines():
        if line.strip():
            return line
    return None


def _check_accepted_unknown(
    name: str, body: str, today: date
) -> list[RiskValidationError]:
    """Validate the rigid *accepted-unknown* shape per ADR-307."""
    errors: list[RiskValidationError] = []
    has_rationale = False
    has_validator = False
    has_review_date = False
    review_date_raw: str | None = None

    for line in body.splitlines():
        if _RATIONALE_RE.match(line):
            has_rationale = True
        if _VALIDATOR_RE.match(line):
            has_validator = True
        m = _REVIEW_DATE_RE.match(line)
        if m:
            has_review_date = True
            review_date_raw = m.group(1)

    if not has_rationale:
        errors.append(
            RiskValidationError(
                code="RA-3",
                section=name,
                message=f"{name} *accepted-unknown* missing 'Rationale:' line",
            )
        )
    if not has_validator:
        errors.append(
            RiskValidationError(
                code="RA-3",
                section=name,
                message=f"{name} *accepted-unknown* missing 'Validator:' line",
            )
        )
    if not has_review_date:
        errors.append(
            RiskValidationError(
                code="RA-3",
                section=name,
                message=f"{name} *accepted-unknown* missing 'Review date:' line",
            )
        )
        return errors

    assert review_date_raw is not None
    try:
        review_date = date.fromisoformat(review_date_raw)
    except ValueError:
        errors.append(
            RiskValidationError(
                code="RA-3",
                section=name,
                message=(
                    f"{name} *accepted-unknown* 'Review date:' value "
                    f"{review_date_raw!r} is not ISO-8601 (YYYY-MM-DD)"
                ),
            )
        )
        return errors

    if review_date < today:
        errors.append(
            RiskValidationError(
                code="RA-3",
                section=name,
                message=(
                    f"{name} *accepted-unknown* is stale: Review date "
                    f"{review_date_raw} is before today ({today.isoformat()})"
                ),
            )
        )

    return errors
