"""TC-INFRA-01: package importability and project-wide constants presence.

Smoke test for P1-C01 (project bootstrap). Verifies that the Python package
layout is correct and that every threshold constant referenced by downstream
chunks exists with the exact value specified in cross-cutting.md.
"""

from __future__ import annotations


def test_gvm_analysis_package_importable() -> None:
    """`import gvm_analysis` must succeed (TC-INFRA-01, part 1)."""
    import gvm_analysis  # noqa: F401 — import is the assertion


def test_sample_size_tiers_present_and_correct() -> None:
    """`from _shared import constants` must work and SAMPLE_SIZE_TIERS must match
    cross-cutting.md exactly (TC-INFRA-01, part 2)."""
    from _shared import constants

    assert constants.SAMPLE_SIZE_TIERS == (10, 30, 100, 1000, 10000)


def test_all_cross_cutting_constants_present() -> None:
    """Every threshold named in cross-cutting.md §Project-wide constants must be
    defined. Guards against drift between spec and code."""
    from _shared import constants

    assert constants.IQR_K == 1.5
    assert constants.MAD_THRESHOLD == 3.5
    assert constants.MULTIVARIATE_MIN_N == 1000
    assert constants.GAP_MULTIPLIER == 2.0
    assert constants.STALE_MULTIPLIER == 1.0
    assert constants.TREND_ALPHA == 0.05
    assert constants.SEASONAL_STRENGTH_THRESHOLD == 0.6
    assert constants.DRIVER_K_FLOOR == 5
    assert constants.DRIVER_K_FRACTION == 0.10
    assert constants.COMPREHENSION_QUESTION_COUNT == 3
