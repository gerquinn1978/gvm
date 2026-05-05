"""Bundle export for /gvm-analysis reports (ADR-309 / AN-45).

Walks the rendered ``analysis/`` output directory, classifies each file
into a role (hub / drillthrough / methodology_appendix / data / asset /
manifest), computes its SHA-256, and writes both ``manifest.json`` and
``report.zip`` (ZIP_DEFLATED) into the same directory.

Determinism: ``manifest.json::generated_at`` MUST come from the findings'
``provenance.timestamp`` field, not ``datetime.now()`` (post-R4 MEDIUM-T34).
Two runs with identical input + seed therefore produce byte-identical
manifests — ASR-3 reproducibility is preserved.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any


SCHEMA_VERSION: int = 1

ROLE_HUB: str = "hub"
ROLE_DRILLTHROUGH: str = "drillthrough"
ROLE_METHODOLOGY_APPENDIX: str = "methodology_appendix"
ROLE_DATA: str = "data"
ROLE_ASSET: str = "asset"
ROLE_MANIFEST: str = "manifest"

_BUNDLE_FILENAME: str = "report.zip"
_MANIFEST_FILENAME: str = "manifest.json"


def _sha256_of(path: Path) -> str:
    """Return the hex SHA-256 of ``path``'s byte content."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _classify(relative: Path) -> str:
    """Assign an ADR-309 role to ``relative`` (relative to the output dir)."""
    name = relative.name
    if relative.parts and relative.parts[0] == "charts":
        return ROLE_ASSET
    if name == _MANIFEST_FILENAME:
        return ROLE_MANIFEST
    if name == "report.html":
        return ROLE_HUB
    if name.startswith("drillthrough-") and name.endswith(".html"):
        return ROLE_DRILLTHROUGH
    # Forward guard: the methodology appendix is currently inlined into
    # report.html via {% include '_methodology_appendix.html.j2' %}, so no
    # standalone file is produced today. This branch fires only if a future
    # chunk externalises the appendix to its own file with this exact name.
    if name == "methodology_appendix.html":
        return ROLE_METHODOLOGY_APPENDIX
    if name == "findings.json":
        return ROLE_DATA
    # Any other asset file (SVG, PNG, etc.) that lands in the output dir.
    return ROLE_ASSET


def _walk_files(out_dir: Path) -> list[Path]:
    """Return every file under ``out_dir`` as relative paths, sorted.

    Excludes the bundle zip itself (it must not contain itself).
    """
    results: list[Path] = []
    for p in sorted(out_dir.rglob("*")):
        # Skip symlinks before is_file() so a circular symlink can't hang rglob.
        if p.is_symlink():
            continue
        if not p.is_file():
            continue
        rel = p.relative_to(out_dir)
        if rel.name == _BUNDLE_FILENAME:
            continue
        results.append(rel)
    return results


def build_manifest(out_dir: Path, *, timestamp: str) -> dict[str, Any]:
    """Walk ``out_dir`` and return the manifest dict.

    ``timestamp`` must be ``findings.provenance.timestamp`` — never
    ``datetime.now()``. The caller is responsible for reading findings.json.
    """
    files: list[dict[str, Any]] = []
    for rel in _walk_files(out_dir):
        role = _classify(rel)
        sha: str | None
        if rel.name == _MANIFEST_FILENAME:
            # Self-referential entry; sha256 is null because the manifest
            # contains its own hash if computed.
            sha = None
        else:
            sha = _sha256_of(out_dir / rel)
        files.append({"name": str(rel), "role": role, "sha256": sha})
    # Ensure manifest.json is listed even before it's written — callers
    # may invoke build_manifest before persistence.
    if not any(f["name"] == _MANIFEST_FILENAME for f in files):
        files.append(
            {"name": _MANIFEST_FILENAME, "role": ROLE_MANIFEST, "sha256": None}
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": timestamp,
        "files": files,
    }


def write_bundle(out_dir: Path, *, findings_path: Path) -> Path:
    """Write ``manifest.json`` and ``report.zip`` into ``out_dir``.

    Returns the path to the written zip. Reads ``findings_path`` once to
    pull ``provenance.timestamp`` (MEDIUM-T34); does not use
    ``datetime.now()``.
    """
    if not out_dir.is_dir():
        raise ValueError(f"out_dir does not exist or is not a directory: {out_dir}")
    findings_data = json.loads(findings_path.read_text(encoding="utf-8"))
    try:
        timestamp = findings_data["provenance"]["timestamp"]
    except KeyError as exc:
        raise ValueError(
            f"findings.json at {findings_path} is missing "
            f"provenance.{exc.args[0]}; cannot build a reproducible manifest."
        ) from exc

    # Build manifest against the current output-dir contents, then persist.
    manifest = build_manifest(out_dir, timestamp=timestamp)
    manifest_path = out_dir / _MANIFEST_FILENAME
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=False), encoding="utf-8"
    )

    zip_path = out_dir / _BUNDLE_FILENAME
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in _walk_files(out_dir):
            zf.write(out_dir / rel, arcname=str(rel))
    return zip_path
