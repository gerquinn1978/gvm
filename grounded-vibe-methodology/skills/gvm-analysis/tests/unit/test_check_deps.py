"""Tests for ``scripts/_check_deps.py`` (ADR-106 / P5-C02).

Covers:
- Helper functions in-process (check_package, format_install_command,
  format_missing_diagnostic, verify_pymannkendall_schema)
- Python-version-too-old branch via injected sys.version_info tuple
- Missing-dep diagnostic format (ERROR / What / What to try)
- Subprocess happy path — the real env has every REQUIRED installed
- Subprocess packaging-bootstrap failure via sabotaged PYTHONPATH
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections import namedtuple
from pathlib import Path
from typing import Generator

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "_check_deps.py"


@pytest.fixture(autouse=True)
def _script_on_syspath() -> Generator[None, None, None]:
    scripts = str(SCRIPT_PATH.parent)
    added = scripts not in sys.path
    if added:
        sys.path.insert(0, scripts)
    try:
        yield
    finally:
        if added and scripts in sys.path:
            sys.path.remove(scripts)


# ---------------------------------------------------------------------------
# Helper tests (in-process)
# ---------------------------------------------------------------------------


def test_required_list_is_nonempty_and_pairs() -> None:
    import _check_deps

    assert _check_deps.REQUIRED, "REQUIRED list must not be empty"
    for entry in _check_deps.REQUIRED:
        assert isinstance(entry, tuple) and len(entry) == 2
        name, min_ver = entry
        assert isinstance(name, str) and name
        assert isinstance(min_ver, str) and min_ver


def test_required_includes_core_analysis_packages() -> None:
    # ADR-106: these are the engine-critical deps the spec names explicitly.
    import _check_deps

    names = {name for name, _ in _check_deps.REQUIRED}
    for expected in {
        "pandas",
        "numpy",
        "scipy",
        "scikit-learn",
        "statsmodels",
        "pymannkendall",
        "openpyxl",
        "pyarrow",
        "packaging",
        "rapidfuzz",
    }:
        assert expected in names, f"{expected} missing from REQUIRED"


def test_optional_list_is_advisory_only() -> None:
    import _check_deps

    names = {name for name, _ in _check_deps.OPTIONAL}
    for expected in {"pmdarima", "shap", "lttbc"}:
        assert expected in names


def test_format_install_command_uses_quoted_specifiers() -> None:
    import _check_deps

    cmd = _check_deps.format_install_command([("pandas", "2.0"), ("numpy", "1.24")])
    assert cmd.startswith("pip install ")
    assert "'pandas>=2.0'" in cmd
    assert "'numpy>=1.24'" in cmd


def test_format_install_command_is_derived_not_hardcoded() -> None:
    # DRY: change to REQUIRED must propagate to the INSTALL line with no
    # hand-typed edit. Feed a single-entry list and confirm the cmd reflects it.
    import _check_deps

    cmd = _check_deps.format_install_command([("foo", "9.9")])
    assert cmd == "pip install 'foo>=9.9'"


def test_check_package_returns_none_when_present_and_current(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import _check_deps

    monkeypatch.setattr(_check_deps.md, "version", lambda name: "99.0.0")
    assert _check_deps.check_package("pandas", "2.0") is None


def test_check_package_flags_missing_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import _check_deps

    def _raise(_name: str) -> str:
        raise _check_deps.md.PackageNotFoundError("boom")

    monkeypatch.setattr(_check_deps.md, "version", _raise)
    result = _check_deps.check_package("pandas", "2.0")
    assert result is not None
    assert result == ("pandas", "2.0", None)


def test_check_package_flags_below_version_floor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import _check_deps

    monkeypatch.setattr(_check_deps.md, "version", lambda name: "1.0.0")
    result = _check_deps.check_package("pandas", "2.0")
    assert result == ("pandas", "2.0", "1.0.0")


def test_format_missing_diagnostic_follows_error_what_whattotry() -> None:
    import _check_deps

    text = _check_deps.format_missing_diagnostic(
        missing=[("pandas", "2.0", None), ("scipy", "1.10", "0.19.0")],
        required=[("pandas", "2.0"), ("scipy", "1.10"), ("numpy", "1.24")],
    )
    assert "ERROR:" in text
    assert "What went wrong" in text
    assert "What to try" in text
    assert "pandas" in text
    assert "scipy" in text
    assert "pip install" in text
    # INSTALL line is derived from the full REQUIRED list, not just missing.
    assert "'numpy>=1.24'" in text


def test_check_python_version_allows_modern_interpreter() -> None:
    import _check_deps

    # Must not raise or exit on a supported interpreter tuple.
    _check_deps.check_python_version(sys_version_info=(3, 12, 0))


def test_check_python_version_rejects_too_old(
    capsys: pytest.CaptureFixture[str],
) -> None:
    import _check_deps

    with pytest.raises(SystemExit) as excinfo:
        _check_deps.check_python_version(sys_version_info=(3, 8, 10))
    assert excinfo.value.code == 1
    err = capsys.readouterr().err
    assert "ERROR" in err
    assert "3.8" in err or "3.9" in err  # names either the have or the need


def test_verify_pymannkendall_schema_accepts_expected_fields() -> None:
    import _check_deps

    Row = namedtuple(
        "MK",
        "trend h p z Tau s var_s slope intercept",
    )

    def fake_test(_series: list[int]) -> object:
        return Row(
            trend="increasing",
            h=True,
            p=0.01,
            z=2.5,
            Tau=0.8,
            s=20,
            var_s=5.0,
            slope=0.3,
            intercept=0.1,
        )

    # Should not raise.
    _check_deps.verify_pymannkendall_schema(probe=fake_test)


def test_verify_pymannkendall_schema_rejects_missing_field() -> None:
    import _check_deps

    Row = namedtuple("MK", "trend h p")  # missing z, Tau, slope, ...

    def fake_test(_series: list[int]) -> object:
        return Row(trend="increasing", h=True, p=0.01)

    with pytest.raises(_check_deps.DependencyError) as excinfo:
        _check_deps.verify_pymannkendall_schema(probe=fake_test)
    assert excinfo.value.package == "pymannkendall"
    assert excinfo.value.reason == "api mismatch"


# ---------------------------------------------------------------------------
# Subprocess integration tests
# ---------------------------------------------------------------------------


def _run_script(env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env is not None:
        merged_env.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        capture_output=True,
        text=True,
        env=merged_env,
    )


def test_subprocess_happy_path_exits_zero_in_dev_env() -> None:
    # All REQUIRED deps are installed in the dev env — the script must pass.
    result = _run_script()
    assert result.returncode == 0, (
        f"expected exit 0 with full deps installed, got {result.returncode}; "
        f"stderr={result.stderr!r}"
    )


def test_subprocess_bootstrap_guard_fires_without_packaging() -> None:
    # Point PYTHONPATH at a dir that contains a stub `packaging` package
    # that raises ImportError on `from packaging.version import parse`.
    import tempfile
    import textwrap

    with tempfile.TemporaryDirectory() as td:
        stub = Path(td) / "packaging"
        stub.mkdir()
        (stub / "__init__.py").write_text("")
        (stub / "version.py").write_text(
            textwrap.dedent(
                """
                raise ImportError("sabotaged: packaging.version shim")
                """
            )
        )
        # Put the stub dir at the front of PYTHONPATH so the real packaging
        # (installed in site-packages) is shadowed for the child.
        result = _run_script(env={"PYTHONPATH": td})

    assert result.returncode == 1
    assert "packaging" in result.stderr
    assert "ERROR" in result.stderr
    # Must use the standard ERROR / What / What to try format even when the
    # check-script itself cannot run its own version comparison.
    assert "What went wrong" in result.stderr
    assert "What to try" in result.stderr


def test_format_install_command_covers_full_required_list() -> None:
    # DRY: the helper consumes REQUIRED directly, so every name must land in
    # the emitted command. Pure in-process test — does not exercise main().
    import _check_deps

    cmd = _check_deps.format_install_command(_check_deps.REQUIRED)
    for name, _ in _check_deps.REQUIRED:
        assert f"'{name}>=" in cmd, f"{name} missing from INSTALL line"


def test_format_missing_diagnostic_emits_install_labelled_line() -> None:
    # ADR-106 / skill-orchestration.md:448: Claude passes the INSTALL: line
    # through verbatim. Without the label automation cannot extract the
    # command — regression-guard the label itself.
    import _check_deps

    text = _check_deps.format_missing_diagnostic(
        missing=[("pandas", "2.0", None)],
        required=[("pandas", "2.0"), ("numpy", "1.24")],
    )
    install_lines = [line for line in text.splitlines() if line.startswith("INSTALL:")]
    assert len(install_lines) == 1, (
        f"exactly one INSTALL: labelled line required; got {install_lines}"
    )
    assert "pip install" in install_lines[0]
    assert "'pandas>=2.0'" in install_lines[0]
    assert "'numpy>=1.24'" in install_lines[0]


def test_verify_pymannkendall_schema_rejects_non_namedtuple_result() -> None:
    # Non-NamedTuple returns (e.g., a future refactor to a dataclass or dict)
    # must produce a specific "result is not a NamedTuple" diagnostic, not a
    # misleading "all fields missing" one.
    import _check_deps

    def fake_test_returns_dict(_series: list[int]) -> dict:
        return {"trend": "up", "h": True, "p": 0.01}

    with pytest.raises(_check_deps.DependencyError) as excinfo:
        _check_deps.verify_pymannkendall_schema(probe=fake_test_returns_dict)
    assert excinfo.value.reason == "api mismatch"
    assert excinfo.value.found is not None
    assert "_fields" in excinfo.value.found


def test_subprocess_missing_required_dep_emits_install_line(
    tmp_path: Path,
) -> None:
    # Real end-to-end: sabotage one REQUIRED package via a PYTHONPATH shim
    # that shadows it with a broken module. Confirms the failure path emits
    # an INSTALL: line that lists every REQUIRED name.
    import textwrap

    # Shadow `rapidfuzz` (chosen because it's imported only lazily by the
    # engine, and the dep-check uses importlib.metadata which queries the
    # installed distribution — not the import system — so shadowing it
    # doesn't actually hide it from md.version). Since md.version reads
    # installed metadata, not sys.path, a simpler approach is to create a
    # shim that monkeypatches importlib.metadata.version for the missing pkg.
    #
    # Instead: run the script via -c with a monkeypatch preamble.
    preamble = textwrap.dedent(
        f"""
        import sys, importlib.metadata as md
        _real_version = md.version
        def fake_version(name):
            if name == "rapidfuzz":
                raise md.PackageNotFoundError(name)
            return _real_version(name)
        md.version = fake_version
        sys.argv = [{str(SCRIPT_PATH)!r}]
        with open({str(SCRIPT_PATH)!r}) as f:
            code = f.read()
        exec(compile(code, {str(SCRIPT_PATH)!r}, "exec"), {{"__name__": "__main__"}})
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", preamble],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "ERROR:" in result.stderr
    assert "rapidfuzz" in result.stderr
    install_lines = [
        line for line in result.stderr.splitlines() if line.startswith("INSTALL:")
    ]
    assert len(install_lines) == 1, result.stderr
    # INSTALL line must cover the full REQUIRED list, not just the missing one.
    assert "'pandas>=2.0'" in install_lines[0]
    assert "'rapidfuzz>=3.0'" in install_lines[0]
