"""HS-2 expiry CI helper (cross-cutting ADR-008).

A single helper with two entry points:

* :func:`run` — pure function returning ``(exit_code, stderr_message)``.
  Called by the skill's own Hard Gate code path.
* ``__main__`` — CLI shim that prints the message to stderr and exits with
  the code. Invoked by CI (e.g. GitHub Actions ``stubs-expiry-check``).

Boundary: ``today == expiry`` is NOT expired (strict ``<`` per
``_stubs_parser.check_expiry``). Missing ``STUBS.md`` and parse errors both
exit non-zero with a readable message — never a stack trace.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

from _stubs_parser import StubsParseError, check_expiry, load_stubs


def _today() -> dt.date:
    return dt.date.today()


def run(stubs_path: Path, today: dt.date | None = None) -> tuple[int, str]:
    """Return ``(exit_code, stderr_message)``.

    * 0 / empty message — no expired stubs.
    * 1 / non-empty message — expired stubs, missing file, or parse error.
    """

    when = today if today is not None else _today()

    if not stubs_path.exists():
        return 1, f"STUBS.md not found at {stubs_path}"

    try:
        stubs = load_stubs(stubs_path)
    except StubsParseError as exc:
        return 1, f"STUBS.md parse error: {exc}"

    expired = check_expiry(stubs, when)
    if not expired:
        return 0, ""

    lines = ["Expired stubs (today > expiry):"]
    lines.extend(f"  {e.path} — expired {e.expiry.isoformat()}" for e in expired)
    return 1, "\n".join(lines)


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("STUBS.md")
    code, msg = run(path)
    if msg:
        print(msg, file=sys.stderr)
    sys.exit(code)


if __name__ == "__main__":
    main()
