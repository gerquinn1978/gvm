"""Tests for `_explore_parser.py` — test/explore-NNN.md schema (ADR-206)."""

from __future__ import annotations

from pathlib import Path

import pytest

from _schema import SchemaTooNewError
from _explore_parser import (
    ExploreParseError,
    load_explore,
)

VALID_HEADER = "---\nschema_version: 1\n---\n# Explore Session\n\n"

CHARTER_BLOCK = """## Charter

```yaml
schema_version: 1
session_id: explore-001
runner: gerard
mission: probe sort
timebox_minutes: 60
target: /report
tour: data
```
"""

SESSION_LOG = """
## Session Log

- 09:00 — started session
- 09:05 — clicked Sort header
"""

DEFECTS_ONE = """
## Defects

### D-1: Sort button does nothing
**Severity:** Important
**Tour:** data
**Given** a table with mixed numeric data
**When** Sort is clicked on the Score column
**Then** rows reorder by score ascending
**Reproduction:**
1. Load /report
2. Click Sort header
3. Observe: order unchanged
**Stub-path:** stubs/sorter.py
"""

OBSERVATIONS_ONE = """
## Observations

### O-1: Loading spinner sticks briefly
**Tour:** feature
**Given** the page is freshly loaded
**When** the user scrolls
**Then** the spinner should be hidden
**Note:** intermittent; about 200ms of stuck spinner.
"""

OVERALL = """
## Overall Assessment

Useful pass; one important defect, one cosmetic.
"""


def _full_report() -> str:
    return (
        VALID_HEADER
        + CHARTER_BLOCK
        + SESSION_LOG
        + DEFECTS_ONE
        + OBSERVATIONS_ONE
        + OVERALL
    )


def _write(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


VALID_STUBS = """---
schema_version: 1
---
# Stubs

| Path | Reason | Real-provider Plan | Owner | Expiry |
|---|---|---|---|---|
| stubs/sorter.py | sort algorithm deferred | TimSort | gq | 2026-12-31 |
"""


# --- Happy path ---


def test_loads_full_report(tmp_path):
    p = _write(tmp_path, "explore-001.md", _full_report())
    r = load_explore(p)
    assert r.schema_version == 1
    assert r.session_id == "explore-001"
    assert r.runner == "gerard"
    assert len(r.defects) == 1
    d = r.defects[0]
    assert d.id == "D-1"
    assert d.severity == "Important"
    assert d.tour == "data"
    assert d.title == "Sort button does nothing"
    assert "table with mixed numeric data" in d.given
    assert "Sort is clicked" in d.when
    assert "reorder by score" in d.then
    assert "Click Sort header" in d.reproduction
    assert d.stub_path == "stubs/sorter.py"
    assert d.in_stub_path is False  # no stubs_path provided
    assert len(r.observations) == 1
    o = r.observations[0]
    assert o.id == "O-1"
    assert o.title == "Loading spinner sticks briefly"
    assert "spinner should be hidden" in o.then
    assert "intermittent" in o.note


def test_in_stub_path_true_when_matched(tmp_path):
    p = _write(tmp_path, "explore-001.md", _full_report())
    s = _write(tmp_path, "STUBS.md", VALID_STUBS)
    r = load_explore(p, s)
    assert r.defects[0].in_stub_path is True


def test_in_stub_path_false_when_unmatched(tmp_path):
    p = _write(tmp_path, "explore-001.md", _full_report())
    s = _write(tmp_path, "STUBS.md", VALID_STUBS.replace("sorter.py", "other.py"))
    r = load_explore(p, s)
    assert r.defects[0].in_stub_path is False


def test_unassigned_runner(tmp_path):
    body = _full_report().replace("runner: gerard", "runner: unassigned")
    p = _write(tmp_path, "explore-002.md", body)
    r = load_explore(p)
    assert r.runner is None


# --- Schema delegation ---


def test_schema_too_new_propagates(tmp_path):
    body = (
        "---\nschema_version: 99\n---\n# Explore\n\n"
        + CHARTER_BLOCK
        + SESSION_LOG
        + "\n## Defects\n\n## Observations\n\n## Overall Assessment\n"
    )
    p = _write(tmp_path, "explore-003.md", body)
    with pytest.raises(SchemaTooNewError):
        load_explore(p)


# --- Structural failures ---


@pytest.mark.parametrize(
    "drop, match",
    [
        ("## Charter", "Charter"),
        ("## Session Log", "Session Log"),
        ("## Defects", "Defects"),
        ("## Observations", "Observations"),
        ("## Overall Assessment", "Overall Assessment"),
    ],
)
def test_missing_section_raises(tmp_path, drop, match):
    body = _full_report().replace(drop, "## Removed")
    p = _write(tmp_path, "explore-004.md", body)
    with pytest.raises(ExploreParseError, match=match):
        load_explore(p)


def test_defect_missing_severity_raises(tmp_path):
    body = _full_report().replace("**Severity:** Important\n", "")
    p = _write(tmp_path, "explore-005.md", body)
    with pytest.raises(ExploreParseError, match="D-1"):
        load_explore(p)


def test_defect_bad_severity_raises(tmp_path):
    body = _full_report().replace(
        "**Severity:** Important", "**Severity:** Catastrophic"
    )
    p = _write(tmp_path, "explore-006.md", body)
    with pytest.raises(ExploreParseError, match="severity"):
        load_explore(p)


def test_defect_missing_given_raises(tmp_path):
    body = _full_report().replace("**Given** a table with mixed numeric data\n", "")
    p = _write(tmp_path, "explore-007.md", body)
    with pytest.raises(ExploreParseError, match="D-1"):
        load_explore(p)


def test_empty_defects_section(tmp_path):
    body = (
        VALID_HEADER
        + CHARTER_BLOCK
        + SESSION_LOG
        + "\n## Defects\n\n"
        + OBSERVATIONS_ONE
        + OVERALL
    )
    p = _write(tmp_path, "explore-008.md", body)
    r = load_explore(p)
    assert r.defects == ()
    assert len(r.observations) == 1


def test_multiple_defects_order_preserved(tmp_path):
    second_defect = """
### D-2: Filter persists across pages
**Severity:** Minor
**Tour:** feature
**Given** a filter is set on page 1
**When** navigating to page 2
**Then** the filter should not persist
**Reproduction:**
1. Set filter
2. Click next page
"""
    body = _full_report().replace(OBSERVATIONS_ONE, second_defect + OBSERVATIONS_ONE)
    p = _write(tmp_path, "explore-009.md", body)
    r = load_explore(p)
    assert [d.id for d in r.defects] == ["D-1", "D-2"]
    assert r.defects[1].severity == "Minor"
