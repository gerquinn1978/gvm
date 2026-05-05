#!/usr/bin/env python3
"""Post-analysis de-anonymisation script (anonymisation-pipeline ADR-405).

P14-C03 (originally P7-C03 in the gvm-analysis impl-guide; renumbered to
avoid clashing with the GVM plugin v2.0.0 build's audit trail).

Standalone CLI: reads a mapping CSV produced by :mod:`anonymise` and walks
one or more rendered HTML files, replacing every ``TOK_{column}_{NNN}``
occurrence with ``html.escape(original_value, quote=True)``. The mapping
CSV stores raw (unescaped) values; escaping happens at substitution time
so the rendered HTML is well-formed for special characters (``<``, ``>``,
``&``, ``"``, ``'``).

Exit codes
----------
* ``0`` — every input file was processed successfully (zero residual
  tokens for any known column after substitution).
* ``1`` — diagnosed user error (missing/empty mapping, missing input,
  conflicting CLI flags). Diagnostic emitted to stderr.
* ``2`` — unexpected internal error (uncaught exception).

The CLI exposes :func:`main(argv)` for in-process testing — pass
``argv=None`` to use ``sys.argv[1:]``.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path
from typing import Sequence

from _shared import mapping as mapping_module
from _shared.diagnostics import MalformedFileError, format_diagnostic
from _shared.tokens import build_match_regex


_DEFAULT_GLOB = "*.html"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "De-anonymise rendered HTML by substituting tokens with the "
            "original values from the mapping CSV. Operates on a single "
            "file or a directory of HTML files."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Input HTML file OR directory of HTML files.",
    )
    parser.add_argument(
        "--mapping",
        required=True,
        type=Path,
        help="Mapping CSV produced by anonymise.py (column,original_value,token).",
    )
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "--output",
        default=None,
        type=Path,
        help=(
            "Output path. For a single-file input, the de-anonymised HTML is "
            "written here. Mutually exclusive with --in-place. Required for "
            "single-file mode unless --in-place is set."
        ),
    )
    output_group.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite each input file. Mutually exclusive with --output.",
    )
    parser.add_argument(
        "--glob",
        default=_DEFAULT_GLOB,
        help=f"Glob pattern for directory mode (default: {_DEFAULT_GLOB}).",
    )
    return parser


def _substitute(text: str, pattern: re.Pattern[str], lookup: dict[str, str]) -> str:
    """Replace every match of ``pattern`` in ``text`` using ``lookup``.

    Each match is the whole token (no capture group); the replacement is
    ``html.escape(original, quote=True)`` so HTML special characters in
    the original value are rendered safely. A token that matches the
    pattern but is absent from ``lookup`` (e.g. residual from a different
    mapping) is left untouched — fail-soft, since the post-check step
    will flag any genuine residuals.
    """

    def _repl(match: re.Match[str]) -> str:
        token = match.group(0)
        if token in lookup:
            return html.escape(lookup[token], quote=True)
        return token

    return pattern.sub(_repl, text)


def _has_residual_token(text: str, pattern: re.Pattern[str]) -> bool:
    """Spec ADR-405 step 5: post-replace there must be no residual token
    that the regex still matches. ``_substitute`` only leaves a token
    in place when it is unknown to the mapping — that is the genuine
    residual case worth flagging."""
    return pattern.search(text) is not None


def _resolve_targets(input_path: Path, glob: str) -> list[Path]:
    """Enumerate the HTML files to process.

    Single-file inputs return ``[input_path]`` regardless of suffix —
    the caller asked for that exact file. Directory inputs walk
    recursively for ``glob``.
    """
    if input_path.is_dir():
        return sorted(input_path.rglob(glob))
    return [input_path]


def _resolve_output_for(
    target: Path, args: argparse.Namespace, input_root: Path
) -> Path:
    """Pick the output path for a single processed target.

    * ``--in-place``        → write back to ``target``.
    * single-file + ``--output`` → write to ``args.output`` (the user's
      explicit choice).
    * directory mode is always in-place (the only sane default for an
      arbitrary tree of HTML files).
    """
    if args.in_place:
        return target
    if input_root.is_dir():
        # Directory mode without --in-place is rejected by the runtime
        # guard in main() (lines 159-165), so this branch is unreachable
        # in practice. Defensive return.
        return target
    return args.output  # single-file + --output


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if not args.in_place and args.output is None:
        print(
            "ERROR: must supply either --output PATH (single-file mode) or "
            "--in-place. Refusing to invent an output location.",
            file=sys.stderr,
        )
        return 1

    if args.input.is_dir() and not args.in_place:
        print(
            "ERROR: directory inputs require --in-place. Per-file output "
            "paths cannot be derived from a single --output flag.",
            file=sys.stderr,
        )
        return 1

    if not args.input.exists():
        print(
            f"ERROR: input path does not exist: {args.input}",
            file=sys.stderr,
        )
        return 1

    try:
        mapping_data = mapping_module.load(args.mapping)
    except MalformedFileError as exc:
        print(format_diagnostic(exc), file=sys.stderr)
        return 1

    if not mapping_data.columns:
        print(
            "ERROR: mapping CSV contains no rows; nothing to substitute. "
            "Re-run anonymise.py to produce a non-empty mapping.",
            file=sys.stderr,
        )
        return 1

    pattern = build_match_regex(mapping_data.columns)
    lookup = mapping_data.token_to_value

    targets = _resolve_targets(args.input, args.glob)
    for target in targets:
        try:
            text = target.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"ERROR: cannot read {target}: {exc}", file=sys.stderr)
            return 1

        replaced = _substitute(text, pattern, lookup)

        if _has_residual_token(replaced, pattern):
            print(
                f"ERROR: residual token(s) remain in {target} after "
                "substitution — the mapping does not cover every token in "
                "the file. Refusing to write a partial output.",
                file=sys.stderr,
            )
            return 1

        out_path = _resolve_output_for(target, args, args.input)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(replaced, encoding="utf-8")

    print(f"de-anonymised {len(targets)} file(s); mapping: {args.mapping}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
