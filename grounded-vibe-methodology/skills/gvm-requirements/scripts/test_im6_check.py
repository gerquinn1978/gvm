"""Tests for P10-C09 — IM-6 persona/Actor coupling check (ADR-311)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_GDS = Path(__file__).resolve().parents[2] / "gvm-design-system" / "scripts"
if str(_GDS) not in sys.path:
    sys.path.insert(0, str(_GDS))
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _im6_check import Im6Warning, persona_actor_coupling  # noqa: E402
from _impact_map_parser import (  # noqa: E402
    Actor,
    Deliverable,
    Goal,
    Impact,
    ImpactMap,
    serialise,
)


def _write_im(path: Path, *actors: Actor) -> Path:
    im = ImpactMap(
        goals=(
            Goal(
                id="G-1", statement="x", metric="m", target="t", deadline="2026-12-31"
            ),
        ),
        actors=actors,
        impacts=(
            Impact(
                id="I-1",
                actor_id=actors[0].id,
                behavioural_change="x",
                direction="increase",
            ),
        ),
        deliverables=(
            Deliverable(id="D-1", impact_id="I-1", title="x", type="feature"),
        ),
        changelog=(),
    )
    path.write_text(serialise(im), encoding="utf-8")
    return path


def _write_req(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_persona_matches_actor_silent(tmp_path: Path):
    im = _write_im(
        tmp_path / "im.md",
        Actor(id="A-1", goal_id="G-1", name="Alice", description="d"),
    )
    req = _write_req(
        tmp_path / "requirements.md",
        "# Requirements\n\n## Personas\n\n**Alice** is the primary user.\n",
    )
    assert persona_actor_coupling(req, im) == []


def test_persona_case_insensitive_match(tmp_path: Path):
    im = _write_im(
        tmp_path / "im.md",
        Actor(id="A-1", goal_id="G-1", name="Alice", description="d"),
    )
    req = _write_req(
        tmp_path / "requirements.md",
        "## Personas\n\n**alice** in lowercase.\n",
    )
    assert persona_actor_coupling(req, im) == []


def test_persona_not_in_actors_warned(tmp_path: Path):
    im = _write_im(
        tmp_path / "im.md",
        Actor(id="A-1", goal_id="G-1", name="Alice", description="d"),
    )
    req = _write_req(
        tmp_path / "requirements.md",
        "## Personas\n\n**Bob** is a stranger.\n",
    )
    warnings = persona_actor_coupling(req, im)
    assert len(warnings) == 1
    assert warnings[0].persona_name == "Bob"
    assert "Bob" in warnings[0].message
    assert "no corresponding Actor" in warnings[0].message
    assert "impact map may be incomplete" in warnings[0].message


def test_no_persona_section_returns_empty(tmp_path: Path):
    im = _write_im(
        tmp_path / "im.md",
        Actor(id="A-1", goal_id="G-1", name="Alice", description="d"),
    )
    req = _write_req(
        tmp_path / "requirements.md", "# Requirements\n\n## Goals\n**Bob** here.\n"
    )
    assert persona_actor_coupling(req, im) == []


def test_multiple_personas(tmp_path: Path):
    im = _write_im(
        tmp_path / "im.md",
        Actor(id="A-1", goal_id="G-1", name="Alice", description="d"),
        Actor(id="A-2", goal_id="G-1", name="Carol", description="d"),
    )
    req = _write_req(
        tmp_path / "requirements.md",
        "## Personas\n\n**Alice** primary\n\n**Bob** missing\n\n**Carol** also here\n",
    )
    warnings = persona_actor_coupling(req, im)
    assert [w.persona_name for w in warnings] == ["Bob"]


def test_first_match_wins_on_duplicate_actor_names(tmp_path: Path):
    # Two Actors with the same name (case-insensitive). Persona "alice"
    # matches one of them — we don't care which but it should be silent.
    # `_check_unique_ids` enforces unique IDs but not unique names.
    im = _write_im(
        tmp_path / "im.md",
        Actor(id="A-2", goal_id="G-1", name="Alice", description="late"),
        Actor(id="A-1", goal_id="G-1", name="Alice", description="early"),
    )
    req = _write_req(tmp_path / "requirements.md", "## Personas\n\n**alice**\n")
    assert persona_actor_coupling(req, im) == []


def test_persona_section_terminates_at_next_h2(tmp_path: Path):
    im = _write_im(
        tmp_path / "im.md",
        Actor(id="A-1", goal_id="G-1", name="Alice", description="d"),
    )
    req = _write_req(
        tmp_path / "requirements.md",
        "## Personas\n\n**Alice** primary\n\n## Functional Requirements\n\n**Bob** is a fake persona elsewhere.\n",
    )
    # Bob should NOT be extracted because it is outside the personas section.
    assert persona_actor_coupling(req, im) == []


def test_parse_error_yields_sentinel(tmp_path: Path):
    req = _write_req(tmp_path / "requirements.md", "## Personas\n**Alice**\n")
    nonexistent = tmp_path / "no-such.md"
    warnings = persona_actor_coupling(req, nonexistent)
    assert len(warnings) == 1
    assert warnings[0].persona_name == "-"


def test_im6warning_dataclass_is_frozen():
    w = Im6Warning(persona_name="x", message="y")
    with pytest.raises(AttributeError):
        w.persona_name = "z"  # type: ignore[misc]


def test_actor_id_tie_break_is_numeric_not_lexicographic():
    """A-2 must sort before A-10 (numeric), not after (lexicographic).

    Direct unit test of the sort key — independent of the parser fixture
    (which forbids duplicate ids and has its own ordering invariants).
    """
    from _im6_check import _id_key

    actors = (
        Actor(id="A-10", goal_id="G-1", name="x", description="d"),
        Actor(id="A-2", goal_id="G-1", name="x", description="d"),
    )
    sorted_ids = [a.id for a in sorted(actors, key=_id_key)]
    assert sorted_ids == ["A-2", "A-10"]


def test_persona_h2_singular_or_plural(tmp_path: Path):
    im = _write_im(
        tmp_path / "im.md",
        Actor(id="A-1", goal_id="G-1", name="Alice", description="d"),
    )
    # Singular "Persona" header
    req1 = tmp_path / "req1.md"
    req1.write_text("## Persona\n\n**Bob**\n", encoding="utf-8")
    assert len(persona_actor_coupling(req1, im)) == 1
    # Plural "Personas" header
    req2 = tmp_path / "req2.md"
    req2.write_text("## Personas\n\n**Bob**\n", encoding="utf-8")
    assert len(persona_actor_coupling(req2, im)) == 1
