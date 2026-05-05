"""Tests for `_calibration_parser.py` — calibration.md schema 0 + 1 (ADR-604)."""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from _schema import SchemaTooNewError
from _calibration_parser import (
    Calibration,
    CalibrationParseError,
    ScoreHistoryRow,
    SchemaDowngradeError,
    UnknownVerdictError,
    Verdict,
    load_calibration,
    map_v0_to_v1,
    serialise,
    write_calibration,
)


def _write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "calibration.md"
    p.write_text(body, encoding="utf-8")
    return p


# --- v0: no frontmatter ---


V0_BODY_NO_FRONTMATTER = """# Calibration

## Score History

| Round | Date | Type | Verdict | Per-dimension scores |
|---|---|---|---|---|
| 1 | 2026-01-15 | code | Pass | a=4 b=5 |
| 2 | 2026-02-15 | code | Pass with gaps | a=3 b=4 |

## Anchor Examples

Some prose here.
"""


def test_loads_v0_no_frontmatter(tmp_path):
    c = load_calibration(_write(tmp_path, V0_BODY_NO_FRONTMATTER))
    assert c.schema_version == 0
    assert len(c.score_history) == 2
    assert c.score_history[0].round == 1
    assert c.score_history[0].verdict == "Pass"
    assert c.score_history[0].verdict_under_schema is None
    assert c.score_history[0].per_dimension_scores == "a=4 b=5"
    assert c.recurring_findings == ()
    assert "Anchor Examples" in c.trailing_body


# --- v0: with stamped schema_version: 0 frontmatter ---


V0_BODY_STAMPED = """---
schema_version: 0
---
# Calibration

## Score History

| Round | Date | Type | Verdict | Per-dimension scores |
|---|---|---|---|---|
| 1 | 2026-01-15 | code | Do not release | a=2 b=2 |
"""


def test_loads_v0_stamped_frontmatter(tmp_path):
    c = load_calibration(_write(tmp_path, V0_BODY_STAMPED))
    assert c.schema_version == 0
    assert len(c.score_history) == 1
    assert c.score_history[0].verdict == "Do not release"
    assert c.score_history[0].verdict_under_schema is None


# --- v1 happy path ---


V1_BODY = """---
schema_version: 1
---
# Calibration

## Score History

| Round | Date | Type | Verdict | verdict_under_schema | Per-dimension scores |
|---|---|---|---|---|---|
| 3 | 2026-05-15 | code | Ship-ready | 1 | a=5 b=5 |
| 4 | 2026-06-01 | code | Demo-ready | 1 | a=4 b=4 |

## Recurring Findings

| Signature | First Round | Last Round | Severity History |
|---|---|---|---|
| auth-mock-leak | 1 | 3 | Important, Important, Minor |

## Anchor Examples

Trailing text.
"""


def test_loads_v1(tmp_path):
    c = load_calibration(_write(tmp_path, V1_BODY))
    assert c.schema_version == 1
    assert len(c.score_history) == 2
    assert c.score_history[0].verdict == "Ship-ready"
    assert c.score_history[0].verdict_under_schema == 1
    assert len(c.recurring_findings) == 1
    assert c.recurring_findings[0].signature == "auth-mock-leak"
    assert c.recurring_findings[0].first_round == 1


def test_loads_v1_without_recurring_findings(tmp_path):
    body = """---
schema_version: 1
---
# Calibration

## Score History

| Round | Date | Type | Verdict | verdict_under_schema | Per-dimension scores |
|---|---|---|---|---|---|
| 1 | 2026-05-15 | code | Ship-ready | 1 | a=5 |
"""
    c = load_calibration(_write(tmp_path, body))
    assert c.recurring_findings == ()


def test_loads_v1_empty_recurring_findings_table(tmp_path):
    body = """---
schema_version: 1
---
# Calibration

## Score History

| Round | Date | Type | Verdict | verdict_under_schema | Per-dimension scores |
|---|---|---|---|---|---|
| 1 | 2026-05-15 | code | Ship-ready | 1 | a=5 |

## Recurring Findings

| Signature | First Round | Last Round | Severity History |
|---|---|---|---|
"""
    c = load_calibration(_write(tmp_path, body))
    assert c.recurring_findings == ()


# --- Schema delegation ---


def test_schema_too_new_propagates(tmp_path):
    body = "---\nschema_version: 99\n---\n# Calibration\n"
    with pytest.raises(SchemaTooNewError):
        load_calibration(_write(tmp_path, body))


# --- Failures ---


def test_v0_bad_column_count_raises(tmp_path):
    body = """# Calibration

## Score History

| Round | Date | Type | Verdict | Per-dimension scores |
|---|---|---|---|---|
| only | three | cells |
"""
    with pytest.raises(CalibrationParseError, match="column"):
        load_calibration(_write(tmp_path, body))


def test_v1_bad_column_headers_raise(tmp_path):
    body = """---
schema_version: 1
---
# Calibration

## Score History

| Round | Date | Verdict | verdict_under_schema | Per-dimension scores |
|---|---|---|---|---|
| 1 | 2026-05-15 | Ship-ready | 1 | a=5 |
"""
    with pytest.raises(CalibrationParseError, match="header"):
        load_calibration(_write(tmp_path, body))


def test_round_field_must_be_int(tmp_path):
    body = """# Calibration

## Score History

| Round | Date | Type | Verdict | Per-dimension scores |
|---|---|---|---|---|
| not-an-int | 2026-01-15 | code | Pass | a=5 |
"""
    with pytest.raises(CalibrationParseError, match="Round"):
        load_calibration(_write(tmp_path, body))


# --- map_v0_to_v1 ---


def test_map_pass():
    assert map_v0_to_v1("Pass") == Verdict.SHIP_READY


def test_map_pass_with_gaps_returns_none():
    assert map_v0_to_v1("Pass with gaps") is None


def test_map_do_not_release():
    assert map_v0_to_v1("Do not release") == Verdict.NOT_SHIPPABLE


def test_map_unknown_raises():
    with pytest.raises(UnknownVerdictError) as exc_info:
        map_v0_to_v1("Mostly fine")
    assert exc_info.value.text == "Mostly fine"


# --- write_calibration: TC-PP-4-04b ---


def _v1_calibration(round_n: int = 1) -> Calibration:
    return Calibration(
        schema_version=1,
        score_history=(
            ScoreHistoryRow(
                round=round_n,
                date="2026-05-15",
                type="code",
                verdict="Ship-ready",
                verdict_under_schema=1,
                per_dimension_scores="a=5",
            ),
        ),
        recurring_findings=(),
        trailing_body="",
    )


def _v0_calibration(round_n: int = 1) -> Calibration:
    return Calibration(
        schema_version=0,
        score_history=(
            ScoreHistoryRow(
                round=round_n,
                date="2026-01-15",
                type="code",
                verdict="Pass",
                verdict_under_schema=None,
                per_dimension_scores="a=5",
            ),
        ),
        recurring_findings=(),
        trailing_body="",
    )


def test_write_no_existing_file(tmp_path):
    p = tmp_path / "calibration.md"
    write_calibration(p, _v1_calibration())
    assert p.exists()
    re_read = load_calibration(p)
    assert re_read.schema_version == 1


def test_write_same_version_succeeds(tmp_path):
    p = tmp_path / "calibration.md"
    write_calibration(p, _v1_calibration(round_n=1))
    write_calibration(p, _v1_calibration(round_n=2))
    assert load_calibration(p).score_history[0].round == 2


def test_write_upgrade_v0_to_v1_succeeds(tmp_path):
    p = tmp_path / "calibration.md"
    write_calibration(p, _v0_calibration())
    write_calibration(p, _v1_calibration())
    assert load_calibration(p).schema_version == 1


def test_write_downgrade_v1_to_v0_raises(tmp_path):
    p = tmp_path / "calibration.md"
    write_calibration(p, _v1_calibration())
    with pytest.raises(SchemaDowngradeError):
        write_calibration(p, _v0_calibration())


# --- Round-trip ---


def test_round_trip_v0(tmp_path):
    p = _write(tmp_path, V0_BODY_NO_FRONTMATTER)
    c = load_calibration(p)
    out = serialise(c)
    p2 = tmp_path / "out.md"
    p2.write_text(out, encoding="utf-8")
    re_read = load_calibration(p2)
    assert re_read.score_history == c.score_history
    assert re_read.schema_version == c.schema_version


def test_round_trip_v1(tmp_path):
    p = _write(tmp_path, V1_BODY)
    c = load_calibration(p)
    out = serialise(c)
    p2 = tmp_path / "out.md"
    p2.write_text(out, encoding="utf-8")
    re_read = load_calibration(p2)
    assert re_read.score_history == c.score_history
    assert re_read.recurring_findings == c.recurring_findings
    assert re_read.schema_version == 1


# --- TC-PP-4-03 PROPERTY: monotonicity ---


@st.composite
def _calibrations(draw):
    schema_v = draw(st.sampled_from([0, 1]))
    if schema_v == 0:
        return _v0_calibration(round_n=draw(st.integers(min_value=1, max_value=100)))
    return _v1_calibration(round_n=draw(st.integers(min_value=1, max_value=100)))


@settings(max_examples=50, deadline=None)
@given(st.lists(_calibrations(), min_size=1, max_size=8))
def test_property_schema_version_monotonic(tmp_path_factory, sequence):
    tmp = tmp_path_factory.mktemp("monotonic")
    p = tmp / "calibration.md"
    last_committed_version = -1
    for c in sequence:
        try:
            write_calibration(p, c)
        except SchemaDowngradeError:
            current = load_calibration(p).schema_version
            assert c.schema_version < current  # confirms refusal was justified
            continue
        on_disk = load_calibration(p).schema_version
        assert on_disk >= last_committed_version
        last_committed_version = on_disk
