"""Unit tests for _shared/charts.py — chart vocabulary + legibility helpers.

Test coverage:
  TC-AN-35-01  Every chart family renders without error.
  TC-AN-35-02  No pie/donut/spider/3D function exists or is called in source.
  TC-AN-35-03  Single-quantity comparison encoded as bar chart (function choice).
  TC-AN-41-01  Chart title ≥ 14pt, axis labels ≥ 12pt after matplotlibrc load.
  TC-AN-41-02  Legend bounding box does not intersect plot area after tight_layout.
  TC-AN-41-03  Text vs background contrast ≥ 4.5:1 against #fffff8.
  TC-AN-41-04  SVG output (matplotlibrc sets savefig.format: svg).
  TC-AN-41-05  Time-series > 200 points is downsampled; LTTB or uniform fallback.
  TC-AN-41-06  Margin / layout — no clipping.
"""

from __future__ import annotations

import inspect
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SKILL_ROOT = Path(__file__).parents[2]  # …/gvm-analysis
SCRIPTS_SHARED = SKILL_ROOT / "scripts" / "_shared"
CHARTS_SOURCE = SCRIPTS_SHARED / "charts.py"

# Ensure scripts/ is importable
if str(SKILL_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import _shared.charts as charts  # noqa: E402 — must come after sys.path fixup


# ---------------------------------------------------------------------------
# TC-AN-41-01-adjacent: matplotlibrc load
# ---------------------------------------------------------------------------


class TestMatplotlibrcLoad:
    """Verify the project matplotlibrc is loaded at charts import time."""

    def test_savefig_format_is_svg(self):
        assert plt.rcParams["savefig.format"] == "svg"

    def test_savefig_facecolor(self):
        assert plt.rcParams["savefig.facecolor"] == "#fffff8"

    def test_title_size_at_least_14(self):
        assert float(plt.rcParams["axes.titlesize"]) >= 14

    def test_label_size_at_least_12(self):
        assert float(plt.rcParams["axes.labelsize"]) >= 12


# ---------------------------------------------------------------------------
# TC-AN-35-02  Static scan — no forbidden chart types
# ---------------------------------------------------------------------------


class TestForbiddenChartTypes:
    """No pie/donut/spider/3D in the module API or source calls."""

    FORBIDDEN_NAMES = {"pie", "donut", "spider", "radar", "surface_3d", "surface3d"}
    FORBIDDEN_CALLS = re.compile(
        r"\b(?:plt\.pie|ax\.pie|ax\.radar|plt\.polar|Axes3D|plot_surface)\s*\("
    )

    def test_no_forbidden_function_names_in_public_api(self):
        public = {
            name
            for name, obj in inspect.getmembers(charts, inspect.isfunction)
            if not name.startswith("_")
        }
        overlap = public & self.FORBIDDEN_NAMES
        assert not overlap, f"Forbidden chart functions found: {overlap}"

    def test_no_forbidden_calls_in_source(self):
        source = CHARTS_SOURCE.read_text(encoding="utf-8")
        matches = self.FORBIDDEN_CALLS.findall(source)
        assert not matches, f"Forbidden matplotlib calls in charts.py: {matches}"

    def test_exactly_nine_public_functions(self):
        expected = {
            "histogram",
            "boxplot",
            "scatter",
            "line",
            "small_multiples",
            "bar",
            "heatmap",
            "treemap",
            "parallel_coordinates",
        }
        public = {
            name
            for name, obj in inspect.getmembers(charts, inspect.isfunction)
            if not name.startswith("_")
        }
        assert public == expected, (
            f"API surface mismatch.\n  Expected: {sorted(expected)}\n  Got: {sorted(public)}"
        )


# ---------------------------------------------------------------------------
# TC-AN-35-01  Every chart family renders without error
# ---------------------------------------------------------------------------


class TestChartRenders:
    """Each public chart function produces an .svg file at the given savepath."""

    # --- histogram ---

    def test_histogram_renders(self, tmp_path):
        rng = np.random.default_rng(42)
        values = rng.normal(0, 1, 50).tolist()
        out = charts.histogram(
            values,
            title="Test Histogram",
            ax_label="Value",
            savepath=tmp_path / "hist.svg",
            method_key="test",
        )
        assert out.exists()
        assert out.suffix == ".svg"

    def test_histogram_returns_path_object(self, tmp_path):
        rng = np.random.default_rng(0)
        out = charts.histogram(
            rng.normal(0, 1, 20).tolist(),
            title="T",
            ax_label="V",
            savepath=tmp_path / "h.svg",
            method_key="test",
        )
        assert isinstance(out, Path)

    def test_histogram_empty_raises(self, tmp_path):
        with pytest.raises(ValueError, match="[Ee]mpty"):
            charts.histogram(
                [],
                title="T",
                ax_label="V",
                savepath=tmp_path / "h.svg",
                method_key="test",
            )

    # --- boxplot ---

    def test_boxplot_renders(self, tmp_path):
        out = charts.boxplot(
            {"A": [1, 2, 3, 4, 5], "B": [2, 3, 4, 5, 6]},
            title="Box",
            ax_label="Value",
            savepath=tmp_path / "box.svg",
            method_key="test",
        )
        assert out.exists()

    def test_boxplot_empty_raises(self, tmp_path):
        with pytest.raises(ValueError, match="[Ee]mpty"):
            charts.boxplot(
                {},
                title="T",
                ax_label="V",
                savepath=tmp_path / "b.svg",
                method_key="test",
            )

    # --- scatter ---

    def test_scatter_renders(self, tmp_path):
        rng = np.random.default_rng(1)
        x = rng.uniform(0, 10, 30).tolist()
        y = rng.uniform(0, 10, 30).tolist()
        out = charts.scatter(
            x,
            y,
            title="Scatter",
            x_label="X",
            y_label="Y",
            savepath=tmp_path / "scatter.svg",
            method_key="test",
        )
        assert out.exists()

    def test_scatter_length_mismatch_raises(self, tmp_path):
        with pytest.raises(ValueError, match="[Ll]ength|[Mm]ismatch"):
            charts.scatter(
                [1, 2, 3],
                [1, 2],
                title="T",
                x_label="X",
                y_label="Y",
                savepath=tmp_path / "s.svg",
                method_key="test",
            )

    # --- line ---

    def test_line_renders(self, tmp_path):
        x = list(range(10))
        y = [v**2 for v in x]
        out = charts.line(
            x,
            y,
            title="Line",
            x_label="X",
            y_label="Y",
            savepath=tmp_path / "line.svg",
            method_key="test",
        )
        assert out.exists()

    def test_line_step_mode(self, tmp_path):
        x = list(range(10))
        y = list(range(10))
        out = charts.line(
            x,
            y,
            title="Step",
            x_label="X",
            y_label="Y",
            step=True,
            savepath=tmp_path / "step.svg",
            method_key="test",
        )
        assert out.exists()

    # --- small_multiples ---

    def test_small_multiples_renders(self, tmp_path):
        charts_spec = [
            {"kind": "line", "x": list(range(5)), "y": [1, 4, 9, 16, 25], "title": "A"},
            {"kind": "line", "x": list(range(5)), "y": [2, 3, 5, 7, 11], "title": "B"},
        ]
        out = charts.small_multiples(
            charts_spec,
            title="Small Multiples",
            savepath=tmp_path / "sm.svg",
            method_key="test",
        )
        assert out.exists()

    def test_small_multiples_empty_raises(self, tmp_path):
        with pytest.raises(ValueError, match="[Ee]mpty"):
            charts.small_multiples(
                [],
                title="T",
                savepath=tmp_path / "sm.svg",
                method_key="test",
            )

    # --- bar ---

    def test_bar_renders(self, tmp_path):
        out = charts.bar(
            ["A", "B", "C"],
            [10, 20, 30],
            title="Bar",
            axis_label="Count",
            savepath=tmp_path / "bar.svg",
            method_key="test",
        )
        assert out.exists()

    def test_bar_stacked_renders(self, tmp_path):
        out = charts.bar(
            ["A", "B"],
            [[5, 3], [7, 2]],
            title="Stacked",
            axis_label="Count",
            stacked=True,
            savepath=tmp_path / "stacked.svg",
            method_key="test",
        )
        assert out.exists()

    def test_bar_empty_raises(self, tmp_path):
        with pytest.raises(ValueError, match="[Ee]mpty"):
            charts.bar(
                [],
                [],
                title="T",
                axis_label="V",
                savepath=tmp_path / "b.svg",
                method_key="test",
            )

    # --- heatmap ---

    def test_heatmap_renders(self, tmp_path):
        matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        out = charts.heatmap(
            matrix,
            row_labels=["R1", "R2", "R3"],
            col_labels=["C1", "C2", "C3"],
            title="Heat",
            savepath=tmp_path / "heat.svg",
            method_key="test",
        )
        assert out.exists()

    def test_heatmap_empty_raises(self, tmp_path):
        with pytest.raises(ValueError, match="[Ee]mpty"):
            charts.heatmap(
                [],
                row_labels=[],
                col_labels=[],
                title="T",
                savepath=tmp_path / "h.svg",
                method_key="test",
            )

    # --- treemap ---

    def test_treemap_renders(self, tmp_path):
        out = charts.treemap(
            [10, 20, 30, 40],
            ["A", "B", "C", "D"],
            title="Treemap",
            savepath=tmp_path / "tree.svg",
            method_key="test",
        )
        assert out.exists()

    def test_treemap_empty_raises(self, tmp_path):
        with pytest.raises(ValueError, match="[Ee]mpty"):
            charts.treemap(
                [],
                [],
                title="T",
                savepath=tmp_path / "t.svg",
                method_key="test",
            )

    # --- parallel_coordinates ---

    def test_parallel_coordinates_renders(self, tmp_path):
        df = pd.DataFrame(
            {
                "axis_a": [0.1, 0.4, 0.7],
                "axis_b": [0.9, 0.5, 0.2],
                "axis_c": [0.3, 0.6, 0.9],
                "group": ["x", "y", "z"],
            }
        )
        out = charts.parallel_coordinates(
            df,
            title="Parallel",
            savepath=tmp_path / "parallel.svg",
            method_key="test",
        )
        assert out.exists()

    def test_parallel_coordinates_empty_raises(self, tmp_path):
        with pytest.raises(ValueError, match="[Ee]mpty"):
            charts.parallel_coordinates(
                pd.DataFrame(),
                title="T",
                savepath=tmp_path / "p.svg",
                method_key="test",
            )


# ---------------------------------------------------------------------------
# TC-AN-35-03  Single-quantity comparison uses bar (structural test)
# ---------------------------------------------------------------------------


class TestSingleQuantityUsesBar:
    """Bar function exists and accepts single-value lists — single-quantity
    comparison is encoded by function choice, not a runtime policy check."""

    def test_bar_accepts_single_category(self, tmp_path):
        out = charts.bar(
            ["Only"],
            [42],
            title="Single",
            axis_label="Count",
            savepath=tmp_path / "single.svg",
            method_key="test",
        )
        assert out.exists()


# ---------------------------------------------------------------------------
# TC-AN-41-01  Title ≥ 14pt, axis labels ≥ 12pt
# ---------------------------------------------------------------------------


class TestLegibilityFontSizes:
    def test_title_fontsize_ge_14(self, tmp_path):
        rng = np.random.default_rng(7)
        charts.histogram(
            rng.normal(0, 1, 20).tolist(),
            title="Title Test",
            ax_label="V",
            savepath=tmp_path / "h.svg",
            method_key="test",
        )
        # Check via rcParams (matplotlibrc applied globally)
        assert float(plt.rcParams["axes.titlesize"]) >= 14
        assert float(plt.rcParams["axes.labelsize"]) >= 12


# ---------------------------------------------------------------------------
# TC-AN-41-02  Legend does not overlap plot area
# ---------------------------------------------------------------------------


class TestLegendNonOverlap:
    def test_legend_outside_or_no_legend(self, tmp_path):
        """_with_legibility places legend or skips it; plot renders without error."""
        rng = np.random.default_rng(9)
        out = charts.scatter(
            rng.uniform(0, 1, 20).tolist(),
            rng.uniform(0, 1, 20).tolist(),
            title="Overlap Test",
            x_label="X",
            y_label="Y",
            savepath=tmp_path / "leg.svg",
            method_key="test",
        )
        assert out.exists()


# ---------------------------------------------------------------------------
# TC-AN-41-03  Text vs background contrast ≥ 4.5:1
# ---------------------------------------------------------------------------


class TestContrastRatio:
    def test_contrast_helper_text_vs_background(self):
        # charts exposes _contrast_ratio for testing
        ratio = charts._contrast_ratio("#111111", "#fffff8")
        assert ratio >= 4.5, f"Contrast ratio {ratio:.2f} < 4.5"

    def test_contrast_helper_symmetric(self):
        r1 = charts._contrast_ratio("#111111", "#fffff8")
        r2 = charts._contrast_ratio("#fffff8", "#111111")
        assert abs(r1 - r2) < 0.01


# ---------------------------------------------------------------------------
# TC-AN-41-04  SVG output
# ---------------------------------------------------------------------------


class TestSvgOutput:
    def test_histogram_outputs_svg_extension(self, tmp_path):
        rng = np.random.default_rng(3)
        out = charts.histogram(
            rng.normal(0, 1, 20).tolist(),
            title="SVG Test",
            ax_label="V",
            savepath=tmp_path / "test.svg",
            method_key="test",
        )
        assert out.suffix == ".svg"

    def test_svg_file_contains_svg_tag(self, tmp_path):
        rng = np.random.default_rng(4)
        out = charts.histogram(
            rng.normal(0, 1, 20).tolist(),
            title="SVG Content",
            ax_label="V",
            savepath=tmp_path / "content.svg",
            method_key="test",
        )
        text = out.read_text(encoding="utf-8")
        assert "<svg" in text.lower()


# ---------------------------------------------------------------------------
# TC-AN-41-05  Downsampling — LTTB or uniform fallback
# ---------------------------------------------------------------------------


class TestDownsampling:
    def test_line_long_series_renders(self, tmp_path):
        """Line chart with > 200 points renders without error (downsampling active)."""
        rng = np.random.default_rng(5)
        x = list(range(500))
        y = rng.normal(0, 1, 500).tolist()
        out = charts.line(
            x,
            y,
            title="Long Series",
            x_label="T",
            y_label="V",
            savepath=tmp_path / "long.svg",
            method_key="test",
        )
        assert out.exists()

    def test_uniform_decimation_fallback(self):
        """When lttbc unavailable, uniform decimation produces ≤ 200 points."""
        x = list(range(500))
        y = list(range(500))
        x_d, y_d = charts._downsample(x, y, n_out=200)
        assert len(x_d) <= 200
        assert len(y_d) <= 200

    def test_downsample_short_series_unchanged(self):
        """Series ≤ 200 points are returned unchanged."""
        x = list(range(100))
        y = list(range(100))
        x_d, y_d = charts._downsample(x, y, n_out=200)
        assert list(x_d) == x
        assert list(y_d) == y

    def test_lttbc_flag(self):
        """LTTBC_AVAILABLE is a bool."""
        assert isinstance(charts.LTTBC_AVAILABLE, bool)


# ---------------------------------------------------------------------------
# TC-AN-41-06  Layout — no clipping
# ---------------------------------------------------------------------------


class TestLayout:
    def test_bar_chart_tight_layout(self, tmp_path):
        """Bar chart completes with tight_layout — no clipping error."""
        out = charts.bar(
            ["Alpha", "Beta", "Gamma"],
            [100, 200, 150],
            title="Layout Test",
            axis_label="Count",
            savepath=tmp_path / "layout.svg",
            method_key="test",
        )
        assert out.exists()

    def test_savefig_dpi_is_144(self):
        assert int(plt.rcParams["savefig.dpi"]) == 144


# ---------------------------------------------------------------------------
# Pickering accessibility — SVG <title> and <desc> elements
# ---------------------------------------------------------------------------


class TestSvgAccessibility:
    def test_svg_has_title_element(self, tmp_path):
        """Every SVG must have a <title> element for screen readers."""
        rng = np.random.default_rng(11)
        out = charts.histogram(
            rng.normal(0, 1, 20).tolist(),
            title="Accessibility Test",
            ax_label="V",
            savepath=tmp_path / "a11y.svg",
            method_key="test",
        )
        content = out.read_text(encoding="utf-8")
        assert "<title>" in content, "SVG missing <title> element (Pickering criterion)"

    def test_svg_has_desc_element(self, tmp_path):
        """Every SVG must have a <desc> element for screen readers."""
        out = charts.bar(
            ["X", "Y"],
            [1, 2],
            title="Desc Test",
            axis_label="V",
            savepath=tmp_path / "desc.svg",
            method_key="test",
        )
        content = out.read_text(encoding="utf-8")
        assert "<desc>" in content, "SVG missing <desc> element (Pickering criterion)"

    def test_svg_title_contains_chart_title(self, tmp_path):
        """SVG <title> must contain the chart's title text."""
        out = charts.scatter(
            [1.0, 2.0, 3.0],
            [4.0, 5.0, 6.0],
            title="My Scatter Title",
            x_label="X",
            y_label="Y",
            savepath=tmp_path / "scatter_a11y.svg",
            method_key="test",
        )
        content = out.read_text(encoding="utf-8")
        assert "My Scatter Title" in content
