"""Tests for `_boundaries_parser.py` — boundaries.md schema (ADR-005, ADR-403)."""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from _schema import SchemaTooNewError
from _boundaries_parser import (
    Boundaries,
    BoundariesParseError,
    Boundary,
    ChangelogEntry,
    DivergenceMissingError,
    MalformedRowError,
    load_boundaries,
    serialise,
)

VALID_HEADER = "---\nschema_version: 1\n---\n# Boundaries\n\n"
TABLE_HEAD = (
    "| name | type | chosen_provider | real_call_status | test_credentials_location | cost_model | sla_notes | production_sandbox_divergence |\n"
    "|---|---|---|---|---|---|---|---|\n"
)


def _write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "boundaries.md"
    p.write_text(body, encoding="utf-8")
    return p


def _row(
    name: str,
    type_: str = "http_api",
    provider: str = "Stripe",
    status: str = "wired",
    creds: str = "ENV_VAR",
    cost: str = "free",
    sla: str = "n/a",
    divergence: str = "n/a",
) -> str:
    return f"| {name} | {type_} | {provider} | {status} | {creds} | {cost} | {sla} | {divergence} |\n"


# --- Happy path ---


def test_loads_three_rows(tmp_path):
    body = (
        VALID_HEADER
        + TABLE_HEAD
        + _row("payments-api", status="wired_sandbox", divergence="rate limits differ")
        + _row("user-db", type_="database", status="wired", divergence="n/a")
        + _row(
            "email",
            type_="email",
            status="deferred_stub",
            creds="n/a",
            cost="n/a",
            divergence="n/a",
        )
    )
    b = load_boundaries(_write(tmp_path, body))
    assert b.schema_version == 1
    assert len(b.rows) == 3
    assert b.rows[0].name == "payments-api"
    assert b.rows[0].real_call_status == "wired_sandbox"
    assert b.rows[0].production_sandbox_divergence == "rate limits differ"
    assert b.rows[1].type == "database"
    assert b.rows[2].real_call_status == "deferred_stub"
    assert b.changelog == ()


def test_changelog_optional(tmp_path):
    body = (
        VALID_HEADER
        + TABLE_HEAD
        + _row("only", divergence="n/a")
        + "\n## Changelog\n| Date | Change | Rationale |\n|---|---|---|\n"
        + "| 2026-04-25 | added only | initial |\n"
    )
    b = load_boundaries(_write(tmp_path, body))
    assert len(b.changelog) == 1
    assert b.changelog[0].change == "added only"


# --- Schema delegation ---


def test_schema_too_new_propagates(tmp_path):
    body = "---\nschema_version: 99\n---\n# Boundaries\n\n" + TABLE_HEAD
    with pytest.raises(SchemaTooNewError):
        load_boundaries(_write(tmp_path, body))


# --- Structural failures ---


def test_missing_h1_raises(tmp_path):
    body = "---\nschema_version: 1\n---\n" + TABLE_HEAD + _row("x")
    with pytest.raises(MalformedRowError, match="Boundaries"):
        load_boundaries(_write(tmp_path, body))


def test_wrong_column_headers_raise(tmp_path):
    bad_head = (
        "| name | type | chosen_provider | real_call_status | creds | cost_model | sla_notes | production_sandbox_divergence |\n"
        "|---|---|---|---|---|---|---|---|\n"
    )
    body = VALID_HEADER + bad_head + _row("x")
    with pytest.raises(MalformedRowError, match="header"):
        load_boundaries(_write(tmp_path, body))


def test_wrong_column_count_raises(tmp_path):
    body = VALID_HEADER + TABLE_HEAD + "| only-three | http_api | Stripe |\n"
    with pytest.raises(MalformedRowError, match="column"):
        load_boundaries(_write(tmp_path, body))


@pytest.mark.parametrize(
    "field, kwargs",
    [
        ("name", {"name": ""}),
        ("chosen_provider", {"name": "x", "provider": ""}),
        ("test_credentials_location", {"name": "x", "creds": ""}),
        ("cost_model", {"name": "x", "cost": ""}),
        ("sla_notes", {"name": "x", "sla": ""}),
    ],
)
def test_empty_required_field_raises(tmp_path, field, kwargs):
    body = VALID_HEADER + TABLE_HEAD + _row(**kwargs)
    with pytest.raises(MalformedRowError, match=field):
        load_boundaries(_write(tmp_path, body))


# --- Enum validation ---


def test_bad_type_enum_raises(tmp_path):
    body = VALID_HEADER + TABLE_HEAD + _row("x", type_="not_a_type")
    with pytest.raises(MalformedRowError, match="type"):
        load_boundaries(_write(tmp_path, body))


def test_bad_status_enum_raises(tmp_path):
    body = VALID_HEADER + TABLE_HEAD + _row("x", status="kinda_wired")
    with pytest.raises(MalformedRowError, match="real_call_status"):
        load_boundaries(_write(tmp_path, body))


# --- Uniqueness ---


def test_duplicate_name_raises(tmp_path):
    body = VALID_HEADER + TABLE_HEAD + _row("dup") + _row("dup")
    with pytest.raises(MalformedRowError, match="duplicate"):
        load_boundaries(_write(tmp_path, body))


# --- Cross-field divergence rule ---


def test_wired_sandbox_with_na_divergence_raises_specific(tmp_path):
    body = (
        VALID_HEADER
        + TABLE_HEAD
        + _row("payments-api", status="wired_sandbox", divergence="n/a")
    )
    with pytest.raises(DivergenceMissingError) as exc_info:
        load_boundaries(_write(tmp_path, body))
    assert exc_info.value.boundary_name == "payments-api"
    assert isinstance(exc_info.value, BoundariesParseError)


def test_wired_sandbox_with_empty_divergence_raises_specific(tmp_path):
    body = (
        VALID_HEADER
        + TABLE_HEAD
        + _row("payments-api", status="wired_sandbox", divergence="")
    )
    with pytest.raises(DivergenceMissingError):
        load_boundaries(_write(tmp_path, body))


def test_wired_with_non_na_divergence_raises_malformed(tmp_path):
    body = (
        VALID_HEADER
        + TABLE_HEAD
        + _row("user-db", status="wired", divergence="some note")
    )
    with pytest.raises(MalformedRowError, match="divergence"):
        load_boundaries(_write(tmp_path, body))


def test_deferred_stub_with_non_na_divergence_raises_malformed(tmp_path):
    body = (
        VALID_HEADER
        + TABLE_HEAD
        + _row("email", status="deferred_stub", divergence="something")
    )
    with pytest.raises(MalformedRowError, match="divergence"):
        load_boundaries(_write(tmp_path, body))


# --- Round-trip property (extra insurance) ---


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
_safe_divergence = (
    st.text(
        alphabet=st.characters(
            blacklist_characters=_SPLITLINES_CHARS,
            blacklist_categories=("Cs",),
        ),
        min_size=1,
        max_size=40,
    )
    .map(str.strip)
    .filter(lambda s: len(s) >= 1 and s != "n/a")
)


@st.composite
def _boundaries(draw):
    n = draw(st.integers(min_value=1, max_value=4))
    rows: list[Boundary] = []
    used_names: set[str] = set()
    for _ in range(n):
        while True:
            name = draw(_safe_text)
            if name not in used_names:
                used_names.add(name)
                break
        status = draw(st.sampled_from(["wired", "wired_sandbox", "deferred_stub"]))
        type_ = draw(
            st.sampled_from(
                [
                    "http_api",
                    "database",
                    "filesystem",
                    "sdk",
                    "queue",
                    "email",
                    "sms",
                    "other",
                ]
            )
        )
        divergence = draw(_safe_divergence) if status == "wired_sandbox" else "n/a"
        rows.append(
            Boundary(
                name=name,
                type=type_,
                chosen_provider=draw(_safe_text),
                real_call_status=status,
                test_credentials_location=draw(_safe_text),
                cost_model=draw(_safe_text),
                sla_notes=draw(_safe_text),
                production_sandbox_divergence=divergence,
            )
        )
    cl_n = draw(st.integers(min_value=0, max_value=2))
    changelog = tuple(
        ChangelogEntry(
            date=draw(_safe_text), change=draw(_safe_text), rationale=draw(_safe_text)
        )
        for _ in range(cl_n)
    )
    return Boundaries(schema_version=1, rows=tuple(rows), changelog=changelog)


@settings(max_examples=80)
@given(_boundaries())
def test_round_trip_preserves_boundaries(tmp_path_factory, b):
    tmp = tmp_path_factory.mktemp("rt")
    f = tmp / "boundaries.md"
    f.write_text(serialise(b), encoding="utf-8")
    parsed = load_boundaries(f)
    assert parsed == b
