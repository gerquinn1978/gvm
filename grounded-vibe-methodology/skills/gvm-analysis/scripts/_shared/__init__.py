"""Internal modules shared across the analysis and render scripts.

Per cross-cutting ADR-007, ``_shared`` is placed under ``scripts/`` so scripts
can ``from _shared import …`` once ``scripts/`` is on ``sys.path``. Tests get
that wiring via ``tests/conftest.py``.
"""

from __future__ import annotations
