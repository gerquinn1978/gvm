"""Tests for `_shared/prefs.py` — YAML prefs with AN-44 versioning (P2-C02).

Covers AN-32 overridable-keys schema, AN-33 persistence, AN-34 hand-editable
format, and AN-44 version/migration. TC-AN-32-01..03 (the AskUserQuestion
prompt) is orchestration (P5-C04) — not tested here. This chunk owns only
the data primitives (read/write/migrate/validate).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st


# --- constants.py extension -------------------------------------------------


def test_constants_declare_preference_defaults() -> None:
    """Every per-key default from the canonical schema must be importable
    as a named constant. A magic number here is a cross-cutting defect.
    """
    from _shared import constants

    assert constants.CURRENT_VERSION == 1
    assert constants.HEADLINE_COUNT == 5
    assert constants.BOOTSTRAP_N_ITER == 1000
    assert constants.BOOTSTRAP_CONFIDENCE == 0.95
    assert constants.TIME_SERIES_GAP_THRESHOLD == 1.5
    assert constants.TIME_SERIES_STALE_THRESHOLD_DAYS == 30
    assert constants.FUZZY_DUPLICATE_THRESHOLD == 0.85
    assert constants.OUTLIER_METHODS_DEFAULT == ("iqr", "mad")
    assert constants.OUTLIER_METHODS_ALLOWED == frozenset(
        {"iqr", "mad", "iforest", "lof"}
    )
    assert constants.DATA_QUALITY_CHECK_KEYS == (
        "run_missingness",
        "run_type_drift",
        "run_rounding",
        "run_exact_duplicates",
        "run_near_duplicates",
    )


def test_constants_preserves_phase_1_threshold_block() -> None:
    """P1-C01 values must NOT drift when P2-C02 extends the module."""
    from _shared import constants

    assert constants.SAMPLE_SIZE_TIERS == (10, 30, 100, 1000, 10000)
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


# --- DEFAULTS ---------------------------------------------------------------


def test_defaults_references_constants_module_not_literals() -> None:
    """DEFAULTS values MUST be drawn from constants.py imports — changing
    a constant must propagate automatically. A literal in prefs.py would
    silently diverge.
    """
    from _shared import constants, prefs

    assert prefs.DEFAULTS["version"] == constants.CURRENT_VERSION
    assert prefs.DEFAULTS["headline_count"] == constants.HEADLINE_COUNT
    assert prefs.DEFAULTS["bootstrap_n_iter"] == constants.BOOTSTRAP_N_ITER
    assert prefs.DEFAULTS["bootstrap_confidence"] == constants.BOOTSTRAP_CONFIDENCE
    assert (
        prefs.DEFAULTS["time_series_gap_threshold"]
        == constants.TIME_SERIES_GAP_THRESHOLD
    )
    assert (
        prefs.DEFAULTS["time_series_stale_threshold_days"]
        == constants.TIME_SERIES_STALE_THRESHOLD_DAYS
    )
    assert (
        prefs.DEFAULTS["fuzzy_duplicate_threshold"]
        == constants.FUZZY_DUPLICATE_THRESHOLD
    )
    assert prefs.DEFAULTS["outlier_methods"] == list(constants.OUTLIER_METHODS_DEFAULT)
    # Every DQ toggle defaults to true and is present by name.
    for key in constants.DATA_QUALITY_CHECK_KEYS:
        assert prefs.DEFAULTS["data_quality_checks"][key] is True


def test_load_returns_deep_copy_not_shared_defaults_reference(
    tmp_path: Path,
) -> None:
    """Mutating the returned dict must not poison subsequent reads — the
    classic shared-mutable-default bug class.
    """
    from _shared import prefs

    missing = tmp_path / "does_not_exist.yaml"
    first, _ = prefs.load(missing)
    first["headline_count"] = 999
    first["data_quality_checks"]["run_missingness"] = False

    second, _ = prefs.load(missing)
    assert second["headline_count"] == 5
    assert second["data_quality_checks"]["run_missingness"] is True


# --- load: missing file + empty file ----------------------------------------


def test_load_on_missing_file_returns_defaults_without_error(tmp_path: Path) -> None:
    """First-run path — no file exists yet. Not an error."""
    from _shared import prefs

    result, warnings = prefs.load(tmp_path / "preferences.yaml")
    assert result["version"] == 1
    assert result["headline_count"] == 5
    assert warnings == []


def test_load_on_empty_file_returns_defaults(tmp_path: Path) -> None:
    """Zero-byte YAML → yaml.safe_load returns None → treat as empty dict."""
    from _shared import prefs

    path = tmp_path / "empty.yaml"
    path.write_text("", encoding="utf-8")
    result, _ = prefs.load(path)
    assert result["version"] == 1


def test_load_accepts_string_path(tmp_path: Path) -> None:
    from _shared import prefs

    path = tmp_path / "str.yaml"
    path.write_text("headline_count: 7\nversion: 1\n", encoding="utf-8")
    result, _ = prefs.load(str(path))
    assert result["headline_count"] == 7


# --- save + round-trip ------------------------------------------------------


def test_save_then_load_roundtrips_defaults(tmp_path: Path) -> None:
    from _shared import prefs

    path = tmp_path / "prefs.yaml"
    prefs.save(path, prefs.DEFAULTS)
    result, warnings = prefs.load(path)
    assert result == prefs.DEFAULTS
    assert warnings == []


def test_save_then_load_roundtrips_partial_customisation(tmp_path: Path) -> None:
    import copy

    from _shared import prefs

    path = tmp_path / "prefs.yaml"
    custom = copy.deepcopy(prefs.DEFAULTS)
    custom["bootstrap_n_iter"] = 500
    prefs.save(path, custom)

    result, _ = prefs.load(path)
    assert result["bootstrap_n_iter"] == 500
    # Unmodified keys retain their defaults.
    assert result["headline_count"] == 5
    assert result["bootstrap_confidence"] == 0.95


def test_save_writes_atomically_via_tmp_rename(tmp_path: Path) -> None:
    """The save path must use `os.replace` on a sibling `.tmp`; after success
    no `.tmp` remains. Tests the atomicity contract from ADR-209 applied to
    YAML writes.
    """
    from _shared import prefs

    path = tmp_path / "prefs.yaml"
    prefs.save(path, prefs.DEFAULTS)
    assert path.exists()
    assert not (tmp_path / "prefs.yaml.tmp").exists()


# --- AN-34 hand-editable YAML -----------------------------------------------


def test_save_output_is_valid_yaml_and_human_readable(tmp_path: Path) -> None:
    """TC-AN-34-01: the saved file must parse as YAML and be a plain text
    document (no binary encoding, no pickled objects).
    """
    import yaml

    from _shared import prefs

    path = tmp_path / "prefs.yaml"
    prefs.save(path, prefs.DEFAULTS)
    text = path.read_text(encoding="utf-8")
    parsed = yaml.safe_load(text)
    assert isinstance(parsed, dict)
    assert parsed["version"] == 1
    # Human-readable means newline-separated key/value pairs, not flow style.
    assert "\n" in text
    assert "{" not in text.splitlines()[1]  # no inline dict on the first data line


def test_save_places_version_key_first(tmp_path: Path) -> None:
    """TC-AN-44-01: version must be the first non-comment key so hand-editors
    see it immediately on opening the file.
    """
    from _shared import prefs

    path = tmp_path / "prefs.yaml"
    prefs.save(path, prefs.DEFAULTS)
    lines = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert lines[0].startswith("version:")


def test_save_emits_commented_default_lines_for_overridden_keys(
    tmp_path: Path,
) -> None:
    """TC-AN-34-01: keys the user has overridden should be followed (or
    preceded) by a commented-out `# default: N` hint so the hand-editor can
    see what the shipped default is without re-running the prompt.
    """
    from _shared import prefs

    path = tmp_path / "prefs.yaml"
    custom = dict(prefs.DEFAULTS)
    custom["bootstrap_n_iter"] = 500
    prefs.save(path, custom)

    text = path.read_text(encoding="utf-8")
    # The override line must be present uncommented.
    assert "bootstrap_n_iter: 500" in text
    # A commented-default hint referencing the shipped default must be present.
    assert "# default: 1000" in text


def test_malformed_yaml_raises_malformed_file_error_with_line(
    tmp_path: Path,
) -> None:
    """TC-AN-34-03: a syntax error produces a clear diagnostic, not a
    pyyaml traceback. `MalformedFileError.row` carries the failing line.
    """
    from _shared import diagnostics, prefs

    path = tmp_path / "broken.yaml"
    path.write_text("version: 1\nheadline_count: [unterminated\n", encoding="utf-8")
    with pytest.raises(diagnostics.MalformedFileError) as exc:
        prefs.load(path)
    assert exc.value.kind == "malformed_yaml"
    assert exc.value.row is not None


def test_load_on_yaml_that_parses_to_non_mapping_raises(tmp_path: Path) -> None:
    """A file containing a bare YAML scalar or list parses successfully but
    is not a preferences mapping. Treat as malformed.
    """
    from _shared import diagnostics, prefs

    path = tmp_path / "scalar.yaml"
    path.write_text("just a string\n", encoding="utf-8")
    with pytest.raises(diagnostics.MalformedFileError) as exc:
        prefs.load(path)
    assert exc.value.kind == "malformed_yaml"


# --- AN-44 version / migration ---------------------------------------------


def test_new_file_saved_by_skill_carries_version_1(tmp_path: Path) -> None:
    """TC-AN-44-01: every newly-saved prefs file has version:1 at the top."""
    from _shared import prefs

    path = tmp_path / "new.yaml"
    prefs.save(path, prefs.DEFAULTS)
    text = path.read_text(encoding="utf-8")
    assert "version: 1" in text


def test_load_of_versionless_file_rewrites_with_version_1(tmp_path: Path) -> None:
    """TC-AN-44-02: hand-authored file without a `version:` key → treated as
    v1 and rewritten with `version: 1` added. The result dict carries v1.
    """
    import yaml

    from _shared import prefs

    path = tmp_path / "legacy.yaml"
    path.write_text("headline_count: 7\nbootstrap_n_iter: 2000\n", encoding="utf-8")
    result, _ = prefs.load(path)
    assert result["version"] == 1
    # File on disk was rewritten with version key.
    reread = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert reread["version"] == 1
    assert reread["headline_count"] == 7
    assert reread["bootstrap_n_iter"] == 2000


def test_load_of_future_version_raises_migration_error(tmp_path: Path) -> None:
    """Forward-only migration: a file written by a newer skill cannot be
    downgraded. Exit with a named error rather than silently corrupting.
    """
    from _shared import prefs

    path = tmp_path / "v2.yaml"
    path.write_text("version: 99\nheadline_count: 5\n", encoding="utf-8")
    with pytest.raises(prefs.PreferencesMigrationError) as exc:
        prefs.load(path)
    assert "99" in str(exc.value)


def test_migrate_with_missing_step_raises(tmp_path: Path) -> None:
    """Per the spec contract: a gap in the MIGRATIONS chain raises; never
    silently skips a version.
    """
    from _shared import prefs

    # Monkey-patch CURRENT_VERSION to 3 without registering 1→2 or 2→3.
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(prefs, "CURRENT_VERSION", 3)
        mp.setattr(prefs, "MIGRATIONS", {})
        with pytest.raises(prefs.PreferencesMigrationError) as exc:
            prefs.migrate({"version": 1, "headline_count": 5})
        assert "v1" in str(exc.value) or "1" in str(exc.value)


def test_migrate_raises_on_non_integer_version() -> None:
    """YAML `version: yes` parses to bool True; `version: foo` parses to str.
    Both must be rejected — silent "treat as v1" is a wrong-result defect.
    """
    from _shared import prefs

    with pytest.raises(prefs.PreferencesMigrationError):
        prefs.migrate({"version": "foo", "headline_count": 5})

    with pytest.raises(prefs.PreferencesMigrationError):
        prefs.migrate({"version": True, "headline_count": 5})


def test_load_with_registered_migration_rewrites_file_on_disk(
    tmp_path: Path,
) -> None:
    """TC-AN-44-03 end-to-end: a v1 file loaded while CURRENT_VERSION==2 with
    a registered v1→v2 migration must be rewritten to disk with version:2.
    """
    import yaml

    from _shared import constants, prefs

    path = tmp_path / "legacy_v1.yaml"
    path.write_text("version: 1\nheadline_count: 5\n", encoding="utf-8")

    def v1_to_v2(d: dict) -> dict:
        return {**d, "headline_count": d.get("headline_count", 5)}

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(constants, "CURRENT_VERSION", 2)
        mp.setattr(prefs, "CURRENT_VERSION", 2)
        mp.setattr(prefs, "MIGRATIONS", {2: v1_to_v2})
        # Also patch SCHEMA's version constraint reference, which reads
        # constants.CURRENT_VERSION at call time via the closure.
        result, _ = prefs.load(path)

    assert result["version"] == 2
    reread = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert reread["version"] == 2
    assert reread["headline_count"] == 5


def test_schema_default_field_mirrors_defaults_dict() -> None:
    """The SCHEMA[key]["default"] contract: downstream chunks (P5-C04
    orchestration, P2-C04 diagnostic formatter) read defaults from SCHEMA.
    Divergence between SCHEMA[key]["default"] and DEFAULTS[key] is a
    silent cross-file bug.
    """
    from _shared import prefs

    for key, spec in prefs.SCHEMA.items():
        assert "default" in spec, f"SCHEMA[{key!r}] missing 'default' field"
        assert spec["default"] == prefs.DEFAULTS[key], (
            f"SCHEMA[{key!r}]['default'] diverges from DEFAULTS[{key!r}]"
        )


def test_migrate_applies_registered_chain(tmp_path: Path) -> None:
    """TC-AN-44-03: a registered v1→v2 migration upgrades the dict and
    leaves version:2.
    """
    from _shared import prefs

    def v1_to_v2(d: dict) -> dict:
        return {**d, "new_v2_field": "hello"}

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(prefs, "CURRENT_VERSION", 2)
        mp.setattr(prefs, "MIGRATIONS", {2: v1_to_v2})
        result = prefs.migrate({"version": 1, "headline_count": 5})
        assert result["version"] == 2
        assert result["new_v2_field"] == "hello"
        assert result["headline_count"] == 5


# --- merge_with_defaults: validation ---------------------------------------


def test_merge_raises_on_headline_count_out_of_range() -> None:
    from _shared import prefs

    with pytest.raises(prefs.PreferencesValidationError) as exc:
        prefs.merge_with_defaults({"version": 1, "headline_count": 11})
    msg = str(exc.value)
    assert "headline_count" in msg
    assert "11" in msg


def test_merge_raises_on_outlier_methods_not_in_allowed_set() -> None:
    from _shared import prefs

    with pytest.raises(prefs.PreferencesValidationError) as exc:
        prefs.merge_with_defaults({"version": 1, "outlier_methods": ["iqr", "unknown"]})
    msg = str(exc.value)
    assert "outlier_methods" in msg
    assert "unknown" in msg


def test_merge_raises_on_bootstrap_confidence_below_floor() -> None:
    from _shared import prefs

    with pytest.raises(prefs.PreferencesValidationError):
        prefs.merge_with_defaults({"version": 1, "bootstrap_confidence": 0.3})


def test_merge_raises_on_trend_alpha_out_of_range() -> None:
    from _shared import prefs

    with pytest.raises(prefs.PreferencesValidationError):
        prefs.merge_with_defaults({"version": 1, "trend_alpha": 0.6})


def test_merge_raises_on_bootstrap_n_iter_out_of_range() -> None:
    from _shared import prefs

    with pytest.raises(prefs.PreferencesValidationError):
        prefs.merge_with_defaults({"version": 1, "bootstrap_n_iter": 100})


def test_merge_unknown_key_warns_does_not_raise() -> None:
    """Per ADR-104: unknown keys are recorded in warnings for
    provenance.warnings but do NOT block the run.
    """
    from _shared import prefs

    merged, warnings = prefs.merge_with_defaults({"version": 1, "nonsense_flag": True})
    assert merged["version"] == 1
    assert any("nonsense_flag" in w for w in warnings)


def test_merge_deep_data_quality_checks_partial_override() -> None:
    """One toggle set false; omitted toggles retain their true defaults."""
    from _shared import prefs

    merged, warnings = prefs.merge_with_defaults(
        {
            "version": 1,
            "data_quality_checks": {"run_missingness": False},
        }
    )
    dq = merged["data_quality_checks"]
    assert dq["run_missingness"] is False
    assert dq["run_type_drift"] is True
    assert dq["run_rounding"] is True
    assert warnings == []


# --- TC-AN-34-02 [PROPERTY] -------------------------------------------------


@given(
    headline_count=st.integers(min_value=3, max_value=10),
    trend_alpha=st.floats(
        min_value=0.01, max_value=0.49, allow_nan=False, allow_infinity=False
    ),
    bootstrap_n_iter=st.integers(min_value=200, max_value=10000),
    bootstrap_confidence=st.floats(
        min_value=0.51, max_value=0.998, allow_nan=False, allow_infinity=False
    ),
    outlier_methods=st.lists(
        st.sampled_from(["iqr", "mad", "iforest", "lof"]),
        min_size=1,
        max_size=4,
        unique=True,
    ),
    fuzzy_duplicate_threshold=st.floats(
        min_value=0.5, max_value=1.0, allow_nan=False, allow_infinity=False
    ),
)
@settings(max_examples=50, deadline=None)
def test_save_load_roundtrip_property(
    tmp_path_factory: pytest.TempPathFactory,
    headline_count: int,
    trend_alpha: float,
    bootstrap_n_iter: int,
    bootstrap_confidence: float,
    outlier_methods: list[str],
    fuzzy_duplicate_threshold: float,
) -> None:
    """For any valid override set from the schema, save→load→merge recovers
    the overrides exactly. Locks in the round-trip contract against any
    refactor that changes YAML serialisation or validation order.
    """
    from _shared import prefs

    tmp = tmp_path_factory.mktemp("prefs_property")
    path = tmp / "prefs.yaml"
    overrides = {
        "version": 1,
        "headline_count": headline_count,
        "trend_alpha": trend_alpha,
        "bootstrap_n_iter": bootstrap_n_iter,
        "bootstrap_confidence": bootstrap_confidence,
        "outlier_methods": outlier_methods,
        "fuzzy_duplicate_threshold": fuzzy_duplicate_threshold,
    }
    merged_before, _ = prefs.merge_with_defaults(overrides)
    prefs.save(path, merged_before)

    merged_after, warnings = prefs.load(path)
    assert merged_after["headline_count"] == headline_count
    assert merged_after["trend_alpha"] == pytest.approx(trend_alpha)
    assert merged_after["bootstrap_n_iter"] == bootstrap_n_iter
    assert merged_after["bootstrap_confidence"] == pytest.approx(bootstrap_confidence)
    assert merged_after["outlier_methods"] == outlier_methods
    assert merged_after["fuzzy_duplicate_threshold"] == pytest.approx(
        fuzzy_duplicate_threshold
    )
    assert warnings == []
