"""Shared methodology references (ADR-211 jargon list; P6-C02 registry).

P4-C06 introduces this module with the ``JARGON_FORBIDDEN`` frozenset so
there is a single source of truth for the forbidden-jargon list consumed
by ``_shared/headline.select()``, ``scripts/_patch_questions.py``, and the
renderer (see ADR-211 post-R4 fix CRITICAL-T50).

P6-C02 extends this module with the methodology registry (per-method
display name, parameters, expert citation, appendix text) populating the
``methodology_ref`` slots in findings.json. See ADR-305 (registry structure)
and ADR-306b (ci_suppressed_small_n verbatim entry).

Public surface (P6-C02 additions):
* :data:`METHODOLOGY_REGISTRY` — static canonical entries (keys → dicts with
  hardcoded display_name/expert_citation/appendix_text; parameters field is a
  template placeholder until ``build_registry`` renders it).
* :exc:`UnknownMethodError` — raised by ``lookup`` for unregistered keys.
* :func:`build_registry` — renders ``parameters`` dynamically from prefs.
* :func:`lookup` — looks up a single entry; raises ``UnknownMethodError`` if
  the key is not registered.
* :func:`aggregate_appendix` — deduplicate + sort by display_name.
"""

from __future__ import annotations

from typing import Iterable

# Case-insensitive substring match; tokens with hyphens/spaces are
# normalised at the call site before scanning.
JARGON_FORBIDDEN: frozenset[str] = frozenset(
    {
        "shapiro-wilk",
        "anderson-darling",
        "bootstrap",
        "partial correlation",
        "lof",
        "isolation forest",
        "mad",
        "iqr",
        "mcar",
        "mar",
        "mnar",
        "stl",
        "mann-kendall",
        "shap",
        "φ",
        "phi coefficient",
        "r²",
        "r-squared",
        "p-value",
        "permutation importance",
        "arima",
        "holt-winters",
        "spearman",
        "pearson",
        "bca",
        "percentile bootstrap",
    }
)

# ---------------------------------------------------------------------------
# P6-C02 — Methodology registry (ADR-305)
# ---------------------------------------------------------------------------


class UnknownMethodError(Exception):
    """Raised when a method key is not in METHODOLOGY_REGISTRY.

    Per McConnell's defensive-programming principle, silent fallbacks are
    forbidden. Callers that supply an unregistered key get a loud failure
    rather than a missing-citation entry in the report.
    """


# Static registry: display_name, expert_citation, and appendix_text are
# invariant.  The ``parameters`` value here is a sentinel; it is replaced
# with a dynamically rendered string by ``build_registry(prefs)``.
# Do NOT use these raw entries for report output — always call
# ``build_registry(prefs)`` or ``lookup(key, prefs)``.
METHODOLOGY_REGISTRY: dict[str, dict] = {
    "spearman": {
        "key": "spearman",
        "display_name": "Spearman rank correlation",
        "parameters": "n=sample, two-sided",  # rendered by build_registry
        "expert_citation": "Tukey, EDA Ch. 6 — rank-based measures resist outlier distortion",
        "appendix_text": (
            "Spearman's rank correlation coefficient measures the strength of the monotonic "
            "relationship between two variables. It is a robust alternative to Pearson when "
            "data contain outliers or when the variables are not normally distributed. Values "
            "range from −1 (perfect inverse rank order) to +1 (perfect rank order); 0 indicates "
            "no monotonic relationship."
        ),
    },
    "pearson": {
        "key": "pearson",
        "display_name": "Pearson correlation",
        "parameters": "n=sample, two-sided",  # no prefs-controlled params; static is correct
        "expert_citation": "Cleveland, Visualizing Data — linear correlation for continuous, near-normal data",
        "appendix_text": (
            "Pearson's correlation coefficient measures the linear relationship between two "
            "continuous variables. It assumes approximate normality and sensitivity to outliers; "
            "used here only when sample size is sufficient (n ≥ 100) and distributions are "
            "approximately symmetric (AN-12)."
        ),
    },
    "bootstrap_ci": {
        "key": "bootstrap_ci",
        "display_name": "Bootstrap confidence interval (BCa)",
        "parameters": "n=1000, BCa, two-sided, 95%",  # rendered by build_registry
        "expert_citation": (
            "Efron & Tibshirani, An Introduction to the Bootstrap §14 "
            "— BCa intervals correct for bias and skewness"
        ),
        "appendix_text": (
            "Bias-corrected and accelerated (BCa) bootstrap confidence intervals are computed "
            "by resampling with replacement. BCa intervals correct for both bias and skewness "
            "in the bootstrap distribution, making them more accurate than percentile intervals "
            "in skewed samples. The reported interval contains the true parameter with the "
            "stated confidence under repeated sampling."
        ),
    },
    "ci_suppressed_small_n": {
        "key": "ci_suppressed_small_n",
        "display_name": "Bootstrap CI suppressed (small n)",
        "parameters": "AN-12 tier n<10 or n=10-29",
        "expert_citation": (
            "Harrell, Regression Modeling Strategies — bootstrap CIs not meaningful below n=30"
        ),
        "appendix_text": (
            "Bootstrap confidence intervals are not computed when n < 30 (AN-12). The sampling "
            "distribution at small n is not well-approximated by the bootstrap; reporting an "
            "interval would imply more precision than the data supports. The point estimate "
            "(median) is shown without an interval."
        ),
    },
    "iqr_outlier": {
        "key": "iqr_outlier",
        "display_name": "IQR outlier detection",
        "parameters": "k=1.5",  # rendered by build_registry
        "expert_citation": "Tukey, EDA Ch. 2 — fences at Q1−k·IQR and Q3+k·IQR",
        "appendix_text": (
            "Outliers are flagged using Tukey's interquartile range (IQR) fence rule. Values "
            "below Q1 − k·IQR or above Q3 + k·IQR are classified as potential outliers. "
            "The multiplier k controls sensitivity; k=1.5 is the standard setting. This method "
            "requires no distributional assumptions."
        ),
    },
    "mad_outlier": {
        "key": "mad_outlier",
        "display_name": "MAD outlier detection",
        "parameters": "threshold=3.5",  # rendered by build_registry
        "expert_citation": (
            "Leys et al., J. Experimental Social Psychology (2013) "
            "— MAD-based detection, recommended threshold 3.5"
        ),
        "appendix_text": (
            "Outliers are flagged using the median absolute deviation (MAD) method. The modified "
            "z-score (0.6745·(x − median) / MAD) is computed; values with absolute modified "
            "z-score above the threshold are classified as potential outliers. MAD is more "
            "resistant to masking than IQR-based methods in heavily skewed distributions."
        ),
    },
    "iforest_outlier": {
        "key": "iforest_outlier",
        "display_name": "Isolation Forest outlier detection",
        "parameters": "n_estimators=100, contamination=auto",
        "expert_citation": (
            "Liu, Ting & Zhou, ICDM 2008 — isolation partitioning identifies anomalies "
            "requiring fewer splits"
        ),
        "appendix_text": (
            "Isolation Forest detects outliers by randomly partitioning the feature space and "
            "measuring how quickly each point is isolated. Anomalous points require fewer "
            "partitions to isolate. Applied only when n ≥ 1000 (MULTIVARIATE_MIN_N) to ensure "
            "sufficient data for the ensemble (AN-14)."
        ),
    },
    "lof_outlier": {
        "key": "lof_outlier",
        "display_name": "Local Outlier Factor detection",
        "parameters": "n_neighbors=20, contamination=auto",
        "expert_citation": (
            "Breunig et al., SIGMOD 2000 — LOF measures local reachability density "
            "relative to neighbours"
        ),
        "appendix_text": (
            "Local Outlier Factor (LOF) compares the local density of each point to the densities "
            "of its k-nearest neighbours. Points with substantially lower local density than "
            "their neighbours receive high LOF scores and are flagged as potential outliers. "
            "Applied only when n ≥ 1000 (MULTIVARIATE_MIN_N) to avoid noise in sparse "
            "neighbourhoods (AN-14)."
        ),
    },
    "stl_seasonality": {
        "key": "stl_seasonality",
        "display_name": "STL seasonal decomposition",
        "parameters": "seasonal=7, seasonal_strength threshold=0.6",  # rendered by build_registry
        "expert_citation": (
            "Cleveland, Cleveland, McRae & Terpenning, Journal of Official Statistics (1990) "
            "— STL: A Seasonal-Trend Decomposition Procedure Based on Loess"
        ),
        "appendix_text": (
            "Seasonality is detected using STL (Seasonal and Trend decomposition using Loess). "
            "The seasonal component is extracted and its strength is measured as "
            "1 − Var(remainder) / Var(seasonal + remainder). Values above the threshold "
            "indicate meaningful periodicity in the series."
        ),
    },
    "mann_kendall_trend": {
        "key": "mann_kendall_trend",
        "display_name": "Mann-Kendall trend test",
        "parameters": "alpha=0.05, two-sided",  # rendered by build_registry
        "expert_citation": (
            "Hamed & Rao, Journal of Hydrology (1998) — modified Mann-Kendall test "
            "correcting for autocorrelation"
        ),
        "appendix_text": (
            "The Mann-Kendall test detects monotonic trends in time series without assuming "
            "normality or linearity. The test statistic S counts concordant minus discordant "
            "pairs of observations. A statistically significant result (p < α) indicates a "
            "consistent directional trend over the period. Sensitive to autocorrelation; "
            "the modified variant adjusts the variance estimate."
        ),
    },
    "shap_drivers": {
        "key": "shap_drivers",
        "display_name": "SHAP feature importance (drivers)",
        "parameters": "top-k=5 or 10% of features, whichever is larger",  # rendered by build_registry
        "expert_citation": (
            "Lundberg & Lee, NeurIPS 2017 — SHAP: a unified approach to interpreting "
            "model predictions via Shapley values"
        ),
        "appendix_text": (
            "Driver analysis uses SHAP (SHapley Additive exPlanations) values to rank feature "
            "contributions to the target variable. SHAP values are grounded in cooperative game "
            "theory and provide a consistent, locally accurate attribution for each feature. "
            "The top-k features by mean absolute SHAP value are reported."
        ),
    },
    "variance_decomposition": {
        "key": "variance_decomposition",
        "display_name": "Variance decomposition",
        "parameters": "method=partial eta-squared",
        "expert_citation": (
            "Cohen, Statistical Power Analysis for the Behavioral Sciences (2nd ed.) "
            "— effect size via explained variance"
        ),
        "appendix_text": (
            "Variance decomposition quantifies the proportion of total variance in the target "
            "that is attributable to each predictor. Partial eta-squared (η²p) measures the "
            "proportion explained by a predictor holding others constant. Values above 0.14 "
            "indicate a large effect (Cohen's convention)."
        ),
    },
    "partial_correlation": {
        "key": "partial_correlation",
        "display_name": "Partial correlation",
        "parameters": "method=Spearman, controlling for collinear features",
        "expert_citation": (
            "Tukey, EDA Ch. 6 — partial rank correlations control for confound variables"
        ),
        "appendix_text": (
            "Partial correlation measures the relationship between two variables after removing "
            "the linear effect of one or more control variables. Rank-based partial correlation "
            "is used here to retain robustness to outliers. This distinguishes direct associations "
            "from those mediated by correlated predictors."
        ),
    },
    "linear_forecast": {
        "key": "linear_forecast",
        "display_name": "Linear trend forecast",
        "parameters": "OLS, horizon=user-specified",
        "expert_citation": (
            "Hyndman & Athanasopoulos, Forecasting: Principles and Practice (3rd ed.) Ch. 5 "
            "— trend models for deterministic growth"
        ),
        "appendix_text": (
            "A linear trend model is fitted to the historical series using ordinary least squares. "
            "The model assumes a constant rate of change; the forecast extrapolates this trend "
            "to the specified horizon. Prediction intervals widen with horizon distance, "
            "reflecting increasing uncertainty."
        ),
    },
    "arima_forecast": {
        "key": "arima_forecast",
        "display_name": "ARIMA forecast",
        "parameters": "order selected by AIC, maximum p=5, d=2, q=5",
        "expert_citation": (
            "Hyndman & Athanasopoulos, Forecasting: Principles and Practice (3rd ed.) Ch. 9 "
            "— ARIMA model identification and selection"
        ),
        "appendix_text": (
            "ARIMA (AutoRegressive Integrated Moving Average) models capture autocorrelation "
            "structure, trends, and moving-average effects in stationary series. The integration "
            "order d is selected to make the series stationary; p and q are chosen to minimise "
            "AIC. Forecast uncertainty is quantified via analytical prediction intervals."
        ),
    },
    "exp_smoothing_forecast": {
        "key": "exp_smoothing_forecast",
        "display_name": "Exponential smoothing forecast (ETS)",
        "parameters": "model selected by AIC (ETS)",
        "expert_citation": (
            "Hyndman, Koehler, Ord & Snyder, Forecasting with Exponential Smoothing (2008) "
            "— ETS state-space framework"
        ),
        "appendix_text": (
            "Exponential smoothing (ETS) models weight recent observations more heavily than "
            "older ones. The ETS framework selects among error, trend, and seasonal components "
            "(additive or multiplicative) by minimising AIC. ETS is robust for series without "
            "strong autocorrelation beyond the seasonal pattern."
        ),
    },
}


def build_registry(prefs: dict) -> dict[str, dict]:
    """Build a copy of METHODOLOGY_REGISTRY with ``parameters`` rendered from *prefs*.

    Post-R4 fix MEDIUM-T66: parameters strings MUST reflect the active
    constants/prefs values, not hardcoded literals from the static registry.

    Args:
        prefs: User preferences dict (see ``_shared/prefs.DEFAULTS``).  Only
            the keys relevant to each method are consumed; unknown keys are
            ignored.

    Returns:
        ``dict[str, dict]`` — a new dict (not a mutated copy of the static
        registry) with every entry's ``parameters`` field replaced by a
        rendered string.
    """
    n_iter = prefs.get("bootstrap_n_iter", 1000)
    confidence = prefs.get("bootstrap_confidence", 0.95)
    confidence_pct = int(confidence * 100)
    iqr_k = prefs.get("outlier_iqr_k", 1.5)
    mad_threshold = prefs.get("outlier_mad_threshold", 3.5)
    trend_alpha = prefs.get("trend_alpha", 0.05)
    seasonal_threshold = prefs.get("seasonal_strength_threshold", 0.6)
    driver_k_floor = prefs.get("driver_k_floor", 5)
    driver_k_fraction = prefs.get("driver_k_fraction", 0.10)
    driver_k_pct = int(driver_k_fraction * 100)

    rendered_parameters: dict[str, str] = {
        "spearman": "n=sample, two-sided",
        "pearson": "n=sample, two-sided",
        "bootstrap_ci": f"n={n_iter}, BCa, two-sided, {confidence_pct}%",
        "ci_suppressed_small_n": "AN-12 tier n<10 or n=10-29",
        "iqr_outlier": f"k={iqr_k}",
        "mad_outlier": f"threshold={mad_threshold}",
        "iforest_outlier": "n_estimators=100, contamination=auto",
        "lof_outlier": "n_neighbors=20, contamination=auto",
        "stl_seasonality": f"seasonal=7, seasonal_strength threshold={seasonal_threshold}",
        "mann_kendall_trend": f"alpha={trend_alpha}, two-sided",
        "shap_drivers": f"top-k={driver_k_floor} or {driver_k_pct}% of features, whichever is larger",
        "variance_decomposition": "method=partial eta-squared",
        "partial_correlation": "method=Spearman, controlling for collinear features",
        "linear_forecast": "OLS, horizon=user-specified",
        "arima_forecast": "order selected by AIC, maximum p=5, d=2, q=5",
        "exp_smoothing_forecast": "model selected by AIC (ETS)",
    }

    result: dict[str, dict] = {}
    for key, entry in METHODOLOGY_REGISTRY.items():
        new_entry = dict(entry)
        new_entry["parameters"] = rendered_parameters.get(key, entry["parameters"])
        result[key] = new_entry
    return result


def lookup(method_key: str, prefs: dict) -> dict:
    """Return the registry entry for *method_key* with rendered parameters.

    Args:
        method_key: Snake-case method identifier (e.g. ``"spearman"``).
        prefs: Active user preferences dict.

    Returns:
        Entry dict with all 5 fields (key, display_name, parameters,
        expert_citation, appendix_text).

    Raises:
        UnknownMethodError: If *method_key* is not in the registry.
            Silent fallbacks are forbidden (McConnell defensive programming).
    """
    reg = build_registry(prefs)
    if method_key not in reg:
        raise UnknownMethodError(
            f"Method key {method_key!r} is not registered in METHODOLOGY_REGISTRY. "
            f"Registered keys: {sorted(reg.keys())}"
        )
    return reg[method_key]


def aggregate_appendix(method_keys: Iterable[str], prefs: dict) -> list[dict]:
    """Deduplicate and sort method entries for the methodology appendix.

    TC-AN-13-02: the appendix consolidates all method + expert citations
    from the analysis, with no duplicates, sorted alphabetically by
    display_name for scannability.

    Args:
        method_keys: Any iterable of method keys (may contain duplicates).
        prefs: Active user preferences dict.

    Returns:
        Sorted ``list[dict]`` — one entry per unique method key, ordered
        by ``display_name`` ascending.
    """
    reg = build_registry(prefs)
    seen: set[str] = set()
    entries: list[dict] = []
    for key in method_keys:
        if key not in seen:
            seen.add(key)
            if key not in reg:
                raise UnknownMethodError(
                    f"Method key {key!r} is not registered in METHODOLOGY_REGISTRY. "
                    f"Registered keys: {sorted(reg.keys())}"
                )
            entries.append(reg[key])
    return sorted(entries, key=lambda e: e["display_name"])
