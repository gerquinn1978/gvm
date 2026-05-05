"""WCAG-vetted colour palette and secondary-encoding helpers for /gvm-analysis.

All colours are pre-tested for >= 4.5:1 contrast ratio against the Tufte
background ``#fffff8`` (WCAG 2.1 AA, normal text and graphical elements).

Colour-blind safety (ADR-310)
------------------------------
CATEGORICAL colours were derived from ColorBrewer Dark2 and darkened to pass
WCAG AA. Hue selection was validated against deuteranopia and protanopia
simulations using Coblis (https://www.color-blindness.com/coblis-color-blindness-simulator/).
The eight hues span teal, orange, purple, pink/magenta, green, amber, brown,
and grey — a spread that remains distinguishable under both red-green colour
vision deficiency simulations.

Sequential palette
-------------------
Nine-step single-hue blue ramp (#051f3e → #0e6fc9), monotonically increasing
in relative luminance. Suitable for heatmaps and density plots.

Diverging palette
------------------
Nine-step red–grey–blue ramp with a neutral grey midpoint (index 4). The
midpoint has higher luminance than both extremes, encoding the zero/neutral
centre. Suitable for correlation matrices and signed-deviation maps.

Secondary encoding
-------------------
``secondary_encoding(n)`` returns ``(colours, shapes)`` pairs so every
colour-encoded distinction also carries a shape marker. This satisfies
TC-NFR-7-03: no colour-only encoding. Callers zip the two lists when drawing
charts (e.g., ``zip(colours, shapes)`` for matplotlib scatter plots).

References
----------
- WCAG 2.1 Success Criterion 1.4.3: Contrast (Minimum)
  https://www.w3.org/TR/WCAG21/#contrast-minimum
- ColorBrewer: https://colorbrewer2.org/ — Dark2 palette as starting point.
- Coblis colour-blind simulator: https://www.color-blindness.com/coblis-color-blindness-simulator/
- ADR-310 in gvm-analysis specs.
"""

from __future__ import annotations

__all__ = [
    "BACKGROUND",
    "TEXT_PRIMARY",
    "TEXT_MUTED",
    "CATEGORICAL",
    "SEQUENTIAL",
    "DIVERGING",
    "SHAPES",
    "PATTERNS",
    "relative_luminance",
    "contrast_ratio",
    "secondary_encoding",
]

# ---------------------------------------------------------------------------
# Background (Tufte off-white)
# ---------------------------------------------------------------------------

BACKGROUND: str = "#fffff8"
"""Tufte background colour. All palette entries achieve >= 4.5:1 contrast vs this."""

# ---------------------------------------------------------------------------
# Text colours
# ---------------------------------------------------------------------------

TEXT_PRIMARY: str = "#111111"
"""Near-black for body text. Contrast vs #fffff8: ~18.8:1."""

TEXT_MUTED: str = "#444444"
"""Dark grey for axis labels, sidenotes, captions. Contrast vs #fffff8: ~9.7:1."""

# ---------------------------------------------------------------------------
# Categorical palette — 8 colours, WCAG AA vs #fffff8
# ---------------------------------------------------------------------------
# Derived from ColorBrewer Dark2, darkened to pass 4.5:1. Each colour retains
# the hue identity of its Dark2 parent for perceptual continuity.
#
# Hue mapping (Dark2 parent → darkened variant):
#   #1b9e77 (teal)    → #0d6b51  cr=6.5
#   #d95f02 (orange)  → #a34800  cr=6.0
#   #7570b3 (purple)  → #4d4b94  cr=7.6
#   #e7298a (pink)    → #a81569  cr=7.0
#   #66a61e (green)   → #3a6b0a  cr=6.4  (borderline original; darkened per ADR-310)
#   #e6ab02 (amber)   → #7a5800  cr=6.5
#   #a6761d (brown)   → #6b4a0d  cr=8.0
#   #666666 (grey)    → #555555  cr=7.4

CATEGORICAL: list[str] = [
    "#0d6b51",  # teal        (Dark2 #1b9e77, darkened)
    "#a34800",  # orange      (Dark2 #d95f02, darkened)
    "#4d4b94",  # purple      (Dark2 #7570b3, darkened)
    "#a81569",  # pink/magenta (Dark2 #e7298a, darkened)
    "#3a6b0a",  # green       (Dark2 #66a61e, darkened — borderline original)
    "#7a5800",  # amber/gold  (Dark2 #e6ab02, darkened)
    "#6b4a0d",  # brown       (Dark2 #a6761d, darkened)
    "#555555",  # grey        (Dark2 #666666, darkened)
]
"""8 categorical colours, each >= 4.5:1 vs BACKGROUND. Hues validated against
deuteranopia and protanopia simulations (Coblis). Match matplotlib/CSS conventions."""

# ---------------------------------------------------------------------------
# Sequential palette — 9-step single-hue blue ramp
# ---------------------------------------------------------------------------
# Monotonically increasing luminance (#051f3e is darkest, #0e6fc9 is least dark).
# All steps pass >= 4.5:1 vs #fffff8.

SEQUENTIAL: list[str] = [
    "#051f3e",  # step 1 — cr=16.4, lum=0.014
    "#07294f",  # step 2 — cr=14.5, lum=0.022
    "#083361",  # step 3 — cr=12.6, lum=0.033
    "#093d72",  # step 4 — cr=10.9, lum=0.046
    "#0a4784",  # step 5 — cr=9.3,  lum=0.062
    "#0b5195",  # step 6 — cr=8.0,  lum=0.081
    "#0c5ba7",  # step 7 — cr=6.8,  lum=0.104
    "#0d65b8",  # step 8 — cr=5.9,  lum=0.129
    "#0e6fc9",  # step 9 — cr=5.1,  lum=0.157
]
"""9-step blue sequential ramp. Monotonically increasing luminance. All steps
>= 4.5:1 vs BACKGROUND. Suitable for heatmaps and density encoding."""

# ---------------------------------------------------------------------------
# Diverging palette — 9-step red–grey–blue
# ---------------------------------------------------------------------------
# Zero-centred: red wing (indices 0–3), neutral grey midpoint (index 4),
# blue wing (indices 5–8). The midpoint has higher luminance than both extremes.
# All steps pass >= 4.5:1 vs #fffff8.

DIVERGING: list[str] = [
    "#67000d",  # red-1 (darkest) — cr=13.2, lum=0.029
    "#7a1218",  # red-2           — cr=10.9, lum=0.046
    "#8d2321",  # red-3           — cr=8.7,  lum=0.070
    "#9d3d34",  # red-4           — cr=6.6,  lum=0.108
    "#555555",  # neutral grey    — cr=7.4,  lum=0.091  ← midpoint
    "#2d4a7a",  # blue-4          — cr=8.8,  lum=0.069
    "#1e3a6e",  # blue-3          — cr=11.1, lum=0.044
    "#102b62",  # blue-2          — cr=13.5, lum=0.027
    "#051c52",  # blue-1 (darkest)— cr=16.2, lum=0.015
]
"""9-step red–grey–blue diverging ramp. Neutral grey midpoint (index 4) has
higher luminance than both extremes. All steps >= 4.5:1 vs BACKGROUND.
Suitable for correlation matrices and signed-deviation maps."""

# ---------------------------------------------------------------------------
# Secondary-encoding repertoires
# ---------------------------------------------------------------------------

SHAPES: list[str] = ["o", "s", "^", "D", "v", "P", "*", "X"]
"""8 filled matplotlib marker characters. Pairwise visually distinct.
Match the 8 CATEGORICAL colours in secondary_encoding()."""

PATTERNS: list[str] = ["/", "\\", "|", "-", "+", "x", "o", "."]
"""8 matplotlib hatch patterns. Used as an alternative to shapes in bar/area charts."""

# ---------------------------------------------------------------------------
# WCAG formulae
# ---------------------------------------------------------------------------


def relative_luminance(hex_color: str) -> float:
    """Convert a hex colour string to WCAG relative luminance.

    Implements the sRGB → linear-light → luminance formula from WCAG 2.1:
    https://www.w3.org/TR/WCAG21/#dfn-relative-luminance

    Args:
        hex_color: A 7-character hex string (``#`` + 6 hex digits, e.g. ``#fffff8``).
                   Case-insensitive. Short form (``#fff``) and rgba are not supported.

    Returns:
        Relative luminance in [0.0, 1.0]. 0.0 = absolute black, 1.0 = absolute white.

    Raises:
        ValueError: If hex_color is not a valid 7-character hex string.
    """
    if len(hex_color) != 7 or hex_color[0] != "#":
        raise ValueError(f"hex_color must be '#' + 6 hex digits; got {hex_color!r}")
    try:
        r_int = int(hex_color[1:3], 16)
        g_int = int(hex_color[3:5], 16)
        b_int = int(hex_color[5:7], 16)
    except ValueError as exc:
        raise ValueError(
            f"hex_color contains non-hex characters: {hex_color!r}"
        ) from exc

    def _linearise(channel_8bit: int) -> float:
        """Convert an 8-bit channel value to linear light."""
        srgb = channel_8bit / 255.0
        if srgb <= 0.03928:
            return srgb / 12.92
        return ((srgb + 0.055) / 1.055) ** 2.4

    r_lin = _linearise(r_int)
    g_lin = _linearise(g_int)
    b_lin = _linearise(b_int)

    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(hex_a: str, hex_b: str) -> float:
    """Compute the WCAG 2.1 contrast ratio between two colours.

    Formula: ``(L1 + 0.05) / (L2 + 0.05)`` where ``L1 >= L2``.

    Args:
        hex_a: First colour as a 7-character hex string.
        hex_b: Second colour as a 7-character hex string.

    Returns:
        Contrast ratio >= 1.0. Identical colours return 1.0. Maximum is 21.0
        (black vs white). WCAG AA requires >= 4.5:1 for normal text.

    The function is symmetric: ``contrast_ratio(a, b) == contrast_ratio(b, a)``.
    """
    lum_a = relative_luminance(hex_a)
    lum_b = relative_luminance(hex_b)
    lighter = max(lum_a, lum_b)
    darker = min(lum_a, lum_b)
    return (lighter + 0.05) / (darker + 0.05)


# ---------------------------------------------------------------------------
# Secondary-encoding helper
# ---------------------------------------------------------------------------


def secondary_encoding(n: int) -> tuple[list[str], list[str]]:
    """Return matched (colours, shapes) pairs for n categories.

    Every colour-encoded distinction must also be encoded by a non-colour
    channel (TC-NFR-7-03 / ADR-310). This helper provides matched colour +
    shape pairs so callers can ``zip(colours, shapes)`` when plotting.

    Args:
        n: Number of categories. Must be >= 1 and <= ``len(SHAPES)`` (8).

    Returns:
        A 2-tuple ``(colours, shapes)`` where each is a list of length ``n``.
        ``colours`` is a slice of ``CATEGORICAL``; ``shapes`` is a slice of
        ``SHAPES``. All entries within each list are pairwise distinct.

    Raises:
        ValueError: If ``n < 1`` or ``n > len(SHAPES)``.
    """
    if n < 1:
        raise ValueError(f"n must be >= 1; got {n}")
    if n > len(SHAPES):
        raise ValueError(
            f"n={n} exceeds available shapes ({len(SHAPES)}). "
            f"Reduce the number of categories or extend SHAPES."
        )
    return CATEGORICAL[:n], SHAPES[:n]
