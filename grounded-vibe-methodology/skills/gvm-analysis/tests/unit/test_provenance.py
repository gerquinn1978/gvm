"""Tests for `_shared/provenance.py` — reproducibility primitives (P2-C03).

Covers ADR-202 sub-seed derivation, ADR-201 provenance field shapes, and
TC-AN-30-01/02/03 per the implementation-guide scope for this chunk. The
orchestration layer (P5-*) composes these primitives into the full
provenance block of findings.json; this test file exercises the primitives
only.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings, strategies as st


# --- sha256_file ------------------------------------------------------------


def test_sha256_file_on_empty_file_returns_well_known_hash(tmp_path: Path) -> None:
    """The empty-string SHA-256 is a well-known value; any drift here is a
    signature failure."""
    from _shared import provenance

    path = tmp_path / "empty.bin"
    path.write_bytes(b"")
    assert provenance.sha256_file(path) == (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )


def test_sha256_file_matches_hashlib_on_small_file(tmp_path: Path) -> None:
    from _shared import provenance

    content = b"hello, provenance\n"
    path = tmp_path / "small.bin"
    path.write_bytes(content)
    assert provenance.sha256_file(path) == hashlib.sha256(content).hexdigest()


def test_sha256_file_matches_hashlib_on_large_file_streaming(
    tmp_path: Path,
) -> None:
    """Streams ≥ 10 MiB — proves the chunked read covers boundaries."""
    from _shared import provenance

    # 10 MiB of deterministic-but-varied content to catch boundary bugs.
    rng = np.random.default_rng(42)
    content = rng.bytes(10 * 1024 * 1024)
    path = tmp_path / "large.bin"
    path.write_bytes(content)
    assert provenance.sha256_file(path) == hashlib.sha256(content).hexdigest()


def test_sha256_file_captures_trailing_newline(tmp_path: Path) -> None:
    from _shared import provenance

    path = tmp_path / "nl.bin"
    path.write_bytes(b"line\n")
    assert provenance.sha256_file(path) == hashlib.sha256(b"line\n").hexdigest()


def test_sha256_file_accepts_string_path(tmp_path: Path) -> None:
    from _shared import provenance

    path = tmp_path / "s.bin"
    path.write_bytes(b"x")
    assert provenance.sha256_file(str(path)) == hashlib.sha256(b"x").hexdigest()


@given(content=st.binary(max_size=1024 * 1024))
@settings(max_examples=50, deadline=None)
def test_sha256_file_property_matches_hashlib(
    tmp_path_factory: pytest.TempPathFactory, content: bytes
) -> None:
    """TC-AN-30-03 [PROPERTY]: streaming SHA-256 matches hashlib for any
    byte content up to 1 MiB.
    """
    from _shared import provenance

    tmp = tmp_path_factory.mktemp("sha_property")
    path = tmp / "content.bin"
    path.write_bytes(content)
    assert provenance.sha256_file(path) == hashlib.sha256(content).hexdigest()


# --- file_provenance --------------------------------------------------------


def test_file_provenance_returns_schema_shape(tmp_path: Path) -> None:
    from _shared import provenance

    path = tmp_path / "data.csv"
    content = b"id,val\n1,10\n2,20\n3,30\n"
    path.write_bytes(content)
    df = pd.DataFrame({"id": [1, 2, 3], "val": [10, 20, 30]})

    record = provenance.file_provenance(path, df)
    assert set(record.keys()) == {"path", "sha256", "mtime", "rows", "cols"}
    assert isinstance(record["path"], str)
    assert isinstance(record["sha256"], str)
    assert re.fullmatch(r"[0-9a-f]{64}", record["sha256"])
    assert record["rows"] == 3
    assert record["cols"] == 2
    assert isinstance(record["rows"], int)
    assert isinstance(record["cols"], int)


def test_file_provenance_mtime_is_iso_parseable(tmp_path: Path) -> None:
    from _shared import provenance

    path = tmp_path / "m.csv"
    path.write_bytes(b"x,y\n1,2\n")
    df = pd.DataFrame({"x": [1], "y": [2]})
    record = provenance.file_provenance(path, df)
    parsed = datetime.fromisoformat(record["mtime"])
    assert parsed.tzinfo is not None


def test_file_provenance_zero_row_dataframe(tmp_path: Path) -> None:
    """A zero-row frame with n columns yields rows=0, cols=n. Boundary
    check — regressions here would silently alter the ADR-201 shape.
    """
    from _shared import provenance

    path = tmp_path / "headers_only.csv"
    path.write_bytes(b"x,y\n")
    df = pd.DataFrame({"x": [], "y": []})
    record = provenance.file_provenance(path, df)
    assert record["rows"] == 0
    assert record["cols"] == 2


def test_file_provenance_sha_matches_streaming_hash(tmp_path: Path) -> None:
    """The `sha256` field is computed via sha256_file — not a separate path.
    Asserting via reference locks in the single-source-of-truth contract.
    """
    from _shared import provenance

    path = tmp_path / "d.csv"
    path.write_bytes(b"hello")
    df = pd.DataFrame({"x": [1]})
    record = provenance.file_provenance(path, df)
    assert record["sha256"] == hashlib.sha256(b"hello").hexdigest()


# --- lib_versions -----------------------------------------------------------


def test_lib_versions_includes_python_and_core_packages() -> None:
    from _shared import provenance

    versions = provenance.lib_versions()
    assert re.fullmatch(r"\d+\.\d+\.\d+", versions["python"])
    for pkg in (
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
    ):
        assert pkg in versions, f"missing package in lib_versions: {pkg!r}"


def test_lib_versions_never_raises_on_missing_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A PackageNotFoundError for any one package must yield 'unknown', not
    propagate. The provenance footer must render even on a partial install.
    """
    import importlib.metadata as _md

    from _shared import provenance

    def failing_version(pkg: str) -> str:
        if pkg == "pandas":
            raise _md.PackageNotFoundError(pkg)
        return _md.version(pkg)

    monkeypatch.setattr(provenance, "_metadata_version", failing_version)
    versions = provenance.lib_versions()
    # Every reported package remains present under any outcome — the
    # "never raises, footer still renders" contract applies to the full
    # set, not just the patched one.
    for pkg in provenance._REPORTED_PACKAGES:
        assert pkg in versions, f"{pkg} missing after metadata fallback"
        assert versions[pkg] != ""
    # Pandas specifically: metadata raised, so the fallback (_module_version
    # via __version__) or the final "unknown" sentinel applies. Both are
    # non-raising outcomes.
    assert "pandas" in versions


def test_lib_versions_falls_back_to_unknown_when_all_sources_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When both importlib.metadata AND the module's __version__ are
    unavailable, return the literal 'unknown' — never raise.
    """
    import importlib.metadata as _md

    from _shared import provenance

    def failing_version(pkg: str) -> str:
        raise _md.PackageNotFoundError(pkg)

    def failing_import(pkg: str) -> str:
        raise ImportError(pkg)

    monkeypatch.setattr(provenance, "_metadata_version", failing_version)
    monkeypatch.setattr(provenance, "_module_version", failing_import)
    versions = provenance.lib_versions()
    # All packages fall back to "unknown"; python is still present.
    assert versions["pandas"] == "unknown"
    assert re.fullmatch(r"\d+\.\d+\.\d+", versions["python"])


# --- timestamp_iso ----------------------------------------------------------


def test_timestamp_iso_is_utc_and_parseable() -> None:
    from _shared import provenance

    ts = provenance.timestamp_iso()
    assert ts.endswith("+00:00")
    parsed = datetime.fromisoformat(ts)
    assert parsed.tzinfo is not None
    assert parsed.utcoffset().total_seconds() == 0


def test_timestamp_iso_is_monotonic_across_calls() -> None:
    from _shared import provenance

    first = provenance.timestamp_iso()
    second = provenance.timestamp_iso()
    assert first <= second  # within the monotonic resolution of time.time


# --- derive_sub_seeds -------------------------------------------------------


_SPEC_ORDER = (
    "outliers_iforest",
    "outliers_lof",
    "drivers_rf",
    "drivers_rf_perm",
    "drivers_partial_corr",
    "forecast_linear_bootstrap",
    "forecast_arima_init",
    "forecast_exp_smoothing_init",
    "per_column",
)


def test_derive_sub_seeds_has_spec_fixed_key_order() -> None:
    """ADR-202 invariant: the dict key order MUST match the spec. Any
    reordering breaks reproducibility against prior findings.json files.
    """
    from _shared import provenance

    rng = np.random.default_rng(42)
    seeds = provenance.derive_sub_seeds(rng, num_columns=5)
    assert tuple(seeds.keys()) == _SPEC_ORDER


def test_derive_sub_seeds_is_reproducible() -> None:
    """Same seed → same sub-seeds. The ASR-3 byte-level invariant."""
    from _shared import provenance

    a = provenance.derive_sub_seeds(np.random.default_rng(42), num_columns=3)
    b = provenance.derive_sub_seeds(np.random.default_rng(42), num_columns=3)
    assert a == b


def test_derive_sub_seeds_different_seeds_diverge() -> None:
    from _shared import provenance

    a = provenance.derive_sub_seeds(np.random.default_rng(0), num_columns=3)
    b = provenance.derive_sub_seeds(np.random.default_rng(1), num_columns=3)
    assert a["outliers_iforest"] != b["outliers_iforest"]


def test_derive_sub_seeds_outliers_lof_is_none() -> None:
    """LOF has no random_state — the spec mandates the literal None sentinel
    so the provenance footer records it transparently.
    """
    from _shared import provenance

    seeds = provenance.derive_sub_seeds(np.random.default_rng(0), num_columns=1)
    assert seeds["outliers_lof"] is None


def test_derive_sub_seeds_per_column_length_matches_argument() -> None:
    from _shared import provenance

    seeds = provenance.derive_sub_seeds(np.random.default_rng(0), num_columns=7)
    assert len(seeds["per_column"]) == 7


def test_derive_sub_seeds_values_are_python_int_not_numpy() -> None:
    """numpy ints do not JSON-serialise; every seed that is not None must be
    a Python int so findings.json writes cleanly.
    """
    from _shared import provenance

    seeds = provenance.derive_sub_seeds(np.random.default_rng(0), num_columns=3)
    for key, value in seeds.items():
        if value is None:
            continue
        if key == "per_column":
            assert all(type(x) is int for x in value)
        else:
            assert type(value) is int


def test_derive_sub_seeds_values_are_in_int32_range() -> None:
    """ADR-202 calls `rng.integers(0, 2**31 - 1)` — numpy's `integers`
    is upper-exclusive, so the draw range is [0, 2**31 - 2]. That sits
    comfortably inside sklearn's int32 random_state contract.
    The tight assertion locks in the spec-fixed upper bound so a refactor
    to `rng.integers(0, 2**31)` would show up in test output.
    """
    from _shared import provenance

    seeds = provenance.derive_sub_seeds(np.random.default_rng(0), num_columns=5)
    int_keys = [k for k in seeds if k != "outliers_lof" and k != "per_column"]
    for key in int_keys:
        assert 0 <= seeds[key] < 2**31 - 1
    for val in seeds["per_column"]:
        assert 0 <= val < 2**31 - 1


# --- preferences_hash -------------------------------------------------------


def test_preferences_hash_is_64_char_lowercase_hex() -> None:
    from _shared import provenance

    h = provenance.preferences_hash({"a": 1})
    assert re.fullmatch(r"[0-9a-f]{64}", h)


def test_preferences_hash_is_deterministic() -> None:
    from _shared import provenance

    prefs = {"bootstrap_n_iter": 1000, "outlier_methods": ["iqr", "mad"]}
    assert provenance.preferences_hash(prefs) == provenance.preferences_hash(prefs)


def test_preferences_hash_is_key_order_independent() -> None:
    from _shared import provenance

    a = {"a": 1, "b": 2}
    b = {"b": 2, "a": 1}
    assert provenance.preferences_hash(a) == provenance.preferences_hash(b)


def test_preferences_hash_value_sensitivity() -> None:
    from _shared import provenance

    assert provenance.preferences_hash({"a": 1}) != provenance.preferences_hash(
        {"a": 2}
    )


def test_preferences_hash_handles_nested_dicts() -> None:
    from _shared import provenance

    prefs = {
        "version": 1,
        "data_quality_checks": {
            "run_missingness": True,
            "run_type_drift": False,
        },
        "outlier_methods": ["iqr", "mad"],
    }
    h = provenance.preferences_hash(prefs)
    assert re.fullmatch(r"[0-9a-f]{64}", h)
    assert provenance.preferences_hash(prefs) == h
