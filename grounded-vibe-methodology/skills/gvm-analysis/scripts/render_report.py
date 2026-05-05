"""Minimal hub renderer for ``/gvm-analysis`` (P1-C04 tracer-bullet scope).

Reads ``findings.json``, builds the ADR-307b bare-name template context,
and renders ``<out>/report.html`` from ``templates/hub.html.j2``. One output
file, one template, self-contained HTML, the GVM attribution as the last
child of ``<main>`` (shared rule 24, TC-AN-31-01).

Deferred to later chunks:

* Drillthrough rendering (per-kind partials) → P6-C04a/b/c.
* Full Tufte/Few CSS shell (``_css.html.j2``) → P6-C02.
* Interactivity JS (sort / filter / tooltip) → P6-C03.
* Bundle zip + manifest (``--bundle``) → P6-C07.
* Chart rendering → P6-C01/C02.
* Executive-summary / sidenote / methodology / full provenance templates
  → P6-C04–C06.
* Jargon scan on ``comprehension_questions`` → P5-C01b (the wrapper that
  patches real questions in).
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from _shared import findings
from _shared.findings import JargonError, _scan_jargon
from _shared.methodology import UnknownMethodError, aggregate_appendix


_TIME_SERIES_METHOD_MAP: dict[str, str] = {
    # trend.method → registry key
    "mann-kendall": "mann_kendall_trend",
    # seasonality.method → registry key
    "stl": "stl_seasonality",
    # forecast.method → registry key
    "linear": "linear_forecast",
    "arima": "arima_forecast",
    "exponential_smoothing": "exp_smoothing_forecast",
}


def _collect_method_keys(findings_data: dict[str, Any]) -> list[str]:
    """Return the registry keys for every method cited anywhere in findings,
    in deterministic document order with duplicates preserved.

    Walks every schema slot that carries a ``methodology_ref`` (ADR-201 plus
    the ADR-306b CI tier mapping). ``aggregate_appendix`` deduplicates and
    alphabetises downstream."""
    keys: list[str] = []

    for col in findings_data.get("columns") or []:
        stats = col.get("stats")
        if not stats:
            continue
        if stats.get("ci_95"):
            keys.append("bootstrap_ci")
        else:
            keys.append("ci_suppressed_small_n")

    outliers = findings_data.get("outliers") or {}
    for row in outliers.get("agreement_matrix") or []:
        ref = row.get("methodology_ref")
        if ref:
            keys.append(ref)

    ts = findings_data.get("time_series") or {}
    trend = ts.get("trend") or {}
    trend_method = trend.get("method")
    if trend_method and trend_method in _TIME_SERIES_METHOD_MAP:
        keys.append(_TIME_SERIES_METHOD_MAP[trend_method])
    seasonality = ts.get("seasonality") or {}
    season_method = seasonality.get("method")
    if season_method and season_method in _TIME_SERIES_METHOD_MAP:
        keys.append(_TIME_SERIES_METHOD_MAP[season_method])
    forecast = ts.get("forecast") or {}
    forecast_method = forecast.get("method")
    if forecast_method and forecast_method in _TIME_SERIES_METHOD_MAP:
        keys.append(_TIME_SERIES_METHOD_MAP[forecast_method])

    drivers = findings_data.get("drivers") or {}
    for row in drivers.get("agreement") or []:
        ref = row.get("methodology_ref")
        if ref:
            keys.append(ref)

    for hf in findings_data.get("headline_findings") or []:
        ref = hf.get("methodology_ref")
        if ref:
            keys.append(ref)

    return keys


class ComprehensionCountError(Exception):
    """Raised when ``comprehension_questions`` does not have exactly 3 items.

    ADR-306 fixes the count at 3 (NFR-4 / TC-NFR-4-01). The renderer fails
    loudly so the orchestration layer regenerates the questions rather than
    emitting a partial report (McConnell: defensive programming at the
    template boundary)."""

    def __init__(self, actual: int) -> None:
        self.actual = actual
        super().__init__(
            f"comprehension_questions must contain exactly 3 items, got {actual}"
        )


class UnknownDrillthroughKindError(Exception):
    """Raised when ``drillthroughs[].kind`` is not in the rendered set.

    P6-C05 renders ``column``, ``outlier``, and ``driver`` kinds. The
    schema (ADR-201) also permits ``methodology`` and ``comparison``;
    both are deferred and raise this error so the orchestration layer is
    not silently producing pages the renderer won't write."""


class JargonInQuestionError(JargonError):
    """Specialised ``JargonError`` raised by the renderer's comprehension scan.

    Subclasses the shared ``JargonError`` so existing ``except JargonError``
    handlers (e.g., the write-path scan in ``_shared.findings``) continue to
    fire, while giving the renderer's contract a named exception per the
    P6-C04b spec. McConnell: name the failure you want the caller to catch."""


_SKILL_ROOT: Path = Path(__file__).resolve().parent.parent
_TEMPLATE_DIR: Path = _SKILL_ROOT / "templates"
_HUB_TEMPLATE_NAME: str = "hub.html.j2"
_HUB_OUTPUT_NAME: str = "report.html"
_DRILLTHROUGH_TEMPLATE_NAME: str = "drillthrough.html.j2"
_RENDERED_DRILLTHROUGH_KINDS: frozenset[str] = frozenset(
    {"column", "outlier", "driver"}
)


def _drillthrough_title(dt: dict[str, Any]) -> str:
    """Human-readable title for the drillthrough page."""
    kind = dt.get("kind", "")
    data = dt.get("data") or {}
    if kind == "column":
        return f"Column: {data.get('column_name', '')}"
    if kind == "outlier":
        return f"Outlier: row {data.get('row_index', '')} in {data.get('column', '')}"
    if kind == "driver":
        return f"Driver: {data.get('feature', '')}"
    return dt.get("id", "Drillthrough")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse CLI arguments.

    ``--findings`` and ``--out`` mirror the Phase-1 exit command in the
    implementation guide. Downstream chunks add ``--bundle`` (P6-C07) and
    whatever else is needed; they MUST NOT rename these two.
    """
    parser = argparse.ArgumentParser(
        prog="render_report",
        description=(
            "Render the /gvm-analysis hub HTML from findings.json into --out."
        ),
    )
    parser.add_argument("--findings", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--bundle",
        action="store_true",
        help=(
            "After rendering, also write manifest.json and report.zip into "
            "--out (ADR-309 / AN-45). Off by default."
        ),
    )
    return parser.parse_args(argv)


def build_template_context(
    findings_data: dict[str, Any], *, output_dir: Path
) -> dict[str, Any]:
    """Return the ADR-307b bare-name context dict.

    Every top-level schema field referenced by any template gets a bare
    name here. Templates MUST use the bare name (e.g., ``mode``), never
    ``findings.provenance.mode``. The full contract is populated even at
    tracer-bullet scope so P6 chunks adding templates inherit the shape
    without churning this function.
    """
    provenance = findings_data["provenance"]
    input_files = provenance.get("input_files") or []
    subtitle_filename = (
        os.path.basename(input_files[0]["path"]) if input_files else None
    )
    method_keys = _collect_method_keys(findings_data)
    prefs_for_methodology = provenance.get("preferences") or {}
    methodology_entries = aggregate_appendix(method_keys, prefs_for_methodology)
    methodology_by_key = {e["key"]: e for e in methodology_entries}
    return {
        "findings": findings_data,
        "provenance": provenance,
        "mode": provenance["mode"],
        "preferences": provenance["preferences"],
        "preferences_hash": provenance["preferences_hash"],
        "lib_versions": provenance["lib_versions"],
        # Bare name `sample` aliases schema field `provenance.sample_applied`
        # per ADR-307b line 263. Templates read `sample`; findings.json carries
        # `sample_applied`. Keep this mapping if the schema field is renamed.
        "sample": provenance["sample_applied"],
        "anonymised_columns": provenance["anonymised_columns"],
        "formula_columns": provenance["formula_columns"],
        "columns": findings_data["columns"],
        "outliers": findings_data["outliers"],
        "duplicates": findings_data["duplicates"],
        "time_series": findings_data["time_series"],
        "drivers": findings_data["drivers"],
        "headline_findings": findings_data["headline_findings"],
        "comprehension_questions": findings_data["comprehension_questions"],
        "drillthroughs": findings_data["drillthroughs"],
        "comparison": findings_data.get("comparison"),
        "subtitle_filename": subtitle_filename,
        "methodology_entries": methodology_entries,
        "methodology_by_key": methodology_by_key,
        "output_dir": output_dir,
    }


def _validate_comprehension_questions(cqs: list[dict[str, Any]]) -> None:
    """Enforce ADR-306 at the renderer boundary: count == 3, no jargon
    in question bodies. Jargon in answers is explicitly permitted
    (they sit behind a ``<details>`` disclosure).

    Raises:
        ComprehensionCountError: count != 3.
        JargonError: a JARGON_FORBIDDEN term appears in any question body.
    """
    if len(cqs) != 3:
        raise ComprehensionCountError(len(cqs))
    for i, cq in enumerate(cqs):
        try:
            _scan_jargon(cq["question"], f"comprehension_questions[{i}].question")
        except JargonError as exc:
            raise JargonInQuestionError(term=exc.term, location=exc.location) from exc


def _make_env() -> Environment:
    """Build the Jinja2 Environment. ``StrictUndefined`` raises on missing
    context keys — silent fall-through would mask builder bugs."""
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "htm", "xml"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_hub(findings_data: dict[str, Any], *, out: Path) -> Path:
    """Render the hub to ``<out>/report.html`` and return the written path.

    The only side effect is the write; the caller is responsible for
    ensuring ``out`` is an acceptable directory (``main`` creates it if
    missing). Raises if the template references an undefined context key.
    """
    out.mkdir(parents=True, exist_ok=True)
    _validate_comprehension_questions(findings_data["comprehension_questions"])
    context = build_template_context(findings_data, output_dir=out)
    env = _make_env()
    template = env.get_template(_HUB_TEMPLATE_NAME)
    html = template.render(**context)
    report_path = out / _HUB_OUTPUT_NAME
    report_path.write_text(html, encoding="utf-8")
    return report_path


def render_drillthrough(
    dt: dict[str, Any],
    findings_data: dict[str, Any],
    *,
    out: Path,
    env: Environment | None = None,
) -> Path:
    """Render a single drillthrough HTML file.

    Raises :class:`UnknownDrillthroughKindError` if ``dt['kind']`` is not
    one of the P6-C05 rendered kinds (column / outlier / driver). The
    schema also permits ``methodology`` and ``comparison`` kinds; both
    are deferred to future chunks.

    ``env`` may be supplied so a batched caller (``render_drillthroughs``)
    reuses one Jinja Environment instead of rebuilding per entry."""
    kind = dt.get("kind", "")
    if kind not in _RENDERED_DRILLTHROUGH_KINDS:
        raise UnknownDrillthroughKindError(
            f"drillthrough kind {kind!r} is not rendered at P6-C05 scope "
            f"(rendered kinds: {sorted(_RENDERED_DRILLTHROUGH_KINDS)})"
        )
    context = build_template_context(findings_data, output_dir=out)
    context["drillthrough"] = dt
    context["dt_kind"] = kind
    context["dt_title"] = _drillthrough_title(dt)
    if env is None:
        env = _make_env()
    template = env.get_template(_DRILLTHROUGH_TEMPLATE_NAME)
    html = template.render(**context)
    path = out / f"drillthrough-{dt['id']}.html"
    path.write_text(html, encoding="utf-8")
    return path


def render_drillthroughs(findings_data: dict[str, Any], *, out: Path) -> list[Path]:
    """Render every entry in ``findings_data['drillthroughs']``.

    Caller ensures ``out`` exists (``render_hub`` creates it as a side
    effect). One Jinja Environment is built and reused across entries."""
    out.mkdir(parents=True, exist_ok=True)
    env = _make_env()
    return [
        render_drillthrough(dt, findings_data, out=out, env=env)
        for dt in findings_data.get("drillthroughs") or []
    ]


def _emit_diagnostic(error_line: str, what_went_wrong: str, what_to_try: str) -> None:
    """Write a three-line ERROR/What/What-to-try block to stderr.

    Surface matches ``analyse.py``; P2-C04 replaces this with the shared
    ``_shared/diagnostics.py`` formatter once the full taxonomy lands.
    """
    sys.stderr.write(f"ERROR: {error_line}\n")
    sys.stderr.write(f"What went wrong: {what_went_wrong}\n")
    sys.stderr.write(f"What to try: {what_to_try}\n")


def main(argv: list[str] | None = None) -> int:
    """Run the renderer. Return process exit code.

    Exit codes:
      0 — success; ``<out>/report.html`` written.
      1 — unexpected internal error; traceback-derived diagnostic on stderr.
      2 — invalid invocation: missing ``--findings`` file, schema mismatch,
          or argparse parse failure. P5-C02's bash wrapper distinguishes
          the subcases by reading stderr, not by exit code (same contract
          as ``analyse.py``).
    """
    args = _parse_args(argv)

    if not args.findings.exists():
        _emit_diagnostic(
            f"findings.json not found: {args.findings}",
            "The path passed to --findings does not exist on disk.",
            "Run analyse.py first, or check the --findings path and re-run.",
        )
        return 2

    try:
        findings_data = findings.read_findings(args.findings)
    except findings.SchemaValidationError as exc:
        _emit_diagnostic(
            str(exc),
            "This findings.json was produced by a different skill version.",
            "Re-run the full analysis with the current skill to produce a "
            "compatible findings.json.",
        )
        return 2
    except Exception as exc:  # noqa: BLE001 — generic fallback is intentional
        _emit_diagnostic(
            f"{type(exc).__name__}: {exc}",
            "The renderer failed before touching --out.",
            "Re-run with the same arguments; if the error persists, "
            "report the traceback below.",
        )
        traceback.print_exc(file=sys.stderr)
        return 1

    try:
        render_hub(findings_data, out=args.out)
        render_drillthroughs(findings_data, out=args.out)
    except UnknownMethodError as exc:
        _emit_diagnostic(
            str(exc),
            "findings.json references a methodology key that is not in the "
            "registry; the methodology appendix cannot be built.",
            "Extend _shared/methodology.py with the missing key, or correct "
            "the methodology_ref values in findings.json.",
        )
        return 2
    except UnknownDrillthroughKindError as exc:
        _emit_diagnostic(
            str(exc),
            "findings.json carries a drillthrough kind the renderer does not write.",
            "Either remove the entry, or extend render_report.py to handle it "
            "(P6-C05 renders column, outlier, and driver; methodology and "
            "comparison are deferred).",
        )
        return 2
    except ComprehensionCountError as exc:
        _emit_diagnostic(
            str(exc),
            "findings.json carries an incorrect number of comprehension_questions.",
            "Re-run /gvm-analysis so the orchestration regenerates exactly 3 "
            "plain-language questions (ADR-306).",
        )
        return 2
    except JargonError as exc:
        _emit_diagnostic(
            f"jargon term {exc.term!r} at {exc.location}",
            "A comprehension question body contains a forbidden statistical "
            "term; questions must be plain-language (ADR-306 / NFR-4).",
            "Re-run /gvm-analysis so the orchestration rephrases the question "
            "without statistical jargon.",
        )
        return 2
    except Exception as exc:  # noqa: BLE001 — generic fallback is intentional
        _emit_diagnostic(
            f"{type(exc).__name__}: {exc}",
            "The renderer failed while writing the hub HTML.",
            "Re-run with the same arguments; if the error persists, "
            "report the traceback below.",
        )
        traceback.print_exc(file=sys.stderr)
        return 1

    if args.bundle:
        import json as _json

        from _shared import bundle

        try:
            bundle.write_bundle(args.out, findings_path=args.findings)
        except (OSError, ValueError, _json.JSONDecodeError) as exc:
            _emit_diagnostic(
                f"{type(exc).__name__}: {exc}",
                "The hub and drillthroughs were rendered, but --bundle failed "
                "while writing manifest.json or report.zip.",
                "Verify --out is writable and findings.json carries a valid "
                "provenance.timestamp; re-run with --bundle to retry.",
            )
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
