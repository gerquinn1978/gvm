"""End-to-end validate-mode comparison test (P21-C03).

Closes defect 3b from the gates-skipped diagnosis: validate mode runs to
exit 0 with a baseline file but `findings.comparison` was never populated,
so `_candidates_comparison` always returned [] and the baseline-divergence
headline never appeared.

Three assertions verify the producer-consumer chain end-to-end:

1. ``test_validate_mode_populates_comparison_block`` — drive analyse.main
   in validate mode against an actual + shifted-baseline pair; assert
   findings.comparison is populated with the spec'd shape.
2. ``test_validate_mode_surfaces_comparison_headline`` — same fixture;
   assert findings.headline_findings includes a `comparison` kind entry.
3. ``test_validate_mode_with_identical_baseline_zero_outliers`` — drive
   against actual = baseline (zero-delta case from the user's smoke);
   assert findings.comparison populates with empty
   file_vs_file_outliers and zero per-column delta means.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def _build_actual(out_path: Path) -> None:
    rows = []
    for i in range(40):
        rows.append({"score": float(i % 5 + 1), "value": float(i) * 2.0})
    pd.DataFrame(rows).to_csv(out_path, index=False)


def _build_shifted_baseline(out_path: Path) -> None:
    """Same shape as actual, but row 10's `value` is shifted dramatically
    so the row-vs-row outlier scan flags it."""
    rows = []
    for i in range(40):
        rows.append({"score": float(i % 5 + 1), "value": float(i) * 2.0})
    df = pd.DataFrame(rows)
    df.loc[10, "value"] = 1000.0  # 10× normal range — clearly divergent.
    df.to_csv(out_path, index=False)


def _run_validate(tmp_path: Path, baseline_path: Path) -> dict:
    import analyse
    from _shared import findings

    actual_path = tmp_path / "actual.csv"
    _build_actual(actual_path)
    out = tmp_path / "out"

    rc = analyse.main(
        [
            "--input",
            str(actual_path),
            "--output-dir",
            str(out),
            "--mode",
            "validate",
            "--target-column",
            "value",
            "--baseline-file",
            str(baseline_path),
            "--seed",
            "42",
        ]
    )
    assert rc == 0, "analyse.main failed in validate mode"
    return findings.read_findings(out / "findings.json")


def test_validate_mode_populates_comparison_block(tmp_path: Path) -> None:
    """Validate mode now populates findings.comparison via P21-C03 wiring."""
    baseline_path = tmp_path / "baseline.csv"
    _build_shifted_baseline(baseline_path)

    data = _run_validate(tmp_path, baseline_path)
    cmp_block = data.get("comparison")
    assert cmp_block is not None, (
        "findings.comparison is None — validate mode did not populate the "
        "comparison block (P21-C03 wiring missing or aggregation.compute "
        "returned None unexpectedly)"
    )
    # Schema check.
    assert set(cmp_block.keys()) == {
        "actual_file",
        "baseline_file",
        "shared_columns",
        "per_file_differences",
        "file_vs_file_outliers",
    }
    assert "value" in cmp_block["shared_columns"]
    # The shifted baseline causes row-level divergences.
    assert cmp_block["file_vs_file_outliers"], (
        "shifted baseline produced no row-level divergences — the row "
        "outlier scanner is silent when it should flag row 10"
    )


def test_validate_mode_surfaces_comparison_headline(tmp_path: Path) -> None:
    """The comparison headline (kind='comparison') appears in
    findings.headline_findings — proves the producer-consumer chain
    (comparison.compute → findings.comparison → _candidates_comparison)
    is wired end-to-end."""
    baseline_path = tmp_path / "baseline.csv"
    _build_shifted_baseline(baseline_path)

    data = _run_validate(tmp_path, baseline_path)
    headlines = data.get("headline_findings") or []
    comparison_headlines = [h for h in headlines if h.get("kind") == "comparison"]
    assert comparison_headlines, (
        f"no comparison headline in headline_findings; saw kinds: "
        f"{[h.get('kind') for h in headlines]}"
    )


def test_validate_mode_without_target_column_still_populates_comparison(
    tmp_path: Path,
) -> None:
    """Pass-1 review fix: validate mode + --baseline-file but NO
    --target-column (a legitimate drift-check workflow) must still
    populate findings.comparison. Pre-fix the wiring sat inside the
    target_column gate and silently no-op'd this case."""
    import analyse
    from _shared import findings

    actual_path = tmp_path / "actual.csv"
    baseline_path = tmp_path / "baseline.csv"
    _build_actual(actual_path)
    _build_shifted_baseline(baseline_path)
    out = tmp_path / "out"

    rc = analyse.main(
        [
            "--input",
            str(actual_path),
            "--output-dir",
            str(out),
            "--mode",
            "validate",
            "--baseline-file",
            str(baseline_path),
            "--seed",
            "42",
            # NO --target-column.
        ]
    )
    assert rc == 0
    data = findings.read_findings(out / "findings.json")
    assert data.get("comparison") is not None, (
        "validate mode without --target-column did not populate "
        "findings.comparison — wiring still gated on target_column"
    )


def test_comparison_headline_count_is_unique_rows_not_row_column_pairs(
    tmp_path: Path,
) -> None:
    """Pass-1 review fix: _candidates_comparison must report unique
    diverging rows, not (row, column) pair count. With a baseline that
    diverges on multiple columns at the same row, the headline summary
    should say 'N rows differ' where N is the row count, not the
    pair count."""
    import analyse
    from _shared import findings

    # Build fixtures where row 5 diverges on TWO columns simultaneously.
    rows = []
    for i in range(40):
        rows.append({"a": float(i), "b": float(i) * 2.0})
    actual_path = tmp_path / "actual.csv"
    pd.DataFrame(rows).to_csv(actual_path, index=False)

    baseline_rows = list(rows)
    baseline_rows[5] = {"a": 1000.0, "b": 9999.0}  # row 5 diverges on a AND b
    baseline_path = tmp_path / "baseline.csv"
    pd.DataFrame(baseline_rows).to_csv(baseline_path, index=False)

    out = tmp_path / "out"
    rc = analyse.main(
        [
            "--input",
            str(actual_path),
            "--output-dir",
            str(out),
            "--mode",
            "validate",
            "--target-column",
            "b",
            "--baseline-file",
            str(baseline_path),
            "--seed",
            "42",
        ]
    )
    assert rc == 0
    data = findings.read_findings(out / "findings.json")
    cmp_block = data["comparison"]
    # The producer emits 2 entries (one per diverging column for row 5).
    assert len(cmp_block["file_vs_file_outliers"]) == 2, cmp_block
    headlines = data.get("headline_findings") or []
    cmp_hl = [h for h in headlines if h.get("kind") == "comparison"]
    assert cmp_hl, "no comparison headline surfaced"
    # The summary should say "1 row differs" (singular form, one
    # unique row), not "2 rows differ" (which would be the pair count).
    summary = cmp_hl[0]["summary"]
    assert summary.startswith("1 row "), (
        f"comparison headline overstated row count or used plural for n=1: "
        f"{summary!r}"
    )


def test_validate_mode_with_identical_baseline_zero_outliers(
    tmp_path: Path,
) -> None:
    """Actual = baseline → comparison populates but file_vs_file_outliers
    is empty and per-column delta means are zero. Honest reporting:
    when nothing differs, nothing is flagged."""
    baseline_path = tmp_path / "baseline.csv"
    _build_actual(baseline_path)  # identical to actual

    data = _run_validate(tmp_path, baseline_path)
    cmp_block = data.get("comparison")
    assert cmp_block is not None
    assert cmp_block["file_vs_file_outliers"] == []
    for diff in cmp_block["per_file_differences"]:
        assert diff["delta"]["mean_change"] == 0.0
        assert diff["delta"]["std_change"] == 0.0
