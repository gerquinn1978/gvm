"""Test suite for _ebt_contract_lint.py — 13 cases per spec P12-C02.

Uses tmp_path fixtures to write real Python/TS/Go test files on disk so the
linter's AST-based and text-based detectors run against genuine source.
No mocks of the lint function itself — the suite is a dogfood target.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from _ebt_contract_lint import detect_source_root, lint


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def write_py(tmp_path: Path, name: str, src: str) -> Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(src))
    return p


def write_ts(tmp_path: Path, name: str, src: str) -> Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(src))
    return p


def write_go(tmp_path: Path, name: str, src: str) -> Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(src))
    return p


def pyproject(directory: Path) -> Path:
    p = directory / "pyproject.toml"
    p.write_text('[tool.poetry]\nname = "myproject"\n')
    return p


# ---------------------------------------------------------------------------
# TC-EBT-1 — positive control: clean test emits no violations
# ---------------------------------------------------------------------------


def test_tc_ebt_2_01_positive_control_no_violations(tmp_path: Path) -> None:
    """TC-EBT-2-01: clean test — no patches against HTTP transports."""
    src = """\
        def test_foo():
            result = 1 + 1
            assert result == 2
    """
    f = write_py(tmp_path, "test_clean.py", src)
    violations = lint(f, ebt_boundaries_path=None, source_root=None)
    assert violations == []


# ---------------------------------------------------------------------------
# TC-EBT-2 — missing negative test detection (positive that lint returns something)
# ---------------------------------------------------------------------------


def test_tc_ebt_2_02_rainsberger_requests_get_detected(tmp_path: Path) -> None:
    """TC-EBT-2-02: requests.get patched — lint must detect Rainsberger."""
    src = """\
        from unittest.mock import patch

        def test_get_user():
            with patch("requests.get") as mock_get:
                mock_get.return_value.json.return_value = {"id": 1}
                result = {"id": 1}
            assert result == {"id": 1}
    """
    f = write_py(tmp_path, "test_missing_negative.py", src)
    violations = lint(f, ebt_boundaries_path=None, source_root=None)
    assert len(violations) >= 1
    assert any(v.kind == "rainsberger" for v in violations)


# ---------------------------------------------------------------------------
# TC-EBT-3-01 — Python: requests.get patched → 1 Rainsberger
# ---------------------------------------------------------------------------


def test_tc_ebt_3_01_python_requests_get_rainsberger(tmp_path: Path) -> None:
    """Patching requests.get in a consumer test → one Rainsberger violation."""
    src = """\
        from unittest.mock import patch

        def test_fetch_data():
            with patch("requests.get") as m:
                m.return_value.status_code = 200
                assert m.called or True
    """
    f = write_py(tmp_path, "test_requests.py", src)
    violations = lint(f, ebt_boundaries_path=None, source_root=None)
    rainsberger = [v for v in violations if v.kind == "rainsberger"]
    assert len(rainsberger) == 1
    assert (
        "requests.get" in rainsberger[0].detail
        or "HTTP transport" in rainsberger[0].detail
    )
    assert "test_fetch_data" in rainsberger[0].test_id


# ---------------------------------------------------------------------------
# TC-EBT-3-02 — Python: httpx.AsyncClient patched → 1 Rainsberger
# ---------------------------------------------------------------------------


def test_tc_ebt_3_02_python_httpx_async_client_rainsberger(tmp_path: Path) -> None:
    """Patching httpx.AsyncClient.send in a consumer test → one Rainsberger."""
    src = """\
        from unittest.mock import patch

        def test_call_api():
            with patch("httpx.AsyncClient.send") as m:
                m.return_value = None
                assert True
    """
    f = write_py(tmp_path, "test_httpx.py", src)
    violations = lint(f, ebt_boundaries_path=None, source_root=None)
    rainsberger = [v for v in violations if v.kind == "rainsberger"]
    assert len(rainsberger) == 1
    assert "httpx" in rainsberger[0].detail or "HTTP transport" in rainsberger[0].detail


# ---------------------------------------------------------------------------
# TC-EBT-4-01 — [CONTRACT] test with real classes → 0 Metz
# ---------------------------------------------------------------------------


def test_tc_ebt_4_01_contract_test_real_classes_no_metz(tmp_path: Path) -> None:
    """[CONTRACT] test that only instantiates real classes → no Metz violation."""
    src = """\
        def test_order_service_contract():
            \"\"\"[CONTRACT] Tests the OrderService collaboration protocol.\"\"\"
            svc = object()  # pretend real instantiation
            assert svc is not None
    """
    f = write_py(tmp_path, "test_contract_clean.py", src)
    violations = lint(
        f,
        ebt_boundaries_path=None,
        source_root=tmp_path,
    )
    metz = [v for v in violations if v.kind == "metz"]
    assert metz == []


# ---------------------------------------------------------------------------
# TC-EBT-4-02 — [CONTRACT] test patching internal class → 1 Metz
# ---------------------------------------------------------------------------


def test_tc_ebt_4_02_contract_test_internal_class_metz(tmp_path: Path) -> None:
    """[CONTRACT] test patching an internal class → one Metz violation."""
    # source_root is tmp_path; mock target "myapp.services.UserRepo" is internal
    src = """\
        from unittest.mock import patch

        def test_user_service_contract():
            \"\"\"[CONTRACT] Tests the UserService collaboration.\"\"\"
            with patch("myapp.services.UserRepo") as m:
                m.return_value.find.return_value = None
                assert True
    """
    f = write_py(tmp_path, "test_contract_metz.py", src)
    violations = lint(
        f,
        ebt_boundaries_path=None,
        source_root=tmp_path,
    )
    metz = [v for v in violations if v.kind == "metz"]
    assert len(metz) == 1
    assert "metz" == metz[0].kind
    assert "UserRepo" in metz[0].detail or "myapp" in metz[0].detail


# ---------------------------------------------------------------------------
# TC-7 — .ebt-boundaries allowlist suppresses internal-path mock
# ---------------------------------------------------------------------------


def test_allowlist_suppresses_internal_path_mock(tmp_path: Path) -> None:
    """When the mock target matches .ebt-boundaries, no Metz violation."""
    # Write a .ebt-boundaries that explicitly allows myapp.services.*
    boundaries_file = tmp_path / ".ebt-boundaries"
    boundaries_file.write_text("# allowed\nmyapp.services.*\n")

    src = """\
        from unittest.mock import patch

        def test_user_contract():
            \"\"\"[CONTRACT] Tests the UserService protocol.\"\"\"
            with patch("myapp.services.UserRepo") as m:
                m.return_value.find.return_value = None
                assert True
    """
    f = write_py(tmp_path, "test_allow.py", src)
    violations = lint(
        f,
        ebt_boundaries_path=boundaries_file,
        source_root=tmp_path,
    )
    metz = [v for v in violations if v.kind == "metz"]
    assert metz == [], (
        f"Expected no Metz violations; allowlist should suppress. Got: {metz}"
    )


# ---------------------------------------------------------------------------
# TC-8 — stack defaults include requests.* (Rainsberger) but not Metz
# ---------------------------------------------------------------------------


def test_stack_defaults_requests_triggers_rainsberger_not_metz(tmp_path: Path) -> None:
    """requests.* is in stack defaults: patch triggers Rainsberger but not Metz."""
    src = """\
        from unittest.mock import patch

        def test_something():
            \"\"\"[CONTRACT] tests.\"\"\"
            with patch("requests.get") as m:
                m.return_value.status_code = 200
                assert True
    """
    f = write_py(tmp_path, "test_defaults.py", src)
    violations = lint(f, ebt_boundaries_path=None, source_root=tmp_path)
    kinds = {v.kind for v in violations}
    assert "rainsberger" in kinds
    assert "metz" not in kinds


# ---------------------------------------------------------------------------
# TC-9 — detect_source_root: Python pyproject.toml walk-up; src/ layout
# ---------------------------------------------------------------------------


def test_detect_source_root_pyproject(tmp_path: Path) -> None:
    """detect_source_root walks up to find pyproject.toml."""
    sub = tmp_path / "tests"
    sub.mkdir()
    pyproject(tmp_path)
    test_file = sub / "test_foo.py"
    test_file.write_text("def test_x(): pass\n")

    root = detect_source_root(test_file, stack="python")
    assert root is not None
    assert root == tmp_path or root == tmp_path / "src"


def test_detect_source_root_src_layout(tmp_path: Path) -> None:
    """detect_source_root returns src/ when it exists alongside pyproject.toml."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    pyproject(tmp_path)
    sub = tmp_path / "tests"
    sub.mkdir()
    test_file = sub / "test_foo.py"
    test_file.write_text("def test_x(): pass\n")

    root = detect_source_root(test_file, stack="python")
    assert root == src_dir


def test_detect_source_root_tsconfig(tmp_path: Path) -> None:
    """detect_source_root for TypeScript reads rootDir from tsconfig.json."""
    tsconfig = tmp_path / "tsconfig.json"
    tsconfig.write_text('{"compilerOptions": {"rootDir": "src"}}')
    test_file = tmp_path / "test_foo.ts"
    test_file.write_text("// test\n")

    root = detect_source_root(test_file, stack="typescript")
    assert root is not None
    assert root == tmp_path / "src"


def test_detect_source_root_go_mod(tmp_path: Path) -> None:
    """detect_source_root for Go finds the directory containing go.mod."""
    go_mod = tmp_path / "go.mod"
    go_mod.write_text("module example.com/mymodule\ngo 1.21\n")
    test_file = tmp_path / "mypackage" / "foo_test.go"
    test_file.parent.mkdir()
    test_file.write_text("package mypackage\n")

    root = detect_source_root(test_file, stack="go")
    assert root == tmp_path


# ---------------------------------------------------------------------------
# TC-10 — Go: localhost exclusion
# ---------------------------------------------------------------------------


def test_go_localhost_exclusion(tmp_path: Path) -> None:
    """http://localhost:8080 in a Go test does NOT trigger Rainsberger."""
    src = """\
import "net/http"

func TestFoo(t *testing.T) {
    resp, _ := http.Get("http://localhost:8080/health")
    _ = resp
}
"""
    f = write_go(tmp_path, "foo_test.go", src)
    violations = lint(f, ebt_boundaries_path=None, source_root=None, stack="go")
    rainsberger = [v for v in violations if v.kind == "rainsberger"]
    assert rainsberger == [], f"localhost should not trigger. Got: {rainsberger}"


# ---------------------------------------------------------------------------
# TC-11 — Go: httptest.New exclusion
# ---------------------------------------------------------------------------


def test_go_httptest_new_exclusion(tmp_path: Path) -> None:
    """httptest.NewServer(...) line with URL does NOT trigger Rainsberger."""
    src = """\
import (
    "net/http"
    "net/http/httptest"
)

func TestBar(t *testing.T) {
    ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {}))
    defer ts.Close()
    resp, _ := http.Get(ts.URL)
    _ = resp
}
"""
    f = write_go(tmp_path, "bar_test.go", src)
    violations = lint(f, ebt_boundaries_path=None, source_root=None, stack="go")
    rainsberger = [v for v in violations if v.kind == "rainsberger"]
    assert rainsberger == [], (
        f"httptest.New line should not trigger. Got: {rainsberger}"
    )


def test_go_external_url_triggers_rainsberger(tmp_path: Path) -> None:
    """A real external URL in a Go test (with net/http import) triggers Rainsberger."""
    src = """\
import "net/http"

func TestCallExternal(t *testing.T) {
    resp, _ := http.Get("https://api.example.com/v1/users")
    _ = resp
}
"""
    f = write_go(tmp_path, "external_test.go", src)
    violations = lint(f, ebt_boundaries_path=None, source_root=None, stack="go")
    rainsberger = [v for v in violations if v.kind == "rainsberger"]
    assert len(rainsberger) >= 1


# ---------------------------------------------------------------------------
# TC-12 — TypeScript: vi.mock("axios") triggers Rainsberger
# ---------------------------------------------------------------------------


def test_ts_vi_mock_axios_rainsberger(tmp_path: Path) -> None:
    """vi.mock('axios', ...) in a TS test triggers Rainsberger."""
    src = """\
import { vi, describe, it } from 'vitest';
import axios from 'axios';

vi.mock('axios', () => ({ default: { get: vi.fn() } }));

describe('UserService', () => {
    it('fetches users', async () => {
        const result = await axios.get('/users');
        expect(result).toBeDefined();
    });
});
"""
    f = write_ts(tmp_path, "user.test.ts", src)
    violations = lint(f, ebt_boundaries_path=None, source_root=None, stack="typescript")
    rainsberger = [v for v in violations if v.kind == "rainsberger"]
    assert len(rainsberger) >= 1


# ---------------------------------------------------------------------------
# TC-13 — path | str accepted; LintViolation is frozen
# ---------------------------------------------------------------------------


def test_contract_tag_detected_in_preceding_comment(tmp_path: Path) -> None:
    """[CONTRACT] tag in a # comment before the def triggers Metz on internal patch."""
    src = """\
        from unittest.mock import patch

        # [CONTRACT] Tests the OrderService protocol via collaboration boundary.
        def test_order_service_contract():
            with patch("myapp.orders.OrderRepo") as m:
                m.return_value.save.return_value = None
                assert True
    """
    f = write_py(tmp_path, "test_preceding_comment.py", src)
    violations = lint(f, ebt_boundaries_path=None, source_root=tmp_path)
    metz = [v for v in violations if v.kind == "metz"]
    assert len(metz) == 1, f"Expected 1 Metz; got: {metz}"
    assert "OrderRepo" in metz[0].detail or "myapp" in metz[0].detail


def test_path_str_accepted_and_frozen_dataclass(tmp_path: Path) -> None:
    """lint() accepts str path; LintViolation is immutable (frozen dataclass)."""
    src = """\
        from unittest.mock import patch

        def test_x():
            with patch("requests.post") as m:
                assert True
    """
    f = write_py(tmp_path, "test_str.py", src)
    # Pass as str, not Path
    violations = lint(str(f), ebt_boundaries_path=None, source_root=None)
    assert len(violations) >= 1
    v = violations[0]
    # frozen=True: assigning should raise FrozenInstanceError
    with pytest.raises(Exception):
        v.kind = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# I-07: lint() raises ValueError on unknown stack (was silent return [])
# ---------------------------------------------------------------------------


def test_lint_raises_on_unknown_stack(tmp_path: Path) -> None:
    """Unknown stack values are programming errors — fail loud, not silent.

    Returning [] for an unknown stack hid detection failures: callers
    couldn't distinguish "clean file" from "detection skipped". The
    contract is now: raise `ValueError` so callers see the failure.
    """
    f = write_py(tmp_path, "test_x.py", "def test_x(): pass\n")
    with pytest.raises(ValueError, match="Unknown stack"):
        lint(f, ebt_boundaries_path=None, source_root=None, stack="rust")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# v2.1.0 mock-budget kind (P24-C01) — TDD-2 / REVIEW-1
# ---------------------------------------------------------------------------


def test_tc_review_1_01_kind_enum_includes_mock_budget() -> None:
    """TC-REVIEW-1-01: the violation-kind enum extends with `mock-budget`.

    Inspects the `KindT` Literal at module level. Asserts all three kind
    strings — `rainsberger`, `metz`, `mock-budget` — are accepted values.
    """
    from typing import get_args

    from _ebt_contract_lint import KindT

    kinds = set(get_args(KindT))
    assert "rainsberger" in kinds
    assert "metz" in kinds
    assert "mock-budget" in kinds


def test_tc_tdd_2_02_two_mocks_internal_flagged_important(tmp_path: Path) -> None:
    """TC-TDD-2-02: two mocks (one external + one internal) → second flagged Important.

    The first mock targets `requests.get` (external boundary, on default
    allowlist). The second targets `myproject.internal.SomeClass` (internal).
    The lint must emit a `mock-budget` violation pointing at the internal
    mock, severity Important, and must NOT emit a Pass verdict (i.e. the
    list is non-empty for this test function).
    """
    pyproject(tmp_path)
    src = """\
        from unittest.mock import patch

        def test_two_mocks():
            with patch("requests.get") as m1, \\
                 patch("myproject.internal.SomeClass") as m2:
                m1.return_value.json.return_value = {"id": 1}
                m2.return_value.do_thing.return_value = "ok"
                assert True
    """
    f = write_py(tmp_path, "test_two_mocks.py", src)
    src_root = detect_source_root(f, stack="python")
    violations = lint(f, ebt_boundaries_path=None, source_root=src_root)

    mock_budget = [v for v in violations if v.kind == "mock-budget"]
    assert len(mock_budget) == 1, (
        f"expected exactly one mock-budget violation, got {len(mock_budget)}: "
        f"{[v.detail for v in mock_budget]}"
    )
    v = mock_budget[0]
    assert v.severity == "important"
    assert "myproject.internal.SomeClass" in v.detail


def test_tc_tdd_2_03_single_internal_class_mock_flagged(tmp_path: Path) -> None:
    """TC-TDD-2-03: single mock of an internal class → flagged regardless of count.

    A single `patch("myproject.services.UserService")` must produce a
    `mock-budget` violation. The "count > 1" rule is not a precondition —
    internal-class mocks are over-budget at any count.
    """
    pyproject(tmp_path)
    src = """\
        from unittest.mock import patch

        def test_single_internal():
            with patch("myproject.services.UserService") as svc:
                svc.return_value.lookup.return_value = None
                assert True
    """
    f = write_py(tmp_path, "test_single_internal.py", src)
    src_root = detect_source_root(f, stack="python")
    violations = lint(f, ebt_boundaries_path=None, source_root=src_root)

    mock_budget = [v for v in violations if v.kind == "mock-budget"]
    assert len(mock_budget) == 1
    v = mock_budget[0]
    assert v.severity == "important"
    assert "myproject.services.UserService" in v.detail


def test_tc_tdd_2_04_wrapper_as_sut_no_violation(tmp_path: Path) -> None:
    """TC-TDD-2-04: wrapper-as-SUT exemption — no violation.

    Test for `class HttpxClient` (the wrapper) that mocks `httpx.AsyncClient`
    (the wrapper's external dep). httpx is on the default external-boundary
    allowlist, so the mock is at a true boundary and must NOT be flagged.
    """
    pyproject(tmp_path)
    src = """\
        from unittest.mock import patch

        from myproject.client import HttpxClient

        def test_httpx_client_get():
            with patch("httpx.AsyncClient") as m:
                m.return_value.get.return_value = {"ok": True}
                client = HttpxClient()
                assert client is not None
    """
    f = write_py(tmp_path, "test_httpx_client.py", src)
    src_root = detect_source_root(f, stack="python")
    violations = lint(f, ebt_boundaries_path=None, source_root=src_root)

    mock_budget = [v for v in violations if v.kind == "mock-budget"]
    assert mock_budget == [], (
        f"wrapper-as-SUT mocking external dep on allowlist must not flag; "
        f"got {[v.detail for v in mock_budget]}"
    )


def test_tc_tdd_2_05_seam_allowlist_escalates_to_critical(tmp_path: Path) -> None:
    """TC-TDD-2-05: severity escalates to Critical when target hits seam allowlist.

    A test that mocks `myproject._shared.aggregator.Aggregator` is normally
    Important. When `.cross-chunk-seams` lists `myproject._shared.*`, the
    severity must escalate to Critical — the mock hides a known cross-chunk
    seam (ADR-MH-03).
    """
    pyproject(tmp_path)
    seams = tmp_path / ".cross-chunk-seams"
    seams.write_text("# Known cross-chunk seams\nmyproject._shared.*\n")

    src = """\
        from unittest.mock import patch

        def test_aggregator_consumer():
            with patch("myproject._shared.aggregator.Aggregator") as m:
                m.return_value.aggregate.return_value = []
                assert True
    """
    f = write_py(tmp_path, "test_consumer.py", src)
    src_root = detect_source_root(f, stack="python")
    violations = lint(
        f,
        ebt_boundaries_path=None,
        source_root=src_root,
        seam_allowlist_path=seams,
    )

    mock_budget = [v for v in violations if v.kind == "mock-budget"]
    assert len(mock_budget) == 1, (
        f"expected one mock-budget violation, got {len(mock_budget)}"
    )
    v = mock_budget[0]
    assert v.severity == "critical", (
        f"seam allowlist match must escalate to Critical; got severity={v.severity}"
    )
    assert "myproject._shared.aggregator.Aggregator" in v.detail


def test_wrapper_as_sut_off_allowlist_external_dep_exempt(tmp_path: Path) -> None:
    """Wrapper-as-SUT exemption — actually exercises the heuristic code path.

    TC-TDD-2-04 uses `httpx`, which is on the default allowlist, so the
    `_is_wrapper_as_sut` branch is dead for that test. This test patches
    `redis.Redis`, which is NOT on `_PYTHON_STACK_DEFAULTS`, forcing the
    code to consult the wrapper-as-SUT heuristic. Test file imports
    `RedisClient` (the wrapper SUT) from a project module rooted at
    `myproject` — `redis`'s top segment differs from the SUT's import
    root, so the exemption fires. No violation expected.
    """
    pyproject(tmp_path)
    src = """\
        from unittest.mock import patch

        from myproject.redis_client import RedisClient

        def test_redis_client_get():
            with patch("redis.Redis") as m:
                m.return_value.get.return_value = b"v"
                client = RedisClient()
                assert client is not None
    """
    f = write_py(tmp_path, "test_redis_client.py", src)
    src_root = detect_source_root(f, stack="python")
    violations = lint(f, ebt_boundaries_path=None, source_root=src_root)
    mock_budget = [v for v in violations if v.kind == "mock-budget"]
    assert mock_budget == [], (
        f"wrapper-as-SUT off-allowlist external dep must be exempt; "
        f"got {[v.detail for v in mock_budget]}"
    )


def test_wrapper_as_sut_does_not_exempt_sibling_internal(tmp_path: Path) -> None:
    """Wrapper-as-SUT must NOT exempt mocks that share the SUT's project root.

    Test for `PaymentService` (imported from `myapp.billing`) that patches
    `myapp.internal.AuditLog`. Both share the `myapp` top segment — the
    target is sibling-internal, NOT the wrapper's external dep. The lint
    must flag this as mock-budget Important, not exempt it.

    This is the false-negative the pass-1 review surfaced: an over-broad
    `not top.startswith("_")` check would exempt this case incorrectly.
    """
    pyproject(tmp_path)
    src = """\
        from unittest.mock import patch

        from myapp.billing import PaymentService

        def test_payment_service_charge():
            with patch("myapp.internal.AuditLog") as m:
                m.return_value.record.return_value = None
                svc = PaymentService()
                assert svc is not None
    """
    f = write_py(tmp_path, "test_payment_service.py", src)
    src_root = detect_source_root(f, stack="python")
    violations = lint(f, ebt_boundaries_path=None, source_root=src_root)
    mock_budget = [v for v in violations if v.kind == "mock-budget"]
    assert len(mock_budget) == 1, (
        f"sibling-internal mock sharing SUT's import root must be flagged; "
        f"got {len(mock_budget)} mock-budget violations"
    )
    assert "myapp.internal.AuditLog" in mock_budget[0].detail


def test_contract_test_internal_patch_emits_metz_only_not_mock_budget(tmp_path: Path) -> None:
    """[CONTRACT] tests own internal-patch flagging via metz — no double-emit.

    Metz says "instantiate real production classes from DI root"; mock-budget
    says "mock at boundaries". Both surface for the SAME patch in a [CONTRACT]
    test — emitting both creates conflicting remediation guidance for one line.
    Mock-budget defers to metz on the contract path; it owns NON-contract
    internal mocks.
    """
    pyproject(tmp_path)
    src = """\
        from unittest.mock import patch

        # [CONTRACT] test
        def test_user_service_contract():
            with patch("myapp.services.UserRepo") as repo:
                repo.return_value.find.return_value = None
                assert True
    """
    f = write_py(tmp_path, "test_contract_metz.py", src)
    src_root = detect_source_root(f, stack="python")
    violations = lint(f, ebt_boundaries_path=None, source_root=src_root)
    metz = [v for v in violations if v.kind == "metz"]
    mock_budget = [v for v in violations if v.kind == "mock-budget"]
    assert len(metz) == 1, f"expected one metz violation, got {len(metz)}"
    assert mock_budget == [], (
        f"[CONTRACT] internal patch must not double-emit mock-budget; "
        f"got {[v.detail for v in mock_budget]}"
    )


# ---------------------------------------------------------------------------
# TC-STACK-DEFAULTS — every named TDD-2 external-boundary category is in the
# Python stack defaults (v2.1.1 closure of the TC-TDD-2-02..05 deferral).
#
# SKILL.md TDD-2 names eight categories: requests, httpx, urllib, aiohttp,
# socket, pathlib.Path (real I/O), subprocess, os (env/fs/signal). Mocking
# any of these inside a [CONTRACT] test is boundary-mocking — must NOT
# emit a metz violation. urllib and aiohttp additionally trip rainsberger
# because they are HTTP transport (per _HTTP_TRANSPORT_PACKAGES).
# ---------------------------------------------------------------------------


def _contract_patch_test(target: str) -> str:
    return f"""\
        from unittest.mock import patch

        def test_something():
            \"\"\"[CONTRACT] tests.\"\"\"
            with patch("{target}") as m:
                m.return_value = None
                assert True
    """


def test_stack_defaults_urllib_triggers_rainsberger_not_metz(tmp_path: Path) -> None:
    """urllib is HTTP transport (rainsberger) AND in stack defaults (no metz)."""
    f = write_py(tmp_path, "test_urllib.py", _contract_patch_test("urllib.request.urlopen"))
    violations = lint(f, ebt_boundaries_path=None, source_root=tmp_path)
    kinds = {v.kind for v in violations}
    assert "rainsberger" in kinds
    assert "metz" not in kinds


def test_stack_defaults_aiohttp_triggers_rainsberger_not_metz(tmp_path: Path) -> None:
    """aiohttp is HTTP transport (rainsberger) AND in stack defaults (no metz)."""
    f = write_py(tmp_path, "test_aiohttp.py", _contract_patch_test("aiohttp.ClientSession.get"))
    violations = lint(f, ebt_boundaries_path=None, source_root=tmp_path)
    kinds = {v.kind for v in violations}
    assert "rainsberger" in kinds
    assert "metz" not in kinds


def test_stack_defaults_socket_no_violations(tmp_path: Path) -> None:
    """socket is the raw network boundary — boundary mock emits zero violations.

    R59 I1: assert the full-zero contract (no metz, no mock-budget, no
    rainsberger). A negative-only assertion (`metz not in kinds`) would
    pass vacuously if `_PYTHON_STACK_DEFAULTS` regressed or `_lint_python`
    returned `[]`. Asserting `violations == []` pins the contract that
    Hard Gate 8 / TDD-2 actually claims for boundary mocks.
    """
    f = write_py(tmp_path, "test_socket.py", _contract_patch_test("socket.socket"))
    violations = lint(f, ebt_boundaries_path=None, source_root=tmp_path)
    assert violations == [], (
        f"socket.socket is in stack defaults — boundary mock must emit "
        f"zero violations, got {[v.kind for v in violations]}"
    )


def test_stack_defaults_pathlib_path_no_violations(tmp_path: Path) -> None:
    """pathlib.Path real-I/O is the filesystem boundary — zero violations."""
    f = write_py(tmp_path, "test_pathlib.py", _contract_patch_test("pathlib.Path.read_text"))
    violations = lint(f, ebt_boundaries_path=None, source_root=tmp_path)
    assert violations == [], (
        f"pathlib.Path.read_text is in stack defaults — boundary mock "
        f"must emit zero violations, got {[v.kind for v in violations]}"
    )


def test_stack_defaults_subprocess_no_violations(tmp_path: Path) -> None:
    """subprocess is the process-spawn boundary — zero violations."""
    f = write_py(tmp_path, "test_subprocess.py", _contract_patch_test("subprocess.run"))
    violations = lint(f, ebt_boundaries_path=None, source_root=tmp_path)
    assert violations == [], (
        f"subprocess.run is in stack defaults — boundary mock must emit "
        f"zero violations, got {[v.kind for v in violations]}"
    )


def test_stack_defaults_os_no_violations(tmp_path: Path) -> None:
    """os.environ / os.path real-I/O / os.signal are external boundaries — zero violations."""
    f = write_py(tmp_path, "test_os.py", _contract_patch_test("os.environ"))
    violations = lint(f, ebt_boundaries_path=None, source_root=tmp_path)
    assert violations == [], (
        f"os.environ is in stack defaults — boundary mock must emit "
        f"zero violations, got {[v.kind for v in violations]}"
    )


# ---------------------------------------------------------------------------
# v2.2.0 P29-C01 — TypeScript mock-budget detector
# ---------------------------------------------------------------------------
#
# TC-TDD-2-12 .. TC-TDD-2-16 cover the TS mock-budget detector wiring per
# spec methodology-hardening-ts-go-mockbudget § ADR-TG-01 / ADR-TG-03.
#
# - 12: axios-only boundary mock → 0 mock-budget violations
# - 13: axios + internal UserService → 1 Important on UserService (acceptance)
# - 14: seam_allowlist matches internal target → escalates to Critical
# - 15: jest.spyOn(realService, "method") on internal target → 1 Important
#       (realistic-fixture variant — TDD-3, exercises a different mock pattern
#        from the synthetic vi.mock-only happy paths)
# - 16: wrapper-as-SUT — file under test is axiosWrapper.ts, mocks axios → 0


def test_tc_tdd_2_13_ts_internal_mock_emits_mock_budget(tmp_path: Path) -> None:
    """vi.mock of internal service alongside axios → 1 Important mock-budget."""
    src = """\
import { vi, it } from "vitest";
vi.mock("axios");
vi.mock("../UserService");
it("does work", () => { /* ... */ });
"""
    f = write_ts(tmp_path, "user.test.ts", src)
    violations = lint(f, ebt_boundaries_path=None, source_root=tmp_path, stack="typescript")
    mb = [v for v in violations if v.kind == "mock-budget"]
    assert len(mb) == 1, f"expected 1 mock-budget violation, got {[v.kind for v in violations]}"
    assert mb[0].severity == "important"
    assert "UserService" in mb[0].detail


def test_tc_tdd_2_12_ts_axios_only_no_mock_budget(tmp_path: Path) -> None:
    """vi.mock('axios') alone → 0 mock-budget violations (axios is on allowlist)."""
    src = """\
import { vi, it } from "vitest";
vi.mock("axios");
it("works", () => {});
"""
    f = write_ts(tmp_path, "axios_only.test.ts", src)
    violations = lint(f, ebt_boundaries_path=None, source_root=tmp_path, stack="typescript")
    mb = [v for v in violations if v.kind == "mock-budget"]
    assert mb == [], f"axios is on allowlist; expected 0 mock-budget, got {mb}"


def test_tc_tdd_2_14_ts_seam_allowlist_escalates_to_critical(tmp_path: Path) -> None:
    """When internal target matches .cross-chunk-seams pattern → Critical."""
    src = """\
import { vi, it } from "vitest";
vi.mock("../UserService");
it("works", () => {});
"""
    f = write_ts(tmp_path, "u.test.ts", src)
    seams = tmp_path / ".cross-chunk-seams"
    seams.write_text("../UserService*\n")
    violations = lint(
        f,
        ebt_boundaries_path=None,
        source_root=tmp_path,
        stack="typescript",
        seam_allowlist_path=seams,
    )
    mb = [v for v in violations if v.kind == "mock-budget"]
    assert len(mb) == 1
    assert mb[0].severity == "critical", (
        f"seam-allowlist match must escalate to critical, got {mb[0].severity}"
    )


def test_tc_tdd_2_15_ts_spyon_realistic_fixture_internal_target(tmp_path: Path) -> None:
    """TDD-3 realistic-fixture variant: jest.spyOn pattern on an internal service.

    The synthetic happy-path tests above use vi.mock("...") string-literal
    target. Real codebases mix idioms — jest.spyOn(obj, "method") is the
    second most common pattern. This variant exercises the realistic shape
    a domain-team test file would carry, per TDD-3 catalogue (web/UI).
    """
    src = """\
import { jest, it } from "@jest/globals";
import * as userService from "../UserService";
jest.spyOn(userService, "getUser");
it("works", () => {});
"""
    f = write_ts(tmp_path, "spy.test.ts", src)
    violations = lint(f, ebt_boundaries_path=None, source_root=tmp_path, stack="typescript")
    mb = [v for v in violations if v.kind == "mock-budget"]
    assert len(mb) == 1, f"expected 1 mock-budget on userService, got {[v.detail for v in violations]}"
    assert mb[0].severity == "important"
    assert "userService" in mb[0].detail, (
        f"jest.spyOn captured target must surface in detail, got {mb[0].detail!r}"
    )


def test_tc_tdd_2_16_ts_wrapper_as_sut_no_violation(tmp_path: Path) -> None:
    """ADR-MH-02 parity: when test-file stem equals the mocked target's
    basename, the file is the wrapper SUT and the mock is exempt.

    Uses a non-allowlisted target (`./axiosWrapper`) that shares the
    test-file stem (`axiosWrapper`). Only the wrapper-as-SUT exemption
    can produce 0 violations — an allowlist match cannot, since the
    target is not in `_TS_STACK_DEFAULTS`. This pins the ADR-MH-02
    code path; a regression deleting `_ts_target_basename` /
    `_ts_sut_stem` would surface as a violation count > 0.
    """
    src = """\
import { vi, it } from "vitest";
vi.mock("./axiosWrapper");
it("wraps axiosWrapper", () => {});
"""
    f = write_ts(tmp_path, "axiosWrapper.test.ts", src)
    violations = lint(f, ebt_boundaries_path=None, source_root=tmp_path, stack="typescript")
    mb = [v for v in violations if v.kind == "mock-budget"]
    assert mb == [], f"wrapper-as-SUT must exempt ./axiosWrapper mock, got {mb}"


def test_ts_stack_defaults_includes_canonical_boundaries() -> None:
    """ADR-TG-01: every documented allowlist entry is present in the constant."""
    from _ebt_contract_lint import _TS_STACK_DEFAULTS  # type: ignore[attr-defined]

    expected = {
        "node:fs.*", "node:path.*", "node:child_process.*", "node:os.*",
        "node:net.*", "node:http.*", "node:https.*", "node:dns.*",
        "node:crypto.*", "node:stream.*",
        "axios.*", "node-fetch.*", "undici.*", "got.*", "ky.*",
        "pg.*", "mysql2.*", "mongodb.*", "mongoose.*", "redis.*", "ioredis.*",
        "sqlite3.*", "aws-sdk.*", "@aws-sdk/*.*", "googleapis.*", "stripe.*",
        "@anthropic-ai/sdk.*", "openai.*",
    }
    missing = expected - set(_TS_STACK_DEFAULTS)
    assert not missing, f"_TS_STACK_DEFAULTS missing canonical entries: {missing}"


# ---------------------------------------------------------------------------
# v2.2.0 P29-C02 — Go mock-budget detector
# ---------------------------------------------------------------------------
#
# TC-TDD-2-17 .. TC-TDD-2-21 cover the Go mock-budget detector wiring per
# ADR-TG-02. Go idiom: count distinct test-double instances per Test func.


def test_tc_tdd_2_18_go_internal_fake_emits_mock_budget(tmp_path: Path) -> None:
    """Boundary mock + internal fake → only the internal flagged.

    `httpClientMock` is added to .ebt-boundaries (project's HTTP boundary
    fake); `userRepoFake` is internal — the rule flags only the latter.
    """
    src = """\
package mypkg
import "testing"
type httpClientMock struct{}
type userRepoFake struct{}
func TestService(t *testing.T) {
    client := &httpClientMock{}
    repo := &userRepoFake{}
    _ = client; _ = repo
}
"""
    f = write_go(tmp_path, "service_test.go", src)
    boundaries = tmp_path / ".ebt-boundaries"
    boundaries.write_text("httpClient*\n")
    violations = lint(
        f, ebt_boundaries_path=boundaries, source_root=tmp_path, stack="go"
    )
    mb = [v for v in violations if v.kind == "mock-budget"]
    assert len(mb) == 1, f"expected 1 mock-budget on userRepoFake, got {[v.detail for v in violations]}"
    assert mb[0].severity == "important"
    assert "userRepoFake" in mb[0].detail


def test_tc_tdd_2_17_go_single_boundary_fake_no_violation(tmp_path: Path) -> None:
    """One *Mock at the http.Client boundary → 0 mock-budget violations."""
    src = """\
package mypkg
import (
    "testing"
    "net/http"
)
type httpClientMock struct{}
func (h *httpClientMock) Do(*http.Request) (*http.Response, error) { return nil, nil }
func TestService(t *testing.T) {
    c := &httpClientMock{}
    _ = c
}
"""
    f = write_go(tmp_path, "boundary_test.go", src)
    boundaries = tmp_path / ".ebt-boundaries"
    boundaries.write_text("httpClient*\n")
    violations = lint(
        f, ebt_boundaries_path=boundaries, source_root=tmp_path, stack="go"
    )
    mb = [v for v in violations if v.kind == "mock-budget"]
    assert mb == [], f"boundary fake (allowlisted) must emit 0, got {mb}"


def test_tc_tdd_2_19_go_seam_allowlist_escalates_to_critical(tmp_path: Path) -> None:
    """Internal target matching .cross-chunk-seams → Critical."""
    src = """\
package mypkg
import "testing"
type userRepoFake struct{}
func TestService(t *testing.T) {
    r := &userRepoFake{}
    _ = r
}
"""
    f = write_go(tmp_path, "x_test.go", src)
    seams = tmp_path / ".cross-chunk-seams"
    seams.write_text("userRepo*\n")
    violations = lint(
        f,
        ebt_boundaries_path=None,
        source_root=tmp_path,
        stack="go",
        seam_allowlist_path=seams,
    )
    mb = [v for v in violations if v.kind == "mock-budget"]
    assert len(mb) == 1
    assert mb[0].severity == "critical", (
        f"seam-allowlist match must escalate to critical, got {mb[0].severity}"
    )


def test_tc_tdd_2_20_go_gomock_controller_counts_as_double(tmp_path: Path) -> None:
    """gomock.NewController + internal struct fake → 2 mock-budget violations.

    Each gomock controller counts as one mocked collaborator (ADR-TG-02);
    the internal struct fake is a second one. Both surface as Important.
    """
    src = """\
package mypkg
import (
    "testing"
    "github.com/golang/mock/gomock"
)
type userRepoFake struct{}
func TestService(t *testing.T) {
    ctrl := gomock.NewController(t)
    defer ctrl.Finish()
    repo := &userRepoFake{}
    _ = repo
}
"""
    f = write_go(tmp_path, "g_test.go", src)
    violations = lint(f, ebt_boundaries_path=None, source_root=tmp_path, stack="go")
    mb = [v for v in violations if v.kind == "mock-budget"]
    assert len(mb) == 2, f"gomock controller + struct fake → 2 doubles, got {[v.detail for v in mb]}"
    details = " | ".join(v.detail for v in mb)
    assert "gomock" in details, f"gomock controller must emit a violation, got {details}"
    assert "userRepoFake" in details, f"userRepoFake must emit a violation, got {details}"


def test_tc_tdd_2_21_go_testify_mock_embed_counts_as_double(tmp_path: Path) -> None:
    """ADR-TG-02: testify mock.Mock embed detected by library API, NOT by
    naming convention. Type name carries no Mock|Fake|Stub|Spy suffix —
    only the testify-embed branch (`_collect_testify_types`) can catch it.
    A regression in that branch would flip violations to 0.
    """
    src = """\
package mypkg
import (
    "testing"
    "github.com/stretchr/testify/mock"
)
type userRepository struct {
    mock.Mock
}
func TestService(t *testing.T) {
    r := &userRepository{}
    _ = r
}
"""
    f = write_go(tmp_path, "t_test.go", src)
    violations = lint(f, ebt_boundaries_path=None, source_root=tmp_path, stack="go")
    mb = [v for v in violations if v.kind == "mock-budget"]
    assert len(mb) == 1, (
        f"testify embed must emit when name lacks Mock|Fake|Stub|Spy suffix, "
        f"got {[v.detail for v in mb]}"
    )
    assert "userRepository" in mb[0].detail
    assert "testify mock.Mock embed" in mb[0].detail, (
        f"detail must identify the testify-embed branch (not the naming arm), "
        f"got {mb[0].detail!r}"
    )


def test_go_stack_defaults_includes_canonical_boundaries() -> None:
    """ADR-TG-02: canonical Go boundary categories present in the constant."""
    from _ebt_contract_lint import _GO_STACK_DEFAULTS  # type: ignore[attr-defined]

    expected = {
        "net/http.*", "net/url.*", "os.*", "os/exec.*", "io.*", "io/fs.*",
        "database/sql.*", "database/sql/driver.*", "context.*",
    }
    missing = expected - set(_GO_STACK_DEFAULTS)
    assert not missing, f"_GO_STACK_DEFAULTS missing canonical entries: {missing}"
