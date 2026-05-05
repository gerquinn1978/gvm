"""Impact-map validator (P10-C02 — IM-2 referential integrity).

Wraps the shared `_impact_map_parser.load_impact_map()` from
`gvm-design-system/scripts/_impact_map_parser.py` (P7-C03) and surfaces
all parse / FK / schema errors as a list of `ValidationError` records
rather than raising. The shape mirrors `_risk_validator.full_check()`
(discovery ADR-306) so consumers in `/gvm-impact-map` and downstream
share one error vocabulary.

Scope:
- IM-2 implicit-parent FK check across the four levels (P10-C02).
- IM-2 "missing-Impact-level" check (P10-C02): any Actor that has no
  Impacts is an implicit parent and is reported.
- IM-3 Goal ambiguity scan (P10-C03): each Goal is scanned for
  unquantified aspirational verbs against
  `references/ambiguity-indicators.md` plus optional project
  extensions at the impact-map's directory root.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

# `_impact_map_parser` lives in the gvm-design-system skill. Insert its scripts
# dir on sys.path so this module imports cleanly from any cwd. Mirrors the
# established pattern in `_hs1_check.py` and `_sd5_promotion.py`.
_DS_SCRIPTS = Path(__file__).resolve().parents[2] / "gvm-design-system" / "scripts"
if str(_DS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_DS_SCRIPTS))

from _impact_map_parser import (  # noqa: E402
    ImpactMap,
    ImpactMapParseError,
    load_impact_map,
)


@dataclass(frozen=True)
class ValidationError:
    code: str
    message: str


def full_check(
    path: str | os.PathLike[str],
) -> tuple[ImpactMap | None, list[ValidationError]]:
    """Validate an impact-map file. Never raises.

    Returns ``(impact_map, errors)``. Pass condition: ``len(errors) == 0``.
    On parse / FK / schema failure, ``impact_map`` is ``None`` and
    ``errors`` carries one or more ``ValidationError`` entries.
    """
    try:
        impact_map = load_impact_map(path)
    except ImpactMapParseError as exc:
        # The shared parser uses ImpactMapParseError both for malformed
        # tables (schema-level) and for FK mismatches. We surface either
        # under the IM-2 code because both are implicit-parent symptoms
        # at the impact-map level.
        return None, [ValidationError(code="IM-2", message=str(exc))]
    except Exception as exc:  # noqa: BLE001 — last-resort guard for the JSON-safe contract
        return None, [ValidationError(code="schema", message=str(exc))]

    errors: list[ValidationError] = []

    # IM-2 missing-Impact-level: every Actor must have ≥1 Impact. An Actor
    # with zero Impacts means the Deliverables under that Actor's intent
    # are routed through some other Actor's Impact — an implicit parent.
    actor_ids_with_impacts = {i.actor_id for i in impact_map.impacts}
    for actor in impact_map.actors:
        if actor.id not in actor_ids_with_impacts:
            errors.append(
                ValidationError(
                    code="IM-2",
                    message=(
                        f"Actor {actor.id} ({actor.name!r}) has no Impacts — "
                        f"every level must be explicit (no implicit parents)"
                    ),
                )
            )

    # IM-3 Goal ambiguity scan. Imported here to avoid a hard cycle at
    # module import-time (`_ambiguity_scan` imports `ValidationError` from
    # this module).
    from _ambiguity_scan import load_denylist, scan_goal  # noqa: PLC0415

    skill_default = (
        Path(__file__).resolve().parent.parent
        / "references"
        / "ambiguity-indicators.md"
    )
    project_root = Path(path).resolve().parent
    denylist = load_denylist(skill_default, project_root=project_root)
    for goal in impact_map.goals:
        errors.extend(scan_goal(goal, denylist))

    if errors:
        return None, errors
    return impact_map, []
