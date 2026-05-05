#!/usr/bin/env python3
"""Reference template for a project-level `check-stubs.py` audit script.

Ship this with your project (typically as `scripts/check-stubs.py` or
`tools/check-stubs.py`) and run it from CI. It audits the canonical GVM
`STUBS.md` format defined in `_stubs_parser.py`: a Markdown table with the
schema-1 frontmatter and the columns:

    | Path | Reason | Real-provider Plan | Owner | Expiry [| Requirement] |

The `Requirement` column is optional. When present it names the
`requirements.md` ID the stub satisfies (e.g. `GS-2`). Both 5-column and
6-column tables are accepted; mixing the two within a single table is not.

The script is stdlib-only so it works without a Python virtualenv on a
fresh CI runner. It accepts `--repo-root` and `--stubs-md` so the same
template can be invoked from any project layout without forking the
source.

What it checks (per honesty-triad ADR-101 and shared rule 27):

1. Every file under a path that begins with `stubs/` or
   `walking-skeleton/stubs/` has a `STUBS.md` row. (Prefix-based, matches
   `_stubs_parser.PATH_PREFIXES`.)
2. Every registered Path exists on disk.
3. Every Expiry is in the future (today included; expiry day is not yet
   overdue).
4. Every row has the right number of cells and a parseable ISO-8601
   expiry.
5. No duplicate Path entries within `STUBS.md`.

Exit codes: 0 clean / 1 findings / 2 script error.

This script audits stubs ONLY. It does NOT look for or emit "surfaced
requirement" findings — surfaced requirements promote to
`requirements/requirements.md` per shared rule 27, never to `STUBS.md`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

# --- Configuration defaults ---
DEFAULT_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STUBS_MD_NAME = "STUBS.md"
EXCLUDED_NAMES = {"__init__.py"}
EXCLUDED_DIRS = {"__pycache__", ".venv", "node_modules", ".git"}

# Canonical format (matches `_stubs_parser.REQUIRED_COLUMNS`).
REQUIRED_COLUMNS = ["Path", "Reason", "Real-provider Plan", "Owner", "Expiry"]
OPTIONAL_COLUMNS = ["Requirement"]

# Prefix-based path rule (matches `_stubs_parser.PATH_PREFIXES`).
PATH_PREFIXES = ("stubs/", "walking-skeleton/stubs/")

_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


def _strip_frontmatter(text: str) -> str:
    return _FRONTMATTER_RE.sub("", text, count=1)


def _split_table_row(line: str) -> list[str] | None:
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|")):
        return None
    return [c.strip() for c in s[1:-1].split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    return all(c and set(c) <= {"-", ":"} for c in cells)


def _parse_stubs_md(text: str) -> tuple[list[dict], list[str]]:
    """Parse the table. Returns (rows, structural_findings)."""
    body = _strip_frontmatter(text)
    findings: list[str] = []
    rows: list[dict] = []

    header_seen = False
    separator_seen = False
    expected_cells = 0
    for line_no, line in enumerate(body.splitlines(), start=1):
        cells = _split_table_row(line)
        if cells is None:
            continue
        if not header_seen:
            if cells == REQUIRED_COLUMNS:
                header_seen = True
                expected_cells = len(REQUIRED_COLUMNS)
                continue
            if cells == REQUIRED_COLUMNS + OPTIONAL_COLUMNS:
                header_seen = True
                expected_cells = len(REQUIRED_COLUMNS) + len(OPTIONAL_COLUMNS)
                continue
            findings.append(
                f"STUBS.md line {line_no}: expected header "
                f"{REQUIRED_COLUMNS!r} (with optional trailing {OPTIONAL_COLUMNS!r}), "
                f"got {cells!r}"
            )
            return rows, findings
        if not separator_seen:
            if _is_separator_row(cells):
                separator_seen = True
                continue
            findings.append(
                f"STUBS.md line {line_no}: expected separator row after header"
            )
            return rows, findings
        if len(cells) != expected_cells:
            findings.append(
                f"STUBS.md line {line_no}: row has {len(cells)} cells, "
                f"expected {expected_cells}"
            )
            continue
        path, reason, plan, owner, expiry_raw = cells[:5]
        requirement = cells[5] if expected_cells == 6 else ""
        expiry_date: dt.date | None = None
        expiry_parse_error = False
        try:
            expiry_date = dt.date.fromisoformat(expiry_raw) if expiry_raw else None
        except ValueError:
            expiry_parse_error = True
        rows.append(
            {
                "Path": path,
                "Reason": reason,
                "Real-provider Plan": plan,
                "Owner": owner,
                "Expiry": expiry_raw,
                "Requirement": requirement,
                "expiry_raw": expiry_raw,
                "expiry_date": expiry_date,
                "expiry_parse_error": expiry_parse_error,
                "line_no": line_no,
            }
        )

    if not header_seen:
        findings.append("STUBS.md has no recognisable table header")
    elif not separator_seen:
        findings.append("STUBS.md table header found but no '|---|' separator row follows")
    return rows, findings


def _walk_stubs_files(root: Path) -> list[Path]:
    """Files whose repo-relative path starts with a known stubs prefix."""
    found: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel_parts = p.relative_to(root).parts
        if any(d in EXCLUDED_DIRS for d in rel_parts):
            continue
        if p.name in EXCLUDED_NAMES:
            continue
        rel_str = p.relative_to(root).as_posix()
        if not any(rel_str.startswith(prefix) for prefix in PATH_PREFIXES):
            continue
        found.append(p)
    return found


def audit(repo_root: Path, stubs_md: Path, today: dt.date) -> list[str]:
    findings: list[str] = []

    if not stubs_md.exists():
        stub_files = _walk_stubs_files(repo_root)
        if stub_files:
            findings.append(
                f"STUBS.md is missing but {len(stub_files)} stubs/ file(s) exist; "
                f"first: {stub_files[0].relative_to(repo_root)}"
            )
        return findings

    rows, structural = _parse_stubs_md(stubs_md.read_text(encoding="utf-8"))
    findings.extend(structural)

    # Duplicate Path detection (MI-6).
    seen: dict[str, int] = {}
    for r in rows:
        if not r["Path"]:
            continue
        if r["Path"] in seen:
            findings.append(
                f"STUBS.md line {r['line_no']}: duplicate Path "
                f"{r['Path']!r} (also at line {seen[r['Path']]})"
            )
        else:
            seen[r["Path"]] = r["line_no"]

    # (1) every stubs/-prefixed file has a STUBS.md row.
    registered = {r["Path"] for r in rows if r["Path"]}
    for f in _walk_stubs_files(repo_root):
        rel = f.relative_to(repo_root).as_posix()
        if rel not in registered:
            findings.append(f"unregistered: {rel} not listed in STUBS.md")

    # (2) every registered Path exists; (3) Expiry valid and in the future.
    for r in rows:
        if not r["Path"]:
            findings.append(f"STUBS.md line {r['line_no']}: empty Path cell")
        elif not (repo_root / r["Path"]).exists():
            findings.append(
                f"STUBS.md line {r['line_no']}: registered path does not exist: {r['Path']}"
            )

        if not r["expiry_raw"]:
            findings.append(f"STUBS.md line {r['line_no']}: empty Expiry cell")
        elif r["expiry_parse_error"]:
            findings.append(
                f"STUBS.md line {r['line_no']}: invalid expiry {r['expiry_raw']!r} "
                f"(must be ISO-8601 YYYY-MM-DD)"
            )
        elif r["expiry_date"] is not None and r["expiry_date"] < today:
            findings.append(
                f"STUBS.md line {r['line_no']}: expired on "
                f"{r['expiry_date'].isoformat()} (today is {today.isoformat()})"
            )

    return findings


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit a project's STUBS.md against its stubs/ tree.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Project root to walk for stubs/ files (default: script's parent's parent).",
    )
    parser.add_argument(
        "--stubs-md",
        type=Path,
        default=None,
        help="Path to STUBS.md (default: <repo-root>/STUBS.md).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root: Path = args.repo_root.resolve()
    stubs_md: Path = (args.stubs_md or repo_root / DEFAULT_STUBS_MD_NAME).resolve()
    try:
        findings = audit(repo_root, stubs_md, dt.date.today())
    except Exception as exc:  # noqa: BLE001 — script-level catch-all
        print(f"check-stubs: ERROR: {exc}", file=sys.stderr)
        return 2
    if findings:
        for line in findings:
            print(line, file=sys.stderr)
        print(f"check-stubs: {len(findings)} finding(s)", file=sys.stderr)
        return 1
    print("check-stubs: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
