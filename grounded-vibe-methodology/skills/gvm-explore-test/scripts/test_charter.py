"""Charter validator tests for `/gvm-explore-test` (P11-C06).

Covers TC-ET-2-01 (all-fields-present accepted) and TC-ET-2-02 (missing
tour rejected with named field error). Adds defensive coverage for every
validation branch ADR-202 specifies — tour case-insensitivity, the
"data tour" rejection, timebox enum, target non-empty, session_id format,
file-missing, frontmatter-missing, and the `runner: unassigned`
ET-7-fallback path.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from _charter import Charter, CharterError, load


def _write_charter(
    tmp_path: Path, body: str, name: str = "explore-001.charter.yml"
) -> Path:
    path = tmp_path / name
    path.write_text(textwrap.dedent(body).lstrip("\n"), encoding="utf-8")
    return path


VALID_CHARTER = """
---
schema_version: 1
session_id: explore-001
mission: Probe the report renderer for honesty failures
timebox_minutes: 60
target:
  - ./report.html
tour: data
runner: gerard
---

# Notes
Optional free text.
"""


def test_load_accepts_all_required_fields(tmp_path):
    """TC-ET-2-01: charter with all four ET-2 fields plus schema_version /
    session_id / runner is accepted."""
    path = _write_charter(tmp_path, VALID_CHARTER)
    charter = load(path)
    assert isinstance(charter, Charter)
    assert charter.schema_version == 1
    assert charter.session_id == "explore-001"
    assert charter.mission.startswith("Probe")
    assert charter.timebox_minutes == 60
    assert charter.target == ("./report.html",)
    assert charter.tour == "data"
    assert charter.runner == "gerard"


def test_missing_tour_raises_charter_error(tmp_path):
    """TC-ET-2-02: charter missing `tour` rejected with a CharterError that
    names the missing field."""
    body = """
    ---
    schema_version: 1
    session_id: explore-001
    mission: x
    timebox_minutes: 60
    target:
      - ./report.html
    runner: gerard
    ---
    """
    path = _write_charter(tmp_path, body)
    with pytest.raises(CharterError) as exc:
        load(path)
    assert exc.value.field == "tour"
    assert "tour" in str(exc.value).lower()


@pytest.mark.parametrize("tour_value", ["data", "Data", "DATA", "feature", "MONEY"])
def test_tour_is_case_insensitive_bare_word(tmp_path, tour_value):
    body = VALID_CHARTER.replace("tour: data", f"tour: {tour_value}")
    path = _write_charter(tmp_path, body)
    charter = load(path)
    assert charter.tour == tour_value.lower()


@pytest.mark.parametrize("bad_tour", ["data tour", "the data tour", "tours-data"])
def test_tour_rejects_non_bare_word(tmp_path, bad_tour):
    body = VALID_CHARTER.replace("tour: data", f"tour: {bad_tour!r}")
    path = _write_charter(tmp_path, body)
    with pytest.raises(CharterError) as exc:
        load(path)
    assert exc.value.field == "tour"
    # Helpful error names the allowed values
    for allowed in ("feature", "data", "money", "interruption", "configuration"):
        assert allowed in str(exc.value)


def test_timebox_must_be_30_60_or_90(tmp_path):
    body = VALID_CHARTER.replace("timebox_minutes: 60", "timebox_minutes: 45")
    path = _write_charter(tmp_path, body)
    with pytest.raises(CharterError) as exc:
        load(path)
    assert exc.value.field == "timebox_minutes"


@pytest.mark.parametrize("ok_timebox", [30, 60, 90])
def test_timebox_accepts_valid_values(tmp_path, ok_timebox):
    body = VALID_CHARTER.replace(
        "timebox_minutes: 60", f"timebox_minutes: {ok_timebox}"
    )
    path = _write_charter(tmp_path, body)
    assert load(path).timebox_minutes == ok_timebox


def test_target_empty_list_rejected(tmp_path):
    body = """
    ---
    schema_version: 1
    session_id: explore-001
    mission: x
    timebox_minutes: 60
    target: []
    tour: data
    runner: gerard
    ---
    """
    path = _write_charter(tmp_path, body)
    with pytest.raises(CharterError) as exc:
        load(path)
    assert exc.value.field == "target"


def test_target_must_be_list_not_scalar(tmp_path):
    body = """
    ---
    schema_version: 1
    session_id: explore-001
    mission: x
    timebox_minutes: 60
    target: ./single.html
    tour: data
    runner: gerard
    ---
    """
    path = _write_charter(tmp_path, body)
    with pytest.raises(CharterError) as exc:
        load(path)
    assert exc.value.field == "target"


@pytest.mark.parametrize(
    "bad_id",
    [
        "explore-1",
        "explore-01",
        "explore-0001",
        "explore-abc",
        "session-001",
        "explore-001a",
    ],
)
def test_session_id_must_be_three_digit(tmp_path, bad_id):
    body = VALID_CHARTER.replace("session_id: explore-001", f"session_id: {bad_id}")
    path = _write_charter(tmp_path, body)
    with pytest.raises(CharterError) as exc:
        load(path)
    assert exc.value.field == "session_id"


def test_file_does_not_exist_raises_charter_error(tmp_path):
    missing = tmp_path / "nope.yml"
    with pytest.raises(CharterError) as exc:
        load(missing)
    assert exc.value.field == "path"


def test_frontmatter_missing_raises_charter_error(tmp_path):
    path = tmp_path / "explore-001.charter.yml"
    path.write_text("schema_version: 1\nmission: x\n", encoding="utf-8")
    with pytest.raises(CharterError) as exc:
        load(path)
    assert exc.value.field == "frontmatter"


def test_runner_unassigned_accepted(tmp_path):
    """ADR-207 / ET-7 fallback — `runner: unassigned` is a valid charter."""
    body = VALID_CHARTER.replace("runner: gerard", "runner: unassigned")
    path = _write_charter(tmp_path, body)
    charter = load(path)
    assert charter.runner == "unassigned"


def test_runner_required(tmp_path):
    body = """
    ---
    schema_version: 1
    session_id: explore-001
    mission: x
    timebox_minutes: 60
    target:
      - ./x.html
    tour: data
    ---
    """
    path = _write_charter(tmp_path, body)
    with pytest.raises(CharterError) as exc:
        load(path)
    assert exc.value.field == "runner"


@pytest.mark.parametrize("bad_version", [0, 2, 3, 99])
def test_schema_version_must_be_one(tmp_path, bad_version):
    """ADR-202 fixes the schema at version 1. A charter declaring a different
    version must be refused so downstream consumers (P11-C07/08) do not
    silently process an incompatible payload."""
    body = VALID_CHARTER.replace("schema_version: 1", f"schema_version: {bad_version}")
    path = _write_charter(tmp_path, body)
    with pytest.raises(CharterError) as exc:
        load(path)
    assert exc.value.field == "schema_version"


def test_charter_error_carries_field_and_reason():
    """CharterError contract: .field and .reason are public attributes."""
    err = CharterError("tour", "missing required field")
    assert err.field == "tour"
    assert err.reason == "missing required field"
    assert "tour" in str(err)
    assert "missing required field" in str(err)
