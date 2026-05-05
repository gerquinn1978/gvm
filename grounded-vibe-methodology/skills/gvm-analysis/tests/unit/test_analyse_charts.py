"""Tests for `scripts/analyse.py::_render_charts` — engine wiring of
`_shared/charts.py` (P19-C02).

The helper provisions ``<output_dir>/charts/``, calls each chart family
guarded by try/except, populates the schema chart-path fields on success,
and appends a `chart_render_failed: ...` warning to `provenance.warnings`
on failure. Charts are mocked at the `analyse.charts_module` boundary so
unit tests never invoke matplotlib.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

import analyse
from _shared import findings


# ---------- Fixtures ------------------------------------------------------


def _build_data_with_columns(df: pd.DataFrame) -> dict[str, Any]:
    """Construct a minimal `findings`-shaped dict for the helper. Mirrors
    what `_populate_findings` writes for numeric columns: each col_entry
    has a non-null `stats` block so `_render_charts` selects it for
    histogram/boxplot.
    """
    data: dict[str, Any] = findings.build_empty_findings(
        provenance={
            "input_files": [
                {
                    "path": "x.csv",
                    "sha256": "0" * 64,
                    "mtime": "2026-04-27T00:00:00+00:00",
                    "rows": int(len(df)),
                    "cols": int(len(df.columns)),
                }
            ],
            "mode": "explore",
            "target_column": None,
            "baseline_file": None,
            "seed": 42,
            "sub_seeds": {},
            "timestamp": "2026-04-27T00:00:00Z",
            "preferences": {},
            "preferences_hash": "0" * 64,
            "lib_versions": {},
            "anonymised_input_detected": False,
            "anonymised_columns": [],
            "formula_columns": [],
            "sample_applied": None,
            "domain": None,
            "warnings": [],
            "time_column": None,
            "bootstrap_n_iter_used": 0,
        }
    )
    cols: list[dict[str, Any]] = []
    for name in df.columns:
        series = df[name]
        is_numeric = pd.api.types.is_numeric_dtype(
            series
        ) and not pd.api.types.is_bool_dtype(series)
        cols.append(
            {
                "name": str(name),
                "dtype": str(series.dtype),
                "n_total": int(series.size),
                "n_non_null": int(series.notna().sum()),
                "completeness_pct": 100.0,
                "missingness_classification": None,
                "stats": {"tier": "rich"} if is_numeric else None,
            }
        )
    data["columns"] = cols
    return data


def _make_path_returner(written: list[Path]):
    """Return a fake chart function that records its savepath kwarg and
    returns it as a Path (mimicking the real chart functions' contract)."""

    def _fake(*args: Any, **kwargs: Any) -> Path:
        sp = Path(kwargs["savepath"])
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text("<svg/>")
        written.append(sp)
        return sp

    return _fake


def _patch_all_charts_success(
    monkeypatch: pytest.MonkeyPatch, written: list[Path]
) -> None:
    fake = _make_path_returner(written)
    for name in (
        "histogram",
        "boxplot",
        "scatter",
        "line",
        "small_multiples",
        "bar",
    ):
        monkeypatch.setattr(analyse.charts_module, name, fake)


# ---------- Charts directory ----------------------------------------------


def test_render_charts_creates_charts_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
    data = _build_data_with_columns(df)
    written: list[Path] = []
    _patch_all_charts_success(monkeypatch, written)

    analyse._render_charts(data, df, tmp_path, {"per_column": [42]})

    assert (tmp_path / "charts").is_dir()


def test_render_charts_dir_creation_failure_records_warning_and_returns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
    data = _build_data_with_columns(df)

    real_mkdir = Path.mkdir

    def _boom(self: Path, *args: Any, **kwargs: Any) -> None:
        if self.name == "charts":
            raise OSError("permission denied")
        real_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", _boom)

    # Should not raise.
    analyse._render_charts(data, df, tmp_path, {"per_column": [42]})

    warnings = data["provenance"]["warnings"]
    assert any("charts directory creation failed" in w for w in warnings), warnings
    # No column charts should have been populated.
    assert data["columns"][0].get("charts") in (
        None,
        {"histogram": None, "boxplot": None},
        {},
    )


# ---------- Per-column charts ---------------------------------------------


def test_render_charts_populates_column_chart_paths_on_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    df = pd.DataFrame({"score": [1.0, 2.0, 3.0, 4.0]})
    data = _build_data_with_columns(df)
    written: list[Path] = []
    _patch_all_charts_success(monkeypatch, written)

    analyse._render_charts(data, df, tmp_path, {"per_column": [42]})

    col = data["columns"][0]
    assert col["charts"]["histogram"] == "charts/score.histogram.svg"
    assert col["charts"]["boxplot"] == "charts/score.boxplot.svg"


def test_render_charts_skips_non_numeric_columns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    df = pd.DataFrame({"label": ["x", "y", "z"]})
    data = _build_data_with_columns(df)
    written: list[Path] = []
    _patch_all_charts_success(monkeypatch, written)

    analyse._render_charts(data, df, tmp_path, {"per_column": []})

    col = data["columns"][0]
    # Non-numeric → no charts dict populated (or charts==None).
    assert col.get("charts") is None or col["charts"] == {
        "histogram": None,
        "boxplot": None,
    }


def test_render_charts_records_warning_when_histogram_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    df = pd.DataFrame({"score": [1.0, 2.0, 3.0]})
    data = _build_data_with_columns(df)
    written: list[Path] = []
    _patch_all_charts_success(monkeypatch, written)

    def _hist_boom(*a: Any, **kw: Any) -> Path:
        raise ValueError("boom")

    monkeypatch.setattr(analyse.charts_module, "histogram", _hist_boom)

    analyse._render_charts(data, df, tmp_path, {"per_column": [42]})

    col = data["columns"][0]
    assert col["charts"]["histogram"] is None
    # Boxplot still works.
    assert col["charts"]["boxplot"] == "charts/score.boxplot.svg"
    warnings = data["provenance"]["warnings"]
    assert any(
        "chart_render_failed" in w and "kind=histogram" in w and "score" in w
        for w in warnings
    ), warnings


def test_render_charts_records_warning_when_boxplot_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    df = pd.DataFrame({"score": [1.0, 2.0, 3.0]})
    data = _build_data_with_columns(df)
    written: list[Path] = []
    _patch_all_charts_success(monkeypatch, written)

    def _box_boom(*a: Any, **kw: Any) -> Path:
        raise RuntimeError("boom")

    monkeypatch.setattr(analyse.charts_module, "boxplot", _box_boom)

    analyse._render_charts(data, df, tmp_path, {"per_column": [42]})

    col = data["columns"][0]
    assert col["charts"]["histogram"] == "charts/score.histogram.svg"
    assert col["charts"]["boxplot"] is None
    warnings = data["provenance"]["warnings"]
    assert any("chart_render_failed" in w and "kind=boxplot" in w for w in warnings), (
        warnings
    )


def test_render_charts_does_not_raise_on_unexpected_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    df = pd.DataFrame({"score": [1.0, 2.0]})
    data = _build_data_with_columns(df)
    written: list[Path] = []
    _patch_all_charts_success(monkeypatch, written)

    def _hist_boom(*a: Any, **kw: Any) -> Path:
        raise Exception("unexpected")

    monkeypatch.setattr(analyse.charts_module, "histogram", _hist_boom)

    # Must not raise.
    analyse._render_charts(data, df, tmp_path, {"per_column": [42]})


def test_render_charts_slug_collision_disambiguates_filenames(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two columns whose slugs collide ('Score' and 'score' both → 'score')
    must not overwrite each other's SVG. The helper must produce distinct
    filenames and emit a collision warning."""
    df = pd.DataFrame({"Score": [1.0, 2.0, 3.0], "score": [4.0, 5.0, 6.0]})
    data = _build_data_with_columns(df)
    written: list[Path] = []
    _patch_all_charts_success(monkeypatch, written)

    analyse._render_charts(data, df, tmp_path, {"per_column": [1, 2]})

    paths = [
        data["columns"][0]["charts"]["histogram"],
        data["columns"][1]["charts"]["histogram"],
    ]
    assert paths[0] != paths[1], paths
    warnings = data["provenance"]["warnings"]
    assert any("chart filename collision" in w for w in warnings), warnings


def test_render_charts_drivers_no_features_yields_empty_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    df = pd.DataFrame({"a": [1.0, 2.0]})
    data = _build_data_with_columns(df)
    data["drivers"] = {"target": "y", "agreement": {}, "method_results": {}}
    written: list[Path] = []
    _patch_all_charts_success(monkeypatch, written)

    analyse._render_charts(data, df, tmp_path, {"per_column": []})

    assert data["drivers"]["entries"] == []


def test_render_charts_survives_unguarded_inner_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failure in per-column setup (slugify, filename allocation) is
    isolated to that column's column_setup guard — it does NOT bubble to
    the outer pass-level catch-all and does NOT abort subsequent
    columns. ADR-201 graceful degradation extends to setup statements.
    """
    df = pd.DataFrame({"score": [1.0, 2.0, 3.0], "other": [4.0, 5.0, 6.0]})
    data = _build_data_with_columns(df)

    def _slugify_boom(_name: str) -> str:
        raise RuntimeError("slugify blew up")

    monkeypatch.setattr(analyse, "_slugify", _slugify_boom)

    written: list[Path] = []
    _patch_all_charts_success(monkeypatch, written)

    # Must not raise.
    analyse._render_charts(data, df, tmp_path, {"per_column": [42, 43]})

    warnings = data["provenance"]["warnings"]
    # Both columns produce a column_setup warning (slugify raises for
    # both). No render_pass-level fallback fires because the column
    # guard contains the failure.
    setup_warnings = [w for w in warnings if "kind=column_setup" in w]
    assert len(setup_warnings) == 2, warnings
    assert all("kind=render_pass" not in w for w in warnings), warnings


def test_render_charts_outlier_unknown_column_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Outlier entries naming a column not in df.columns are skipped
    silently — no chart, no warning, no crash."""
    df = pd.DataFrame({"score": [1.0, 2.0, 3.0]})
    data = _build_data_with_columns(df)
    data["outliers"] = {
        "by_method": {
            "iqr": [{"row_index": 0, "column": "ghost", "value": 99.0, "z_iqr": 4.0}],
            "mad": None,
            "isolation_forest": None,
            "local_outlier_factor": None,
        },
        "agreement_matrix": {},
        "agreement_summary": {},
    }
    written: list[Path] = []
    _patch_all_charts_success(monkeypatch, written)

    analyse._render_charts(data, df, tmp_path, {"per_column": [42]})

    entry = data["outliers"]["by_method"]["iqr"][0]
    assert "chart" not in entry


# ---------- Outlier charts ------------------------------------------------


def test_render_charts_outlier_chart_per_method_column_group(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    df = pd.DataFrame({"score": [1.0, 2.0, 99.0, 100.0]})
    data = _build_data_with_columns(df)
    data["outliers"] = {
        "by_method": {
            "iqr": [
                {"row_index": 2, "column": "score", "value": 99.0, "z_iqr": 4.5},
                {"row_index": 3, "column": "score", "value": 100.0, "z_iqr": 4.7},
            ],
            "mad": None,
            "isolation_forest": None,
            "local_outlier_factor": None,
        },
        "agreement_matrix": {},
        "agreement_summary": {},
    }
    written: list[Path] = []
    _patch_all_charts_success(monkeypatch, written)

    analyse._render_charts(data, df, tmp_path, {"per_column": [42]})

    entries = data["outliers"]["by_method"]["iqr"]
    expected = "charts/outliers.iqr.score.svg"
    assert entries[0]["chart"] == expected
    assert entries[1]["chart"] == expected


def test_render_charts_outlier_failure_leaves_chart_absent_with_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    df = pd.DataFrame({"score": [1.0, 2.0, 99.0]})
    data = _build_data_with_columns(df)
    data["outliers"] = {
        "by_method": {
            "iqr": [{"row_index": 2, "column": "score", "value": 99.0, "z_iqr": 4.5}],
            "mad": None,
            "isolation_forest": None,
            "local_outlier_factor": None,
        },
        "agreement_matrix": {},
        "agreement_summary": {},
    }
    written: list[Path] = []
    _patch_all_charts_success(monkeypatch, written)

    def _scatter_boom(*a: Any, **kw: Any) -> Path:
        raise ValueError("boom")

    monkeypatch.setattr(analyse.charts_module, "scatter", _scatter_boom)

    analyse._render_charts(data, df, tmp_path, {"per_column": [42]})

    entry = data["outliers"]["by_method"]["iqr"][0]
    assert "chart" not in entry or entry["chart"] is None
    warnings = data["provenance"]["warnings"]
    assert any(
        "chart_render_failed" in w
        and "kind=scatter" in w
        and "section=outliers" in w
        and "iqr" in w
        for w in warnings
    ), warnings


# ---------- Driver charts -------------------------------------------------


def test_render_charts_drivers_entries_built_from_agreement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    df = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
    data = _build_data_with_columns(df)
    data["drivers"] = {
        "target": "y",
        "agreement": {"top_k_features": ["a", "b"]},
        "method_results": {
            "rf_importance": [
                {"feature": "a", "importance": 0.6},
                {"feature": "b", "importance": 0.4},
            ]
        },
    }
    written: list[Path] = []
    _patch_all_charts_success(monkeypatch, written)

    analyse._render_charts(data, df, tmp_path, {"per_column": []})

    entries = data["drivers"].get("entries")
    assert isinstance(entries, list)
    assert len(entries) == 2
    expected = "charts/drivers.partial_dependence.svg"
    assert entries[0]["feature"] == "a"
    assert entries[0]["partial_dependence_chart"] == expected
    assert entries[1]["partial_dependence_chart"] == expected


def test_render_charts_drivers_no_top_features_records_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    df = pd.DataFrame({"a": [1.0, 2.0]})
    data = _build_data_with_columns(df)
    data["drivers"] = {"target": "y", "agreement": {}, "method_results": {}}
    written: list[Path] = []
    _patch_all_charts_success(monkeypatch, written)

    analyse._render_charts(data, df, tmp_path, {"per_column": []})

    assert "entries" not in data["drivers"] or data["drivers"]["entries"] == []
    warnings = data["provenance"]["warnings"]
    assert any(
        "chart_skipped" in w and "section=drivers" in w and "no top features" in w
        for w in warnings
    ), warnings


# ---------- Time-series charts --------------------------------------------


def test_render_charts_time_series_line_populated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    df = pd.DataFrame(
        {
            "ts": pd.date_range("2024-01-01", periods=5, freq="D"),
            "v": [1.0, 2.0, 3.0, 4.0, 5.0],
        }
    )
    data = _build_data_with_columns(df)
    data["time_series"] = {
        "time_column": "ts",
        "cadence": "daily",
        "median_gap_seconds": 86400,
        "expected_cadence_seconds": 86400,
        "gaps": [],
        "stale": False,
        "multi_window_outliers": [],
        "trend": {},
        "seasonality": None,
        "forecast": None,
    }
    written: list[Path] = []
    _patch_all_charts_success(monkeypatch, written)

    analyse._render_charts(data, df, tmp_path, {"per_column": [1, 2]})

    assert data["time_series"]["charts"]["line"] == "charts/time_series.line.svg"
    assert data["time_series"]["charts"]["decomposition"] is None


# ---------- Schema gate ---------------------------------------------------


def test_render_charts_output_validates_against_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    df = pd.DataFrame({"score": [1.0, 2.0, 3.0]})
    data = _build_data_with_columns(df)
    data["outliers"] = {
        "by_method": {
            "iqr": [{"row_index": 2, "column": "score", "value": 99.0, "z_iqr": 4.5}],
            "mad": None,
            "isolation_forest": None,
            "local_outlier_factor": None,
        },
        "agreement_matrix": {},
        "agreement_summary": {},
    }
    data["drivers"] = {
        "target": "y",
        "agreement": {"top_k_features": ["score"]},
        "method_results": {"rf_importance": [{"feature": "score", "importance": 1.0}]},
    }
    written: list[Path] = []
    _patch_all_charts_success(monkeypatch, written)

    analyse._render_charts(data, df, tmp_path, {"per_column": [42]})

    # Should not raise.
    findings.validate(data)
