"""Pytest bootstrap for the /gvm-analysis skill.

Two imports must work in tests (per cross-cutting ADR-007 and P1-C01):

  - ``import gvm_analysis``        → satisfied by a package marker at the skill
    root on ``sys.path``.
  - ``from _shared import constants`` → satisfied by putting ``scripts/`` on
    ``sys.path`` so ``_shared`` is importable without a ``scripts.`` prefix.

This conftest resolves both by prepending the skill root and the ``scripts/``
directory to ``sys.path``. Tests stay free of path hacks; this file holds the
one-time wiring in a single obvious location.
"""

from __future__ import annotations

import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_ROOT / "scripts"

for candidate in (str(SKILL_ROOT), str(SCRIPTS_DIR)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)
