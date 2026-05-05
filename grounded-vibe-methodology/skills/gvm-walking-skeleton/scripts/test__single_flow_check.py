"""P11-C03 unit tests for `_single_flow_check.py`.

Spec ref: walking-skeleton ADR-405 (single-flow constraint enforced via
chunk-count budget).

Test cases: TC-WS-4-01 (lint passes one flow), TC-WS-4-02 (lint rejects
the second flow).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from _single_flow_check import OvercountError, lint


# ----------------------------------------------------------------- helpers


def _write(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


# ----------------------------------------------------------------- python


def test_empty_file_returns_empty_list(tmp_path: Path) -> None:
    p = _write(tmp_path, "test_skeleton.py", "")
    assert lint(p, language="python") == []


def test_single_test_function_passes(tmp_path: Path) -> None:
    p = _write(tmp_path, "test_skeleton.py", "def test_one():\n    assert True\n")
    assert lint(p, language="python") == []


def test_three_test_functions_pass_at_max(tmp_path: Path) -> None:
    body = (
        "def test_a():\n    assert True\n"
        "def test_b():\n    assert True\n"
        "def test_c():\n    assert True\n"
    )
    p = _write(tmp_path, "test_skeleton.py", body)
    assert lint(p, language="python") == []


def test_four_test_functions_fail(tmp_path: Path) -> None:
    body = (
        "def test_a():\n    pass\n"
        "def test_b():\n    pass\n"
        "def test_c():\n    pass\n"
        "def test_d():\n    pass\n"
    )
    p = _write(tmp_path, "test_skeleton.py", body)
    errors = lint(p, language="python")
    assert len(errors) == 1
    err = errors[0]
    assert isinstance(err, OvercountError)
    assert err.count == 4
    assert err.max_tests == 3
    assert err.file == p
    assert len(err.matched_lines) == 4


def test_async_test_counted(tmp_path: Path) -> None:
    body = (
        "async def test_a():\n    pass\n"
        "async def test_b():\n    pass\n"
        "async def test_c():\n    pass\n"
        "async def test_d():\n    pass\n"
    )
    p = _write(tmp_path, "test_skeleton.py", body)
    errors = lint(p, language="python")
    assert errors and errors[0].count == 4


def test_helpers_not_counted(tmp_path: Path) -> None:
    body = (
        "def test_a():\n    pass\n"
        "def helper():\n    pass\n"
        "def test_b():\n    pass\n"
        "def _internal():\n    pass\n"
    )
    p = _write(tmp_path, "test_skeleton.py", body)
    assert lint(p, language="python") == []


def test_custom_max_tests_one(tmp_path: Path) -> None:
    body = "def test_a():\n    pass\ndef test_b():\n    pass\n"
    p = _write(tmp_path, "test_skeleton.py", body)
    errors = lint(p, language="python", max_tests=1)
    assert len(errors) == 1
    assert errors[0].count == 2
    assert errors[0].max_tests == 1


def test_matched_line_numbers_are_one_based(tmp_path: Path) -> None:
    body = "# comment\ndef test_a():\n    pass\ndef test_b():\n    pass\ndef test_c():\n    pass\ndef test_d():\n    pass\n"
    p = _write(tmp_path, "test_skeleton.py", body)
    errors = lint(p, language="python")
    assert errors[0].matched_lines == (2, 4, 6, 8)


def test_indented_def_not_counted(tmp_path: Path) -> None:
    # nested defs (e.g. inside fixtures) aren't pytest test functions.
    body = (
        "def test_a():\n"
        "    def test_inner():\n"
        "        return 1\n"
        "    assert test_inner() == 1\n"
    )
    p = _write(tmp_path, "test_skeleton.py", body)
    assert lint(p, language="python") == []


# ----------------------------------------------------------------- typescript


def test_typescript_under_max(tmp_path: Path) -> None:
    body = (
        "test('one', () => { expect(1).toBe(1) })\n"
        "test('two', () => { expect(2).toBe(2) })\n"
    )
    p = _write(tmp_path, "test_skeleton.ts", body)
    assert lint(p, language="typescript") == []


def test_typescript_backtick_quoted_test_counted(tmp_path: Path) -> None:
    body = (
        "test(`a`, () => {})\n"
        "test(`b`, () => {})\n"
        "it(`c`, () => {})\n"
        "it(`d`, () => {})\n"
    )
    p = _write(tmp_path, "test_skeleton.ts", body)
    errors = lint(p, language="typescript")
    assert len(errors) == 1
    assert errors[0].count == 4


def test_typescript_over_max(tmp_path: Path) -> None:
    body = (
        "test('a', () => {})\n"
        'test("b", () => {})\n'
        "it('c', () => {})\n"
        'it("d", () => {})\n'
    )
    p = _write(tmp_path, "test_skeleton.ts", body)
    errors = lint(p, language="typescript")
    assert len(errors) == 1
    assert errors[0].count == 4


# ----------------------------------------------------------------- go


def test_go_under_max(tmp_path: Path) -> None:
    body = "func TestA(t *testing.T) {}\nfunc TestB(t *testing.T) {}\n"
    p = _write(tmp_path, "skeleton_test.go", body)
    assert lint(p, language="go") == []


def test_go_over_max(tmp_path: Path) -> None:
    body = (
        "func TestA(t *testing.T) {}\n"
        "func TestB(t *testing.T) {}\n"
        "func TestC(t *testing.T) {}\n"
        "func TestD(t *testing.T) {}\n"
    )
    p = _write(tmp_path, "skeleton_test.go", body)
    errors = lint(p, language="go")
    assert len(errors) == 1
    assert errors[0].count == 4


def test_go_helper_not_counted(tmp_path: Path) -> None:
    body = "func helper() {}\nfunc TestA(t *testing.T) {}\n"
    p = _write(tmp_path, "skeleton_test.go", body)
    assert lint(p, language="go") == []


# ----------------------------------------------------------------- error paths


def test_unknown_language_raises(tmp_path: Path) -> None:
    p = _write(tmp_path, "x.rb", "")
    with pytest.raises(ValueError, match="ruby"):
        lint(p, language="ruby")


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        lint(tmp_path / "nope.py", language="python")


def test_overcount_error_is_frozen(tmp_path: Path) -> None:
    p = _write(tmp_path, "test_skeleton.py", "def test_a():\n    pass\n")
    err = OvercountError(file=p, count=4, max_tests=3, matched_lines=(1, 2, 3, 4))
    with pytest.raises(Exception):
        err.count = 99  # type: ignore[misc]
