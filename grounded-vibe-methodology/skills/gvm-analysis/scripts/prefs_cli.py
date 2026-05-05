"""CLI wrapper for the preferences flow (ADR-104 / P5-C04).

Thin dispatcher around :mod:`_shared.prefs`. Orchestration (SKILL.md step 6)
invokes this via Bash and branches on exit code — it never parses stderr.
Exit codes mirror the `_patch_questions.py` pattern: one class per failure
mode.

Subcommands
-----------
``load --path PATH``
    Read/migrate/validate the prefs file and print a JSON object to stdout::

        { "prefs": { ... }, "warnings": [ "..." ] }

    A missing file returns defaults with an empty warnings list (first-run
    path — not an error). A version-less file is migrated to v1 AND the
    file is rewritten on disk (AN-44).

``save --path PATH --prefs-json STRING``
    Parse the JSON string, validate against the schema, atomic-write to
    PATH. Refuses to write on validation failure.

Exit codes
----------
- 0 success
- 1 I/O failure
- 2 validation (PreferencesValidationError, malformed JSON input,
  bad arguments)
- 3 migration refused (PreferencesMigrationError — future version or
  broken chain)
- 4 malformed YAML (diagnostics.MalformedFileError kind=malformed_yaml)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _shared import diagnostics
from _shared.prefs import (
    PreferencesMigrationError,
    PreferencesValidationError,
    load,
    merge_with_defaults,
    save,
)

EXIT_OK: int = 0
EXIT_IO: int = 1
EXIT_VALIDATION: int = 2
EXIT_MIGRATION: int = 3
EXIT_MALFORMED_YAML: int = 4


def _emit_error(summary: str, what: str, try_: str) -> None:
    """Write the canonical ERROR / What went wrong / What to try block."""
    sys.stderr.write(f"ERROR: {summary}\n")
    sys.stderr.write(f"What went wrong:\n  {what}\n")
    sys.stderr.write(f"What to try:\n  {try_}\n")


def _cmd_load(path: Path) -> int:
    try:
        prefs, warnings = load(path)
    except PreferencesMigrationError as exc:
        _emit_error(
            summary="preferences migration refused",
            what=str(exc),
            try_=(
                "Either upgrade the /gvm-analysis skill to a version that "
                "supports this preferences file, or delete the file to "
                "start fresh with shipped defaults."
            ),
        )
        return EXIT_MIGRATION
    except PreferencesValidationError as exc:
        _emit_error(
            summary="preferences validation failed",
            what=str(exc),
            try_=(
                "Open the preferences file, fix the offending value to "
                "match the documented constraint, and retry. Or delete the "
                "file to restore shipped defaults."
            ),
        )
        return EXIT_VALIDATION
    except diagnostics.MalformedFileError as exc:
        _emit_error(
            summary=f"preferences file is malformed YAML: {path}",
            what=str(exc),
            try_=(
                "Check the file for an unclosed bracket, missing colon, or "
                "stray tab character. pyyaml will name the offending row."
            ),
        )
        return EXIT_MALFORMED_YAML
    except OSError as exc:
        _emit_error(
            summary=f"cannot read preferences file: {path}",
            what=str(exc),
            try_=(
                "Confirm the file is readable and the parent directory "
                "exists. `~/.claude/gvm/analysis/` is the canonical home."
            ),
        )
        return EXIT_IO

    print(json.dumps({"prefs": prefs, "warnings": warnings}), flush=True)
    return EXIT_OK


def _cmd_save(path: Path, prefs_json: str) -> int:
    try:
        prefs = json.loads(prefs_json)
    except json.JSONDecodeError as exc:
        _emit_error(
            summary="prefs-json argument is not valid JSON",
            what=str(exc),
            try_=(
                "Pass a JSON-encoded preferences object to --prefs-json. "
                "Single-quote the shell argument so the shell doesn't eat "
                "your double quotes."
            ),
        )
        return EXIT_VALIDATION

    if not isinstance(prefs, dict):
        _emit_error(
            summary="prefs-json must decode to a JSON object",
            what=f"decoded to {type(prefs).__name__}, not an object",
            try_="Wrap your preferences in { ... }.",
        )
        return EXIT_VALIDATION

    # merge_with_defaults() is the validator; save() itself does not
    # validate. Call the validator BEFORE hitting disk so an out-of-range
    # value cannot sneak past via the CLI.
    try:
        merged, warnings = merge_with_defaults(prefs)
    except PreferencesValidationError as exc:
        _emit_error(
            summary="preferences validation failed",
            what=str(exc),
            try_="Adjust the offending value to match its documented constraint.",
        )
        return EXIT_VALIDATION

    if warnings:
        for msg in warnings:
            sys.stderr.write(f"WARNING: {msg}\n")

    # save() is write-only; validation completed above by merge_with_defaults.
    # Ensure the parent directory exists — first-run saves into
    # ~/.claude/gvm/analysis/ would otherwise fail with FileNotFoundError,
    # which is the one case this CLI is explicitly designed to serve.
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _emit_error(
            summary=f"cannot create preferences directory: {path.parent}",
            what=str(exc),
            try_="Confirm your home directory is writable.",
        )
        return EXIT_IO

    try:
        save(path, merged)
    except OSError as exc:
        _emit_error(
            summary=f"cannot write preferences file: {path}",
            what=str(exc),
            try_=(
                "Confirm the parent directory is writable. Create "
                "`~/.claude/gvm/analysis/` if needed."
            ),
        )
        return EXIT_IO

    return EXIT_OK


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="prefs_cli",
        description="Preferences I/O for /gvm-analysis (ADR-104).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    load_p = sub.add_parser("load", help="read + migrate + validate prefs")
    load_p.add_argument("--path", type=Path, required=True)

    save_p = sub.add_parser("save", help="validate + atomic-write prefs")
    save_p.add_argument("--path", type=Path, required=True)
    save_p.add_argument(
        "--prefs-json",
        required=True,
        help="JSON-encoded prefs object",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.command == "load":
        return _cmd_load(args.path)
    if args.command == "save":
        return _cmd_save(args.path, args.prefs_json)
    # argparse's `required=True` on subparsers forbids reaching here. If a
    # future Python/argparse regression ever does, loudly refuse rather than
    # masquerade as a user validation error.
    raise AssertionError(f"unreachable: unknown subcommand {args.command!r}")


if __name__ == "__main__":
    sys.exit(main())
