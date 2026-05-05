"""Tests for `_stubs_parser.py` — STUBS.md schema (ADR-004, ADR-101).

Includes the HS-1-03 property test (parse/serialise round-trip).
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from _schema import SchemaTooNewError
from _stubs_parser import (
    StubEntry,
    StubsParseError,
    check_expiry,
    load_stubs,
    serialise,
    validate_plan,
)

VALID_HEADER = "---\nschema_version: 1\n---\n# Stubs\n\n"
TABLE_HEAD = (
    "| Path | Reason | Real-provider Plan | Owner | Expiry |\n|---|---|---|---|---|\n"
)


def _write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "STUBS.md"
    p.write_text(body, encoding="utf-8")
    return p


# --- Happy path ---


def test_loads_single_row(tmp_path):
    f = _write(
        tmp_path,
        VALID_HEADER
        + TABLE_HEAD
        + "| stubs/mock_provider.py | Rightmove paywall deferred | Rightmove API v3 | gq | 2026-06-01 |\n",
    )
    entries = load_stubs(f)
    assert len(entries) == 1
    e = entries[0]
    assert isinstance(e, StubEntry)
    assert e.path == "stubs/mock_provider.py"
    assert e.reason == "Rightmove paywall deferred"
    assert e.real_provider_plan == "Rightmove API v3"
    assert e.owner == "gq"
    assert e.expiry == dt.date(2026, 6, 1)


def test_loads_multiple_rows_preserve_order(tmp_path):
    rows = (
        "| stubs/a.py | reason number one | plan A | gq | 2026-06-01 |\n"
        "| stubs/b.py | reason number two | plan B | alice | 2026-07-01 |\n"
        "| walking-skeleton/stubs/c.py | reason number three | unknown | bob | 2026-08-01 |\n"
    )
    f = _write(tmp_path, VALID_HEADER + TABLE_HEAD + rows)
    entries = load_stubs(f)
    assert [e.path for e in entries] == [
        "stubs/a.py",
        "stubs/b.py",
        "walking-skeleton/stubs/c.py",
    ]


def test_empty_table_is_valid(tmp_path):
    f = _write(tmp_path, VALID_HEADER + TABLE_HEAD)
    assert load_stubs(f) == []


TABLE_HEAD_WITH_REQUIREMENT = (
    "| Path | Reason | Real-provider Plan | Owner | Expiry | Requirement |\n"
    "|---|---|---|---|---|---|\n"
)


def test_loads_row_with_optional_requirement_column(tmp_path):
    f = _write(
        tmp_path,
        VALID_HEADER
        + TABLE_HEAD_WITH_REQUIREMENT
        + "| stubs/x.py | reason ten chars | plan A | gq | 2026-06-01 | GS-2 |\n",
    )
    entries = load_stubs(f)
    assert len(entries) == 1
    assert entries[0].requirement == "GS-2"


def test_loads_row_without_requirement_column_defaults_to_none(tmp_path):
    f = _write(
        tmp_path,
        VALID_HEADER
        + TABLE_HEAD
        + "| stubs/x.py | reason ten chars | plan A | gq | 2026-06-01 |\n",
    )
    entries = load_stubs(f)
    assert entries[0].requirement is None


def test_six_column_header_without_six_cells_raises(tmp_path):
    f = _write(
        tmp_path,
        VALID_HEADER
        + TABLE_HEAD_WITH_REQUIREMENT
        + "| stubs/x.py | reason ten chars | plan | gq | 2026-06-01 |\n",
    )
    with pytest.raises(StubsParseError, match="column"):
        load_stubs(f)


def test_empty_requirement_cell_is_none(tmp_path):
    f = _write(
        tmp_path,
        VALID_HEADER
        + TABLE_HEAD_WITH_REQUIREMENT
        + "| stubs/x.py | reason ten chars | plan A | gq | 2026-06-01 |  |\n",
    )
    entries = load_stubs(f)
    assert entries[0].requirement is None


def test_serialise_includes_requirement_column_when_any_entry_has_one():
    entries = [
        StubEntry(
            path="stubs/x.py",
            reason="reason ten chars",
            real_provider_plan="plan",
            owner="gq",
            expiry=dt.date(2026, 6, 1),
            requirement="GS-2",
        ),
    ]
    text = serialise(entries)
    assert "Requirement" in text
    assert "GS-2" in text


def test_serialise_omits_requirement_column_when_no_entry_has_one():
    entries = [
        StubEntry(
            path="stubs/x.py",
            reason="reason ten chars",
            real_provider_plan="plan",
            owner="gq",
            expiry=dt.date(2026, 6, 1),
        ),
    ]
    text = serialise(entries)
    assert "Requirement" not in text


def test_walking_skeleton_path_accepted(tmp_path):
    f = _write(
        tmp_path,
        VALID_HEADER
        + TABLE_HEAD
        + "| walking-skeleton/stubs/x.py | placeholder ten chars | unknown | gq | 2026-06-01 |\n",
    )
    entries = load_stubs(f)
    assert entries[0].path == "walking-skeleton/stubs/x.py"


# --- Schema delegation ---


def test_schema_too_new_propagates(tmp_path):
    f = _write(
        tmp_path,
        "---\nschema_version: 99\n---\n# Stubs\n\n" + TABLE_HEAD,
    )
    with pytest.raises(SchemaTooNewError):
        load_stubs(f)


# --- Row validation failures ---


@pytest.mark.parametrize(
    "row, match",
    [
        # Path not under stubs/ or walking-skeleton/stubs/
        (
            "| src/x.py | reason ten chars | plan | gq | 2026-06-01 |\n",
            "path",
        ),
        # Reason too short (< 10 chars)
        (
            "| stubs/x.py | short | plan | gq | 2026-06-01 |\n",
            "reason",
        ),
        # Empty plan
        (
            "| stubs/x.py | reason ten chars | | gq | 2026-06-01 |\n",
            "plan",
        ),
        # Empty owner
        (
            "| stubs/x.py | reason ten chars | plan |  | 2026-06-01 |\n",
            "owner",
        ),
        # Bad expiry format
        (
            "| stubs/x.py | reason ten chars | plan | gq | 06/01/2026 |\n",
            "expiry",
        ),
        # Wrong number of columns
        (
            "| stubs/x.py | reason ten chars | plan | gq |\n",
            "column",
        ),
    ],
)
def test_row_validation_failures(tmp_path, row, match):
    f = _write(tmp_path, VALID_HEADER + TABLE_HEAD + row)
    with pytest.raises(StubsParseError, match=match):
        load_stubs(f)


def test_missing_h1_raises(tmp_path):
    f = _write(tmp_path, "---\nschema_version: 1\n---\n" + TABLE_HEAD)
    with pytest.raises(StubsParseError, match="# Stubs"):
        load_stubs(f)


def test_wrong_column_headers_raise(tmp_path):
    bad_head = (
        "| Path | Reason | Plan | Owner | Expiry |\n"
        "|---|---|---|---|---|\n"
        "| stubs/x.py | reason ten chars | plan | gq | 2026-06-01 |\n"
    )
    f = _write(tmp_path, VALID_HEADER + bad_head)
    with pytest.raises(StubsParseError, match="header"):
        load_stubs(f)


# --- HS-7 plan validator ---


def test_validate_plan_concrete_returns_true():
    assert validate_plan("Stripe SDK 5.x") is True


def test_validate_plan_unknown_returns_false():
    assert validate_plan("unknown") is False


def test_validate_plan_empty_returns_false():
    assert validate_plan("") is False


# --- HS-7 → VV-4(f) wiring (TC-HS-7-02) ---


def _entry(path: str, plan: str) -> StubEntry:
    return StubEntry(
        path=path,
        reason="reason ten chars",
        real_provider_plan=plan,
        owner="gq",
        expiry=dt.date(2099, 1, 1),
    )


def test_vv4_f_status_empty_is_na():
    from _stubs_parser import vv4_f_status

    status, evidence = vv4_f_status([])
    assert status == "NA"
    assert "no stubs" in evidence.lower()


def test_vv4_f_status_all_concrete_is_pass():
    from _stubs_parser import vv4_f_status

    entries = [
        _entry("stubs/a.py", "Stripe SDK 5.x"),
        _entry("stubs/b.py", "Rightmove API v3"),
    ]
    status, evidence = vv4_f_status(entries)
    assert status == "PASS"
    assert "no unknown plan" in evidence


def test_vv4_f_status_any_unknown_is_fail():
    from _stubs_parser import vv4_f_status

    entries = [
        _entry("stubs/a.py", "Stripe SDK 5.x"),
        _entry("stubs/b.py", "unknown"),
        _entry("stubs/c.py", ""),
    ]
    status, evidence = vv4_f_status(entries)
    assert status == "FAIL"
    # Evidence must list ALL offending paths, not just the first.
    assert "stubs/b.py" in evidence
    assert "stubs/c.py" in evidence
    assert "unknown" in evidence


def test_vv4_f_status_slots_into_verdict_inputs():
    """Return shape is `tuple[CriterionStatus, str]` — slots into VerdictInputs.vv4_f."""
    import sys
    from pathlib import Path

    test_dir = Path(__file__).resolve().parents[2] / "gvm-test" / "scripts"
    if str(test_dir) not in sys.path:
        sys.path.insert(0, str(test_dir))
    from gvm_verdict import VerdictInputs  # noqa: E402

    from _stubs_parser import vv4_f_status

    vv4_f = vv4_f_status([_entry("stubs/a.py", "unknown")])
    inputs = VerdictInputs(
        vv2_a=("PASS", ""),
        vv2_b=("PASS", ""),
        vv2_c=("PASS", ""),
        vv3_a=("PASS", ""),
        vv3_b=("PASS", ""),
        vv3_c=("PASS", ""),
        vv3_d=("PASS", ""),
        vv4_a=("PASS", ""),
        vv4_b=("PASS", ""),
        vv4_c=("PASS", ""),
        vv4_d=("PASS", ""),
        vv4_e=("PASS", ""),
        vv4_f=vv4_f,
    )
    assert inputs.vv4_f[0] == "FAIL"


# --- check_expiry boundary (TC-HS-2-01, TC-HS-2-02) ---


def _stub(path: str, expiry: dt.date) -> StubEntry:
    return StubEntry(
        path=path,
        reason="reason ten chars",
        real_provider_plan="plan",
        owner="gq",
        expiry=expiry,
    )


def test_check_expiry_today_equals_expiry_not_expired():
    s = _stub("stubs/x.py", dt.date(2026, 4, 22))
    today = dt.date(2026, 4, 22)
    assert check_expiry([s], today) == []


def test_check_expiry_today_after_expiry_returns_entry():
    s = _stub("stubs/x.py", dt.date(2026, 4, 21))
    today = dt.date(2026, 4, 22)
    assert check_expiry([s], today) == [s]


def test_check_expiry_today_before_expiry_not_expired():
    s = _stub("stubs/x.py", dt.date(2026, 12, 31))
    today = dt.date(2026, 4, 22)
    assert check_expiry([s], today) == []


def test_check_expiry_returns_only_expired_subset():
    a = _stub("stubs/a.py", dt.date(2026, 1, 1))
    b = _stub("stubs/b.py", dt.date(2999, 1, 1))
    today = dt.date(2026, 6, 1)
    assert check_expiry([a, b], today) == [a]


# --- HS-1-03 round-trip property ---


# Forbid pipe (table delimiter) and every codepoint Python's str.splitlines()
# treats as a line separator: \n \r \v \f \x1c \x1d \x1e \x85 \u2028 \u2029.
_SPLITLINES_CHARS = "|\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029"
_safe_text = st.text(
    alphabet=st.characters(
        blacklist_characters=_SPLITLINES_CHARS,
        blacklist_categories=("Cs",),  # surrogates are not encodable as UTF-8
    ),
    min_size=10,
    max_size=80,
).map(str.strip)


@st.composite
def _stub_entries(draw):
    suffix = draw(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_-."
            ),
            min_size=1,
            max_size=20,
        )
    )
    prefix = draw(st.sampled_from(["stubs/", "walking-skeleton/stubs/"]))
    path = prefix + suffix + ".py"

    reason = draw(_safe_text.filter(lambda s: len(s) >= 10))
    plan = draw(
        st.one_of(
            st.just("unknown"),
            _safe_text.filter(lambda s: s and s != "unknown"),
        )
    )
    owner = draw(_safe_text.filter(lambda s: len(s) >= 1))
    expiry = draw(
        st.dates(min_value=dt.date(2000, 1, 1), max_value=dt.date(2100, 12, 31))
    )

    return StubEntry(
        path=path,
        reason=reason,
        real_provider_plan=plan,
        owner=owner,
        expiry=expiry,
    )


@settings(max_examples=100)
@given(st.lists(_stub_entries(), min_size=0, max_size=5))
def test_round_trip_preserves_entries(tmp_path_factory, entries):
    tmp = tmp_path_factory.mktemp("rt")
    f = tmp / "STUBS.md"
    f.write_text(serialise(entries), encoding="utf-8")
    parsed = load_stubs(f)
    assert parsed == entries


def test_round_trip_leap_day():
    e = StubEntry(
        path="stubs/leap.py",
        reason="leap day boundary case",
        real_provider_plan="real api",
        owner="gq",
        expiry=dt.date(2024, 2, 29),
    )
    parsed = _round_trip([e])
    assert parsed[0].expiry == dt.date(2024, 2, 29)


def test_round_trip_unicode_path():
    e = StubEntry(
        path="stubs/ünïcödé_module.py",
        reason="unicode path counterexample",
        real_provider_plan="ascii plan",
        owner="gq",
        expiry=dt.date(2026, 6, 1),
    )
    parsed = _round_trip([e])
    assert parsed[0].path == "stubs/ünïcödé_module.py"


def _round_trip(
    entries: list[StubEntry], tmp_path: Path | None = None
) -> list[StubEntry]:
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "STUBS.md"
        f.write_text(serialise(entries), encoding="utf-8")
        return load_stubs(f)
