"""Keyword presence test for `/gvm-code-review` SKILL.md (partial TC-PP-1-01).

The full PP-1 verifier (P13-C03) scans every affected SKILL.md across the
plugin tree. This chunk-level test covers the gvm-code-review side: the
SKILL.md must reference Panel E, the prompt/allowlist/promotion helpers, the
findings JSON sidecar producer, and the violation_type vocabulary.
"""

from __future__ import annotations

from pathlib import Path

import pytest

SKILL_MD = Path(__file__).resolve().parents[1] / "SKILL.md"


@pytest.fixture(scope="module")
def skill_text() -> str:
    return SKILL_MD.read_text(encoding="utf-8")


REQUIRED_KEYWORDS = (
    "Panel E",
    "stub-detection",
    "_panel_e_prompt",
    "_allowlist",
    "_sd5_promotion",
    "_findings_serialiser",
    "code-review-NNN.findings.json",
    "unregistered",
    "expired",
    "namespace_violation",
    # P12-C08 — Panel B EBT contract/collaboration lint (testing-mandates ADR-508)
    "_ebt_contract_lint",
    "rainsberger",
    "metz",
    "ADR-503",
    "ADR-504",
    "ADR-508",
    "detect_source_root",
    ".ebt-boundaries",
    "ebt_boundaries_path",
    # P13-C02 — first-run migration hook (pipeline-propagation ADR-608, TC-PP-8-02)
    "schema_version",
    "gvm-migrate-calibration",  # script display name (hyphens)
    "gvm_migrate_calibration",  # module name (underscores) — invoked via python -m
    "ADR-608",
    "TC-PP-8-02",
)


def test_skill_md_first_run_hook_offers_migration_options(skill_text: str):
    # Per ADR-608 sequence: the AskUserQuestion options must match verbatim so
    # the practitioner sees a clear binary choice with an explicit consequence
    # for deferring.
    assert "Yes, run gvm-migrate-calibration now" in skill_text, (
        "ADR-608 first-run hook is missing the affirmative option"
    )
    assert "Skip (legacy calibration retained)" in skill_text, (
        "ADR-608 first-run hook is missing the deferred-consequence option"
    )


def test_skill_md_first_run_hook_covers_both_missing_cases(skill_text: str):
    # The hook must trigger when (a) the file has no frontmatter, OR (b) the
    # frontmatter is present but does not declare schema_version. Both cases
    # are explicit in the ADR-608 sequence — drift between the two would let
    # half the legacy fleet through unmigrated.
    assert "no frontmatter" in skill_text.lower(), (
        "first-run hook does not name the no-frontmatter trigger"
    )
    assert "no schema_version" in skill_text or "no `schema_version`" in skill_text, (
        "first-run hook does not name the missing-schema_version trigger"
    )


@pytest.mark.parametrize("keyword", REQUIRED_KEYWORDS)
def test_skill_md_contains_keyword(skill_text: str, keyword: str):
    assert keyword in skill_text, (
        f"PP-1 keyword {keyword!r} missing from gvm-code-review/SKILL.md"
    )


def test_skill_md_dispatches_panel_e_in_parallel(skill_text: str):
    # The mention of "Panel E" must be co-located with "parallel" — the bug
    # this guards against is Panel E being described only as supplementary
    # without being wired into the parallel dispatch step.
    lowered = skill_text.lower()
    panel_e_positions = [
        i for i in range(len(skill_text)) if skill_text.startswith("Panel E", i)
    ]
    assert panel_e_positions, "Panel E not mentioned at all"
    # At least one Panel E mention must sit within 400 chars of "parallel".
    parallel_positions = [
        i for i in range(len(lowered)) if lowered.startswith("parallel", i)
    ]
    assert any(
        abs(p - q) < 400 for p in panel_e_positions for q in parallel_positions
    ), "Panel E and 'parallel' are never co-located — dispatch wiring missing"


def test_skill_md_documents_serialise_step(skill_text: str):
    # The serialise-findings step must be discoverable as a heading.
    assert (
        "SERIALISE FINDINGS" in skill_text
        or "Serialise findings" in skill_text
        or "serialise findings" in skill_text
    )


def test_skill_md_names_ndjson_sidecar_format(skill_text: str):
    # Sidecar is NDJSON — readers must be able to find this fact.
    assert "NDJSON" in skill_text or "one JSON object per line" in skill_text
