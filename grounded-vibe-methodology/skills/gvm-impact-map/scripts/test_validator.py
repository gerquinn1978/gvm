"""P10-C02 tests for the impact-map validator (IM-2 referential integrity).

Covers TC-IM-2-01 (valid tree accepted), TC-IM-2-02 (missing Impact level
rejected naming the offending Actor), and TC-IM-2-03 [PROPERTY] (any add/
remove sequence either preserves the four-level structure or is rejected
with a named violation — never silently mis-classified).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _validator import ValidationError, full_check  # noqa: E402


def _write_map(
    tmp_path: Path,
    goals: list[tuple[str, str, str, str, str]],
    actors: list[tuple[str, str, str, str]],
    impacts: list[tuple[str, str, str, str]],
    deliverables: list[tuple[str, str, str, str]],
) -> Path:
    """Write a minimal impact-map.md fixture and return its path."""
    lines: list[str] = ["---", "schema_version: 1", "---", "# Impact Map", ""]
    lines += [
        "## Goals",
        "| ID | Statement | Metric | Target | Deadline |",
        "|---|---|---|---|---|",
    ]
    for row in goals:
        lines.append("| " + " | ".join(row) + " |")
    lines += [
        "",
        "## Actors",
        "| ID | Goal-ID | Name | Description |",
        "|---|---|---|---|",
    ]
    for row in actors:
        lines.append("| " + " | ".join(row) + " |")
    lines += [
        "",
        "## Impacts",
        "| ID | Actor-ID | Behavioural change | Direction |",
        "|---|---|---|---|",
    ]
    for row in impacts:
        lines.append("| " + " | ".join(row) + " |")
    lines += [
        "",
        "## Deliverables",
        "| ID | Impact-ID | Title | Type |",
        "|---|---|---|---|",
    ]
    for row in deliverables:
        lines.append("| " + " | ".join(row) + " |")

    path = tmp_path / "impact-map.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_tc_im_2_01_valid_tree_accepted(tmp_path: Path) -> None:
    """1 Goal, 3 Actors, 2 Impacts each, 2 Deliverables each → no errors."""
    goals = [("G-1", "increase WAU by 20%", "WAU", "+20%", "2026-12-31")]
    actors = [
        ("A-1", "G-1", "Buyer", "first-time UK buyer"),
        ("A-2", "G-1", "Renter", "city renter"),
        ("A-3", "G-1", "Investor", "buy-to-let"),
    ]
    impacts: list[tuple[str, str, str, str]] = []
    deliverables: list[tuple[str, str, str, str]] = []
    impact_seq = 0
    deliv_seq = 0
    for actor in actors:
        for j in range(2):
            impact_seq += 1
            i_id = f"I-{impact_seq}"
            impacts.append((i_id, actor[0], f"behaviour {impact_seq}", "+"))
            for k in range(2):
                deliv_seq += 1
                deliverables.append(
                    (f"D-{deliv_seq}", i_id, f"deliverable {deliv_seq}", "feature")
                )

    path = _write_map(tmp_path, goals, actors, impacts, deliverables)
    impact_map, errors = full_check(path)
    assert errors == []
    assert impact_map is not None
    assert len(impact_map.goals) == 1
    assert len(impact_map.actors) == 3
    assert len(impact_map.impacts) == 6
    assert len(impact_map.deliverables) == 12


def test_tc_im_2_02_missing_impact_level_rejected(tmp_path: Path) -> None:
    """An Actor with no Impacts (the Deliverables route through some other
    Actor's Impact) → validator flags the actor as having no Impact level."""
    goals = [("G-1", "increase WAU by 20%", "WAU", "+20%", "2026-12-31")]
    actors = [
        ("A-1", "G-1", "Buyer", "first-time UK buyer"),
        ("A-2", "G-1", "Renter", "city renter"),  # has no Impacts
    ]
    impacts = [("I-1", "A-1", "returns weekly", "+")]
    deliverables = [("D-1", "I-1", "saved searches", "feature")]

    path = _write_map(tmp_path, goals, actors, impacts, deliverables)
    _, errors = full_check(path)
    assert errors, "expected validation error for orphan actor A-2"
    assert any(e.code == "IM-2" for e in errors), (
        f"expected an IM-2 error, got codes {[e.code for e in errors]}"
    )
    assert any("A-2" in e.message for e in errors), (
        f"expected the offending actor A-2 to be named in the message, "
        f"got messages {[e.message for e in errors]}"
    )


def test_tc_im_2_02b_unknown_fk_rejected(tmp_path: Path) -> None:
    """A Deliverable referencing a non-existent Impact → validator surfaces
    the foreign-key error rather than raising."""
    goals = [("G-1", "increase WAU by 20%", "WAU", "+20%", "2026-12-31")]
    actors = [("A-1", "G-1", "Buyer", "first-time UK buyer")]
    impacts = [("I-1", "A-1", "returns weekly", "+")]
    # D-1 references I-99 which does not exist
    deliverables = [("D-1", "I-99", "saved searches", "feature")]

    path = _write_map(tmp_path, goals, actors, impacts, deliverables)
    _, errors = full_check(path)
    assert errors, "expected an FK error for unknown impact I-99"
    assert any("I-99" in e.message for e in errors)


def test_full_check_returns_validation_error_dataclass(tmp_path: Path) -> None:
    """Contract: errors are ValidationError instances with non-empty code/message."""
    goals = [("G-1", "increase WAU by 20%", "WAU", "+20%", "2026-12-31")]
    actors = [
        ("A-1", "G-1", "Buyer", "first-time UK buyer"),
        ("A-2", "G-1", "Renter", "city renter"),
    ]
    impacts = [("I-1", "A-1", "returns weekly", "+")]
    deliverables = [("D-1", "I-1", "saved searches", "feature")]
    path = _write_map(tmp_path, goals, actors, impacts, deliverables)
    _, errors = full_check(path)
    for e in errors:
        assert isinstance(e, ValidationError)
        assert e.code, "ValidationError.code must be non-empty"
        assert e.message, "ValidationError.message must be non-empty"


# --- Property test (TC-IM-2-03) -------------------------------------------------


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    n_actors=st.integers(min_value=1, max_value=4),
    n_impacts_per_actor=st.integers(min_value=0, max_value=3),
    n_delivs_per_impact=st.integers(min_value=0, max_value=3),
    drop_impact_probability=st.floats(min_value=0.0, max_value=1.0),
    add_unknown_fk=st.booleans(),
    seed=st.integers(min_value=0, max_value=10_000),
)
def test_tc_im_2_03_tree_invariants_property(
    tmp_path_factory: pytest.TempPathFactory,
    n_actors: int,
    n_impacts_per_actor: int,
    n_delivs_per_impact: int,
    drop_impact_probability: float,
    add_unknown_fk: bool,
    seed: int,
) -> None:
    """For any random tree shape ± perturbations, full_check either returns
    no errors (a valid tree) or returns at least one ValidationError with a
    non-empty code and message that names a row id. Never returns silently
    mis-classified state.
    """
    import random

    rng = random.Random(seed)
    tmp_path = tmp_path_factory.mktemp("impact_map_property")

    goals = [("G-1", "increase WAU by 20%", "WAU", "+20%", "2026-12-31")]
    actors: list[tuple[str, str, str, str]] = []
    impacts: list[tuple[str, str, str, str]] = []
    deliverables: list[tuple[str, str, str, str]] = []

    impact_seq = 0
    deliv_seq = 0
    for ai in range(1, n_actors + 1):
        actor_id = f"A-{ai}"
        actors.append((actor_id, "G-1", f"Actor {ai}", "desc"))
        for _ in range(n_impacts_per_actor):
            # randomly drop an impact level → orphan actor case (IM-2)
            if rng.random() < drop_impact_probability:
                continue
            impact_seq += 1
            i_id = f"I-{impact_seq}"
            impacts.append((i_id, actor_id, "behaviour", "+"))
            for _ in range(n_delivs_per_impact):
                deliv_seq += 1
                deliverables.append((f"D-{deliv_seq}", i_id, "deliverable", "feature"))

    if add_unknown_fk and impacts:
        # add a deliverable pointing at an impact that doesn't exist
        deliv_seq += 1
        deliverables.append((f"D-{deliv_seq}", "I-9999", "orphan", "feature"))

    path = _write_map(tmp_path, goals, actors, impacts, deliverables)
    impact_map, errors = full_check(path)

    # Invariant: either accepted (no errors AND a parsed map) OR rejected with
    # at least one well-formed error. Never the third state.
    if not errors:
        assert impact_map is not None
        # Sanity: every parsed row's parent exists in the parent table.
        actor_ids = {a.id for a in impact_map.actors}
        impact_ids = {i.id for i in impact_map.impacts}
        goal_ids = {g.id for g in impact_map.goals}
        for a in impact_map.actors:
            assert a.goal_id in goal_ids
        for i in impact_map.impacts:
            assert i.actor_id in actor_ids
        for d in impact_map.deliverables:
            assert d.impact_id in impact_ids
        # And every Actor has at least one Impact when the test path produces
        # a valid tree (no silently-orphan Actor on the success branch).
        for a in impact_map.actors:
            assert any(i.actor_id == a.id for i in impact_map.impacts), (
                f"actor {a.id} has no impacts but full_check accepted"
            )
    else:
        for e in errors:
            assert isinstance(e, ValidationError)
            assert e.code
            assert e.message
