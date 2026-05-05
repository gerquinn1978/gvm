"""HS-1 chunk-handover gate (honesty-triad ADR-101).

A pure function that the `/gvm-build` SKILL.md handover writer calls immediately
before writing `build/handovers/P{X}-C{XX}.md`. It accepts the chunk's explicit
file list (assembled from the handover template's "Files Created" + "Files
Modified" sections) and the path to the project's `STUBS.md`. For every file
under a stub namespace (`stubs/` or `walking-skeleton/stubs/`) without a
matching `STUBS.md` registration, an `UnregisteredStubError` is returned. An
empty list = pass; a non-empty list = handover refused.

Per ADR-101 (file-list mechanism, F-CRIT-4): this script does NOT invoke `git`,
does NOT read the working tree, and does NOT probe the file list on disk. Its
sole disk read is `stubs_path`. A missing `stubs_path` is interpreted as "no
registrations" so any stub-namespaced file in `files` becomes unregistered.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

# `_stubs_parser` lives in the gvm-design-system skill. Insert its scripts dir
# on sys.path so this module imports cleanly when invoked from any cwd. Mirrors
# the established pattern in `_sd5_promotion.py`.
_DS_SCRIPTS = Path(__file__).resolve().parents[2] / "gvm-design-system" / "scripts"
if str(_DS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_DS_SCRIPTS))

from _stubs_parser import PATH_PREFIXES, load_stubs  # noqa: E402


@dataclass(frozen=True)
class UnregisteredStubError:
    path: str


def _is_stub_namespaced(file: str) -> bool:
    return any(file.startswith(prefix) for prefix in PATH_PREFIXES)


def _registered_paths(stubs_path: Path) -> set[str]:
    if not stubs_path.exists():
        return set()
    return {entry.path for entry in load_stubs(stubs_path)}


def check(files: Iterable[str], stubs_path: Path) -> list[UnregisteredStubError]:
    """Return one `UnregisteredStubError` per stub-namespaced file in `files`
    that is not registered in `STUBS.md` at `stubs_path`.

    Empty list = pass (handover may proceed). Non-empty = handover refused.
    Files outside the stub namespace are ignored. A missing `stubs_path` is
    treated as an empty registry. The function never probes the file list on
    disk and never invokes any subprocess.
    """

    registered = _registered_paths(stubs_path)
    return [
        UnregisteredStubError(path=f)
        for f in files
        if _is_stub_namespaced(f) and f not in registered
    ]
