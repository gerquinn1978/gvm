"""RA-6 trace column lookup (discovery ADR-310).

Looks up a Deliverable's risks for the requirements-index "Related Risks"
column. Never raises; missing or malformed input yields ``()`` / ``""``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_GDS = Path(__file__).resolve().parents[2] / "gvm-design-system" / "scripts"
if str(_GDS) not in sys.path:
    sys.path.insert(0, str(_GDS))

from _impact_map_parser import RISK_CODES_ORDER, load_impact_map  # noqa: E402


def risks_for_deliverable(
    impact_map_path: str | os.PathLike[str],
    deliverable_id: str,
) -> tuple[str, ...]:
    """Return risks for ``deliverable_id`` in canonical order. Empty tuple
    on missing deliverable, parse failure, or no-risks."""
    try:
        im = load_impact_map(impact_map_path)
    except Exception:  # noqa: BLE001
        return ()
    for d in im.deliverables:
        if d.id == deliverable_id:
            return tuple(c for c in RISK_CODES_ORDER if c in d.risks)
    return ()


def render_risks_cell(risks: frozenset[str] | tuple[str, ...] | set[str]) -> str:
    """Render risks as ``"V, F"`` in canonical order. Empty input → ``""``."""
    if not risks:
        return ""
    risks_set = set(risks)
    return ", ".join(c for c in RISK_CODES_ORDER if c in risks_set)
