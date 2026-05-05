"""CLI wrapper for the comprehension-question bridge (ADR-109 / P5-C01b).

Reads a sibling temp JSON file produced by Claude, invokes
``_shared.findings.patch_comprehension_questions`` to patch ``findings.json``
atomically, and maps every failure class to a deterministic exit code so
SKILL.md can implement the retry policy without parsing stderr.

Exit codes
----------
- 0  success; temp file removed
- 1  I/O failure (cross-volume write, permission, disk)
- 2  structural failure (missing path, malformed JSON, wrong shape)
- 3  referential integrity (supporting_finding_id absent from headline_findings)
- 4  jargon violation in question or answer text
- 5  privacy boundary violation (defensive — helper does not raise this today)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _shared.diagnostics import (
    JargonError,
    PrivacyBoundaryViolation,
    ReferentialIntegrityError,
    format_diagnostic,
)
from _shared.findings import (
    SchemaValidationError,
    patch_comprehension_questions,
)

EXIT_OK: int = 0
EXIT_IO: int = 1
EXIT_STRUCTURE: int = 2
EXIT_REFERENTIAL: int = 3
EXIT_JARGON: int = 4
EXIT_PRIVACY: int = 5


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="_patch_questions",
        description="Patch findings.json::comprehension_questions per ADR-109.",
    )
    parser.add_argument("--findings", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    return parser.parse_args(argv)


def _fail(exc: Exception, code: int) -> int:
    sys.stderr.write(format_diagnostic(exc) + "\n")
    return code


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if not args.findings.is_file():
        return _fail(
            SchemaValidationError(
                f"findings path is not a regular file: {args.findings}"
            ),
            EXIT_STRUCTURE,
        )
    if not args.questions.is_file():
        return _fail(
            SchemaValidationError(
                f"questions path is not a regular file: {args.questions}"
            ),
            EXIT_STRUCTURE,
        )

    try:
        questions_text = args.questions.read_text(encoding="utf-8")
    except OSError as exc:
        return _fail(exc, EXIT_IO)

    try:
        questions = json.loads(questions_text)
    except json.JSONDecodeError as exc:
        return _fail(
            SchemaValidationError(f"questions JSON is malformed: {exc.msg}"),
            EXIT_STRUCTURE,
        )

    try:
        patch_comprehension_questions(args.findings, questions)
    except SchemaValidationError as exc:
        return _fail(exc, EXIT_STRUCTURE)
    except ReferentialIntegrityError as exc:
        return _fail(exc, EXIT_REFERENTIAL)
    except JargonError as exc:
        return _fail(exc, EXIT_JARGON)
    except PrivacyBoundaryViolation as exc:
        return _fail(exc, EXIT_PRIVACY)
    except OSError as exc:
        return _fail(exc, EXIT_IO)

    # Success: temp questions file was Claude's working artefact. Remove it.
    # Failure to delete is not fatal — the patch already succeeded — but warn
    # so the operator knows a stale temp file remains on disk.
    try:
        args.questions.unlink(missing_ok=True)
    except OSError as exc:
        sys.stderr.write(
            f"warning: patch succeeded but could not remove temp file "
            f"{args.questions}: {exc}\n"
        )
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
