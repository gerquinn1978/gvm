"""PP-6 structural test for `pipeline-contracts.md` (TC-PP-6-01).

Pipeline-propagation ADR-606 / ADR-609 require seven cross-cutting artefact
entries in `references/pipeline-contracts.md`. The cross-cutting verifier
`_verify_pp_cross_cutting.check_pipeline_contracts_sections` enforces the
H2 headings; this test extends the coverage to substantive content (each
section has Producer + at least one Consumer + a non-trivial body).

The canonical heading list is `_verify_pp_cross_cutting.PP6_REQUIRED_SECTIONS`
— DRY: the verifier and this test never drift.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = PLUGIN_ROOT / "references" / "pipeline-contracts.md"


def _load_required_sections() -> tuple[str, ...]:
    """Re-import the verifier's canonical list (DRY).

    Canonical sys.path idiom (P13-C04..C09): insert + try/finally with
    `sys.path.remove(value)` + `sys.modules.pop(name, None)` so a later test
    importing a same-named module from a different path is not aliased.
    """
    scripts_dir = PLUGIN_ROOT / "scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        import _verify_pp_cross_cutting as v
        return v.PP6_REQUIRED_SECTIONS
    finally:
        try:
            sys.path.remove(str(scripts_dir))
        except ValueError:
            pass
        sys.modules.pop("_verify_pp_cross_cutting", None)


REQUIRED_SECTIONS = _load_required_sections()


@pytest.fixture(scope="module")
def contracts_text() -> str:
    return CONTRACTS.read_text(encoding="utf-8")


def _extract_section_body(text: str, heading: str) -> str:
    """Return the body between *heading* (an H2) and the next H2 (or EOF).

    Returns "" if the heading is not present at start-of-line.
    """
    pattern = re.compile(
        rf"^{re.escape(heading)}\s*$(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    return match.group(1) if match else ""


@pytest.mark.parametrize("heading", REQUIRED_SECTIONS)
def test_h2_section_present_at_start_of_line(heading: str, contracts_text: str):
    """Each required heading appears as a real H2, not embedded in prose."""
    pattern = re.compile(rf"^{re.escape(heading)}\s*$", re.MULTILINE)
    assert pattern.search(contracts_text), (
        f"PP-6 H2 heading {heading!r} missing from pipeline-contracts.md "
        "— must appear at start-of-line per ADR-606"
    )


@pytest.mark.parametrize("heading", REQUIRED_SECTIONS)
def test_section_has_substantive_body(heading: str, contracts_text: str):
    """Section body must be ≥ 200 chars — guards against skeleton entries."""
    body = _extract_section_body(contracts_text, heading)
    assert len(body.strip()) >= 200, (
        f"PP-6 section {heading!r} body is only {len(body.strip())} chars "
        "— expected ≥ 200 (Producer + Consumers + Required structure + "
        "What consumers depend on, same shape as existing entries)"
    )


@pytest.mark.parametrize("heading", REQUIRED_SECTIONS)
def test_section_names_producer(heading: str, contracts_text: str):
    body = _extract_section_body(contracts_text, heading)
    assert "**Producer:**" in body, (
        f"PP-6 section {heading!r} missing '**Producer:**' field — "
        "every contract must name its producer skill"
    )


@pytest.mark.parametrize("heading", REQUIRED_SECTIONS)
def test_section_names_consumer(heading: str, contracts_text: str):
    body = _extract_section_body(contracts_text, heading)
    assert "**Consumers:**" in body or "**Consumer:**" in body, (
        f"PP-6 section {heading!r} missing '**Consumers:**' field — "
        "every contract must name at least one consumer skill"
    )


@pytest.mark.parametrize("heading", REQUIRED_SECTIONS)
def test_section_documents_required_structure(
    heading: str, contracts_text: str
):
    body = _extract_section_body(contracts_text, heading)
    assert "Required structure" in body or "Required content" in body, (
        f"PP-6 section {heading!r} missing 'Required structure' subsection "
        "— matches the shape of existing PP-6 entries"
    )


def test_section_order_matches_pp6_canonical():
    """Sections appear in the order declared in PP6_REQUIRED_SECTIONS."""
    text = CONTRACTS.read_text(encoding="utf-8")
    positions: list[int] = []
    for heading in REQUIRED_SECTIONS:
        pattern = re.compile(rf"^{re.escape(heading)}\s*$", re.MULTILINE)
        match = pattern.search(text)
        assert match is not None, f"heading {heading!r} not found"
        positions.append(match.start())
    assert positions == sorted(positions), (
        f"PP-6 sections not in canonical order. Positions: {positions}; "
        f"canonical order: {REQUIRED_SECTIONS}"
    )
