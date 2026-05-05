# Source: gvm_stubs v1.0 (sha256: PLUGIN_SOURCE)
"""HS-3 startup loader (honesty-triad ADR-102).

Provides :func:`warn_if_active` — emits ``STUB ACTIVE: <name> — expires <date>``
to stderr for every registered, non-expired entry in ``STUBS.md``. Each
entry-point script in a project that has wired honesty-triad calls this at
``__main__`` start.

Boundary semantics: an entry is *active* while ``today <= expiry`` (the strict
``<`` in :func:`_stubs_parser.check_expiry` defines "expired"; everything
that is not expired is still active, including the expiry day itself).

Output goes directly to ``sys.stderr`` (or an injected stream) — NOT through
``warnings`` or ``logging``. Per TC-HS-3-04 the warning is unconditional and
must not be suppressible by ``STUB_WARNINGS``, ``NO_WARNINGS``, or
``PYTHONWARNINGS``.

The provenance header line above (``# Source: gvm_stubs vN.M (sha256: ...)``)
is the contract surface for ``/gvm-build``'s drift-detection step. When this
file is copied into a project as ``gvm_stubs/__init__.py``, the placeholder
``PLUGIN_SOURCE`` is replaced with the SHA-256 of the source at copy time.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TextIO
import datetime as dt

from _stubs_parser import load_stubs


def _today() -> dt.date:
    return dt.date.today()


def warn_if_active(
    stubs_path: Path | None = None,
    today: dt.date | None = None,
    stream: TextIO | None = None,
) -> int:
    """Emit a `STUB ACTIVE` line for each registered, non-expired entry.

    Returns the count of warnings written. Silent (returns 0) on missing
    ``STUBS.md`` or any parse error — the runtime helper must never raise.
    """

    path = stubs_path if stubs_path is not None else Path("STUBS.md")
    when = today if today is not None else _today()
    out = stream if stream is not None else sys.stderr

    if not path.exists():
        return 0

    try:
        entries = load_stubs(path)
    except Exception:  # pragma: no cover - defensive: parsing surfaces elsewhere
        return 0

    count = 0
    for entry in entries:
        if when > entry.expiry:
            continue
        name = Path(entry.path).stem
        out.write(f"STUB ACTIVE: {name} — expires {entry.expiry.isoformat()}\n")
        count += 1
    return count
