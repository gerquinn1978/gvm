"""Goal ambiguity scanner (P10-C03 — IM-3, discovery ADR-303).

Default denylist ships in `references/ambiguity-indicators.md`. Project
extensions live at the project root as `.gvm-impact-map.denylist`
(additions) and `.gvm-impact-map.allowlist` (subtractions). Loader
merges them into a single effective denylist; `scan_goal` tokenizes a
`Goal` and returns IM-3 errors for unquantified hits.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _validator import ValidationError  # noqa: E402

# `_impact_map_parser` lives in gvm-design-system. _validator.py already
# inserts that path on sys.path at import-time; we rely on that side effect.
from _impact_map_parser import Goal  # noqa: E402

_TOKEN_RE = re.compile(r"[A-Za-z]+")
_NUMERIC_RE = re.compile(r"\d+%?")
_PROJECT_DENYLIST_FILENAME = ".gvm-impact-map.denylist"
_PROJECT_ALLOWLIST_FILENAME = ".gvm-impact-map.allowlist"


def tokenize(text: str) -> list[str]:
    """Split *text* on non-letter characters; lowercase each token."""
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text)]


def _read_word_file(path: Path) -> set[str]:
    """Parse a denylist/allowlist file. Comments (`#`) and blanks ignored."""
    words: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        words.add(line.lower())
    return words


def load_denylist(
    skill_default: Path,
    project_root: Path | None,
) -> frozenset[str]:
    """Return the effective denylist.

    ``skill_default`` is required and must exist. ``project_root`` is
    optional; missing project files are not errors.
    """
    base = _read_word_file(skill_default)

    if project_root is not None and project_root.exists():
        deny = project_root / _PROJECT_DENYLIST_FILENAME
        if deny.exists():
            base |= _read_word_file(deny)
        allow = project_root / _PROJECT_ALLOWLIST_FILENAME
        if allow.exists():
            base -= _read_word_file(allow)

    return frozenset(base)


def scan_goal(goal: Goal, denylist: frozenset[str]) -> list[ValidationError]:
    """Return IM-3 errors for *goal*. Empty list = pass.

    Algorithm (ADR-303): the goal passes iff (a) no token in
    ``goal.statement`` matches the effective denylist, OR (b) any matching
    token is on the same line as a numeric quantity (regex ``\\d+%?``) in
    the combined text ``goal.statement + goal.metric + goal.target``.
    """
    statement_tokens = set(tokenize(goal.statement))
    hits = statement_tokens & denylist
    if not hits:
        return []

    # Strict ADR-303 reading: the hit is quantified iff a numeric quantity
    # appears on the SAME LINE as the matching token within
    # `statement + "\n" + metric + "\n" + target`. A numeric elsewhere in
    # the combined text does not rescue an unquantified hit on another line.
    combined = "\n".join((goal.statement, goal.metric, goal.target))
    for line in combined.splitlines():
        if not _NUMERIC_RE.search(line):
            continue
        if set(tokenize(line)) & hits:
            return []

    return [
        ValidationError(
            code="IM-3",
            message=(
                f"Goal {goal.id} uses unquantified verb {word!r} — "
                f"pair it with a numeric target or rephrase as an outcome"
            ),
        )
        for word in sorted(hits)
    ]
