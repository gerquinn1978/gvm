"""Property-detection heuristic loader (ADR-507).

Parses ``references/property-detection.md`` and exposes a typed, immutable
:class:`PropertyHeuristic` so that the Phase-2 generator (P12-C05) can decide
whether to emit ``[PROPERTY]`` tests for a requirement.

Parsing rules
-------------
- A ``##`` heading begins a new category; its text is the category name.
- Lines starting with ``#`` (after heading lines) are comments — skipped.
- Empty lines are skipped.
- Any other non-empty line is a keyword; stored lowercased.
- Duplicate category names → :exc:`PropertyDetectionParseError`.
- Keyword line before any ``##`` heading → :exc:`PropertyDetectionParseError`.

Public surface
--------------
- :class:`PropertyHeuristic`
- :func:`load_property_detection`
- :exc:`PropertyDetectionParseError`
"""

from __future__ import annotations

import types
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Public exception
# ---------------------------------------------------------------------------


class PropertyDetectionParseError(Exception):
    """Raised when ``property-detection.md`` has a structural problem."""


# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PropertyHeuristic:
    """Loaded heuristic.

    ``categories`` maps category-name → tuple of keyword phrases
    (lowercased, preserved file order).  The mapping is a
    :class:`types.MappingProxyType` so it is immutable at runtime as well as
    at the dataclass level.
    """

    # Stored internally as a MappingProxyType via __post_init__.
    categories: types.MappingProxyType  # type: ignore[type-arg]

    def __post_init__(self) -> None:
        # Freeze the dict regardless of what the caller passed in.
        raw = dict(self.categories)
        # Convert each value to a tuple (idempotent if already a tuple).
        frozen = {k: tuple(v) for k, v in raw.items()}
        object.__setattr__(self, "categories", types.MappingProxyType(frozen))

    def matches(self, text: str) -> tuple[str, ...]:
        """Return category names whose keywords appear in *text* (case-insensitive).

        Returns an empty tuple when nothing matches.  Order matches file order.
        """
        text_lower = text.lower()
        return tuple(
            name
            for name, keywords in self.categories.items()
            if any(kw in text_lower for kw in keywords)
        )


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def _parse(content: str, source: str) -> PropertyHeuristic:
    """Parse *content* (the file text) and return a :class:`PropertyHeuristic`.

    *source* is used only for error messages.
    """
    categories: dict[str, list[str]] = {}
    current: str | None = None  # current category name

    for lineno, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()

        # ── ## heading → new category ──────────────────────────────────────
        if line.startswith("## "):
            name = line[3:].strip()
            if name in categories:
                raise PropertyDetectionParseError(
                    f"{source}:{lineno}: duplicate category '{name}'"
                )
            categories[name] = []
            current = name
            continue

        # ── comment (# …) or empty line → skip ────────────────────────────
        if not line or line.startswith("#"):
            continue

        # ── keyword ────────────────────────────────────────────────────────
        if current is None:
            raise PropertyDetectionParseError(
                f"{source}:{lineno}: keyword line before any '## ' heading: {line!r}"
            )
        categories[current].append(line.lower())

    return PropertyHeuristic(categories={k: tuple(v) for k, v in categories.items()})


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

_SKILLS_RELATIVE = Path(
    "grounded-vibe-methodology/skills/gvm-test-cases/references/property-detection.md"
)
_INSTALLED = Path.home() / ".claude/skills/gvm-test-cases/references/property-detection.md"


def _repo_path() -> Path:
    """Walk up from this file looking for the repo-root marker."""
    here = Path(__file__).resolve().parent
    # Walk up until we find the skills directory or exhaust the tree.
    candidate = here
    for _ in range(10):
        probe = candidate / _SKILLS_RELATIVE
        if probe.exists():
            return probe
        candidate = candidate.parent
    # Last-ditch: return the expected path even if it doesn't exist yet.
    return here.parent / "references" / "property-detection.md"


def load_property_detection(path: Path | str | None = None) -> PropertyHeuristic:
    """Load and parse the property-detection heuristic file.

    Resolution order when *path* is ``None``:

    1. ``~/.claude/skills/gvm-test-cases/references/property-detection.md``
       (the hook-copy production location).
    2. Walk up from this module's location to find
       ``grounded-vibe-methodology/skills/gvm-test-cases/references/property-detection.md``
       (test / CI context).

    Parameters
    ----------
    path:
        Explicit :class:`~pathlib.Path`, ``str`` path, or ``None`` to use
        default resolution.

    Raises
    ------
    PropertyDetectionParseError
        If the file content is structurally malformed.
    FileNotFoundError
        If no file can be located.
    """
    if path is None:
        resolved = _INSTALLED if _INSTALLED.exists() else _repo_path()
    else:
        resolved = Path(path)

    content = resolved.read_text(encoding="utf-8")
    return _parse(content, str(resolved))
