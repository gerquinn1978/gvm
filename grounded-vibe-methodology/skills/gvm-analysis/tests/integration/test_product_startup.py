"""End-to-end product startup smoke (P15-C04 — final acceptance gate).

This is the explicit "the product runs" gate per the implementation guide.
It drives ``analyse.main`` then ``render_report.main`` against a small
fixture (CI mode — explicit argv bypasses AskUserQuestion prompts) and
asserts three structural invariants of the produced hub HTML that the
spec mandates as MUST acceptance criteria:

1. ``test_hub_renders_at_expected_path`` — TC-AN-26-01. Hub file exists at
   ``<out>/report.html`` (the renderer's canonical location), parses
   cleanly via html5lib, root element is ``<html>``.

2. ``test_hub_attribution_is_last_main_child`` — TC-AN-31-01. The last
   element child of ``<main>`` is ``<p class="gvm-attribution">`` with the
   canonical text "Developed using the Grounded Vibe Methodology"
   (shared rule 24).

3. ``test_comprehension_block_has_exactly_three_questions`` — TC-NFR-4-01.
   The ``<aside class="comprehension-questions">`` block exists and its
   descendant ``<ol>`` contains exactly three ``<li>`` items, each with a
   non-empty ``<p class="cq-question">`` body.

Engine is at tracer-bullet scope (per P15-C03a/b handovers); per-column
stats, drivers, time-series, charts, drillthroughs, and the print
stylesheet are not wired into ``analyse.main``/``render_report.main``
yet. Smoke-test coverage is therefore intentionally limited to the
invariants the running product can already satisfy. Deferred coverage
(TC-AN-26-02 section ordering on real content, TC-NFR-4-01b per-report
question variation, TC-AN-27-01 drillthrough link existence, print
stylesheet PDF render) is documented in the chunk handover.

Test cases: TC-AN-26-01, TC-AN-31-01, TC-NFR-4-01.
"""

from __future__ import annotations

from pathlib import Path

import html5lib
import pandas as pd


_SMOKE_FIXTURE_ROWS: int = 10
_GVM_ATTRIBUTION_TEXT: str = "Developed using the Grounded Vibe Methodology"


def _build_small_fixture(out_path: Path) -> None:
    """Write a 10-row × 5-column CSV fixture for the smoke run.

    Same shape as P15-C03a/b: numeric + categorical + label + timestamp
    so the renderer's section partials all see expected types. Refactor
    to a shared conftest helper is a candidate (Fowler — rule of three
    crossed across perf/wcag/startup) but is intentionally out of scope
    for the final acceptance chunk."""
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

    In-process ``main(argv)`` invocation pattern proven in P15-C02/C03a/C03b
    — exit-code contract is the source of truth, no subprocess overhead."""
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
    assert rc_engine == 0, "analyse.main failed under product startup fixture"

    rc_render = render_report.main(
        [
            "--findings",
            str(out_dir / "findings.json"),
            "--out",
            str(out_dir),
        ]
    )
    assert rc_render == 0, "render_report.main failed under product startup fixture"

    hub_path = (out_dir / "report.html").resolve()
    assert hub_path.is_file(), f"hub not produced at {hub_path}"
    return hub_path


def test_hub_renders_at_expected_path(tmp_path: Path) -> None:
    """TC-AN-26-01: a successful /gvm-analysis run produces a hub HTML
    file at the canonical path; the file parses as a single complete
    HTML document."""
    hub_path = _build_hub(tmp_path)
    html = hub_path.read_text(encoding="utf-8")

    assert html.lstrip().lower().startswith("<!doctype html>"), (
        "hub HTML must start with <!DOCTYPE html> (single complete document)"
    )

    doc = html5lib.parse(html, namespaceHTMLElements=False)
    assert doc.tag == "html", f"root element must be <html>, got {doc.tag!r}"
    assert doc.find(".//body") is not None, "missing <body>"
    assert doc.find(".//main") is not None, "missing <main>"


def test_hub_attribution_is_last_main_child(tmp_path: Path) -> None:
    """TC-AN-31-01: the last element child of <main> is the GVM
    attribution paragraph with the canonical text (shared rule 24)."""
    hub_path = _build_hub(tmp_path)
    doc = html5lib.parse(
        hub_path.read_text(encoding="utf-8"), namespaceHTMLElements=False
    )

    main_el = doc.find(".//main")
    assert main_el is not None, "missing <main>"

    children = list(main_el)
    assert children, "<main> has no element children"

    last = children[-1]
    assert last.tag == "p", f"last <main> child must be <p>, got <{last.tag}>"
    assert last.get("class") == "gvm-attribution", (
        f'last <main> child must have class="gvm-attribution", got {last.get("class")!r}'
    )

    text = "".join(last.itertext()).strip()
    assert text == _GVM_ATTRIBUTION_TEXT, (
        f"gvm-attribution text mismatch: got {text!r}, expected {_GVM_ATTRIBUTION_TEXT!r}"
    )


def test_comprehension_block_has_exactly_three_questions(tmp_path: Path) -> None:
    """TC-NFR-4-01: the comprehension-question block is present and
    contains exactly three questions, each with a non-empty question
    body."""
    hub_path = _build_hub(tmp_path)
    doc = html5lib.parse(
        hub_path.read_text(encoding="utf-8"), namespaceHTMLElements=False
    )

    asides = [
        a
        for a in doc.findall(".//aside")
        if a.get("class") == "comprehension-questions"
    ]
    assert len(asides) == 1, (
        f"expected exactly one <aside class='comprehension-questions'>, found {len(asides)}"
    )
    aside = asides[0]

    ols = aside.findall(".//ol")
    assert len(ols) == 1, (
        f"comprehension <aside> must contain exactly one <ol>, found {len(ols)}"
    )
    items = ols[0].findall("li")
    assert len(items) == 3, (
        f"comprehension block must contain exactly 3 <li>, found {len(items)}"
    )

    for idx, li in enumerate(items):
        question_ps = [p for p in li.findall(".//p") if p.get("class") == "cq-question"]
        assert len(question_ps) == 1, (
            f"<li>[{idx}] must contain exactly one <p class='cq-question'>, found {len(question_ps)}"
        )
        body = "".join(question_ps[0].itertext()).strip()
        assert body, f"<li>[{idx}] cq-question body is empty"
