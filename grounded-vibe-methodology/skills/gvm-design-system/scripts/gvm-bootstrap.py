#!/usr/bin/env python3
"""
gvm-bootstrap.py — initialise the GVM home directory.

Replaces the previous multi-line shell snippet in shared-rules.md rule 14.
Single-command, idempotent, atomic — eliminates the failure mode where
a copy-paste of the bootstrap's right-hand side (`echo 'header' > file`)
would clobber an existing activation log.

Cross-platform: macOS, Linux, Windows. Standard library only.

Behaviour:

1. Creates ``~/.claude/gvm/`` and ``~/.claude/gvm/docs/`` (idempotent).
2. Creates ``expert-activations.csv`` with the canonical header if it
   does not exist.
3. **Self-heals a header-less file.** If the activation CSV exists but
   the first line is not the expected header (which is exactly what
   happens when another process clobbers the file with ``>`` or writes
   raw rows without a header), the script atomically prepends the
   header — no rows are lost.
4. Copies ``plugin-guide.html`` from the plugin's ``docs/`` directory
   into ``~/.claude/gvm/docs/`` if present (existing behaviour).
5. Migrates a legacy activation log from the old location
   (``~/.claude/skills/gvm-design-system/expert-activations.csv``) to
   the new location if the new file does not yet exist.

Exit codes:

  0 — success (or already-initialised; idempotent)
  1 — I/O error
  2 — invalid arguments (none accepted)

Usage:

    python3 ~/.claude/skills/gvm-design-system/scripts/gvm-bootstrap.py
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

HEADER_LINE = (
    '"timestamp","project","skill","phase","expert","work",'
    '"classification","tier","event"'
)


def gvm_home() -> Path:
    return Path.home() / ".claude" / "gvm"


def activations_csv() -> Path:
    return gvm_home() / "expert-activations.csv"


def legacy_activations_csv() -> Path:
    return (
        Path.home()
        / ".claude"
        / "skills"
        / "gvm-design-system"
        / "expert-activations.csv"
    )


def plugin_docs_dir() -> Path:
    return Path.home() / ".claude" / "skills" / "gvm-design-system" / "docs"


def ensure_directories() -> None:
    """Create the GVM home and docs directories if they don't exist."""
    (gvm_home() / "docs").mkdir(parents=True, exist_ok=True)


def migrate_legacy_log() -> None:
    """Move legacy activation log to its current location if needed.

    If the legacy file exists at the old skills/ path AND the current
    file does not yet exist, MOVE (not copy) the legacy file. This
    handles the rare case of a user upgrading from a pre-v1 install.
    """
    new_path = activations_csv()
    old_path = legacy_activations_csv()
    if old_path.exists() and not new_path.exists():
        shutil.move(str(old_path), str(new_path))


def is_canonical_header(line: str) -> bool:
    """Return True if the line is the expected header.

    Tolerates trailing whitespace and either CSV-quoted or unquoted
    field names (older bootstraps used unquoted; log-expert.py writes
    quoted via csv.QUOTE_ALL).
    """
    stripped = line.rstrip()
    if stripped == HEADER_LINE:
        return True
    # Accept the legacy unquoted form too.
    legacy = (
        "timestamp,project,skill,phase,expert,work,classification,tier,event"
    )
    return stripped == legacy


def ensure_header() -> None:
    """Ensure the activation CSV exists and has a valid header.

    Three cases:

    a) File does not exist → create it with header.
    b) File exists, first line is the canonical header → no-op.
    c) File exists but first line is NOT the canonical header (clobbered,
       missing, or corrupted) → atomically prepend the canonical header.
       Existing rows are preserved.
    """
    csv_path = activations_csv()

    # Case (a): create from scratch.
    if not csv_path.exists():
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            f.write(HEADER_LINE + "\n")
        return

    # Read first line to decide between (b) and (c).
    try:
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            first_line = f.readline()
    except OSError:
        # If we can't even read it, escalate to the caller.
        raise

    # Case (b): canonical header already present.
    if is_canonical_header(first_line):
        return

    # Case (c): self-heal. Atomically rewrite with header prepended.
    # Use a temp file in the SAME directory so os.replace is atomic
    # (cross-volume rename degrades to copy+delete and breaks atomicity).
    with csv_path.open("rb") as src:
        existing = src.read()

    fd, tmp_name = tempfile.mkstemp(
        prefix=".expert-activations.",
        suffix=".tmp",
        dir=str(csv_path.parent),
    )
    try:
        with os.fdopen(fd, "wb") as out:
            out.write((HEADER_LINE + "\n").encode("utf-8"))
            out.write(existing)
        os.replace(tmp_name, csv_path)
    except OSError:
        # Best-effort cleanup if rename failed.
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def copy_plugin_guide() -> None:
    """Copy plugin-guide.html into the GVM home docs directory if present."""
    src = plugin_docs_dir() / "plugin-guide.html"
    if src.exists():
        dest = gvm_home() / "docs" / "plugin-guide.html"
        try:
            shutil.copyfile(src, dest)
        except OSError:
            # Non-fatal: missing the doc copy doesn't break the skills.
            pass


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        print(
            "gvm-bootstrap: takes no arguments. "
            "Run with no args to initialise the GVM home directory.",
            file=sys.stderr,
        )
        return 2

    try:
        ensure_directories()
        migrate_legacy_log()
        ensure_header()
        copy_plugin_guide()
    except OSError as e:
        print(f"gvm-bootstrap: I/O error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
