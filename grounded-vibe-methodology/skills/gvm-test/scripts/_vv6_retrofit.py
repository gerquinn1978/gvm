"""VV-6 retrofit helper (honesty-triad ADR-105 + PP-ADR-604).

One-time migration of `reviews/calibration.md` from schema 0 to schema 1.
Each schema-0 row maps deterministically (`Pass → SHIP_READY`,
`Do not release → NOT_SHIPPABLE`) or asks the practitioner
(`Pass with gaps → DEMO_READY | NOT_SHIPPABLE`). Auto-mapped rows preserve
the original verdict text and record `verdict_under_schema=0`. Manually
mapped rows rewrite the verdict text to the user's choice and record
`verdict_under_schema=1`.

The retrofit is idempotent: invoking ``apply_retrofit`` on a schema-1
calibration raises :class:`VV6AlreadyAppliedError`. The caller (``/gvm-test``
SKILL.md driver) catches this and reports "already applied".
"""

from __future__ import annotations

import dataclasses
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

# Cross-skill import: `_calibration_parser` lives in gvm-design-system.
_DS_SCRIPTS = Path(__file__).resolve().parents[2] / "gvm-design-system" / "scripts"
if str(_DS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_DS_SCRIPTS))

from _calibration_parser import (  # noqa: E402
    Calibration,
    ScoreHistoryRow,
    map_v0_to_v1 as _parser_map_v0_to_v1,
)
from gvm_verdict import Verdict  # noqa: E402


def _map_v0_to_v1(text: str) -> Verdict | None:
    """Wrap `_calibration_parser.map_v0_to_v1` so the canonical
    `gvm_verdict.Verdict` enum is returned (the parser ships a parallel
    `Verdict` enum with identical values but distinct identity — see
    handover Surfaced Requirements).
    """
    parser_verdict = _parser_map_v0_to_v1(text)
    if parser_verdict is None:
        return None
    return Verdict(parser_verdict.value)


@dataclass(frozen=True)
class RowDecision:
    round: int
    original_verdict: str
    auto_mapping: Verdict | None
    needs_manual_choice: bool


@dataclass(frozen=True)
class RetrofitPlan:
    already_applied: bool
    decisions: tuple[RowDecision, ...]
    manual_required: tuple[RowDecision, ...]


class VV6AlreadyAppliedError(Exception):
    """Raised by apply_retrofit when the calibration is already schema 1."""


class MissingManualChoiceError(Exception):
    """Raised by apply_retrofit when a Pass-with-gaps row has no choice."""


_PASS_WITH_GAPS = "Pass with gaps"


def plan_retrofit(calibration: Calibration) -> RetrofitPlan:
    """Classify each score-history row. Pure; safe to call on any schema."""
    if calibration.schema_version >= 1:
        return RetrofitPlan(already_applied=True, decisions=(), manual_required=())

    decisions: list[RowDecision] = []
    for row in calibration.score_history:
        if row.verdict == _PASS_WITH_GAPS:
            decisions.append(
                RowDecision(
                    round=row.round,
                    original_verdict=row.verdict,
                    auto_mapping=None,
                    needs_manual_choice=True,
                )
            )
        else:
            mapped = _map_v0_to_v1(row.verdict)  # may raise UnknownVerdictError
            decisions.append(
                RowDecision(
                    round=row.round,
                    original_verdict=row.verdict,
                    auto_mapping=mapped,
                    needs_manual_choice=False,
                )
            )

    manual = tuple(d for d in decisions if d.needs_manual_choice)
    return RetrofitPlan(
        already_applied=False,
        decisions=tuple(decisions),
        manual_required=manual,
    )


def apply_retrofit(
    calibration: Calibration,
    manual_choices: Mapping[int, Verdict],
) -> Calibration:
    """Build the schema-1 Calibration. Pure.

    ``manual_choices`` maps round number → user's choice for each
    Pass-with-gaps row. Allowed values: ``Verdict.DEMO_READY`` or
    ``Verdict.NOT_SHIPPABLE``. ``Verdict.SHIP_READY`` is rejected — the
    practitioner cannot map a Pass-with-gaps row to Ship-ready (per
    PP-ADR-604).
    """
    if calibration.schema_version >= 1:
        raise VV6AlreadyAppliedError(
            f"calibration is already schema {calibration.schema_version}; "
            "VV-6 retrofit is one-time"
        )

    new_rows: list[ScoreHistoryRow] = []
    for row in calibration.score_history:
        if row.verdict == _PASS_WITH_GAPS:
            choice = manual_choices.get(row.round)
            if choice is None:
                raise MissingManualChoiceError(
                    f"round {row.round}: 'Pass with gaps' requires a manual "
                    "choice (Demo-ready or Not shippable)"
                )
            if choice is Verdict.SHIP_READY:
                raise ValueError(
                    f"round {row.round}: 'Pass with gaps' cannot map to "
                    "Ship-ready; choose Demo-ready or Not shippable"
                )
            new_rows.append(
                dataclasses.replace(
                    row,
                    verdict=choice.value,
                    verdict_under_schema=1,
                )
            )
        else:
            # map_v0_to_v1 raises UnknownVerdictError on garbage; let it propagate.
            _map_v0_to_v1(row.verdict)
            new_rows.append(
                dataclasses.replace(
                    row,
                    verdict=row.verdict,  # preserved verbatim
                    verdict_under_schema=0,
                )
            )

    return dataclasses.replace(
        calibration,
        schema_version=1,
        score_history=tuple(new_rows),
        recurring_findings=(),
    )
