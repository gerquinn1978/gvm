"""Tests for ``scripts/anonymise.py`` (P14-C02).

Covers TC-AN-36-01 (format support), TC-AN-36-02 (categorical tokenisation),
TC-AN-36-03 (numeric pass-through), plus path-risk integration, numeric-
column refusal, pre-emptive TOK_ collision scan, and YAML config support.

Anonymisation-pipeline ADR-401 (CLI external to the skill), ADR-402
(categorical-only), ADR-403 (token format + collision check), ADR-404
(path validation).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


# --- TC-AN-36-02: categorical tokenisation (the central happy path) ---------


def _write_csv_three_dept(tmp_path: Path) -> Path:
    inp = tmp_path / "input.csv"
    pd.DataFrame(
        {
            "department": ["Engineering", "Sales", "HR"],
            "salary": [100, 120, 90],
        }
    ).to_csv(inp, index=False)
    return inp


def test_tc_an_36_02_categorical_replaced_with_column_prefixed_tokens(tmp_path):
    from scripts import anonymise

    inp = _write_csv_three_dept(tmp_path)
    out = tmp_path / "out.csv"
    mapping = tmp_path / "private" / "mapping.csv"

    rc = anonymise.main(
        [
            "--input",
            str(inp),
            "--output",
            str(out),
            "--cols",
            "department",
            "--mapping-out",
            str(mapping),
        ]
    )
    assert rc == 0

    df = pd.read_csv(out)
    assert df["department"].tolist() == [
        "TOK_department_001",
        "TOK_department_002",
        "TOK_department_003",
    ]

    mdf = pd.read_csv(mapping)
    assert list(mdf.columns) == ["column", "original_value", "token"]
    assert set(mdf["original_value"]) == {"Engineering", "Sales", "HR"}


# --- TC-AN-36-03: numeric pass-through --------------------------------------


def test_tc_an_36_03_numeric_columns_pass_through_byte_identical(tmp_path):
    from scripts import anonymise

    inp = tmp_path / "input.csv"
    pd.DataFrame(
        {
            "employee_name": ["Alice", "Bob", "Carol"],
            "salary": [100000, 95000, 110000],
            "bonus": [5000, 4500, 7500],
        }
    ).to_csv(inp, index=False)
    out = tmp_path / "out.csv"
    mapping = tmp_path / "private" / "mapping.csv"

    rc = anonymise.main(
        [
            "--input",
            str(inp),
            "--output",
            str(out),
            "--cols",
            "employee_name",
            "--mapping-out",
            str(mapping),
        ]
    )
    assert rc == 0

    df_in = pd.read_csv(inp)
    df_out = pd.read_csv(out)
    # employee_name was tokenised; salary + bonus are byte-identical.
    assert df_out["salary"].tolist() == df_in["salary"].tolist()
    assert df_out["bonus"].tolist() == df_in["bonus"].tolist()


# --- TC-AN-36-01: format round-trip across csv/parquet/xlsx/json -------------


@pytest.mark.parametrize(
    "suffix,reader",
    [
        ("csv", lambda p: pd.read_csv(p)),
        ("tsv", lambda p: pd.read_csv(p, sep="\t")),
        ("parquet", lambda p: pd.read_parquet(p)),
        ("xlsx", lambda p: pd.read_excel(p)),
        ("json", lambda p: pd.read_json(p, orient="records")),
    ],
)
def test_tc_an_36_01_format_round_trip(tmp_path, suffix, reader):
    from scripts import anonymise

    inp = tmp_path / f"input.{suffix}"
    df = pd.DataFrame(
        {
            "department": ["Engineering", "Sales", "Engineering"],
            "salary": [100, 120, 110],
        }
    )
    if suffix == "csv":
        df.to_csv(inp, index=False)
    elif suffix == "tsv":
        df.to_csv(inp, sep="\t", index=False)
    elif suffix == "parquet":
        df.to_parquet(inp, index=False)
    elif suffix == "xlsx":
        df.to_excel(inp, index=False)
    elif suffix == "json":
        df.to_json(inp, orient="records")

    out = tmp_path / f"out.{suffix}"
    mapping = tmp_path / "private" / "mapping.csv"

    rc = anonymise.main(
        [
            "--input",
            str(inp),
            "--output",
            str(out),
            "--cols",
            "department",
            "--mapping-out",
            str(mapping),
        ]
    )
    assert rc == 0
    out_df = reader(out)
    # Engineering appears twice → same token (TC-AN-36-04 stability).
    assert out_df["department"].iloc[0] == out_df["department"].iloc[2]
    assert out_df["department"].iloc[0].startswith("TOK_department_")
    assert mapping.exists()


# --- Numeric-column refusal -------------------------------------------------


def test_numeric_column_refused_with_diagnostic(tmp_path, capsys):
    from scripts import anonymise

    inp = tmp_path / "input.csv"
    pd.DataFrame({"salary": [100, 200], "name": ["A", "B"]}).to_csv(inp, index=False)
    out = tmp_path / "out.csv"
    mapping = tmp_path / "private" / "mapping.csv"

    rc = anonymise.main(
        [
            "--input",
            str(inp),
            "--output",
            str(out),
            "--cols",
            "salary",  # numeric — must be refused
            "--mapping-out",
            str(mapping),
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "salary" in err
    assert "numeric" in err.lower()
    assert not out.exists()
    assert not mapping.exists()


# --- Nullable / temporal dtype refusal --------------------------------------


@pytest.mark.parametrize(
    "dtype",
    ["Int64", "Float64", "UInt32"],
)
def test_pandas_nullable_numeric_refused(tmp_path, capsys, dtype):
    """Nullable extension dtypes (common in parquet) must be refused."""
    from scripts import anonymise

    inp = tmp_path / "input.parquet"
    df = pd.DataFrame(
        {
            "amount": pd.array([1, 2, None], dtype=dtype),
            "name": ["A", "B", "C"],
        }
    )
    df.to_parquet(inp, index=False)
    out = tmp_path / "out.parquet"
    mapping = tmp_path / "private" / "mapping.csv"

    rc = anonymise.main(
        [
            "--input",
            str(inp),
            "--output",
            str(out),
            "--cols",
            "amount",
            "--mapping-out",
            str(mapping),
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "amount" in err


def test_datetime_column_refused(tmp_path, capsys):
    """Datetime columns are temporal — tokenising would break time-series analyses."""
    from scripts import anonymise

    # Use parquet so the datetime dtype survives the round-trip — CSV
    # loaders parse datetimes back as object/string by default, which
    # would not exercise the datetime branch.
    inp = tmp_path / "input.parquet"
    pd.DataFrame(
        {
            "event_at": pd.to_datetime(["2026-01-01", "2026-02-01", "2026-03-01"]),
            "name": ["A", "B", "C"],
        }
    ).to_parquet(inp, index=False)
    out = tmp_path / "out.parquet"
    mapping = tmp_path / "private" / "mapping.csv"

    rc = anonymise.main(
        [
            "--input",
            str(inp),
            "--output",
            str(out),
            "--cols",
            "event_at",
            "--mapping-out",
            str(mapping),
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "event_at" in err


# --- Structured config-error diagnostic -------------------------------------


def test_malformed_config_emits_structured_diagnostic(tmp_path, capsys):
    """Missing 'columns:' key must produce ERROR / What / What-to-try blocks."""
    from scripts import anonymise

    inp = _write_csv_three_dept(tmp_path)
    out = tmp_path / "out.csv"
    mapping = tmp_path / "private" / "mapping.csv"

    config = tmp_path / "config.yaml"
    config.write_text("mapping_out: /tmp/mapping.csv\n", encoding="utf-8")

    rc = anonymise.main(
        [
            "--input",
            str(inp),
            "--output",
            str(out),
            "--config",
            str(config),
            "--mapping-out",
            str(mapping),
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "ERROR:" in err
    assert "What went wrong:" in err
    assert "What to try:" in err
    assert "columns:" in err


# --- Path-risk validation passes through ------------------------------------


def test_risky_mapping_path_refused_without_accept_risk(tmp_path, monkeypatch, capsys):
    from scripts import anonymise

    inp = _write_csv_three_dept(tmp_path)
    out = tmp_path / "out.csv"
    mapping = tmp_path / "mapping.csv"  # under cwd → risky

    # Force cwd to tmp_path so the mapping path falls under it.
    monkeypatch.chdir(tmp_path)
    # Empty settings.json so additionalDirectories is empty.
    settings = tmp_path / "settings.json"
    settings.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("HOME", str(tmp_path))

    rc = anonymise.main(
        [
            "--input",
            str(inp),
            "--output",
            str(out),
            "--cols",
            "department",
            "--mapping-out",
            str(mapping),
            "--claude-settings-path",
            str(settings),
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "risk" in err.lower() or "scope" in err.lower()
    assert not out.exists()


def test_risky_mapping_path_accepted_with_flag(tmp_path, monkeypatch):
    from scripts import anonymise

    inp = _write_csv_three_dept(tmp_path)
    out = tmp_path / "out.csv"
    mapping = tmp_path / "mapping.csv"  # under cwd → would be risky

    monkeypatch.chdir(tmp_path)
    rc = anonymise.main(
        [
            "--input",
            str(inp),
            "--output",
            str(out),
            "--cols",
            "department",
            "--mapping-out",
            str(mapping),
            "--i-accept-the-risk",
        ]
    )
    assert rc == 0
    assert out.exists()
    assert mapping.exists()


# --- Pre-emptive TOK_ collision scan ---------------------------------------


def test_tok_prefix_in_input_refused_without_override(tmp_path, capsys):
    from scripts import anonymise

    inp = tmp_path / "input.csv"
    pd.DataFrame({"department": ["Engineering", "TOK_already_001", "Sales"]}).to_csv(
        inp, index=False
    )
    out = tmp_path / "out.csv"
    mapping = tmp_path / "private" / "mapping.csv"

    rc = anonymise.main(
        [
            "--input",
            str(inp),
            "--output",
            str(out),
            "--cols",
            "department",
            "--mapping-out",
            str(mapping),
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "TOK_" in err
    assert not out.exists()
    assert not mapping.exists()


def test_tok_prefix_in_input_allowed_with_override(tmp_path, capsys):
    from scripts import anonymise

    inp = tmp_path / "input.csv"
    pd.DataFrame({"department": ["Engineering", "TOK_already_001", "Sales"]}).to_csv(
        inp, index=False
    )
    out = tmp_path / "out.csv"
    mapping = tmp_path / "private" / "mapping.csv"

    rc = anonymise.main(
        [
            "--input",
            str(inp),
            "--output",
            str(out),
            "--cols",
            "department",
            "--mapping-out",
            str(mapping),
            "--allow-tok-prefix",
        ]
    )
    assert rc == 0
    err = capsys.readouterr().err
    assert "warning" in err.lower()
    assert "TOK_" in err


# --- YAML --config support --------------------------------------------------


def test_yaml_config_loads_columns(tmp_path):
    from scripts import anonymise

    inp = _write_csv_three_dept(tmp_path)
    out = tmp_path / "out.csv"
    mapping = tmp_path / "private" / "mapping.csv"

    config = tmp_path / "config.yaml"
    config.write_text("columns:\n  - department\n", encoding="utf-8")

    rc = anonymise.main(
        [
            "--input",
            str(inp),
            "--output",
            str(out),
            "--config",
            str(config),
            "--mapping-out",
            str(mapping),
        ]
    )
    assert rc == 0
    df = pd.read_csv(out)
    assert df["department"].iloc[0].startswith("TOK_department_")


def test_yaml_config_takes_precedence_over_cols_flag(tmp_path):
    from scripts import anonymise

    inp = tmp_path / "input.csv"
    pd.DataFrame(
        {
            "department": ["Eng", "Sales"],
            "name": ["Alice", "Bob"],
        }
    ).to_csv(inp, index=False)
    out = tmp_path / "out.csv"
    mapping = tmp_path / "private" / "mapping.csv"

    config = tmp_path / "config.yaml"
    # Config says department; flag says name. Config wins.
    config.write_text("columns:\n  - department\n", encoding="utf-8")

    rc = anonymise.main(
        [
            "--input",
            str(inp),
            "--output",
            str(out),
            "--cols",
            "name",
            "--config",
            str(config),
            "--mapping-out",
            str(mapping),
        ]
    )
    assert rc == 0
    df = pd.read_csv(out)
    # department was anonymised (from config); name was NOT (config won).
    assert df["department"].iloc[0].startswith("TOK_department_")
    assert df["name"].tolist() == ["Alice", "Bob"]


def test_yaml_config_missing_columns_key_refused(tmp_path, capsys):
    from scripts import anonymise

    inp = _write_csv_three_dept(tmp_path)
    out = tmp_path / "out.csv"
    mapping = tmp_path / "private" / "mapping.csv"

    config = tmp_path / "config.yaml"
    config.write_text("mapping_out: /tmp/mapping.csv\n", encoding="utf-8")

    rc = anonymise.main(
        [
            "--input",
            str(inp),
            "--output",
            str(out),
            "--config",
            str(config),
            "--mapping-out",
            str(mapping),
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "columns" in err.lower()


# --- Unknown column -----------------------------------------------------


def test_unknown_column_in_cols_refused(tmp_path, capsys):
    from scripts import anonymise

    inp = _write_csv_three_dept(tmp_path)
    out = tmp_path / "out.csv"
    mapping = tmp_path / "private" / "mapping.csv"

    rc = anonymise.main(
        [
            "--input",
            str(inp),
            "--output",
            str(out),
            "--cols",
            "nonexistent",
            "--mapping-out",
            str(mapping),
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "nonexistent" in err


# --- Stability: same value → same token ------------------------------------


def test_repeated_value_gets_same_token(tmp_path):
    from scripts import anonymise

    inp = tmp_path / "input.csv"
    pd.DataFrame(
        {
            "department": ["Eng", "Sales", "Eng", "HR", "Sales"],
        }
    ).to_csv(inp, index=False)
    out = tmp_path / "out.csv"
    mapping = tmp_path / "private" / "mapping.csv"

    rc = anonymise.main(
        [
            "--input",
            str(inp),
            "--output",
            str(out),
            "--cols",
            "department",
            "--mapping-out",
            str(mapping),
        ]
    )
    assert rc == 0
    df = pd.read_csv(out)
    # Eng appears at idx 0 and 2 → same token.
    assert df["department"].iloc[0] == df["department"].iloc[2]
    # Sales at 1 and 4 → same token.
    assert df["department"].iloc[1] == df["department"].iloc[4]
    # 3 distinct departments → 3 distinct tokens in the mapping.
    mdf = pd.read_csv(mapping)
    assert len(mdf) == 3


# --- NaN handling: nulls preserved, not tokenised -------------------------


def test_null_cells_preserved_not_tokenised(tmp_path):
    from scripts import anonymise

    inp = tmp_path / "input.csv"
    pd.DataFrame(
        {
            "department": ["Eng", None, "Sales", None, "Eng"],
        }
    ).to_csv(inp, index=False)
    out = tmp_path / "out.csv"
    mapping = tmp_path / "private" / "mapping.csv"

    rc = anonymise.main(
        [
            "--input",
            str(inp),
            "--output",
            str(out),
            "--cols",
            "department",
            "--mapping-out",
            str(mapping),
        ]
    )
    assert rc == 0
    df = pd.read_csv(out)
    # Two nulls preserved; non-null values tokenised; mapping has 2 entries.
    assert df["department"].isna().sum() == 2
    mdf = pd.read_csv(mapping)
    assert len(mdf) == 2  # Eng + Sales
