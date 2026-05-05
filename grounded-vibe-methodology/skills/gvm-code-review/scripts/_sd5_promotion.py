"""SD-5 severity-promotion helper (honesty-triad ADR-109).

Pure classifier for Panel-E findings. Reads the current `recurring_findings`
table from a parsed `Calibration`, classifies each new finding's severity by
consecutive-round count, and emits build-check promotions when a signature
hits round 3. No file I/O — caller owns load/write.

Round count = ``current_round − first_round + 1`` when ``last_round ==
current_round − 1`` (consecutive). A gap resets the row to round 1.
Resolution (signature absent this round) drops the row from
``updated_recurring``.
"""

from __future__ import annotations

import hashlib
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

# `_calibration_parser` lives in the gvm-design-system skill. Insert its
# scripts dir on sys.path so this module imports cleanly when invoked from
# any cwd. The path is relative to this file, not the cwd.
_DS_SCRIPTS = Path(__file__).resolve().parents[2] / "gvm-design-system" / "scripts"
if str(_DS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_DS_SCRIPTS))

from _calibration_parser import RecurringFinding  # noqa: E402


@dataclass(frozen=True)
class FindingInput:
    file_path: str
    symbol: str
    heuristic_class: str
    violation_type: str
    initial_severity: str


@dataclass(frozen=True)
class PromotedFinding:
    file_path: str
    symbol: str
    heuristic_class: str
    violation_type: str
    severity: str
    signature: str
    round_count: int


@dataclass(frozen=True)
class BuildCheckPromotion:
    signature: str
    heuristic_class: str
    file_path: str
    symbol: str


@dataclass(frozen=True)
class SD5Result:
    promoted_findings: tuple[PromotedFinding, ...]
    updated_recurring: tuple[RecurringFinding, ...]
    build_check_promotions: tuple[BuildCheckPromotion, ...]


def compute_signature(
    file_path: str, symbol: str, heuristic_class: str, violation_type: str
) -> str:
    """First 12 hex chars of sha1 over the four-field key (ADR-109)."""
    key = f"{file_path}::{symbol}::{heuristic_class}::{violation_type}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def apply_sd5(
    findings: Sequence[FindingInput],
    current_recurring: Sequence[RecurringFinding],
    current_round: int,
) -> SD5Result:
    """Classify each finding's severity by round-count and emit BC promotions.

    The caller supplies *current_round* (typically
    ``len(calibration.score_history) + 1``) and the current
    ``recurring_findings`` tuple. The result's ``updated_recurring`` is the
    full new table to write back: rows whose signatures don't appear in
    *findings* this round are dropped (resolution).
    """
    if current_round < 1:
        raise ValueError(f"current_round must be >= 1, got {current_round}")

    existing_by_sig: dict[str, RecurringFinding] = {
        r.signature: r for r in current_recurring
    }

    promoted: list[PromotedFinding] = []
    new_rows_by_sig: dict[str, RecurringFinding] = {}
    bc_promotions: list[BuildCheckPromotion] = []

    for f in findings:
        sig = compute_signature(
            f.file_path, f.symbol, f.heuristic_class, f.violation_type
        )

        prior = existing_by_sig.get(sig)
        consecutive = prior is not None and prior.last_round == current_round - 1

        if consecutive:
            assert prior is not None
            round_count = current_round - prior.first_round + 1
            # consecutive → last_round == current_round - 1, so count is
            # necessarily >= 2; the elevation always fires.
            severity = "Critical"
            new_history = f"{prior.severity_history},{severity}"
            new_row = RecurringFinding(
                signature=sig,
                first_round=prior.first_round,
                last_round=current_round,
                severity_history=new_history,
            )
            if round_count == 3:
                bc_promotions.append(
                    BuildCheckPromotion(
                        signature=sig,
                        heuristic_class=f.heuristic_class,
                        file_path=f.file_path,
                        symbol=f.symbol,
                    )
                )
        else:
            # New signature OR a gap → fresh round-1 row; severity unchanged.
            round_count = 1
            severity = f.initial_severity
            new_row = RecurringFinding(
                signature=sig,
                first_round=current_round,
                last_round=current_round,
                severity_history=f.initial_severity,
            )

        promoted.append(
            PromotedFinding(
                file_path=f.file_path,
                symbol=f.symbol,
                heuristic_class=f.heuristic_class,
                violation_type=f.violation_type,
                severity=severity,
                signature=sig,
                round_count=round_count,
            )
        )

        # Duplicate signatures within one round: keep the first row written.
        new_rows_by_sig.setdefault(sig, new_row)

    return SD5Result(
        promoted_findings=tuple(promoted),
        updated_recurring=tuple(new_rows_by_sig.values()),
        build_check_promotions=tuple(bc_promotions),
    )
