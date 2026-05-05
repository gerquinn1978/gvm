"""P11-C12 cross-suite isolation conftest.

Two skills can ship same-named private modules (e.g. `_validator.py` in both
`gvm-walking-skeleton/scripts/` and `gvm-impact-map/scripts/`). Under
pytest's default `prepend` import mode, the first-imported wins
`sys.modules["_validator"]` and shadows the second skill's tests. The root
`pytest.ini` sets `--import-mode=importlib` so test files themselves are
imported under unique path-based names; this conftest then handles
test-internal `from _* import` statements by:

  1. At conftest import time, prepending THIS scripts/ at sys.path[0] AND
     evicting any cached `_*` module whose `__file__` lives elsewhere, so
     the test file's collection-time imports resolve locally.
  2. Per test (autouse fixture), re-applying the same guarantee — a sibling
     conftest that was imported between this conftest and this directory's
     tests would otherwise have left another scripts/ at sys.path[0].

Each scripts/ dir owns this same conftest content (DRY by copy — the
file-scoped HERE captures the local directory).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_HERE_STR = str(HERE)
_HERE_PREFIX = _HERE_STR + os.sep
_OWNED = frozenset(p.stem for p in HERE.glob("_*.py") if not p.stem.startswith("__"))


def _isolate() -> None:
    while _HERE_STR in sys.path:
        sys.path.remove(_HERE_STR)
    sys.path.insert(0, _HERE_STR)
    for name in _OWNED:
        cached = sys.modules.get(name)
        if cached is None:
            continue
        # Namespace packages have ``__file__ is None``; the ``or ""`` below
        # coerces that to "", which never starts with _HERE_PREFIX, so any
        # cached _* namespace package is treated as foreign and evicted.
        # No current _* file under any scripts/ dir is a namespace package,
        # so this branch is latent — kept for defensive correctness (R24 M-3).
        cached_file = getattr(cached, "__file__", "") or ""
        if not cached_file.startswith(_HERE_PREFIX):
            del sys.modules[name]


_isolate()


@pytest.fixture(autouse=True)
def _isolate_sibling_modules():
    _isolate()
    yield
