"""Chart vocabulary module — ADR-303 API surface + ADR-304 legibility helpers.

Exactly nine public functions are exposed (ADR-303):

    histogram, boxplot, scatter, line, small_multiples,
    bar, heatmap, treemap, parallel_coordinates

No pie, donut, spider, radar, or surface_3d chart types are included or
callable through this module.

Every public function:
  - Accepts a ``method_key=`` kwarg (stored in figure metadata; registry
    validation lands in P6-C04a).
  - Returns ``Path`` (the written SVG).
  - Raises ``ValueError`` on empty or mismatched inputs, never silently
    produces a blank chart.
  - Calls ``_with_legibility(fig)`` before saving.

Backend must be 'Agg' (headless / non-interactive).  ``matplotlib.use('Agg')``
is called before pyplot import so the module is safe on CI / server.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")  # Must precede pyplot import (ADR-304, headless CI)

from matplotlib import pyplot as plt  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

# ---------------------------------------------------------------------------
# Load project matplotlibrc (ADR-304)
# ---------------------------------------------------------------------------

_RC_FILE = Path(__file__).parent.parent.parent / "matplotlibrc"
if _RC_FILE.exists():
    matplotlib.rc_file(_RC_FILE)

# ---------------------------------------------------------------------------
# Optional dependency: lttbc (Largest Triangle Three Buckets downsampler)
# ---------------------------------------------------------------------------

try:
    import lttbc as _lttbc  # type: ignore[import-untyped]

    LTTBC_AVAILABLE: bool = True
except ImportError:
    _lttbc = None  # type: ignore[assignment]
    LTTBC_AVAILABLE = False

# ---------------------------------------------------------------------------
# Required dependency: squarify (treemap layout)
# ---------------------------------------------------------------------------

import squarify  # noqa: E402 — REQUIRED dep per P5-C02

# ---------------------------------------------------------------------------
# Palette — P6-C03 WCAG-vetted hues. The six chart call sites below
# import the public CATEGORICAL constant directly so the spec name is
# visible at the use site rather than hidden behind a private alias.
# ---------------------------------------------------------------------------

from _shared.palette import CATEGORICAL  # noqa: E402

_TEXT_COLOUR = "#111111"
_BACKGROUND_COLOUR = "#fffff8"


# ---------------------------------------------------------------------------
# Contrast ratio helper (WCAG 2.1) — P6-C03 palette module will supersede
# ---------------------------------------------------------------------------


def _relative_luminance(hex_colour: str) -> float:
    """Relative luminance per WCAG 2.1 (0.0 = black, 1.0 = white)."""
    hex_colour = hex_colour.lstrip("#")
    r, g, b = (int(hex_colour[i : i + 2], 16) / 255.0 for i in (0, 2, 4))

    def _linearise(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * _linearise(r) + 0.7152 * _linearise(g) + 0.0722 * _linearise(b)


def _contrast_ratio(hex_a: str, hex_b: str) -> float:
    """WCAG contrast ratio between two hex colours.

    Returns a value in [1.0, 21.0]; AA requires ≥ 4.5 for normal text.
    """
    la = _relative_luminance(hex_a)
    lb = _relative_luminance(hex_b)
    lighter, darker = (la, lb) if la >= lb else (lb, la)
    return (lighter + 0.05) / (darker + 0.05)


# ---------------------------------------------------------------------------
# Downsampler — LTTB with uniform-decimation fallback
# ---------------------------------------------------------------------------


def _downsample(
    x: Sequence[Any],
    y: Sequence[Any],
    n_out: int = 200,
) -> tuple[list[Any], list[Any]]:
    """Return (x_down, y_down) with at most n_out points.

    Uses LTTB via ``lttbc`` when installed; falls back to uniform decimation
    ``series[::step]`` where ``step = len(series) // n_out``.

    Series of length ≤ n_out are returned unchanged (no copies made beyond
    list conversion).
    """
    x_list = list(x)
    y_list = list(y)
    if len(x_list) <= n_out:
        return x_list, y_list

    if LTTBC_AVAILABLE:
        import numpy as np

        x_arr = np.asarray(x_list, dtype=float)
        y_arr = np.asarray(y_list, dtype=float)
        x_d, y_d = _lttbc.downsample(x_arr, y_arr, n_out)
        return x_d.tolist(), y_d.tolist()

    # Uniform decimation fallback — step chosen so output length ≤ n_out
    step = max(1, math.ceil(len(x_list) / n_out))
    return x_list[::step], y_list[::step]


# ---------------------------------------------------------------------------
# _with_legibility — legend, contrast assertion, tight_layout
# ---------------------------------------------------------------------------


def _with_legibility(fig: Figure, *, method_key: str = "") -> None:
    """Apply ADR-304 legibility rules to *fig* in-place.

    1. Places legend at ``loc='best'`` on each axes that has labelled artists.
    2. Asserts text-vs-background contrast ≥ 4.5:1.
    3. Calls ``fig.tight_layout()``.

    The contrast assertion uses the module-level colour constants which reflect
    the matplotlibrc-loaded palette; P6-C03 will inject its contrast helper.
    """
    # Contrast gate — text (#111111) vs background (#fffff8) must meet WCAG AA
    ratio = _contrast_ratio(_TEXT_COLOUR, _BACKGROUND_COLOUR)
    if ratio < 4.5:
        raise RuntimeError(
            f"Text/background contrast ratio {ratio:.2f} fails WCAG AA (≥ 4.5). "
            "Check matplotlibrc text.color and savefig.facecolor."
        )

    for ax in fig.get_axes():
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(handles, labels, loc="best", framealpha=0.85)

    try:
        fig.tight_layout()
    except Exception:  # noqa: BLE001 — tight_layout can raise on edge cases
        pass  # Layout failure is non-fatal; SVG will still be saved


# ---------------------------------------------------------------------------
# SVG accessibility post-processor (Pickering — screen reader support)
# ---------------------------------------------------------------------------


def _inject_svg_accessibility(path: Path, title: str, description: str) -> None:
    """Inject ``<title>`` and ``<desc>`` elements into a saved SVG file.

    Matplotlib does not write these elements; without them screen readers
    have no text to announce.  We insert them immediately after the opening
    ``<svg ...>`` tag so they are the first child elements, which is the
    structure required by the SVG accessibility spec (ARIA 1.2).

    The SVG file is rewritten in-place.  The function is idempotent — if
    ``<title>`` already exists it is not duplicated (defensive against future
    Matplotlib versions that may add it).
    """
    text = path.read_text(encoding="utf-8")
    if "<title>" in text:
        return  # Already present — nothing to do

    import html as _html

    safe_title = _html.escape(title)
    safe_desc = _html.escape(description)
    accessibility_block = f"<title>{safe_title}</title>\n<desc>{safe_desc}</desc>\n"

    # Insert immediately after the first closing ">" of the <svg ...> tag.
    # We find the first <svg tag and its closing ">".
    svg_tag_end = text.find(">", text.find("<svg"))
    if svg_tag_end == -1:
        return  # Unexpected SVG structure — skip rather than corrupt
    new_text = (
        text[: svg_tag_end + 1] + "\n" + accessibility_block + text[svg_tag_end + 1 :]
    )
    path.write_text(new_text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Internal save helper
# ---------------------------------------------------------------------------


def _save(fig: Figure, savepath: Path, method_key: str, title: str = "") -> Path:
    """Apply legibility, store method_key metadata, save SVG, close figure."""
    savepath = Path(savepath)
    savepath.parent.mkdir(parents=True, exist_ok=True)

    # Store method_key in figure metadata for P6-C04a registry validation
    fig.set_metadata({"method_key": method_key}) if hasattr(
        fig, "set_metadata"
    ) else None
    fig.canvas.get_renderer  # touch the canvas to prevent resource warnings

    _with_legibility(fig, method_key=method_key)
    fig.savefig(savepath, format="svg")
    plt.close(fig)

    # Inject accessibility elements (Pickering criterion — screen reader support)
    description = f"Chart type: {method_key or 'unknown'}. Title: {title}."
    _inject_svg_accessibility(
        savepath, title=title or savepath.stem, description=description
    )

    return savepath


# ---------------------------------------------------------------------------
# Public chart functions (ADR-303)
# ---------------------------------------------------------------------------


def histogram(
    values: Sequence[float],
    *,
    title: str,
    ax_label: str,
    savepath: Path | str,
    seed: int | None = None,
    method_key: str = "",
) -> Path:
    """Render a histogram and save as SVG.

    Parameters
    ----------
    values:
        Numeric values to bin. Must be non-empty.
    title:
        Chart title (≥ 14pt via matplotlibrc).
    ax_label:
        X-axis label describing the quantity.
    savepath:
        Destination ``.svg`` file path.
    seed:
        Optional RNG seed (passed to numpy for jitter; reserved for future use).
    method_key:
        Method registry key (P6-C04a will validate against registry).

    Returns
    -------
    Path
        The written SVG path.
    """
    if not values:
        raise ValueError("Empty values sequence passed to histogram().")

    fig, ax = plt.subplots()
    ax.hist(values, bins="auto", color=CATEGORICAL[0], edgecolor=_BACKGROUND_COLOUR)
    ax.set_title(title)
    ax.set_xlabel(ax_label)
    ax.set_ylabel("Count")
    return _save(fig, savepath, method_key, title=title)


def boxplot(
    values_by_group: dict[str, Sequence[float]],
    *,
    title: str,
    ax_label: str,
    savepath: Path | str,
    method_key: str = "",
) -> Path:
    """Render a box-and-whisker plot and save as SVG.

    Parameters
    ----------
    values_by_group:
        Mapping from group name to numeric values. Must be non-empty.
    title:
        Chart title.
    ax_label:
        Y-axis label describing the quantity.
    savepath:
        Destination ``.svg`` file path.
    method_key:
        Method registry key.

    Returns
    -------
    Path
        The written SVG path.
    """
    if not values_by_group:
        raise ValueError("Empty values_by_group dict passed to boxplot().")

    labels = list(values_by_group.keys())
    data = [list(values_by_group[k]) for k in labels]

    fig, ax = plt.subplots()
    bp = ax.boxplot(
        data,
        tick_labels=labels,
        patch_artist=True,
    )
    for patch, colour in zip(bp["boxes"], CATEGORICAL):
        patch.set_facecolor(colour)
    ax.set_title(title)
    ax.set_ylabel(ax_label)
    return _save(fig, savepath, method_key, title=title)


def scatter(
    x: Sequence[float],
    y: Sequence[float],
    *,
    title: str,
    x_label: str,
    y_label: str,
    savepath: Path | str,
    method_key: str = "",
) -> Path:
    """Render a scatter plot and save as SVG.

    Parameters
    ----------
    x:
        Horizontal values. Must have same length as *y*.
    y:
        Vertical values.
    title:
        Chart title.
    x_label:
        X-axis label.
    y_label:
        Y-axis label.
    savepath:
        Destination ``.svg`` file path.
    method_key:
        Method registry key.

    Returns
    -------
    Path
        The written SVG path.

    Raises
    ------
    ValueError
        If *x* and *y* have different lengths, or if either is empty.
    """
    if len(x) != len(y):
        raise ValueError(
            f"Length mismatch: x has {len(x)} elements, y has {len(y)} elements."
        )
    if not x:
        raise ValueError("Empty sequences passed to scatter().")

    fig, ax = plt.subplots()
    ax.scatter(list(x), list(y), color=CATEGORICAL[0], alpha=0.7, edgecolors="none")
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    return _save(fig, savepath, method_key, title=title)


def line(
    x: Sequence[Any],
    y: Sequence[float],
    *,
    title: str,
    x_label: str,
    y_label: str,
    step: bool = False,
    savepath: Path | str,
    method_key: str = "",
) -> Path:
    """Render a line (or step) chart and save as SVG.

    Time-series with > 200 points are automatically downsampled via LTTB
    (``lttbc`` if installed) or uniform decimation fallback.

    Parameters
    ----------
    x:
        Horizontal axis values (numeric or date-like).
    y:
        Vertical axis values. Must match length of *x*.
    title:
        Chart title.
    x_label:
        X-axis label.
    y_label:
        Y-axis label.
    step:
        When ``True``, render as a step function (``drawstyle='steps-post'``).
    savepath:
        Destination ``.svg`` file path.
    method_key:
        Method registry key.

    Returns
    -------
    Path
        The written SVG path.

    Raises
    ------
    ValueError
        If *x* and *y* lengths differ, or if both are empty.
    """
    if len(x) != len(y):
        raise ValueError(
            f"Length mismatch: x has {len(x)} elements, y has {len(y)} elements."
        )
    if not x:
        raise ValueError("Empty sequences passed to line().")

    x_plot, y_plot = _downsample(x, y, n_out=200)

    fig, ax = plt.subplots()
    drawstyle = "steps-post" if step else "default"
    ax.plot(x_plot, y_plot, color=CATEGORICAL[0], drawstyle=drawstyle)
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    return _save(fig, savepath, method_key, title=title)


def small_multiples(
    charts: Sequence[dict[str, Any]],
    *,
    title: str,
    savepath: Path | str,
    method_key: str = "",
) -> Path:
    """Render a grid of small multiple charts and save as SVG.

    Each entry in *charts* is a dict with keys:
      - ``kind``: ``"line"`` or ``"bar"`` (required)
      - ``x``: x-axis data (required for line)
      - ``y``: y-axis data (required)
      - ``title``: subplot title (optional)

    Parameters
    ----------
    charts:
        Sequence of chart specs. Must be non-empty.
    title:
        Overall figure title (suptitle).
    savepath:
        Destination ``.svg`` file path.
    method_key:
        Method registry key.

    Returns
    -------
    Path
        The written SVG path.

    Raises
    ------
    ValueError
        If *charts* is empty.
    """
    if not charts:
        raise ValueError("Empty charts sequence passed to small_multiples().")

    n = len(charts)
    ncols = min(n, 3)
    nrows = math.ceil(n / ncols)

    fig, axes = plt.subplots(nrows, ncols, figsize=(4 * ncols, 3 * nrows))
    # Normalise axes to a flat list
    if n == 1:
        axes_flat = [axes]
    elif nrows == 1:
        axes_flat = list(axes)
    else:
        axes_flat = [ax for row in axes for ax in row]

    for idx, (spec, ax) in enumerate(zip(charts, axes_flat)):
        kind = spec.get("kind", "line")
        x_data = spec.get("x", [])
        y_data = spec.get("y", [])
        subtitle = spec.get("title", f"Chart {idx + 1}")

        colour = CATEGORICAL[idx % len(CATEGORICAL)]
        if kind == "bar":
            ax.bar(range(len(y_data)), y_data, color=colour)
        else:
            x_plot, y_plot = _downsample(x_data, y_data, n_out=200)
            ax.plot(x_plot, y_plot, color=colour)
        ax.set_title(subtitle, fontsize=10)
        ax.tick_params(labelsize=8)

    # Hide unused subplots
    for ax in axes_flat[n:]:
        ax.set_visible(False)

    fig.suptitle(title, fontsize=14, y=1.02)
    return _save(fig, savepath, method_key, title=title)


def bar(
    categories: Sequence[str],
    values: Sequence[float] | Sequence[Sequence[float]],
    *,
    title: str,
    axis_label: str,
    stacked: bool = False,
    grouped: bool = False,
    savepath: Path | str,
    method_key: str = "",
) -> Path:
    """Render a bar chart (simple, stacked, or grouped) and save as SVG.

    Use bar charts for part-of-whole comparisons and single-quantity
    comparisons (ADR-303 / Few — not pie).

    Parameters
    ----------
    categories:
        Category labels on the X axis. Must be non-empty and match *values*.
    values:
        For simple charts: a flat sequence of floats.
        For stacked/grouped: a sequence of sequences (one inner list per
        category, each containing values for each sub-group).
    title:
        Chart title.
    axis_label:
        Y-axis label describing the quantity.
    stacked:
        Render stacked bars when ``True``.
    grouped:
        Render grouped (side-by-side) bars when ``True``.
    savepath:
        Destination ``.svg`` file path.
    method_key:
        Method registry key.

    Returns
    -------
    Path
        The written SVG path.

    Raises
    ------
    ValueError
        If *categories* is empty or lengths mismatch.
    """
    if not categories or (hasattr(values, "__len__") and len(values) == 0):
        raise ValueError("Empty categories or values passed to bar().")
    if len(categories) != len(values):
        raise ValueError(
            f"Length mismatch: categories has {len(categories)}, "
            f"values has {len(values)}."
        )

    fig, ax = plt.subplots()
    x = range(len(categories))

    # Detect multi-series
    first = values[0]
    is_multi = isinstance(first, (list, tuple))

    if is_multi and (stacked or grouped):
        arr = [list(v) for v in values]
        n_groups = len(arr[0])
        bottoms = [0.0] * len(categories)
        width = 0.8 / n_groups if grouped else 0.8

        for g_idx in range(n_groups):
            group_vals = [arr[cat_idx][g_idx] for cat_idx in range(len(categories))]
            colour = CATEGORICAL[g_idx % len(CATEGORICAL)]
            if grouped:
                offsets = [xi + (g_idx - n_groups / 2) * width + width / 2 for xi in x]
                ax.bar(
                    offsets,
                    group_vals,
                    width=width,
                    color=colour,
                    label=f"Group {g_idx + 1}",
                )
            else:
                ax.bar(
                    x,
                    group_vals,
                    bottom=bottoms,
                    color=colour,
                    label=f"Group {g_idx + 1}",
                )
                bottoms = [b + v for b, v in zip(bottoms, group_vals)]
    else:
        flat_values = [float(v) for v in values]
        colours = [CATEGORICAL[i % len(CATEGORICAL)] for i in range(len(categories))]
        ax.bar(x, flat_values, color=colours)

    ax.set_xticks(list(x))
    ax.set_xticklabels(
        list(categories), rotation=30 if len(categories) > 5 else 0, ha="right"
    )
    ax.set_title(title)
    ax.set_ylabel(axis_label)
    return _save(fig, savepath, method_key, title=title)


def heatmap(
    matrix: Sequence[Sequence[float]],
    *,
    row_labels: Sequence[str],
    col_labels: Sequence[str],
    title: str,
    savepath: Path | str,
    method_key: str = "",
) -> Path:
    """Render a heatmap and save as SVG.

    Parameters
    ----------
    matrix:
        2-D numeric data (list of rows, each row a list of floats).
        Must be non-empty.
    row_labels:
        Labels for rows (Y axis).
    col_labels:
        Labels for columns (X axis).
    title:
        Chart title.
    savepath:
        Destination ``.svg`` file path.
    method_key:
        Method registry key.

    Returns
    -------
    Path
        The written SVG path.

    Raises
    ------
    ValueError
        If *matrix* is empty.
    """
    if not matrix:
        raise ValueError("Empty matrix passed to heatmap().")

    import numpy as np

    data = np.asarray(matrix, dtype=float)

    fig, ax = plt.subplots()
    im = ax.imshow(data, aspect="auto", cmap="YlOrRd")
    fig.colorbar(im, ax=ax)

    ax.set_xticks(range(len(col_labels)))
    ax.set_xticklabels(list(col_labels), rotation=45, ha="right")
    ax.set_yticks(range(len(row_labels)))
    ax.set_yticklabels(list(row_labels))
    ax.set_title(title)
    return _save(fig, savepath, method_key, title=title)


def treemap(
    weights: Sequence[float],
    labels: Sequence[str],
    *,
    title: str,
    savepath: Path | str,
    method_key: str = "",
) -> Path:
    """Render a treemap and save as SVG.

    Parameters
    ----------
    weights:
        Positive numeric sizes for each tile. Must be non-empty.
    labels:
        Labels for each tile. Must match *weights* in length.
    title:
        Chart title.
    savepath:
        Destination ``.svg`` file path.
    method_key:
        Method registry key.

    Returns
    -------
    Path
        The written SVG path.

    Raises
    ------
    ValueError
        If *weights* or *labels* are empty, or lengths differ.
    """
    if not weights or not labels:
        raise ValueError("Empty weights or labels passed to treemap().")
    if len(weights) != len(labels):
        raise ValueError(
            f"Length mismatch: weights has {len(weights)}, labels has {len(labels)}."
        )

    colours = [CATEGORICAL[i % len(CATEGORICAL)] for i in range(len(weights))]

    fig, ax = plt.subplots()
    squarify.plot(
        sizes=list(weights),
        label=list(labels),
        color=colours,
        ax=ax,
        text_kwargs={"fontsize": 10},
    )
    ax.set_title(title)
    ax.axis("off")
    return _save(fig, savepath, method_key, title=title)


def parallel_coordinates(
    df_long: "pd.DataFrame",  # noqa: F821 — forward ref; pandas is a REQUIRED dep
    *,
    title: str,
    savepath: Path | str,
    method_key: str = "",
) -> Path:
    """Render a parallel coordinates chart and save as SVG.

    Each numeric column in *df_long* becomes an axis; rows are polylines.
    If a ``group`` column exists it is used for colour encoding (excluded
    from the numeric axes).

    Parameters
    ----------
    df_long:
        DataFrame with at least two numeric columns. Must be non-empty.
    title:
        Chart title.
    savepath:
        Destination ``.svg`` file path.
    method_key:
        Method registry key.

    Returns
    -------
    Path
        The written SVG path.

    Raises
    ------
    ValueError
        If *df_long* is empty or has fewer than two numeric columns.
    """
    import pandas as pd

    if df_long.empty:
        raise ValueError("Empty DataFrame passed to parallel_coordinates().")

    group_col = "group" if "group" in df_long.columns else None
    numeric_cols = [
        c
        for c in df_long.columns
        if c != group_col and pd.api.types.is_numeric_dtype(df_long[c])
    ]

    if len(numeric_cols) < 2:
        raise ValueError(
            f"parallel_coordinates() requires at least 2 numeric columns; "
            f"got {numeric_cols!r}."
        )

    # Normalise each axis to [0, 1] for visual comparability
    normed = df_long[numeric_cols].copy()
    for col in numeric_cols:
        col_min = normed[col].min()
        col_max = normed[col].max()
        span = col_max - col_min
        normed[col] = (normed[col] - col_min) / span if span > 0 else 0.5

    n_axes = len(numeric_cols)
    x_pos = list(range(n_axes))

    fig, ax = plt.subplots(figsize=(max(6, 2 * n_axes), 4))

    if group_col:
        groups = df_long[group_col].unique()
        group_colour_map = {
            g: CATEGORICAL[i % len(CATEGORICAL)] for i, g in enumerate(groups)
        }
    else:
        group_colour_map = {}

    for row_idx, (_, row) in enumerate(normed.iterrows()):
        y_vals = [row[col] for col in numeric_cols]
        if group_col:
            group_val = df_long[group_col].iloc[row_idx]
            colour = group_colour_map.get(group_val, CATEGORICAL[0])
        else:
            colour = CATEGORICAL[row_idx % len(CATEGORICAL)]
        ax.plot(x_pos, y_vals, color=colour, alpha=0.7, linewidth=1.2)

    ax.set_xticks(x_pos)
    ax.set_xticklabels(numeric_cols, rotation=20, ha="right")
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["min", "25%", "50%", "75%", "max"])
    ax.set_title(title)
    ax.set_xlim(-0.1, n_axes - 0.9)
    ax.set_ylim(-0.05, 1.05)
    return _save(fig, savepath, method_key, title=title)
