"""End-to-end performance budget audit (NFR-2, P15-C03a).

System-level test that runs ``analyse.main`` followed by ``render_report.main``
against a synthesised 1M-row × 10-column fixture and asserts the run completes
within the NFR-2 budget: wall-clock < 5 minutes, peak Python heap ≤ 6 GB.

The measurement uses stdlib only — ``time.perf_counter`` for wall-clock,
``tracemalloc`` for peak Python-heap memory. ``psutil`` is deliberately not
used: RSS includes shared library mappings and OS-level allocations that vary
between machines and obscure the Python-heap signal NFR-2 actually budgets.

Today the engine is at tracer-bullet level (per the P15-C02 handover's
"Surfaced Requirements" note): per-column stats, outliers, drivers,
time-series, and headline selection are NOT yet wired into ``analyse.main``,
so the test passes for the cheap reason — load + AN-40 detect + provenance
write. The test becomes *load-bearing* the moment analytical wiring lands.

The test is env-gated by ``GVM_RUN_PERF_TESTS=1`` so the default
``pytest tests/`` invocation does not pay the multi-second 1M-row fixture
build cost. CI runs it explicitly. Markers ``slow`` and ``perf`` exist for
selector-based runs (``pytest -m perf``).

Test cases: TC-NFR-2-01.
"""

from __future__ import annotations

import os
import time
import tracemalloc
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import numpy as np
import pandas as pd
import pytest

_NFR2_WALL_CLOCK_BUDGET_SECONDS: float = 5 * 60.0  # 5 minutes
_NFR2_PEAK_RAM_BUDGET_BYTES: int = 6 * 1024**3  # 6 GiB

_NFR2_FIXTURE_ROWS: int = 1_000_000


def _synth_one_million_row_fixture(out_path: Path) -> None:
    """Write a 1,000,000-row × 10-column CSV at ``out_path``.

    Mix matches the NFR-2 scenario: 5 numeric columns, 3 low-cardinality
    categoricals, 1 high-cardinality id-like categorical, 1 timestamp.
    Deterministic via a fixed numpy Generator seed."""
    rng = np.random.default_rng(42)
    n = _NFR2_FIXTURE_ROWS
    df = pd.DataFrame(
        {
            "num_a": rng.random(n),
            "num_b": rng.normal(loc=100.0, scale=15.0, size=n),
            "num_c": rng.integers(0, 1_000_000, size=n),
            "num_d": rng.exponential(scale=2.0, size=n),
            "num_e": rng.uniform(-10.0, 10.0, size=n),
            "cat_low_a": rng.choice(["alpha", "beta", "gamma"], size=n),
            "cat_low_b": rng.choice(["x", "y", "z", "w"], size=n),
            "cat_low_c": rng.choice(["red", "green", "blue"], size=n),
            "cat_high": np.char.add("id_", rng.integers(0, n, size=n).astype(str)),
            "ts": pd.date_range("2020-01-01", periods=n, freq="min"),
        }
    )
    df.to_csv(out_path, index=False)


@contextmanager
def _measure_pipeline() -> Iterator[dict[str, float]]:
    """Wrap a pipeline run, populate the yielded dict with measurements.

    Mutating a dict the caller already holds is the canonical way to return
    values from a context manager without breaking the ``with`` semantics —
    ``yield`` cannot return after exit. The dict gains
    ``wall_clock_seconds`` and ``peak_bytes`` keys on exit."""
    out: dict[str, float] = {}
    start: float = time.perf_counter()
    try:
        tracemalloc.start()
        start = time.perf_counter()
        yield out
    finally:
        out["wall_clock_seconds"] = time.perf_counter() - start
        if tracemalloc.is_tracing():
            _, peak = tracemalloc.get_traced_memory()
            out["peak_bytes"] = float(peak)
            tracemalloc.stop()
        else:
            out["peak_bytes"] = 0.0


@pytest.mark.slow
@pytest.mark.perf
@pytest.mark.skipif(
    os.environ.get("GVM_RUN_PERF_TESTS") != "1",
    reason="Perf budget test gated behind GVM_RUN_PERF_TESTS=1; runs in CI.",
)
def test_one_million_rows_under_nfr2_budget(tmp_path: Path) -> None:
    """NFR-2: 1M-row × 10-col Explore-mode pipeline must complete in
    < 5 minutes wall-clock and ≤ 6 GiB peak Python-heap RAM."""
    import analyse
    import render_report

    csv_path = tmp_path / "one_million.csv"
    _synth_one_million_row_fixture(csv_path)

    out_dir = tmp_path / "out"

    with _measure_pipeline() as measurements:
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
        assert rc_engine == 0, "analyse.main failed under NFR-2 fixture"

        rc_render = render_report.main(
            [
                "--findings",
                str(out_dir / "findings.json"),
                "--out",
                str(out_dir),
            ]
        )
        assert rc_render == 0, "render_report.main failed under NFR-2 fixture"

    duration_s = measurements["wall_clock_seconds"]
    peak_bytes = measurements["peak_bytes"]
    peak_gib = peak_bytes / (1024**3)

    assert duration_s < _NFR2_WALL_CLOCK_BUDGET_SECONDS, (
        f"NFR-2 wall-clock budget violated: pipeline took "
        f"{duration_s:.1f}s (budget {_NFR2_WALL_CLOCK_BUDGET_SECONDS:.0f}s)."
    )
    assert peak_bytes <= _NFR2_PEAK_RAM_BUDGET_BYTES, (
        f"NFR-2 peak-RAM budget violated: pipeline peaked at "
        f"{peak_gib:.2f} GiB (budget 6.00 GiB)."
    )
