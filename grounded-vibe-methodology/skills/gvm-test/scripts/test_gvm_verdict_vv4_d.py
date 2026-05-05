"""Tests for `gvm_verdict.evaluate_vv4_d` — ET-5 wiring (P11-C09).

Closes the seam between `/gvm-explore-test`'s output (`test/explore-NNN.md`)
and `/gvm-test`'s VV-4(d) row. Test cases TC-ET-5-01..04 plus defensive
coverage for empty/malformed inputs and the unassigned-runner branch
(ADR-207).

The fixtures use the SPEC-conformant explore-NNN.md shape (frontmatter +
fenced YAML charter + labelled-body severity) — what `_explore_parser`
expects. The writer-parser format divergence is documented as an Upstream
Fix in the P11-C09 handover; resolving it is not in this chunk's scope.
"""

from __future__ import annotations

from pathlib import Path  # noqa: F401  (used in type annotations)

import pytest

# evaluate_vv4_d performs its own cross-skill sys.path injection for
# `_explore_parser` (see gvm_verdict.py); tests do not need to set it up.
from gvm_verdict import evaluate_vv4_d


# ----------------------------------------------------------- fixture builders


def _frontmatter() -> str:
    return "---\nschema_version: 1\n---\n"


def _charter_block(runner: str = "gerard") -> str:
    return (
        "## Charter\n\n"
        "```yaml\n"
        "schema_version: 1\n"
        "session_id: explore-001\n"
        f"runner: {runner}\n"
        "mission: probe sort\n"
        "timebox_minutes: 60\n"
        "target: /report\n"
        "tour: data\n"
        "```\n"
    )


def _session_log() -> str:
    return "\n## Session Log\n\n- 09:00 — start\n"


def _defect_block(
    did: str = "D-1",
    severity: str = "Critical",
    title: str = "Sort dies on numeric column",
    stub_path: str | None = None,
) -> str:
    block = (
        f"### {did}: {title}\n"
        f"**Severity:** {severity}\n"
        "**Tour:** data\n"
        "**Given** a table with numbers\n"
        "**When** sort is clicked\n"
        "**Then** rows reorder by score\n"
        "**Reproduction:**\n"
        "1. Load /report\n"
        "2. Click Sort\n"
        "3. Observe: column is unsorted\n"
    )
    if stub_path is not None:
        block += f"**Stub-path:** {stub_path}\n"
    return block


def _defects_section(*defect_blocks: str) -> str:
    body = "\n## Defects\n\n"
    if not defect_blocks:
        return body
    return body + "\n".join(defect_blocks)


def _observations_empty() -> str:
    return "\n## Observations\n\n"


def _overall() -> str:
    return "\n## Overall Assessment\n\nAll good.\n"


def _write_report(test_dir: Path, nnn: str, body: str) -> Path:
    test_dir.mkdir(parents=True, exist_ok=True)
    p = test_dir / f"explore-{nnn}.md"
    p.write_text(body, encoding="utf-8")
    return p


def _make_full_report(
    *,
    runner: str = "gerard",
    defect_blocks: tuple[str, ...] = (),
) -> str:
    """Keyword-only signature so a defect-block string cannot be silently
    bound to `runner` by a caller who omitted the runner argument."""
    return (
        _frontmatter()
        + _charter_block(runner=runner)
        + _session_log()
        + _defects_section(*defect_blocks)
        + _observations_empty()
        + _overall()
    )


def _write_stubs(stubs_path: Path, paths: list[str]) -> None:
    """Minimal valid STUBS.md for the stubs parser (cross-cutting ADR-004)."""
    today = "2099-12-31"
    rows = []
    for p in paths:
        rows.append(
            f"| {p} | reason placeholder text | unknown | gerard | {today} |"
        )
    content = (
        "---\nschema_version: 1\n---\n"
        "# Stubs\n\n"
        "| Path | Reason | Real-provider Plan | Owner | Expiry |\n"
        "|---|---|---|---|---|\n"
        + "\n".join(rows)
        + "\n"
    )
    stubs_path.write_text(content, encoding="utf-8")


# ----------------------------------------------------------- TC-ET-5-01


def test_critical_in_non_stub_path_fails(tmp_path):
    test_dir = tmp_path / "test"
    body = _make_full_report(
        defect_blocks=(_defect_block(severity="Critical", stub_path=None),)
    )
    _write_report(test_dir, "001", body)

    status, evidence = evaluate_vv4_d(test_dir, stubs_path=None)
    assert status == "FAIL"
    assert "Critical" in evidence
    assert "explore-001" in evidence


# ----------------------------------------------------------- TC-ET-5-02


def test_critical_in_registered_stub_path_passes(tmp_path):
    test_dir = tmp_path / "test"
    stubs_path = tmp_path / "STUBS.md"
    _write_stubs(stubs_path, ["stubs/sorter.py"])

    body = _make_full_report(
        defect_blocks=(
            _defect_block(severity="Critical", stub_path="stubs/sorter.py"),
        )
    )
    _write_report(test_dir, "001", body)

    status, evidence = evaluate_vv4_d(test_dir, stubs_path=stubs_path)
    assert status == "PASS"
    # evidence should explain why — zero non-stub Criticals
    assert "0" in evidence or "no" in evidence.lower()


# ----------------------------------------------------------- TC-ET-5-04 (gap-tolerant ordering)


def test_highest_nnn_wins_with_gap(tmp_path):
    """`explore-001.md` Critical, `explore-003.md` clean, no `002` — pass."""
    test_dir = tmp_path / "test"
    _write_report(
        test_dir,
        "001",
        _make_full_report(
            defect_blocks=(_defect_block(severity="Critical", stub_path=None),)
        ),
    )
    _write_report(test_dir, "003", _make_full_report())

    status, evidence = evaluate_vv4_d(test_dir, stubs_path=None)
    assert status == "PASS"
    assert "explore-003" in evidence


def test_highest_nnn_wins_critical_in_latest(tmp_path):
    """Inverse: `explore-001.md` clean, `explore-003.md` Critical — fail."""
    test_dir = tmp_path / "test"
    _write_report(test_dir, "001", _make_full_report())
    _write_report(
        test_dir,
        "003",
        _make_full_report(
            defect_blocks=(_defect_block(severity="Critical", stub_path=None),)
        ),
    )

    status, evidence = evaluate_vv4_d(test_dir, stubs_path=None)
    assert status == "FAIL"
    assert "explore-003" in evidence


# ----------------------------------------------------------- ADR-207 unassigned runner


def test_unassigned_runner_passes_with_warning(tmp_path):
    test_dir = tmp_path / "test"
    # Charter validator rejects empty defects + unassigned-runner combination
    # only at charter creation; the report file may legitimately have an empty
    # defects section under ADR-207. The parser sets runner=None when the
    # charter says "unassigned".
    body = _make_full_report(runner="unassigned")
    _write_report(test_dir, "001", body)

    status, evidence = evaluate_vv4_d(test_dir, stubs_path=None)
    assert status == "PASS"
    assert "unassigned" in evidence.lower()
    assert "warning" in evidence.lower() or "et-7" in evidence.lower()


# ----------------------------------------------------------- no charters


def test_no_test_dir_fails(tmp_path):
    """Per spec Error Handling: no charters → Ship-ready not warranted."""
    missing = tmp_path / "test"
    status, evidence = evaluate_vv4_d(missing, stubs_path=None)
    assert status == "FAIL"
    assert "no charter" in evidence.lower() or "no explore" in evidence.lower()


def test_empty_test_dir_fails(tmp_path):
    test_dir = tmp_path / "test"
    test_dir.mkdir()
    status, evidence = evaluate_vv4_d(test_dir, stubs_path=None)
    assert status == "FAIL"
    assert "no charter" in evidence.lower() or "no explore" in evidence.lower()


# ----------------------------------------------------------- malformed report


def test_malformed_report_fails_with_evidence(tmp_path):
    test_dir = tmp_path / "test"
    test_dir.mkdir()
    (test_dir / "explore-001.md").write_text("not a valid report\n", encoding="utf-8")

    status, evidence = evaluate_vv4_d(test_dir, stubs_path=None)
    assert status == "FAIL"
    # evidence names the parse error or the file
    assert "explore-001" in evidence or "parse" in evidence.lower()


# ----------------------------------------------------------- non-Critical defects


def test_only_important_defect_passes(tmp_path):
    test_dir = tmp_path / "test"
    _write_report(
        test_dir,
        "001",
        _make_full_report(
            defect_blocks=(_defect_block(severity="Important", stub_path=None),)
        ),
    )
    status, evidence = evaluate_vv4_d(test_dir, stubs_path=None)
    assert status == "PASS"


def test_only_minor_defect_passes(tmp_path):
    test_dir = tmp_path / "test"
    _write_report(
        test_dir,
        "001",
        _make_full_report(
            defect_blocks=(_defect_block(severity="Minor", stub_path=None),)
        ),
    )
    status, evidence = evaluate_vv4_d(test_dir, stubs_path=None)
    assert status == "PASS"


# ----------------------------------------------------------- mixed defects


def test_mixed_critical_one_in_stub_one_out_fails(tmp_path):
    test_dir = tmp_path / "test"
    stubs_path = tmp_path / "STUBS.md"
    _write_stubs(stubs_path, ["stubs/sorter.py"])
    body = _make_full_report(
        defect_blocks=(
            _defect_block(did="D-1", severity="Critical", stub_path="stubs/sorter.py"),
            _defect_block(did="D-2", severity="Critical", stub_path=None),
        )
    )
    _write_report(test_dir, "001", body)
    status, evidence = evaluate_vv4_d(test_dir, stubs_path=stubs_path)
    assert status == "FAIL"
    assert "D-2" in evidence or "1" in evidence  # at least one non-stub Critical


def test_zero_defects_passes(tmp_path):
    test_dir = tmp_path / "test"
    _write_report(test_dir, "001", _make_full_report())
    status, evidence = evaluate_vv4_d(test_dir, stubs_path=None)
    assert status == "PASS"


def test_four_digit_nnn_sorts_numerically(tmp_path):
    """If NNN ever exceeds three digits (beyond spec), the numeric key still
    selects the latest report. Lex-only sort would pick `explore-999.md` over
    `explore-1000.md`."""
    test_dir = tmp_path / "test"
    # Older charter — Critical defect
    _write_report(
        test_dir,
        "999",
        _make_full_report(
            defect_blocks=(_defect_block(severity="Critical", stub_path=None),)
        ),
    )
    # Newer charter — clean
    _write_report(test_dir, "1000", _make_full_report())

    status, evidence = evaluate_vv4_d(test_dir, stubs_path=None)
    assert status == "PASS"
    assert "explore-1000" in evidence


# ----------------------------------------------------------- stubs_path missing


def test_stub_path_supplied_but_stubs_md_missing_fails_safe(tmp_path):
    """If practitioner declares stub_path but STUBS.md doesn't exist, the
    parser sets in_stub_path=False (per ADR-206 — conservative). The Critical
    therefore counts → FAIL. Documents the safe-default branch."""
    test_dir = tmp_path / "test"
    body = _make_full_report(
        defect_blocks=(
            _defect_block(severity="Critical", stub_path="stubs/sorter.py"),
        )
    )
    _write_report(test_dir, "001", body)

    status, _ = evaluate_vv4_d(test_dir, stubs_path=None)
    assert status == "FAIL"  # in_stub_path=False when stubs_path is None


# ----------------------------------------------------------- return type


@pytest.mark.parametrize(
    "subdir,create",
    [
        ("missing", False),  # directory does not exist
        ("empty", True),     # directory exists but contains no explore-*.md
    ],
)
def test_return_shape_is_tuple_str_str(tmp_path, subdir, create):
    test_dir = tmp_path / subdir
    if create:
        test_dir.mkdir()
    result = evaluate_vv4_d(test_dir, stubs_path=None)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert result[0] in ("PASS", "FAIL")
    assert isinstance(result[1], str)
    assert result[1]  # non-empty


# ----------------------------------------------------------- R24 S-1: stubs_path supplied but file missing
#
# The "fail safe" behaviour for absent STUBS.md must apply whether the path
# is `None` (caller signals no stubs in scope) OR provided-but-absent
# (caller expected stubs but the file is gone). Both must FAIL on a Critical
# in a stubs/ path so we never silently let a defect through because the
# audit trail file vanished.


def test_stubs_path_provided_but_file_missing_fails_safe(tmp_path):
    test_dir = tmp_path / "test"
    _write_report(
        test_dir,
        "001",
        _make_full_report(
            defect_blocks=(
                _defect_block(severity="Critical", stub_path="stubs/sorter.py"),
            )
        ),
    )
    missing_stubs = tmp_path / "does-not-exist-STUBS.md"
    assert not missing_stubs.exists()

    status, evidence = evaluate_vv4_d(test_dir, stubs_path=missing_stubs)
    # The contract: a missing stubs file MUST NOT silently allow a Critical
    # through. The current evaluator surfaces this as a parse-error-flavoured
    # FAIL (the parse fails when load_stubs is called with a non-existent
    # path). Either path is acceptable as long as the verdict is FAIL and
    # the missing-file cause is named in evidence.
    assert status == "FAIL"
    assert evidence  # non-empty
    assert (
        "Critical" in evidence
        or "D-001" in evidence
        or "STUBS" in evidence
        or "stubs" in evidence
    )
