"""Tests for `_impact_map_parser.py` — impact-map.md schema (ADR-005, ADR-302).

Includes the IM-2-03 property test (parse/serialise round-trip + tree invariants).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from _schema import SchemaTooNewError
from _impact_map_parser import (
    Actor,
    ChangelogEntry,
    Deliverable,
    Goal,
    Impact,
    ImpactMap,
    ImpactMapParseError,
    load_impact_map,
    serialise,
    validate_referential_integrity,
)

VALID_HEADER = "---\nschema_version: 1\n---\n# Impact Map\n\n"

GOALS_HEAD = (
    "## Goals\n| ID | Statement | Metric | Target | Deadline |\n|---|---|---|---|---|\n"
)
ACTORS_HEAD = "## Actors\n| ID | Goal-ID | Name | Description |\n|---|---|---|---|\n"
IMPACTS_HEAD = "## Impacts\n| ID | Actor-ID | Behavioural change | Direction |\n|---|---|---|---|\n"
DELIV_HEAD = "## Deliverables\n| ID | Impact-ID | Title | Type |\n|---|---|---|---|\n"
CHLOG_HEAD = "## Changelog\n| Date | Change | Rationale |\n|---|---|---|\n"


def _write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "impact-map.md"
    p.write_text(body, encoding="utf-8")
    return p


def _full_valid_body() -> str:
    return (
        VALID_HEADER
        + GOALS_HEAD
        + "| G-1 | Increase WAU by 20% | WAU count | +20% | 2026-12-31 |\n\n"
        + ACTORS_HEAD
        + "| A-1 | G-1 | Property buyer | First-time UK buyer |\n"
        + "| A-2 | G-1 | Returning buyer | Repeat customer |\n\n"
        + IMPACTS_HEAD
        + "| I-1 | A-1 | Returns weekly | + |\n"
        + "| I-2 | A-2 | Refers a friend | + |\n\n"
        + DELIV_HEAD
        + "| D-1 | I-1 | Saved-search dashboard | feature |\n"
        + "| D-2 | I-2 | Referral programme | feature |\n\n"
        + CHLOG_HEAD
        + "| 2026-04-25 | Initial creation | First Round |\n"
    )


# --- Happy path ---


def test_loads_full_map(tmp_path):
    f = _write(tmp_path, _full_valid_body())
    im = load_impact_map(f)
    assert len(im.goals) == 1
    assert len(im.actors) == 2
    assert len(im.impacts) == 2
    assert len(im.deliverables) == 2
    assert len(im.changelog) == 1
    assert im.goals[0] == Goal(
        "G-1", "Increase WAU by 20%", "WAU count", "+20%", "2026-12-31"
    )
    assert im.actors[0].goal_id == "G-1"
    assert im.impacts[1].actor_id == "A-2"
    assert im.deliverables[0].impact_id == "I-1"
    assert im.changelog[0].date == "2026-04-25"


def test_changelog_is_optional(tmp_path):
    body = (
        VALID_HEADER
        + GOALS_HEAD
        + "| G-1 | Goal | metric | target | 2026-12-31 |\n\n"
        + ACTORS_HEAD
        + "| A-1 | G-1 | Actor | desc |\n\n"
        + IMPACTS_HEAD
        + "| I-1 | A-1 | change | + |\n\n"
        + DELIV_HEAD
        + "| D-1 | I-1 | title | feature |\n"
    )
    im = load_impact_map(_write(tmp_path, body))
    assert im.changelog == ()


def test_order_preserved(tmp_path):
    f = _write(tmp_path, _full_valid_body())
    im = load_impact_map(f)
    assert [a.id for a in im.actors] == ["A-1", "A-2"]
    assert [i.id for i in im.impacts] == ["I-1", "I-2"]


# --- Schema delegation ---


def test_schema_too_new_propagates(tmp_path):
    body = (
        "---\nschema_version: 99\n---\n# Impact Map\n\n"
        + GOALS_HEAD
        + ACTORS_HEAD
        + IMPACTS_HEAD
        + DELIV_HEAD
    )
    with pytest.raises(SchemaTooNewError):
        load_impact_map(_write(tmp_path, body))


# --- Structural failures ---


def test_missing_h1_raises(tmp_path):
    body = (
        "---\nschema_version: 1\n---\n"
        + GOALS_HEAD
        + ACTORS_HEAD
        + IMPACTS_HEAD
        + DELIV_HEAD
    )
    with pytest.raises(ImpactMapParseError, match="Impact Map"):
        load_impact_map(_write(tmp_path, body))


@pytest.mark.parametrize(
    "drop_section, match",
    [
        ("goals", "Goals"),
        ("actors", "Actors"),
        ("impacts", "Impacts"),
        ("deliverables", "Deliverables"),
    ],
)
def test_missing_required_section_raises(tmp_path, drop_section, match):
    sections = {
        "goals": GOALS_HEAD + "| G-1 | g | m | t | 2026-12-31 |\n\n",
        "actors": ACTORS_HEAD + "| A-1 | G-1 | a | d |\n\n",
        "impacts": IMPACTS_HEAD + "| I-1 | A-1 | c | + |\n\n",
        "deliverables": DELIV_HEAD + "| D-1 | I-1 | t | feature |\n",
    }
    sections.pop(drop_section)
    body = VALID_HEADER + "".join(sections.values())
    with pytest.raises(ImpactMapParseError, match=match):
        load_impact_map(_write(tmp_path, body))


def test_empty_table_raises(tmp_path):
    body = (
        VALID_HEADER
        + GOALS_HEAD
        + "| G-1 | g | m | t | 2026-12-31 |\n\n"
        + ACTORS_HEAD
        + "| A-1 | G-1 | a | d |\n\n"
        + IMPACTS_HEAD
        + "\n"
        + DELIV_HEAD
        + "| D-1 | I-1 | t | feature |\n"
    )
    with pytest.raises(ImpactMapParseError, match="Impacts"):
        load_impact_map(_write(tmp_path, body))


def test_wrong_column_headers_raise(tmp_path):
    bad_actors = (
        "## Actors\n| ID | GoalID | Name | Description |\n|---|---|---|---|\n"
        + "| A-1 | G-1 | a | d |\n\n"
    )
    body = (
        VALID_HEADER
        + GOALS_HEAD
        + "| G-1 | g | m | t | 2026-12-31 |\n\n"
        + bad_actors
        + IMPACTS_HEAD
        + "| I-1 | A-1 | c | + |\n\n"
        + DELIV_HEAD
        + "| D-1 | I-1 | t | feature |\n"
    )
    with pytest.raises(ImpactMapParseError, match="Actors"):
        load_impact_map(_write(tmp_path, body))


# --- ID validation ---


@pytest.mark.parametrize(
    "section, bad_id, match",
    [
        ("goals", "Goal-1", "Goals"),
        ("actors", "Act-1", "Actors"),
        ("impacts", "Imp-1", "Impacts"),
        ("deliverables", "Del-1", "Deliverables"),
    ],
)
def test_bad_id_format_raises(tmp_path, section, bad_id, match):
    rows = {
        "goals": ("G-1", lambda i: f"| {i} | g | m | t | 2026-12-31 |\n\n"),
        "actors": ("A-1", lambda i: f"| {i} | G-1 | a | d |\n\n"),
        "impacts": ("I-1", lambda i: f"| {i} | A-1 | c | + |\n\n"),
        "deliverables": ("D-1", lambda i: f"| {i} | I-1 | t | feature |\n"),
    }
    parts: list[str] = [VALID_HEADER]
    for k, head in (
        ("goals", GOALS_HEAD),
        ("actors", ACTORS_HEAD),
        ("impacts", IMPACTS_HEAD),
        ("deliverables", DELIV_HEAD),
    ):
        parts.append(head)
        good_id, fmt = rows[k]
        used_id = bad_id if k == section else good_id
        parts.append(fmt(used_id))
    with pytest.raises(ImpactMapParseError, match=match):
        load_impact_map(_write(tmp_path, "".join(parts)))


def test_duplicate_id_raises(tmp_path):
    body = (
        VALID_HEADER
        + GOALS_HEAD
        + "| G-1 | g | m | t | 2026-12-31 |\n\n"
        + ACTORS_HEAD
        + "| A-1 | G-1 | a | d |\n"
        + "| A-1 | G-1 | b | e |\n\n"
        + IMPACTS_HEAD
        + "| I-1 | A-1 | c | + |\n\n"
        + DELIV_HEAD
        + "| D-1 | I-1 | t | feature |\n"
    )
    with pytest.raises(ImpactMapParseError, match="duplicate"):
        load_impact_map(_write(tmp_path, body))


# --- Referential integrity (IM-2) ---


def test_actor_unknown_goal_raises(tmp_path):
    body = (
        VALID_HEADER
        + GOALS_HEAD
        + "| G-1 | g | m | t | 2026-12-31 |\n\n"
        + ACTORS_HEAD
        + "| A-1 | G-9 | a | d |\n\n"
        + IMPACTS_HEAD
        + "| I-1 | A-1 | c | + |\n\n"
        + DELIV_HEAD
        + "| D-1 | I-1 | t | feature |\n"
    )
    with pytest.raises(ImpactMapParseError, match=r"A-1.*G-9"):
        load_impact_map(_write(tmp_path, body))


def test_impact_unknown_actor_raises(tmp_path):
    body = (
        VALID_HEADER
        + GOALS_HEAD
        + "| G-1 | g | m | t | 2026-12-31 |\n\n"
        + ACTORS_HEAD
        + "| A-1 | G-1 | a | d |\n\n"
        + IMPACTS_HEAD
        + "| I-1 | A-9 | c | + |\n\n"
        + DELIV_HEAD
        + "| D-1 | I-1 | t | feature |\n"
    )
    with pytest.raises(ImpactMapParseError, match=r"I-1.*A-9"):
        load_impact_map(_write(tmp_path, body))


def test_deliverable_unknown_impact_raises(tmp_path):
    """TC-IM-2-02: Actor with Deliverables but no parent Impact → FK fails."""
    body = (
        VALID_HEADER
        + GOALS_HEAD
        + "| G-1 | g | m | t | 2026-12-31 |\n\n"
        + ACTORS_HEAD
        + "| A-1 | G-1 | a | d |\n\n"
        + IMPACTS_HEAD
        + "| I-1 | A-1 | c | + |\n\n"
        + DELIV_HEAD
        + "| D-1 | I-9 | t | feature |\n"
    )
    with pytest.raises(ImpactMapParseError, match=r"D-1.*I-9"):
        load_impact_map(_write(tmp_path, body))


# --- Round-trip property (IM-2-03) ---


_SPLITLINES_CHARS = "|\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029"
_safe_text = (
    st.text(
        alphabet=st.characters(
            blacklist_characters=_SPLITLINES_CHARS,
            blacklist_categories=("Cs",),
        ),
        min_size=1,
        max_size=40,
    )
    .map(str.strip)
    .filter(lambda s: len(s) >= 1)
)


@st.composite
def _impact_maps(draw):
    actor_n = draw(st.integers(min_value=1, max_value=3))
    actors: list[Actor] = []
    impacts: list[Impact] = []
    deliverables: list[Deliverable] = []
    impact_counter = 0
    deliv_counter = 0
    for a in range(1, actor_n + 1):
        actors.append(
            Actor(
                id=f"A-{a}",
                goal_id="G-1",
                name=draw(_safe_text),
                description=draw(_safe_text),
            )
        )
        impacts_for_a = draw(st.integers(min_value=1, max_value=3))
        for _ in range(impacts_for_a):
            impact_counter += 1
            impacts.append(
                Impact(
                    id=f"I-{impact_counter}",
                    actor_id=f"A-{a}",
                    behavioural_change=draw(_safe_text),
                    direction=draw(st.sampled_from(["+", "-"])),
                )
            )
            delivs_for_i = draw(st.integers(min_value=1, max_value=3))
            for _ in range(delivs_for_i):
                deliv_counter += 1
                deliverables.append(
                    Deliverable(
                        id=f"D-{deliv_counter}",
                        impact_id=f"I-{impact_counter}",
                        title=draw(_safe_text),
                        type=draw(_safe_text),
                    )
                )

    goal = Goal(
        id="G-1",
        statement=draw(_safe_text),
        metric=draw(_safe_text),
        target=draw(_safe_text),
        deadline=draw(_safe_text),
    )
    cl_n = draw(st.integers(min_value=0, max_value=2))
    changelog = tuple(
        ChangelogEntry(
            date=draw(_safe_text),
            change=draw(_safe_text),
            rationale=draw(_safe_text),
        )
        for _ in range(cl_n)
    )
    return ImpactMap(
        goals=(goal,),
        actors=tuple(actors),
        impacts=tuple(impacts),
        deliverables=tuple(deliverables),
        changelog=changelog,
    )


@settings(max_examples=80)
@given(_impact_maps())
def test_round_trip_preserves_map(tmp_path_factory, im):
    tmp = tmp_path_factory.mktemp("rt")
    f = tmp / "impact-map.md"
    f.write_text(serialise(im), encoding="utf-8")
    parsed = load_impact_map(f)
    assert parsed == im


def test_validate_referential_integrity_passes_on_clean_map(tmp_path):
    im = load_impact_map(_write(tmp_path, _full_valid_body()))
    validate_referential_integrity(im)  # should not raise


def test_validate_referential_integrity_raises_on_orphan():
    bad = ImpactMap(
        goals=(Goal("G-1", "g", "m", "t", "2026-12-31"),),
        actors=(Actor("A-1", "G-9", "n", "d"),),
        impacts=(),
        deliverables=(),
        changelog=(),
    )
    with pytest.raises(ImpactMapParseError, match=r"A-1.*G-9"):
        validate_referential_integrity(bad)
