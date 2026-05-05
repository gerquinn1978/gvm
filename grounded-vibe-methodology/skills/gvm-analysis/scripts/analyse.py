"""Engine command-line entrypoint for ``/gvm-analysis``.

Reads an input file via ``_shared.io.load``, runs token-pattern detection
(AN-40), invokes the per-column and cross-column analytical modules
through ``_populate_findings`` (P16-C01: stats, missing, type_drift,
rounding per column; outliers, duplicates, time_series, drivers,
headline across columns), assembles the ADR-201 provenance via
``_shared.provenance`` (P16-C02), and atomically writes ``findings.json``
via ``_shared.findings.write_atomic``.

Two engine-layer placeholders remain:

* ``_STUB_COMPREHENSION_QUESTIONS`` (below) — bridge stub by design.
  The engine emits three placeholders; the SKILL.md orchestration shell
  synthesises real questions from ``findings.headline_findings`` and
  overwrites them via ``scripts/_patch_questions.py`` post-engine,
  pre-render. Registered in ``STUBS.md``.
* ``--forecast-only`` mode (P4-C04 still pending) — declared in argparse
  and refused with an explicit diagnostic so any caller that selects it
  fails loudly rather than silently succeeding.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import sys
import traceback
from pathlib import Path
from typing import Any

import numpy as np

from _shared import aggregation
from _shared import charts as charts_module
from _shared import comparison
from _shared import default_questions
from _shared import drivers
from _shared import duplicates
from _shared import findings
from _shared import headline
from _shared import io as io_module
from _shared import missing
from _shared import outliers
from _shared import provenance as provenance_module
from _shared import rounding
from _shared import stats
from _shared import time_series
from _shared import token_detect
from _shared import type_drift

# -- Comprehension-question bridge stub (ADR-109, STUBS.md) -----------------
#
# Bridge stub by design: the engine emits three placeholder Q/A pairs
# here; the SKILL.md orchestration shell synthesises real questions from
# ``findings.headline_findings`` (populated by P16-C01) and overwrites
# this list at runtime via ``scripts/_patch_questions.py``. The engine
# layer is the wrong place for question synthesis — that step requires
# an LLM call against headline content, which lives in the orchestrator.
# The stub stays; retirement happens in the wrapper layer.
_STUB_COMPREHENSION_QUESTIONS: list[dict[str, str]] = [
    {
        "question": "[tracer-bullet stub question 1]",
        "answer": "[tracer-bullet stub answer 1]",
        "supporting_finding_id": "",
    },
    {
        "question": "[tracer-bullet stub question 2]",
        "answer": "[tracer-bullet stub answer 2]",
        "supporting_finding_id": "",
    },
    {
        "question": "[tracer-bullet stub question 3]",
        "answer": "[tracer-bullet stub answer 3]",
        "supporting_finding_id": "",
    },
]

_MODE_CHOICES: tuple[str, ...] = (
    "explore",
    "decompose",
    "validate",
    "run-everything",
)

_SUB_SEED_MAX: int = 2**31 - 1


def _default_seed_from_input(input_path: Path) -> tuple[int, str]:
    """Derive a deterministic 31-bit default seed from the input file
    (ADR-202). Returns ``(seed, warning_message)`` so the caller can
    record the derivation in provenance.warnings.

    The same input file produces the same seed across runs (preserving
    reproducibility); a different input file produces a different seed
    (so independent inputs do not collide on identical RNG sequences).
    The seed range is ``[0, 2**31 - 1]`` to match
    ``numpy.random.default_rng`` constraints and the historical
    sub-seed integer range."""
    digest = provenance_module.sha256_file(input_path)
    seed = int(digest[:8], 16) % _SUB_SEED_MAX
    warning = (
        f"seed derived deterministically from input SHA-256 "
        f"(seed={seed}); pass --seed to override"
    )
    return seed, warning


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse CLI arguments per the P1-C03 flag table.

    The full flag set is declared here so downstream chunks (P2-C01 loading,
    P2-C02 prefs, P4-C04 forecast) do not need to churn the CLI surface —
    they only need to replace the ``None`` / no-op behaviours with real
    implementations.
    """
    parser = argparse.ArgumentParser(
        prog="analyse",
        description=(
            "GVM analysis engine entrypoint. Writes findings.json into --output-dir."
        ),
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        action="append",
        help=(
            "Input file path. Pass once per file for multi-file invocations "
            "(e.g. --input a.csv --input b.csv). Single-file is the default."
        ),
    )
    parser.add_argument(
        "--aggregation-strategy",
        type=str,
        default="concat",
        choices=["concat"],
        help=(
            "Strategy for combining multiple --input files (only consulted "
            "when more than one --input is supplied). 'concat' merges the "
            "shared-column intersection into a single frame with a "
            "__source_file__ provenance column. per_file and comparative "
            "strategies are out of scope for the engine (return dicts of "
            "frames, which the single-pass analyser cannot consume)."
        ),
    )
    parser.add_argument(
        "--sheet",
        type=str,
        default=None,
        help=(
            "Name of the sheet to load from a multi-sheet xlsx input. "
            "Forwarded to io.load(sheet=...). The AskUserQuestion sheet "
            "picker that resolves this value is in SKILL.md orchestration."
        ),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--mode",
        choices=_MODE_CHOICES,
        default="explore",
    )
    parser.add_argument("--target-column", type=str, default=None)
    parser.add_argument("--baseline-file", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--prefs", type=Path, default=None)
    parser.add_argument("--sample-n", type=int, default=None)
    parser.add_argument("--forecast-only", action="store_true")
    parser.add_argument("--in-file", type=Path, default=None)
    parser.add_argument("--time-column", type=str, default=None)
    return parser.parse_args(argv)


def _derive_sub_seeds(rng: np.random.Generator, *, num_columns: int) -> dict[str, Any]:
    """Pre-derive ADR-202 sub-seeds in the canonical fixed order.

    Every int is cast to plain :class:`int` (not ``numpy.int64``) so the
    dict is JSON-serialisable without an encoder hook. The derivation order
    is load-bearing: inserting a new key in the middle shifts the parent
    RNG draw order and breaks reproducibility against existing
    ``findings.json`` files. New keys MUST append to the end of the dict.
    """
    return {
        "outliers_iforest": int(rng.integers(0, _SUB_SEED_MAX)),
        "outliers_lof": None,
        "drivers_rf": int(rng.integers(0, _SUB_SEED_MAX)),
        "drivers_rf_perm": int(rng.integers(0, _SUB_SEED_MAX)),
        "drivers_partial_corr": int(rng.integers(0, _SUB_SEED_MAX)),
        "forecast_linear_bootstrap": int(rng.integers(0, _SUB_SEED_MAX)),
        "forecast_arima_init": int(rng.integers(0, _SUB_SEED_MAX)),
        "forecast_exp_smoothing_init": int(rng.integers(0, _SUB_SEED_MAX)),
        "per_column": [
            int(s) for s in rng.integers(0, _SUB_SEED_MAX, size=num_columns)
        ],
    }


def _iso8601_utc_now() -> str:
    """Return the current UTC instant as an ISO-8601 ``Z`` string."""
    now = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0)
    return now.isoformat().replace("+00:00", "Z")


def _is_numeric(series: Any) -> bool:
    """True if ``series`` has a numeric dtype (excludes datetime, object,
    bool). Routes per-column primitive selection."""
    import pandas as pd  # local import keeps module top clean for callers

    return pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(
        series
    )


def _resolve_time_column(df: Any, override: str | None) -> str | None:
    """Resolve the time column for ``time_series.analyse``. Returns the
    explicit ``--time-column`` override when supplied and present in the
    frame; otherwise the first datetime-typed column; otherwise the first
    object-dtype column whose values mostly parse as datetimes (a CSV
    fixture loaded as strings); otherwise ``None``."""
    import pandas as pd

    if override:
        return override if override in df.columns else None
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            return str(col)
    # Fallback for CSV-loaded frames where date columns arrive as strings.
    # io.load uses StringDtype (or plain object) for non-numeric columns;
    # `is_string_dtype` covers both. Accept the first such column whose
    # values parse as datetime with > 80% success.
    for col in df.columns:
        series = df[col]
        if pd.api.types.is_numeric_dtype(series):
            continue
        if pd.api.types.is_datetime64_any_dtype(series):
            continue  # already handled above; defensive
        non_null = series.dropna()
        if non_null.empty:
            continue
        parsed = pd.to_datetime(non_null.astype(str), errors="coerce")
        if parsed.notna().mean() >= 0.8:
            return str(col)
    return None


def _populate_findings(
    data: dict[str, Any],
    df: Any,
    sub_seeds: dict[str, Any],
    args: argparse.Namespace,
) -> None:
    """Wire P3/P4 analytical modules through the engine boundary (P16-C01).

    Mutates ``data`` in place. Each module call is guarded — failures
    append a provenance warning and leave the corresponding findings key
    at its empty default. The call order matches the wiring matrix in
    ``specs/implementation-guide.md``.
    """
    warnings: list[str] = data["provenance"].setdefault("warnings", [])

    # --- per-column primitives (stats, missing, type_drift, rounding) ---
    per_column_seeds: list[int] = sub_seeds.get("per_column") or []
    columns: list[dict[str, Any]] = []
    for col_idx, col_name in enumerate(df.columns):
        series = df[col_name]
        # Default keys established up front so any partial failure mid-block
        # leaves the col_entry shape valid for templates running under
        # StrictUndefined (no key absent → no UndefinedError).
        col_entry: dict[str, Any] = {
            "name": str(col_name),
            "dtype": str(series.dtype),
            "n_total": int(series.size),
            "n_non_null": int(series.notna().sum()),
            "completeness_pct": 0.0,
            "missingness_classification": None,
            "stats": None,
        }

        try:
            comp = missing.completeness(df, str(col_name))
            col_entry["missing"] = comp
            col_entry["n_total"] = int(comp["n_total"])
            col_entry["n_non_null"] = int(comp["n_non_null"])
            col_entry["completeness_pct"] = float(comp["completeness_pct"])
        except Exception as exc:  # noqa: BLE001 — graceful degradation
            warnings.append(
                f"missing.completeness failed for column {col_name!r}: {exc}"
            )

        try:
            col_entry["missingness_classification"] = missing.classify(
                df, str(col_name)
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"missing.classify failed for column {col_name!r}: {exc}")

        # `stats` is always present in the column dict — None for non-numeric
        # or empty-after-dropna columns. Templates use `selectattr('stats')`
        # under StrictUndefined and need the key to exist. When populated,
        # the dict carries `tier`, `robust`, `classical`, `distribution`,
        # and `ci_95` (None when AN-12/ADR-306b suppress CI at low tier).
        col_entry["stats"] = None
        if _is_numeric(series):
            try:
                values = series.dropna().to_numpy()
                if values.size > 0:
                    n = int(values.size)
                    col_tier = stats.tier(n)
                    stats_block: dict[str, Any] = {
                        "tier": col_tier.value,
                        "robust": stats.robust_stats(values),
                        "classical": stats.classical_stats(values),
                        "distribution": stats.distribution_check(values),
                        "ci_95": None,
                    }
                    # CI suppressed below n=30 per AN-12 (Harrell — bootstrap
                    # CIs not meaningful at small n). Above the threshold,
                    # compute the median CI via the BCa bootstrap, seeded
                    # from this column's per-column sub-seed (ADR-202) so
                    # adding/removing columns does not shift other columns'
                    # CIs and reproducibility is column-isolated.
                    if n >= 30 and col_idx < len(per_column_seeds):
                        try:
                            ci_rng = np.random.default_rng(per_column_seeds[col_idx])
                            low, high = stats.bootstrap_ci(
                                values, np.median, rng=ci_rng
                            )
                            stats_block["ci_95"] = {"median": [low, high]}
                        except Exception as exc:  # noqa: BLE001
                            warnings.append(
                                f"stats.bootstrap_ci failed for column {col_name!r}: {exc}"
                            )
                    elif n >= 30:
                        # n is large enough but no per-column seed is
                        # available — distinguish from the legitimate
                        # n<30 suppression so consumers do not mis-read
                        # ci_95=None as a small-sample signal.
                        warnings.append(
                            f"stats.bootstrap_ci skipped for column {col_name!r}: "
                            f"no per-column seed at index {col_idx} "
                            f"(per_column_seeds length={len(per_column_seeds)})"
                        )
                    col_entry["stats"] = stats_block
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"stats.* failed for column {col_name!r}: {exc}")

        try:
            td = type_drift.check(series, str(col_name))
            if td is not None:
                col_entry["type_drift"] = td
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"type_drift.check failed for column {col_name!r}: {exc}")

        if _is_numeric(series):
            try:
                rs = rounding.suspicious_rounding(series)
                if rs is not None:
                    col_entry["rounding_signal"] = rs
            except Exception as exc:  # noqa: BLE001
                warnings.append(
                    f"rounding.suspicious_rounding failed for column {col_name!r}: {exc}"
                )

        columns.append(col_entry)

    data["columns"] = columns

    # --- cross-column: duplicates (privacy-safe summariser, P17-C01) ---
    try:
        data["duplicates"] = duplicates.summarise(df)
    except Exception as exc:  # noqa: BLE001 — graceful degradation
        warnings.append(f"duplicates.summarise failed: {exc}")

    # --- cross-column: outliers ---
    try:
        outlier_seed = sub_seeds.get("outliers_iforest")
        outlier_rng = np.random.default_rng(outlier_seed)
        data["outliers"] = outliers.detect(df, rng=outlier_rng)
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"outliers.detect failed: {exc}")

    # --- cross-column: time-series (when a time column resolves) ---
    time_col = _resolve_time_column(df, args.time_column)
    if time_col is not None:
        try:
            ts_block = time_series.analyse(df, time_col)
            if ts_block is not None:
                data["time_series"] = ts_block
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"time_series.analyse failed: {exc}")
    else:
        warnings.append(
            "time_series.analyse skipped: no time column resolved "
            "(no --time-column override and no datetime-typed column found)"
        )

    # --- cross-column: drivers (P17-C02 — Decompose, Validate,
    # Run-everything). Driver decomposition runs whenever a target
    # column resolves; the mode determines the data context:
    #   - Decompose / Run-everything: run against the input frame as
    #     loaded (no baseline join);
    #   - Validate: load the baseline file and join it to the input
    #     before driver decomposition (compares effects under both
    #     conditions). Explore mode never runs drivers regardless.
    # P21-C03: validate-mode comparison block wiring. Independent of the
    # target_column / drivers path so a validate-mode run without
    # --target-column (a legitimate drift-check workflow) still populates
    # findings.comparison.
    baseline_df = None
    if args.mode == "validate" and args.baseline_file is not None:
        try:
            baseline_df = io_module.load(args.baseline_file)
            cmp_block = comparison.compute(
                df,
                baseline_df,
                actual_file=str(args.input[0]) if args.input else "",
                baseline_file=str(args.baseline_file),
            )
            if cmp_block is not None:
                data["comparison"] = cmp_block
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"comparison.compute failed: {exc}")

    if args.mode != "explore" and args.target_column:
        try:
            driver_input_df = df
            if args.mode == "validate":
                if args.baseline_file is None:
                    raise ValueError(
                        "Validate mode requires --baseline-file but none was supplied"
                    )
                # baseline_df was loaded above; load defensively if the
                # comparison branch errored before assignment.
                if baseline_df is None:
                    baseline_df = io_module.load(args.baseline_file)

                # Concat input and baseline; downstream RF / partial-corr
                # use the joined frame to compare. Index is reset so
                # row_indices stay non-collapsing.
                import pandas as _pd

                driver_input_df = _pd.concat(
                    [
                        df.assign(_dataset="input"),
                        baseline_df.assign(_dataset="baseline"),
                    ],
                    ignore_index=True,
                )
            data["drivers"] = drivers.decompose(
                driver_input_df,
                args.target_column,
                rng_seed=int(data["provenance"]["seed"]),
                sub_seeds={
                    "drivers_rf": sub_seeds["drivers_rf"],
                    "drivers_rf_perm": sub_seeds["drivers_rf_perm"],
                    "drivers_partial_corr": sub_seeds["drivers_partial_corr"],
                },
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"drivers.decompose failed: {exc}")
    elif args.mode != "explore" and not args.target_column:
        # Decompose / Validate / Run-everything declared but no target
        # column — surface so consumers do not silently see drivers=None.
        warnings.append(
            f"drivers.decompose skipped: mode={args.mode!r} requires "
            "--target-column to resolve a driver target"
        )

    # --- headline selection (must run last; reads other findings sections) ---
    try:
        data["headline_findings"] = headline.select(df, data)
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"headline.select failed: {exc}")

    # --- comprehension-question synthesis (P18-C01 — deterministic
    # engine-layer fallback). The engine-level placeholder list at
    # _STUB_COMPREHENSION_QUESTIONS is overwritten here with three
    # plain-language Q/A entries derived from headline_findings. The
    # SKILL.md orchestration layer (P17-C03 step 12b +
    # scripts/_patch_questions.py) remains the canonical override path
    # for richer LLM-synthesised content.
    try:
        data["comprehension_questions"] = default_questions.generate(
            data.get("headline_findings") or []
        )
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"default_questions.generate failed: {exc}")


def _slugify(name: str) -> str:
    """Filesystem-safe lowercase slug. Replaces any character outside
    ``[a-z0-9._-]`` with ``_``. Preserves dots so the call sites can
    compose ``<col>.<kind>.svg`` directly."""
    return re.sub(r"[^a-z0-9._-]", "_", str(name).lower())


def _chart_relpath(filename: str) -> str:
    """Forward-slash relative POSIX path under ``charts/``. Matches
    ``findings._CHART_PATH_PREFIX`` so paths produced here pass the
    P19-C01 schema validator."""
    return f"{findings._CHART_PATH_PREFIX}{filename}"


def _render_charts(
    data: dict[str, Any],
    df: Any,
    output_dir: Path,
    sub_seeds: dict[str, Any],
) -> None:
    """Render charts for each populated section of ``data``. Mutates
    ``data`` in place: sets chart-path fields on success, appends a
    ``chart_render_failed: ...`` warning to ``provenance.warnings`` on
    failure. Never raises.

    Wired into ``main()`` after ``_populate_findings(...)`` and before
    ``findings.write_atomic(...)`` (P19-C02 wiring matrix). Sub-seeds
    thread through ``per_column`` for histogram RNG.
    """
    import pandas as pd  # local import keeps module top clean

    # Outer guard: every inner site is also try/except'd, but unguarded
    # statements between sites (pandas dtype probes, dict access, list
    # comprehensions) can raise too. The helper's contract is "never
    # raises" — surface any escapee as a single render-pass warning so
    # ADR-201 graceful degradation holds end-to-end.
    try:
        warnings: list[str] = data["provenance"].setdefault("warnings", [])
    except Exception:  # noqa: BLE001
        # No place to record the warning; nothing safe to do but bail.
        return

    charts_dir = output_dir / "charts"
    try:
        charts_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:  # noqa: BLE001 — graceful degradation
        warnings.append(f"charts directory creation failed: {exc}")
        return

    # `used_filenames` disambiguates slug collisions across the whole
    # render pass (e.g. columns "Score" and "score" both slug to
    # "score"). Without this, the second writer overwrites the first
    # SVG and both findings.json paths point to the same file —
    # silent corruption that the schema cannot catch.
    used_filenames: set[str] = set()

    def _unique_filename(base: str, *, label: str) -> str:
        if base not in used_filenames:
            used_filenames.add(base)
            return base
        stem, _, ext = base.rpartition(".")
        n = 2
        while True:
            candidate = f"{stem}_{n}.{ext}"
            if candidate not in used_filenames:
                used_filenames.add(candidate)
                warnings.append(
                    f"chart filename collision: {base} reused for {label}; "
                    f"writing to {candidate} instead"
                )
                return candidate
            n += 1

    try:
        _render_charts_body(
            data,
            df,
            df_pd=pd,
            charts_dir=charts_dir,
            sub_seeds=sub_seeds,
            warnings=warnings,
            unique_filename=_unique_filename,
        )
    except Exception as exc:  # noqa: BLE001 — outer catch-all
        warnings.append(f"chart_render_failed: kind=render_pass, error={exc}")


def _render_charts_body(
    data: dict[str, Any],
    df: Any,
    *,
    df_pd: Any,
    charts_dir: Path,
    sub_seeds: dict[str, Any],
    warnings: list[str],
    unique_filename: Any,
) -> None:
    """Inner body of `_render_charts`. Extracted so the outer helper can
    install a single catch-all without indenting the entire body."""
    pd = df_pd  # alias for readability
    per_column_seeds: list[int] = sub_seeds.get("per_column") or []

    # --- per-column charts (numeric only) ---
    for col_idx, col_entry in enumerate(data.get("columns") or []):
        col_name = col_entry.get("name")
        if col_name is None:
            continue
        if col_name not in df.columns:
            continue
        series = df[col_name]
        if not (
            pd.api.types.is_numeric_dtype(series)
            and not pd.api.types.is_bool_dtype(series)
        ):
            continue
        if col_entry.get("stats") is None:
            continue
        values = series.dropna().tolist()
        if not values:
            continue

        col_entry["charts"] = {"histogram": None, "boxplot": None}
        # Per-column setup wrapped in its own try/except so a slug or
        # filename-allocation failure isolates to this column instead of
        # bubbling to the pass-level catch (which would abort all
        # subsequent columns). Per ADR-201: failure isolation is
        # per-chart, but setup statements are part of the "chart
        # rendering" step from the spec's point of view.
        try:
            slug = _slugify(str(col_name))
            seed = (
                per_column_seeds[col_idx] if col_idx < len(per_column_seeds) else None
            )
            hist_name = unique_filename(
                f"{slug}.histogram.svg", label=f"column {col_name!r}"
            )
            box_name = unique_filename(
                f"{slug}.boxplot.svg", label=f"column {col_name!r}"
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(
                f"chart_render_failed: kind=column_setup, "
                f"column={col_name}, error={exc}"
            )
            continue

        try:
            charts_module.histogram(
                values,
                title=f"Distribution of {col_name}",
                ax_label=str(col_name),
                savepath=charts_dir / hist_name,
                seed=seed,
            )
            col_entry["charts"]["histogram"] = _chart_relpath(hist_name)
        except Exception as exc:  # noqa: BLE001
            warnings.append(
                f"chart_render_failed: kind=histogram, column={col_name}, error={exc}"
            )

        try:
            charts_module.boxplot(
                {str(col_name): values},
                title=f"Boxplot of {col_name}",
                ax_label=str(col_name),
                savepath=charts_dir / box_name,
            )
            col_entry["charts"]["boxplot"] = _chart_relpath(box_name)
        except Exception as exc:  # noqa: BLE001
            warnings.append(
                f"chart_render_failed: kind=boxplot, column={col_name}, error={exc}"
            )

    # --- outlier scatter charts (one per (method, column) group) ---
    outliers_block = data.get("outliers")
    if isinstance(outliers_block, dict):
        by_method = outliers_block.get("by_method")
        if isinstance(by_method, dict):
            for method, entries in by_method.items():
                if not isinstance(entries, list) or not entries:
                    continue
                # Group entries by column.
                by_column: dict[str, list[dict[str, Any]]] = {}
                for entry in entries:
                    col = str(entry.get("column", ""))
                    by_column.setdefault(col, []).append(entry)

                for col_name, group in by_column.items():
                    if not col_name or col_name not in df.columns:
                        continue
                    method_slug = _slugify(method)
                    col_slug = _slugify(col_name)
                    filename = unique_filename(
                        f"outliers.{method_slug}.{col_slug}.svg",
                        label=f"outliers method={method!r} column={col_name!r}",
                    )
                    try:
                        x = [int(e.get("row_index", 0)) for e in group]
                        y = [float(e.get("value", 0.0)) for e in group]
                        charts_module.scatter(
                            x,
                            y,
                            title=f"Outliers ({method}) — {col_name}",
                            x_label="row index",
                            y_label=str(col_name),
                            savepath=charts_dir / filename,
                        )
                        path = _chart_relpath(filename)
                        for entry in group:
                            entry["chart"] = path
                    except Exception as exc:  # noqa: BLE001
                        warnings.append(
                            f"chart_render_failed: kind=scatter, section=outliers, "
                            f"method={method}, column={col_name}, error={exc}"
                        )

    # --- driver partial-dependence chart (one bar chart, attached to
    # every constructed entry under drivers.entries) ---
    drivers_block = data.get("drivers")
    if isinstance(drivers_block, dict):
        agreement = drivers_block.get("agreement") or {}
        method_results = drivers_block.get("method_results") or {}
        top_features: list[str] = []
        if isinstance(agreement.get("top_k_features"), list):
            top_features = [str(f) for f in agreement["top_k_features"]]
        elif isinstance(method_results.get("rf_importance"), list):
            top_features = [
                str(r.get("feature"))
                for r in method_results["rf_importance"]
                if isinstance(r, dict) and r.get("feature") is not None
            ]

        if top_features:
            # Build importance values from rf_importance when available;
            # fall back to uniform 1.0 so bar() still has a valid call.
            rf_rows = method_results.get("rf_importance") or []
            importance_by_feature: dict[str, float] = {}
            if isinstance(rf_rows, list):
                for r in rf_rows:
                    if isinstance(r, dict) and r.get("feature") is not None:
                        try:
                            importance_by_feature[str(r["feature"])] = float(
                                r.get("importance", r.get("mean_abs_shap", 1.0))
                            )
                        except (TypeError, ValueError):
                            continue
            values = [importance_by_feature.get(f, 1.0) for f in top_features]

            filename = "drivers.partial_dependence.svg"
            try:
                charts_module.bar(
                    list(top_features),
                    values,
                    title="Driver importance",
                    axis_label="importance",
                    savepath=charts_dir / filename,
                )
                path = _chart_relpath(filename)
                drivers_block["entries"] = [
                    {"feature": f, "partial_dependence_chart": path}
                    for f in top_features
                ]
            except Exception as exc:  # noqa: BLE001
                warnings.append(
                    f"chart_render_failed: kind=bar, section=drivers, error={exc}"
                )
                drivers_block["entries"] = [
                    {"feature": f, "partial_dependence_chart": None}
                    for f in top_features
                ]
        else:
            warnings.append(
                "chart_skipped: kind=bar, section=drivers, "
                "reason=no top features resolved"
            )
            drivers_block["entries"] = []

    # --- time-series charts ---
    ts_block = data.get("time_series")
    if isinstance(ts_block, dict):
        ts_block["charts"] = {"line": None, "decomposition": None}
        time_col = ts_block.get("time_column")
        if time_col and time_col in df.columns:
            # Pick the first numeric column for the line plot value axis.
            numeric_col: str | None = None
            for c in df.columns:
                if c == time_col:
                    continue
                series = df[c]
                if pd.api.types.is_numeric_dtype(
                    series
                ) and not pd.api.types.is_bool_dtype(series):
                    numeric_col = str(c)
                    break
            if numeric_col is not None:
                filename = "time_series.line.svg"
                try:
                    x = df[time_col].tolist()
                    y = df[numeric_col].tolist()
                    charts_module.line(
                        x,
                        y,
                        title=f"{numeric_col} over time",
                        x_label=str(time_col),
                        y_label=numeric_col,
                        savepath=charts_dir / filename,
                    )
                    ts_block["charts"]["line"] = _chart_relpath(filename)
                except Exception as exc:  # noqa: BLE001
                    warnings.append(
                        f"chart_render_failed: kind=line, section=time_series, error={exc}"
                    )

        # Decomposition chart only when seasonality block carries the
        # three required arrays. Current `time_series.analyse` does not
        # populate them at this layer; left as null when absent.
        seasonality = ts_block.get("seasonality")
        if isinstance(seasonality, dict) and all(
            isinstance(seasonality.get(k), list) and seasonality.get(k)
            for k in ("trend", "seasonal", "residual")
        ):
            filename = "time_series.decomposition.svg"
            try:
                specs = [
                    {
                        "kind": "line",
                        "x": list(range(len(seasonality[k]))),
                        "y": list(seasonality[k]),
                        "title": k,
                    }
                    for k in ("trend", "seasonal", "residual")
                ]
                charts_module.small_multiples(
                    specs,
                    title="Time-series decomposition",
                    savepath=charts_dir / filename,
                )
                ts_block["charts"]["decomposition"] = _chart_relpath(filename)
            except Exception as exc:  # noqa: BLE001
                warnings.append(
                    f"chart_render_failed: kind=small_multiples, section=time_series, error={exc}"
                )


def _build_provenance(
    *,
    input_paths: list[Path],
    mode: str,
    seed: int,
    sub_seeds: dict[str, Any],
    df: Any | None = None,
    preferences: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
    target_column: str | None = None,
    baseline_file: Path | None = None,
    sample_n: int | None = None,
    time_column: str | None = None,
    anonymised_input_detected: bool = False,
    anonymised_columns: list[str] | None = None,
) -> dict[str, Any]:
    """Build the ADR-201 provenance dict.

    Delegates to ``_shared.provenance`` (P2-C03) for the load-bearing
    fields: SHA-256 of the input file, library versions via
    ``importlib.metadata``, ISO-8601 timestamp, and preferences hash.
    The local helper used to emit a thin tracer-bullet skeleton with
    these fields blank — that placeholder was retired in P16-C02.

    ``input_paths`` is a list to support multi-file aggregation
    (P20-C01). Single-input invocations pass a one-element list. The
    rows/cols totals on the SHARED frame go on the FIRST entry (when
    aggregation merged frames the shape is the post-aggregation total);
    each entry's SHA-256 + mtime are computed from the original on-disk
    file. ``df`` is the (possibly-aggregated) frame the engine
    processes; passing it stamps rows/cols on the first input entry.
    """
    prefs = preferences or {}
    from datetime import datetime, timezone

    file_records: list[dict[str, Any]] = []
    for idx, path in enumerate(input_paths):
        if df is not None and idx == 0:
            file_records.append(provenance_module.file_provenance(path, df))
        else:
            mtime_dt = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            file_records.append(
                {
                    "path": str(path),
                    "sha256": provenance_module.sha256_file(path),
                    "mtime": mtime_dt.isoformat(),
                    "rows": None,
                    "cols": None,
                }
            )

    return {
        "input_files": file_records,
        "mode": mode,
        "target_column": target_column,
        "baseline_file": str(baseline_file) if baseline_file else None,
        "seed": seed,
        "sub_seeds": sub_seeds,
        "timestamp": provenance_module.timestamp_iso(),
        "preferences": dict(prefs),
        "preferences_hash": provenance_module.preferences_hash(prefs),
        "lib_versions": provenance_module.lib_versions(),
        "anonymised_input_detected": anonymised_input_detected,
        "anonymised_columns": (
            list(anonymised_columns) if anonymised_columns is not None else []
        ),
        "formula_columns": [],
        "sample_applied": (
            {"configured_n": sample_n} if sample_n is not None else None
        ),
        "domain": None,
        "warnings": list(warnings) if warnings else [],
        "time_column": time_column,
        "bootstrap_n_iter_used": 0,
    }


def _emit_diagnostic(error_line: str, what_went_wrong: str, what_to_try: str) -> None:
    """Write a three-line ERROR/What/What-to-try block to stderr.

    Matches the cross-cutting diagnostic shape (the full formatter lives in
    ``_shared/diagnostics.py`` in P2-C04). Emitting the three-line shape
    here keeps the surface stable so P2-C04 can replace this helper with a
    one-liner without touching any caller.
    """
    sys.stderr.write(f"ERROR: {error_line}\n")
    sys.stderr.write(f"What went wrong: {what_went_wrong}\n")
    sys.stderr.write(f"What to try: {what_to_try}\n")


def main(argv: list[str] | None = None) -> int:
    """Run the engine. Return process exit code.

    Exit codes:
      0 — success; ``findings.json`` written.
      1 — unexpected internal error; traceback-derived diagnostic on stderr.
      2 — invalid invocation: missing ``--input`` path, unsupported
          ``--forecast-only`` (until P4-C04), cross-volume
          ``--output-dir`` (``CrossVolumeWriteError``), or argparse parse
          failure. Argparse parse failures exit 2 directly via
          ``SystemExit`` — they do NOT flow through ``main()``'s ``return 2``.
          Per Unix convention — the P5-C02 bash wrapper distinguishes the
          subcases by reading the stderr diagnostic, not by exit code.
    """
    args = _parse_args(argv)

    if args.forecast_only:
        _emit_diagnostic(
            "--forecast-only is not yet implemented (P4-C04).",
            "The forecast-only path will be added in Phase 4 chunk 4.",
            "Run without --forecast-only for the standard analysis pass.",
        )
        return 2

    missing_inputs = [p for p in args.input if not p.exists()]
    if missing_inputs:
        _emit_diagnostic(
            f"input file not found: {missing_inputs[0]}",
            "The path passed to --input does not exist on disk.",
            "Check the path and file permissions, then re-run.",
        )
        return 2

    # The multi-input aggregation path loads each file via the default
    # sheet (aggregation.aggregate calls io.load(p) with no sheet=).
    # If the user supplies --sheet alongside multiple --input files,
    # silently discarding the sheet selection would analyse the wrong
    # sheet with no error and no provenance warning. Refuse loudly
    # rather than mis-load. Single-input + --sheet is the supported
    # combination.
    if args.sheet is not None and len(args.input) > 1:
        _emit_diagnostic(
            "--sheet is not supported with multi-file --input invocations",
            (
                "The aggregation pipeline loads each file via the default "
                "sheet; specifying --sheet on a multi-file invocation would "
                "either be silently discarded or applied inconsistently."
            ),
            (
                "For multi-sheet xlsx selection, use single-file mode "
                "(--input one.xlsx --sheet SheetName). For multi-file "
                "aggregation, ensure each file has its target sheet as the "
                "default, or pre-extract sheets to per-file CSVs."
            ),
        )
        return 2

    try:
        # Seed derivation (ADR-202): when multiple inputs are supplied,
        # seed off the first input's SHA-256. Same first input → same
        # seed across runs; reorder the inputs and the seed changes.
        # The warning records this behaviour so the practitioner sees
        # which file's hash governed the run.
        if args.seed is None:
            seed, default_warning = _default_seed_from_input(args.input[0])
            warnings = [default_warning]
        else:
            seed = args.seed
            warnings = []

        rng = np.random.default_rng(seed)

        # AN-40 wiring (anonymisation-pipeline ADR-406, P15-C01). The engine
        # loads the input via the canonical io boundary, runs the read-only
        # token-pattern detector, and threads the result into provenance so
        # the renderer footer and downstream consumers see the flag.
        # P20-C01: route through aggregation.aggregate when multiple
        # inputs are supplied; preserve the single-input fast path.
        if len(args.input) == 1:
            df = io_module.load(args.input[0], sheet=args.sheet)
        else:
            import pandas as pd  # local import per project convention

            df = aggregation.aggregate(args.input, strategy=args.aggregation_strategy)
            if not isinstance(df, pd.DataFrame):
                # Defence in depth: argparse choices=['concat'] should
                # already prevent this, but if a future strategy is
                # added that returns dict[str, DataFrame] without
                # updating the engine, fail loudly rather than crash
                # downstream on dict-without-columns access.
                _emit_diagnostic(
                    f"aggregation strategy {args.aggregation_strategy!r} returned "
                    f"{type(df).__name__}, not a single DataFrame",
                    (
                        "The single-pass engine consumes one DataFrame. "
                        "Strategies that return dict[str, DataFrame] "
                        "(per_file, comparative) require orchestration-layer "
                        "support not yet built."
                    ),
                    "Run with --aggregation-strategy concat (the default).",
                )
                return 2
        detection = token_detect.detect(df)
        warnings.extend(detection.warnings)

        # P16-C01: derive sub-seeds AFTER load so per_column seeds match
        # the actual column count. The historical tracer-bullet path
        # passed num_columns=0 because no analytical wiring consumed the
        # per_column list; with engine wiring (bootstrap CI, per-column
        # rng) the count is load-bearing for reproducibility (ADR-202).
        sub_seeds = _derive_sub_seeds(rng, num_columns=len(df.columns))

        provenance = _build_provenance(
            input_paths=args.input,
            mode=args.mode,
            seed=seed,
            df=df,
            sub_seeds=sub_seeds,
            warnings=warnings,
            target_column=args.target_column,
            baseline_file=args.baseline_file,
            sample_n=args.sample_n,
            time_column=args.time_column,
            anonymised_input_detected=detection.anonymised_input_detected,
            anonymised_columns=list(detection.anonymised_columns),
        )

        data = findings.build_empty_findings(provenance=provenance)
        data["comprehension_questions"] = [
            dict(q) for q in _STUB_COMPREHENSION_QUESTIONS
        ]

        # P16-C01 wiring: invoke P3/P4 analytical modules through the
        # engine boundary so findings.json carries real content rather
        # than the build_empty_findings skeleton. Each module call is
        # guarded inside the helper — failures degrade to provenance
        # warnings and leave the corresponding key at its empty default
        # per ADR-201 graceful degradation.
        _populate_findings(data, df, sub_seeds, args)

        args.output_dir.mkdir(parents=True, exist_ok=True)

        # P19-C02 wiring: render charts and populate the schema
        # chart-path fields. The helper guards every call site so
        # render failures degrade to provenance warnings without
        # halting the run.
        _render_charts(data, df, args.output_dir, sub_seeds)
    except Exception as exc:  # noqa: BLE001 — generic fallback is intentional
        _emit_diagnostic(
            f"{type(exc).__name__}: {exc}",
            "The engine failed before writing findings.json.",
            "Re-run with the same arguments; if the error persists, "
            "report the traceback below.",
        )
        traceback.print_exc(file=sys.stderr)
        return 1

    try:
        findings.write_atomic(args.output_dir / "findings.json", data)
    except findings.CrossVolumeWriteError as exc:
        _emit_diagnostic(
            str(exc),
            "The --output-dir is on a different filesystem volume than the "
            "temporary file directory; atomic rename is not possible.",
            "Choose an --output-dir on the same volume as the input file and re-run.",
        )
        return 2
    except Exception as exc:  # noqa: BLE001 — generic fallback is intentional
        _emit_diagnostic(
            f"{type(exc).__name__}: {exc}",
            "The engine failed while writing findings.json.",
            "Re-run with the same arguments; if the error persists, "
            "report the traceback below.",
        )
        traceback.print_exc(file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
