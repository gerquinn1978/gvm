"""Tests for `_panel_e_prompt.assemble_panel_e_prompt` (honesty-triad ADR-107)."""

from __future__ import annotations

from pathlib import Path

import pytest

from _panel_e_prompt import (
    HeuristicSectionMissingError,
    PanelEPromptError,
    UnknownLanguageError,
    assemble_panel_e_prompt,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
LIVE_HEURISTIC = (
    REPO_ROOT
    / "grounded-vibe-methodology"
    / "skills"
    / "gvm-code-review"
    / "references"
    / "stub-detection.md"
)


def _write_heuristic(path: Path) -> None:
    path.write_text(
        "# Stub-Detection Heuristics\n\n"
        "## Python\n"
        "A function body is a stub candidate iff it returns a literal.\n"
        "Excluded: I/O, parameter-dependent branch.\n\n"
        "## TypeScript / JavaScript\n"
        "A function body is a stub candidate iff it returns Promise.resolve(<literal>).\n\n"
        "## Go\n"
        "A function body is a stub candidate iff it returns a literal struct, slice, or map.\n"
    )


def test_prompt_contains_stubs_md_verbatim(tmp_path: Path):
    stubs = tmp_path / "STUBS.md"
    stubs.write_text(
        "---\nschema_version: 1\n---\n# Stubs\n| col |\n| --- |\n| row |\n"
    )
    allowlist = tmp_path / ".stub-allowlist"
    allowlist.write_text("# empty\n")
    heur = tmp_path / "h.md"
    _write_heuristic(heur)
    out = assemble_panel_e_prompt(
        stubs_md_path=stubs,
        allowlist_path=allowlist,
        heuristic_md_path=heur,
        language="Python",
    )
    assert "schema_version: 1" in out
    assert "| row |" in out


def test_prompt_contains_allowlist_verbatim(tmp_path: Path):
    stubs = tmp_path / "STUBS.md"
    stubs.write_text("# Stubs\n")
    allowlist = tmp_path / ".stub-allowlist"
    allowlist.write_text("constants/iso.py::ISO_CODES | enum | ISO 3166 codes\n")
    heur = tmp_path / "h.md"
    _write_heuristic(heur)
    out = assemble_panel_e_prompt(
        stubs_md_path=stubs,
        allowlist_path=allowlist,
        heuristic_md_path=heur,
        language="Python",
    )
    assert "constants/iso.py::ISO_CODES | enum | ISO 3166 codes" in out


def test_prompt_python_section_only(tmp_path: Path):
    heur = tmp_path / "h.md"
    _write_heuristic(heur)
    out = assemble_panel_e_prompt(
        stubs_md_path=None,
        allowlist_path=None,
        heuristic_md_path=heur,
        language="Python",
    )
    # Python section content present
    assert "returns a literal" in out
    assert "I/O" in out
    # Other-language markers absent
    assert "Promise.resolve" not in out
    assert "literal struct, slice, or map" not in out


def test_prompt_typescript_section_only(tmp_path: Path):
    heur = tmp_path / "h.md"
    _write_heuristic(heur)
    out = assemble_panel_e_prompt(
        stubs_md_path=None,
        allowlist_path=None,
        heuristic_md_path=heur,
        language="TypeScript",
    )
    assert "Promise.resolve" in out
    # Python iff-rule body should not leak in (uses different wording)
    assert "Excluded: I/O, parameter-dependent branch." not in out


def test_prompt_go_section_only(tmp_path: Path):
    heur = tmp_path / "h.md"
    _write_heuristic(heur)
    out = assemble_panel_e_prompt(
        stubs_md_path=None,
        allowlist_path=None,
        heuristic_md_path=heur,
        language="Go",
    )
    assert "literal struct, slice, or map" in out
    assert "Promise.resolve" not in out


def test_missing_stubs_md_uses_placeholder(tmp_path: Path):
    heur = tmp_path / "h.md"
    _write_heuristic(heur)
    out = assemble_panel_e_prompt(
        stubs_md_path=tmp_path / "does-not-exist.md",
        allowlist_path=None,
        heuristic_md_path=heur,
        language="Python",
    )
    assert "(empty — no entries)" in out


def test_missing_allowlist_uses_placeholder(tmp_path: Path):
    heur = tmp_path / "h.md"
    _write_heuristic(heur)
    out = assemble_panel_e_prompt(
        stubs_md_path=None,
        allowlist_path=tmp_path / "does-not-exist",
        heuristic_md_path=heur,
        language="Python",
    )
    assert out.count("(empty — no entries)") >= 2


def test_none_paths_use_placeholder(tmp_path: Path):
    heur = tmp_path / "h.md"
    _write_heuristic(heur)
    out = assemble_panel_e_prompt(
        stubs_md_path=None,
        allowlist_path=None,
        heuristic_md_path=heur,
        language="Python",
    )
    assert out.count("(empty — no entries)") >= 2


def test_unknown_language_raises(tmp_path: Path):
    heur = tmp_path / "h.md"
    _write_heuristic(heur)
    with pytest.raises(UnknownLanguageError, match="Rust"):
        assemble_panel_e_prompt(
            stubs_md_path=None,
            allowlist_path=None,
            heuristic_md_path=heur,
            language="Rust",  # type: ignore[arg-type]
        )


def test_missing_heuristic_section_raises(tmp_path: Path):
    heur = tmp_path / "h.md"
    heur.write_text("# Stub-Detection Heuristics\n\n## Python\nbody\n")
    with pytest.raises(HeuristicSectionMissingError, match="Go"):
        assemble_panel_e_prompt(
            stubs_md_path=None,
            allowlist_path=None,
            heuristic_md_path=heur,
            language="Go",
        )


def test_missing_heuristic_file_raises(tmp_path: Path):
    with pytest.raises(PanelEPromptError):
        assemble_panel_e_prompt(
            stubs_md_path=None,
            allowlist_path=None,
            heuristic_md_path=tmp_path / "missing.md",
            language="Python",
        )


def test_section_extraction_stops_at_next_h2(tmp_path: Path):
    heur = tmp_path / "h.md"
    heur.write_text(
        "# Heuristics\n\n## Python\nA-line\nB-line\n\n## TypeScript / JavaScript\nC-line\n"
    )
    out = assemble_panel_e_prompt(
        stubs_md_path=None,
        allowlist_path=None,
        heuristic_md_path=heur,
        language="Python",
    )
    assert "A-line" in out
    assert "B-line" in out
    assert "C-line" not in out


def test_output_includes_panel_purpose_header(tmp_path: Path):
    heur = tmp_path / "h.md"
    _write_heuristic(heur)
    out = assemble_panel_e_prompt(
        stubs_md_path=None,
        allowlist_path=None,
        heuristic_md_path=heur,
        language="Python",
    )
    # The prompt must orient the reviewer agent
    assert "Panel E" in out
    assert "STUBS.md" in out
    assert "allowlist" in out.lower()


def test_deterministic_on_identical_inputs(tmp_path: Path):
    heur = tmp_path / "h.md"
    _write_heuristic(heur)
    a = assemble_panel_e_prompt(
        stubs_md_path=None,
        allowlist_path=None,
        heuristic_md_path=heur,
        language="Python",
    )
    b = assemble_panel_e_prompt(
        stubs_md_path=None,
        allowlist_path=None,
        heuristic_md_path=heur,
        language="Python",
    )
    assert a == b


def test_live_heuristic_python_section_loads():
    """End-to-end: the project's actual stub-detection.md has a usable Python section."""
    out = assemble_panel_e_prompt(
        stubs_md_path=None,
        allowlist_path=None,
        heuristic_md_path=LIVE_HEURISTIC,
        language="Python",
    )
    # SD-2 heuristic markers must survive the round-trip
    assert "literal" in out
    assert "parameter" in out


def test_live_heuristic_typescript_section_loads():
    out = assemble_panel_e_prompt(
        stubs_md_path=None,
        allowlist_path=None,
        heuristic_md_path=LIVE_HEURISTIC,
        language="TypeScript",
    )
    assert "Promise.resolve" in out


def test_live_heuristic_go_section_loads():
    out = assemble_panel_e_prompt(
        stubs_md_path=None,
        allowlist_path=None,
        heuristic_md_path=LIVE_HEURISTIC,
        language="Go",
    )
    assert "struct, slice, or map" in out


# --- HS-5 namespace policy (ADR-104) ----------------------------------


def test_prompt_contains_namespace_policy(tmp_path: Path):
    """The assembled prompt names the `stubs/` bounded context and the
    `namespace_violation` violation_type so Panel E can emit HS-5 findings."""
    heur = tmp_path / "h.md"
    _write_heuristic(heur)
    out = assemble_panel_e_prompt(
        stubs_md_path=None,
        allowlist_path=None,
        heuristic_md_path=heur,
        language="Python",
    )
    assert "stubs/" in out
    assert "namespace_violation" in out
    # Must spell out the rule: outside-stubs is Critical regardless of registration
    assert "Critical" in out


def test_namespace_check_precedes_registration(tmp_path: Path):
    """HS-5 namespace check must be applied BEFORE STUBS.md / allowlist
    reconciliation so a non-`stubs/` match is not downgraded by registration."""
    heur = tmp_path / "h.md"
    _write_heuristic(heur)
    out = assemble_panel_e_prompt(
        stubs_md_path=None,
        allowlist_path=None,
        heuristic_md_path=heur,
        language="Python",
    )
    ns_idx = out.find("namespace_violation")
    reg_idx = out.find("Reconcile against STUBS.md")
    assert ns_idx >= 0 and reg_idx >= 0
    assert ns_idx < reg_idx, (
        "namespace policy must appear before STUBS.md reconciliation in the prompt"
    )


# --- violation_type contract on every reconciliation branch (R22 C-1) ----


def test_expired_branch_emits_violation_type_expired(tmp_path: Path):
    """ADR-104: every Panel E finding has a typed violation_type. The expired
    branch of the reconciliation step MUST instruct the agent to emit
    violation_type="expired", not just a Critical severity label.
    """
    heur = tmp_path / "h.md"
    _write_heuristic(heur)
    out = assemble_panel_e_prompt(
        stubs_md_path=None,
        allowlist_path=None,
        heuristic_md_path=heur,
        language="Python",
    )
    assert 'violation_type="expired"' in out, (
        'Panel E prompt step 1 must emit violation_type="expired" for '
        "registered-but-expired stubs so the JSON sidecar consumer can route "
        "the finding correctly."
    )


def test_unregistered_branch_emits_violation_type_unregistered(tmp_path: Path):
    """Same contract for the unregistered branch — explicit field, not a
    paraphrase."""
    heur = tmp_path / "h.md"
    _write_heuristic(heur)
    out = assemble_panel_e_prompt(
        stubs_md_path=None,
        allowlist_path=None,
        heuristic_md_path=heur,
        language="Python",
    )
    assert 'violation_type="unregistered"' in out


def test_empty_section_body_raises(tmp_path: Path):
    """A heuristic file with `## Python` followed by only whitespace must
    raise HeuristicSectionMissingError, distinct from the absent-header case
    which is already covered."""
    heur = tmp_path / "h.md"
    heur.write_text(
        "# Heuristics\n\n"
        "## Python\n"
        "\n"
        "## TypeScript / JavaScript\n"
        "some content\n"
        "## Go\n"
        "more content\n",
        encoding="utf-8",
    )
    with pytest.raises(HeuristicSectionMissingError):
        assemble_panel_e_prompt(
            stubs_md_path=None,
            allowlist_path=None,
            heuristic_md_path=heur,
            language="Python",
        )
