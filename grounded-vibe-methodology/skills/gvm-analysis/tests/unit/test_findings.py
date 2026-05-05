"""Tests for `_shared/findings.py` — schema validation + atomic write (P1-C02).

Covers the tracer-bullet scope: top-level structural validation, schema_version
check, roundtrip via write_atomic + read_findings, refusal to write invalid data.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


MINIMAL_PROVENANCE = {
    "input_files": [],
    "mode": "explore",
    "target_column": None,
    "baseline_file": None,
    "seed": 42,
    "sub_seeds": {},
    "timestamp": "2026-04-20T00:00:00Z",
    "preferences": {},
    "preferences_hash": "sha256:deadbeef",
    "lib_versions": {"python": "3.12.0"},
    "anonymised_input_detected": False,
    "anonymised_columns": [],
    "formula_columns": [],
    "sample_applied": None,
    "domain": None,
    "warnings": [],
    "time_column": None,
    "bootstrap_n_iter_used": 0,
}


def test_build_empty_findings_validates() -> None:
    """The skeleton produced by build_empty_findings is schema-valid."""
    from _shared import findings

    data = findings.build_empty_findings(provenance=MINIMAL_PROVENANCE)
    findings.validate(data)  # must not raise


def test_build_empty_findings_has_all_top_level_keys() -> None:
    """The skeleton contains every required top-level key from ADR-201."""
    from _shared import findings

    data = findings.build_empty_findings(provenance=MINIMAL_PROVENANCE)
    required = {
        "schema_version",
        "provenance",
        "columns",
        "outliers",
        "duplicates",
        "time_series",
        "drivers",
        "headline_findings",
        "comprehension_questions",
        "drillthroughs",
    }
    assert required <= set(data.keys())
    assert data["schema_version"] == findings.CURRENT_SCHEMA_VERSION


def test_validate_raises_on_wrong_schema_version() -> None:
    """Wrong schema_version raises SchemaValidationError naming both values."""
    from _shared import findings

    data = findings.build_empty_findings(provenance=MINIMAL_PROVENANCE)
    data["schema_version"] = 2

    with pytest.raises(findings.SchemaValidationError) as exc:
        findings.validate(data)
    assert "schema_version" in str(exc.value)
    assert "2" in str(exc.value)
    assert "1" in str(exc.value)


def test_validate_raises_on_missing_top_level_key() -> None:
    """Missing a required top-level key raises with the key name."""
    from _shared import findings

    data = findings.build_empty_findings(provenance=MINIMAL_PROVENANCE)
    del data["columns"]

    with pytest.raises(findings.SchemaValidationError) as exc:
        findings.validate(data)
    assert "columns" in str(exc.value)


def test_validate_rejects_non_dict() -> None:
    """Non-dict input raises with type info in the message."""
    from _shared import findings

    with pytest.raises(findings.SchemaValidationError) as exc:
        findings.validate("not a dict")  # type: ignore[arg-type]
    assert "dict" in str(exc.value).lower()


def test_roundtrip_write_read(tmp_path: Path) -> None:
    """write_atomic + read_findings round-trip preserves structural content."""
    from _shared import findings

    data = findings.build_empty_findings(provenance=MINIMAL_PROVENANCE)
    target = tmp_path / "findings.json"

    findings.write_atomic(target, data)
    roundtripped = findings.read_findings(target)

    assert roundtripped == data


def test_write_atomic_refuses_invalid_data_and_leaves_target_alone(
    tmp_path: Path,
) -> None:
    """write_atomic validates and refuses to create the target on invalid input."""
    from _shared import findings

    target = tmp_path / "findings.json"
    broken = {"schema_version": 1}  # missing all the other required keys

    with pytest.raises(findings.SchemaValidationError):
        findings.write_atomic(target, broken)
    assert not target.exists(), "target must not be created when validation fails"


def test_write_atomic_preserves_existing_target_on_validation_failure(
    tmp_path: Path,
) -> None:
    """A pre-existing valid findings.json survives a failed overwrite attempt.

    This is the core atomicity guarantee of ADR-209: a subsequent write_atomic
    that fails validation MUST NOT corrupt or truncate the existing file.
    """
    from _shared import findings

    target = tmp_path / "findings.json"
    valid = findings.build_empty_findings(provenance=MINIMAL_PROVENANCE)
    findings.write_atomic(target, valid)
    original_text = target.read_text()

    broken = {"schema_version": 1}  # missing all the other required keys
    with pytest.raises(findings.SchemaValidationError):
        findings.write_atomic(target, broken)

    assert target.read_text() == original_text, (
        "existing target must be preserved byte-for-byte on validation failure"
    )


def test_crossvolumewriteerror_inherits_oserror() -> None:
    """CrossVolumeWriteError is catchable as OSError for callers that handle both."""
    from _shared import findings

    assert issubclass(findings.CrossVolumeWriteError, OSError)


def test_write_atomic_accepts_string_path(tmp_path: Path) -> None:
    """write_atomic accepts str paths identically to Path objects."""
    from _shared import findings

    data = findings.build_empty_findings(provenance=MINIMAL_PROVENANCE)
    target = tmp_path / "findings.json"

    findings.write_atomic(str(target), data)
    assert target.exists()

    # File contains valid JSON that matches the input
    assert json.loads(target.read_text()) == data


def test_read_findings_accepts_string_path(tmp_path: Path) -> None:
    """read_findings accepts str paths identically to Path objects.

    Symmetric with write_atomic's string-path test; covers the other arm
    of the ``Path | str`` contract declared on the public API.
    """
    from _shared import findings

    data = findings.build_empty_findings(provenance=MINIMAL_PROVENANCE)
    target = tmp_path / "findings.json"
    findings.write_atomic(target, data)

    roundtripped = findings.read_findings(str(target))
    assert roundtripped == data


def test_write_atomic_raises_cross_volume_write_error_on_exdev(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """EXDEV on os.replace is wrapped as CrossVolumeWriteError per ADR-209.

    Simulated via monkeypatching os.replace to raise OSError(errno.EXDEV).
    The diagnostic must mention the different-filesystem cause so the
    caller (P5-C02 wrapper) can surface actionable guidance.
    """
    import errno
    import os as _os

    from _shared import findings

    data = findings.build_empty_findings(provenance=MINIMAL_PROVENANCE)
    target = tmp_path / "findings.json"

    def _fake_replace(src: object, dst: object) -> None:
        raise OSError(errno.EXDEV, "Invalid cross-device link")

    monkeypatch.setattr(_os, "replace", _fake_replace)

    with pytest.raises(findings.CrossVolumeWriteError) as exc:
        findings.write_atomic(target, data)

    msg = str(exc.value)
    assert "different filesystems" in msg or "different filesystem" in msg
    assert "output-dir" in msg


def _empty_with(provenance: dict | None = None) -> dict:
    """Helper: return a fresh empty findings doc."""
    from _shared import findings

    return findings.build_empty_findings(provenance=provenance or MINIMAL_PROVENANCE)


# ---------------------------------------------------------------------------
# P19-C01: chart-path schema additions
# ---------------------------------------------------------------------------


def test_build_empty_findings_chart_fields_absent_or_null() -> None:
    """build_empty_findings produces a doc that is schema-valid without chart fields.

    The chart-path additions are OPTIONAL; the empty skeleton must keep validating.
    """
    from _shared import findings

    data = _empty_with()
    findings.validate(data)


def test_validate_accepts_columns_with_chart_paths() -> None:
    """columns[].charts with relative POSIX paths under charts/ validates."""
    from _shared import findings

    data = _empty_with()
    data["columns"] = [
        {
            "name": "score",
            "charts": {
                "histogram": "charts/score.histogram.svg",
                "boxplot": "charts/score.boxplot.svg",
            },
        }
    ]
    findings.validate(data)


def test_validate_accepts_partial_chart_population() -> None:
    """Histogram populated, boxplot null — still valid (each path is independent)."""
    from _shared import findings

    data = _empty_with()
    data["columns"] = [
        {
            "name": "score",
            "charts": {"histogram": "charts/score.histogram.svg", "boxplot": None},
        }
    ]
    findings.validate(data)


def test_validate_accepts_outlier_entry_chart_path() -> None:
    """outliers.by_method.iqr[].chart accepts a relative POSIX charts/ path."""
    from _shared import findings

    data = _empty_with()
    data["outliers"]["by_method"]["iqr"] = [
        {"row_index": 7, "column": "score", "chart": "charts/score.outliers.iqr.svg"}
    ]
    findings.validate(data)


def test_validate_accepts_driver_partial_dependence_chart() -> None:
    """drivers.entries[].partial_dependence_chart accepts a charts/ path."""
    from _shared import findings

    data = _empty_with()
    data["drivers"] = {
        "entries": [
            {
                "feature": "score",
                "partial_dependence_chart": "charts/drivers.score.pdp.svg",
            }
        ]
    }
    findings.validate(data)


def test_validate_accepts_time_series_charts() -> None:
    """time_series.charts.line and .decomposition accept charts/ paths."""
    from _shared import findings

    data = _empty_with()
    data["time_series"] = {
        "charts": {
            "line": "charts/timeseries.line.svg",
            "decomposition": "charts/timeseries.decomposition.svg",
        }
    }
    findings.validate(data)


@pytest.mark.parametrize(
    "bad_path,reason",
    [
        ("/charts/score.histogram.svg", "absolute"),
        ("C:/charts/score.svg", "windows-drive"),
        ("score.svg", "outside-charts-dir"),
        ("../charts/score.svg", "parent-traversal"),
        ("charts/../etc/passwd", "parent-traversal-mid"),
        ("charts/./score.svg", "dot-segment"),
        ("charts\\score.svg", "backslash"),
        ("Charts/score.svg", "wrong-case-prefix"),
    ],
)
def test_validate_rejects_invalid_chart_path(bad_path: str, reason: str) -> None:
    """Any chart path that is not a relative POSIX path under charts/ is rejected."""
    from _shared import findings

    data = _empty_with()
    data["columns"] = [
        {"name": "score", "charts": {"histogram": bad_path, "boxplot": None}}
    ]
    with pytest.raises(findings.SchemaValidationError) as exc:
        findings.validate(data)
    msg = str(exc.value).lower()
    assert "chart" in msg or "charts/" in msg
    # parametrised `reason` is the test-id label only


@pytest.mark.parametrize(
    "method", ["iqr", "mad", "isolation_forest", "local_outlier_factor"]
)
def test_validate_rejects_invalid_path_in_any_outlier_method(method: str) -> None:
    """Every outlier method's entries[].chart is validated, not just iqr/mad."""
    from _shared import findings

    data = _empty_with()
    data["outliers"]["by_method"][method] = [
        {"row_index": 0, "column": "x", "chart": "/abs/path.svg"}
    ]
    with pytest.raises(findings.SchemaValidationError):
        findings.validate(data)


def test_validate_rejects_non_list_outlier_method() -> None:
    """A non-null non-list value under outliers.by_method.<method> is rejected.

    Prevents an invalid chart path from smuggling through validate() because
    the scan loop silently skipped a malformed (e.g. dict) container.
    """
    from _shared import findings

    data = _empty_with()
    data["outliers"]["by_method"]["iqr"] = {
        "not": "a list",
        "chart": "/abs.svg",
    }
    with pytest.raises(findings.SchemaValidationError) as exc:
        findings.validate(data)
    assert "iqr" in str(exc.value)


def test_validate_rejects_invalid_path_in_outlier_entry() -> None:
    """The validation traversal reaches outliers.by_method[*][i].chart, not just columns."""
    from _shared import findings

    data = _empty_with()
    data["outliers"]["by_method"]["mad"] = [
        {"row_index": 0, "column": "x", "chart": "/abs/path.svg"}
    ]
    with pytest.raises(findings.SchemaValidationError):
        findings.validate(data)


def test_validate_rejects_invalid_path_in_driver_entry() -> None:
    """drivers.entries[].partial_dependence_chart is validated."""
    from _shared import findings

    data = _empty_with()
    data["drivers"] = {
        "entries": [{"feature": "x", "partial_dependence_chart": "../escape.svg"}]
    }
    with pytest.raises(findings.SchemaValidationError):
        findings.validate(data)


def test_validate_rejects_invalid_path_in_time_series_charts() -> None:
    """time_series.charts.line is validated."""
    from _shared import findings

    data = _empty_with()
    data["time_series"] = {"charts": {"line": "no_prefix.svg", "decomposition": None}}
    with pytest.raises(findings.SchemaValidationError):
        findings.validate(data)


def test_validate_rejects_non_string_chart_path() -> None:
    """A non-string non-null chart path (e.g. int, list) is rejected."""
    from _shared import findings

    data = _empty_with()
    data["columns"] = [{"name": "score", "charts": {"histogram": 42, "boxplot": None}}]
    with pytest.raises(findings.SchemaValidationError):
        findings.validate(data)


def test_roundtrip_write_read_with_charts_populated(tmp_path: Path) -> None:
    """write_atomic + read_findings round-trips a doc with all chart fields populated."""
    from _shared import findings

    data = _empty_with()
    data["columns"] = [
        {
            "name": "score",
            "charts": {
                "histogram": "charts/score.histogram.svg",
                "boxplot": "charts/score.boxplot.svg",
            },
        }
    ]
    data["outliers"]["by_method"]["iqr"] = [
        {"row_index": 7, "column": "score", "chart": "charts/score.iqr.svg"}
    ]
    data["drivers"] = {
        "entries": [
            {
                "feature": "score",
                "partial_dependence_chart": "charts/score.pdp.svg",
            }
        ]
    }
    data["time_series"] = {
        "charts": {
            "line": "charts/ts.line.svg",
            "decomposition": "charts/ts.decomp.svg",
        }
    }

    target = tmp_path / "findings.json"
    findings.write_atomic(target, data)
    roundtripped = findings.read_findings(target)
    assert roundtripped == data


def test_write_atomic_refuses_invalid_chart_path(tmp_path: Path) -> None:
    """write_atomic refuses to materialise findings with an invalid chart path."""
    from _shared import findings

    data = _empty_with()
    data["columns"] = [
        {"name": "score", "charts": {"histogram": "/abs/score.svg", "boxplot": None}}
    ]
    target = tmp_path / "findings.json"
    with pytest.raises(findings.SchemaValidationError):
        findings.write_atomic(target, data)
    assert not target.exists()


def test_write_atomic_reraises_non_exdev_oserror_leaving_tmp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-EXDEV OSErrors from os.replace propagate unwrapped.

    ADR-209 callers MAY clean up the .tmp artefact. Here we assert two
    things: (a) the OSError propagates as itself (not CrossVolumeWriteError),
    (b) the .tmp file persists for caller inspection.
    """
    import errno
    import os as _os

    from _shared import findings

    data = findings.build_empty_findings(provenance=MINIMAL_PROVENANCE)
    target = tmp_path / "findings.json"
    tmp = target.parent / (target.name + ".tmp")

    def _fake_replace(src: object, dst: object) -> None:
        raise OSError(errno.EACCES, "Permission denied")

    monkeypatch.setattr(_os, "replace", _fake_replace)

    with pytest.raises(OSError) as exc:
        findings.write_atomic(target, data)

    assert not isinstance(exc.value, findings.CrossVolumeWriteError)
    assert tmp.exists(), "non-EXDEV failure must leave .tmp for inspection"
    assert not target.exists(), "target must not be created on failed replace"
