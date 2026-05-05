"""Dependency check for /gvm-analysis (ADR-106 / P5-C02).

Runs before any analysis work. Verifies:
  1. Python interpreter is new enough (NFR-5: ≥3.9).
  2. The ``packaging`` library is importable (bootstrap guard — without it the
     rest of this script cannot compare versions).
  3. Every REQUIRED package is installed at or above its minimum version.
  4. The ``pymannkendall`` NamedTuple schema matches what the engine depends on
     (analysis-engine.md HIGH-T40).
  5. Optional packages are reported advisorily; their absence does not block.

Exit codes:
  0 — all REQUIRED present (advisory may still print for OPTIONAL gaps).
  1 — any blocking failure (old Python / missing packaging / missing REQUIRED
      / pymannkendall schema mismatch). stderr carries the
      ERROR / What went wrong / What to try diagnostic.

The REQUIRED list is the single source for the INSTALL command emitted on
failure (ADR-106 post-R2 fix I-2: drift-proof).
"""

from __future__ import annotations

import importlib.metadata as md
import sys
from typing import Callable

# ---------------------------------------------------------------------------
# Bootstrap guard — must run before any packaging.* import in the module body.
# ---------------------------------------------------------------------------
try:
    from packaging.version import parse as parse_version
except ImportError:
    sys.stderr.write("ERROR: required package 'packaging' is not installed.\n")
    sys.stderr.write(
        "What went wrong: _check_deps.py needs the 'packaging' library to "
        "compare installed versions against minimum floors.\n"
    )
    sys.stderr.write("What to try: pip install 'packaging>=21.0'\n")
    sys.exit(1)

# Late import — _shared.diagnostics lives next to this script (via pyproject
# package config). Fall back to a minimal local class if the shared module is
# unavailable (e.g., partial install). The script must never crash with an
# ImportError before emitting a diagnostic.
try:
    from _shared.diagnostics import DependencyError
except ImportError:  # pragma: no cover — defensive path

    class DependencyError(Exception):  # type: ignore[no-redef]
        def __init__(
            self,
            package: str,
            reason: str,
            *,
            required: str | None = None,
            found: str | None = None,
        ) -> None:
            self.package = package
            self.reason = reason
            self.required = required
            self.found = found
            super().__init__(f"dependency error: {package} ({reason})")


REQUIRED: list[tuple[str, str]] = [
    ("pandas", "2.0"),
    ("numpy", "1.24"),
    ("scipy", "1.10"),
    ("scikit-learn", "1.3"),
    ("statsmodels", "0.14"),
    ("jinja2", "3.1"),
    ("pyyaml", "6.0"),
    ("matplotlib", "3.7"),
    ("pymannkendall", "1.4"),
    ("openpyxl", "3.1"),
    ("pyarrow", "14.0"),
    ("squarify", "0.4"),
    ("packaging", "21.0"),
    ("rapidfuzz", "3.0"),
]

OPTIONAL: list[tuple[str, str]] = [
    ("pmdarima", "2.0"),
    ("shap", "0.44"),
    ("lttbc", "0.2"),
]

MIN_PYTHON: tuple[int, int] = (3, 9)

PYMANNKENDALL_EXPECTED_FIELDS: frozenset[str] = frozenset(
    {"trend", "h", "p", "z", "Tau", "s", "var_s", "slope", "intercept"}
)


def check_python_version(
    sys_version_info: tuple[int, int, int] | None = None,
) -> None:
    """Abort with exit code 1 if the interpreter is older than MIN_PYTHON.

    ``sys_version_info`` is an optional injection point for tests — in
    production the real ``sys.version_info`` is used.
    """
    if sys_version_info is None:
        v = sys.version_info
        version_tuple: tuple[int, int, int] = (v.major, v.minor, v.micro)
    else:
        version_tuple = sys_version_info

    if version_tuple[:2] < MIN_PYTHON:
        have = ".".join(str(part) for part in version_tuple)
        need = ".".join(str(part) for part in MIN_PYTHON)
        sys.stderr.write(f"ERROR: requires Python {need} or later (have {have}).\n")
        sys.stderr.write(
            "What went wrong: the /gvm-analysis engine depends on language "
            f"features introduced in Python {need}.\n"
        )
        sys.stderr.write(
            f"What to try: install Python {need} or newer, then re-run the "
            "skill with `python3` pointing at the newer interpreter.\n"
        )
        sys.exit(1)


def check_package(name: str, min_ver: str) -> tuple[str, str, str | None] | None:
    """Return None if the package is installed at/above ``min_ver``.

    On failure returns ``(name, min_ver, installed_or_None)`` where
    ``installed_or_None`` is ``None`` for a missing package and a version
    string for a below-floor package.
    """
    try:
        installed = md.version(name)
    except md.PackageNotFoundError:
        return (name, min_ver, None)
    if parse_version(installed) >= parse_version(min_ver):
        return None
    return (name, min_ver, installed)


def format_install_command(required: list[tuple[str, str]]) -> str:
    """Return ``pip install '<pkg>>=<ver>' ...`` for every entry.

    Derived from the input list — never hand-typed, so there is no drift
    between what was checked and what the diagnostic recommends installing.
    """
    specs = " ".join(f"'{name}>={ver}'" for name, ver in required)
    return f"pip install {specs}"


def format_missing_diagnostic(
    missing: list[tuple[str, str, str | None]],
    required: list[tuple[str, str]],
) -> str:
    """Assemble the ERROR / What went wrong / What to try block for a
    missing-dep failure.

    Also emits an `INSTALL:` labelled line carrying the full pip command
    (ADR-106 post-R2 fix I-2). SKILL.md / skill-orchestration.md both
    promise Claude will pass the `INSTALL:` line through verbatim — a
    labelled line is machine-parseable and survives future automation.
    """
    install_cmd = format_install_command(required)
    lines = ["ERROR: Missing Python dependencies.", "", "What went wrong:"]
    lines.append(
        "  The following packages are not installed or below the minimum version:"
    )
    for name, min_ver, found in missing:
        if found is None:
            lines.append(f"  • {name} (required: ≥{min_ver}, not installed)")
        else:
            lines.append(f"  • {name} (required: ≥{min_ver}, found: {found})")
    lines.append("")
    lines.append("What to try:")
    lines.append(f"  {install_cmd}")
    lines.append("")
    lines.append(f"INSTALL: {install_cmd}")
    return "\n".join(lines)


def verify_pymannkendall_schema(
    probe: Callable[[list[int]], object] | None = None,
) -> None:
    """Raise DependencyError if pymannkendall's result NamedTuple drifted.

    ``probe`` is an injection point for tests — in production we call the
    real ``pymannkendall.original_test``.
    """
    if probe is None:
        try:
            import pymannkendall as pmk
        except ImportError as exc:
            raise DependencyError(
                "pymannkendall",
                "import failed",
                required="import (version ≥1.4)",
                found=str(exc),
            ) from exc
        try:
            probe = pmk.original_test
        except AttributeError as exc:
            raise DependencyError(
                "pymannkendall",
                "api mismatch",
                required="attribute 'original_test'",
                found="attribute missing from installed package",
            ) from exc

    result = probe([1, 2, 3, 4, 5])
    if not hasattr(result, "_fields"):
        raise DependencyError(
            "pymannkendall",
            "api mismatch",
            required="NamedTuple result type",
            found=f"{type(result).__name__} (no _fields attribute)",
        )
    actual_fields = set(result._fields)
    if not PYMANNKENDALL_EXPECTED_FIELDS.issubset(actual_fields):
        missing_fields = sorted(PYMANNKENDALL_EXPECTED_FIELDS - actual_fields)
        raise DependencyError(
            "pymannkendall",
            "api mismatch",
            required=f"NamedTuple fields ⊇ {sorted(PYMANNKENDALL_EXPECTED_FIELDS)}",
            found=f"missing {missing_fields}",
        )


def _format_dependency_error(exc: DependencyError) -> str:
    lines = [f"ERROR: dependency error: {exc.package} ({exc.reason}).", ""]
    lines.append("What went wrong:")
    if exc.reason == "api mismatch":
        lines.append(
            f"  {exc.package}'s installed API does not match the version the "
            f"engine was built against."
        )
        if exc.required is not None:
            lines.append(f"  expected: {exc.required}")
        if exc.found is not None:
            lines.append(f"  found:    {exc.found}")
        lines.append("")
        lines.append("What to try:")
        lines.append(
            f"  Reinstall {exc.package} at a matching version: "
            f"`pip install --upgrade {exc.package}`."
        )
    else:
        lines.append(f"  {exc.package}: {exc.reason}.")
        lines.append("")
        lines.append("What to try:")
        lines.append(f"  pip install --upgrade {exc.package}")
    return "\n".join(lines)


def main() -> int:
    check_python_version()

    missing = [
        entry
        for entry in (check_package(n, mv) for n, mv in REQUIRED)
        if entry is not None
    ]
    if missing:
        sys.stderr.write(format_missing_diagnostic(missing, REQUIRED) + "\n")
        return 1

    try:
        verify_pymannkendall_schema()
    except DependencyError as exc:
        sys.stderr.write(_format_dependency_error(exc) + "\n")
        return 1

    optional_missing = [
        entry
        for entry in (check_package(n, mv) for n, mv in OPTIONAL)
        if entry is not None
    ]
    if optional_missing:
        names = ", ".join(f"{name}>={min_ver}" for name, min_ver, _ in optional_missing)
        sys.stderr.write(
            f"ADVISORY: optional packages not installed: {names} — some "
            "features (auto-ARIMA, SHAP, LTTB downsampling) will degrade.\n"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
