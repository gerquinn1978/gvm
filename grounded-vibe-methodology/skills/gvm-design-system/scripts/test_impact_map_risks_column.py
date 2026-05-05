"""Tests for the optional `risks` column on Deliverables (ADR-310, P10-C09).

Co-located with `test_impact_map_parser.py`. The 4-column shape is the legacy
default; the 5-column shape carries an optional `risks` cell from
``frozenset({"V","U","F","Va"})``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from _impact_map_parser import (
    DELIVERABLES_COLUMNS,
    DELIVERABLES_COLUMNS_WITH_RISKS,
    Actor,
    Deliverable,
    Goal,
    Impact,
    ImpactMap,
    ImpactMapParseError,
    load_impact_map,
    serialise,
)

GOAL_HEAD = (
    "## Goals\n"
    "| ID | Statement | Metric | Target | Deadline |\n"
    "|---|---|---|---|---|\n"
    "| G-1 | x | m | t | 2026-12-31 |\n\n"
)
ACTOR_HEAD = (
    "## Actors\n"
    "| ID | Goal-ID | Name | Description |\n"
    "|---|---|---|---|\n"
    "| A-1 | G-1 | Alice | desc |\n\n"
)
IMPACT_HEAD = (
    "## Impacts\n"
    "| ID | Actor-ID | Behavioural change | Direction |\n"
    "|---|---|---|---|\n"
    "| I-1 | A-1 | x | increase |\n\n"
)


def _wrap(deliv_table: str) -> str:
    return (
        "---\nschema_version: 1\n---\n# Impact Map\n\n"
        + GOAL_HEAD
        + ACTOR_HEAD
        + IMPACT_HEAD
        + deliv_table
    )


def _write(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_deliverables_4col_back_compat(tmp_path: Path):
    body = _wrap(
        "## Deliverables\n"
        "| ID | Impact-ID | Title | Type |\n"
        "|---|---|---|---|\n"
        "| D-1 | I-1 | Thing | feature |\n"
    )
    p = _write(tmp_path / "im.md", body)
    im = load_impact_map(p)
    assert im.deliverables[0].risks == frozenset()


def test_deliverables_5col_parses_risks(tmp_path: Path):
    body = _wrap(
        "## Deliverables\n"
        "| ID | Impact-ID | Title | Type | risks |\n"
        "|---|---|---|---|---|\n"
        "| D-1 | I-1 | Thing | feature | V,F |\n"
    )
    p = _write(tmp_path / "im.md", body)
    im = load_impact_map(p)
    assert im.deliverables[0].risks == frozenset({"V", "F"})


def test_deliverables_5col_unknown_code_rejected(tmp_path: Path):
    body = _wrap(
        "## Deliverables\n"
        "| ID | Impact-ID | Title | Type | risks |\n"
        "|---|---|---|---|---|\n"
        "| D-1 | I-1 | Thing | feature | X,V |\n"
    )
    p = _write(tmp_path / "im.md", body)
    with pytest.raises(ImpactMapParseError) as exc:
        load_impact_map(p)
    assert "X" in str(exc.value)


def test_deliverables_5col_empty_cell_means_no_risks(tmp_path: Path):
    body = _wrap(
        "## Deliverables\n"
        "| ID | Impact-ID | Title | Type | risks |\n"
        "|---|---|---|---|---|\n"
        "| D-1 | I-1 | Thing | feature |  |\n"
    )
    p = _write(tmp_path / "im.md", body)
    im = load_impact_map(p)
    assert im.deliverables[0].risks == frozenset()


def test_deliverables_unknown_header_shape_rejected(tmp_path: Path):
    body = _wrap(
        "## Deliverables\n"
        "| ID | Impact-ID | Title | Type | foo |\n"
        "|---|---|---|---|---|\n"
        "| D-1 | I-1 | Thing | feature | bar |\n"
    )
    p = _write(tmp_path / "im.md", body)
    with pytest.raises(ImpactMapParseError):
        load_impact_map(p)


def _build_im(*deliverables: Deliverable) -> ImpactMap:
    return ImpactMap(
        goals=(
            Goal(
                id="G-1", statement="x", metric="m", target="t", deadline="2026-12-31"
            ),
        ),
        actors=(Actor(id="A-1", goal_id="G-1", name="Alice", description="d"),),
        impacts=(
            Impact(
                id="I-1", actor_id="A-1", behavioural_change="x", direction="increase"
            ),
        ),
        deliverables=deliverables,
        changelog=(),
    )


def test_serialise_emits_4col_when_no_risks():
    im = _build_im(Deliverable(id="D-1", impact_id="I-1", title="x", type="feature"))
    rendered = serialise(im)
    assert "| risks |" not in rendered
    assert "| ID | Impact-ID | Title | Type |" in rendered


def test_serialise_emits_5col_when_any_risks_present():
    im = _build_im(
        Deliverable(id="D-1", impact_id="I-1", title="x", type="feature"),
        Deliverable(
            id="D-2",
            impact_id="I-1",
            title="y",
            type="feature",
            risks=frozenset({"V"}),
        ),
    )
    rendered = serialise(im)
    assert "| ID | Impact-ID | Title | Type | risks |" in rendered
    # D-1 has no risks; cell renders blank
    assert "| D-1 | I-1 | x | feature |  |" in rendered
    # D-2 has V
    assert "| D-2 | I-1 | y | feature | V |" in rendered


def test_serialise_canonical_risks_order():
    im = _build_im(
        Deliverable(
            id="D-1",
            impact_id="I-1",
            title="x",
            type="feature",
            risks=frozenset({"Va", "V", "F", "U"}),
        ),
    )
    rendered = serialise(im)
    # canonical order is V, U, F, Va
    assert "| V, U, F, Va |" in rendered


def test_round_trip_with_risks(tmp_path: Path):
    im = _build_im(
        Deliverable(
            id="D-1",
            impact_id="I-1",
            title="x",
            type="feature",
            risks=frozenset({"V", "F"}),
        ),
    )
    p = tmp_path / "im.md"
    p.write_text(serialise(im), encoding="utf-8")
    reloaded = load_impact_map(p)
    assert reloaded.deliverables[0].risks == frozenset({"V", "F"})


def test_columns_constants_consistent():
    assert DELIVERABLES_COLUMNS_WITH_RISKS == DELIVERABLES_COLUMNS + ["risks"]


def test_serialise_rejects_constructed_invalid_risk_code():
    """Defensive: a Deliverable constructed bypassing the parser with an
    invalid risk code must NOT silently corrupt the rendered table."""
    im = _build_im(
        Deliverable(
            id="D-1",
            impact_id="I-1",
            title="x",
            type="feature",
            risks=frozenset({"X"}),  # not in {V,U,F,Va}
        ),
    )
    with pytest.raises(ImpactMapParseError) as exc:
        serialise(im)
    assert "X" in str(exc.value)


def test_unknown_code_error_message_uses_canonical_order(tmp_path: Path):
    body = _wrap(
        "## Deliverables\n"
        "| ID | Impact-ID | Title | Type | risks |\n"
        "|---|---|---|---|---|\n"
        "| D-1 | I-1 | Thing | feature | X |\n"
    )
    p = _write(tmp_path / "im.md", body)
    with pytest.raises(ImpactMapParseError) as exc:
        load_impact_map(p)
    msg = str(exc.value)
    # Canonical V/U/F/Va order, not lexicographic F/U/V/Va.
    assert "['V', 'U', 'F', 'Va']" in msg
