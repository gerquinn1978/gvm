"""Subprocess smoke for `scripts/analyse.py` — covers TC-AN-4-02.

The engine must be invocable as a Python subprocess via bash. At P1-C03 we
do not yet exercise "reads the data file directly from disk" — file loading
arrives in P2-C01 — so this test only verifies the subprocess boundary and
the exit contract.

**Relative script path rationale (A-5 review note):** Python inserts the
script's parent directory (``scripts/``) into ``sys.path[0]`` automatically
when a ``.py`` file is executed directly, which is why
``from _shared import findings`` resolves inside the subprocess. If a
future refactor switches to ``python3 -m analyse`` invocation, that
mechanism goes away and ``conftest.py``-equivalent path wiring must be
reinstated for the subprocess. Until then, ``cwd=SKILL_ROOT`` + relative
script path is the simplest working invocation.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "tiny.csv"


def test_analyse_subprocess_smoke(tmp_path: Path) -> None:
    """python3 scripts/analyse.py invoked via subprocess produces
    findings.json and exits 0 (TC-AN-4-02)."""
    assert FIXTURE.exists(), f"test fixture missing: {FIXTURE}"
    out = tmp_path / "out"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/analyse.py",
            "--input",
            str(FIXTURE),
            "--output-dir",
            str(out),
            "--seed",
            "42",
        ],
        cwd=SKILL_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, (
        f"analyse.py exited {result.returncode}; stderr:\n{result.stderr}"
    )

    findings_path = out / "findings.json"
    assert findings_path.exists(), "findings.json was not written"

    data = json.loads(findings_path.read_text(encoding="utf-8"))
    # Use the canonical constant rather than a literal so a schema bump
    # cannot silently regress this assertion.
    from _shared import findings as _findings

    assert data["schema_version"] == _findings.CURRENT_SCHEMA_VERSION
    assert len(data["comprehension_questions"]) == 3
