"""Trace resolver for `/gvm-test-cases` (P12-C03, ADR-505).

Resolves a requirement's ``[impact-deliverable: D-N]`` tag through the
impact-map's foreign keys to produce the full discovery-audit chain::

    Goal → Actor → Impact → Deliverable → Requirement

Public surface:
  :class:`Trace` — frozen dataclass holding the five IDs.
  :class:`BrokenTraceError` — raised when any parent FK is unresolvable.
  :func:`resolve` — core resolver; requires caller to supply the deliverable ID.
  :func:`resolve_from_requirement_line` — convenience wrapper that parses the
    ``[impact-deliverable: ...]`` tag first.
  :func:`format_trace` — single source of truth for the trace string; callers
    MUST NOT build their own (per Brooks conceptual-integrity rule).

Multiple-deliverable convention
--------------------------------
When a requirement line carries multiple deliverable IDs
(``[impact-deliverable: D-3, D-7]``), :func:`resolve_from_requirement_line`
resolves the **first** deliverable only and returns a single :class:`Trace`.
Emitting one test case per deliverable is the responsibility of the P12-C05
caller, which iterates over all deliverable IDs and calls
:func:`resolve` for each.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _impact_map_parser import ImpactMap

# ---------------------------------------------------------------------------
# ID validation pattern
# ---------------------------------------------------------------------------

_DELIVERABLE_ID_RE = re.compile(r"^D-\d+$")


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Trace:
    """Full discovery-audit chain for a single requirement–deliverable pair."""

    goal_id: str
    actor_id: str
    impact_id: str
    deliverable_id: str
    requirement_id: str


class BrokenTraceError(Exception):
    """A parent FK failed to resolve in the impact map.

    For example: D-3 references I-99 but the Impacts table has no I-99.
    The :attr:`missing_link` attribute holds the unresolvable ID string
    (e.g. ``"I-99"``) so callers can produce a useful diagnostic message.
    """

    def __init__(self, missing_link: str) -> None:
        super().__init__(f"broken trace: {missing_link}")
        self.missing_link = missing_link


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def resolve(requirement_id: str, deliverable_id: str, impact_map: "ImpactMap") -> Trace:
    """Resolve *deliverable_id* through the impact-map's FK chain.

    Returns a :class:`Trace` with all five IDs populated.

    Raises:
        ValueError: *deliverable_id* does not match ``D-<digits>``.
        BrokenTraceError: any FK in the chain (D→I, I→A, A→G) is absent
            from the impact map; :attr:`BrokenTraceError.missing_link` is
            the first unresolvable ID.
    """
    if not _DELIVERABLE_ID_RE.match(deliverable_id):
        raise ValueError(
            f"deliverable_id {deliverable_id!r} does not match required format D-<digits>"
        )

    # Build lookup dicts for O(1) resolution.
    deliverables_by_id = {d.id: d for d in impact_map.deliverables}
    impacts_by_id = {i.id: i for i in impact_map.impacts}
    actors_by_id = {a.id: a for a in impact_map.actors}
    goals_by_id = {g.id: g for g in impact_map.goals}

    # D-N → Impact
    deliverable = deliverables_by_id.get(deliverable_id)
    if deliverable is None:
        raise BrokenTraceError(deliverable_id)

    # I-M → Actor
    impact = impacts_by_id.get(deliverable.impact_id)
    if impact is None:
        raise BrokenTraceError(deliverable.impact_id)

    # A-K → Goal
    actor = actors_by_id.get(impact.actor_id)
    if actor is None:
        raise BrokenTraceError(impact.actor_id)

    # G-J — must exist
    goal = goals_by_id.get(actor.goal_id)
    if goal is None:
        raise BrokenTraceError(actor.goal_id)

    return Trace(
        goal_id=goal.id,
        actor_id=actor.id,
        impact_id=impact.id,
        deliverable_id=deliverable.id,
        requirement_id=requirement_id,
    )


def resolve_from_requirement_line(
    requirement_line: str,
    requirement_id: str,
    impact_map: "ImpactMap",
) -> Trace | None:
    """Parse the ``[impact-deliverable: ...]`` tag from *requirement_line* and resolve.

    Returns:
        :class:`Trace` for the **first** deliverable ID found in the tag.
        ``None`` when no parseable tag is present — covers both "no tag at
        all" (transitional, requirement not yet tagged) AND "tag inner text
        does not match the ``D-<digits>`` shape" (the regex in
        :mod:`_im_tags` pre-filters to valid IDs, so malformed inner text
        is silently treated as no tag).

    Raises:
        BrokenTraceError: the tag is present and well-formed but a parent
            FK in the impact map fails to resolve.
    """
    # Import here to keep the module importable even when gvm-design-system
    # scripts dir is not on sys.path at module load time.  Callers are
    # responsible for inserting the correct sys.path entry before importing
    # this module (see conftest.py and the cross-skill walk-up pattern used
    # in test_trace_resolver.py).
    from _im_tags import parse_impact_deliverable_tag  # noqa: PLC0415

    ids = parse_impact_deliverable_tag(requirement_line)
    if not ids:
        return None

    # First deliverable wins; P12-C05 caller iterates for multi-deliverable.
    return resolve(requirement_id, ids[0], impact_map)


def format_trace(trace: Trace, test_case_id: str) -> str:
    """Return the ADR-505 canonical trace string with *test_case_id* appended.

    Exact format (U+2192 RIGHTWARDS ARROW between every segment)::

        [Trace: G-J → A-K → I-M → D-N → RE-X → TC-RE-X-NN]

    This is the single source of truth.  Callers MUST NOT build the string
    themselves (Brooks conceptual-integrity rule).
    """
    return (
        f"[Trace: {trace.goal_id} \u2192 {trace.actor_id} \u2192 "
        f"{trace.impact_id} \u2192 {trace.deliverable_id} \u2192 "
        f"{trace.requirement_id} \u2192 {test_case_id}]"
    )
