"""Project-wide thresholds and tunable constants.

Single source of truth per cross-cutting ADR-007. Every threshold referenced by
any analysis module, by user-preference defaults, or by tests is defined here
with the value from cross-cutting.md §Project-wide constants. User preferences
(Domain 9, AN-32..AN-34) may override these at runtime; the values below are
the defaults.

Changing any constant here is a cross-cutting change — per BC-1, audit consumers
before commit.
"""

from __future__ import annotations

# ---- Sample-size tiers (AN-12) ---------------------------------------------
# Boundaries that dispatch per-column statistical methods (classical vs robust
# vs bootstrap) based on available sample size.
SAMPLE_SIZE_TIERS: tuple[int, int, int, int, int] = (10, 30, 100, 1000, 10000)

# ---- Outlier detection (AN-14) ---------------------------------------------
IQR_K: float = 1.5
MAD_THRESHOLD: float = 3.5

# ---- Multivariate detection threshold (AN-12, AN-14) -----------------------
# Below this n, multivariate methods (IsolationForest, LOF) are not dispatched.
MULTIVARIATE_MIN_N: int = 1000

# ---- Time-series gap and staleness (AN-20) ---------------------------------
GAP_MULTIPLIER: float = 2.0
STALE_MULTIPLIER: float = 1.0

# ---- Trend and seasonality tests (AN-22) -----------------------------------
TREND_ALPHA: float = 0.05  # Mann-Kendall significance level
SEASONAL_STRENGTH_THRESHOLD: float = 0.6  # STL seasonal-strength threshold

# ---- Drivers top-K rule (AN-23) --------------------------------------------
DRIVER_K_FLOOR: int = 5
DRIVER_K_FRACTION: float = 0.10

# ---- Comprehension questions (NFR-4) ---------------------------------------
COMPREHENSION_QUESTION_COUNT: int = 3

# ---- Preferences schema version (AN-44) ------------------------------------
# The top-level key in preferences.yaml. Future schema changes bump this and
# register a migration in `_shared/prefs.py::MIGRATIONS`.
CURRENT_VERSION: int = 1

# ---- Headline selection (ADR-211) ------------------------------------------
HEADLINE_COUNT: int = 5

# ---- Bootstrap CI defaults (ADR-203) ---------------------------------------
BOOTSTRAP_N_ITER: int = 1000
BOOTSTRAP_CONFIDENCE: float = 0.95

# ---- Time-series preferences (ADR-208) -------------------------------------
# Multiplier of inferred cadence beyond which a gap is flagged.
TIME_SERIES_GAP_THRESHOLD: float = 1.5
# Days without an observation that mark a series stale.
TIME_SERIES_STALE_THRESHOLD_DAYS: int = 30

# ---- Duplicate detection (ADR-203) -----------------------------------------
FUZZY_DUPLICATE_THRESHOLD: float = 0.85

# ---- Outlier method selection (ADR-205) ------------------------------------
OUTLIER_METHODS_DEFAULT: tuple[str, ...] = ("iqr", "mad")
OUTLIER_METHODS_ALLOWED: frozenset[str] = frozenset({"iqr", "mad", "iforest", "lof"})

# ---- Data-quality check toggles (ADR-104) ----------------------------------
# Names MUST match the schema keys under `data_quality_checks:` in prefs.yaml.
DATA_QUALITY_CHECK_KEYS: tuple[str, ...] = (
    "run_missingness",
    "run_type_drift",
    "run_rounding",
    "run_exact_duplicates",
    "run_near_duplicates",
)
