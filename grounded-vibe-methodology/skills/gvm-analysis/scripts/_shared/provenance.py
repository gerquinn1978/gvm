"""Reproducibility primitives: SHA-256, lib versions, timestamps, sub-seeds,
and preferences hash (P2-C03).

Owns the pure-function primitives the engine entry-point and orchestration
layer (P5-*) assemble into the ``provenance`` block of ``findings.json``
per ADR-201. This module does NOT:

* load files (that is :mod:`_shared.io`);
* write ``findings.json`` (that is :mod:`_shared.findings` in a later chunk);
* orchestrate the engine (that is P5).

The ASR-3 reproducibility contract (same input + same seed → byte-identical
``findings.json``) depends on two invariants this module enforces:

1. :func:`sha256_file` is a streaming hash — arbitrary file sizes hash
   without OOM. Its output equals ``hashlib.sha256(content).hexdigest()``
   for every byte content.
2. :func:`derive_sub_seeds` draws from the parent RNG in the SPEC-FIXED
   order. Any reordering shifts the parent RNG draw count and breaks
   reproducibility against existing ``findings.json`` files. New sub-seeds
   MUST append at the end of the returned dict; never insert.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata as _metadata
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

__all__ = [
    "sha256_file",
    "file_provenance",
    "lib_versions",
    "timestamp_iso",
    "derive_sub_seeds",
    "preferences_hash",
]


# Package list mirrors the required-dep group in pyproject.toml. The key is
# the importable name (AN-5 contract — sklearn, not scikit-learn).
_REPORTED_PACKAGES: tuple[str, ...] = (
    "pandas",
    "numpy",
    "scipy",
    "sklearn",
    "statsmodels",
    "openpyxl",
    "matplotlib",
    "pyyaml",
    "jinja2",
    "pymannkendall",
    "packaging",
    "pyarrow",
)

# Some importable names diverge from their distribution names on PyPI —
# importlib.metadata.version needs the distribution name.
_DISTRIBUTION_NAMES: dict[str, str] = {
    "sklearn": "scikit-learn",
    "pyyaml": "PyYAML",
}


def sha256_file(path: Path | str, *, chunk_size: int = 64 * 1024) -> str:
    """Return the lowercase-hex SHA-256 of ``path``'s byte content.

    Streams the file in ``chunk_size`` chunks so memory is O(chunk_size),
    not O(file). Output equals ``hashlib.sha256(path.read_bytes()).hexdigest()``
    for every byte content — the streaming path is a memory optimisation,
    not a semantic one.

    The hash is content-addressable, not secret material — never treat it
    as an authentication token.
    """
    path = Path(path)
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def file_provenance(path: Path | str, df: pd.DataFrame) -> dict[str, Any]:
    """Return the per-file ADR-201 provenance record.

    The caller provides ``df`` — the DataFrame already loaded from
    ``path``. This chunk does not re-load the file (SRP against
    ``_shared.io.load``).

    Returns a dict with exactly the keys ``path``, ``sha256``, ``mtime``,
    ``rows``, ``cols``. Integer fields are Python ``int`` so they JSON-
    serialise cleanly (``numpy.int64`` from ``len(df)`` would otherwise
    require a custom encoder downstream).
    """
    path = Path(path)
    mtime_ts = path.stat().st_mtime
    mtime_dt = datetime.fromtimestamp(mtime_ts, tz=timezone.utc)
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "mtime": mtime_dt.isoformat(),
        "rows": int(len(df)),
        "cols": int(df.shape[1]),
    }


def _metadata_version(package: str) -> str:
    """Thin wrapper around :func:`importlib.metadata.version`.

    Exists so :func:`lib_versions` can be monkeypatched in tests without
    reaching into the stdlib surface.
    """
    distribution = _DISTRIBUTION_NAMES.get(package, package)
    return _metadata.version(distribution)


def _module_version(package: str) -> str:
    """Import ``package`` and read ``__version__``.

    Fallback path when ``importlib.metadata`` cannot resolve the
    distribution (editable installs, vendored modules). A bare
    ``ImportError`` or ``AttributeError`` propagates so the caller can
    fall through to the ``"unknown"`` sentinel.
    """
    module = importlib.import_module(package)
    return str(module.__version__)


def lib_versions() -> dict[str, str]:
    """Snapshot of the Python interpreter + required-package versions.

    Never raises. Missing packages yield ``"unknown"`` — the provenance
    footer must render even on a partial install, and dep enforcement is
    ``_check_deps.py``'s responsibility, not this module's.
    """
    versions: dict[str, str] = {"python": platform.python_version()}
    for pkg in _REPORTED_PACKAGES:
        try:
            versions[pkg] = _metadata_version(pkg)
            continue
        except _metadata.PackageNotFoundError:
            pass
        try:
            versions[pkg] = _module_version(pkg)
        except (ImportError, AttributeError):
            versions[pkg] = "unknown"
    return versions


def timestamp_iso() -> str:
    """UTC ISO-8601 timestamp with explicit ``+00:00`` suffix.

    Uses :func:`datetime.datetime.now` with an explicit ``timezone.utc``
    argument — :func:`datetime.datetime.utcnow` is deprecated in 3.12 and
    returns a naive datetime that would render without a timezone suffix.
    """
    return datetime.now(timezone.utc).isoformat()


def derive_sub_seeds(rng: np.random.Generator, num_columns: int) -> dict[str, Any]:
    """Draw every ADR-202 sub-seed from ``rng`` in the spec-fixed order.

    The dict key order is the contract — ASR-3 reproducibility depends on
    the parent RNG being drawn in a stable sequence so that prior
    ``findings.json`` files remain byte-reproducible against the current
    engine. New sub-seeds MUST append at the end; reordering is a breaking
    change against every historical run.

    ``outliers_lof`` is returned as ``None``: LOF has no ``random_state``,
    so there is nothing to draw. The entry exists so the provenance footer
    records the determinism explicitly.

    Integers are drawn in ``[0, 2**31)`` to fit sklearn's int32
    ``random_state`` contract and cast to Python ``int`` so they serialise
    to JSON without a custom encoder.
    """
    high = 2**31 - 1
    return {
        "outliers_iforest": int(rng.integers(0, high)),
        "outliers_lof": None,
        "drivers_rf": int(rng.integers(0, high)),
        "drivers_rf_perm": int(rng.integers(0, high)),
        "drivers_partial_corr": int(rng.integers(0, high)),
        "forecast_linear_bootstrap": int(rng.integers(0, high)),
        "forecast_arima_init": int(rng.integers(0, high)),
        "forecast_exp_smoothing_init": int(rng.integers(0, high)),
        "per_column": [int(s) for s in rng.integers(0, high, size=num_columns)],
    }


def preferences_hash(prefs: dict[str, Any]) -> str:
    """Deterministic lowercase-hex SHA-256 of a preferences dict.

    Serialises via ``json.dumps(prefs, sort_keys=True, default=str)`` —
    key order is irrelevant, nested structures hash uniformly, and
    non-JSON-native types (e.g. tuples in some future schema extension)
    stringify rather than raise.

    The canonical prefs schema (P2-C02) contains no credentials; this
    function does not sanitise because there is nothing to sanitise. Any
    future schema extension that introduces secrets MUST redact before
    hashing — the hash value appears verbatim in the rendered provenance
    footer.
    """
    canonical = json.dumps(prefs, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
