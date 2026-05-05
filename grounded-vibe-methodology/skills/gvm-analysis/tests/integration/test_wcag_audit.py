"""End-to-end WCAG audit (NFR-7, P15-C03b).

Two integration tests against the hub HTML produced by
``analyse.main → render_report.main``:

1. ``test_hub_static_structure_meets_wcag`` — fast, always-on. Parses the
   hub via ``html5lib`` and asserts: exactly one ``<h1>``, the
   ``<header>``/``<nav>``/``<main>`` landmarks are present, and every
   ``<table>`` has a ``<thead>`` and ``<th scope="col">``. Covers the
   structural half of TC-NFR-7-01.

2. ``test_hub_has_no_serious_axe_violations`` — env-gated by
   ``GVM_RUN_WCAG_TESTS=1``. Launches headless Chromium via Playwright,
   loads the generated hub via ``file://``, injects the bundled
   ``tests/data/axe.min.js`` (axe-core 4.10.2), evaluates ``axe.run()``,
   and asserts no Critical/Serious violations. Moderate/Minor are logged
   for visibility but do NOT fail the gate (NFR-7 is SHOULD priority —
   advisory rules are noise at this level).

The engine is at tracer-bullet level (per P15-C02 / P15-C03a handovers):
per-column stats, outliers, drivers, time-series, and chart layers are
not yet wired into ``analyse.main``. The hub is therefore sparse — but
the structural invariants tested here apply to whatever the hub emits,
so the audit is meaningful at every wiring level. TC-NFR-7-03/04
(no-colour-only, alt-text-or-data-table) are chart-level concerns and
out of scope until the chart layer lands.

Test cases: TC-NFR-7-01, partial TC-NFR-7-02 (axe rules
``focus-order-semantics``, ``link-name``, ``button-name``, ``tabindex``).
"""

from __future__ import annotations

import os
from pathlib import Path

import html5lib
import pandas as pd
import pytest


_SMOKE_FIXTURE_ROWS: int = 10


def _build_small_fixture(out_path: Path) -> None:
    """Write a 10-row × 5-column CSV fixture for the hub render.

    Column mix is deliberately small but exercises both numeric and
    categorical template paths (so the rendered hub contains the table
    sections whose semantic structure NFR-7 audits)."""
    df = pd.DataFrame(
        {
            "n_a": [i * 1.5 for i in range(_SMOKE_FIXTURE_ROWS)],
            "n_b": [i * 2 for i in range(_SMOKE_FIXTURE_ROWS)],
            "cat": ["alpha", "beta", "gamma"] * 3 + ["alpha"],
            "label": [f"row_{i}" for i in range(_SMOKE_FIXTURE_ROWS)],
            "ts": pd.date_range("2025-01-01", periods=_SMOKE_FIXTURE_ROWS, freq="D"),
        }
    )
    df.to_csv(out_path, index=False)


def _build_hub(tmp_path: Path) -> Path:
    """Drive ``analyse.main`` then ``render_report.main`` and return the
    path to the generated hub (``<out>/report.html``).

    Uses the in-process ``main(argv)`` invocation pattern proven in
    P15-C02 / P15-C03a — same exit-code contract, no subprocess overhead."""
    import analyse
    import render_report

    csv_path = tmp_path / "small.csv"
    _build_small_fixture(csv_path)
    out_dir = tmp_path / "out"

    rc_engine = analyse.main(
        [
            "--input",
            str(csv_path),
            "--output-dir",
            str(out_dir),
            "--mode",
            "explore",
            "--seed",
            "42",
        ]
    )
    assert rc_engine == 0, "analyse.main failed under WCAG fixture"

    rc_render = render_report.main(
        [
            "--findings",
            str(out_dir / "findings.json"),
            "--out",
            str(out_dir),
        ]
    )
    assert rc_render == 0, "render_report.main failed under WCAG fixture"

    hub_path = (out_dir / "report.html").resolve()
    assert hub_path.is_file(), f"hub not produced at {hub_path}"
    return hub_path


def _format_violation_diagnostic(violations: list[dict]) -> str:
    """Build a diagnostic string for axe violation failures."""
    lines = [f"axe-core reported {len(violations)} Critical/Serious violation(s):"]
    for v in violations:
        rule_id = v.get("id", "?")
        impact = v.get("impact", "?")
        description = v.get("description", "?")
        targets = [", ".join(node.get("target", [])) for node in v.get("nodes", [])]
        lines.append(f"  - [{impact}] {rule_id}: {description}")
        for tgt in targets[:3]:
            lines.append(f"      target: {tgt}")
        if len(targets) > 3:
            lines.append(f"      (+{len(targets) - 3} more)")
    return "\n".join(lines)


def test_hub_static_structure_meets_wcag(tmp_path: Path) -> None:
    """TC-NFR-7-01: hub HTML uses semantic structure — single h1, the
    header/nav/main landmarks are present, and every table has thead
    plus th scope=\"col\"."""
    hub_path = _build_hub(tmp_path)
    html = hub_path.read_text(encoding="utf-8")
    doc = html5lib.parse(html, namespaceHTMLElements=False)

    h1s = doc.findall(".//h1")
    assert len(h1s) == 1, f"expected exactly one <h1>, found {len(h1s)}"

    assert doc.find(".//header") is not None, "missing <header> landmark"
    assert doc.find(".//nav") is not None, "missing <nav> landmark"
    assert doc.find(".//main") is not None, "missing <main> landmark"

    tables = doc.findall(".//table")
    if not tables:
        # Tracer-bullet hub emits no <table> at this scope (per-column,
        # outliers, drivers, time-series wiring not yet landed). Skip
        # rather than pass vacuously — once a table-emitting partial
        # wires in, this skip drops out and the loop body enforces the
        # contract for real.
        pytest.skip(
            "no <table> elements in hub — WCAG table check vacuous at tracer-bullet scope"
        )
    for idx, tbl in enumerate(tables):
        thead = tbl.find("thead")
        assert thead is not None, f"<table>[{idx}] missing <thead>"
        ths = tbl.findall(".//th")
        assert ths, f"<table>[{idx}] has no <th> cells"
        for th in ths:
            assert th.get("scope") == "col", (
                f'<table>[{idx}] <th> missing scope="col" (text={th.text!r})'
            )


@pytest.mark.slow
@pytest.mark.wcag
@pytest.mark.skipif(
    os.environ.get("GVM_RUN_WCAG_TESTS") != "1",
    reason="WCAG audit gated behind GVM_RUN_WCAG_TESTS=1; runs in CI.",
)
def test_hub_has_no_serious_axe_violations(tmp_path: Path) -> None:
    """TC-NFR-7-01 + partial TC-NFR-7-02: axe-core scan over the hub
    must report zero Critical or Serious violations.

    Moderate/Minor advisory findings are logged for visibility but do
    not fail the gate (NFR-7 SHOULD-priority gate)."""
    hub_path = _build_hub(tmp_path)
    axe_path = Path(__file__).resolve().parent.parent / "data" / "axe.min.js"
    if not axe_path.is_file():
        pytest.skip(f"axe.min.js missing at {axe_path} — vendor it under tests/data/")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(f"file://{hub_path}")
            page.add_script_tag(path=str(axe_path))
            result = page.evaluate("axe.run()")
        finally:
            browser.close()

    violations = result.get("violations", [])
    blocking = [v for v in violations if v.get("impact") in {"critical", "serious"}]
    advisory = [v for v in violations if v.get("impact") in {"moderate", "minor"}]
    if advisory:
        print(
            f"\naxe-core advisory (moderate/minor, non-blocking): "
            f"{len(advisory)} finding(s)"
        )
        for v in advisory:
            print(f"  - [{v.get('impact')}] {v.get('id')}: {v.get('description')}")

    assert blocking == [], _format_violation_diagnostic(blocking)
