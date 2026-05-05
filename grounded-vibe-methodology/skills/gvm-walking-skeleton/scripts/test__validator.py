"""P11-C02 unit tests for `_validator.py`.

Spec ref: walking-skeleton ADR-403 (HG-1, HG-2 schema), ADR-404 (HG-3 mock-refusal),
ADR-407 (HG-2 deferred-stub registration via STUBS.md).

Test cases: TC-WS-2-01..02, TC-WS-3-01..03.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from _validator import ValidationError, full_check


# ----------------------------------------------------------------- fixtures


CLEAN_BOUNDARIES = """\
---
schema_version: 1
---
# Boundaries

| name | type | chosen_provider | real_call_status | test_credentials_location | cost_model | sla_notes | production_sandbox_divergence |
|---|---|---|---|---|---|---|---|
| payments-api | http_api | Stripe | wired | `STRIPE_TEST_KEY` env | $0 sandbox | 99.9% | n/a |
"""

SANDBOX_BOUNDARIES = """\
---
schema_version: 1
---
# Boundaries

| name | type | chosen_provider | real_call_status | test_credentials_location | cost_model | sla_notes | production_sandbox_divergence |
|---|---|---|---|---|---|---|---|
| payments-api | http_api | Stripe | wired_sandbox | `STRIPE_TEST_KEY` env | $0 sandbox | 99.9% | Test cards only; no Apple Pay |
"""

DEFERRED_BOUNDARIES = """\
---
schema_version: 1
---
# Boundaries

| name | type | chosen_provider | real_call_status | test_credentials_location | cost_model | sla_notes | production_sandbox_divergence |
|---|---|---|---|---|---|---|---|
| email | email | SendGrid | deferred_stub | n/a | n/a | n/a | n/a |
"""


def _write(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


# ----------------------------------------------------------------- HG-1 / HG-2 schema


def test_clean_boundaries_yields_no_errors(tmp_path: Path) -> None:
    bp = _write(tmp_path, "boundaries.md", CLEAN_BOUNDARIES)
    boundaries, errors = full_check(bp)
    assert errors == []
    assert boundaries is not None
    assert len(boundaries.rows) == 1
    assert boundaries.rows[0].name == "payments-api"


def test_missing_boundaries_file_returns_ws2_error(tmp_path: Path) -> None:
    boundaries, errors = full_check(tmp_path / "nope.md")
    assert boundaries is None
    assert len(errors) == 1
    assert errors[0].code == "WS-2"


def test_malformed_row_yields_ws2_error(tmp_path: Path) -> None:
    # 7 columns instead of 8 (missing production_sandbox_divergence column).
    body = """\
---
schema_version: 1
---
# Boundaries

| name | type | chosen_provider | real_call_status | test_credentials_location | cost_model | sla_notes |
|---|---|---|---|---|---|---|
| x | http_api | Y | wired | env | $0 | 99% |
"""
    bp = _write(tmp_path, "boundaries.md", body)
    boundaries, errors = full_check(bp)
    assert boundaries is None
    assert len(errors) == 1
    assert errors[0].code == "WS-2"


def test_wired_sandbox_with_empty_divergence_yields_ws2_error(tmp_path: Path) -> None:
    # Parser raises DivergenceMissingError; validator surfaces it.
    body = SANDBOX_BOUNDARIES.replace("Test cards only; no Apple Pay", "n/a")
    bp = _write(tmp_path, "boundaries.md", body)
    boundaries, errors = full_check(bp)
    assert boundaries is None
    assert len(errors) == 1
    assert errors[0].code == "WS-2"
    assert "payments-api" in errors[0].message


# ----------------------------------------------------------------- HG-2 deferred-stub cross-check (WS-6)


def _stubs_md_with_email(tmp_path: Path, *, expiry: str = "2026-12-31") -> Path:
    body = f"""\
---
schema_version: 1
---
# Stubs

| Path | Reason | Real-provider Plan | Owner | Expiry |
|---|---|---|---|---|
| walking-skeleton/stubs/email.py | deferred email boundary | swap for SendGrid client | gerard | {expiry} |
"""
    return _write(tmp_path, "STUBS.md", body)


def test_deferred_stub_with_matching_stubs_entry_passes(tmp_path: Path) -> None:
    bp = _write(tmp_path, "boundaries.md", DEFERRED_BOUNDARIES)
    sp = _stubs_md_with_email(tmp_path)
    boundaries, errors = full_check(bp, stubs_path=sp)
    assert errors == []
    assert boundaries is not None


def test_deferred_stub_without_stubs_entry_yields_ws6(tmp_path: Path) -> None:
    bp = _write(tmp_path, "boundaries.md", DEFERRED_BOUNDARIES)
    sp = _write(
        tmp_path,
        "STUBS.md",
        "---\nschema_version: 1\n---\n# Stubs\n\n| Path | Reason | Real-provider Plan | Owner | Expiry |\n|---|---|---|---|---|\n",
    )
    boundaries, errors = full_check(bp, stubs_path=sp)
    assert any(e.code == "WS-6" for e in errors)
    assert any("email" in e.message for e in errors if e.code == "WS-6")


def test_deferred_stub_without_stubs_path_yields_ws6(tmp_path: Path) -> None:
    bp = _write(tmp_path, "boundaries.md", DEFERRED_BOUNDARIES)
    boundaries, errors = full_check(bp, stubs_path=None)
    assert any(e.code == "WS-6" for e in errors)


def test_wired_row_does_not_require_stubs_entry(tmp_path: Path) -> None:
    bp = _write(tmp_path, "boundaries.md", CLEAN_BOUNDARIES)
    boundaries, errors = full_check(bp, stubs_path=None)
    # No deferred_stub rows → no WS-6 errors regardless.
    assert all(e.code != "WS-6" for e in errors)


# ----------------------------------------------------------------- HG-3 mock-refusal (WS-3)


def test_mock_in_skeleton_test_yields_ws3(tmp_path: Path) -> None:
    bp = _write(tmp_path, "boundaries.md", CLEAN_BOUNDARIES)
    skel = _write(
        tmp_path,
        "test_skeleton.py",
        "from unittest.mock import patch\n\ndef test_payments():\n    with patch('requests.get'):\n        pass\n",
    )
    boundaries, errors = full_check(bp, skeleton_test_path=skel)
    assert any(e.code == "WS-3" for e in errors)


def test_real_call_skeleton_test_passes(tmp_path: Path) -> None:
    bp = _write(tmp_path, "boundaries.md", CLEAN_BOUNDARIES)
    skel = _write(
        tmp_path,
        "test_skeleton.py",
        "import requests\n\ndef test_payments():\n    r = requests.get('https://api.stripe.com/v1/charges')\n    assert r.status_code == 200\n",
    )
    boundaries, errors = full_check(bp, skeleton_test_path=skel)
    assert all(e.code != "WS-3" for e in errors)


def test_skeleton_test_path_none_skips_mock_scan(tmp_path: Path) -> None:
    bp = _write(tmp_path, "boundaries.md", CLEAN_BOUNDARIES)
    boundaries, errors = full_check(bp, skeleton_test_path=None)
    assert all(e.code != "WS-3" for e in errors)


def test_empty_skeleton_test_yields_ws3(tmp_path: Path) -> None:
    bp = _write(tmp_path, "boundaries.md", CLEAN_BOUNDARIES)
    skel = _write(tmp_path, "test_skeleton.py", "")
    boundaries, errors = full_check(bp, skeleton_test_path=skel)
    assert any(e.code == "WS-3" for e in errors)


def test_missing_skeleton_test_file_yields_ws3(tmp_path: Path) -> None:
    bp = _write(tmp_path, "boundaries.md", CLEAN_BOUNDARIES)
    boundaries, errors = full_check(
        bp, skeleton_test_path=tmp_path / "does_not_exist.py"
    )
    assert any(e.code == "WS-3" for e in errors)


@pytest.mark.parametrize(
    "pattern",
    [
        "unittest.mock",
        "from mock import",
        "import mock",
        "MagicMock",
        "Mock(",
        "monkeypatch",
        "pytest_mock",
        "mocker.",
    ],
)
def test_python_mock_patterns_all_trigger_ws3(tmp_path: Path, pattern: str) -> None:
    bp = _write(tmp_path, "boundaries.md", CLEAN_BOUNDARIES)
    skel = _write(
        tmp_path,
        "test_skeleton.py",
        f"def test_x(): {pattern}\n    requests.get('https://x')\n",
    )
    boundaries, errors = full_check(
        bp, skeleton_test_path=skel, primary_language="python"
    )
    assert any(e.code == "WS-3" for e in errors), (
        f"pattern {pattern!r} did not trigger WS-3"
    )


@pytest.mark.parametrize(
    "pattern",
    ["vi.mock(", "vi.fn(", "jest.mock(", "jest.fn(", "sinon.stub(", "sinon.fake("],
)
def test_typescript_mock_patterns_all_trigger_ws3(tmp_path: Path, pattern: str) -> None:
    bp = _write(tmp_path, "boundaries.md", CLEAN_BOUNDARIES)
    skel = _write(
        tmp_path,
        "test_skeleton.ts",
        f"test('payments', () => {{ {pattern} }})\n",
    )
    boundaries, errors = full_check(
        bp, skeleton_test_path=skel, primary_language="typescript"
    )
    assert any(e.code == "WS-3" for e in errors), (
        f"pattern {pattern!r} did not trigger WS-3"
    )


# ----------------------------------------------------------------- ValidationError shape


def test_validation_error_is_frozen() -> None:
    e = ValidationError(code="WS-2", message="x")
    with pytest.raises(Exception):
        e.code = "WS-3"  # type: ignore[misc]


def test_validation_error_has_code_and_message() -> None:
    e = ValidationError(code="WS-3", message="mock detected at line 4")
    assert e.code == "WS-3"
    assert "mock detected" in e.message


# ----------------------------------------------------------------- combined / aggregation


def test_multiple_errors_returned_together(tmp_path: Path) -> None:
    """When several gates fail, all errors are returned in one call —
    the practitioner sees the full picture, not one error at a time."""
    bp = _write(tmp_path, "boundaries.md", DEFERRED_BOUNDARIES)
    skel = _write(
        tmp_path,
        "test_skeleton.py",
        "from unittest.mock import patch\n",
    )
    # No stubs_path supplied AND mocked skeleton → at least 2 errors.
    boundaries, errors = full_check(bp, skeleton_test_path=skel, stubs_path=None)
    codes = {e.code for e in errors}
    assert "WS-3" in codes
    assert "WS-6" in codes


# ----------------------------------------------------------------- R24 I-2: bare-Exception path
# Beck: a branch that exists in code must be exercised by a test or it is
# unfinished work. The third `except Exception` clause in `full_check`
# catches any unanticipated parser error — without this test, a refactor
# that drops it would not regress any test.


def test_unexpected_load_boundaries_exception_returns_ws2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Beck: every code branch needs a test. The bare `except Exception`
    in `full_check` must demote unanticipated parser errors to WS-2 so
    the practitioner sees a structured error, not a stack trace.

    Note: the conftest's autouse fixture evicts `_validator` from
    sys.modules between tests, so we must re-import inside the test
    body to get the same module instance our `full_check` reference
    will use. Otherwise monkeypatch acts on a stale module."""
    bp = _write(tmp_path, "boundaries.md", CLEAN_BOUNDARIES)
    import _validator as v  # noqa: PLC0415

    def boom(_path: object) -> object:
        raise RuntimeError("internal error")

    monkeypatch.setattr(v, "load_boundaries", boom)
    boundaries, errors = v.full_check(bp)
    assert boundaries is None
    assert len(errors) == 1
    assert errors[0].code == "WS-2"
    assert "internal error" in errors[0].message


# ----------------------------------------------------------------- R24 I-3: empty skeleton + zero wired
# McConnell: deliberately silent-pass states must be locked by a test so
# refactors cannot re-flip the semantics without breaking something visible.


_ALL_DEFERRED_BOUNDARIES = """\
---
schema_version: 1
---
# Boundaries

| name | type | chosen_provider | real_call_status | test_credentials_location | cost_model | sla_notes | production_sandbox_divergence |
|---|---|---|---|---|---|---|---|
| later-api | http_api | Vendor | deferred | n/a | n/a | n/a | n/a |
"""


def test_empty_skeleton_with_zero_wired_passes_ws3(tmp_path: Path) -> None:
    """Spec intent (ADR-404): mock-scan only fires when there is at least
    one wired boundary. Zero-wired + empty skeleton = nothing to mock,
    nothing to scan. Locked here so it cannot regress silently."""
    bp = _write(tmp_path, "boundaries.md", _ALL_DEFERRED_BOUNDARIES)
    skel = _write(tmp_path, "test_skeleton.py", "")
    stubs = _write(
        tmp_path,
        "STUBS.md",
        """---
schema_version: 1
---
| ID | Path | Reason | Real provider plan | Owner | Expiry |
|---|---|---|---|---|---|
| STUB-01 | walking-skeleton/stubs/later-api.py | deferred | Vendor real | gerard | 2030-01-01 |
""",
    )
    _, errors = full_check(bp, skeleton_test_path=skel, stubs_path=stubs)
    ws3 = [e for e in errors if e.code == "WS-3"]
    assert ws3 == []  # silent pass is the deliberate behaviour
