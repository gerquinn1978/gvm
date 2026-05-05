"""Phase-1 exit criterion — end-to-end analyse.py → render_report.py chain.

From implementation-guide.md line 170:

    python3 scripts/analyse.py --input fixtures/tiny.csv \\
        --output-dir /tmp/test --seed 42 &&
    python3 scripts/render_report.py --findings /tmp/test/findings.json \\
        --out /tmp/test

produces an HTML hub with the attribution footer. If this test passes, the
walking skeleton is proven end-to-end.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import html5lib

SKILL_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "tiny.csv"

ATTRIBUTION_TEXT: str = "Developed using the Grounded Vibe Methodology"


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=SKILL_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_phase1_exit_criterion_produces_hub_with_attribution(
    tmp_path: Path,
) -> None:
    """analyse.py → render_report.py chain produces report.html with the
    GVM attribution as the last child of <main>."""
    assert FIXTURE.exists(), f"fixture missing: {FIXTURE}"

    out_dir = tmp_path / "out"

    analyse = _run(
        [
            sys.executable,
            "scripts/analyse.py",
            "--input",
            str(FIXTURE),
            "--output-dir",
            str(out_dir),
            "--seed",
            "42",
        ]
    )
    assert analyse.returncode == 0, f"analyse.py failed; stderr:\n{analyse.stderr}"
    findings_path = out_dir / "findings.json"
    assert findings_path.exists(), "analyse.py did not write findings.json"

    render = _run(
        [
            sys.executable,
            "scripts/render_report.py",
            "--findings",
            str(findings_path),
            "--out",
            str(out_dir),
        ]
    )
    assert render.returncode == 0, f"render_report.py failed; stderr:\n{render.stderr}"

    report = out_dir / "report.html"
    assert report.exists(), "render_report.py did not write report.html"

    html = report.read_text(encoding="utf-8")
    assert html.lstrip().startswith("<!DOCTYPE html>")

    tree = html5lib.parse(html, treebuilder="etree", namespaceHTMLElements=False)
    main = tree.find(".//main")
    assert main is not None
    last = list(main)[-1]
    assert last.tag == "p"
    assert "gvm-attribution" in (last.get("class") or "").split()
    assert (last.text or "").strip() == ATTRIBUTION_TEXT
