"""`.stub-allowlist` loader (honesty-triad ADR-108).

Flat-text format: ``<path>::<symbol> | <kind> | <justification>``.
Lines beginning with ``#`` and blank lines are skipped. Loader validates
that ``<kind> ∈ {enum, constant, fixture}`` and that ``<path>`` exists
under ``project_root``. First malformed line aborts the load — no partial
load. Returns an immutable :class:`Allowlist` with two parallel views:
``pairs`` (set of ``(path, symbol)``) for membership tests and ``kinds``
(map of ``(path, symbol) → kind``) for classification.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

KIND_VALUES: frozenset[str] = frozenset({"enum", "constant", "fixture"})

Kind = Literal["enum", "constant", "fixture"]


class AllowlistError(Exception):
    """Base class for `.stub-allowlist` load failures."""


class MalformedAllowlistLineError(AllowlistError):
    """Pipe count, `::` separator, or empty fields wrong on a line."""


class UnknownKindError(AllowlistError):
    """`<kind>` is not in :data:`KIND_VALUES`."""


class MissingPathError(AllowlistError):
    """`<path>` does not exist under the project root."""


@dataclass(frozen=True)
class AllowlistEntry:
    path: Path
    symbol: str
    kind: Kind
    justification: str


@dataclass(frozen=True)
class Allowlist:
    entries: tuple[AllowlistEntry, ...]
    pairs: frozenset[tuple[str, str]]
    kinds: dict[tuple[str, str], str]


def load_allowlist(
    path: Path | str,
    *,
    project_root: Path | str | None = None,
) -> Allowlist:
    """Load and validate the allowlist at *path*. Aborts on first error.

    Path-existence checks resolve `<path>` relative to *project_root* (or
    the current working directory if not supplied).
    """
    file_path = Path(path)
    if not file_path.exists():
        raise AllowlistError(f"allowlist file not found: {file_path}")

    root = Path(project_root) if project_root is not None else Path.cwd()
    text = file_path.read_text(encoding="utf-8")

    entries: list[AllowlistEntry] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        entries.append(_parse_line(stripped, line_no, file_path, root))

    pairs = frozenset((str(e.path), e.symbol) for e in entries)
    kinds = {(str(e.path), e.symbol): e.kind for e in entries}
    return Allowlist(entries=tuple(entries), pairs=pairs, kinds=kinds)


def _parse_line(
    line: str,
    line_no: int,
    file_path: Path,
    project_root: Path,
) -> AllowlistEntry:
    parts = [p.strip() for p in line.split("|")]
    if len(parts) != 3:
        raise MalformedAllowlistLineError(
            f"{file_path}:{line_no}: expected 3 pipe-separated fields, got {len(parts)}"
        )
    locator, kind_raw, justification = parts

    if locator.count("::") != 1:
        raise MalformedAllowlistLineError(
            f"{file_path}:{line_no}: expected exactly one '::' separator in "
            f"'<path>::<symbol>', got {locator!r}"
        )
    path_raw, symbol = (s.strip() for s in locator.split("::"))
    if not path_raw or not symbol:
        raise MalformedAllowlistLineError(
            f"{file_path}:{line_no}: empty path or symbol in {locator!r}"
        )

    if kind_raw not in KIND_VALUES:
        valid = ", ".join(sorted(KIND_VALUES))
        raise UnknownKindError(
            f"{file_path}:{line_no}: unknown kind {kind_raw!r} "
            f"(expected one of: {valid})"
        )

    if not justification:
        raise MalformedAllowlistLineError(
            f"{file_path}:{line_no}: justification is empty"
        )

    target = project_root / path_raw
    if not target.exists():
        raise MissingPathError(
            f"{file_path}:{line_no}: path {path_raw!r} does not exist under "
            f"{project_root}"
        )

    return AllowlistEntry(
        path=Path(path_raw),
        symbol=symbol,
        kind=kind_raw,  # type: ignore[arg-type]  # validated above
        justification=justification,
    )
