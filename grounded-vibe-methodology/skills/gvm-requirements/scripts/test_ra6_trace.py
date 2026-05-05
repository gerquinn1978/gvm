"""Tests for P10-C09 — RA-6 trace column lookup (ADR-310)."""

from __future__ import annotations

import sys
from pathlib import Path

_GDS = Path(__file__).resolve().parents[2] / "gvm-design-system" / "scripts"
if str(_GDS) not in sys.path:
    sys.path.insert(0, str(_GDS))
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _impact_map_parser import (  # noqa: E402
    Actor,
    Deliverable,
    Goal,
    Impact,
    ImpactMap,
    serialise,
)
from _ra6_trace import render_risks_cell, risks_for_deliverable  # noqa: E402


def _write(path: Path, *deliverables: Deliverable) -> Path:
    im = ImpactMap(
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
    path.write_text(serialise(im), encoding="utf-8")
    return path


def test_risks_for_existing_deliverable(tmp_path: Path):
    p = _write(
        tmp_path / "im.md",
        Deliverable(
            id="D-1",
            impact_id="I-1",
            title="x",
            type="feature",
            risks=frozenset({"V", "F"}),
        ),
    )
    assert risks_for_deliverable(p, "D-1") == ("V", "F")


def test_risks_for_missing_deliverable(tmp_path: Path):
    p = _write(
        tmp_path / "im.md",
        Deliverable(
            id="D-1", impact_id="I-1", title="x", type="feature", risks=frozenset({"V"})
        ),
    )
    assert risks_for_deliverable(p, "D-99") == ()


def test_risks_for_deliverable_with_no_risks_column(tmp_path: Path):
    # 4-column back-compat — all deliverables have empty risks
    p = _write(
        tmp_path / "im.md",
        Deliverable(id="D-1", impact_id="I-1", title="x", type="feature"),
    )
    assert risks_for_deliverable(p, "D-1") == ()


def test_risks_for_deliverable_canonical_order(tmp_path: Path):
    p = _write(
        tmp_path / "im.md",
        Deliverable(
            id="D-1",
            impact_id="I-1",
            title="x",
            type="feature",
            risks=frozenset({"Va", "F", "V", "U"}),
        ),
    )
    assert risks_for_deliverable(p, "D-1") == ("V", "U", "F", "Va")


def test_risks_for_parse_error(tmp_path: Path):
    nonexistent = tmp_path / "no-such.md"
    assert risks_for_deliverable(nonexistent, "D-1") == ()


def test_render_risks_cell_empty():
    assert render_risks_cell(frozenset()) == ""


def test_render_risks_cell_canonical_order():
    assert render_risks_cell(frozenset({"Va", "V"})) == "V, Va"


def test_render_risks_cell_full_set():
    assert render_risks_cell(frozenset({"V", "U", "F", "Va"})) == "V, U, F, Va"


def test_render_risks_cell_accepts_tuple():
    assert render_risks_cell(("V", "F")) == "V, F"
