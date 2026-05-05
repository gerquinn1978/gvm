"""VV-4(a) feeder — parses the Panel-E NDJSON sidecar.

Reads `code-review/code-review-NNN.findings.json` (NDJSON, one
`PanelEFinding` per line per honesty-triad ADR-104) and returns a verdict
tuple consumed by `gvm_verdict.evaluate` via `VerdictInputs.vv4_a`.

Decision rules:
  - Empty file (zero bytes) — PASS, evidence "no Panel E findings recorded".
  - Any line with `severity == "Critical"` — FAIL with the count.
  - All findings non-Critical — PASS.

Caller is responsible for handling the missing-file case: if no
`code-review-NNN.findings.json` exists, the caller passes
`("NA", "no code-review report")` directly to `VerdictInputs.vv4_a`
without invoking this module (per gvm-test SKILL.md step 8).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

CriterionStatus = Literal["PASS", "FAIL", "NA"]


def load(path: Path) -> tuple[CriterionStatus, str]:
    """Return ``(status, evidence)`` for VV-4(a) from the NDJSON sidecar.

    PASS if no Critical-severity findings; FAIL otherwise. Empty file is
    treated as PASS (zero findings).
    """

    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return ("PASS", "no Panel E findings recorded")

    total = 0
    critical = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        total += 1
        if record.get("severity") == "Critical":
            critical += 1

    if critical > 0:
        return (
            "FAIL",
            f"{critical} Critical Panel E finding(s) of {total} total in {path.name}",
        )
    return ("PASS", f"{total} Panel E finding(s) in {path.name}, 0 Critical")
