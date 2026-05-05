"""Tests for `scripts/render_report.py` — minimal hub renderer (P1-C04).

Tracer-bullet scope: build_template_context bare-name contract (ADR-307b),
hub renders at the expected path (TC-AN-26-01), attribution is the last
child of <main> (TC-AN-31-01), comprehension-questions bridge survives the
JSON → HTML round-trip (post-R4 HIGH-T71).
"""

from __future__ import annotations

import json
from pathlib import Path

import html5lib
import pytest


ATTRIBUTION_TEXT: str = "Developed using the Grounded Vibe Methodology"


def _full_findings_fixture() -> dict[str, object]:
    """A structurally-complete findings dict for context + template tests.

    Matches the P1-C03 output shape (what render_report.py actually consumes
    when the Phase-1 end-to-end chain runs)."""
    from _shared import findings

    provenance = {
        # List-of-dicts per ADR-201 — matches the shape analyse.py emits.
        "input_files": [
            {
                "path": "/tmp/fixture.csv",
                "sha256": None,
                "mtime": None,
                "rows": None,
                "cols": None,
            }
        ],
        "mode": "explore",
        "target_column": None,
        "baseline_file": None,
        "seed": 42,
        # All 9 ADR-202 sub-seed keys — representative of actual engine output.
        "sub_seeds": {
            "outliers_iforest": 1,
            "outliers_lof": None,
            "drivers_rf": 2,
            "drivers_rf_perm": 3,
            "drivers_partial_corr": 4,
            "forecast_linear_bootstrap": 5,
            "forecast_arima_init": 6,
            "forecast_exp_smoothing_init": 7,
            "per_column": [],
        },
        "timestamp": "2026-04-20T00:00:00Z",
        "preferences": {},
        "preferences_hash": None,
        "lib_versions": {"python": "3.12.0"},
        "anonymised_input_detected": False,
        "anonymised_columns": [],
        "formula_columns": [],
        "sample_applied": None,
        "domain": None,
        "warnings": [],
        "time_column": None,
        "bootstrap_n_iter_used": 0,
    }
    data = findings.build_empty_findings(provenance=provenance)
    data["comprehension_questions"] = [
        {
            "question": f"Stub question {i}?",
            "answer": f"Stub answer {i}.",
            "supporting_finding_id": "",
        }
        for i in (1, 2, 3)
    ]
    return data


# --- build_template_context (ADR-307b bare-name contract) -------------------


def test_build_template_context_contains_every_bare_name(tmp_path: Path) -> None:
    """Every ADR-307b bare name is present and sourced from the right field."""
    import render_report

    findings_data = _full_findings_fixture()
    ctx = render_report.build_template_context(findings_data, output_dir=tmp_path)

    # Top-level bare names enumerated by ADR-307b spec excerpt.
    required_bare_names = {
        "findings",
        "provenance",
        "mode",
        "preferences",
        "preferences_hash",
        "lib_versions",
        "sample",
        "anonymised_columns",
        "formula_columns",
        "columns",
        "outliers",
        "duplicates",
        "time_series",
        "drivers",
        "headline_findings",
        "comprehension_questions",
        "drillthroughs",
        "comparison",
        "output_dir",
    }
    assert required_bare_names <= set(ctx.keys()), (
        f"missing bare names: {required_bare_names - set(ctx.keys())}"
    )

    assert ctx["mode"] == "explore"
    assert ctx["sample"] is None
    assert ctx["comprehension_questions"] == findings_data["comprehension_questions"]
    assert ctx["findings"] is findings_data


def test_build_template_context_passes_output_dir_through(tmp_path: Path) -> None:
    """output_dir is passed through verbatim (not stringified)."""
    import render_report

    ctx = render_report.build_template_context(
        _full_findings_fixture(), output_dir=tmp_path
    )
    assert ctx["output_dir"] == tmp_path


def test_build_template_context_sample_aliases_provenance_sample_applied(
    tmp_path: Path,
) -> None:
    """The bare name ``sample`` mirrors ``provenance.sample_applied``.

    Guards the ADR-307b aliasing beyond the trivial None case — a future
    refactor that accidentally sourced ``sample`` from a different key
    would be caught here."""
    import render_report

    findings_data = _full_findings_fixture()
    findings_data["provenance"]["sample_applied"] = {
        "configured_n": 10000,
        "n_sampled": 10000,
        "n_total": 1_000_000,
        "seed": 42,
    }

    ctx = render_report.build_template_context(findings_data, output_dir=tmp_path)
    assert ctx["sample"] == findings_data["provenance"]["sample_applied"]
    assert ctx["sample"]["configured_n"] == 10000


def test_hub_template_path_exists() -> None:
    """A-6 — the hub template actually resolves at the path render_hub
    expects. Catches a _SKILL_ROOT / layout drift before runtime."""
    import render_report

    assert (render_report._TEMPLATE_DIR / render_report._HUB_TEMPLATE_NAME).exists()


# --- render_hub (the template-to-file pipeline) -----------------------------


def _parse(html: str) -> object:
    return html5lib.parse(html, treebuilder="etree", namespaceHTMLElements=False)


def _find_main(tree: object) -> object:
    main = tree.find(".//main")
    assert main is not None, "rendered HTML has no <main> element"
    return main


def test_render_hub_writes_report_html(tmp_path: Path) -> None:
    """TC-AN-26-01: hub is written at <out>/report.html and is parseable HTML."""
    import render_report

    render_report.render_hub(_full_findings_fixture(), out=tmp_path)
    report = tmp_path / "report.html"
    assert report.exists(), "render_hub did not write report.html"

    html = report.read_text(encoding="utf-8")
    assert html.lstrip().startswith("<!DOCTYPE html>"), (
        "rendered HTML must start with <!DOCTYPE html>"
    )

    _parse(html)  # raises on broken HTML


def test_render_hub_attribution_is_last_child_of_main(tmp_path: Path) -> None:
    """TC-AN-31-01: <p class="gvm-attribution">...</p> is the last element
    child of <main>, with the canonical attribution text."""
    import render_report

    render_report.render_hub(_full_findings_fixture(), out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    tree = _parse(html)
    main = _find_main(tree)
    children = list(main)
    assert children, "<main> has no element children"

    last = children[-1]
    assert last.tag == "p", f"last child of <main> is <{last.tag}>, expected <p>"
    cls = last.get("class", "")
    assert "gvm-attribution" in cls.split(), (
        f"last child class is {cls!r}, expected to contain 'gvm-attribution'"
    )
    assert (last.text or "").strip() == ATTRIBUTION_TEXT


def test_render_hub_renders_comprehension_questions(tmp_path: Path) -> None:
    """Post-R4 HIGH-T71 bridge tracer-bullet: every stub question's text
    appears in the rendered HTML (proves the JSON → HTML round-trip)."""
    import render_report

    findings_data = _full_findings_fixture()
    render_report.render_hub(findings_data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    for q in findings_data["comprehension_questions"]:
        assert q["question"] in html, f"question missing from HTML: {q['question']!r}"
        assert q["answer"] in html, f"answer missing from HTML: {q['answer']!r}"


def test_render_hub_is_self_contained(tmp_path: Path) -> None:
    """AN-26 self-containment: no external stylesheets or script srcs."""
    import render_report

    render_report.render_hub(_full_findings_fixture(), out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert '<link rel="stylesheet"' not in html
    assert "<link rel='stylesheet'" not in html
    assert "<script src=" not in html


def test_render_hub_is_a_complete_html5_document(tmp_path: Path) -> None:
    """TDD item 6: <html>, <head>, <body> must be explicit in the source.

    html5lib silently synthesises these structural elements when they are
    missing — so a template that accidentally drops <head> would still
    parse into a tree with a synthesised <head>, giving later tests a
    false green. Assert the raw source text contains each opening tag so
    a P6 chunk that removes one breaks this test loudly.
    """
    import render_report

    render_report.render_hub(_full_findings_fixture(), out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert html.lstrip().startswith("<!DOCTYPE html>")
    for required in (
        "<html",
        "<head",
        "<body",
        "<main",
        "</main>",
        "</body>",
        "</html>",
    ):
        assert required in html, (
            f"rendered HTML missing required element marker: {required}"
        )


# --- main (CLI surface + exit-code contract) --------------------------------


def _write_valid_findings(path: Path) -> None:
    path.write_text(json.dumps(_full_findings_fixture()), encoding="utf-8")


def test_main_returns_zero_on_success(tmp_path: Path) -> None:
    """Exit-code contract lock: successful render returns 0 (int)."""
    import render_report

    findings_path = tmp_path / "findings.json"
    out = tmp_path / "out"
    _write_valid_findings(findings_path)

    rc = render_report.main(["--findings", str(findings_path), "--out", str(out)])
    assert rc == 0
    assert isinstance(rc, int)
    assert (out / "report.html").exists()


def test_main_missing_findings_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Missing --findings path → exit 2 + stderr diagnostic; no output."""
    import render_report

    missing = tmp_path / "does-not-exist.json"
    out = tmp_path / "out"

    rc = render_report.main(["--findings", str(missing), "--out", str(out)])
    assert rc == 2
    captured = capsys.readouterr()
    assert "does-not-exist.json" in captured.err
    assert not (out / "report.html").exists()


def test_main_schema_mismatch_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A findings.json with wrong schema_version → exit 2 with a diagnostic
    that names 'schema_version' per ADR-201 post-R4 HIGH-T49."""
    import render_report

    findings_path = tmp_path / "findings.json"
    bad = _full_findings_fixture()
    bad["schema_version"] = 2
    findings_path.write_text(json.dumps(bad), encoding="utf-8")
    out = tmp_path / "out"

    rc = render_report.main(["--findings", str(findings_path), "--out", str(out)])
    assert rc == 2
    captured = capsys.readouterr()
    assert "schema_version" in captured.err
    assert not (out / "report.html").exists()


def test_main_accepts_valid_findings_fixture(tmp_path: Path) -> None:
    """main() accepts the full canonical findings fixture without error.
    Guards against build_template_context drifting away from the engine's
    actual output shape. Renamed from test_main_accepts_findings_produced_by_analyse
    — the test uses the static fixture; the live analyse.py chain is
    covered by tests/integration/test_phase1_exit.py."""
    import render_report

    findings_path = tmp_path / "findings.json"
    _write_valid_findings(findings_path)
    out = tmp_path / "out"

    assert (
        render_report.main(["--findings", str(findings_path), "--out", str(out)]) == 0
    )


def test_main_corrupt_findings_json_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A non-JSON payload at --findings is an unexpected internal error,
    not a schema mismatch — exit 1 with a traceback on stderr."""
    import render_report

    findings_path = tmp_path / "findings.json"
    findings_path.write_text("{not valid json}", encoding="utf-8")
    out = tmp_path / "out"

    rc = render_report.main(["--findings", str(findings_path), "--out", str(out)])
    assert rc == 1
    captured = capsys.readouterr()
    assert "JSONDecodeError" in captured.err or "Expecting" in captured.err
    assert not (out / "report.html").exists()


def test_main_unexpected_error_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exit code 1 path: an unexpected error inside render_hub produces
    exit 1 + stderr traceback. Forced by monkeypatching read_findings to
    return a dict that triggers an undefined template variable further
    down the render pipeline."""
    import render_report
    from _shared import findings

    findings_path = tmp_path / "findings.json"
    _write_valid_findings(findings_path)
    out = tmp_path / "out"

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("simulated render failure")

    monkeypatch.setattr(render_report, "render_hub", _boom)

    rc = render_report.main(["--findings", str(findings_path), "--out", str(out)])
    assert rc == 1
    captured = capsys.readouterr()
    assert "RuntimeError" in captured.err
    assert "simulated render failure" in captured.err
    # Silence unused-import warning for findings: it documents the dep.
    _ = findings


def test_render_hub_raises_on_undefined_template_variable(tmp_path: Path) -> None:
    """StrictUndefined enforcement: a findings dict missing a key the
    template reads (e.g., provenance.seed accessed via {{ provenance.seed }})
    must raise ``jinja2.UndefinedError`` rather than silently render an
    empty value. This locks the Jinja2 Environment configuration."""
    import jinja2
    import pytest as _pytest

    import render_report

    findings_data = _full_findings_fixture()
    # Strip a key the template references (provenance.seed is used in the
    # <p class="meta"> line). StrictUndefined must raise on the missing sub-key.
    del findings_data["provenance"]["seed"]

    with _pytest.raises(jinja2.UndefinedError):
        render_report.render_hub(findings_data, out=tmp_path)


# --- P6-C04a: hub skeleton (TOC + section stubs + attribution) ---------------

import re as _re  # noqa: E402 — grouped with P6-C04a helpers below


SPEC_SECTION_ORDER: tuple[str, ...] = (
    "executive-summary",
    "data-quality",
    "distributions",
    "outliers",
    "time-series",
    "drivers",
    "comparison",
    "methodology-appendix",
    "provenance",
)


def _populate_optional_blocks(findings_data: dict[str, object]) -> dict[str, object]:
    """Give the optional context keys truthy values so conditional
    sections (time-series / drivers / comparison) render."""
    findings_data["time_series"] = {
        "time_column": "ts",
        "cadence": "daily",
        "median_gap_seconds": 86400,
        "expected_cadence_seconds": 86400,
        "gaps": [],
        "stale": None,
        "multi_window_outliers": [],
        "trend": {
            "method": "mann-kendall",
            "alpha": 0.05,
            "p_value": 0.5,
            "significant": False,
            "trend_label": "no trend",
        },
        "seasonality": {
            "method": "stl",
            "strength": 0.1,
            "threshold": 0.6,
            "significant": False,
            "period": None,
        },
        "forecast": None,
    }
    findings_data["drivers"] = {
        "target": "target_col",
        "K": 5,
        "K_rule": "max(5, ceil(0.10 * num_features))",
        "causation_disclaimer": "Association, not causation.",
        "method_results": {
            "variance_decomposition": [],
            "partial_correlation": [],
            "rf_importance": [],
            "shap": None,
        },
        "agreement": [],
    }
    findings_data["comparison"] = {"baseline": "baseline.csv", "deltas": []}
    return findings_data


def _section_ids_in_order(html: str) -> list[str]:
    """Extract ids of <section> elements that are direct children of <main>,
    in document order. Nested sections (e.g., comprehension-questions inside
    executive-summary) are deliberately excluded — this enforces the
    top-level hub structure from ADR-301."""
    tree = _parse(html)
    main = _find_main(tree)
    ids: list[str] = []
    for child in main:
        if child.tag == "section":
            sec_id = child.get("id")
            if sec_id:
                ids.append(sec_id)
    return ids


def test_hub_includes_css_partial(tmp_path: Path) -> None:
    """P6-C04a: the hub includes the real Tufte/Few CSS shell via
    {% include '_css.html.j2' %} rather than the P1-C04 inline placeholder.

    The shell carries a provenance comment beginning 'Source:
    tufte-html-reference.md' — use that as the anchor so the test
    survives a CSS refresh (which changes the sha256 but not the marker)."""
    import render_report

    render_report.render_hub(_full_findings_fixture(), out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert "Source: tufte-html-reference.md" in html


def test_hub_does_not_contain_inline_placeholder_style(tmp_path: Path) -> None:
    """P6-C04a: the P1-C04 placeholder style block is gone; all CSS now
    comes through the {% include '_css.html.j2' %} partial."""
    import render_report

    render_report.render_hub(_full_findings_fixture(), out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert "P1-C04 placeholder" not in html


def test_hub_has_toc_nav(tmp_path: Path) -> None:
    """P6-C04a: <nav class="toc" aria-label="..."> placeholder present.
    Body is empty — interactivity JS (P6-C07) populates it at runtime."""
    import render_report

    render_report.render_hub(_full_findings_fixture(), out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert _re.search(r'<nav\s+class="toc"\s+aria-label="[^"]+"', html), (
        'expected <nav class="toc" aria-label="..."> in rendered HTML'
    )


def test_hub_section_order_matches_spec(tmp_path: Path) -> None:
    """TC-AN-26-02: sections appear in the order declared by the
    report-generation hub-structure block, with all optional sections
    included (context populates time_series / drivers / comparison)."""
    import render_report

    findings_data = _populate_optional_blocks(_full_findings_fixture())
    render_report.render_hub(findings_data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert _section_ids_in_order(html) == list(SPEC_SECTION_ORDER)


def test_hub_section_ids_match_adr_301(tmp_path: Path) -> None:
    """ADR-301 hub structure: each section id matches the spec
    vocabulary verbatim (no 'exec-summary' / 'methodology' / etc.)
    and every section's first <h2> carries the matching id."""
    import render_report

    findings_data = _populate_optional_blocks(_full_findings_fixture())
    render_report.render_hub(findings_data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert set(_section_ids_in_order(html)) == set(SPEC_SECTION_ORDER)

    # Every section's first element child is an <h2> (heading order h1 → h2).
    # The <section id="X"> is the anchor target; the <h2> carries no id of its
    # own (HTML id uniqueness — see independent review P6-C04a).
    tree = _parse(html)
    main = _find_main(tree)
    for child in main:
        if child.tag != "section":
            continue
        sec_id = child.get("id")
        if sec_id not in SPEC_SECTION_ORDER:
            continue
        first_elem = next(iter(child), None)
        assert first_elem is not None, f'<section id="{sec_id}"> is empty'
        assert first_elem.tag == "h2", (
            f'<section id="{sec_id}"> opens with <{first_elem.tag}>, expected <h2>'
        )
        assert first_elem.get("id") is None, (
            f'<h2> inside <section id="{sec_id}"> has an id attribute; '
            "the parent <section> is the unique anchor target"
        )


def test_hub_conditional_sections_absent_when_context_missing(tmp_path: Path) -> None:
    """time-series / drivers / comparison sections must NOT render when
    their context key is falsy — they are legitimately None in many runs
    (e.g., no temporal column, explore mode without target)."""
    import render_report

    findings_data = _full_findings_fixture()
    # build_empty_findings leaves these as None/empty; assert the preconditions
    # so the test fails fast if the fixture changes.
    assert findings_data["time_series"] in (None, {}, [])
    assert findings_data["drivers"] in (None, {}, [])
    assert not findings_data.get("comparison")

    render_report.render_hub(findings_data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    ids = set(_section_ids_in_order(html))
    for conditional in ("time-series", "drivers", "comparison"):
        assert conditional not in ids, (
            f"conditional section {conditional!r} rendered despite falsy context"
        )

    # Non-conditional sections still present.
    for required in (
        "executive-summary",
        "data-quality",
        "distributions",
        "outliers",
        "methodology-appendix",
        "provenance",
    ):
        assert required in ids, f"required section {required!r} missing"


def test_hub_conditional_sections_present_when_context_populated(
    tmp_path: Path,
) -> None:
    """Counterpart to the absent-when-missing test: populating the optional
    context keys makes the three conditional sections render."""
    import render_report

    findings_data = _populate_optional_blocks(_full_findings_fixture())
    render_report.render_hub(findings_data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    ids = set(_section_ids_in_order(html))
    for conditional in ("time-series", "drivers", "comparison"):
        assert conditional in ids, (
            f"conditional section {conditional!r} missing despite populated context"
        )


def test_hub_attribution_still_last_child_of_main_after_skeleton(
    tmp_path: Path,
) -> None:
    """TC-AN-31-01 regression guard: even with every section present, the
    <p class="gvm-attribution"> stays the last element child of <main>."""
    import render_report

    findings_data = _populate_optional_blocks(_full_findings_fixture())
    render_report.render_hub(findings_data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    tree = _parse(html)
    main = _find_main(tree)
    children = list(main)
    assert children, "<main> has no element children"

    last = children[-1]
    assert last.tag == "p"
    assert "gvm-attribution" in (last.get("class") or "").split()
    assert (last.text or "").strip() == ATTRIBUTION_TEXT


# --- P6-C04b: exec summary + comprehension block + jargon scan + privacy test


def test_exec_summary_is_included(tmp_path: Path) -> None:
    """The exec-summary partial is included (not inlined). Anchor on the
    canonical ADR-306 heading text."""
    import render_report

    render_report.render_hub(_full_findings_fixture(), out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert '<aside class="comprehension-questions"' in html
    # Template emits &mdash; entity; autoescape leaves it verbatim.
    assert "Headline findings &mdash; can you answer these?" in html


def test_exec_summary_heading_and_aria(tmp_path: Path) -> None:
    """ADR-306: the comprehension block has aria-labelledby pointing at an
    <h3 id='cq-heading'>."""
    import render_report

    render_report.render_hub(_full_findings_fixture(), out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert 'aria-labelledby="cq-heading"' in html
    assert '<h3 id="cq-heading">' in html


def test_exec_summary_uses_details_disclosure(tmp_path: Path) -> None:
    """ADR-306: answers sit behind a <details>/<summary> disclosure."""
    import render_report

    findings_data = _full_findings_fixture()
    render_report.render_hub(findings_data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    # One <details> per question, each with a <summary>Reveal answer</summary>.
    assert html.count("<details>") == 3
    assert html.count("<summary>Reveal answer</summary>") == 3
    for q in findings_data["comprehension_questions"]:
        assert q["answer"] in html


def test_exec_summary_renders_three_questions(tmp_path: Path) -> None:
    """TC-NFR-4-01: exactly 3 questions rendered as <li> items in the <ol>."""
    import render_report

    render_report.render_hub(_full_findings_fixture(), out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    tree = _parse(html)
    ol = tree.find(".//aside[@class='comprehension-questions']/ol")
    assert ol is not None, "comprehension-questions <aside> has no <ol>"
    assert len([c for c in ol if c.tag == "li"]) == 3


def test_comprehension_count_mismatch_raises(tmp_path: Path) -> None:
    """ADR-306: count != 3 raises ComprehensionCountError at render time."""
    import render_report

    findings_data = _full_findings_fixture()
    findings_data["comprehension_questions"] = findings_data["comprehension_questions"][
        :2
    ]

    with pytest.raises(render_report.ComprehensionCountError):
        render_report.render_hub(findings_data, out=tmp_path)


def test_comprehension_count_mismatch_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """main() returns exit code 2 on count mismatch, with clear diagnostic."""
    import render_report

    findings_data = _full_findings_fixture()
    findings_data["comprehension_questions"] = findings_data["comprehension_questions"][
        :2
    ]
    findings_path = tmp_path / "findings.json"
    findings_path.write_text(json.dumps(findings_data), encoding="utf-8")
    out = tmp_path / "out"

    rc = render_report.main(["--findings", str(findings_path), "--out", str(out)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "comprehension_questions" in err.lower() or "count" in err.lower()


def test_comprehension_jargon_in_question_raises(tmp_path: Path) -> None:
    """ADR-306: jargon in any question body raises at render time."""
    from _shared.findings import JargonError

    import render_report

    findings_data = _full_findings_fixture()
    findings_data["comprehension_questions"][0]["question"] = (
        "What does the bootstrap tell us about the revenue trend?"
    )

    with pytest.raises(JargonError):
        render_report.render_hub(findings_data, out=tmp_path)


def test_comprehension_jargon_case_insensitive(tmp_path: Path) -> None:
    """The jargon scan is case-insensitive (matches the existing findings.py
    scan behaviour). 'Bootstrap', 'SHAP', 'MAD' all trigger."""
    from _shared.findings import JargonError

    import render_report

    for term in ("Bootstrap", "SHAP", "MAD"):
        findings_data = _full_findings_fixture()
        findings_data["comprehension_questions"][0]["question"] = (
            f"How does {term} apply to the data?"
        )
        with pytest.raises(JargonError):
            render_report.render_hub(findings_data, out=tmp_path)


def test_comprehension_jargon_in_answer_does_not_raise(tmp_path: Path) -> None:
    """ADR-306: jargon in answers is allowed (behind <details> disclosure).
    Only questions are scanned by the renderer."""
    import render_report

    findings_data = _full_findings_fixture()
    findings_data["comprehension_questions"][0]["answer"] = (
        "The bootstrap confidence interval is [1.2, 3.4] at 95% via BCa."
    )

    # Must NOT raise.
    render_report.render_hub(findings_data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "bootstrap confidence interval" in html


def test_hub_header_has_subtitle_and_meta(tmp_path: Path) -> None:
    """ADR-301: <header> has <p class='subtitle'> then <p class='meta'>."""
    import render_report

    findings_data = _full_findings_fixture()
    findings_data["provenance"]["input_files"] = [
        {
            "path": "/tmp/revenue_2025.csv",
            "sha256": None,
            "mtime": None,
            "rows": None,
            "cols": None,
        }
    ]
    render_report.render_hub(findings_data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert '<p class="subtitle">' in html
    assert '<p class="meta">' in html
    assert "revenue_2025.csv" in html  # basename of input file in subtitle
    assert "Mode: explore" in html


def test_hub_subtitle_without_input_files(tmp_path: Path) -> None:
    """With no input_files, subtitle still renders with mode-only copy."""
    import render_report

    findings_data = _full_findings_fixture()
    findings_data["provenance"]["input_files"] = []
    render_report.render_hub(findings_data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert '<p class="subtitle">' in html
    assert "Mode: explore" in html


def test_tc_nfr_4_02_jargon_absent_from_main_flow(tmp_path: Path) -> None:
    """TC-NFR-4-02 (hub partial): the main flow outside sidenotes / appendix
    / provenance contains no JARGON_FORBIDDEN terms.

    At P6-C04b scope the main flow only carries stub text; the assertion is
    the forward-looking guard that catches a P6-C04c chunk that accidentally
    paraphrases jargon into a section heading or stub paragraph.
    """
    from _shared.methodology import JARGON_FORBIDDEN

    import render_report

    render_report.render_hub(_full_findings_fixture(), out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8").lower()

    # Restrict the scan to <main> (CSS lives in <head>, which is out of scope
    # for the main-flow jargon rule — the CSS shell contains words like
    # "margin" that collide with e.g. JARGON_FORBIDDEN "mar").
    main_match = _re.search(r"<main\b[^>]*>(.*?)</main>", html, flags=_re.DOTALL)
    assert main_match is not None, "no <main> block"
    main_html = main_match.group(1)

    # Strip allowed-jargon channels inside <main>: sidenotes (<aside>),
    # <details> disclosures, methodology appendix, provenance.
    stripped = _re.sub(r"<aside\b.*?</aside>", "", main_html, flags=_re.DOTALL)
    stripped = _re.sub(r"<details\b.*?</details>", "", stripped, flags=_re.DOTALL)
    stripped = _re.sub(
        r'<section id="methodology-appendix".*?</section>',
        "",
        stripped,
        flags=_re.DOTALL,
    )
    stripped = _re.sub(
        r'<section id="provenance".*?</section>',
        "",
        stripped,
        flags=_re.DOTALL,
    )

    # Word-boundary match (matches the existing findings._scan_jargon contract).
    for term in JARGON_FORBIDDEN:
        pattern = rf"\b{_re.escape(term)}\b"
        assert not _re.search(pattern, stripped), (
            f"jargon term {term!r} leaked into main-flow text"
        )


def test_tc_nfr_1_01_no_sentinel_leakage_at_hub(tmp_path: Path) -> None:
    """TC-NFR-1-01 (hub partial): raw-row sentinels must not appear in the
    rendered HTML. This guard catches a future code path that surfaces a
    findings field that is NOT in the renderer's documented contract.

    Legitimate channels (input_files.path, comprehension_questions.answer)
    render user-facing text and are excluded — raw-row data should never
    have been placed in them by the engine. The test targets fields that
    the renderer is NOT supposed to surface to check the allow-list shape.
    """
    import render_report

    findings_data = _full_findings_fixture()
    # Inject a sentinel into a findings key that the renderer does NOT
    # surface: a per-column row_sample_cache (hypothetical; if the engine
    # ever adds such a field, the renderer must not touch it).
    findings_data["_internal_row_cache"] = [
        "SENTINEL_LEAK_ROW_001_should_never_appear",
        "SENTINEL_LEAK_ROW_002_should_never_appear",
    ]

    render_report.render_hub(findings_data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert "SENTINEL_LEAK_" not in html, (
        "raw-row sentinel leaked into rendered HTML — the renderer touched "
        "a field outside its documented contract"
    )


# --- P6-C04c: per-section hub rendering -------------------------------------


def _populated_sections_fixture() -> dict[str, object]:
    """A findings dict with enough per-section content to exercise the
    P6-C04c rendering: two columns (one populated, one CI-suppressed),
    one flagged outlier, a trending+seasonal time-series, and one driver."""
    data = _full_findings_fixture()

    data["columns"] = [
        {
            "name": "revenue",
            "dtype": "numeric",
            "n_total": 200,
            "n_non_null": 198,
            "completeness_pct": 99.0,
            "missingness_classification": {
                "label": "MCAR",
                "basis": "Little's test p=0.42",
                "confidence": "high",
            },
            "type_drift": None,
            "rounding_signal": None,
            "stats": {
                "robust": {
                    "median": 100.5,
                    "mad": 12.3,
                    "iqr": 24.6,
                    "q1": 88.0,
                    "q3": 112.6,
                },
                "classical": None,
                "ci_95": {"median": [95.0, 106.0], "mean": None},
                "tier": "n=100+",
            },
            "formula": None,
        },
        {
            "name": "small_col",
            "dtype": "numeric",
            "n_total": 20,
            "n_non_null": 20,
            "completeness_pct": 100.0,
            "missingness_classification": None,
            "type_drift": None,
            "rounding_signal": None,
            "stats": {
                "robust": {
                    "median": 5.0,
                    "mad": 1.0,
                    "iqr": 2.0,
                    "q1": 4.0,
                    "q3": 6.0,
                },
                "classical": None,
                "ci_95": None,
                "tier": "n=10-29",
            },
            "formula": None,
        },
        {
            "name": "category",
            "dtype": "categorical",
            "n_total": 200,
            "n_non_null": 200,
            "completeness_pct": 100.0,
            "missingness_classification": None,
            "type_drift": None,
            "rounding_signal": None,
            "stats": None,
            "formula": None,
        },
    ]

    data["outliers"] = {
        "by_method": {
            "iqr": [
                {"row_index": 42, "column": "revenue", "value": 500.0, "z_iqr": 4.2}
            ],
            "mad": [],
            "isolation_forest": None,
            "local_outlier_factor": None,
        },
        "agreement_matrix": [
            {
                "row_index": 42,
                "column": "revenue",
                "value": 500.0,
                "methods": ["iqr"],
                "confidence": "review",
                "methodology_ref": "iqr_outlier",
            }
        ],
        "agreement_summary": {"high": 0, "review": 1, "low": 0},
    }

    data["time_series"] = {
        "time_column": "date",
        "cadence": "monthly",
        "median_gap_seconds": 2592000,
        "expected_cadence_seconds": 2592000,
        "gaps": [],
        "stale": None,
        "multi_window_outliers": [],
        "trend": {
            "method": "mann-kendall",
            "alpha": 0.05,
            "p_value": 0.01,
            "significant": True,
            "trend_label": "increasing",
        },
        "seasonality": {
            "method": "stl",
            "strength": 0.7,
            "threshold": 0.6,
            "significant": True,
            "period": 12,
        },
        "forecast": None,
    }

    data["drivers"] = {
        "target": "revenue",
        "K": 5,
        "K_rule": "max(5, ceil(0.10 * num_features))",
        "causation_disclaimer": "Association, not causation.",
        "method_results": {
            "variance_decomposition": [],
            "partial_correlation": [],
            "rf_importance": [],
            "shap": None,
        },
        "agreement": [
            {
                "feature": "marketing_spend",
                "in_top_k": ["variance_decomposition", "rf_importance"],
                "label": "high-confidence",
                "methodology_ref": "shap_drivers",
            }
        ],
    }

    return data


def test_data_quality_table_renders_one_row_per_column(tmp_path: Path) -> None:
    import render_report

    data = _populated_sections_fixture()
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    tree = _parse(html)
    main = _find_main(tree)
    dq_section = None
    for child in main:
        if child.tag == "section" and child.get("id") == "data-quality":
            dq_section = child
            break
    assert dq_section is not None
    rows = dq_section.findall(".//tbody/tr")
    assert len(rows) == 3
    row_text = "".join("".join(r.itertext()) for r in rows)
    for name in ("revenue", "small_col", "category"):
        assert name in row_text


def test_data_quality_missingness_sidenote(tmp_path: Path) -> None:
    import render_report

    data = _populated_sections_fixture()
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert "Little's test p=0.42" in html
    # The basis text renders inside a sidenote aside.
    assert _re.search(
        r'<aside[^>]*class="[^"]*sidenote[^"]*"[^>]*>[^<]*Little',
        html,
        flags=_re.DOTALL,
    ), "missingness basis not rendered inside <aside class='sidenote'>"


def test_distributions_ci_present_for_populated_stats(tmp_path: Path) -> None:
    import render_report

    data = _populated_sections_fixture()
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    # The revenue row shows a numeric CI interval.
    assert "95.0" in html and "106.0" in html
    # A bootstrap_ci sidenote cites Efron & Tibshirani via the registry.
    assert "Efron" in html


def test_distributions_ci_suppressed_when_null_ci(tmp_path: Path) -> None:
    """ADR-306b: small-n column renders the warning chip + ci_suppressed_small_n
    sidenote, never a blank cell."""
    import render_report

    data = _populated_sections_fixture()
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert '<span class="ci-suppressed"' in html
    assert "CI n/a &mdash; n=10-29" in html or "CI n/a — n=10-29" in html
    # Harrell is cited in the ci_suppressed_small_n registry entry.
    assert "Harrell" in html


def test_distributions_no_stats_row_renders_placeholder(tmp_path: Path) -> None:
    """A categorical column (stats=None) renders a row but no CI chip or
    numeric interval — StrictUndefined must not raise."""
    import render_report

    data = _populated_sections_fixture()
    # Only the categorical column.
    data["columns"] = [c for c in data["columns"] if c["dtype"] == "categorical"]
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert "category" in html
    assert '<span class="ci-suppressed"' not in html


def test_outliers_section_shows_agreement_summary(tmp_path: Path) -> None:
    import render_report

    data = _populated_sections_fixture()
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    tree = _parse(html)
    main = _find_main(tree)
    ol_section = None
    for child in main:
        if child.tag == "section" and child.get("id") == "outliers":
            ol_section = child
            break
    assert ol_section is not None
    text = "".join(ol_section.itertext())
    # The agreement_summary has review=1 — surface the count plainly.
    assert "1" in text


def test_outliers_row_has_methodology_ref_sidenote(tmp_path: Path) -> None:
    """Main flow names the flagged column/value; the method name lives in the
    sidenote via the registry display_name."""
    import render_report

    data = _populated_sections_fixture()
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    # The registry display_name for iqr_outlier.
    assert "IQR outlier detection" in html
    # And the expert citation.
    assert "Tukey, EDA" in html


def test_time_series_section_renders_trend_label_and_sidenote(tmp_path: Path) -> None:
    import render_report

    data = _populated_sections_fixture()
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert "increasing" in html.lower()
    # Mann-Kendall registry entry cites Hamed & Rao.
    assert "Hamed" in html
    # STL registry entry cites Cleveland.
    assert "Cleveland" in html


def test_drivers_section_renders_agreement_with_sidenotes(tmp_path: Path) -> None:
    import render_report

    data = _populated_sections_fixture()
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert "marketing_spend" in html
    # shap_drivers registry entry cites Lundberg.
    assert "Lundberg" in html


def test_methodology_appendix_lists_every_used_method(tmp_path: Path) -> None:
    """TC-AN-13-02: every method referenced anywhere in the report appears in
    the appendix, each with its expert citation."""
    import render_report

    data = _populated_sections_fixture()
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    tree = _parse(html)
    main = _find_main(tree)
    app = None
    for child in main:
        if child.tag == "section" and child.get("id") == "methodology-appendix":
            app = child
            break
    assert app is not None
    app_text = "".join(app.itertext())
    for display_name in (
        "Bootstrap confidence interval (BCa)",
        "Bootstrap CI suppressed (small n)",
        "IQR outlier detection",
        "Mann-Kendall trend test",
        "STL seasonal decomposition",
        "SHAP feature importance (drivers)",
    ):
        assert display_name in app_text, f"appendix missing: {display_name}"


def test_methodology_appendix_empty_when_no_methods_used(tmp_path: Path) -> None:
    import render_report

    render_report.render_hub(_full_findings_fixture(), out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    tree = _parse(html)
    main = _find_main(tree)
    app = None
    for child in main:
        if child.tag == "section" and child.get("id") == "methodology-appendix":
            app = child
            break
    assert app is not None
    text = "".join(app.itertext())
    assert "No methods" in text


def test_tc_an_13_01_numeric_findings_have_sidenotes(tmp_path: Path) -> None:
    """TC-AN-13-01: every flagged outlier row carries a sidenote."""
    import render_report

    data = _populated_sections_fixture()
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    tree = _parse(html)
    main = _find_main(tree)
    outliers_sec = None
    for child in main:
        if child.tag == "section" and child.get("id") == "outliers":
            outliers_sec = child
            break
    assert outliers_sec is not None
    # Every <li> in the flagged list has an <aside class="sidenote"> descendant.
    for li in outliers_sec.findall(".//li"):
        asides = [
            a for a in li.iter("aside") if "sidenote" in (a.get("class") or "").split()
        ]
        assert asides, "flagged outlier <li> lacks a sidenote"


def test_tc_nfr_4_02_survives_populated_sections(tmp_path: Path) -> None:
    """Rerun the main-flow jargon guard with every section populated."""
    from _shared.methodology import JARGON_FORBIDDEN

    import render_report

    data = _populated_sections_fixture()
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8").lower()

    main_match = _re.search(r"<main\b[^>]*>(.*?)</main>", html, flags=_re.DOTALL)
    assert main_match is not None
    main_html = main_match.group(1)

    stripped = _re.sub(r"<aside\b.*?</aside>", "", main_html, flags=_re.DOTALL)
    stripped = _re.sub(r"<details\b.*?</details>", "", stripped, flags=_re.DOTALL)
    stripped = _re.sub(
        r'<section id="methodology-appendix".*?</section>',
        "",
        stripped,
        flags=_re.DOTALL,
    )
    stripped = _re.sub(
        r'<section id="provenance".*?</section>',
        "",
        stripped,
        flags=_re.DOTALL,
    )

    for term in JARGON_FORBIDDEN:
        pattern = rf"\b{_re.escape(term)}\b"
        assert not _re.search(pattern, stripped), (
            f"jargon term {term!r} leaked into main-flow text"
        )


def test_tc_an_26_03_no_row_cache_leakage(tmp_path: Path) -> None:
    import render_report

    data = _populated_sections_fixture()
    data["_internal_row_cache"] = ["SENTINEL_PC04C_MUST_NEVER_APPEAR"]
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "SENTINEL_PC04C" not in html


def test_methodology_entries_alphabetical(tmp_path: Path) -> None:
    """White-box: build_template_context places alphabetised registry entries
    under methodology_entries."""
    import render_report

    data = _populated_sections_fixture()
    ctx = render_report.build_template_context(data, output_dir=tmp_path)
    entries = ctx["methodology_entries"]
    display_names = [e["display_name"] for e in entries]
    assert display_names == sorted(display_names)
    assert "IQR outlier detection" in display_names


# --- P6-C05: drillthrough templates -----------------------------------------


def _drillthrough_fixture() -> dict[str, object]:
    """A findings dict with three drillthroughs (column / outlier / driver)
    and enough column-stats content to exercise the ADR-306b CI-null rule."""
    data = _populated_sections_fixture()
    data["drillthroughs"] = [
        {
            "id": "dt-col-revenue",
            "kind": "column",
            "data": {
                "column_name": "revenue",
                "stats": data["columns"][0]["stats"],
                "missingness": data["columns"][0]["missingness_classification"],
                "type_drift": None,
                "rounding_signal": None,
                "histogram_svg_path": "charts/hist-revenue.svg",
                "boxplot_svg_path": "charts/box-revenue.svg",
                "methodology_ref": "bootstrap_ci",
            },
        },
        {
            "id": "dt-col-small",
            "kind": "column",
            "data": {
                "column_name": "small_col",
                "stats": data["columns"][1]["stats"],
                "missingness": None,
                "type_drift": None,
                "rounding_signal": None,
                "histogram_svg_path": None,
                "boxplot_svg_path": None,
                "methodology_ref": "ci_suppressed_small_n",
            },
        },
        {
            "id": "dt-outlier-42",
            "kind": "outlier",
            "data": {
                "row_index": 42,
                "column": "revenue",
                "value": 500.0,
                "method_flags": ["iqr_outlier"],
                "context_window_stats": {"median": 100.5, "mad": 12.3},
                "row_excerpt": None,
            },
        },
        {
            "id": "dt-driver-marketing",
            "kind": "driver",
            "data": {
                "feature": "marketing_spend",
                "method_results_per_feature": {
                    "shap_drivers": {"mean_abs_shap": 0.42},
                },
                "shap_plot_svg_path": "charts/shap-marketing.svg",
                "partial_dependence_svg_path": None,
            },
        },
    ]
    return data


def test_drillthrough_writes_per_entry_file(tmp_path: Path) -> None:
    import render_report

    data = _drillthrough_fixture()
    render_report.render_drillthroughs(data, out=tmp_path)
    for dt in data["drillthroughs"]:
        path = tmp_path / f"drillthrough-{dt['id']}.html"
        assert path.exists(), f"missing {path}"


def test_drillthrough_is_parseable_and_self_contained(tmp_path: Path) -> None:
    import render_report

    render_report.render_drillthroughs(_drillthrough_fixture(), out=tmp_path)
    for path in sorted(tmp_path.glob("drillthrough-*.html")):
        html = path.read_text(encoding="utf-8")
        assert html.lstrip().startswith("<!DOCTYPE html>")
        _parse(html)
        assert '<link rel="stylesheet"' not in html
        assert "<script src=" not in html


def test_drillthrough_back_to_hub_link_is_relative(tmp_path: Path) -> None:
    """TC-AN-27-03: back-link href is exactly 'report.html'."""
    import render_report

    render_report.render_drillthroughs(_drillthrough_fixture(), out=tmp_path)
    for path in sorted(tmp_path.glob("drillthrough-*.html")):
        html = path.read_text(encoding="utf-8")
        assert 'href="report.html"' in html
        assert 'href="/report.html"' not in html
        assert "file://" not in html


def test_drillthrough_attribution_is_last_child_of_main(tmp_path: Path) -> None:
    import render_report

    render_report.render_drillthroughs(_drillthrough_fixture(), out=tmp_path)
    for path in sorted(tmp_path.glob("drillthrough-*.html")):
        html = path.read_text(encoding="utf-8")
        tree = _parse(html)
        main = _find_main(tree)
        children = list(main)
        last = children[-1]
        assert last.tag == "p"
        assert "gvm-attribution" in (last.get("class") or "").split()
        assert (last.text or "").strip() == ATTRIBUTION_TEXT


def test_drillthrough_column_renders_stats_with_ci(tmp_path: Path) -> None:
    import render_report

    render_report.render_drillthroughs(_drillthrough_fixture(), out=tmp_path)
    html = (tmp_path / "drillthrough-dt-col-revenue.html").read_text(encoding="utf-8")
    assert "revenue" in html
    assert "95.0" in html and "106.0" in html
    assert "Efron" in html


def test_drillthrough_column_ci_suppressed(tmp_path: Path) -> None:
    """ADR-306b: small-n column drillthrough renders the chip + sidenote."""
    import render_report

    render_report.render_drillthroughs(_drillthrough_fixture(), out=tmp_path)
    html = (tmp_path / "drillthrough-dt-col-small.html").read_text(encoding="utf-8")
    assert '<span class="ci-suppressed"' in html
    assert "CI n/a &mdash; n=10-29" in html or "CI n/a — n=10-29" in html
    assert "Harrell" in html


def test_drillthrough_outlier_privacy_note(tmp_path: Path) -> None:
    import render_report

    render_report.render_drillthroughs(_drillthrough_fixture(), out=tmp_path)
    html = (tmp_path / "drillthrough-dt-outlier-42.html").read_text(encoding="utf-8")
    assert "row contents" in html.lower() or "row content" in html.lower()


def test_drillthrough_outlier_no_raw_sentinels(tmp_path: Path) -> None:
    """TC-AN-27-02: sentinels injected into fields the renderer does not
    surface must never appear in any drillthrough."""
    import render_report

    data = _drillthrough_fixture()
    data["_internal_row_cache"] = ["SENTINEL_DT_MUST_NEVER_APPEAR"]
    data["drillthroughs"][2]["data"]["row_excerpt"] = "SENTINEL_DT_ROW_EXCERPT"
    render_report.render_drillthroughs(data, out=tmp_path)
    for path in sorted(tmp_path.glob("drillthrough-*.html")):
        html = path.read_text(encoding="utf-8")
        assert "SENTINEL_DT" not in html, f"sentinel leaked into {path.name}"


def test_drillthrough_driver_renders_feature_and_sidenote(tmp_path: Path) -> None:
    import render_report

    render_report.render_drillthroughs(_drillthrough_fixture(), out=tmp_path)
    html = (tmp_path / "drillthrough-dt-driver-marketing.html").read_text(
        encoding="utf-8"
    )
    assert "marketing_spend" in html
    assert "Lundberg" in html


def test_drillthrough_unknown_kind_raises(tmp_path: Path) -> None:
    import render_report

    data = _drillthrough_fixture()
    data["drillthroughs"] = [{"id": "dt-m", "kind": "methodology", "data": {}}]
    with pytest.raises(render_report.UnknownDrillthroughKindError):
        render_report.render_drillthroughs(data, out=tmp_path)


def test_drillthrough_unknown_kind_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import render_report

    data = _drillthrough_fixture()
    data["drillthroughs"] = [{"id": "dt-m", "kind": "methodology", "data": {}}]
    findings_path = tmp_path / "findings.json"
    findings_path.write_text(json.dumps(data), encoding="utf-8")
    out = tmp_path / "out"
    rc = render_report.main(["--findings", str(findings_path), "--out", str(out)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "methodology" in err.lower()


def test_render_drillthroughs_returns_list_of_paths(tmp_path: Path) -> None:
    import render_report

    data = _drillthrough_fixture()
    paths = render_report.render_drillthroughs(data, out=tmp_path)
    assert len(paths) == len(data["drillthroughs"])
    for p in paths:
        assert p.exists()


def test_main_renders_hub_and_drillthroughs(tmp_path: Path) -> None:
    import render_report

    data = _drillthrough_fixture()
    findings_path = tmp_path / "findings.json"
    findings_path.write_text(json.dumps(data), encoding="utf-8")
    out = tmp_path / "out"
    rc = render_report.main(["--findings", str(findings_path), "--out", str(out)])
    assert rc == 0
    assert (out / "report.html").exists()
    assert len(list(out.glob("drillthrough-*.html"))) == len(data["drillthroughs"])


def test_drillthrough_column_formula_rendered_when_present(tmp_path: Path) -> None:
    """ADR-306b post-R4 fix MEDIUM-T22: columns[].formula is rendered
    inside the per-column drillthrough as a sidenote."""
    import render_report

    data = _drillthrough_fixture()
    data["drillthroughs"][0]["data"]["formula"] = "=A2*B2"
    render_report.render_drillthroughs(data, out=tmp_path)
    html = (tmp_path / "drillthrough-dt-col-revenue.html").read_text(encoding="utf-8")
    assert "=A2*B2" in html
    # Formula sits inside <aside class="sidenote">
    assert _re.search(
        r'<aside[^>]*class="[^"]*sidenote[^"]*"[^>]*>[^<]*(?:<code>)?[^<]*=A2\*B2',
        html,
        flags=_re.DOTALL,
    )


def test_drillthrough_column_formula_absent_when_none(tmp_path: Path) -> None:
    import render_report

    render_report.render_drillthroughs(_drillthrough_fixture(), out=tmp_path)
    html = (tmp_path / "drillthrough-dt-col-revenue.html").read_text(encoding="utf-8")
    assert "Formula:" not in html


def test_drillthrough_column_svg_refs_are_relative(tmp_path: Path) -> None:
    import render_report

    render_report.render_drillthroughs(_drillthrough_fixture(), out=tmp_path)
    html = (tmp_path / "drillthrough-dt-col-revenue.html").read_text(encoding="utf-8")
    assert 'src="charts/hist-revenue.svg"' in html
    assert 'src="charts/box-revenue.svg"' in html
    assert 'src="/' not in html
    assert "file://" not in html


# --- P6-C06: provenance footer ---------------------------------------------


def _provenance_fixture() -> dict[str, object]:
    """Full-shape fixture with realistic provenance content for ADR-308 tests."""
    data = _full_findings_fixture()
    data["provenance"]["input_files"] = [
        {
            "path": "/tmp/revenue_2025.csv",
            "sha256": "abc123def456abc123def456abc123def456abc123def456abc123def456abcd",
            "mtime": "2026-04-19T12:34:56Z",
            "rows": 1000,
            "cols": 12,
        }
    ]
    data["provenance"]["lib_versions"] = {
        "python": "3.12.1",
        "pandas": "2.2.0",
        "numpy": "1.26.0",
    }
    data["provenance"]["preferences"] = {"mode": "explore", "risk_tier": "medium"}
    return data


def test_provenance_renders_required_fields(tmp_path: Path) -> None:
    """TC-AN-30-01: provenance footer lists every required field."""
    import render_report

    render_report.render_hub(_provenance_fixture(), out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    prov_match = _re.search(
        r'<section[^>]*id="provenance".*?</section>\s*<p class="gvm-attribution"',
        html,
        flags=_re.DOTALL,
    )
    assert prov_match, "provenance section not found before attribution"
    prov = prov_match.group(0)

    # input file fields
    assert "/tmp/revenue_2025.csv" in prov
    assert "abc123def456" in prov  # SHA-256 prefix
    assert "2026-04-19T12:34:56Z" in prov  # mtime
    assert "1000" in prov  # rows
    assert "12" in prov  # cols
    # runtime fields
    assert "3.12.1" in prov  # python version
    assert "pandas" in prov and "2.2.0" in prov  # lib version
    assert "42" in prov  # seed
    assert "2026-04-20T00:00:00Z" in prov  # run timestamp
    # mode
    assert "explore" in prov
    # preferences as JSON
    assert "risk_tier" in prov


def test_provenance_sample_rendered_when_applied(tmp_path: Path) -> None:
    import render_report

    data = _provenance_fixture()
    data["provenance"]["sample_applied"] = {
        "n_sampled": 5000,
        "n_total": 100000,
        "seed": 42,
    }
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "Sampled 5000 of 100000" in html


def test_provenance_sample_absent_when_none(tmp_path: Path) -> None:
    import render_report

    render_report.render_hub(_provenance_fixture(), out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "Sampled" not in html
    assert "Sampling applied" not in html


def test_provenance_anonymised_columns_rendered_when_nonempty(tmp_path: Path) -> None:
    import render_report

    data = _provenance_fixture()
    data["provenance"]["anonymised_columns"] = ["customer_id", "email"]
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "Anonymised input" in html
    assert "customer_id" in html
    assert "email" in html


def test_provenance_anonymised_columns_absent_when_empty(tmp_path: Path) -> None:
    import render_report

    render_report.render_hub(_provenance_fixture(), out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "Anonymised input" not in html


def test_provenance_formula_columns_rendered_when_nonempty(tmp_path: Path) -> None:
    import render_report

    data = _provenance_fixture()
    data["provenance"]["formula_columns"] = [
        {"column": "total", "formula": "=A2*B2"},
        {"column": "tax", "formula": "=total*0.2"},
    ]
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "Excel-formula columns" in html
    assert "=A2*B2" in html
    assert "=total*0.2" in html


def test_provenance_formula_columns_absent_when_empty(tmp_path: Path) -> None:
    import render_report

    render_report.render_hub(_provenance_fixture(), out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "Excel-formula columns" not in html


def test_provenance_warnings_section_rendered_when_present(tmp_path: Path) -> None:
    """Post-R4 HIGH-T7: provenance.warnings must render."""
    import render_report

    data = _provenance_fixture()
    data["provenance"]["warnings"] = [
        "STL seasonality skipped — series too short",
        "lttbc not installed — falling back to uniform decimation",
    ]
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "Analysis warnings" in html
    assert "STL seasonality skipped" in html
    assert "lttbc not installed" in html


def test_provenance_warnings_section_absent_when_empty(tmp_path: Path) -> None:
    import render_report

    render_report.render_hub(_provenance_fixture(), out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "Analysis warnings" not in html


def test_tc_an_30_03_sha256_roundtrip_property(tmp_path: Path) -> None:
    """TC-AN-30-03 [PROPERTY]: SHA-256 in footer equals the fixture value byte-for-byte."""
    import render_report

    sha = "f" * 64
    data = _provenance_fixture()
    data["provenance"]["input_files"][0]["sha256"] = sha
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert sha in html


def test_provenance_reproducibility_byte_identical(tmp_path: Path) -> None:
    """TC-AN-30-02: same fixture → identical rendered HTML."""
    import render_report

    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"
    render_report.render_hub(_provenance_fixture(), out=out1)
    render_report.render_hub(_provenance_fixture(), out=out2)
    assert (out1 / "report.html").read_bytes() == (out2 / "report.html").read_bytes()


def test_tc_an_31_01_attribution_last_child_of_main_hub_with_provenance(
    tmp_path: Path,
) -> None:
    """TC-AN-31-01: after provenance is wired, attribution is still last child of main."""
    import render_report

    render_report.render_hub(_provenance_fixture(), out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    main_match = _re.search(r"<main\b[^>]*>(.*?)</main>", html, flags=_re.DOTALL)
    assert main_match
    main_inner = main_match.group(1).rstrip()
    assert main_inner.endswith(f'<p class="gvm-attribution">{ATTRIBUTION_TEXT}</p>')


def test_tc_an_31_02_attribution_last_child_of_main_drillthrough_with_provenance(
    tmp_path: Path,
) -> None:
    """TC-AN-31-02: drillthroughs also terminate <main> with the attribution."""
    import render_report

    render_report.render_drillthroughs(_drillthrough_fixture(), out=tmp_path)
    for path in sorted(tmp_path.glob("drillthrough-*.html")):
        html = path.read_text(encoding="utf-8")
        main_match = _re.search(r"<main\b[^>]*>(.*?)</main>", html, flags=_re.DOTALL)
        assert main_match, f"no <main> in {path.name}"
        main_inner = main_match.group(1).rstrip()
        assert main_inner.endswith(
            f'<p class="gvm-attribution">{ATTRIBUTION_TEXT}</p>'
        ), f"attribution not last in {path.name}"


def test_drillthrough_includes_provenance_section(tmp_path: Path) -> None:
    """Each drillthrough embeds the provenance footer (same partial as hub)."""
    import render_report

    render_report.render_drillthroughs(_drillthrough_fixture(), out=tmp_path)
    for path in sorted(tmp_path.glob("drillthrough-*.html")):
        html = path.read_text(encoding="utf-8")
        assert 'id="provenance"' in html, f"provenance section missing in {path.name}"


def test_provenance_no_sentinel_leakage(tmp_path: Path) -> None:
    """TC-NFR-1-01 (provenance): internal fields must not leak into footer."""
    import render_report

    data = _provenance_fixture()
    data["_internal_row_cache"] = ["SENTINEL_PROV_LEAK"]
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "SENTINEL_PROV_LEAK" not in html


# --- P6-C07: interactivity JS ----------------------------------------------


def _extract_script_body(html: str) -> str:
    m = _re.search(r"<script\b[^>]*>(.*?)</script>", html, flags=_re.DOTALL)
    assert m, "no <script> tag in HTML"
    return m.group(1)


def test_hub_includes_interactivity_script(tmp_path: Path) -> None:
    import render_report

    render_report.render_hub(_provenance_fixture(), out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "<script" in html and "</script>" in html
    body = _extract_script_body(html)
    assert body.strip(), "script body is empty"


def test_drillthrough_includes_interactivity_script(tmp_path: Path) -> None:
    import render_report

    render_report.render_drillthroughs(_drillthrough_fixture(), out=tmp_path)
    for path in sorted(tmp_path.glob("drillthrough-*.html")):
        html = path.read_text(encoding="utf-8")
        assert "<script" in html, f"no <script> in {path.name}"
        body = _extract_script_body(html)
        assert body.strip(), f"empty script in {path.name}"


def test_interactivity_no_forbidden_network_apis(tmp_path: Path) -> None:
    """TC-AN-29-05: static scan — forbidden network / storage / dynamic-import APIs."""
    import render_report

    render_report.render_hub(_provenance_fixture(), out=tmp_path)
    render_report.render_drillthroughs(_drillthrough_fixture(), out=tmp_path)

    forbidden = [
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "EventSource",
        "document.write",
        "localStorage",
        "sessionStorage",
    ]
    html_files = [tmp_path / "report.html"] + list(tmp_path.glob("drillthrough-*.html"))
    for hf in html_files:
        body = _extract_script_body(hf.read_text(encoding="utf-8"))
        for token in forbidden:
            assert token not in body, f"{token} found in {hf.name}"
        # Dynamic import() — match `import(` with optional whitespace.
        assert not _re.search(r"\bimport\s*\(", body), f"dynamic import() in {hf.name}"


def test_interactivity_has_sortable_handler(tmp_path: Path) -> None:
    import render_report

    render_report.render_hub(_provenance_fixture(), out=tmp_path)
    body = _extract_script_body((tmp_path / "report.html").read_text(encoding="utf-8"))
    assert "data-sortable" in body
    assert "addEventListener" in body
    assert "data-sort-value" in body


def test_interactivity_has_filter_handler(tmp_path: Path) -> None:
    import render_report

    render_report.render_hub(_provenance_fixture(), out=tmp_path)
    body = _extract_script_body((tmp_path / "report.html").read_text(encoding="utf-8"))
    assert "findings-filter" in body
    assert "data-search-text" in body


def test_interactivity_has_tooltip_handler(tmp_path: Path) -> None:
    import render_report

    render_report.render_hub(_provenance_fixture(), out=tmp_path)
    body = _extract_script_body((tmp_path / "report.html").read_text(encoding="utf-8"))
    assert "tooltip-zone" in body
    assert "data-tooltip-text" in body


def test_interactivity_populates_toc(tmp_path: Path) -> None:
    import render_report

    render_report.render_hub(_provenance_fixture(), out=tmp_path)
    body = _extract_script_body((tmp_path / "report.html").read_text(encoding="utf-8"))
    assert "nav.toc" in body or "'.toc'" in body or '"toc"' in body
    # Walks section headings.
    assert "h2" in body.lower()


def test_interactivity_script_is_iife(tmp_path: Path) -> None:
    import render_report

    render_report.render_hub(_provenance_fixture(), out=tmp_path)
    body = _extract_script_body((tmp_path / "report.html").read_text(encoding="utf-8"))
    assert _re.search(r"\(function\s*\(\s*\)\s*\{", body) or _re.search(
        r"\(\s*\(\s*\)\s*=>\s*\{", body
    ), "script is not wrapped in an IIFE"


def test_interactivity_script_present_at_end_of_body(tmp_path: Path) -> None:
    import render_report

    render_report.render_hub(_provenance_fixture(), out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    body_match = _re.search(r"<body\b[^>]*>(.*?)</body>", html, flags=_re.DOTALL)
    assert body_match
    body_inner = body_match.group(1).rstrip()
    assert body_inner.endswith("</script>"), (
        "<script> is not the final element of <body>"
    )


# --- P6-C08: --bundle flag wiring -------------------------------------------


def test_bundle_flag_off_by_default_produces_no_zip(tmp_path: Path) -> None:
    """TC-AN-45-03: --bundle is off by default."""
    import render_report

    data = _drillthrough_fixture()
    findings_path = tmp_path / "findings.json"
    findings_path.write_text(json.dumps(data), encoding="utf-8")
    out = tmp_path / "out"
    rc = render_report.main(["--findings", str(findings_path), "--out", str(out)])
    assert rc == 0
    assert not (out / "report.zip").exists()
    assert not (out / "manifest.json").exists()


def test_css_overrides_loaded_in_hub(tmp_path: Path) -> None:
    """F-10 / F-11: the css overrides partial is loaded into hub <head> and
    carries the table-cell sidenote + chart-tooltip rules."""
    import render_report

    render_report.render_hub(_provenance_fixture(), out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    # F-10: table-cell sidenote override present.
    assert "td .sidenote" in html
    assert "float: none" in html
    # F-11: chart-tooltip has a CSS rule.
    assert ".chart-tooltip" in html and "border" in html


def test_css_overrides_loaded_in_drillthrough(tmp_path: Path) -> None:
    import render_report

    render_report.render_drillthroughs(_drillthrough_fixture(), out=tmp_path)
    for path in sorted(tmp_path.glob("drillthrough-*.html")):
        html = path.read_text(encoding="utf-8")
        assert "td .sidenote" in html, f"override missing in {path.name}"
        assert ".chart-tooltip" in html, f"tooltip rule missing in {path.name}"


def test_bundle_failure_returns_exit_2_with_typed_diagnostic(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """F-02 fix: a --bundle failure exits 2 with a bundle-specific diagnostic,
    not 1 with the hub fallback message."""
    import render_report
    from _shared import bundle as _bundle

    def _raise_bundle_err(*args: object, **kwargs: object) -> None:
        raise ValueError("synthetic bundle failure")

    monkeypatch.setattr(_bundle, "write_bundle", _raise_bundle_err)

    data = _drillthrough_fixture()
    findings_path = tmp_path / "findings.json"
    findings_path.write_text(json.dumps(data), encoding="utf-8")
    out = tmp_path / "out"
    rc = render_report.main(
        ["--findings", str(findings_path), "--out", str(out), "--bundle"]
    )
    assert rc == 2
    err = capsys.readouterr().err
    assert "bundle" in err.lower() or "manifest" in err.lower()
    # Hub + drillthroughs rendered before the bundle step failed.
    assert (out / "report.html").exists()


def test_bundle_unknown_method_error_returns_exit_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """F-06 fix: UnknownMethodError exits 2 with a methodology-specific
    diagnostic, not 1 with the hub fallback."""
    import render_report
    from _shared.methodology import UnknownMethodError

    def _raise_unknown(*args: object, **kwargs: object) -> list[dict[str, str]]:
        raise UnknownMethodError("unknown methodology key: synthetic_method")

    monkeypatch.setattr(render_report, "aggregate_appendix", _raise_unknown)

    data = _drillthrough_fixture()
    findings_path = tmp_path / "findings.json"
    findings_path.write_text(json.dumps(data), encoding="utf-8")
    out = tmp_path / "out"
    rc = render_report.main(["--findings", str(findings_path), "--out", str(out)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "methodology" in err.lower()


def test_bundle_flag_on_produces_zip(tmp_path: Path) -> None:
    """TC-AN-45-01 end-to-end via main(): --bundle writes report.zip + manifest.json."""
    import render_report

    data = _drillthrough_fixture()
    findings_path = tmp_path / "findings.json"
    findings_path.write_text(json.dumps(data), encoding="utf-8")
    out = tmp_path / "out"
    rc = render_report.main(
        ["--findings", str(findings_path), "--out", str(out), "--bundle"]
    )
    assert rc == 0
    assert (out / "report.zip").exists()
    assert (out / "manifest.json").exists()
