"""Tests for `scripts/analyse.py` — minimal entrypoint (P1-C03).

Tracer-bullet scope: argparse contract, ADR-202 sub-seed pre-derivation,
provenance shape, three-question comprehension stub (post-R4 HIGH-T71),
idempotency, boundary defence on missing input.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# --- _parse_args -----------------------------------------------------------


def test_parse_args_requires_input_and_output_dir() -> None:
    """argparse raises SystemExit when mandatory flags are missing."""
    import analyse

    with pytest.raises(SystemExit):
        analyse._parse_args([])
    with pytest.raises(SystemExit):
        analyse._parse_args(["--input", "/tmp/x"])
    with pytest.raises(SystemExit):
        analyse._parse_args(["--output-dir", "/tmp/x"])


def test_parse_args_defaults(tmp_path: Path) -> None:
    """Defaults match the CLI contract in the prompt table."""
    import analyse

    fixture = tmp_path / "in.csv"
    fixture.write_text("a,b\n1,2\n")
    out = tmp_path / "out"

    args = analyse._parse_args(["--input", str(fixture), "--output-dir", str(out)])
    assert args.mode == "explore"
    assert args.seed is None
    assert args.forecast_only is False
    assert args.target_column is None
    assert args.baseline_file is None
    # D-2 fix — every declared flag has its default pinned.
    assert args.prefs is None
    assert args.sample_n is None
    assert args.in_file is None
    assert args.time_column is None


def test_parse_args_rejects_invalid_mode(tmp_path: Path) -> None:
    """Unknown --mode values are rejected by argparse before main runs."""
    import analyse

    with pytest.raises(SystemExit):
        analyse._parse_args(
            [
                "--input",
                str(tmp_path / "x"),
                "--output-dir",
                str(tmp_path / "o"),
                "--mode",
                "bogus",
            ]
        )


# --- _derive_sub_seeds (ADR-202) -------------------------------------------

ADR_202_KEYS: tuple[str, ...] = (
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


def test_derive_sub_seeds_returns_all_adr_202_keys() -> None:
    """All nine ADR-202 sub-seed keys present, in the canonical order, with
    outliers_lof == None and per_column the correct length."""
    import numpy as np

    import analyse

    rng = np.random.default_rng(42)
    sub_seeds = analyse._derive_sub_seeds(rng, num_columns=3)

    assert tuple(sub_seeds.keys()) == ADR_202_KEYS
    assert sub_seeds["outliers_lof"] is None
    assert isinstance(sub_seeds["per_column"], list)
    assert len(sub_seeds["per_column"]) == 3


def test_derive_sub_seeds_is_reproducible() -> None:
    """Same seed → identical sub-seed dict; different seed → different dict."""
    import numpy as np

    import analyse

    a = analyse._derive_sub_seeds(np.random.default_rng(42), num_columns=2)
    b = analyse._derive_sub_seeds(np.random.default_rng(42), num_columns=2)
    c = analyse._derive_sub_seeds(np.random.default_rng(43), num_columns=2)

    assert a == b
    assert a != c


def test_derive_sub_seeds_values_are_json_serialisable() -> None:
    """Every int is a Python int, not numpy.int64 — so json.dumps never
    raises TypeError. This guards against silently-broken write_atomic."""
    import numpy as np

    import analyse

    sub_seeds = analyse._derive_sub_seeds(np.random.default_rng(42), num_columns=4)

    # Round-trip through json — raises TypeError on numpy ints.
    json.dumps(sub_seeds)

    # Also assert types directly for a cleaner failure message.
    for key in (
        "outliers_iforest",
        "drivers_rf",
        "drivers_rf_perm",
        "drivers_partial_corr",
        "forecast_linear_bootstrap",
        "forecast_arima_init",
        "forecast_exp_smoothing_init",
    ):
        assert type(sub_seeds[key]) is int, (
            f"{key} must be a plain Python int, got {type(sub_seeds[key]).__name__}"
        )
    assert all(type(s) is int for s in sub_seeds["per_column"])


def test_derive_sub_seeds_zero_columns() -> None:
    """The production call at tracer-bullet scope passes num_columns=0.
    per_column MUST be an empty list; all other keys MUST still be
    present with well-typed values."""
    import numpy as np

    import analyse

    sub_seeds = analyse._derive_sub_seeds(np.random.default_rng(42), num_columns=0)

    assert tuple(sub_seeds.keys()) == ADR_202_KEYS
    assert sub_seeds["per_column"] == []
    assert sub_seeds["outliers_lof"] is None
    for key in (
        "outliers_iforest",
        "drivers_rf",
        "drivers_rf_perm",
        "drivers_partial_corr",
        "forecast_linear_bootstrap",
        "forecast_arima_init",
        "forecast_exp_smoothing_init",
    ):
        assert type(sub_seeds[key]) is int


# --- _build_provenance -----------------------------------------------------


def test_build_provenance_has_every_required_field(tmp_path: Path) -> None:
    """Provenance skeleton includes every key the schema will eventually
    require. Missing fields at P1-C03 default to None / [] / {}."""
    import analyse

    fixture = tmp_path / "in.csv"
    fixture.write_text("a\n1\n")
    prov = analyse._build_provenance(
        input_paths=[fixture],
        mode="explore",
        seed=42,
        sub_seeds={"outliers_iforest": 1, "outliers_lof": None, "per_column": []},
    )

    for key in (
        "input_files",
        "mode",
        "target_column",
        "baseline_file",
        "seed",
        "sub_seeds",
        "timestamp",
        "preferences",
        "preferences_hash",
        "lib_versions",
        "anonymised_input_detected",
        "anonymised_columns",
        "formula_columns",
        "sample_applied",
        "domain",
        "warnings",
        "time_column",
        "bootstrap_n_iter_used",
    ):
        assert key in prov, f"provenance missing required key: {key}"

    assert prov["seed"] == 42
    assert prov["mode"] == "explore"
    # input_files is a list of dicts per ADR-201. sha256/mtime/rows/cols are
    # None at tracer-bullet scope; P2-C03 populates them.
    assert isinstance(prov["input_files"], list)
    assert prov["input_files"]
    entry = prov["input_files"][0]
    assert entry["path"] == str(fixture)
    for key in ("sha256", "mtime", "rows", "cols"):
        assert key in entry, f"input_files entry missing required key: {key}"


# --- main() ---------------------------------------------------------------


def _run_main(tmp_path: Path, *extra: str) -> tuple[int, Path]:
    """Helper: run analyse.main and return (exit_code, findings_path)."""
    import analyse

    fixture = tmp_path / "in.csv"
    fixture.write_text("a,b\n1,2\n")
    out = tmp_path / "out"

    rc = analyse.main(["--input", str(fixture), "--output-dir", str(out), *extra])
    return rc, out / "findings.json"


def test_main_writes_validated_findings(tmp_path: Path) -> None:
    """After main(), findings.json exists and round-trips cleanly."""
    from _shared import findings

    rc, findings_path = _run_main(tmp_path, "--seed", "42")

    assert rc == 0
    assert findings_path.exists()
    data = findings.read_findings(findings_path)
    assert data["schema_version"] == findings.CURRENT_SCHEMA_VERSION


def test_main_writes_three_question_stub(tmp_path: Path) -> None:
    """Bridge tracer-bullet (post-R4 HIGH-T71): comprehension_questions
    contains exactly three dicts with the ADR-109 shape."""
    from _shared import findings

    _, findings_path = _run_main(tmp_path, "--seed", "42")
    data = findings.read_findings(findings_path)

    questions = data["comprehension_questions"]
    assert len(questions) == 3
    for q in questions:
        assert set(q.keys()) == {
            "question",
            "answer",
            "supporting_finding_id",
        }
        assert isinstance(q["question"], str)
        assert isinstance(q["answer"], str)
        assert isinstance(q["supporting_finding_id"], str)


def test_main_records_mode_and_seed_in_provenance(tmp_path: Path) -> None:
    """Provenance echoes the CLI args so downstream chunks can trust the
    record."""
    from _shared import findings

    _, findings_path = _run_main(tmp_path, "--seed", "99", "--mode", "decompose")
    data = findings.read_findings(findings_path)

    assert data["provenance"]["seed"] == 99
    assert data["provenance"]["mode"] == "decompose"


def test_main_missing_input_returns_nonzero_with_diagnostic(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A non-existent --input path produces a non-zero exit and a stderr
    diagnostic (McConnell: boundary defence, fail loud)."""
    import analyse

    missing = tmp_path / "does-not-exist.csv"
    out = tmp_path / "out"

    rc = analyse.main(
        ["--input", str(missing), "--output-dir", str(out), "--seed", "42"]
    )
    # Pin the exit code explicitly so a later refactor that routes the
    # error through the generic `except Exception` handler (exit 1) would
    # fail this test — P5-C02's bash wrapper cares which branch was hit.
    assert rc == 2

    captured = capsys.readouterr()
    assert "does-not-exist.csv" in captured.err
    assert not (out / "findings.json").exists()


def test_main_returns_zero_on_success(tmp_path: Path) -> None:
    """Exit-code contract lock: successful runs return 0, not ``None`` and
    not any truthy value. Named test per the TDD list (item 10) so the
    contract is unambiguous even if other tests drop their rc assertions."""
    rc, _ = _run_main(tmp_path, "--seed", "42")
    assert rc == 0
    assert isinstance(rc, int)


def test_main_defaults_seed_to_sha256_derived_with_warning(tmp_path: Path) -> None:
    """--seed omitted → seed deterministically derived from input
    SHA-256 (P16-C02 retired the tracer-bullet 0 default). The same
    input file always produces the same default seed; a different input
    produces a different one. A warning is still recorded so users
    inspecting findings.json see the engine fell back to the default."""
    from _shared import findings

    rc, findings_path = _run_main(tmp_path)  # no --seed
    assert rc == 0

    data = findings.read_findings(findings_path)
    seed = data["provenance"]["seed"]
    # Deterministic 31-bit derivation; cannot equal the historical
    # placeholder 0 except by 1-in-2**31 collision (an SHA-256 prefix
    # of all zeros, vanishingly unlikely for any real input).
    assert isinstance(seed, int)
    assert 0 <= seed < 2**31

    warnings = data["provenance"]["warnings"]
    assert any("seed" in w.lower() for w in warnings), (
        f"expected a seed-default warning in provenance.warnings, got {warnings}"
    )


def test_main_forecast_only_exits_nonzero_with_stub_diagnostic(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--forecast-only is a P4-C04 deliverable; at P1-C03 it must fail loudly
    so a caller who selects it accidentally cannot get silent success."""
    import analyse

    fixture = tmp_path / "in.csv"
    fixture.write_text("a\n1\n")
    out = tmp_path / "out"

    rc = analyse.main(
        [
            "--input",
            str(fixture),
            "--output-dir",
            str(out),
            "--seed",
            "42",
            "--forecast-only",
        ]
    )
    # Pin exit code 2 — symmetric with the missing-input test. Regression
    # that routed --forecast-only through the generic `except Exception`
    # handler (exit 1) would be caught here.
    assert rc == 2
    captured = capsys.readouterr()
    assert "forecast" in captured.err.lower()
    assert not (out / "findings.json").exists()


def test_main_unexpected_error_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exit code 1 is the third arm of the main() contract — an unexpected
    internal error (not a user-input problem) produces exit 1 plus a
    traceback on stderr. Forces a RuntimeError by monkeypatching the RNG
    constructor."""
    import analyse
    import numpy as np

    def _boom(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("simulated internal failure")

    monkeypatch.setattr(np.random, "default_rng", _boom)

    fixture = tmp_path / "in.csv"
    fixture.write_text("a,b\n1,2\n")
    out = tmp_path / "out"

    rc = analyse.main(
        ["--input", str(fixture), "--output-dir", str(out), "--seed", "42"]
    )
    assert rc == 1
    captured = capsys.readouterr()
    assert "RuntimeError" in captured.err
    assert "simulated internal failure" in captured.err
    assert not (out / "findings.json").exists()


def test_main_is_idempotent(tmp_path: Path) -> None:
    """Two runs with the same seed produce byte-identical findings.json.
    Requires sort_keys=True inside write_atomic (ADR-209) and deterministic
    provenance (timestamp excepted — tested separately below)."""
    import analyse
    from _shared import findings

    fixture = tmp_path / "in.csv"
    fixture.write_text("a,b\n1,2\n")
    out = tmp_path / "out"

    def canonical_payload(path: Path) -> dict[str, object]:
        data = findings.read_findings(path)
        # timestamp varies by wall-clock; exclude it from the comparison.
        data["provenance"].pop("timestamp", None)
        return data

    assert (
        analyse.main(
            ["--input", str(fixture), "--output-dir", str(out), "--seed", "42"]
        )
        == 0
    )
    first = canonical_payload(out / "findings.json")

    assert (
        analyse.main(
            ["--input", str(fixture), "--output-dir", str(out), "--seed", "42"]
        )
        == 0
    )
    second = canonical_payload(out / "findings.json")

    assert first == second


# --- AN-40 wiring (P15-C01) ------------------------------------------------


def test_main_anonymised_input_flips_flag(tmp_path: Path) -> None:
    """TC-AN-40-01: an input where ≥ one column matches the
    ``TOK_<column>_<NNN>`` pattern flips ``provenance.anonymised_input_detected``
    to True and lists the matching column(s) in
    ``provenance.anonymised_columns``."""
    import analyse
    from _shared import findings

    fixture = tmp_path / "in.csv"
    fixture.write_text(
        "dept,value\n"
        "TOK_dept_001,1\n"
        "TOK_dept_002,2\n"
        "TOK_dept_001,3\n"
        "TOK_dept_003,4\n"
        "TOK_dept_002,5\n"
    )
    out = tmp_path / "out"

    rc = analyse.main(
        ["--input", str(fixture), "--output-dir", str(out), "--seed", "42"]
    )
    assert rc == 0

    data = findings.read_findings(out / "findings.json")
    assert data["provenance"]["anonymised_input_detected"] is True
    assert data["provenance"]["anonymised_columns"] == ["dept"]


def test_main_non_anonymised_input_keeps_flag_false(tmp_path: Path) -> None:
    """TC-AN-40-02: ordinary categorical / numeric input → flag stays False
    and ``anonymised_columns`` stays empty."""
    import analyse
    from _shared import findings

    fixture = tmp_path / "in.csv"
    fixture.write_text("name,age\nAlice,30\nBob,40\nCarol,50\n")
    out = tmp_path / "out"

    rc = analyse.main(
        ["--input", str(fixture), "--output-dir", str(out), "--seed", "42"]
    )
    assert rc == 0

    data = findings.read_findings(out / "findings.json")
    assert data["provenance"]["anonymised_input_detected"] is False
    assert data["provenance"]["anonymised_columns"] == []


def test_main_partial_anonymised_below_threshold_not_flagged(
    tmp_path: Path,
) -> None:
    """Smoke test for the ADR-406 threshold: 7/10 (= 0.7) < 0.8 must not
    flip the flag. Exhaustive boundary coverage lives in
    ``test_token_detect.py``; this is the engine-level regression guard."""
    import analyse
    from _shared import findings

    rows = ["TOK_x_001"] * 7 + ["raw_a", "raw_b", "raw_c"]
    fixture = tmp_path / "in.csv"
    fixture.write_text("x\n" + "\n".join(rows) + "\n")
    out = tmp_path / "out"

    rc = analyse.main(
        ["--input", str(fixture), "--output-dir", str(out), "--seed", "42"]
    )
    assert rc == 0

    data = findings.read_findings(out / "findings.json")
    assert data["provenance"]["anonymised_input_detected"] is False
    assert data["provenance"]["anonymised_columns"] == []


def test_main_appends_token_detect_warnings_to_provenance(tmp_path: Path) -> None:
    """ADR-406 step 1: an all-null column emits the canonical warning text
    into ``provenance.warnings``. Pre-existing engine warnings (e.g. the
    seed-default warning) coexist with detection warnings — order is
    'engine warnings first, detection warnings appended'."""
    import analyse
    from _shared import findings

    # Two columns: one with data, one entirely null. Build via pandas so
    # column 'b' is unambiguously NaN (raw CSV with trailing commas is
    # dialect-sensitive — empty cells may resolve to "" rather than NaN
    # on some platforms, which would not exercise the n_non_null == 0
    # branch).
    import pandas as pd

    fixture = tmp_path / "in.csv"
    pd.DataFrame({"a": [1, 2, 3], "b": [pd.NA, pd.NA, pd.NA]}).to_csv(
        fixture, index=False
    )
    out = tmp_path / "out"

    # No --seed → engine emits the seed-default warning. Detection should
    # then append its all-null warning for column 'b'.
    rc = analyse.main(["--input", str(fixture), "--output-dir", str(out)])
    assert rc == 0

    data = findings.read_findings(out / "findings.json")
    warnings_field = data["provenance"]["warnings"]
    assert any("derived deterministically" in w for w in warnings_field)
    assert any(
        "column 'b' is entirely null — token-pattern detection skipped" in w
        for w in warnings_field
    )


def test_build_provenance_threads_an40_keyword_args(tmp_path: Path) -> None:
    """``_build_provenance`` accepts the AN-40 fields as keyword-only args
    and threads them into the dict."""
    import analyse

    fixture = tmp_path / "in.csv"
    fixture.write_text("dept\nTOK_dept_001\n")

    prov = analyse._build_provenance(
        input_paths=[fixture],
        mode="explore",
        seed=42,
        sub_seeds={"outliers_iforest": 1, "outliers_lof": None, "per_column": []},
        anonymised_input_detected=True,
        anonymised_columns=["dept"],
    )

    assert prov["anonymised_input_detected"] is True
    assert prov["anonymised_columns"] == ["dept"]


def test_main_load_error_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """An ``io.load`` failure on a path that passed the existence check
    routes through the generic-fallback exit-1 handler. Pinning the exit
    code so a future refactor that accidentally routes it through the
    exit-2 branch (reserved for invalid invocation, not for unreadable
    inputs) is caught."""
    import analyse
    from _shared.diagnostics import MalformedFileError

    def _boom(*_args: object, **_kwargs: object) -> object:
        raise MalformedFileError(
            path=tmp_path / "in.csv", row=None, col=None, kind="parser_error"
        )

    monkeypatch.setattr(analyse.io_module, "load", _boom)

    fixture = tmp_path / "in.csv"
    fixture.write_text("a,b\n1,2\n")
    out = tmp_path / "out"

    rc = analyse.main(
        ["--input", str(fixture), "--output-dir", str(out), "--seed", "42"]
    )
    assert rc == 1
    captured = capsys.readouterr()
    assert "MalformedFileError" in captured.err
    assert not (out / "findings.json").exists()


def test_main_token_detect_error_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ``token_detect.detect`` failure routes through the generic-
    fallback exit-1 handler. Pins the exit code so a regression that
    accidentally returns 0 from a broken ``detect`` (or routes the
    error through exit 2) is caught. Complements
    ``test_main_load_error_exits_1`` — the load-error monkeypatch
    only covers the io seam; this covers the post-load token_detect
    seam."""
    import analyse

    def _boom(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("synthetic token_detect failure")

    monkeypatch.setattr(analyse.token_detect, "detect", _boom)

    fixture = tmp_path / "in.csv"
    fixture.write_text("a,b\n1,2\n3,4\n")
    out = tmp_path / "out"

    rc = analyse.main(
        ["--input", str(fixture), "--output-dir", str(out), "--seed", "42"]
    )
    assert rc == 1
    captured = capsys.readouterr()
    assert "RuntimeError" in captured.err
    assert "synthetic token_detect failure" in captured.err
    assert not (out / "findings.json").exists()


def test_build_provenance_an40_defaults_preserve_tracer_bullet_shape(
    tmp_path: Path,
) -> None:
    """Calling ``_build_provenance`` without the new args preserves the
    existing False/[] tracer-bullet shape — non-breaking signature."""
    import analyse

    fixture = tmp_path / "in.csv"
    fixture.write_text("a\n1\n")

    prov = analyse._build_provenance(
        input_paths=[fixture],
        mode="explore",
        seed=42,
        sub_seeds={"outliers_iforest": 1, "outliers_lof": None, "per_column": []},
    )

    assert prov["anonymised_input_detected"] is False
    assert prov["anonymised_columns"] == []
