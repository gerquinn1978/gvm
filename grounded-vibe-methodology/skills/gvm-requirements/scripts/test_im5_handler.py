"""Tests for P10-C08 — IM-5 mid-flight handler (intent classifier + atomic append).

Pin the intent-classification triggers, the atomic-append round-trip, and the
failure semantics: on any error, the original file is byte-identical and the
.tmp file is removed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make _impact_map_parser available
_GDS_SCRIPTS = Path(__file__).resolve().parents[2] / "gvm-design-system" / "scripts"
if str(_GDS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_GDS_SCRIPTS))

# Make sibling modules importable
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import _im5_handler  # noqa: E402
from _im5_handler import (  # noqa: E402
    AppendResult,
    Intent,
    append_actor,
    append_deliverable,
    append_impact,
    classify_intent,
)
from _impact_map_parser import (  # noqa: E402
    Actor,
    Deliverable,
    Goal,
    Impact,
    ImpactMap,
    load_impact_map,
    serialise,
)


# -------------------------- fixtures --------------------------


def _minimal_map() -> ImpactMap:
    return ImpactMap(
        goals=(
            Goal(
                id="G-1",
                statement="Reduce churn",
                metric="Monthly retention",
                target="95%",
                deadline="2026-12-31",
            ),
        ),
        actors=(
            Actor(id="A-1", goal_id="G-1", name="End user", description="Primary user"),
        ),
        impacts=(
            Impact(
                id="I-1",
                actor_id="A-1",
                behavioural_change="Logs in weekly",
                direction="increase",
            ),
        ),
        deliverables=(
            Deliverable(
                id="D-1", impact_id="I-1", title="Email digest", type="feature"
            ),
        ),
        changelog=(),
    )


@pytest.fixture
def map_path(tmp_path: Path) -> Path:
    p = tmp_path / "impact-map.md"
    p.write_text(serialise(_minimal_map()), encoding="utf-8")
    return p


# -------------------------- classify_intent --------------------------


@pytest.mark.parametrize(
    "phrase",
    [
        "add an impact please",
        "add impact I-9",
        "we have a new impact to capture",
        "I missed an impact during phase 1",
    ],
)
def test_classify_intent_add_impact_phrasings(phrase: str):
    intent = classify_intent(phrase)
    assert intent is not None
    assert intent.action == "add_impact"


def test_classify_intent_first_match_wins_for_ambiguous_phrasing():
    # "add an impact for new actor" hits both add_impact and add_actor patterns.
    # Tie-break is dict-insertion order: add_impact is registered first, so it
    # wins. Pin this so a future reorder of _PATTERNS surfaces as a test
    # failure rather than a silent behaviour change at the AskUserQuestion
    # confirmation step.
    intent = classify_intent("add an impact for new actor")
    assert intent is not None
    assert intent.action == "add_impact"


@pytest.mark.parametrize(
    "phrase",
    [
        "add an actor",
        "add actor A-3",
        "we need a new actor",
        "I missed an actor",
    ],
)
def test_classify_intent_add_actor_phrasings(phrase: str):
    intent = classify_intent(phrase)
    assert intent is not None
    assert intent.action == "add_actor"


@pytest.mark.parametrize(
    "phrase",
    [
        "add a deliverable",
        "add deliverable D-9",
        "we need a new deliverable",
        "I missed a deliverable",
    ],
)
def test_classify_intent_add_deliverable_phrasings(phrase: str):
    intent = classify_intent(phrase)
    assert intent is not None
    assert intent.action == "add_deliverable"


def test_classify_intent_no_match_returns_none():
    assert classify_intent("tell me about acceptance criteria") is None
    assert classify_intent("the user logs in weekly") is None


def test_classify_intent_case_insensitive():
    intent = classify_intent("Add An Impact For The Power User")
    assert intent is not None
    assert intent.action == "add_impact"


def test_classify_intent_does_not_overmatch_unrelated_text():
    # "the impact of this is huge" — has 'impact' but no add/new/missed verb adjacent
    assert classify_intent("the impact of this change is huge") is None
    # "an actor in the play" — no add/new/missed
    assert classify_intent("an actor in the play arrived late") is None


# -------------------------- append_impact --------------------------


def test_append_impact_round_trips_through_load(map_path: Path):
    new_impact = Impact(
        id="I-2",
        actor_id="A-1",
        behavioural_change="Shares with friends",
        direction="increase",
    )
    result = append_impact(map_path, new_impact, change_summary="Added I-2 mid-flight")
    assert result.success is True
    assert result.error is None

    reloaded = load_impact_map(map_path)
    assert any(i.id == "I-2" for i in reloaded.impacts)
    assert len(reloaded.changelog) == 1
    assert (
        "I-2" in reloaded.changelog[0].change
        or "mid-flight" in reloaded.changelog[0].change
    )


def test_append_impact_atomic_on_validation_failure(map_path: Path):
    original_bytes = map_path.read_bytes()
    bad_impact = Impact(
        id="I-9", actor_id="A-99", behavioural_change="Will fail", direction="increase"
    )
    result = append_impact(map_path, bad_impact, change_summary="Should fail")
    assert result.success is False
    assert result.error is not None
    assert map_path.read_bytes() == original_bytes
    assert not map_path.with_suffix(map_path.suffix + ".tmp").exists()


def test_append_impact_atomic_on_io_failure(tmp_path: Path):
    nonexistent = tmp_path / "missing-dir" / "impact-map.md"
    new_impact = Impact(
        id="I-1", actor_id="A-1", behavioural_change="x", direction="increase"
    )
    result = append_impact(nonexistent, new_impact, change_summary="x")
    assert result.success is False
    assert result.error is not None


def test_append_actor_round_trips(map_path: Path):
    new_actor = Actor(id="A-2", goal_id="G-1", name="Admin", description="Operator")
    result = append_actor(map_path, new_actor, change_summary="Added A-2")
    assert result.success is True
    reloaded = load_impact_map(map_path)
    assert any(a.id == "A-2" for a in reloaded.actors)


def test_append_deliverable_round_trips(map_path: Path):
    new_deliverable = Deliverable(
        id="D-2", impact_id="I-1", title="Push notification", type="feature"
    )
    result = append_deliverable(map_path, new_deliverable, change_summary="Added D-2")
    assert result.success is True
    reloaded = load_impact_map(map_path)
    assert any(d.id == "D-2" for d in reloaded.deliverables)


def test_append_writes_changelog_entry_with_summary(map_path: Path):
    new_impact = Impact(
        id="I-2", actor_id="A-1", behavioural_change="x", direction="increase"
    )
    result = append_impact(map_path, new_impact, change_summary="The summary text")
    assert result.success is True
    reloaded = load_impact_map(map_path)
    assert any("The summary text" in c.change for c in reloaded.changelog)


def test_append_does_not_mutate_on_failure(map_path: Path):
    before = map_path.read_bytes()
    bad = Impact(
        id="I-2", actor_id="A-NOPE", behavioural_change="x", direction="increase"
    )
    result = append_impact(map_path, bad, change_summary="fail")
    assert result.success is False
    assert map_path.read_bytes() == before


# -------------------------- frozen dataclasses --------------------------


def test_intent_dataclass_is_frozen():
    intent = Intent(action="add_impact", raw_text="add an impact")
    with pytest.raises(AttributeError):
        intent.action = "add_actor"  # type: ignore[misc]


def test_append_result_dataclass_is_frozen():
    r = AppendResult(success=True, error=None)
    with pytest.raises(AttributeError):
        r.success = False  # type: ignore[misc]


# -------------------------- module surface --------------------------


def test_module_exposes_required_symbols():
    for name in (
        "Intent",
        "AppendResult",
        "classify_intent",
        "append_impact",
        "append_actor",
        "append_deliverable",
    ):
        assert hasattr(_im5_handler, name), f"missing public symbol: {name}"
