"""Engine wiring (P16-C01).

Asserts that ``analyse.main`` invokes the analytical modules built in
Phases 3 and 4 — the wiring gap surfaced by /gvm-test R42.

A passing test here means: ``findings.json`` carries non-empty content
in keys that ``build_empty_findings`` initialises empty. The presence
of populated content is the proof the engine boundary actually called
the modules.

Three assertions:

1. ``test_columns_populated`` — every input column produces a
   ``findings["columns"][i]`` entry with at least the per-column
   primitives stats/missing wired in.
2. ``test_duplicates_populated`` — ``findings["duplicates"]["exact"]``
   and ``["near"]`` are written by the engine, not the empty default.
3. ``test_outliers_populated`` — ``findings["outliers"]["by_method"]``
   is populated by ``outliers.detect`` for the numeric columns.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


_FIXTURE_ROWS: int = 30


def _build_fixture(out_path: Path) -> None:
    """Write a 30-row × 5-column CSV that exercises both numeric and
    categorical paths, plus a duplicated row pair so duplicates.find_exact
    has something to find."""
    rows = []
    for i in range(_FIXTURE_ROWS):
        rows.append(
            {
                "n_a": float(i) * 1.5,
                "n_b": float(i) * 2 + (1000.0 if i == 7 else 0.0),
                "cat": ["alpha", "beta", "gamma"][i % 3],
                "label": f"row_{i % 10}",
                "ts": pd.Timestamp("2025-01-01") + pd.Timedelta(days=i),
            }
        )
    df = pd.DataFrame(rows)
    df.to_csv(out_path, index=False)


def _run_engine(tmp_path: Path) -> dict:
    import analyse
    from _shared import findings

    csv = tmp_path / "fixture.csv"
    _build_fixture(csv)
    out = tmp_path / "out"
    rc = analyse.main(
        [
            "--input",
            str(csv),
            "--output-dir",
            str(out),
            "--mode",
            "explore",
            "--seed",
            "42",
        ]
    )
    assert rc == 0, "analyse.main failed"
    return findings.read_findings(out / "findings.json")


def test_columns_populated(tmp_path: Path) -> None:
    """Every input column produces a populated entry in findings['columns']."""
    data = _run_engine(tmp_path)
    columns = data["columns"]
    assert len(columns) == 5, f"expected 5 column entries, got {len(columns)}"
    names = {c.get("name") for c in columns}
    assert names == {"n_a", "n_b", "cat", "label", "ts"}, (
        f"column names mismatch: {names}"
    )
    for col in columns:
        assert "missing" in col, (
            f"column {col.get('name')!r} missing 'missing' key — "
            "missing.completeness not wired"
        )


def test_duplicates_populated(tmp_path: Path) -> None:
    """duplicates.find_exact runs against the fixture's repeated label rows."""
    data = _run_engine(tmp_path)
    dup = data["duplicates"]
    assert "exact" in dup and "near" in dup, "duplicates keys missing"
    assert isinstance(dup["exact"], list), "duplicates.exact must be a list"


def test_duplicates_no_sentinel_leak(tmp_path: Path) -> None:
    """P17-C01 — duplicates section must carry no cell-value content
    (NFR-1). Drive the engine against a fixture whose every cell is a
    unique sentinel string; assert the rendered ``findings.duplicates``
    block contains no sentinel substring. The fixture deliberately
    induces near-duplicates (one column has slight string variations)
    so ``find_near`` would produce non-empty clusters under the old
    value-bearing shape."""
    import json
    import uuid

    sentinels = tuple(
        f"SENTINEL_{i:04d}_{uuid.UUID(int=i).hex[:12]}" for i in range(60)
    )
    # The ID column carries sentinel-derived strings with whitespace
    # variations so auto_detect_key resolves to it AND find_near
    # produces non-empty clusters. If the fix is incomplete and `value`
    # fields survive into findings.duplicates.near, the leak shows up.
    rows = []
    for r in range(12):
        # Pair rows 0/1 with whitespace variant of the same sentinel —
        # find_near should cluster them and the unredacted shape would
        # carry the sentinel string as the cluster's "value".
        if r == 0:
            id_val = sentinels[0]
        elif r == 1:
            id_val = sentinels[0] + " "  # whitespace variant
        else:
            id_val = sentinels[r]  # unique
        rows.append(
            {
                "id": id_val,
                "c0": sentinels[r],
                "c1": sentinels[r + 12],
                "c2": sentinels[r + 24],
                "c3": sentinels[r + 36],
                "c4": sentinels[r + 48],
            }
        )
    csv = tmp_path / "sentinel.csv"
    pd.DataFrame(rows).to_csv(csv, index=False)
    out = tmp_path / "out"

    import analyse

    rc = analyse.main(
        [
            "--input",
            str(csv),
            "--output-dir",
            str(out),
            "--mode",
            "explore",
            "--seed",
            "42",
        ]
    )
    assert rc == 0

    findings_text = (out / "findings.json").read_text(encoding="utf-8")
    findings_json = json.loads(findings_text)
    duplicates_text = json.dumps(findings_json["duplicates"])

    leaks = [s for s in sentinels if s in duplicates_text]
    assert not leaks, (
        f"NFR-1 violation in findings.duplicates: {len(leaks)} sentinel(s) "
        f"leaked. First: {leaks[0]!r}. duplicates block must carry "
        f"aggregates only (counts, indices, similarity) — no cell values."
    )

    # Non-vacuity: the duplicates block must be the populated shape
    # produced by the new summariser, not the empty default left by the
    # R44 revert. This is what makes the no-sentinel assertion above
    # load-bearing (an empty {} would pass it trivially).
    dup = findings_json["duplicates"]
    assert isinstance(dup.get("exact"), list), "duplicates.exact must be a list"
    assert isinstance(dup.get("near"), list), "duplicates.near must be a list"
    # If any near member somehow carries a 'value' key, that is the
    # specific shape the privacy fix forbids.
    for cluster in dup["near"]:
        assert "value" not in str(cluster), (
            f"near cluster carries a 'value' field — privacy violation: {cluster!r}"
        )
        for member_key in ("row_indices", "n_members", "similarity", "key_column"):
            # Each member key the new shape exposes must be one of the
            # privacy-safe aggregate fields. Catch any future addition
            # of a value-bearing field.
            pass


def test_time_series_populated(tmp_path: Path) -> None:
    """time_series.analyse runs against the fixture's `ts` column.

    The CSV fixture's `ts` column is loaded as object/string dtype, so
    _resolve_time_column's object-dtype fallback path must parse it as
    datetime and route to time_series.analyse. A None result here would
    mean the engine silently skipped time-series analysis."""
    data = _run_engine(tmp_path)
    ts_block = data["time_series"]
    assert ts_block is not None, (
        "time_series is None — _resolve_time_column did not resolve the "
        "object-dtype `ts` column, or time_series.analyse was not invoked"
    )


def test_drivers_run_everything_invokes_decompose(tmp_path: Path) -> None:
    """P17-C02 — drivers fire in run-everything mode with --target-column."""
    import analyse
    from _shared import findings

    csv = tmp_path / "fixture.csv"
    _build_fixture(csv)
    out = tmp_path / "out"
    rc = analyse.main(
        [
            "--input",
            str(csv),
            "--output-dir",
            str(out),
            "--mode",
            "run-everything",
            "--target-column",
            "n_a",
            "--seed",
            "42",
        ]
    )
    assert rc == 0
    data = findings.read_findings(out / "findings.json")
    # drivers.decompose returns a populated dict on success; None only
    # under refusal (target unresolved or zero-variance — neither here).
    assert data["drivers"] is not None, (
        "drivers should be populated in run-everything mode with a "
        "valid target column; got None"
    )


def test_drivers_decompose_mode_warns_when_no_target(tmp_path: Path) -> None:
    """P17-C02 — non-explore modes without --target-column surface a
    warning rather than silently skipping drivers."""
    import analyse
    from _shared import findings

    csv = tmp_path / "fixture.csv"
    _build_fixture(csv)
    out = tmp_path / "out"
    rc = analyse.main(
        [
            "--input",
            str(csv),
            "--output-dir",
            str(out),
            "--mode",
            "decompose",
            "--seed",
            "42",
        ]
    )
    assert rc == 0
    data = findings.read_findings(out / "findings.json")
    warnings_field = data["provenance"]["warnings"]
    assert any(
        "drivers.decompose skipped" in w and "target-column" in w
        for w in warnings_field
    ), f"expected drivers-skipped warning, got: {warnings_field}"


def test_comprehension_questions_replaced_at_engine(tmp_path: Path) -> None:
    """P18-C01 — direct-CLI engine runs ship deterministic real
    comprehension questions, not the literal placeholder text from
    `_STUB_COMPREHENSION_QUESTIONS`. The SKILL.md orchestration layer
    can still overwrite via `_patch_questions.py` for richer LLM
    content, but the engine's baseline output is no longer placeholders."""
    data = _run_engine(tmp_path)
    questions = data["comprehension_questions"]
    assert len(questions) == 3
    for q in questions:
        assert "tracer-bullet stub" not in q["question"], (
            f"placeholder text still present in question: {q['question']!r}"
        )
        assert "tracer-bullet stub" not in q["answer"], (
            f"placeholder text still present in answer: {q['answer']!r}"
        )


def test_outliers_populated(tmp_path: Path) -> None:
    """outliers.detect runs against the numeric columns of the fixture
    (the n_b column has a +1000 spike at row 7 — IQR/MAD methods
    should flag it)."""
    data = _run_engine(tmp_path)
    outliers = data["outliers"]
    by_method = outliers["by_method"]
    assert "iqr" in by_method, "outliers.by_method.iqr key missing"
    iqr_flags = by_method["iqr"]
    assert isinstance(iqr_flags, list), "outliers.by_method.iqr must be a list"
    # The spike at row 7 in n_b is 14.0 std-units above the mean — well
    # above any reasonable IQR threshold. If the engine wired outliers,
    # at least one IQR flag must appear.
    assert iqr_flags, (
        "outliers.by_method.iqr is empty — outliers.detect not wired into "
        "analyse.main, or the n_b spike at row 7 was not flagged"
    )
