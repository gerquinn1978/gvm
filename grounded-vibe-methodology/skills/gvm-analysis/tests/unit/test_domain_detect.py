"""Unit tests for ``_shared/domain_detect.py`` (ADR-105)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from _shared import domain_detect as dd


def _write_industry(
    dir_path: Path,
    *,
    filename: str,
    domain: str,
    activation: list[str],
    strong: list[str] | None = None,
) -> Path:
    frontmatter_lines = [
        "---",
        f"domain_name: {domain}",
        "activation_signals:",
        *[f"  - {s}" for s in activation],
    ]
    if strong:
        frontmatter_lines.append("strong_signals:")
        frontmatter_lines.extend([f"  - {s}" for s in strong])
    frontmatter_lines.append("---")
    frontmatter_lines.append("")
    frontmatter_lines.append("# Body")
    (dir_path / filename).write_text("\n".join(frontmatter_lines))
    return dir_path / filename


@pytest.fixture()
def credit_risk_dir(tmp_path):
    _write_industry(
        tmp_path,
        filename="credit-risk.md",
        domain="credit_risk",
        activation=["pd_pit", "pd_ttc", "lgd", "ead", "default_indicator"],
        strong=["rwa", "basel_iii"],
    )
    return tmp_path


# ---------------------------------------------------------------------------
# TC-AN-6-01 + TC-AN-6-02
# ---------------------------------------------------------------------------


def test_tc_an_6_01_credit_risk_match(credit_risk_dir):
    result = dd.detect(
        ["borrower_id", "loan_amount", "pd_pit", "lgd", "fico_score"],
        industry_dir=credit_risk_dir,
    )
    assert result["matched"] == "credit_risk"


def test_tc_an_6_02_signals_include_matching_columns(credit_risk_dir):
    result = dd.detect(
        ["borrower_id", "loan_amount", "pd_pit", "lgd", "fico_score"],
        industry_dir=credit_risk_dir,
    )
    assert "pd_pit" in result["signals"]
    assert "lgd" in result["signals"]
    assert len(result["signals"]) >= 2


def test_single_activation_signal_not_enough(credit_risk_dir):
    """A single activation signal should NOT confirm a match."""
    result = dd.detect(
        ["borrower_id", "loan_amount", "pd_pit", "fico_score"],
        industry_dir=credit_risk_dir,
    )
    assert result["matched"] is None


def test_strong_signal_single_match_confirms(credit_risk_dir):
    """A single `strong_signals` hit confirms the match."""
    result = dd.detect(
        ["borrower_id", "rwa"],  # rwa is strong
        industry_dir=credit_risk_dir,
    )
    assert result["matched"] == "credit_risk"
    assert result["signals"] == ["rwa"]


# ---------------------------------------------------------------------------
# TC-AN-8-01 unidentifiable
# ---------------------------------------------------------------------------


def test_tc_an_8_01_unidentifiable(credit_risk_dir):
    result = dd.detect(
        ["x", "y", "z", "value_1", "value_2"], industry_dir=credit_risk_dir
    )
    assert result["matched"] is None
    assert result["candidate_domain"] is None
    assert result["signals"] == []


# ---------------------------------------------------------------------------
# TC-AN-7-01 identifiable-but-no-file candidate
# ---------------------------------------------------------------------------


def test_tc_an_7_01_clinical_candidate_no_file(credit_risk_dir):
    # No clinical industry file, but clinical-signal columns present
    result = dd.detect(
        ["patient_id", "hba1c", "ldl", "triglycerides", "creatinine"],
        industry_dir=credit_risk_dir,
    )
    assert result["matched"] is None
    assert result["candidate_domain"] == "clinical"


# ---------------------------------------------------------------------------
# Malformed frontmatter
# ---------------------------------------------------------------------------


def test_missing_domain_name_skipped_with_warning(tmp_path, capsys):
    (tmp_path / "bad.md").write_text("---\nactivation_signals:\n  - foo\n---\n")
    result = dd.detect(["foo"], industry_dir=tmp_path)
    assert result["matched"] is None
    assert "skipping malformed industry file" in capsys.readouterr().err


def test_missing_activation_signals_skipped_with_warning(tmp_path, capsys):
    (tmp_path / "bad.md").write_text("---\ndomain_name: x\n---\n")
    result = dd.detect(["foo"], industry_dir=tmp_path)
    assert result["matched"] is None
    assert "skipping malformed industry file" in capsys.readouterr().err


def test_empty_activation_signals_skipped_with_warning(tmp_path, capsys):
    (tmp_path / "bad.md").write_text(
        "---\ndomain_name: x\nactivation_signals: []\n---\n"
    )
    result = dd.detect(["foo"], industry_dir=tmp_path)
    assert result["matched"] is None
    assert "skipping malformed industry file" in capsys.readouterr().err


def test_no_frontmatter_skipped_with_warning(tmp_path, capsys):
    (tmp_path / "narrative.md").write_text("# Just narrative\nNo frontmatter.\n")
    result = dd.detect(["foo"], industry_dir=tmp_path)
    assert result["matched"] is None
    assert "skipping malformed industry file" in capsys.readouterr().err


def test_malformed_file_does_not_block_match_in_sibling_file(tmp_path, capsys):
    """A broken credit-risk.md must not stop a market_risk match in market-risk.md."""
    (tmp_path / "broken.md").write_text("# no frontmatter\n")
    _write_industry(
        tmp_path,
        filename="market-risk.md",
        domain="market_risk",
        activation=["var", "delta", "pnl"],
    )
    result = dd.detect(["trade_id", "var", "delta"], industry_dir=tmp_path)
    assert result["matched"] == "market_risk"
    assert "skipping malformed industry file" in capsys.readouterr().err


def test_parse_industry_file_still_raises_for_direct_callers(tmp_path):
    """The low-level parser keeps the strict contract — only the loader skips."""
    bad = tmp_path / "bad.md"
    bad.write_text("# no frontmatter\n")
    with pytest.raises(dd.MalformedIndustryFileError):
        dd._parse_industry_file(bad)


# ---------------------------------------------------------------------------
# Case insensitivity
# ---------------------------------------------------------------------------


def test_case_insensitive_match(credit_risk_dir):
    result = dd.detect(["Borrower_Id", "PD_PIT", "LGD"], industry_dir=credit_risk_dir)
    assert result["matched"] == "credit_risk"
    # Original-case echo preserved in signals output.
    assert "PD_PIT" in result["signals"]
    assert "LGD" in result["signals"]


def test_whitespace_padded_columns_match(credit_risk_dir):
    result = dd.detect(["  PD_PIT  ", " lgd"], industry_dir=credit_risk_dir)
    assert result["matched"] == "credit_risk"
    # Original (padded) spelling echoed back.
    assert "  PD_PIT  " in result["signals"]


def test_duplicate_normalised_columns_use_first_spelling(credit_risk_dir):
    result = dd.detect(["PD_PIT", "pd_pit", "LGD"], industry_dir=credit_risk_dir)
    assert result["matched"] == "credit_risk"
    assert "PD_PIT" in result["signals"]
    assert "pd_pit" not in result["signals"]


def test_bom_prefixed_industry_file_parses(tmp_path):
    (tmp_path / "credit-risk.md").write_text(
        "\ufeff---\ndomain_name: credit_risk\nactivation_signals:\n  - pd_pit\n  - lgd\n---\n",
        encoding="utf-8",
    )
    result = dd.detect(["pd_pit", "lgd"], industry_dir=tmp_path)
    assert result["matched"] == "credit_risk"


def test_null_strong_signals_parses_as_empty(tmp_path):
    (tmp_path / "x.md").write_text(
        "---\ndomain_name: x\nactivation_signals:\n  - a\n  - b\nstrong_signals: null\n---\n"
    )
    result = dd.detect(["a", "b"], industry_dir=tmp_path)
    assert result["matched"] == "x"


def test_non_list_strong_signals_skipped_with_warning(tmp_path, capsys):
    (tmp_path / "bad.md").write_text(
        "---\ndomain_name: x\nactivation_signals:\n  - a\nstrong_signals: just_a_string\n---\n"
    )
    result = dd.detect(["a"], industry_dir=tmp_path)
    assert result["matched"] is None
    assert "strong_signals" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Deterministic ordering
# ---------------------------------------------------------------------------


def test_deterministic_first_match_when_two_domains_fit(tmp_path):
    _write_industry(
        tmp_path,
        filename="alpha.md",
        domain="alpha_domain",
        activation=["shared_a", "shared_b"],
    )
    _write_industry(
        tmp_path,
        filename="beta.md",
        domain="beta_domain",
        activation=["shared_a", "shared_b"],
    )
    result = dd.detect(["shared_a", "shared_b"], industry_dir=tmp_path)
    # Sorted directory order — "alpha.md" comes first
    assert result["matched"] == "alpha_domain"


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------


def test_cli_emits_expected_json_schema(tmp_path, credit_risk_dir):
    csv = tmp_path / "input.csv"
    csv.write_text("borrower_id,pd_pit,lgd,fico_score\n1,0.05,0.4,720\n")

    skill_root = Path(__file__).resolve().parents[2]
    script = skill_root / "scripts" / "domain_detect_cli.py"
    env_src = skill_root / "scripts"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(env_src) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--input",
            str(csv),
            "--industry-dir",
            str(credit_risk_dir),
        ],
        capture_output=True,
        text=True,
        cwd=str(skill_root),
        env=env,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert set(payload.keys()) == {"matched", "signals", "candidate_domain"}
    assert payload["matched"] == "credit_risk"
