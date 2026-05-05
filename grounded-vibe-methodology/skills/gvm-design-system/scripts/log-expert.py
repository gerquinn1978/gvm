#!/usr/bin/env python3
"""
log-expert.py — append a row to the expert activation CSV.

Used by shared rule 1. Invoking this script replaces having the model
generate CSV rows inline, which saves tokens on every skill invocation.

Cross-platform: runs on macOS, Linux, and Windows. Requires only the
Python 3 standard library.

Usage:
    python3 log-expert.py <skill> <phase> <expert> <work> \\
        <classification> <tier> <event>

Example:
    python3 log-expert.py /gvm-requirements elicitation "Karl Wiegers" \\
        "Software Requirements (3rd ed.)" Canonical tier1 loaded

Fields:
    skill           e.g. /gvm-requirements, /gvm-doc-review
    phase           e.g. elicitation, scoring, review
    expert          Author/expert name
    work            Primary work cited (book, paper, etc.)
    classification  Canonical | Established | Recognised | Emerging | Provisional | unscored
                    (closed set from expert-scoring.md; unscored is a
                    lifecycle sentinel used before a score is assigned)
    tier            tier1 | tier2a | tier2b | tier3 | discovered
    event           loaded | cited

The timestamp and project path are filled in automatically. The CSV file
is created with a header row if it does not exist.
"""

import csv
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HEADER = [
    "timestamp",
    "project",
    "skill",
    "phase",
    "expert",
    "work",
    "classification",
    "tier",
    "event",
]

HEADER_LINE_QUOTED = (
    '"timestamp","project","skill","phase","expert","work",'
    '"classification","tier","event"'
)
HEADER_LINE_UNQUOTED = (
    "timestamp,project,skill,phase,expert,work,classification,tier,event"
)


def _self_heal_header(csv_path: Path) -> None:
    """Defensive self-heal: ensure the file has a valid header.

    Three cases:

    a) File does not exist -> no-op (the open("a+") below will create it
       and the tell()==0 check will write the header on first append).
    b) File exists, first line is the canonical header -> no-op.
    c) File exists but first line is NOT the canonical header -> atomically
       prepend the header. This handles the failure mode where another
       script clobbers the file with `>` and writes raw rows without a
       header (the previous shell-snippet bootstrap was vulnerable to this
       via copy-paste of its right-hand side).

    Atomic prepend: write to a sibling temp file in the same directory,
    then os.replace(). os.replace is atomic for same-volume renames; the
    temp lives next to the CSV so the precondition is guaranteed.

    On any I/O failure, this function silently returns. The original file
    is intact; the worst case is the header remains missing this run and
    the next call tries again.
    """
    if not csv_path.exists():
        return  # Case (a) -- handled by the open("a+") path below.

    try:
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            first_line = f.readline()
    except OSError:
        return  # If unreadable, let the append path raise its own error.

    stripped = first_line.rstrip()
    if stripped == HEADER_LINE_QUOTED or stripped == HEADER_LINE_UNQUOTED:
        return  # Case (b) -- header already present.

    # Case (c) -- prepend the header atomically.
    try:
        with csv_path.open("rb") as src:
            existing = src.read()

        fd, tmp_name = tempfile.mkstemp(
            prefix=".expert-activations.",
            suffix=".tmp",
            dir=str(csv_path.parent),
        )
        try:
            with os.fdopen(fd, "wb") as out:
                out.write((HEADER_LINE_QUOTED + "\n").encode("utf-8"))
                out.write(existing)
            os.replace(tmp_name, csv_path)
        except OSError:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
    except OSError:
        pass


VALID_CLASSIFICATIONS = {
    "Canonical",
    "Established",
    "Recognised",
    "Emerging",
    "Provisional",
    "unscored",
}
VALID_TIERS = {"tier1", "tier2a", "tier2b", "tier3", "discovered"}
VALID_EVENTS = {"loaded", "cited"}


def main() -> int:
    if len(sys.argv) != 8:
        print(
            "Usage: log-expert.py <skill> <phase> <expert> <work> "
            "<classification> <tier> <event>",
            file=sys.stderr,
        )
        print(f"Got {len(sys.argv) - 1} arguments.", file=sys.stderr)
        return 2

    skill, phase, expert, work, classification, tier, event = sys.argv[1:8]

    if classification not in VALID_CLASSIFICATIONS:
        print(
            f"log-expert: invalid classification '{classification}'. "
            f"Expected one of: {sorted(VALID_CLASSIFICATIONS)}",
            file=sys.stderr,
        )
        return 2
    if tier not in VALID_TIERS:
        print(
            f"log-expert: invalid tier '{tier}'. "
            f"Expected one of: {sorted(VALID_TIERS)}",
            file=sys.stderr,
        )
        return 2
    if event not in VALID_EVENTS:
        print(
            f"log-expert: invalid event '{event}'. "
            f"Expected one of: {sorted(VALID_EVENTS)}",
            file=sys.stderr,
        )
        return 2

    csv_path = Path.home() / ".claude" / "gvm" / "expert-activations.csv"

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    project = os.getcwd()

    row = [
        timestamp,
        project,
        skill,
        phase,
        expert,
        work,
        classification,
        tier,
        event,
    ]

    try:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        # Defensive self-heal: if the file exists but lacks the canonical
        # header (e.g., another script clobbered it with `>`), atomically
        # prepend the header before we append. Existing rows are preserved.
        _self_heal_header(csv_path)
        # Open once in append-read mode, then check position after seeking
        # to end. f.tell() == 0 means the file is brand new (or was just
        # created by this open call). This avoids the TOCTOU race between
        # exists() and open(); two concurrent first-runs will not both
        # write the header because only the first open that created the
        # file sees tell() == 0. newline="" is required on Windows so the
        # csv module does not emit blank lines.
        with csv_path.open("a+", newline="", encoding="utf-8") as f:
            f.seek(0, 2)  # seek to end
            needs_header = f.tell() == 0
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            if needs_header:
                writer.writerow(HEADER)
            writer.writerow(row)
    except OSError as e:
        print(f"log-expert: cannot write to {csv_path}: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
