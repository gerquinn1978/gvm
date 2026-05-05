"""Tests for the module audit gate (P20-C02 — `_module_audit.audit`).

The gate complements the existing Hard Gate 7 row-grep audit: it ensures
every built module under `scripts/_shared/*.py` (or equivalent globs) is
referenced by the wiring matrix as a consumed module. This catches the
silent-omission failure mode that allowed P19 chart wiring and P20
aggregation wiring to ship dead-code in v2.0.0.

Eight tests cover the contract:

1. Empty project (no globbed modules) → `[]`.
2. One module + matrix references it → `[]`.
3. One module + matrix lacks the reference → one `UnwiredModuleError`.
4. Same as #3 but module is in `.module-allowlist` → `[]`.
5. Allowlist supports `#` comments and blank lines.
6. Missing matrix file → `FileNotFoundError`.
7. Missing allowlist treated as empty (no error) — module without
   matrix row still surfaces.
8. Matrix references in prose vs in matrix table — only the table-row
   references count (regression guard against false-positive matching).
"""

from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _module_audit import UnwiredModuleError, audit  # noqa: E402


_MATRIX_HEADER = """# Implementation guide

Some prose. Mentions `_shared.aggregation` here in narrative context only.

### Wiring matrix

| Entry point | Consumed modules | Wiring chunk |
|---|---|---|
"""

_MATRIX_FOOTER = "\n### Next section\n\nMore prose.\n"


def _write_matrix(path: Path, rows: list[str]) -> None:
    path.write_text(_MATRIX_HEADER + "\n".join(rows) + _MATRIX_FOOTER, encoding="utf-8")


def _make_project(
    tmp_path: Path,
    module_stems: list[str],
    matrix_rows: list[str],
    allowlist_lines: list[str] | None = None,
) -> Path:
    project = tmp_path / "proj"
    shared = project / "scripts" / "_shared"
    shared.mkdir(parents=True)
    for stem in module_stems:
        (shared / f"{stem}.py").write_text("# real module\n", encoding="utf-8")
    specs = project / "specs"
    specs.mkdir()
    _write_matrix(specs / "implementation-guide.md", matrix_rows)
    if allowlist_lines is not None:
        (project / ".module-allowlist").write_text(
            "\n".join(allowlist_lines), encoding="utf-8"
        )
    return project


def test_empty_project_returns_empty_list(tmp_path: Path) -> None:
    project = _make_project(tmp_path, module_stems=[], matrix_rows=[])
    assert audit(project) == []


def test_module_referenced_in_matrix_passes(tmp_path: Path) -> None:
    project = _make_project(
        tmp_path,
        module_stems=["aggregation"],
        matrix_rows=[
            "| `analyse.main` | `_shared.aggregation.aggregate` | **P20-C01** |"
        ],
    )
    assert audit(project) == []


def test_module_unreferenced_surfaces_error(tmp_path: Path) -> None:
    project = _make_project(
        tmp_path,
        module_stems=["aggregation"],
        matrix_rows=["| `analyse.main` | `_shared.charts.histogram` | **P19-C02** |"],
    )
    errors = audit(project)
    assert len(errors) == 1
    assert errors[0].module_name == "aggregation"
    assert errors[0].path.endswith("scripts/_shared/aggregation.py")


def test_allowlist_suppresses_unwired_error(tmp_path: Path) -> None:
    project = _make_project(
        tmp_path,
        module_stems=["aggregation"],
        matrix_rows=["| `analyse.main` | `_shared.charts.histogram` | **P19-C02** |"],
        allowlist_lines=["aggregation"],
    )
    assert audit(project) == []


def test_allowlist_supports_comments_and_blank_lines(tmp_path: Path) -> None:
    project = _make_project(
        tmp_path,
        module_stems=["aggregation"],
        matrix_rows=["| `x.main` | `_shared.other` | **P1-C01** |"],
        allowlist_lines=[
            "# Modules without entry-point consumers",
            "",
            "aggregation  # internal-helper rationale",
            "",
            "# end of list",
        ],
    )
    assert audit(project) == []


def test_missing_matrix_file_raises(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    (project / "scripts" / "_shared").mkdir(parents=True)
    (project / "scripts" / "_shared" / "foo.py").write_text("# real")
    # No specs/ directory.
    with pytest.raises(FileNotFoundError):
        audit(project)


def test_missing_allowlist_treated_as_empty(tmp_path: Path) -> None:
    """No .module-allowlist on disk; module not in matrix → error
    surfaces (as if allowlist were empty)."""
    project = _make_project(
        tmp_path,
        module_stems=["aggregation"],
        matrix_rows=["| `x.main` | `_shared.other.foo` | **P1-C01** |"],
        allowlist_lines=None,
    )
    errors = audit(project)
    assert len(errors) == 1
    assert errors[0].module_name == "aggregation"


def test_prose_mentions_do_not_count_as_matrix_references(
    tmp_path: Path,
) -> None:
    """The matrix header's prose mentions `_shared.aggregation` outside
    the table. Only table-row references count — otherwise unwired
    modules would be silently masked by narrative mentions."""
    project = tmp_path / "proj"
    shared = project / "scripts" / "_shared"
    shared.mkdir(parents=True)
    (shared / "aggregation.py").write_text("# real")
    specs = project / "specs"
    specs.mkdir()
    # The matrix header includes "`_shared.aggregation`" in prose; the
    # table itself has zero rows referencing aggregation. The audit must
    # NOT count the prose mention.
    (specs / "implementation-guide.md").write_text(
        _MATRIX_HEADER  # ← carries the prose mention
        + "| `x.main` | `_shared.other.foo` | **P1-C01** |\n"
        + _MATRIX_FOOTER,
        encoding="utf-8",
    )
    errors = audit(project)
    assert len(errors) == 1
    assert errors[0].module_name == "aggregation"


def test_unwired_module_error_is_frozen_dataclass() -> None:
    err = UnwiredModuleError(module_name="x", path="/a/b")
    assert is_dataclass(err)
    with pytest.raises(FrozenInstanceError):
        err.module_name = "y"  # type: ignore[misc]


def test_results_are_sorted_by_module_name(tmp_path: Path) -> None:
    """Determinism: when multiple modules are unwired, results sort by
    name so `/gvm-build` Phase Completion output is reproducible."""
    project = _make_project(
        tmp_path,
        module_stems=["zebra", "alpha", "mango"],
        matrix_rows=["| `x.main` | `_shared.unrelated.x` | **P1-C01** |"],
    )
    errors = audit(project)
    assert [e.module_name for e in errors] == ["alpha", "mango", "zebra"]


def test_dunder_files_excluded(tmp_path: Path) -> None:
    """`__init__.py`, `__main__.py`, dunder files are not modules in
    the audit's sense — they are package machinery, not implementations."""
    project = tmp_path / "proj"
    shared = project / "scripts" / "_shared"
    shared.mkdir(parents=True)
    (shared / "__init__.py").write_text("")
    (shared / "real.py").write_text("# real")
    specs = project / "specs"
    specs.mkdir()
    _write_matrix(
        specs / "implementation-guide.md",
        ["| `x.main` | `_shared.real.fn` | **P1-C01** |"],
    )
    assert audit(project) == []
