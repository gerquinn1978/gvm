"""One-time migration: stamp schema_version: 0 on legacy calibration.md.

Idempotent. Refuses non-calibration files. Does not modify verdicts.
Routes the monotonicity check through `_calibration_parser._assert_no_downgrade`
so the guard exists on a single code path (cross-cutting ADR-111, ADR-608).

Usage:
    python -m gvm_migrate_calibration <path>

Default <path>: ./reviews/calibration.md

Exit codes:
    0  success or already-migrated (idempotent)
    1  file not found
    2  refused (path not allowlisted, or not a calibration file)
"""

from __future__ import annotations

import sys
from pathlib import Path

ALLOWED_SUFFIX = "reviews/calibration.md"
CALIBRATION_MARKER = "## Score History"


def main(argv: list[str]) -> int:
    target = Path(argv[1]) if len(argv) > 1 else Path("reviews/calibration.md")

    # Hardened allowlist (resolves R2 M-R2-1; matches honesty-triad ADR-111 contract):
    # 1. Absolute paths refused outright.
    if target.is_absolute():
        sys.stderr.write(f"ERROR: absolute paths not accepted: {target}\n")
        return 2
    # 2. Normalised relative path must equal `reviews/calibration.md` exactly,
    #    or end with `/reviews/calibration.md`.
    normalised = str(target).replace("\\", "/")
    while normalised.startswith("./"):
        normalised = normalised[2:]
    if normalised != ALLOWED_SUFFIX and not normalised.endswith("/" + ALLOWED_SUFFIX):
        sys.stderr.write(f"ERROR: refusing to process non-calibration path: {target}\n")
        return 2

    if not target.exists():
        sys.stderr.write(f"ERROR: file not found: {target}\n")
        return 1

    text = target.read_text(encoding="utf-8")

    # Idempotence: already-migrated detection. If the file starts with a YAML
    # frontmatter block whose body contains a `schema_version:` key (line-start
    # match — not a substring, so YAML comments or nested values can't trigger
    # a false positive), treat as already migrated.
    if text.startswith("---\n"):
        parts = text.split("---", 2)
        if len(parts) >= 3 and any(
            line.startswith("schema_version:")
            for line in parts[1].splitlines()
        ):
            sys.stdout.write(f"already migrated: {target} — no change\n")
            return 0

    # Sanity: must contain the canonical marker. Runs AFTER idempotence so
    # already-migrated files (which still contain the marker, but might have
    # different framing) take the no-op path first.
    if CALIBRATION_MARKER not in text:
        sys.stderr.write(
            f"ERROR: file does not contain '{CALIBRATION_MARKER}' — "
            f"not a calibration file.\n"
        )
        return 2

    # Route through the shared monotonicity guard. For an unmigrated file
    # (no frontmatter), `load_calibration` will treat it as schema 0, so
    # writing schema 0 is allowed. The guard exists to refuse a future
    # accidental re-stamping of a higher-version file with version 0.
    sys.path.insert(
        0,
        str(
            Path(__file__).resolve().parent.parent.parent
            / "gvm-design-system"
            / "scripts"
        ),
    )
    try:
        from _calibration_parser import (  # noqa: E402
            SchemaDowngradeError,
            _assert_no_downgrade,
        )
    except ImportError as exc:
        sys.stderr.write(
            f"ERROR: _calibration_parser not importable: {exc}. "
            "This indicates a broken plugin installation, not a calibration issue.\n"
        )
        return 2

    try:
        _assert_no_downgrade(target, attempted_schema_version=0)
    except SchemaDowngradeError as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 2

    new_text = "---\nschema_version: 0\n---\n" + text
    target.write_text(new_text, encoding="utf-8")
    sys.stdout.write(f"migrated: {target} — schema_version: 0 stamped\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
