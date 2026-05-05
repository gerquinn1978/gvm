"""Tests for `_shared/bundle.py` — zip + manifest (P6-C08 / ADR-309 / AN-45)."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


TIMESTAMP = "2026-04-20T00:00:00Z"


def _populate_output_dir(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.html").write_text("<html>hub</html>", encoding="utf-8")
    (out / "drillthrough-dt-col-revenue.html").write_text(
        "<html>dt1</html>", encoding="utf-8"
    )
    (out / "drillthrough-dt-outlier-42.html").write_text(
        "<html>dt2</html>", encoding="utf-8"
    )
    (out / "methodology_appendix.html").write_text(
        "<html>methods</html>", encoding="utf-8"
    )
    (out / "findings.json").write_text(
        json.dumps({"provenance": {"timestamp": TIMESTAMP}}),
        encoding="utf-8",
    )
    charts_dir = out / "charts"
    charts_dir.mkdir()
    (charts_dir / "hist-revenue.svg").write_text("<svg/>", encoding="utf-8")


def _write_findings(path: Path) -> None:
    path.write_text(
        json.dumps({"provenance": {"timestamp": TIMESTAMP}}),
        encoding="utf-8",
    )


def test_manifest_schema_version_is_1(tmp_path: Path) -> None:
    from _shared import bundle

    _populate_output_dir(tmp_path)
    m = bundle.build_manifest(tmp_path, timestamp=TIMESTAMP)
    assert m["schema_version"] == 1


def test_manifest_generated_at_from_findings_timestamp(tmp_path: Path) -> None:
    """MEDIUM-T34: generated_at comes from provenance.timestamp, not datetime.now()."""
    from _shared import bundle

    _populate_output_dir(tmp_path)
    m = bundle.build_manifest(tmp_path, timestamp=TIMESTAMP)
    assert m["generated_at"] == TIMESTAMP


def test_manifest_lists_hub_and_drillthroughs_with_roles(tmp_path: Path) -> None:
    from _shared import bundle

    _populate_output_dir(tmp_path)
    m = bundle.build_manifest(tmp_path, timestamp=TIMESTAMP)
    by_name = {f["name"]: f for f in m["files"]}
    assert by_name["report.html"]["role"] == "hub"
    assert by_name["drillthrough-dt-col-revenue.html"]["role"] == "drillthrough"
    assert by_name["drillthrough-dt-outlier-42.html"]["role"] == "drillthrough"
    assert by_name["methodology_appendix.html"]["role"] == "methodology_appendix"


def test_manifest_sha256_matches_file_content(tmp_path: Path) -> None:
    """TC-AN-45-02: every listed sha256 matches hashlib.sha256 of the file bytes."""
    from _shared import bundle

    _populate_output_dir(tmp_path)
    m = bundle.build_manifest(tmp_path, timestamp=TIMESTAMP)
    for entry in m["files"]:
        if entry["sha256"] is None:
            continue
        actual = hashlib.sha256((tmp_path / entry["name"]).read_bytes()).hexdigest()
        assert entry["sha256"] == actual, f"hash mismatch for {entry['name']}"


def test_manifest_self_sha256_is_null(tmp_path: Path) -> None:
    from _shared import bundle

    _populate_output_dir(tmp_path)
    m = bundle.build_manifest(tmp_path, timestamp=TIMESTAMP)
    by_name = {f["name"]: f for f in m["files"]}
    assert by_name["manifest.json"]["sha256"] is None
    assert by_name["manifest.json"]["role"] == "manifest"


def test_manifest_classifies_charts_as_asset(tmp_path: Path) -> None:
    from _shared import bundle

    _populate_output_dir(tmp_path)
    m = bundle.build_manifest(tmp_path, timestamp=TIMESTAMP)
    names = {f["name"]: f for f in m["files"]}
    # Path uses forward slashes regardless of OS in str(relative)
    chart_key = [k for k in names if k.endswith("hist-revenue.svg")][0]
    assert names[chart_key]["role"] == "asset"


def test_manifest_classifies_findings_json_as_data(tmp_path: Path) -> None:
    from _shared import bundle

    _populate_output_dir(tmp_path)
    m = bundle.build_manifest(tmp_path, timestamp=TIMESTAMP)
    by_name = {f["name"]: f for f in m["files"]}
    assert by_name["findings.json"]["role"] == "data"


def test_write_bundle_produces_zip_at_report_zip(tmp_path: Path) -> None:
    """TC-AN-45-01: a single zip archive appears in the output dir."""
    from _shared import bundle

    out = tmp_path / "analysis"
    _populate_output_dir(out)
    findings = tmp_path / "findings.json"
    _write_findings(findings)

    zip_path = bundle.write_bundle(out, findings_path=findings)
    assert zip_path == out / "report.zip"
    assert zip_path.exists()
    assert (out / "manifest.json").exists()


def test_bundle_zip_uses_deflated_compression(tmp_path: Path) -> None:
    """MEDIUM-T35: ZIP_DEFLATED, not ZIP_STORED."""
    from _shared import bundle

    out = tmp_path / "analysis"
    _populate_output_dir(out)
    findings = tmp_path / "findings.json"
    _write_findings(findings)
    zip_path = bundle.write_bundle(out, findings_path=findings)

    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            assert info.compress_type == zipfile.ZIP_DEFLATED, (
                f"{info.filename} uses {info.compress_type}, expected ZIP_DEFLATED"
            )


def test_bundle_zip_contains_every_output_file_plus_manifest(tmp_path: Path) -> None:
    from _shared import bundle

    out = tmp_path / "analysis"
    _populate_output_dir(out)
    findings = tmp_path / "findings.json"
    _write_findings(findings)
    bundle.write_bundle(out, findings_path=findings)

    with zipfile.ZipFile(out / "report.zip") as zf:
        names = set(zf.namelist())
    assert "report.html" in names
    assert "drillthrough-dt-col-revenue.html" in names
    assert "drillthrough-dt-outlier-42.html" in names
    assert "methodology_appendix.html" in names
    assert "findings.json" in names
    assert "manifest.json" in names
    assert any(n.endswith("hist-revenue.svg") for n in names)
    # The zip must not contain itself.
    assert "report.zip" not in names


def test_bundle_extracts_cleanly_in_fresh_dir(tmp_path: Path) -> None:
    """TC-AN-45-04: bundle is portable — unzip in a fresh dir, hub file exists."""
    from _shared import bundle

    out = tmp_path / "analysis"
    _populate_output_dir(out)
    findings = tmp_path / "findings.json"
    _write_findings(findings)
    zip_path = bundle.write_bundle(out, findings_path=findings)

    dest = tmp_path / "unpacked"
    dest.mkdir()
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest)
    assert (dest / "report.html").read_text(encoding="utf-8") == "<html>hub</html>"
    assert (dest / "manifest.json").exists()
    manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1


def test_bundle_has_no_sentinel_leakage(tmp_path: Path) -> None:
    """TC-AN-45-privacy-01: findings.json in the bundle carries no raw-row sentinels."""
    from _shared import bundle

    out = tmp_path / "analysis"
    _populate_output_dir(out)
    findings = tmp_path / "findings.json"
    # findings.json the engine writes does not contain row data; for this
    # privacy smoke test we rewrite the in-output findings with a benign
    # payload and assert the bundle does not introduce sentinels from any
    # other source.
    (out / "findings.json").write_text(
        json.dumps({"provenance": {"timestamp": TIMESTAMP}, "columns": []}),
        encoding="utf-8",
    )
    _write_findings(findings)
    bundle.write_bundle(out, findings_path=findings)

    with zipfile.ZipFile(out / "report.zip") as zf:
        for name in zf.namelist():
            data = zf.read(name)
            assert b"SENTINEL_LEAK" not in data, f"sentinel leak in {name}"


def test_write_bundle_raises_valueerror_when_out_dir_missing(tmp_path: Path) -> None:
    """F-05: missing out_dir must raise a typed ValueError, not bare OSError."""
    from _shared import bundle
    import pytest

    findings = tmp_path / "findings.json"
    _write_findings(findings)
    missing = tmp_path / "does-not-exist"
    with pytest.raises(ValueError, match="out_dir"):
        bundle.write_bundle(missing, findings_path=findings)


def test_write_bundle_raises_valueerror_when_timestamp_missing(tmp_path: Path) -> None:
    """F-03: missing provenance.timestamp must raise ValueError, not bare KeyError."""
    from _shared import bundle
    import pytest

    out = tmp_path / "analysis"
    _populate_output_dir(out)
    findings = tmp_path / "findings.json"
    findings.write_text(json.dumps({"provenance": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="timestamp"):
        bundle.write_bundle(out, findings_path=findings)


def test_walk_files_skips_symlinks(tmp_path: Path) -> None:
    """F-04: circular symlink under out_dir must not hang the walker."""
    from _shared import bundle

    out = tmp_path / "analysis"
    _populate_output_dir(out)
    # Circular symlink: <out>/loop → <out>
    (out / "loop").symlink_to(out)
    files = bundle._walk_files(out)
    # Must complete; must not list "loop" as a file.
    assert all("loop" not in str(f) for f in files)


def test_manifest_files_listed_in_deterministic_order(tmp_path: Path) -> None:
    """Reproducibility: re-runs produce manifests with the same file order."""
    from _shared import bundle

    out = tmp_path / "analysis"
    _populate_output_dir(out)
    m1 = bundle.build_manifest(out, timestamp=TIMESTAMP)
    m2 = bundle.build_manifest(out, timestamp=TIMESTAMP)
    assert [f["name"] for f in m1["files"]] == [f["name"] for f in m2["files"]]
