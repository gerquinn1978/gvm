"""Walking-skeleton generator (P11-C03 — ADR-404, ADR-405, ADR-407).

Given a parsed `Boundaries` registry, emit:
    - <output_dir>/test_skeleton.<ext>  — exactly one test function exercising
      every boundary (single-flow constraint, ADR-405)
    - <output_dir>/clients/<name>.<ext>  — one placeholder per boundary; the
      practitioner fills in the real call (Freeman & Pryce: shape, not meat)

The emitted skeleton is the *forcing function* of WS-3: real-call validation
fails on first run if credentials, CORS, rate limits, or the wire format are
wrong. That is exactly the kind of integration failure walking skeletons exist
to surface.

Pure module — no AskUserQuestion, no network, no mutation outside the
explicit `output_dir` write. Per Clements decomposition, does NOT import
`_single_flow_check` (the lint runs against this module's output but the two
modules are independent).
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

# `_boundaries_parser` lives in the gvm-design-system skill. Insert its scripts
# dir on sys.path; mirror lines 32-36 of `_validator.py`.
_DS_SCRIPTS = Path(__file__).resolve().parents[2] / "gvm-design-system" / "scripts"
if str(_DS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_DS_SCRIPTS))

from _boundaries_parser import Boundaries, Boundary  # noqa: E402

_LANGUAGE_EXTENSIONS: dict[str, str] = {
    "python": ".py",
    "typescript": ".ts",
    "go": ".go",
}
# Go's test-file convention is `<name>_test.go` (the runtime requires this
# suffix for `go test` to discover). Pythons / TS use the leading `test_`
# convention.
_TEST_FILE_BASENAMES: dict[str, str] = {
    "python": "test_skeleton",
    "typescript": "test_skeleton",
    "go": "skeleton_test",
}

_IDENT_RE = re.compile(r"[^a-zA-Z0-9_]")


@dataclass(frozen=True)
class SkeletonResult:
    test_file: Path
    client_files: tuple[Path, ...]
    primary_language: str


def generate(
    boundaries: Boundaries,
    output_dir: Path,
    *,
    primary_language: str = "python",
) -> SkeletonResult:
    """Emit the skeleton test file and per-boundary client placeholders.

    Raises:
        ValueError when primary_language is not in {"python", "typescript", "go"}
        FileExistsError when the test file already exists at output_dir
    """

    lang = primary_language.lower()
    if lang not in _LANGUAGE_EXTENSIONS:
        raise ValueError(
            f"unsupported language {primary_language!r}; expected one of "
            f"{sorted(_LANGUAGE_EXTENSIONS)}"
        )

    ext = _LANGUAGE_EXTENSIONS[lang]
    test_file = output_dir / f"{_TEST_FILE_BASENAMES[lang]}{ext}"
    if test_file.exists():
        raise FileExistsError(
            f"refusing to overwrite existing skeleton at {test_file}; "
            f"delete the file first to regenerate"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    clients_dir = output_dir / "clients"
    # Go: client files MUST end in `_test.go` so `go test` links them into the
    # test binary (a `*.go` file compiled into the production package may not
    # import "testing", and `*_test.go` is the only visibility surface for
    # `*testing.T`-typed helpers). Python / TS use the boundary name as-is.
    client_paths = [
        clients_dir / _client_basename(_module_name(row.name), lang, ext)
        for row in boundaries.rows
    ]
    init_path = clients_dir / "__init__.py" if lang == "python" else None

    # Refuse to overwrite practitioner edits to ANY emitted artefact — clients,
    # __init__.py, or the test file. The forcing-function value of a walking
    # skeleton comes from the practitioner replacing the placeholders; we
    # never silently clobber that work.
    candidates: list[Path] = list(client_paths)
    if init_path is not None:
        candidates.append(init_path)
    existing = [str(p) for p in candidates if p.exists()]
    if existing:
        raise FileExistsError(
            "refusing to overwrite existing skeleton file(s): " + ", ".join(existing)
        )

    if boundaries.rows:
        clients_dir.mkdir(parents=True, exist_ok=True)
        if init_path is not None:
            init_path.write_text("", encoding="utf-8")

    client_files: list[Path] = []
    for row, client_path in zip(boundaries.rows, client_paths, strict=True):
        client_path.write_text(_render_client(row, lang), encoding="utf-8")
        client_files.append(client_path)

    test_file.write_text(_render_test(boundaries, lang), encoding="utf-8")

    return SkeletonResult(
        test_file=test_file,
        client_files=tuple(client_files),
        primary_language=lang,
    )


# --------------------------------------------------------- helpers


def _client_basename(module_name: str, language: str, ext: str) -> str:
    """Return the client filename for a given language. Go requires the
    `_test.go` suffix so `go test` includes the file in the test binary;
    Python/TS use the bare module name + extension."""
    if language == "go":
        return f"{module_name}_test{ext}"
    return f"{module_name}{ext}"


def _module_name(boundary_name: str) -> str:
    """Convert a boundary name (which may contain hyphens, dots) to a valid
    snake_case Python/TS module / Go file basename. Prefixes a leading
    underscore when the cleaned name starts with a digit so the result is a
    legal Python/Go identifier (e.g. "3rdparty-api" -> "_3rdparty_api")."""
    cleaned = _IDENT_RE.sub("_", boundary_name).strip("_")
    if not cleaned:
        return "boundary"
    if cleaned[0].isdigit():
        return "_" + cleaned
    return cleaned


def _render_test(boundaries: Boundaries, language: str) -> str:
    if language == "python":
        return _render_test_python(boundaries)
    if language == "typescript":
        return _render_test_typescript(boundaries)
    return _render_test_go(boundaries)


def _render_client(row: Boundary, language: str) -> str:
    if language == "python":
        return _render_client_python(row)
    if language == "typescript":
        return _render_client_typescript(row)
    return _render_client_go(row)


# --------------------------------------------------------- python


def _render_test_python(boundaries: Boundaries) -> str:
    lines: list[str] = [
        '"""Walking-skeleton runtime test (generated by /gvm-walking-skeleton).',
        "",
        "ADR-404: real-call validation. ADR-405: single-flow constraint (<= 3 tests).",
        "ADR-407: deferred boundaries are no-op assertions registered in STUBS.md.",
        '"""',
        "from __future__ import annotations",
        "",
    ]
    if boundaries.rows:
        lines.append(
            "from clients import "
            + ", ".join(_module_name(r.name) for r in boundaries.rows)
        )
    lines.append("")
    lines.append("")
    lines.append("def test_walking_skeleton_flow() -> None:")
    if not boundaries.rows:
        lines.append('    """Placeholder: no boundaries discovered. Add boundaries via')
        lines.append('    /gvm-walking-skeleton then re-run."""')
        lines.append("    assert True")
        return "\n".join(lines) + "\n"

    for row in boundaries.rows:
        lines.append("")
        lines.append(f"    # boundary {row.name!r} ({row.type}, {row.chosen_provider})")
        if row.real_call_status == "deferred_stub":
            lines.append(
                "    # deferred per ADR-407 — see STUBS.md "
                f"walking-skeleton/stubs/{row.name}.py"
            )
            lines.append(f"    # boundary status: {row.real_call_status}")
            lines.append("    assert True  # deferred no-op")
        else:
            lines.append(f"    # status: {row.real_call_status}")
            if (
                row.real_call_status == "wired_sandbox"
                and row.production_sandbox_divergence
            ):
                lines.append(
                    f"    # sandbox divergence: {row.production_sandbox_divergence}"
                )
            lines.append(
                f"    {_module_name(row.name)}.exercise()  "
                f"# real call (HTTP/DB/SDK per type={row.type})"
            )
    return "\n".join(lines) + "\n"


def _render_client_python(row: Boundary) -> str:
    sandbox_note = ""
    if row.real_call_status == "wired_sandbox" and row.production_sandbox_divergence:
        sandbox_note = (
            f"\nSandbox divergence (from boundaries.md): "
            f"{row.production_sandbox_divergence}"
        )
    return (
        f'"""Client wrapper for boundary {row.name!r} '
        f"({row.type}, {row.chosen_provider}).\n"
        f"\n"
        f"Test credentials: {row.test_credentials_location}\n"
        f"Cost model: {row.cost_model}\n"
        f"SLA: {row.sla_notes}\n"
        f"Status: {row.real_call_status}{sandbox_note}\n"
        f"\n"
        f"PRACTITIONER: implement the real call below. The walking skeleton's\n"
        f"value comes from forcing real-integration debugging at scaffold time.\n"
        f'"""\n'
        f"from __future__ import annotations\n"
        f"\n"
        f"\n"
        f"def exercise() -> None:\n"
        f"    raise NotImplementedError(\n"
        f'        "Wire the real call to {row.chosen_provider} for boundary '
        f'{row.name!r} here"\n'
        f"    )\n"
    )


# --------------------------------------------------------- typescript


def _render_test_typescript(boundaries: Boundaries) -> str:
    header = (
        "// Walking-skeleton runtime test (generated by /gvm-walking-skeleton).\n"
        "// ADR-404: real-call validation. ADR-405: single-flow constraint.\n"
    )
    if not boundaries.rows:
        return (
            header
            + "test('walking skeleton flow', () => {\n"
            + "  // no boundaries discovered\n"
            + "  expect(true).toBe(true);\n"
            + "});\n"
        )
    imports = "".join(
        f"import * as {_module_name(r.name)} from './clients/{_module_name(r.name)}';\n"
        for r in boundaries.rows
    )
    body_lines = ["test('walking skeleton flow', async () => {"]
    for row in boundaries.rows:
        body_lines.append(
            f"  // boundary '{row.name}' ({row.type}, {row.chosen_provider})"
        )
        if row.real_call_status == "deferred_stub":
            body_lines.append(
                f"  // deferred per ADR-407 — see STUBS.md "
                f"walking-skeleton/stubs/{row.name}.ts"
            )
            body_lines.append("  expect(true).toBe(true); // deferred no-op")
        else:
            if (
                row.real_call_status == "wired_sandbox"
                and row.production_sandbox_divergence
            ):
                body_lines.append(
                    f"  // sandbox divergence: {row.production_sandbox_divergence}"
                )
            body_lines.append(f"  await {_module_name(row.name)}.exercise();")
    body_lines.append("});")
    return header + imports + "\n" + "\n".join(body_lines) + "\n"


def _render_client_typescript(row: Boundary) -> str:
    sandbox_note = ""
    if row.real_call_status == "wired_sandbox" and row.production_sandbox_divergence:
        sandbox_note = f"\n// Sandbox divergence: {row.production_sandbox_divergence}"
    return (
        f"// Client wrapper for boundary '{row.name}' "
        f"({row.type}, {row.chosen_provider}).\n"
        f"// Test credentials: {row.test_credentials_location}\n"
        f"// Status: {row.real_call_status}{sandbox_note}\n"
        f"// PRACTITIONER: implement the real call below.\n"
        f"export async function exercise(): Promise<void> {{\n"
        f"  throw new Error(\n"
        f'    "Wire the real call to {row.chosen_provider} for boundary '
        f"'{row.name}' here\"\n"
        f"  );\n"
        f"}}\n"
    )


# --------------------------------------------------------- go


def _render_test_go(boundaries: Boundaries) -> str:
    header = (
        "package walkingskeleton\n"
        "\n"
        "// Walking-skeleton runtime test (generated by /gvm-walking-skeleton).\n"
        "// ADR-404: real-call validation. ADR-405: single-flow constraint.\n"
        "\n"
        'import "testing"\n'
        "\n"
    )
    if not boundaries.rows:
        return (
            header
            + "func TestWalkingSkeletonFlow(t *testing.T) {\n"
            + "    // no boundaries discovered\n"
            + "}\n"
        )
    body = ["func TestWalkingSkeletonFlow(t *testing.T) {"]
    for row in boundaries.rows:
        body.append(f"    // boundary '{row.name}' ({row.type}, {row.chosen_provider})")
        if row.real_call_status == "deferred_stub":
            body.append(
                f"    // deferred per ADR-407 — see STUBS.md "
                f"walking-skeleton/stubs/{row.name}.go"
            )
            body.append("    // deferred no-op")
        else:
            if (
                row.real_call_status == "wired_sandbox"
                and row.production_sandbox_divergence
            ):
                body.append(
                    f"    // sandbox divergence: {row.production_sandbox_divergence}"
                )
            body.append(f"    if err := exercise{_camel(row.name)}(t); err != nil {{")
            body.append("        t.Fatal(err)")
            body.append("    }")
    body.append("}")
    return header + "\n".join(body) + "\n"


def _render_client_go(row: Boundary) -> str:
    sandbox_note = ""
    if row.real_call_status == "wired_sandbox" and row.production_sandbox_divergence:
        sandbox_note = f"\n// Sandbox divergence: {row.production_sandbox_divergence}"
    return (
        f"package walkingskeleton\n"
        f"\n"
        f"// Client wrapper for boundary '{row.name}' "
        f"({row.type}, {row.chosen_provider}).\n"
        f"// Test credentials: {row.test_credentials_location}\n"
        f"// Status: {row.real_call_status}{sandbox_note}\n"
        f"// PRACTITIONER: implement the real call below.\n"
        f"\n"
        f'import "testing"\n'
        f"\n"
        f"func exercise{_camel(row.name)}(t *testing.T) error {{\n"
        f'    t.Fatalf("Wire the real call to {row.chosen_provider} for '
        f"boundary '{row.name}' here\")\n"
        f"    return nil\n"
        f"}}\n"
    )


def _camel(name: str) -> str:
    parts = re.split(r"[^a-zA-Z0-9]+", name)
    return "".join(p[:1].upper() + p[1:] for p in parts if p) or "Boundary"
