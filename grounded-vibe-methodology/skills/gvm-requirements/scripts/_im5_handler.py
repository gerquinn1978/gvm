"""IM-5 mid-flight handler for `/gvm-requirements` (discovery ADR-305).

Detects practitioner intent to extend the impact-map mid-elicitation, then
appends rows + a Changelog entry **atomically**: write to ``.tmp``, validate
by re-loading, then ``os.replace`` over the original. On any failure (parse,
validation, I/O) the original file is left byte-identical and ``.tmp`` is
removed; the caller receives ``AppendResult(success=False, ...)`` and never
sees a raised exception.

The classifier is intentionally liberal — false positives are caught by the
``AskUserQuestion`` confirmation step described in ADR-305.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, replace
from datetime import date as _date
from pathlib import Path

# _impact_map_parser lives in gvm-design-system/scripts/. Insert that path so
# this skill-internal module can import it without a packaged install.
_GDS = Path(__file__).resolve().parents[2] / "gvm-design-system" / "scripts"
if str(_GDS) not in sys.path:
    sys.path.insert(0, str(_GDS))

from _impact_map_parser import (  # noqa: E402
    Actor,
    ChangelogEntry,
    Deliverable,
    Impact,
    ImpactMap,
    load_impact_map,
    serialise,
)


# --- Public dataclasses -----------------------------------------------------


@dataclass(frozen=True)
class Intent:
    action: str  # "add_impact" | "add_actor" | "add_deliverable"
    raw_text: str


@dataclass(frozen=True)
class AppendResult:
    success: bool
    error: str | None


# --- Intent classifier ------------------------------------------------------

# Trigger verb adjacent to the artefact noun. Keeps "the impact of this
# change is huge" from matching, while accepting all phrasings listed in
# ADR-305.
_TRIGGER_VERBS = r"add|new|missed|another"

_PATTERNS = {
    "add_impact": re.compile(
        rf"\b(?:{_TRIGGER_VERBS})\b[^.\n]{{0,40}}\bimpact\b", re.IGNORECASE
    ),
    "add_actor": re.compile(
        rf"\b(?:{_TRIGGER_VERBS})\b[^.\n]{{0,40}}\bactor\b", re.IGNORECASE
    ),
    "add_deliverable": re.compile(
        rf"\b(?:{_TRIGGER_VERBS})\b[^.\n]{{0,40}}\bdeliverable\b", re.IGNORECASE
    ),
}


def classify_intent(text: str) -> Intent | None:
    """Return an Intent if the text matches a mid-flight action trigger.

    The classifier is liberal by design — the caller MUST present an
    AskUserQuestion confirmation before any write. False positives are
    expected and intended to be caught at confirmation time.
    """
    if not text:
        return None
    for action, pattern in _PATTERNS.items():
        if pattern.search(text):
            return Intent(action=action, raw_text=text)
    return None


# --- Atomic append helpers --------------------------------------------------


def _today_iso(today: _date | None) -> str:
    return (today or _date.today()).isoformat()


def _atomic_write_and_validate(map_path: Path, new_im: ImpactMap) -> AppendResult:
    """Serialise ``new_im``, write to ``.tmp``, re-load to validate, rename.

    On any failure: discard the ``.tmp`` (best-effort) and return
    ``AppendResult(success=False, error=...)``. The original file is never
    touched on the failure path.
    """
    tmp_path = map_path.with_suffix(map_path.suffix + ".tmp")
    try:
        rendered = serialise(new_im)
        # Parent directory must exist — write_text raises FileNotFoundError otherwise.
        tmp_path.write_text(rendered, encoding="utf-8")
        # Round-trip validation: re-loading invokes referential-integrity
        # checks. If the new state is internally inconsistent, this raises.
        load_impact_map(tmp_path)
        os.replace(tmp_path, map_path)
        return AppendResult(success=True, error=None)
    except Exception as exc:  # noqa: BLE001 — must NEVER raise to caller.
        # Best-effort tmp cleanup. FileNotFoundError is the common case
        # (write_text failed before the file was created). Other OSErrors
        # (permission, FS full) are suppressed because surfacing them here
        # would mask the original `exc` that the caller actually needs to
        # see. A stale .tmp left on disk is recoverable; a swallowed root
        # cause is not.
        try:
            tmp_path.unlink()
        except (FileNotFoundError, OSError):
            pass
        return AppendResult(success=False, error=str(exc))


def append_impact(
    map_path: str | os.PathLike[str],
    impact: Impact,
    *,
    change_summary: str,
    today: _date | None = None,
) -> AppendResult:
    """Append ``impact`` and a Changelog entry to ``map_path`` atomically."""
    p = Path(map_path)
    try:
        im = load_impact_map(p)
    except Exception as exc:  # noqa: BLE001
        return AppendResult(success=False, error=str(exc))
    new_im = replace(
        im,
        impacts=im.impacts + (impact,),
        changelog=im.changelog
        + (
            ChangelogEntry(
                date=_today_iso(today),
                change=change_summary,
                rationale="Mid-flight addition (IM-5)",
            ),
        ),
    )
    return _atomic_write_and_validate(p, new_im)


def append_actor(
    map_path: str | os.PathLike[str],
    actor: Actor,
    *,
    change_summary: str,
    today: _date | None = None,
) -> AppendResult:
    """Append ``actor`` and a Changelog entry to ``map_path`` atomically."""
    p = Path(map_path)
    try:
        im = load_impact_map(p)
    except Exception as exc:  # noqa: BLE001
        return AppendResult(success=False, error=str(exc))
    new_im = replace(
        im,
        actors=im.actors + (actor,),
        changelog=im.changelog
        + (
            ChangelogEntry(
                date=_today_iso(today),
                change=change_summary,
                rationale="Mid-flight addition (IM-5)",
            ),
        ),
    )
    return _atomic_write_and_validate(p, new_im)


def append_deliverable(
    map_path: str | os.PathLike[str],
    deliverable: Deliverable,
    *,
    change_summary: str,
    today: _date | None = None,
) -> AppendResult:
    """Append ``deliverable`` and a Changelog entry to ``map_path`` atomically."""
    p = Path(map_path)
    try:
        im = load_impact_map(p)
    except Exception as exc:  # noqa: BLE001
        return AppendResult(success=False, error=str(exc))
    new_im = replace(
        im,
        deliverables=im.deliverables + (deliverable,),
        changelog=im.changelog
        + (
            ChangelogEntry(
                date=_today_iso(today),
                change=change_summary,
                rationale="Mid-flight addition (IM-5)",
            ),
        ),
    )
    return _atomic_write_and_validate(p, new_im)
