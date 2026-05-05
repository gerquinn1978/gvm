"""IM-4 trace gate for `/gvm-requirements` Phase 5 finalisation (discovery ADR-304).

Every functional requirement (priority Must / Should / Could) must carry an
inline `[impact-deliverable: D-N]` source tag whose `D-N` resolves to a row
in the project's `impact-map.md`. Won't-priority requirements are exempt by
definition (out-of-scope under MoSCoW).

Public surface: :class:`Im4Error`, :func:`check`. The function never raises;
malformed impact-maps are returned as a single sentinel error so the Phase 5
loop can surface the issue to the practitioner without crashing.

The bracket-tag regex lives in `gvm-design-system/scripts/_im_tags.py` so
this module and `_trace_resolver.py` cannot diverge — both call
`parse_impact_deliverable_tag`.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# `_impact_map_parser` and `_im_tags` live in the gvm-design-system skill.
# Mirror the sys.path arithmetic from `_validator.py` (P10-C02) and
# `_hs1_check.py`.
_DS_SCRIPTS = Path(__file__).resolve().parents[2] / "gvm-design-system" / "scripts"
if str(_DS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_DS_SCRIPTS))

from _im_tags import parse_impact_deliverable_tag  # noqa: E402
from _impact_map_parser import (  # noqa: E402
    ImpactMapParseError,
    load_impact_map,
)

# Match a requirement priority line: `**XX-N (Priority) [impact-deliverable: ...]:**`.
# The priority is restricted to the MoSCoW vocabulary so prose like
# `**Note (see also): ...**` does not get spuriously scanned. The bracket span
# is optional here — its absence is itself an IM-4 finding for in-scope
# priorities.
_PRIORITY_RE = r"Must|Should|Could|Won['\u2019]?t|Wont"
_REQ_LINE_RE = re.compile(
    r"\*\*(?P<id>[A-Z]{1,8}-\d+)\s*\(\s*(?P<priority>" + _PRIORITY_RE + r")\s*\)"
    r"\s*(?P<tag_span>\[impact-deliverable:[^\]]*\])?\s*:\*\*",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Im4Error:
    code: str
    requirement_id: str
    message: str


def _is_out_of_scope(priority: str) -> bool:
    """Won't / Wont / WONT — exact match (case-insensitive), with or without
    apostrophe (ASCII or Unicode right-single-quote). Anything else (typo,
    unrecognised priority) is treated as in-scope so the gate flags it rather
    than silently skipping it."""
    normalised = priority.strip().lower().replace("\u2019", "'")
    return normalised in {"won't", "wont"}


def check(
    requirements_path: str | os.PathLike[str],
    impact_map_path: str | os.PathLike[str],
) -> list[Im4Error]:
    """Validate IM-4 trace coverage. Never raises.

    Returns a list of :class:`Im4Error` records, one per disqualifying
    requirement. Empty list = pass. On impact-map parse failure, returns a
    single sentinel error with ``requirement_id == "-"``.
    """
    try:
        impact_map = load_impact_map(impact_map_path)
    except ImpactMapParseError as exc:
        return [
            Im4Error(
                code="IM-4",
                requirement_id="-",
                message=f"impact-map.md could not be loaded: {exc}",
            )
        ]
    except Exception as exc:  # noqa: BLE001 — last-resort: never raise from check()
        return [
            Im4Error(
                code="IM-4",
                requirement_id="-",
                message=f"impact-map.md could not be loaded: {exc}",
            )
        ]

    valid_ids = {d.id for d in impact_map.deliverables}

    text = Path(requirements_path).read_text(encoding="utf-8")

    errors: list[Im4Error] = []
    for m in _REQ_LINE_RE.finditer(text):
        rid = m.group("id")
        priority = m.group("priority")
        tag_span = m.group("tag_span")

        if _is_out_of_scope(priority):
            continue

        if tag_span is None:
            errors.append(
                Im4Error(
                    code="IM-4",
                    requirement_id=rid,
                    message=(
                        f"Requirement {rid} has no [impact-deliverable: D-N] "
                        f"source tag — add a trace or downgrade to Won't"
                    ),
                )
            )
            continue

        deliverable_ids = parse_impact_deliverable_tag(tag_span)
        if not deliverable_ids:
            errors.append(
                Im4Error(
                    code="IM-4",
                    requirement_id=rid,
                    message=(
                        f"Requirement {rid} has an empty or malformed "
                        f"[impact-deliverable: ...] tag"
                    ),
                )
            )
            continue

        missing = [d for d in deliverable_ids if d not in valid_ids]
        if missing:
            errors.append(
                Im4Error(
                    code="IM-4",
                    requirement_id=rid,
                    message=(
                        f"Requirement {rid} references unknown deliverable(s) "
                        f"{', '.join(missing)} — not present in impact-map.md"
                    ),
                )
            )

    def _sort_key(e: Im4Error) -> tuple[str, int, str]:
        # Sort sentinel ("-") first, then by ID prefix and numeric suffix so
        # RE-2 < RE-9 < RE-10 (lexicographic alone gives RE-10 < RE-2 < RE-9).
        m = re.match(r"^([A-Z]+)-(\d+)$", e.requirement_id)
        if m is None:
            return ("", 0, e.requirement_id)
        return (m.group(1), int(m.group(2)), e.requirement_id)

    errors.sort(key=_sort_key)
    return errors
