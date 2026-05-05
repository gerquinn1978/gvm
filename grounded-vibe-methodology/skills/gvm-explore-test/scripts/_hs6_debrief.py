"""HS-6 retroactive registration helper for `/gvm-explore-test` (P11-C11).

The debrief flow assembles a list of `StubEntry` records from the
practitioner's session decisions (out of scope here — driven by a future
SKILL.md AskUserQuestion sequence). This helper takes that list and
appends each entry to ``STUBS.md`` atomically via ``_stubs_parser.append``.

Per honesty-triad ADR-110: HS-6 fires once per project; this helper is
the write-path the debrief uses to materialise the discovered cohort.
Duplicate-path findings are caught and surfaced in the result rather
than crashing — the practitioner sees a summary at debrief, not an
exception.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


def _ensure_design_system_on_path() -> None:
    scripts = Path(__file__).resolve().parents[2] / "gvm-design-system" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))


_ensure_design_system_on_path()

from _stubs_parser import (  # noqa: E402  (import after sys.path mutation)
    DuplicatePathError,
    StubEntry,
    append,
)


@dataclass(frozen=True)
class RegistrationResult:
    appended: tuple[StubEntry, ...]
    skipped_duplicates: tuple[str, ...]


def register_discovered_stubs(
    stubs_path: Path, entries: Sequence[StubEntry]
) -> RegistrationResult:
    """Append each entry to ``stubs_path`` via ``_stubs_parser.append``.

    Duplicate paths are caught and recorded in ``skipped_duplicates`` so
    the debrief flow can summarise to the practitioner. Other exceptions
    (``FileNotFoundError``, ``StubsParseError``) propagate — they
    indicate misconfiguration or invalid input.
    """
    appended: list[StubEntry] = []
    skipped: list[str] = []
    for entry in entries:
        try:
            append(stubs_path, entry)
        except DuplicatePathError:
            skipped.append(entry.path)
            continue
        appended.append(entry)
    return RegistrationResult(
        appended=tuple(appended),
        skipped_duplicates=tuple(skipped),
    )
