"""Structural assertions for SKILL.md (P5-C01).

These tests enforce ADR-101 / ADR-102 / ADR-103 at the document level:
- the four modes are named verbatim (TC-AN-1-01)
- Decompose prompts for a target column (TC-AN-1-02)
- Validate requires a baseline (TC-AN-1-03)
- no hardcoded industry-formula names (TC-AN-25-02)
- no inline statistical methodology (ADR-101 drive/do-work split)
- the ADR-102 AskUserQuestion steps appear in order
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from _shared.methodology import JARGON_FORBIDDEN

SKILL_ROOT = Path(__file__).resolve().parents[2]
SKILL_MD = SKILL_ROOT / "SKILL.md"


def _section(skill_text: str, heading: str) -> str:
    """Return the body of a `### N. Name` section, or '' if absent."""
    pattern = rf"(?is)###\s+{re.escape(heading)}\s*(.+?)(?=\n###\s+\d|\Z)"
    match = re.search(pattern, skill_text)
    return match.group(1) if match else ""


INDUSTRY_FORMULA_NAMES = ("VaR", "RWA", "NPV", "FICO", "Black-Scholes", "CVaR")

MODE_NAMES = ("Explore", "Decompose", "Validate", "Not sure — run everything")


@pytest.fixture(scope="module")
def skill_text() -> str:
    assert SKILL_MD.exists(), f"SKILL.md missing at {SKILL_MD}"
    return SKILL_MD.read_text(encoding="utf-8")


def test_skill_md_exists() -> None:
    assert SKILL_MD.exists(), f"SKILL.md must exist at {SKILL_MD}"


def test_skill_md_has_frontmatter(skill_text: str) -> None:
    assert skill_text.startswith("---\n"), "SKILL.md must start with YAML frontmatter"
    end = skill_text.find("\n---\n", 4)
    assert end > 0, "SKILL.md frontmatter must be closed with ---"
    front = skill_text[4:end]
    assert re.search(r"^name:\s*gvm-analysis\s*$", front, re.MULTILINE), (
        "frontmatter must declare name: gvm-analysis"
    )
    assert re.search(r"^description:\s*\S", front, re.MULTILINE), (
        "frontmatter must declare a non-empty description"
    )


def test_tc_an_1_01_all_four_modes_named_verbatim(skill_text: str) -> None:
    # TC-AN-1-01: mode-selection AskUserQuestion (step 2) lists exactly four
    # option labels. Scope the check to the Mode selection section so that
    # the Modes overview table alone cannot satisfy it.
    match = re.search(
        r"(?is)###\s+2\.\s*Mode\s+selection\s*(.+?)(?=\n###\s+\d)",
        skill_text,
    )
    assert match, "Mode selection (step 2) section missing from SKILL.md"
    step_2 = match.group(1)
    assert "AskUserQuestion" in step_2, "Step 2 must name AskUserQuestion explicitly"
    for mode in MODE_NAMES:
        assert mode in step_2, (
            f"mode name '{mode}' missing from step 2 AskUserQuestion block"
        )


def test_tc_an_1_02_decompose_prompts_for_target_column(skill_text: str) -> None:
    # TC-AN-1-02: Decompose mode references a target-column AskUserQuestion.
    lower = skill_text.lower()
    assert "target column" in lower, "Decompose flow must reference 'target column'"
    assert "askuserquestion" in lower, "Decompose step must use AskUserQuestion"


def test_tc_an_1_03_validate_requires_baseline(skill_text: str) -> None:
    # TC-AN-1-03: Validate mode names baseline-file requirement.
    lower = skill_text.lower()
    assert "baseline" in lower, "Validate flow must reference a baseline file"
    # Must mention that a single-file invocation + Validate prompts for baseline.
    assert re.search(r"validate", lower), "SKILL.md must describe Validate mode"


def test_tc_an_25_02_no_hardcoded_industry_formulas(skill_text: str) -> None:
    # TC-AN-25-02: skill body must not hardcode industry-formula names.
    for name in INDUSTRY_FORMULA_NAMES:
        assert name not in skill_text, (
            f"SKILL.md contains hardcoded industry-formula name '{name}' "
            f"(violates TC-AN-25-02 / AN-25 / C-3)"
        )


def test_no_inline_statistical_methodology(skill_text: str) -> None:
    """ADR-101: methodology lives in Python, not in SKILL.md.

    Uses _shared.methodology.JARGON_FORBIDDEN as the single source of truth
    (per ADR-211 post-R4 CRITICAL-T50), narrowed by:

    - Word-boundary matching: "Bootstrap GVM home" / "summarise" are English,
      not the statistical bootstrap / MAR jargon the frozenset targets.
    - Spec-mandated allowlist: ADR-102 step 11 requires naming forecast
      methods (`linear`, `ARIMA`, `exponential smoothing`) as user-facing
      AskUserQuestion option labels. These are choices, not methodology prose.
    """
    # ADR-102 step 11 mandates naming forecast methods as AskUserQuestion
    # option labels: `linear`, `ARIMA`, `exponential smoothing`. Only `arima`
    # is in JARGON_FORBIDDEN; the other two are not, so no other exemption
    # is needed. A narrow allowlist here keeps the gate strict.
    USER_FACING_METHOD_LABELS = {"arima"}
    lower = skill_text.lower()
    leaked = []
    for term in JARGON_FORBIDDEN:
        if term in USER_FACING_METHOD_LABELS:
            continue
        # Word-boundary match to reject substring false positives
        # (e.g., "bootstrap" inside "Bootstrap GVM home directory", or
        # "mar" inside "summarise").
        if re.search(rf"\b{re.escape(term)}\b", lower):
            leaked.append(term)
    assert not leaked, (
        f"SKILL.md contains inline statistical methodology terms {leaked}; "
        f"methodology belongs in Python (ADR-101)"
    )


def test_askuserquestion_sequence_ordered(skill_text: str) -> None:
    """ADR-102 process steps must appear in order in SKILL.md."""
    # Locate each step marker by its numeric prefix. Tolerate minor
    # formatting variation (e.g. "Step 0", "0.", "## 0 —").
    expected = [
        "dependency check",  # 0
        "mode selection",  # 2
        "multi-sheet",  # 3
        "multi-file",  # 4
        "domain detection",  # 5
        "preferences",  # 6
        "sampling",  # 7
        "multi-datetime",  # 7b
        "target column",  # 8
        "baseline",  # 9
        "engine invocation",  # 10
        "forecast offer",  # 11
        "re-invoke engine",  # 12
        "render report",  # 13
        "present report",  # 14
    ]
    lower = skill_text.lower()
    last = -1
    for label in expected:
        idx = lower.find(label, last + 1)
        assert idx > last, (
            f"step '{label}' must appear after prior step in SKILL.md (ADR-102 order)"
        )
        last = idx


def test_bash_invocation_template_present(skill_text: str) -> None:
    assert "python3 scripts/analyse.py" in skill_text, (
        "SKILL.md must contain the bash invocation template for analyse.py"
    )


def test_hard_gates_section_present(skill_text: str) -> None:
    assert re.search(r"(?im)^##\s+hard\s+gates\b", skill_text), (
        "SKILL.md must declare a Hard Gates section (ADR-101)"
    )


def test_privacy_boundary_hard_gate(skill_text: str) -> None:
    lower = skill_text.lower()
    # ASR-1: Claude orchestrates but never reads raw rows.
    assert "privacy" in lower, "Hard Gates must name the privacy boundary (ASR-1/AN-4)"
    assert "raw" in lower or "never sees" in lower, (
        "Hard Gates must state Claude never reads raw data (ASR-1/NFR-1)"
    )


def test_step_0_names_check_deps_script(skill_text: str) -> None:
    body = _section(skill_text, "0. Dependency check (blocking)")
    assert "_check_deps.py" in body, (
        "step 0 must invoke scripts/_check_deps.py (ADR-106)"
    )
    assert "python3" in body, "step 0 must use python3 for Bash dispatch"


def test_step_0_specifies_verbatim_stderr_passthrough(skill_text: str) -> None:
    body = _section(skill_text, "0. Dependency check (blocking)").lower()
    assert "verbatim" in body, (
        "step 0 must instruct verbatim stderr passthrough (ADR-106, ADR-107)"
    )
    assert "exit" in body, (
        "step 0 must branch on the dep-check exit code, not on parsed stderr"
    )


def test_step_0_documents_advisory_path(skill_text: str) -> None:
    body = _section(skill_text, "0. Dependency check (blocking)")
    assert "ADVISORY" in body, (
        "step 0 must describe the optional-packages advisory path "
        "(exit 0 with stderr notice)"
    )


def test_step_10_names_bash_template(skill_text: str) -> None:
    body = _section(skill_text, "10. Engine invocation")
    assert "Bash Invocation Template" in body, (
        "step 10 must point at the single Bash Invocation Template section"
    )
    assert "findings.json" in body, (
        "step 10 must name findings.json as the only privacy-cleared output"
    )


def test_step_10_forbids_claude_reading_input(skill_text: str) -> None:
    body = _section(skill_text, "10. Engine invocation").lower()
    # ASR-1 / AN-4: Claude cannot touch raw rows.
    assert re.search(r"\b(must not|may not|never|under no circumstances)\b", body), (
        "step 10 must carry an explicit prohibition against reading raw data"
    )
    assert "input" in body, (
        "step 10 must explicitly forbid reading the user's input file"
    )


def test_step_5_invokes_domain_detect_cli(skill_text: str) -> None:
    body = _section(skill_text, "5. Domain detection")
    assert "domain_detect_cli.py" in body, (
        "step 5 must invoke scripts/domain_detect_cli.py (ADR-105 post-R4 CRITICAL-T20)"
    )
    assert "python3" in body
    assert "--input" in body, "step 5 must show the --input flag (repeatable per file)"


def test_step_5_names_json_contract_keys(skill_text: str) -> None:
    body = _section(skill_text, "5. Domain detection")
    for key in ("matched", "signals", "candidate_domain"):
        assert key in body, (
            f"step 5 must reference stdout JSON key '{key}' (ADR-105 exact contract)"
        )


def test_step_5_covers_all_four_branches(skill_text: str) -> None:
    body = _section(skill_text, "5. Domain detection").lower()
    # (a) matched path — loads industry file
    assert "domain detected" in body, (
        "step 5 must announce 'Domain detected' on match (ADR-105)"
    )
    assert "industry" in body, "step 5 must reference the industry/ reference directory"
    # (b) identifiable but no file — Expert Discovery (shared rule 2)
    assert "expert discovery" in body, (
        "step 5 must offer Expert Discovery for identifiable-but-no-file case"
    )
    # (c) unidentifiable — general-purpose fallback
    assert "general-purpose" in body or "general purpose" in body, (
        "step 5 must name the general-purpose fallback for unidentifiable domains"
    )
    # (d) --domain override (AN-9)
    assert "--domain" in body, "step 5 must document the --domain override (AN-9)"


def test_step_5_stderr_passthrough_on_failure(skill_text: str) -> None:
    body = _section(skill_text, "5. Domain detection").lower()
    assert "verbatim" in body, (
        "step 5 must instruct verbatim stderr passthrough on non-zero exit"
    )


def test_step_5_override_refuses_missing_file(skill_text: str) -> None:
    body = _section(skill_text, "5. Domain detection").lower()
    # AN-9: if --domain names a file that does not exist, fail with a
    # diagnostic listing available industry files.
    assert "available" in body or "list" in body, (
        "step 5 must describe what happens when --domain names a missing file"
    )
    # Regression guard: the override path bypasses the CLI, so the missing-
    # file diagnostic cannot source its file list from CLI stderr. The prose
    # must name a concrete source for the list — the industry/ directory
    # itself.
    assert "directory" in body or "contents of" in body, (
        "step 5 override path must name a concrete source for 'available "
        "domains' (the industry/ directory), since the CLI is bypassed"
    )


def test_step_6_invokes_prefs_cli(skill_text: str) -> None:
    body = _section(skill_text, "6. Preferences load / customise")
    assert "prefs_cli.py" in body, "step 6 must dispatch scripts/prefs_cli.py"
    assert "python3" in body
    assert "load" in body and "save" in body, (
        "step 6 must cite both `load` and `save` subcommands"
    )


def test_step_6_names_canonical_path(skill_text: str) -> None:
    body = _section(skill_text, "6. Preferences load / customise")
    assert "~/.claude/gvm/analysis/preferences.yaml" in body, (
        "step 6 must name the canonical prefs path"
    )


def test_step_6_covers_state_machine_branches(skill_text: str) -> None:
    body = _section(skill_text, "6. Preferences load / customise").lower()
    # Missing file → customise yes/no
    assert "does not exist" in body or "missing" in body
    assert "customise preferences" in body or "customize preferences" in body
    assert "shipped defaults" in body
    # Exists → edit yes/no
    assert "edit preferences" in body
    assert "use loaded preferences" in body or "as-is" in body
    # Migration announcement
    assert "warnings" in body or "an-44" in body


def test_step_6_forbids_direct_yaml_read(skill_text: str) -> None:
    body = _section(skill_text, "6. Preferences load / customise").lower()
    # The prose must explicitly route through the CLI, not `Read`.
    assert "never" in body or "do not" in body, (
        "step 6 must forbid direct YAML Read and route everything via the CLI"
    )


def test_step_6_exit_codes_documented(skill_text: str) -> None:
    body = _section(skill_text, "6. Preferences load / customise")
    # Must list the four non-zero exit codes the CLI emits so the skill can branch.
    for code in ("1", "2", "3", "4"):
        assert code in body, f"step 6 must document exit code {code}"


# ---------------------------------------------------------------------------
# Step 11 — Forecast offer (P5-C05 / ADR-108)
# ---------------------------------------------------------------------------


def test_step_11_names_nested_field_paths(skill_text: str) -> None:
    body = _section(skill_text, "11. Forecast offer")
    # ADR-108 post-C1 fix: flat paths do NOT exist. Nested paths are
    # load-bearing — a typo silently evaluates falsy and the offer never fires.
    assert "time_series.trend.significant" in body, (
        "step 11 must cite the nested field path `time_series.trend.significant`"
    )
    assert "time_series.seasonality.strength" in body, (
        "step 11 must cite the nested field path `time_series.seasonality.strength`"
    )
    # Explicitly forbid the flat variants — regression guard against C1.
    assert "trend_significant" not in body, (
        "step 11 must NOT use the flat path `trend_significant` (does not exist)"
    )
    assert "seasonality_strength" not in body, (
        "step 11 must NOT use the flat path `seasonality_strength` (does not exist)"
    )


def test_step_11_cites_null_guard(skill_text: str) -> None:
    body = _section(skill_text, "11. Forecast offer").lower()
    # HIGH-T28 post-R4 fix: guard must be explicit, else TypeError on
    # non-temporal data.
    assert (
        "is not none" in body or "not null" in body or "time_series exists" in body
    ), "step 11 must state the `time_series is not None` guard (HIGH-T28)"


def test_step_11_threshold_comes_from_preferences(skill_text: str) -> None:
    body = _section(skill_text, "11. Forecast offer")
    assert "seasonal_strength_threshold" in body, (
        "step 11 must name `seasonal_strength_threshold` as the comparator "
        "(TC-AN-22-08 — thresholds are user-overridable via preferences)"
    )
    # The prefs-derived threshold must be compared against, not a hardcoded literal.
    # 0.6 is the shipped default; it must not appear as an inline literal in the
    # comparison prose (it may still appear in an explanatory note referencing the default).
    # We assert the pref key is cited; literal 0.6 is allowed only if the pref key is also cited.
    assert "preferences" in body.lower() or "$PREFS" in body, (
        "step 11 must route the threshold through the preferences object"
    )


def test_step_11_lists_methods_and_skip(skill_text: str) -> None:
    body = _section(skill_text, "11. Forecast offer")
    # TC-AN-22-01: offer names the three methods verbatim.
    assert "linear" in body
    assert "ARIMA" in body
    assert "exponential smoothing" in body.lower()
    # TC-AN-22-05: off by default — Skip option must be explicit.
    assert "Skip" in body or "skip" in body
    # Forecast option must be present (it's the offer).
    assert "Forecast" in body


def test_step_11_restates_input_privacy(skill_text: str) -> None:
    # ASR-1 / AN-4 / NFR-1: orchestration reads findings.json only, never the
    # input file. Re-stated on both Skip and Forecast branches so a reader
    # following either path sees the boundary.
    body = _section(skill_text, "11. Forecast offer").lower()
    prohibition = re.search(
        r"\b(must not|may not|never|under no circumstances)\b", body
    )
    assert prohibition is not None, (
        "step 11 must explicitly prohibit reading the input file (ASR-1/AN-4/NFR-1)"
    )


# ---------------------------------------------------------------------------
# Step 12 — Re-invoke engine for forecast (P5-C05 / ADR-108)
# ---------------------------------------------------------------------------


def test_step_12_invokes_forecast_only(skill_text: str) -> None:
    body = _section(skill_text, "12. Re-invoke engine for forecast")
    assert "analyse.py" in body
    assert "--forecast-only" in body, (
        "step 12 must invoke `analyse.py --forecast-only` (ADR-108 option 2)"
    )


def test_step_12_cites_findings_json_as_input(skill_text: str) -> None:
    body = _section(skill_text, "12. Re-invoke engine for forecast")
    # The forecast pass reads findings.json — never the original user input
    # (ASR-1 / ADR-108). The spec says `--in findings.json`; analyse.py's
    # argparse declares `--in-file`. SKILL.md follows the argparse reality.
    assert "findings.json" in body, (
        "step 12 must name findings.json as the forecast-pass input"
    )


def test_step_12_cites_atomic_write_protocol(skill_text: str) -> None:
    body = _section(skill_text, "12. Re-invoke engine for forecast").lower()
    # ADR-209: forecast pass patches findings.json in place via atomic write
    # (temp + rename). Readers must know findings.json is safe to re-read after
    # non-zero exit — the original is untouched.
    assert "atomic" in body or "temp" in body or "rename" in body, (
        "step 12 must cite the ADR-209 atomic-write protocol so readers know "
        "findings.json is patched in place safely"
    )


def test_step_12_documents_exit_code_handling(skill_text: str) -> None:
    body = _section(skill_text, "12. Re-invoke engine for forecast").lower()
    # Same discipline as step 10: branch by exit code, stderr verbatim on failure.
    assert "exit 0" in body or "exit code 0" in body, (
        "step 12 must document the exit-0 (proceed to render) branch"
    )
    assert "stderr" in body, "step 12 must document verbatim stderr on non-zero exit"


def test_step_12_forbids_reading_input_file(skill_text: str) -> None:
    # ASR-1 restatement: the forecast pass must not re-read the input file
    # either — findings.json is the only privacy-cleared channel.
    body = _section(skill_text, "12. Re-invoke engine for forecast").lower()
    prohibition = re.search(
        r"\b(must not|may not|never|under no circumstances)\b", body
    )
    assert prohibition is not None, (
        "step 12 must explicitly prohibit reading the input file (ASR-1/AN-4/NFR-1)"
    )


def test_step_12_proceeds_to_render(skill_text: str) -> None:
    # Completeness: after a successful forecast pass, orchestration proceeds
    # to step 13 (render). The prose must state the next state.
    body = _section(skill_text, "12. Re-invoke engine for forecast").lower()
    assert "render" in body or "step 13" in body, (
        "step 12 must state the next step (render) so the state machine is complete"
    )
