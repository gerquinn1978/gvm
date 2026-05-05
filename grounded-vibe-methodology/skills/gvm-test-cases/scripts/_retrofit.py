"""EBT-6 retrofit mode for /gvm-test-cases (P12-C06, ADR-506).

Walk every MUST requirement, find those lacking an `[EXAMPLE]`-shape
test, and produce draft retrofit candidates (input + positive +
negative) for the practitioner to review. Pure, read-only — never
writes. Reuses `_ebt_validator.audit(...)` (Hunt & Thomas — DRY).

Public surface: `scan`, `RetrofitReport`, `RetrofitCandidate`.

Heuristic generation rules are documented inline near each helper so
downstream readers can correlate the code to ADR-506 directly.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from _ebt_validator import parse_requirements, audit

# ---------------------------------------------------------------------------
# Public dataclasses (frozen — Ramalho)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetrofitCandidate:
    requirement_id: str
    requirement_text: str
    suggested_input: str
    suggested_positive: str
    suggested_negative: str
    rationale: str
    draft_block: str


@dataclass(frozen=True)
class RetrofitReport:
    total_must_requirements: int
    requirements_already_covered: int
    candidates: tuple[RetrofitCandidate, ...]


# ---------------------------------------------------------------------------
# Requirement line lookup (we need the prose, not just the id; reuse the
# validator's parser for *which* requirements are MUST + uncovered, but
# walk the file once more to capture the line text for heuristics).
# ---------------------------------------------------------------------------

_REQ_LINE_RE = re.compile(r"^\*\*([A-Z]+-\d+)\s*\(([^)]+)\)\*?\*?\s*(.*)$")


def _index_requirement_lines(req_path: Path) -> dict[str, str]:
    """Return a mapping ``requirement_id -> stripped requirement line``.

    The validator already parses ids/priorities; here we only need the
    prose for heuristic input/positive/negative extraction.
    """
    out: dict[str, str] = {}
    for raw in req_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        m = _REQ_LINE_RE.match(line)
        if m:
            out[m.group(1)] = line
    return out


# ---------------------------------------------------------------------------
# Heuristic helpers
# ---------------------------------------------------------------------------

# Antonym pairs (small, explicit, both directions). No ML, no thesaurus.
_ANTONYMS: dict[str, str] = {}
for _a, _b in (
    ("included", "excluded"),
    ("valid", "invalid"),
    ("accept", "reject"),
    ("accepts", "rejects"),
    ("accepted", "rejected"),
    ("pass", "fail"),
    ("passes", "fails"),
    ("passed", "failed"),
    ("enabled", "disabled"),
    ("allowed", "denied"),
    ("allow", "deny"),
):
    _ANTONYMS[_a] = _b
    _ANTONYMS[_b] = _a


_QUOTED_RE = re.compile(r'"([^"\n]+)"')
_INPUT_CUE_RE = re.compile(
    r"\b(?:for|given|with|when)\s+([A-Za-z][A-Za-z0-9_-]*)",
    re.IGNORECASE,
)
_OUTCOME_CUE_RE = re.compile(
    r"\b(?:shall|MUST|returns|return|produces|produce|accept|accepts|reject|rejects)\b\s+([A-Za-z][A-Za-z0-9_-]*)",
)
_EXPLICIT_NEG_RE = re.compile(
    r'MUST\s+NOT\s+contain\s+"([^"\n]+)"',
)


def _extract_input(text: str) -> tuple[str, str]:
    """Return ``(suggested_input, rationale_fragment)``."""
    m = _QUOTED_RE.search(text)
    if m:
        return f'"{m.group(1)}"', "input: quoted literal in requirement"
    m = _INPUT_CUE_RE.search(text)
    if m:
        return m.group(1), f"input: cue '{m.group(0).strip()}'"
    return "<TBD: practitioner-supplied>", "input: no cue — practitioner-supplied"


def _extract_positive(text: str) -> tuple[str, str]:
    """Return ``(suggested_positive, rationale_fragment)``."""
    m = _OUTCOME_CUE_RE.search(text)
    if m:
        # The token following the outcome verb (e.g. "shall accept" → "accept"
        # — but our regex captured the noun *after* the verb. We actually
        # want the verb itself when it's an action verb, so prefer the verb
        # if it is a known antonym key.
        verb = m.group(0).split()[0]
        if verb.lower() in _ANTONYMS:
            return verb, "positive: outcome verb is antonym key"
        return m.group(1), f"positive: token after '{verb}'"
    return "<TBD: positive token from requirement>", "positive: no outcome cue"


def _extract_negative(text: str, positive: str) -> tuple[str, str]:
    """Return ``(suggested_negative, rationale_fragment)``."""
    m = _EXPLICIT_NEG_RE.search(text)
    if m:
        return f'"{m.group(1)}"', "negative: explicit MUST NOT in requirement"
    pos_key = positive.strip().strip('"').lower()
    if pos_key in _ANTONYMS:
        return _ANTONYMS[
            pos_key
        ], f"negative: antonym pair {pos_key}↔{_ANTONYMS[pos_key]}"
    return (
        "<TBD: counterexample value to add>",
        "negative: no antonym — practitioner-supplied",
    )


def _build_draft_block(
    requirement_id: str,
    suggested_input: str,
    suggested_positive: str,
    suggested_negative: str,
) -> str:
    """Assemble the ADR-502 three-element example block."""
    return (
        f"TC-{requirement_id}-NN: <derived from requirement> [EXAMPLE]\n"
        f"Input: {suggested_input}\n"
        f"Given <precondition placeholder>\n"
        f"When the system processes the input\n"
        f"Then the output MUST contain: {suggested_positive}\n"
        f"And the output MUST NOT contain: {suggested_negative}\n"
        f"[Requirement: {requirement_id}] [Priority: MUST]\n"
        f"[Trace: not-yet-traced]\n"
    )


def _make_candidate(requirement_id: str, requirement_text: str) -> RetrofitCandidate:
    suggested_input, ri = _extract_input(requirement_text)
    suggested_positive, rp = _extract_positive(requirement_text)
    suggested_negative, rn = _extract_negative(requirement_text, suggested_positive)
    rationale = "; ".join((ri, rp, rn))
    draft_block = _build_draft_block(
        requirement_id, suggested_input, suggested_positive, suggested_negative
    )
    return RetrofitCandidate(
        requirement_id=requirement_id,
        requirement_text=requirement_text,
        suggested_input=suggested_input,
        suggested_positive=suggested_positive,
        suggested_negative=suggested_negative,
        rationale=rationale,
        draft_block=draft_block,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def scan(
    test_cases_path: Path | str,
    requirements_path: Path | str,
) -> RetrofitReport:
    """Walk MUST requirements; produce candidates for those lacking
    an `[EXAMPLE]`-shape test.

    DRY: gap detection is delegated to `_ebt_validator.audit`.
    """
    tc_path = Path(test_cases_path)
    req_path = Path(requirements_path)

    report = audit(tc_path, req_path)

    # MUST gaps == retrofit candidates. The validator emits gap.priority
    # only for MUST requirements (`coverage_gaps` is filtered MUST-only)
    # and either `missing="any-test"` or `missing="example-test"` or
    # `missing="negative-assertion"`. All three classes mean "no
    # example-based test exists" — they are all retrofit-targets.
    must_gap_ids = [
        g.requirement_id for g in report.coverage_gaps if g.priority == "MUST"
    ]

    # Reuse the validator's own parser for (id, priority) — no
    # reimplementation of priority normalisation here (DRY: Hunt &
    # Thomas). A second pass over the file captures the *prose* line
    # for heuristic extraction; the validator does not retain it.
    req_lines = _index_requirement_lines(req_path)
    parsed = parse_requirements(req_path.read_text(encoding="utf-8"))
    total_must = sum(1 for _id, prio in parsed if prio == "MUST")
    already_covered = total_must - len(must_gap_ids)

    candidates = tuple(
        _make_candidate(req_id, req_lines.get(req_id, req_id))
        for req_id in must_gap_ids
    )

    return RetrofitReport(
        total_must_requirements=total_must,
        requirements_already_covered=already_covered,
        candidates=candidates,
    )


# ---------------------------------------------------------------------------
# CLI entry — `python -m _retrofit --requirements R --test-cases T`
# ---------------------------------------------------------------------------


def _format_report(report: RetrofitReport) -> str:
    lines: list[str] = []
    lines.append("EBT-6 Retrofit Report")
    lines.append("=" * 21)
    lines.append(f"MUST requirements:           {report.total_must_requirements}")
    lines.append(f"Already covered (EBT shape): {report.requirements_already_covered}")
    lines.append(f"Retrofit candidates:         {len(report.candidates)}")
    lines.append("")
    for i, cand in enumerate(report.candidates, 1):
        lines.append(f"--- Candidate {i}: {cand.requirement_id} ---")
        lines.append(f"Rationale: {cand.rationale}")
        lines.append("")
        lines.append(cand.draft_block)
    return "\n".join(lines)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="_retrofit",
        description="EBT-6 retrofit candidate generator (read-only).",
    )
    parser.add_argument("--requirements", required=True, help="Path to requirements.md")
    parser.add_argument("--test-cases", required=True, help="Path to test-cases.md")
    args = parser.parse_args(argv)

    report = scan(args.test_cases, args.requirements)
    print(_format_report(report))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
