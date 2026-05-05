"""User preferences: YAML read/write + AN-44 version/migration (P2-C02).

Owns the data primitives for `analysis/preferences.yaml`. The AskUserQuestion
prompt that customises values lives in skill-orchestration (P5-C04); this
module is strictly the file layer.

Public surface:

* :data:`DEFAULTS` — canonical preferences dict. Every value is drawn from
  :mod:`_shared.constants` so a constants edit propagates automatically.
* :data:`SCHEMA` — per-key type + constraint table used by
  :func:`merge_with_defaults`.
* :data:`MIGRATIONS` — per-version migration registry (empty at v1). Future
  versions register `{N: callable(v(N-1)_dict) -> vN_dict}`.
* :data:`CURRENT_VERSION` — mirrors :data:`constants.CURRENT_VERSION`; the
  target the migration chain climbs to.
* :func:`load` — read, migrate (rewriting the file if the version bumped),
  merge-with-defaults, return `(dict, warnings)`. Missing file is not an
  error — it yields a defaults copy.
* :func:`save` — atomic write (tmp + rename) with commented-default lines so
  the file is hand-editable per AN-34.
* :func:`merge_with_defaults` — overlay + validate. Unknown keys warn;
  out-of-range values raise :class:`PreferencesValidationError`.
* :func:`migrate` — apply the migration chain until the dict is at
  :data:`CURRENT_VERSION`.

YAML parsing goes through ``yaml.safe_load`` exclusively — AN-34 invites
hand-editing, which makes the prefs file attacker-controllable surface.
``yaml.load`` deserialises arbitrary Python objects and is an RCE vector
against this file.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any, Callable

import yaml

from _shared import constants, diagnostics

__all__ = [
    "DEFAULTS",
    "SCHEMA",
    "MIGRATIONS",
    "CURRENT_VERSION",
    "PreferencesMigrationError",
    "PreferencesValidationError",
    "load",
    "save",
    "merge_with_defaults",
    "migrate",
]


CURRENT_VERSION: int = constants.CURRENT_VERSION


class PreferencesMigrationError(Exception):
    """Raised when a prefs file cannot be upgraded to CURRENT_VERSION.

    Includes: a missing step in the MIGRATIONS chain, a file written at a
    version newer than this skill supports (forward-only), or a registered
    migration raising during application.
    """


class PreferencesValidationError(Exception):
    """Raised when a merged prefs dict violates a SCHEMA constraint.

    Names the offending key and the received value so the orchestration
    layer can surface an actionable diagnostic.
    """


def _build_defaults() -> dict[str, Any]:
    """Assemble DEFAULTS from constants.py.

    Built at import time rather than stored as a literal so changing a
    value in constants.py propagates here without a parallel edit. The
    outer helper makes the sourcing explicit.
    """
    return {
        "version": constants.CURRENT_VERSION,
        "headline_count": constants.HEADLINE_COUNT,
        "bootstrap_n_iter": constants.BOOTSTRAP_N_ITER,
        "bootstrap_confidence": constants.BOOTSTRAP_CONFIDENCE,
        "trend_alpha": constants.TREND_ALPHA,
        "seasonal_strength_threshold": constants.SEASONAL_STRENGTH_THRESHOLD,
        "outlier_methods": list(constants.OUTLIER_METHODS_DEFAULT),
        "time_series_gap_threshold": constants.TIME_SERIES_GAP_THRESHOLD,
        "time_series_stale_threshold_days": constants.TIME_SERIES_STALE_THRESHOLD_DAYS,
        "fuzzy_duplicate_threshold": constants.FUZZY_DUPLICATE_THRESHOLD,
        "data_quality_checks": {key: True for key in constants.DATA_QUALITY_CHECK_KEYS},
    }


DEFAULTS: dict[str, Any] = _build_defaults()


def _in_closed_range(lo: float, hi: float) -> Callable[[Any], bool]:
    return lambda v: (
        isinstance(v, (int, float)) and not isinstance(v, bool) and lo <= v <= hi
    )


def _in_open_range(lo: float, hi: float) -> Callable[[Any], bool]:
    return lambda v: (
        isinstance(v, (int, float)) and not isinstance(v, bool) and lo < v < hi
    )


def _is_subset_of(allowed: frozenset[str]) -> Callable[[Any], bool]:
    def check(v: Any) -> bool:
        if not isinstance(v, list) or not v:
            return False
        return all(isinstance(item, str) for item in v) and set(v).issubset(allowed)

    return check


def _is_positive_int() -> Callable[[Any], bool]:
    return lambda v: isinstance(v, int) and not isinstance(v, bool) and v > 0


def _is_bool_dict(required_keys: tuple[str, ...]) -> Callable[[Any], bool]:
    def check(v: Any) -> bool:
        if not isinstance(v, dict):
            return False
        if not set(v.keys()).issubset(set(required_keys)):
            return False
        return all(isinstance(val, bool) for val in v.values())

    return check


SCHEMA: dict[str, dict[str, Any]] = {
    "version": {
        "type": int,
        "default": constants.CURRENT_VERSION,
        "constraint": lambda v: (
            isinstance(v, int)
            and not isinstance(v, bool)
            and v == constants.CURRENT_VERSION
        ),
        "description": "must equal CURRENT_VERSION",
    },
    "headline_count": {
        "type": int,
        "default": constants.HEADLINE_COUNT,
        "constraint": lambda v: (
            isinstance(v, int) and not isinstance(v, bool) and 3 <= v <= 10
        ),
        "description": "range [3, 10]",
    },
    "bootstrap_n_iter": {
        "type": int,
        "default": constants.BOOTSTRAP_N_ITER,
        "constraint": lambda v: (
            isinstance(v, int) and not isinstance(v, bool) and 200 <= v <= 10000
        ),
        "description": "range [200, 10000]",
    },
    "bootstrap_confidence": {
        "type": float,
        "default": constants.BOOTSTRAP_CONFIDENCE,
        "constraint": _in_open_range(0.5, 0.999),
        "description": "range (0.5, 0.999)",
    },
    "trend_alpha": {
        "type": float,
        "default": constants.TREND_ALPHA,
        "constraint": _in_open_range(0.0, 0.5),
        "description": "range (0, 0.5)",
    },
    "seasonal_strength_threshold": {
        "type": float,
        "default": constants.SEASONAL_STRENGTH_THRESHOLD,
        "constraint": _in_open_range(0.0, 1.0),
        "description": "range (0, 1)",
    },
    "outlier_methods": {
        "type": list,
        "default": list(constants.OUTLIER_METHODS_DEFAULT),
        "constraint": _is_subset_of(constants.OUTLIER_METHODS_ALLOWED),
        "description": f"subset of {sorted(constants.OUTLIER_METHODS_ALLOWED)}",
    },
    "time_series_gap_threshold": {
        "type": float,
        "default": constants.TIME_SERIES_GAP_THRESHOLD,
        "constraint": lambda v: (
            isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0
        ),
        "description": "positive number (multiplier × inferred cadence)",
    },
    "time_series_stale_threshold_days": {
        "type": int,
        "default": constants.TIME_SERIES_STALE_THRESHOLD_DAYS,
        "constraint": _is_positive_int(),
        "description": "positive integer",
    },
    "fuzzy_duplicate_threshold": {
        "type": float,
        "default": constants.FUZZY_DUPLICATE_THRESHOLD,
        "constraint": _in_closed_range(0.5, 1.0),
        "description": "range [0.5, 1.0]",
    },
    "data_quality_checks": {
        "type": dict,
        "default": {key: True for key in constants.DATA_QUALITY_CHECK_KEYS},
        "constraint": _is_bool_dict(constants.DATA_QUALITY_CHECK_KEYS),
        "description": (
            f"dict with bool values; keys subset of {list(constants.DATA_QUALITY_CHECK_KEYS)}"
        ),
    },
}


MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {}


def migrate(prefs: dict[str, Any]) -> dict[str, Any]:
    """Climb the MIGRATIONS chain until ``prefs["version"] == CURRENT_VERSION``.

    Files without a ``version`` key are treated as v1 (AN-44). A file from
    a newer skill raises — this is a forward-only migration path. A missing
    step in the chain raises rather than silently skipping.
    """
    v = prefs.get("version", 1)
    if not isinstance(v, int) or isinstance(v, bool):
        raise PreferencesMigrationError(
            f"preferences.yaml has a non-integer `version` value: {v!r}. "
            f"The top-level `version` key must be an integer."
        )
    if v > CURRENT_VERSION:
        raise PreferencesMigrationError(
            f"preferences.yaml was written at version {v}; "
            f"this skill supports CURRENT_VERSION={CURRENT_VERSION}. "
            f"Downgrade is not supported — upgrade the skill or delete "
            f"preferences.yaml to start fresh."
        )
    while v < CURRENT_VERSION:
        step = v + 1
        if step not in MIGRATIONS:
            raise PreferencesMigrationError(
                f"No migration registered from v{v} to v{step}. "
                f"Cannot upgrade preferences.yaml from version {v} to "
                f"{CURRENT_VERSION}."
            )
        prefs = MIGRATIONS[step](prefs)
        prefs["version"] = step
        v = step
    return prefs


def _deep_merge(defaults: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Recursively overlay overrides on defaults for nested dicts.

    Only one level of nesting is used (`data_quality_checks`), but the
    recursive form is clearer at the point of use and avoids a special case
    that would need its own test.
    """
    merged = copy.deepcopy(defaults)
    for key, value in overrides.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def merge_with_defaults(prefs: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Overlay ``prefs`` on DEFAULTS and validate against SCHEMA.

    Unknown keys are recorded in ``warnings`` (ADR-104: unknown keys must
    not block the run — they are surfaced via ``provenance.warnings``).
    Values outside their declared constraints raise
    :class:`PreferencesValidationError`.
    """
    if not isinstance(prefs, dict):
        raise PreferencesValidationError(
            f"preferences payload must be a dict, got {type(prefs).__name__}"
        )

    warnings: list[str] = []
    for key in prefs:
        if key not in SCHEMA:
            warnings.append(
                f"unknown preference key `{key}` ignored (not in canonical schema)"
            )

    merged = _deep_merge(DEFAULTS, prefs)

    for key, spec in SCHEMA.items():
        value = merged[key]
        if not spec["constraint"](value):
            raise PreferencesValidationError(
                f"preference `{key}` = {value!r} is invalid: {spec['description']}"
            )

    return merged, warnings


def _parse_yaml(text: str, path: Path) -> dict[str, Any]:
    """Parse YAML text; map pyyaml errors to MalformedFileError.

    ``yaml.safe_load`` only — never ``yaml.load``. AN-34 explicitly invites
    hand-editing, which makes the file attacker-controllable; the safe
    loader refuses to instantiate arbitrary Python objects.
    """
    try:
        loaded = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        row: int | None = None
        col: int | None = None
        mark = getattr(exc, "problem_mark", None)
        if mark is not None:
            row = mark.line
            col = mark.column
        raise diagnostics.MalformedFileError(
            path, row=row, col=col, kind="malformed_yaml"
        ) from exc

    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise diagnostics.MalformedFileError(
            path, row=None, col=None, kind="malformed_yaml"
        )
    return loaded


def load(path: Path | str) -> tuple[dict[str, Any], list[str]]:
    """Read preferences.yaml, migrate if needed, validate, and return
    ``(merged_prefs, warnings)``.

    Missing file: returns a deep-copy of DEFAULTS with no warnings (the
    first-run path; not an error). Empty file: same as missing.

    Version-less file: per AN-44, treated as v1; the file is rewritten with
    ``version: 1`` added so the next run sees an explicit version key.

    Newer version: raises :class:`PreferencesMigrationError` (forward-only).

    Malformed YAML: raises :class:`diagnostics.MalformedFileError` with
    ``kind="malformed_yaml"`` and the pyyaml-reported row/col.
    """
    path = Path(path)
    if not path.exists():
        return copy.deepcopy(DEFAULTS), []

    text = path.read_text(encoding="utf-8")
    raw = _parse_yaml(text, path)

    rewrite_after_load = "version" not in raw
    migrated = migrate(raw)

    merged, warnings = merge_with_defaults(migrated)

    if rewrite_after_load or migrated.get("version") != raw.get("version"):
        save(path, merged)

    return merged, warnings


def save(path: Path | str, prefs: dict[str, Any]) -> None:
    """Atomic-write preferences.yaml with commented-default lines (AN-34).

    The write protocol mirrors ADR-209's ``write_atomic``: serialise to a
    sibling ``.tmp`` file, then ``os.replace`` onto the target so a reader
    never observes a partially-written file. ADR-209's canonical
    implementation lives in ``_shared/findings.py`` and handles JSON; this
    is its YAML twin and intentionally inlined (findings.py is built in a
    later chunk). Same-volume precondition: writing to the same directory
    guarantees it.
    """
    path = Path(path)
    header = (
        "# analysis/preferences.yaml — GVM /gvm-analysis preferences.\n"
        "# Hand-editable. Run /gvm-analysis to apply.\n"
        "# Each overridable key shows its shipped default in a `# default:` comment.\n"
        "\n"
    )

    emitted_keys = [
        "version",
        "headline_count",
        "bootstrap_n_iter",
        "bootstrap_confidence",
        "trend_alpha",
        "seasonal_strength_threshold",
        "outlier_methods",
        "time_series_gap_threshold",
        "time_series_stale_threshold_days",
        "fuzzy_duplicate_threshold",
        "data_quality_checks",
    ]

    sections: list[str] = []
    for key in emitted_keys:
        if key not in prefs:
            continue
        current = {key: prefs[key]}
        default_value = DEFAULTS[key]
        block = yaml.safe_dump(
            current, sort_keys=False, default_flow_style=False
        ).rstrip()
        if prefs[key] != default_value:
            default_hint = yaml.safe_dump(
                {"default": default_value},
                sort_keys=False,
                default_flow_style=False,
            ).rstrip()
            commented = "\n".join(f"# {line}" for line in default_hint.splitlines())
            block = f"{commented}\n{block}"
        sections.append(block + "\n")

    content = header + "\n".join(sections)

    tmp = path.parent / (path.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)
