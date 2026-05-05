"""Module audit gate (P20-C02) — complementary to Hard Gate 7's row-grep.

Hard Gate 7 (existing) audits the wiring matrix's rows: for each row, it
greps the entry-point file for an import + call site of the named
module. That catches matrix entries that the build silently failed to
wire. It does NOT catch the inverse failure mode: a module that was
built but never written into the matrix in the first place.

Both v2.0.0 wiring bugs (P19 chart producer, P20 aggregation) had this
shape — the modules existed and had unit tests, but no consumer chunk
had been declared, so Hard Gate 7's row scan had nothing to verify.

`audit(project_root)` closes that gap. It enumerates every built module
under the conventional `scripts/_shared/*.py` glob, parses the wiring
matrix in `specs/implementation-guide.md`, and returns one
`UnwiredModuleError` per module whose stem does not appear in the
matrix's "Consumed modules" column. Modules that legitimately have no
entry-point consumer (internal helpers shared across `_shared` modules
themselves, e.g. `diagnostics`) can be listed in `.module-allowlist` at
the project root, one stem per line; lines starting with `#` and blank
lines are ignored.

Per the existing skill convention (`_hs1_check.py`), this is a pure
function. The SKILL.md call site at `/gvm-build` Phase Completion is
responsible for reading `audit()`'s output and refusing the phase if
the list is non-empty.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

__all__ = ["UnwiredModuleError", "audit"]

# Regex extracts the module stem from any reference of the form
# ``_shared.NAME`` or ``_shared.NAME.symbol``. The `\b` ensures we don't
# match longer identifiers as prefixes (`_shared.aggregator` ≠ `_shared.aggregation`).
_MATRIX_REF_RE = re.compile(r"_shared\.(\w+)")

# Default glob the audit covers. The `_shared/` convention is used by every
# GVM-built skill that ships Python entry points; pass a different tuple
# via `module_globs=` for stacks with a different layout.
_DEFAULT_MODULE_GLOBS: tuple[str, ...] = ("scripts/_shared/*.py",)

_DEFAULT_ALLOWLIST_NAME = ".module-allowlist"
_DEFAULT_IMPL_GUIDE_REL = "specs/implementation-guide.md"

# Markdown table-row marker. We restrict matrix-reference extraction to
# table rows so prose paragraphs that happen to mention `_shared.X` do
# not silently mask an unwired module.
_TABLE_ROW_PREFIX = "|"


@dataclass(frozen=True)
class UnwiredModuleError:
    """A built module that does not appear in the wiring matrix.

    `module_name` is the file stem (e.g. ``aggregation``).
    `path` is the absolute filesystem path of the offending module.
    """

    module_name: str
    path: str


def _parse_matrix_modules(impl_guide_path: Path) -> set[str]:
    """Return the set of `_shared.<stem>` references found in any
    Markdown table row of the implementation guide.

    Restricting to table rows (lines starting with `|`) is deliberate:
    the `### Wiring matrix` section's prose may mention modules in
    narrative context. Only table entries declare a real consumer
    relationship.
    """
    if not impl_guide_path.exists():
        raise FileNotFoundError(
            f"implementation guide not found at {impl_guide_path}; "
            "the module audit cannot run without the wiring matrix."
        )
    stems: set[str] = set()
    for line in impl_guide_path.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith(_TABLE_ROW_PREFIX):
            continue
        for match in _MATRIX_REF_RE.finditer(line):
            stems.add(match.group(1))
    return stems


def _load_allowlist(path: Path) -> set[str]:
    """Return the set of allowlisted module stems from `path`.

    A missing file is treated as an empty allowlist. Lines starting
    with `#` are comments. Inline `#` comments are stripped. Blank
    lines are ignored.
    """
    if not path.exists():
        return set()
    stems: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        # Strip inline `#` comments, then surrounding whitespace.
        line = raw.split("#", 1)[0].strip()
        if line:
            stems.add(line)
    return stems


def _enumerate_modules(project_root: Path, module_globs: Iterable[str]) -> list[Path]:
    """Return every Python file matched by any glob, excluding dunder files."""
    found: list[Path] = []
    for pattern in module_globs:
        for path in project_root.glob(pattern):
            if path.name.startswith("__") and path.name.endswith("__.py"):
                continue
            found.append(path)
    return found


def audit(
    project_root: Path,
    *,
    module_globs: Iterable[str] = _DEFAULT_MODULE_GLOBS,
    allowlist_path: Path | None = None,
    impl_guide_path: Path | None = None,
) -> list[UnwiredModuleError]:
    """Return the list of built modules that do not appear in the
    wiring matrix.

    Parameters
    ----------
    project_root
        Repository root. The default `module_globs` are evaluated
        relative to this directory.
    module_globs
        Glob patterns matching the project's built modules. Default
        covers the `scripts/_shared/*.py` convention shared by every
        GVM-built skill that ships Python entry points.
    allowlist_path
        Path to the project's allowlist file. Default
        ``<project_root>/.module-allowlist``. A missing file is
        treated as an empty allowlist.
    impl_guide_path
        Path to the implementation guide containing the wiring matrix.
        Default ``<project_root>/specs/implementation-guide.md``.

    Returns
    -------
    A list of `UnwiredModuleError` records, sorted by ``module_name``
    for deterministic output. Empty list = pass.

    Raises
    ------
    FileNotFoundError
        If the implementation guide cannot be located. The audit is
        load-bearing on the matrix existing — silent passes against a
        missing matrix would defeat the purpose of the gate.
    """
    if allowlist_path is None:
        allowlist_path = project_root / _DEFAULT_ALLOWLIST_NAME
    if impl_guide_path is None:
        impl_guide_path = project_root / _DEFAULT_IMPL_GUIDE_REL

    matrix_stems = _parse_matrix_modules(impl_guide_path)
    allowed_stems = _load_allowlist(allowlist_path)
    modules = _enumerate_modules(project_root, module_globs)

    errors: list[UnwiredModuleError] = []
    for path in modules:
        stem = path.stem
        if stem in matrix_stems or stem in allowed_stems:
            continue
        errors.append(UnwiredModuleError(module_name=stem, path=str(path)))

    errors.sort(key=lambda e: e.module_name)
    return errors
