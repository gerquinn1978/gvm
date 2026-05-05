"""IM-6 persona/Actor coupling check (discovery ADR-311).

Reads `requirements.md` for personas declared under an `## Persona[s]?`
H2 section (where each persona is a `**<Name> ...**` bold marker — the
established `/gvm-requirements` skill convention) and checks that each
persona name corresponds to an Actor in `impact-map.md` (case-insensitive
on the Actor's `name`; first match wins; ties broken by Actor `id` order).

Returns a list of warnings, never raises. On parse error of either file,
returns a single sentinel warning with ``persona_name == "-"`` so the
Phase-5 caller can branch.

Note: an absent ``## Persona[s]?`` section returns ``[]`` — indistinguishable
from "section present, all personas matched". Callers cannot tell the two
cases apart from this function's output alone.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_GDS = Path(__file__).resolve().parents[2] / "gvm-design-system" / "scripts"
if str(_GDS) not in sys.path:
    sys.path.insert(0, str(_GDS))

from _impact_map_parser import Actor, load_impact_map  # noqa: E402

_PERSONA_HEADER_RE = re.compile(r"^##\s+Personas?\s*$", re.MULTILINE)
_NEXT_H2_RE = re.compile(r"^##\s+\S", re.MULTILINE)
_BOLD_NAME_RE = re.compile(r"\*\*([^*]+?)\*\*")


@dataclass(frozen=True)
class Im6Warning:
    persona_name: str
    message: str


def _id_key(a: Actor) -> tuple[int, str]:
    """Sort key for actors: numeric suffix then full id.

    `Actor.id` matches ``r"^A-\\d+$"`` (enforced by the parser) so the
    ``int(suffix)`` cast is total. Falling back to ``(0, a.id)`` on parse
    failure preserves a stable order if the invariant ever weakens.
    """
    suffix = a.id.split("-", 1)[-1]
    return (int(suffix), a.id) if suffix.isdigit() else (0, a.id)


def _extract_personas(requirements_text: str) -> list[str]:
    m = _PERSONA_HEADER_RE.search(requirements_text)
    if m is None:
        return []
    section_start = m.end()
    rest = requirements_text[section_start:]
    next_m = _NEXT_H2_RE.search(rest)
    section_body = rest if next_m is None else rest[: next_m.start()]

    personas: list[str] = []
    seen: set[str] = set()
    for line in section_body.splitlines():
        bold = _BOLD_NAME_RE.search(line)
        if bold is None:
            continue
        first_token = bold.group(1).split()[0] if bold.group(1).split() else ""
        if first_token and first_token not in seen:
            seen.add(first_token)
            personas.append(first_token)
    return personas


def persona_actor_coupling(
    requirements_path: str | os.PathLike[str],
    impact_map_path: str | os.PathLike[str],
) -> list[Im6Warning]:
    try:
        req_text = Path(requirements_path).read_text(encoding="utf-8")
    except OSError as exc:
        return [
            Im6Warning(persona_name="-", message=f"Could not read requirements: {exc}")
        ]

    try:
        im = load_impact_map(impact_map_path)
    except Exception as exc:  # noqa: BLE001
        return [
            Im6Warning(persona_name="-", message=f"Could not load impact-map: {exc}")
        ]

    personas = _extract_personas(req_text)
    if not personas:
        return []

    # Sort actors by id so that ties on case-insensitive name match resolve
    # to the lowest id deterministically. See `_id_key` for the numeric vs
    # lexicographic tie-break (ADR-311 says "ties broken by id order" —
    # logical/numeric, not lexicographic).
    actors_by_name: dict[str, str] = {}  # lower(name) -> id of first match
    for actor in sorted(im.actors, key=_id_key):
        key = actor.name.lower()
        if key not in actors_by_name:
            actors_by_name[key] = actor.id

    warnings: list[Im6Warning] = []
    for persona in personas:
        if persona.lower() not in actors_by_name:
            warnings.append(
                Im6Warning(
                    persona_name=persona,
                    message=(
                        f"Persona '{persona}' in requirements.md has no "
                        "corresponding Actor in impact-map.md — the impact map "
                        "may be incomplete."
                    ),
                )
            )
    return warnings
