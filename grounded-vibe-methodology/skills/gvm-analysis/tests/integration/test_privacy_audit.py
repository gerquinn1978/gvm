"""End-to-end privacy audit (NFR-1, P15-C02).

System-level test that runs ``analyse.main`` followed by
``render_report.main`` against a sentinel fixture and asserts no sentinel
string survives in any artefact under ``--output-dir``. Parametrised over
the four engine modes and over with-/without-anonymisation, so the
matrix is 4 × 2 = 8 cases.

Component-level coverage already exists in ``test_bundle.py``,
``test_render_report.py``, etc.; this test adds the integration-layer
backstop — a leak that is invisible to component tests but appears in
the A→B composition is what this test exists to catch.

The audit is byte-level, not text-level: encoders may escape, percent-encode,
or HTML-entity-encode their inputs, but a substring of bytes survives
every encoding round-trip the pipeline performs.

Test cases: TC-AN-4-01, TC-AN-26-03, TC-AN-27-02, TC-AN-29-05, TC-AN-38-03,
TC-NFR-1-01, TC-AN-40-01 (the AN-40 flag round-trip exercised by
``test_anonymised_run_sets_an40_flag``).
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pandas as pd
import pytest

# 200 deterministic, unique, ASCII-only sentinels. Each is long enough that
# random byte collision with engine/renderer output (e.g. timestamps,
# UUIDs, numeric formatting) is negligible. Deterministic UUID derivation
# makes leaks reproducible across CI runs.
SENTINELS: tuple[str, ...] = tuple(
    f"SENTINEL_{i:04d}_{uuid.UUID(int=i).hex[:12]}" for i in range(200)
)

# Sentinel-matrix fixture sizing. Distinct naming family from the smoke
# tests' _SMOKE_FIXTURE_ROWS (test_wcag_audit, test_product_startup) and
# the perf budget's _NFR2_FIXTURE_ROWS (test_perf_budget) — this fixture
# is a sentinel matrix for byte-leak scanning, not a structural smoke
# fixture, and intentionally uses its own naming.
_NUM_COLUMNS = 10
_NUM_ROWS = 20


def _build_sentinel_fixture(out_path: Path) -> list[str]:
    """Write a CSV at ``out_path`` whose every cell carries a unique
    sentinel string. Returns the column names so the with-anonymisation
    arm can pass them to ``--cols``."""
    columns = [f"col_{i}" for i in range(_NUM_COLUMNS)]
    data: dict[str, list[str]] = {col: [] for col in columns}
    sentinel_idx = 0
    for _row in range(_NUM_ROWS):
        for col in columns:
            data[col].append(SENTINELS[sentinel_idx])
            sentinel_idx += 1
    df = pd.DataFrame(data)
    df.to_csv(out_path, index=False)
    return columns


def _scan_for_sentinels(
    out_dir: Path, sentinels: tuple[str, ...]
) -> list[tuple[Path, str]]:
    """Walk ``out_dir`` recursively; for every file, search the bytes for
    every sentinel substring. Return the ``(file, sentinel)`` pairs that
    leaked. Empty list = clean."""
    leaks: list[tuple[Path, str]] = []
    encoded = [(s, s.encode("utf-8")) for s in sentinels]
    for path in out_dir.rglob("*"):
        if not path.is_file():
            continue
        data = path.read_bytes()
        for sentinel, sentinel_bytes in encoded:
            if sentinel_bytes in data:
                leaks.append((path, sentinel))
    return leaks


@pytest.mark.parametrize("mode", ["explore", "decompose", "validate", "run-everything"])
@pytest.mark.parametrize("anonymise_first", [False, True])
def test_no_sentinel_in_any_output_artefact(
    tmp_path: Path, mode: str, anonymise_first: bool
) -> None:
    """The cartesian product of (mode × anonymisation) — 8 cases. None may
    produce an artefact containing any sentinel substring. The without-
    anonymisation arm proves the engine's "raw rows never leave the file"
    contract; the with-anonymisation arm proves anonymise.py's
    tokenisation also clears the path.

    NOTE — at tracer-bullet engine scope (per P15-C03a/b/C04 handovers),
    ``analyse.main`` does not echo cell values into ``findings.json``;
    per-column stats, outlier rows, time-series points, etc. are not
    yet wired. The without-anonymisation arm therefore passes by
    structural absence (no cell content is written) rather than by an
    enforced privacy invariant. The arm becomes load-bearing as
    analytical content lands in later chunks; until then, the
    ``produced_files`` and ``anonymised_input != raw`` guards above
    keep this test from being fully vacuous (they verify the engine
    actually ran and the anonymisation step actually transformed the
    fixture)."""
    import analyse
    import render_report

    raw_input = tmp_path / "raw.csv"
    columns = _build_sentinel_fixture(raw_input)

    if anonymise_first:
        import anonymise

        anonymised_input = tmp_path / "anonymised.csv"
        mapping_out = tmp_path / "mapping.csv"
        rc_anon = anonymise.main(
            [
                "--input",
                str(raw_input),
                "--output",
                str(anonymised_input),
                "--mapping-out",
                str(mapping_out),
                "--cols",
                ",".join(columns),
                "--i-accept-the-risk",
            ]
        )
        assert rc_anon == 0, "anonymise.main failed before engine ran"
        # Defensive: prove anonymisation actually transformed the data.
        # If --cols silently matches no columns, anonymise.main still
        # exits 0 but the output equals the input — the privacy assertion
        # below would then be vacuously true. Asserting bytes differ
        # guards against that silent-no-op regression.
        assert anonymised_input.read_bytes() != raw_input.read_bytes(), (
            "anonymise.main exited 0 but output equals input — the "
            "anonymisation step did not transform the fixture; "
            "with-anonymisation arm is a no-op."
        )
        engine_input = anonymised_input
    else:
        engine_input = raw_input

    out_dir = tmp_path / "out"
    rc_engine = analyse.main(
        [
            "--input",
            str(engine_input),
            "--output-dir",
            str(out_dir),
            "--mode",
            mode,
            "--seed",
            "42",
        ]
    )
    assert rc_engine == 0, "analyse.main failed"

    rc_render = render_report.main(
        ["--findings", str(out_dir / "findings.json"), "--out", str(out_dir)]
    )
    assert rc_render == 0, "render_report.main failed"

    # The output dir must be non-empty — an empty walk would silently pass
    # the leak check, which is a test-setup defect, not a privacy win.
    produced_files = [p for p in out_dir.rglob("*") if p.is_file()]
    assert produced_files, "render produced no artefacts — test setup is wrong"

    leaks = _scan_for_sentinels(out_dir, SENTINELS)
    assert not leaks, (
        f"NFR-1 violation: sentinel(s) leaked into output artefacts. "
        f"First leak: {leaks[0][0]} contains {leaks[0][1]!r}. "
        f"Total leaks: {len(leaks)}."
    )


def test_anonymised_run_sets_an40_flag(tmp_path: Path) -> None:
    """When the engine consumes an anonymised input (via anonymise.py), the
    AN-40 detector should flag the input — every column is fully tokenised,
    so the threshold is trivially exceeded. Validates the P15-C01 wiring
    under a realistic round-trip rather than a hand-crafted token fixture."""
    import analyse
    import anonymise

    raw_input = tmp_path / "raw.csv"
    columns = _build_sentinel_fixture(raw_input)

    anonymised_input = tmp_path / "anonymised.csv"
    rc_anon = anonymise.main(
        [
            "--input",
            str(raw_input),
            "--output",
            str(anonymised_input),
            "--mapping-out",
            str(tmp_path / "mapping.csv"),
            "--cols",
            ",".join(columns),
            "--i-accept-the-risk",
        ]
    )
    assert rc_anon == 0

    out_dir = tmp_path / "out"
    rc_engine = analyse.main(
        [
            "--input",
            str(anonymised_input),
            "--output-dir",
            str(out_dir),
            "--mode",
            "explore",
            "--seed",
            "42",
        ]
    )
    assert rc_engine == 0

    findings_data = json.loads((out_dir / "findings.json").read_text())
    provenance = findings_data["provenance"]
    assert provenance["anonymised_input_detected"] is True
    # Every column was tokenised — every column should flag.
    assert sorted(provenance["anonymised_columns"]) == sorted(columns)
