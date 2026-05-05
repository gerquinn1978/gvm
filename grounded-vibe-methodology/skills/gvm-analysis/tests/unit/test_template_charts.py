"""P19-C03 — Per-section partials must surface chart paths from findings.

Templates emit `<figure><img src="charts/…">` when paths are non-null and
degrade silently to text when paths are null/absent. Path contract is
P19-C01: relative POSIX under `charts/`.
"""

from __future__ import annotations

import re
from pathlib import Path


# Reuse the populated-sections fixture style from test_render_report.
def _base_findings() -> dict:
    from _shared import findings

    provenance = {
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
        "timestamp": "2026-04-27T00:00:00Z",
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
        {"question": f"Q{i}?", "answer": f"A{i}.", "supporting_finding_id": ""}
        for i in (1, 2, 3)
    ]
    return data


def _column(name: str, *, charts: dict | None = None) -> dict:
    col: dict = {
        "name": name,
        "dtype": "numeric",
        "n_total": 100,
        "n_non_null": 100,
        "completeness_pct": 100.0,
        "missingness_classification": None,
        "type_drift": None,
        "rounding_signal": None,
        "stats": {
            "robust": {"median": 5.0, "mad": 1.0, "iqr": 2.0, "q1": 4.0, "q3": 6.0},
            "classical": None,
            "ci_95": None,
            "tier": "n=100+",
        },
        "formula": None,
    }
    if charts is not None:
        col["charts"] = charts
    return col


# --- distributions section ---


def test_distributions_emits_figure_when_charts_populated(tmp_path: Path) -> None:
    import render_report

    data = _base_findings()
    data["columns"] = [
        _column(
            "revenue",
            charts={
                "histogram": "charts/revenue.histogram.svg",
                "boxplot": "charts/revenue.boxplot.svg",
            },
        )
    ]
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert '<img src="charts/revenue.histogram.svg"' in html
    assert '<img src="charts/revenue.boxplot.svg"' in html
    assert "Histogram of revenue" in html
    assert "Boxplot of revenue" in html


def test_distributions_no_img_when_charts_block_absent(tmp_path: Path) -> None:
    import render_report

    data = _base_findings()
    data["columns"] = [_column("revenue")]  # no `charts` key
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert "revenue" in html  # text still present
    assert 'src="charts/' not in html


def test_distributions_no_img_when_path_is_none(tmp_path: Path) -> None:
    import render_report

    data = _base_findings()
    data["columns"] = [_column("revenue", charts={"histogram": None, "boxplot": None})]
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert "revenue" in html
    assert 'src="charts/' not in html


def test_distributions_mixed_per_row_degradation(tmp_path: Path) -> None:
    import render_report

    data = _base_findings()
    data["columns"] = [
        _column(
            "revenue",
            charts={"histogram": "charts/revenue.histogram.svg", "boxplot": None},
        ),
        _column("cost"),  # no charts block
    ]
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert '<img src="charts/revenue.histogram.svg"' in html
    assert '<img src="charts/revenue.boxplot.svg"' not in html
    # cost row has no images at all
    img_srcs = re.findall(r'<img\s+src="([^"]+)"', html)
    cost_imgs = [s for s in img_srcs if "cost" in s]
    assert cost_imgs == []


# --- outliers section ---


def test_outliers_emits_figure_for_method_chart(tmp_path: Path) -> None:
    import render_report

    data = _base_findings()
    data["columns"] = [_column("revenue")]
    data["outliers"] = {
        "by_method": {
            "iqr": [
                {
                    "row_index": 42,
                    "column": "revenue",
                    "value": 500.0,
                    "z_iqr": 4.2,
                    "chart": "charts/outliers.iqr.revenue.svg",
                }
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
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert '<img src="charts/outliers.iqr.revenue.svg"' in html


def test_outliers_no_img_when_chart_absent(tmp_path: Path) -> None:
    import render_report

    data = _base_findings()
    data["columns"] = [_column("revenue")]
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
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert "Row 42" in html or "row 42" in html.lower()
    assert 'src="charts/outliers' not in html


def test_outliers_dedupes_chart_per_method_column(tmp_path: Path) -> None:
    """Engine assigns the same chart path to every entry in a (method, column)
    group. Template should emit each unique chart only once."""
    import render_report

    data = _base_findings()
    data["columns"] = [_column("revenue")]
    data["outliers"] = {
        "by_method": {
            "iqr": [
                {
                    "row_index": 42,
                    "column": "revenue",
                    "value": 500.0,
                    "z_iqr": 4.2,
                    "chart": "charts/outliers.iqr.revenue.svg",
                },
                {
                    "row_index": 99,
                    "column": "revenue",
                    "value": 600.0,
                    "z_iqr": 5.0,
                    "chart": "charts/outliers.iqr.revenue.svg",
                },
            ],
            "mad": [],
            "isolation_forest": None,
            "local_outlier_factor": None,
        },
        "agreement_matrix": [],
        "agreement_summary": {"high": 0, "review": 0, "low": 0},
    }
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    matches = re.findall(r'<img src="charts/outliers\.iqr\.revenue\.svg"', html)
    assert len(matches) == 1


# --- drivers section ---


def test_drivers_emits_figure_for_partial_dependence(tmp_path: Path) -> None:
    import render_report

    data = _base_findings()
    data["columns"] = [_column("revenue")]
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
        "agreement": [],
        "entries": [
            {
                "feature": "marketing_spend",
                "partial_dependence_chart": "charts/drivers.partial_dependence.svg",
            }
        ],
    }
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert '<img src="charts/drivers.partial_dependence.svg"' in html
    assert "marketing_spend" in html


def test_drivers_no_img_when_partial_dependence_none(tmp_path: Path) -> None:
    import render_report

    data = _base_findings()
    data["columns"] = [_column("revenue")]
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
        "agreement": [],
        "entries": [{"feature": "marketing_spend", "partial_dependence_chart": None}],
    }
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    # null path must NOT produce an <img>; drivers section still renders.
    assert 'src="charts/drivers' not in html
    assert "Target" in html  # text section still rendered


def test_drivers_no_entries_no_chart_section(tmp_path: Path) -> None:
    import render_report

    data = _base_findings()
    data["columns"] = [_column("revenue")]
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
        "agreement": [],
        "entries": [],
    }
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert 'src="charts/drivers' not in html


# --- time_series section ---


def _ts_block(charts: dict | None = None) -> dict:
    block = {
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
    if charts is not None:
        block["charts"] = charts
    return block


def test_time_series_emits_line_and_decomposition_figures(tmp_path: Path) -> None:
    import render_report

    data = _base_findings()
    data["columns"] = [_column("revenue")]
    data["time_series"] = _ts_block(
        charts={
            "line": "charts/time_series.line.svg",
            "decomposition": "charts/time_series.decomposition.svg",
        }
    )
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert '<img src="charts/time_series.line.svg"' in html
    assert '<img src="charts/time_series.decomposition.svg"' in html


def test_time_series_no_img_when_charts_absent(tmp_path: Path) -> None:
    import render_report

    data = _base_findings()
    data["columns"] = [_column("revenue")]
    data["time_series"] = _ts_block()  # no charts key
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert "increasing" in html.lower()  # text still rendered
    assert 'src="charts/time_series' not in html


def test_time_series_no_img_when_path_none(tmp_path: Path) -> None:
    import render_report

    data = _base_findings()
    data["columns"] = [_column("revenue")]
    data["time_series"] = _ts_block(charts={"line": None, "decomposition": None})
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert 'src="charts/time_series' not in html


def test_time_series_partial_only_line(tmp_path: Path) -> None:
    import render_report

    data = _base_findings()
    data["columns"] = [_column("revenue")]
    data["time_series"] = _ts_block(
        charts={"line": "charts/time_series.line.svg", "decomposition": None}
    )
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert '<img src="charts/time_series.line.svg"' in html
    assert '<img src="charts/time_series.decomposition.svg"' not in html


# --- cross-section: schema validation passes after consumption ---


def test_render_succeeds_with_full_chart_population(tmp_path: Path) -> None:
    """End-to-end check: a fully-populated chart-bearing findings dict
    renders without StrictUndefined or jinja errors."""
    import render_report

    data = _base_findings()
    data["columns"] = [
        _column(
            "revenue",
            charts={
                "histogram": "charts/revenue.histogram.svg",
                "boxplot": "charts/revenue.boxplot.svg",
            },
        ),
        _column(
            "cost", charts={"histogram": "charts/cost.histogram.svg", "boxplot": None}
        ),
    ]
    data["outliers"] = {
        "by_method": {
            "iqr": [
                {
                    "row_index": 1,
                    "column": "revenue",
                    "value": 9.0,
                    "z_iqr": 3.5,
                    "chart": "charts/outliers.iqr.revenue.svg",
                }
            ],
            "mad": [],
            "isolation_forest": None,
            "local_outlier_factor": None,
        },
        "agreement_matrix": [],
        "agreement_summary": {"high": 0, "review": 0, "low": 0},
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
        "agreement": [],
        "entries": [
            {"feature": "cost", "partial_dependence_chart": "charts/drivers.cost.svg"}
        ],
    }
    data["time_series"] = _ts_block(
        charts={
            "line": "charts/time_series.line.svg",
            "decomposition": "charts/time_series.decomposition.svg",
        }
    )
    render_report.render_hub(data, out=tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    # All five chart kinds present.
    assert '<img src="charts/revenue.histogram.svg"' in html
    assert '<img src="charts/revenue.boxplot.svg"' in html
    assert '<img src="charts/cost.histogram.svg"' in html
    assert '<img src="charts/outliers.iqr.revenue.svg"' in html
    assert '<img src="charts/drivers.cost.svg"' in html
    assert '<img src="charts/time_series.line.svg"' in html
