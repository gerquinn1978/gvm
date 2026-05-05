"""Tests for the charter template library (P11-C10, ADR-208).

Verifies the file at `references/charters.md` agrees with `_charter.load`'s
schema (ADR-202): every template parses, populates a valid `Charter` once
the practitioner adds `target` + `runner`, and edits to mission/tour do not
break validation (TC-ET-6-02).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from _charter import Charter, load


_LIBRARY = (
    Path(__file__).resolve().parents[1] / "references" / "charters.md"
)

_YAML_BLOCK_RE = re.compile(r"```yaml\n(.*?)```", re.DOTALL)


# ----------------------------------------------------------- helpers


def _extract_templates(text: str) -> list[dict]:
    blocks = _YAML_BLOCK_RE.findall(text)
    return [yaml.safe_load(b) for b in blocks]


def _materialise(template: dict, tmp_path: Path, *, target=None, runner="gerard") -> Path:
    """Take a template, add the practitioner-supplied fields, write a charter
    file the validator can load."""
    full = {
        "schema_version": 1,
        "session_id": "explore-001",
        "mission": template["mission"],
        "timebox_minutes": template["timebox_minutes"],
        "target": target if target is not None else ["/sample"],
        "tour": template["tour"],
        "runner": runner,
    }
    body = "---\n" + yaml.safe_dump(full, sort_keys=False) + "---\n"
    p = tmp_path / "charter.yml"
    p.write_text(body, encoding="utf-8")
    return p


# ----------------------------------------------------------- TC-ET-6-01


def test_library_file_exists():
    assert _LIBRARY.exists(), f"charter library not found at {_LIBRARY}"


def test_library_has_at_least_three_templates():
    text = _LIBRARY.read_text(encoding="utf-8")
    templates = _extract_templates(text)
    assert len(templates) >= 3


def test_each_template_has_mission_timebox_tour():
    text = _LIBRARY.read_text(encoding="utf-8")
    templates = _extract_templates(text)
    assert templates, "no templates found"
    for i, t in enumerate(templates):
        assert isinstance(t, dict), f"template {i} is not a mapping"
        assert "mission" in t and isinstance(t["mission"], str) and t["mission"].strip()
        assert "timebox_minutes" in t and isinstance(t["timebox_minutes"], int)
        assert "tour" in t and isinstance(t["tour"], str)


# ----------------------------------------------------------- ADR-208 (six templates)


def test_library_has_six_initial_templates():
    """ADR-208's Round 1 table lists six project types."""
    text = _LIBRARY.read_text(encoding="utf-8")
    templates = _extract_templates(text)
    assert len(templates) == 6, (
        f"ADR-208 mandates 6 initial templates; found {len(templates)}"
    )


def test_library_covers_each_adr208_project_type():
    """Headings for each project-type must be present (verbatim per ADR-208)."""
    text = _LIBRARY.read_text(encoding="utf-8")
    expected = [
        "data-analysis skill",
        "CRUD app",
        "agent-based system",
        "content pipeline",
        "billing/payment surface",
        "network-degraded scenario",
    ]
    for name in expected:
        assert name in text, f"ADR-208 project type missing: {name!r}"


# ----------------------------------------------------------- per-template round-trip


def test_every_template_round_trips_through_charter_load(tmp_path):
    """Each template, with practitioner-supplied target+runner, validates."""
    text = _LIBRARY.read_text(encoding="utf-8")
    templates = _extract_templates(text)
    for i, t in enumerate(templates):
        subdir = tmp_path / f"t{i}"
        subdir.mkdir()
        path = _materialise(t, subdir)
        charter = load(path)
        assert isinstance(charter, Charter)
        assert charter.mission == t["mission"]
        assert charter.timebox_minutes == t["timebox_minutes"]
        assert charter.tour == t["tour"]


# ----------------------------------------------------------- TC-ET-6-02


def test_template_mission_can_be_edited_without_validation_failure(tmp_path):
    """A template with a different (valid) mission still loads. Templates
    are starting points, not mandates."""
    text = _LIBRARY.read_text(encoding="utf-8")
    templates = _extract_templates(text)
    assert templates
    t = dict(templates[0])
    t["mission"] = "Edited mission: probe a different aspect entirely."
    path = _materialise(t, tmp_path)
    charter = load(path)
    assert charter.mission.startswith("Edited mission")


def test_template_tour_can_be_swapped_to_other_valid_tour(tmp_path):
    """A practitioner can change tour from the template's default to another
    allowed value."""
    text = _LIBRARY.read_text(encoding="utf-8")
    templates = _extract_templates(text)
    assert templates
    t = dict(templates[0])
    # Pick a tour that differs from the template's default.
    new_tour = "configuration" if t["tour"] != "configuration" else "feature"
    t["tour"] = new_tour
    path = _materialise(t, tmp_path)
    charter = load(path)
    assert charter.tour == new_tour


# ----------------------------------------------------------- schema-conformance smoke


@pytest.mark.parametrize(
    "field,allowed",
    [
        ("timebox_minutes", {30, 60, 90}),
        ("tour", {"feature", "data", "money", "interruption", "configuration"}),
    ],
)
def test_template_values_are_in_allowed_sets(field, allowed):
    """Catches a typo in the library file (e.g. `tour: dat` or
    `timebox_minutes: 45`) before it reaches a practitioner."""
    text = _LIBRARY.read_text(encoding="utf-8")
    templates = _extract_templates(text)
    for i, t in enumerate(templates):
        assert t[field] in allowed, (
            f"template {i}: {field}={t[field]!r} not in allowed set {allowed}"
        )
