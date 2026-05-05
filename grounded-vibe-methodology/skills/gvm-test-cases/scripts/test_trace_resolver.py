"""Tests for _trace_resolver.py (P12-C03).

6 test cases covering:
  TC-01: full chain resolves correctly
  TC-02: missing impact link raises BrokenTraceError
  TC-03: untagged requirement line returns None
  TC-04: multiple deliverables on one line — first wins
  TC-05: format_trace produces exact literal string
  TC-06: invalid deliverable ID format raises ValueError
"""

from __future__ import annotations

import sys
from pathlib import Path

# Cross-skill import: add gvm-design-system/scripts to sys.path so
# _impact_map_parser and _im_tags resolve. Walk up from this file's
# location to the skills/ directory, then descend into gvm-design-system.
_GDS = Path(__file__).resolve().parents[2] / "gvm-design-system" / "scripts"
if str(_GDS) not in sys.path:
    sys.path.insert(0, str(_GDS))
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import pytest  # noqa: E402

from _impact_map_parser import (  # noqa: E402
    Actor,
    Deliverable,
    Goal,
    Impact,
    ImpactMap,
    serialise,
)
from _trace_resolver import (  # noqa: E402
    BrokenTraceError,
    Trace,
    format_trace,
    resolve,
    resolve_from_requirement_line,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _write_impact_map(path: Path, **overrides) -> ImpactMap:
    """Write a minimal but valid ImpactMap to *path* and return it.

    D-3 → I-1 → A-1 → G-1 by default. Pass keyword args to override
    individual parts (goals, actors, impacts, deliverables).
    """
    goals = overrides.get(
        "goals",
        (Goal(id="G-1", statement="Increase revenue", metric="ARR", target="10%", deadline="2026-12-31"),),
    )
    actors = overrides.get(
        "actors",
        (Actor(id="A-1", goal_id="G-1", name="Sales Team", description="Sells stuff"),),
    )
    impacts = overrides.get(
        "impacts",
        (Impact(id="I-1", actor_id="A-1", behavioural_change="Closes more deals", direction="increase"),),
    )
    deliverables = overrides.get(
        "deliverables",
        (Deliverable(id="D-3", impact_id="I-1", title="Dashboard", type="feature"),),
    )
    im = ImpactMap(
        goals=goals,
        actors=actors,
        impacts=impacts,
        deliverables=deliverables,
        changelog=(),
    )
    path.write_text(serialise(im), encoding="utf-8")
    return im


def _load_impact_map(path: Path) -> ImpactMap:
    """Load ImpactMap via the parser (not mocked, per spec)."""
    from _impact_map_parser import load_impact_map  # noqa: PLC0415

    return load_impact_map(path)


# ---------------------------------------------------------------------------
# TC-01: Full chain D-3 → I-1 → A-1 → G-1
# ---------------------------------------------------------------------------


def test_full_chain_resolves(tmp_path: Path):
    """TC-EBT-5-01: resolve() returns correct Trace when full FK chain exists."""
    im_path = tmp_path / "impact-map.md"
    _write_impact_map(im_path)
    im = _load_impact_map(im_path)

    trace = resolve("RE-5", "D-3", im)

    assert isinstance(trace, Trace)
    assert trace.goal_id == "G-1"
    assert trace.actor_id == "A-1"
    assert trace.impact_id == "I-1"
    assert trace.deliverable_id == "D-3"
    assert trace.requirement_id == "RE-5"


# ---------------------------------------------------------------------------
# TC-02: Missing link raises BrokenTraceError
# ---------------------------------------------------------------------------


def test_missing_impact_raises_broken_trace_error(tmp_path: Path):
    """TC-EBT-5-02: D-3 references I-99 which is absent → BrokenTraceError."""
    # Manually construct an ImpactMap where D-3 points to I-99 but I-99
    # does not exist. We bypass the parser's FK validation by constructing
    # the dataclass directly (parser would reject it).
    im = ImpactMap(
        goals=(Goal(id="G-1", statement="s", metric="m", target="t", deadline="2026-12-31"),),
        actors=(Actor(id="A-1", goal_id="G-1", name="n", description="d"),),
        impacts=(Impact(id="I-1", actor_id="A-1", behavioural_change="b", direction="increase"),),
        # D-3 references I-99 which is absent from impacts table
        deliverables=(Deliverable(id="D-3", impact_id="I-99", title="Dashboard", type="feature"),),
        changelog=(),
    )

    with pytest.raises(BrokenTraceError) as exc_info:
        resolve("RE-5", "D-3", im)

    err = exc_info.value
    assert err.missing_link == "I-99"
    assert "I-99" in str(err)


# ---------------------------------------------------------------------------
# TC-03: Untagged requirement line returns None
# ---------------------------------------------------------------------------


def test_untagged_requirement_returns_none(tmp_path: Path):
    """resolve_from_requirement_line returns None when no tag is present."""
    im_path = tmp_path / "impact-map.md"
    _write_impact_map(im_path)
    im = _load_impact_map(im_path)

    line = "**RE-7 (Must):** the system shall do something without any tag"
    result = resolve_from_requirement_line(line, "RE-7", im)

    assert result is None


# ---------------------------------------------------------------------------
# TC-04: Multiple deliverables on one line — first wins
# ---------------------------------------------------------------------------


def test_multiple_deliverables_first_wins(tmp_path: Path):
    """First deliverable ID wins when multiple appear in the tag."""
    im_path = tmp_path / "impact-map.md"
    # D-3 and D-7 both present; D-3 → I-1 → A-1 → G-1
    im_raw = ImpactMap(
        goals=(Goal(id="G-1", statement="s", metric="m", target="t", deadline="2026-12-31"),),
        actors=(Actor(id="A-1", goal_id="G-1", name="n", description="d"),),
        impacts=(Impact(id="I-1", actor_id="A-1", behavioural_change="b", direction="increase"),),
        deliverables=(
            Deliverable(id="D-3", impact_id="I-1", title="Dashboard", type="feature"),
            Deliverable(id="D-7", impact_id="I-1", title="Report", type="report"),
        ),
        changelog=(),
    )
    im_path.write_text(serialise(im_raw), encoding="utf-8")
    im = _load_impact_map(im_path)

    line = "**RE-9 (Must) [impact-deliverable: D-3, D-7]:** shall do both"
    trace = resolve_from_requirement_line(line, "RE-9", im)

    assert trace is not None
    assert trace.deliverable_id == "D-3"
    assert trace.requirement_id == "RE-9"


# ---------------------------------------------------------------------------
# TC-05: format_trace produces exact literal string
# ---------------------------------------------------------------------------


def test_format_trace_exact_string():
    """format_trace() produces the exact string mandated by ADR-505."""
    trace = Trace(
        goal_id="G-1",
        actor_id="A-1",
        impact_id="I-1",
        deliverable_id="D-3",
        requirement_id="RE-5",
    )
    result = format_trace(trace, "TC-RE-5-01")

    assert result == "[Trace: G-1 → A-1 → I-1 → D-3 → RE-5 → TC-RE-5-01]"


# ---------------------------------------------------------------------------
# TC-06: Invalid deliverable ID format raises ValueError
# ---------------------------------------------------------------------------


def test_invalid_deliverable_id_raises_value_error(tmp_path: Path):
    """resolve() raises ValueError when deliverable_id is not a valid D-N ID."""
    im_path = tmp_path / "impact-map.md"
    _write_impact_map(im_path)
    im = _load_impact_map(im_path)

    with pytest.raises(ValueError):
        resolve("RE-5", "INVALID-ID", im)


# ---------------------------------------------------------------------------
# M-04: resolve_from_requirement_line treats malformed tag content as absent
# ---------------------------------------------------------------------------


def test_resolve_from_requirement_line_malformed_tag_returns_none(tmp_path: Path):
    """The tag regex (`TAG_RE` in `_im_tags`) pre-filters to ``D-<digits>``,
    so a tag whose inner text does not match the shape (e.g.
    ``[impact-deliverable: NOT-A-VALID-ID]``) is treated as if no tag were
    present and the wrapper returns ``None``. This pins the contract: the
    wrapper does not surface a "malformed tag" signal — only the
    "broken FK" path raises (`BrokenTraceError`, exercised elsewhere)."""
    im_path = tmp_path / "impact-map.md"
    _write_impact_map(im_path)
    im = _load_impact_map(im_path)

    line = "**RE-99 (MUST):** thing. [impact-deliverable: NOT-A-VALID-ID]"
    assert resolve_from_requirement_line(line, "RE-99", im) is None
