"""Verdict enum and decision-table evaluator (honesty-triad ADR-105 + ADR-106).

The three-verdict taxonomy (Ship-ready / Demo-ready / Not shippable) is encoded
as a `str`-Enum so `Verdict.SHIP_READY == "Ship-ready"`. The evaluator walks an
ordered Copeland decision table over pre-computed criterion records:

    1. Any VV-4 trigger fired → NOT_SHIPPABLE.
    2. Else, all VV-2 (a, b, c) PASS → SHIP_READY.
    3. Else, all VV-3 (a, b, c, d) PASS → DEMO_READY.
    4. Else → NOT_SHIPPABLE (fall-through default).

`NA` on a VV-2/VV-3 row aggregates as PASS. `NA` on a VV-4 row aggregates as
"trigger not fired". The evaluator is pure: no I/O, no exceptions for benign
input.

OQ-5 branch: when `oq5_applies=True` and VV-2 would have passed, the user's
choice ("ship"/"demo") is honoured; `None` (non-interactive / CI) defaults to
DEMO_READY per ADR-106.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal

_EXPLORE_NNN_RE = re.compile(r"^explore-(\d+)\.md$")


class Verdict(str, Enum):
    SHIP_READY = "Ship-ready"
    DEMO_READY = "Demo-ready"
    NOT_SHIPPABLE = "Not shippable"


CriterionStatus = Literal["PASS", "FAIL", "NA"]


@dataclass(frozen=True)
class Criterion:
    name: str
    status: CriterionStatus
    evidence: str


@dataclass(frozen=True)
class VerdictInputs:
    vv2_a: tuple[CriterionStatus, str]
    vv2_b: tuple[CriterionStatus, str]
    vv2_c: tuple[CriterionStatus, str]
    vv3_a: tuple[CriterionStatus, str]
    vv3_b: tuple[CriterionStatus, str]
    vv3_c: tuple[CriterionStatus, str]
    vv3_d: tuple[CriterionStatus, str]
    vv4_a: tuple[CriterionStatus, str]
    vv4_b: tuple[CriterionStatus, str]
    vv4_c: tuple[CriterionStatus, str]
    vv4_d: tuple[CriterionStatus, str]
    vv4_e: tuple[CriterionStatus, str]
    vv4_f: tuple[CriterionStatus, str]
    oq5_applies: bool = False
    oq5_user_choice: Literal["ship", "demo"] | None = None


@dataclass(frozen=True)
class VerdictResult:
    verdict: Verdict
    criteria: tuple[Criterion, ...] = field(default_factory=tuple)


_VV2_FIELDS = ("vv2_a", "vv2_b", "vv2_c")
_VV3_FIELDS = ("vv3_a", "vv3_b", "vv3_c", "vv3_d")
_VV4_FIELDS = ("vv4_a", "vv4_b", "vv4_c", "vv4_d", "vv4_e", "vv4_f")


def _name(field_name: str) -> str:
    # "vv2_a" -> "VV-2(a)"
    domain, letter = field_name.split("_")
    return f"{domain[:2].upper()}-{domain[2]}({letter})"


def _all_pass(inputs: VerdictInputs, fields: tuple[str, ...]) -> bool:
    return all(getattr(inputs, f)[0] in ("PASS", "NA") for f in fields)


def _any_fired(inputs: VerdictInputs, fields: tuple[str, ...]) -> bool:
    return any(getattr(inputs, f)[0] == "FAIL" for f in fields)


def _criteria_records(inputs: VerdictInputs) -> tuple[Criterion, ...]:
    rows: list[Criterion] = []
    for f in _VV2_FIELDS + _VV3_FIELDS + _VV4_FIELDS:
        status, evidence = getattr(inputs, f)
        rows.append(Criterion(name=_name(f), status=status, evidence=evidence))
    return tuple(rows)


def evaluate(inputs: VerdictInputs) -> VerdictResult:
    """Walk the ordered decision table; return verdict + full criterion list."""
    criteria = _criteria_records(inputs)

    if _any_fired(inputs, _VV4_FIELDS):
        return VerdictResult(verdict=Verdict.NOT_SHIPPABLE, criteria=criteria)

    vv2_pass = _all_pass(inputs, _VV2_FIELDS)
    vv3_pass = _all_pass(inputs, _VV3_FIELDS)

    if inputs.oq5_applies and vv2_pass:
        choice = inputs.oq5_user_choice
        if choice == "ship":
            return VerdictResult(verdict=Verdict.SHIP_READY, criteria=criteria)
        # "demo" or None (non-interactive default)
        return VerdictResult(verdict=Verdict.DEMO_READY, criteria=criteria)

    if vv2_pass:
        return VerdictResult(verdict=Verdict.SHIP_READY, criteria=criteria)
    if vv3_pass:
        return VerdictResult(verdict=Verdict.DEMO_READY, criteria=criteria)
    return VerdictResult(verdict=Verdict.NOT_SHIPPABLE, criteria=criteria)


# ----------------------------------------------------------------- VV-4(d) wiring (P11-C09)


def evaluate_vv4_d(
    test_dir: Path,
    stubs_path: Path | None,
) -> tuple[CriterionStatus, str]:
    """Evaluate VV-4(d) against the latest `test/explore-NNN.md` artefact.

    Returns ``("PASS"|"FAIL", evidence)``.

    Decision rules (per ADR-206 + ADR-207 + Error Handling):
      - No `test_dir` or no `explore-NNN.md` → FAIL ("Ship-ready requires
        ≥1 zero-Critical charter").
      - Highest-NNN report's `runner == None` (charter said "unassigned") →
        PASS with ET-7-warning evidence.
      - Highest-NNN report has ≥1 Critical defect with `not in_stub_path` →
        FAIL.
      - Otherwise → PASS.
      - Parse error on the latest report → FAIL with parse-error evidence.

    Pure boundary helper: never raises; total over its domain.
    """
    if not test_dir.exists() or not test_dir.is_dir():
        return ("FAIL", f"no charter found: {test_dir} does not exist")

    # Numeric NNN key: spec mandates zero-padded three-digit NNN (lex == numeric
    # in that range), but using an integer key is robust to any digit width and
    # to filenames that happen to glob-match but aren't valid (sorts to -1).
    def _nnn_key(p: Path) -> int:
        m = _EXPLORE_NNN_RE.match(p.name)
        return int(m.group(1)) if m else -1

    reports = sorted(test_dir.glob("explore-*.md"), key=_nnn_key)
    reports = [r for r in reports if _nnn_key(r) >= 0]
    if not reports:
        return ("FAIL", f"no charter found in {test_dir} (no explore-*.md files)")

    latest = reports[-1]

    # Cross-skill import: _explore_parser lives under gvm-design-system/scripts/.
    # Resolve the path lazily so tests and runtime both work without environment plumbing.
    design_system_scripts = (
        Path(__file__).resolve().parents[2] / "gvm-design-system" / "scripts"
    )
    if str(design_system_scripts) not in sys.path:
        sys.path.insert(0, str(design_system_scripts))

    try:
        from _explore_parser import load_explore  # local import to defer sys.path mutation
    except ImportError as exc:
        return ("FAIL", f"could not load _explore_parser: {exc}")

    try:
        report = load_explore(latest, stubs_path)
    except Exception as exc:  # parser may raise ExploreParseError, ValueError, OSError
        return ("FAIL", f"parse error on {latest.name}: {exc}")

    if report.runner is None:
        # ADR-207: unassigned-runner charter contributes zero Critical findings;
        # default-pass with ET-7 warning evidence.
        return (
            "PASS",
            f"{latest.name}: charter is unassigned; "
            "ET-7 not yet implemented — warning: this charter contributes "
            "no Critical findings to the verdict",
        )

    non_stub_critical = [
        d for d in report.defects if d.severity == "Critical" and not d.in_stub_path
    ]
    if non_stub_critical:
        ids = ", ".join(d.id for d in non_stub_critical)
        return (
            "FAIL",
            f"{latest.name}: {len(non_stub_critical)} Critical defect(s) "
            f"in non-stub paths: {ids}",
        )

    return (
        "PASS",
        f"{latest.name}: 0 Critical defects in non-stub paths "
        f"({len(report.defects)} total defects)",
    )
