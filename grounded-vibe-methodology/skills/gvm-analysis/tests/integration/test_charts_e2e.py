"""End-to-end chart producer-consumer integration test (P19-C04).

The regression backstop the v2.0.0 release lacked. Drives the full chain:
``analyse.main`` produces SVGs and writes chart paths into findings;
``render_report.main`` reads findings and emits ``<img>`` references.

Six assertions cover the chain:

1. ``test_svgs_produced_for_every_numeric_column`` — at least one
   ``histogram`` and one ``boxplot`` SVG per numeric column on disk.
2. ``test_findings_json_carries_non_null_chart_paths`` — schema fields
   populated for every numeric column.
3. ``test_html_references_produced_svgs`` — every ``<img src="charts/...">``
   in ``report.html`` resolves to an SVG that actually exists on disk.
4. ``test_failure_injection_histogram_degrades_gracefully`` — monkey-
   patching ``_shared.charts.histogram`` to raise must not crash the
   run; histogram paths stay null; warnings surface; HTML omits the
   missing references; boxplots still render.
5. ``test_no_sentinel_leak_in_chart_svgs`` — NFR-1 privacy audit
   restricted to chart output (the rest of the output tree is covered
   by ``test_privacy_audit.py``).
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest


_FIXTURE_ROWS: int = 30
_NUMERIC_COLS: tuple[str, ...] = ("n_a", "n_b", "n_c")


def _build_fixture(out_path: Path) -> None:
    """Write a 30-row × 5-column CSV with three numeric columns plus
    one categorical and one timestamp. Numeric columns drive the
    histogram + boxplot producer."""
    rows: list[dict[str, object]] = []
    for i in range(_FIXTURE_ROWS):
        rows.append(
            {
                "n_a": float(i) * 1.5,
                "n_b": float(i) * 2.0 + (1000.0 if i == 7 else 0.0),
                "n_c": float(i) ** 0.5,
                "cat": ["alpha", "beta", "gamma"][i % 3],
                "ts": pd.Timestamp("2025-01-01") + pd.Timedelta(days=i),
            }
        )
    pd.DataFrame(rows).to_csv(out_path, index=False)


def _run_engine(tmp_path: Path) -> tuple[Path, dict]:
    """Run ``analyse.main`` against the deterministic fixture. Returns
    ``(output_dir, findings_dict)``."""
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
    return out, findings.read_findings(out / "findings.json")


def _run_renderer(out: Path) -> Path:
    """Run ``render_report.main`` against the produced findings. Returns
    the path to ``report.html``."""
    import render_report

    rc = render_report.main(
        ["--findings", str(out / "findings.json"), "--out", str(out)]
    )
    assert rc == 0, "render_report.main failed"
    report_html = out / "report.html"
    assert report_html.exists(), "render_report.main did not produce report.html"
    return report_html


def test_svgs_produced_for_every_numeric_column(tmp_path: Path) -> None:
    """Histogram + boxplot SVGs land on disk for every numeric column."""
    out, _ = _run_engine(tmp_path)
    charts_dir = out / "charts"
    assert charts_dir.is_dir(), f"charts dir missing at {charts_dir}"

    svgs = list(charts_dir.rglob("*.svg"))
    assert svgs, "no SVGs produced — chart producer not wired"

    names = {p.name for p in svgs}
    for col in _NUMERIC_COLS:
        hist_matches = [n for n in names if n.startswith(col) and "histogram" in n]
        box_matches = [n for n in names if n.startswith(col) and "boxplot" in n]
        assert hist_matches, f"no histogram SVG for column {col}; found {sorted(names)}"
        assert box_matches, f"no boxplot SVG for column {col}; found {sorted(names)}"


def test_findings_json_carries_non_null_chart_paths(tmp_path: Path) -> None:
    """findings.json columns[i].charts.{histogram,boxplot} populated."""
    out, data = _run_engine(tmp_path)

    numeric_entries = [c for c in data["columns"] if c.get("name") in _NUMERIC_COLS]
    assert len(numeric_entries) == len(_NUMERIC_COLS), (
        f"expected {len(_NUMERIC_COLS)} numeric column entries, "
        f"got {len(numeric_entries)}"
    )

    for entry in numeric_entries:
        charts = entry.get("charts")
        assert charts, f"column {entry['name']}: charts block missing/empty"
        hist = charts.get("histogram")
        box = charts.get("boxplot")
        assert hist, f"column {entry['name']}: histogram path null"
        assert box, f"column {entry['name']}: boxplot path null"
        assert hist.startswith("charts/"), f"histogram path not under charts/: {hist}"
        assert box.startswith("charts/"), f"boxplot path not under charts/: {box}"
        assert (out / hist).exists(), f"histogram SVG missing on disk: {hist}"
        assert (out / box).exists(), f"boxplot SVG missing on disk: {box}"


def test_html_references_produced_svgs(tmp_path: Path) -> None:
    """Every <img src="charts/..."> in report.html resolves to a real file."""
    out, _ = _run_engine(tmp_path)
    report_html = _run_renderer(out)

    html = report_html.read_text(encoding="utf-8")
    refs = re.findall(r'<img\s+src="(charts/[^"]+)"', html)
    assert refs, (
        'report.html contains zero <img src="charts/..."> references — '
        "templates not consuming chart paths (P19-C03 wiring gap)"
    )

    broken = [ref for ref in refs if not (out / ref).exists()]
    assert not broken, f"broken chart references in report.html: {broken}"

    # At minimum we expect histogram + boxplot per numeric column referenced.
    for col in _NUMERIC_COLS:
        assert any(col in ref and "histogram" in ref for ref in refs), (
            f"no histogram <img> reference for column {col}"
        )
        assert any(col in ref and "boxplot" in ref for ref in refs), (
            f"no boxplot <img> reference for column {col}"
        )


def test_failure_injection_histogram_degrades_gracefully(
    tmp_path: Path,
) -> None:
    """Patch _shared.charts.histogram to raise. The full chain must still
    succeed: run exits 0, histogram paths stay null, warnings surface,
    HTML omits broken histogram references, boxplots still render.
    This is the failure-mode contract from ADR-201 (graceful
    degradation) — the seam the v2.0.0 release lacked a regression
    test for."""
    import analyse
    import render_report
    from _shared import findings as findings_mod

    csv = tmp_path / "fixture.csv"
    _build_fixture(csv)
    out = tmp_path / "out"

    with patch(
        "_shared.charts.histogram",
        side_effect=RuntimeError("injected histogram failure"),
    ):
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
    assert rc == 0, (
        "analyse.main crashed under histogram failure — graceful "
        "degradation contract violated (ADR-201)"
    )

    data = findings_mod.read_findings(out / "findings.json")

    # All histogram paths null; all boxplot paths still populated.
    for entry in data["columns"]:
        if entry.get("name") not in _NUMERIC_COLS:
            continue
        charts = entry.get("charts") or {}
        assert charts.get("histogram") is None, (
            f"column {entry['name']}: histogram path populated despite "
            f"injected failure ({charts.get('histogram')!r})"
        )
        assert charts.get("boxplot"), (
            f"column {entry['name']}: boxplot path null — failure "
            f"isolation broken (boxplot should still render)"
        )

    warnings = data["provenance"].get("warnings", [])
    histogram_failures = [
        w for w in warnings if "chart_render_failed" in w and "kind=histogram" in w
    ]
    assert histogram_failures, (
        "no chart_render_failed warning for histogram in provenance — "
        f"got warnings: {warnings}"
    )

    # Render must succeed and HTML must NOT reference any histogram SVG.
    rc_render = render_report.main(
        ["--findings", str(out / "findings.json"), "--out", str(out)]
    )
    assert rc_render == 0, "render_report.main failed under degraded findings"
    html = (out / "report.html").read_text(encoding="utf-8")
    histogram_refs = re.findall(r'<img\s+src="(charts/[^"]*histogram[^"]*)"', html)
    assert not histogram_refs, (
        "report.html references histogram SVGs that were never produced — "
        f"template guard failed: {histogram_refs}"
    )
    # Boxplot references must remain (failure isolated to histogram).
    boxplot_refs = re.findall(r'<img\s+src="(charts/[^"]*boxplot[^"]*)"', html)
    assert boxplot_refs, (
        "report.html lost all boxplot references — failure isolation "
        "broken (only histogram should have degraded)"
    )


def test_no_sentinel_leak_in_chart_svgs(tmp_path: Path) -> None:
    """NFR-1 privacy audit restricted to chart output. The full output
    tree is covered by tests/integration/test_privacy_audit.py — this
    case asserts the chart producer specifically does not leak."""
    from tests.integration.test_privacy_audit import (
        SENTINELS,
        _build_sentinel_fixture,
    )
    import analyse

    raw_input = tmp_path / "sentinels.csv"
    _build_sentinel_fixture(raw_input)
    out = tmp_path / "out"

    rc = analyse.main(
        [
            "--input",
            str(raw_input),
            "--output-dir",
            str(out),
            "--mode",
            "explore",
            "--seed",
            "42",
        ]
    )
    assert rc == 0, "analyse.main failed on sentinel fixture"

    charts_dir = out / "charts"
    svgs = list(charts_dir.rglob("*.svg")) if charts_dir.is_dir() else []
    if not svgs:
        pytest.skip(
            "no SVGs produced for sentinel fixture (all-string columns) — "
            "privacy audit vacuous"
        )

    encoded = [(s, s.encode("utf-8")) for s in SENTINELS]
    leaks: list[tuple[Path, str]] = []
    for svg in svgs:
        data = svg.read_bytes()
        for sentinel, sentinel_bytes in encoded:
            if sentinel_bytes in data:
                leaks.append((svg, sentinel))
    assert not leaks, (
        "NFR-1 violation: sentinel substring(s) leaked into chart SVGs: "
        f"{leaks[:5]}{'…' if len(leaks) > 5 else ''}"
    )
