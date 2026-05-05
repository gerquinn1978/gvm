#!/usr/bin/env bash
# PP-3 release-gate: zero hits for "Pass with gaps" and near-variants
# (pipeline-propagation ADR-603).
#
# Usage:  _verify_pp3.sh [scan_dir]
#         scan_dir defaults to ~/.claude/skills/
#
# Reads `.pp3-allowlist` from the current working directory if present.
# Each non-comment, non-blank line is a substring; matching file paths are
# dropped from the hit set before the exit-code decision.

set -euo pipefail

SCAN_DIR="${1:-$HOME/.claude/skills/}"
PATTERN='pass[- ]with[- ]gaps|passing with (caveats|gaps)'
ALLOWLIST=".pp3-allowlist"

# -I: skip binary files; --include limits to source/doc/text artefacts.
raw=$(grep -riEnI \
        --include='*.md' --include='*.html' --include='*.py' \
        --include='*.sh' --include='*.txt' --include='*.json' \
        "$PATTERN" "$SCAN_DIR" 2>/dev/null || true)

if [ -f "$ALLOWLIST" ]; then
    # Build a temp pattern file: drop comments and blanks.
    pattern_file=$(mktemp)
    trap 'rm -f "$pattern_file"' EXIT
    grep -vE '^\s*(#|$)' "$ALLOWLIST" > "$pattern_file" || true
    if [ -s "$pattern_file" ]; then
        filtered=$(echo "$raw" | grep -vFf "$pattern_file" || true)
    else
        filtered=$raw
    fi
else
    filtered=$raw
fi

if [ -n "$filtered" ]; then
    echo "PP-3 FAIL — surviving 'Pass with gaps' variants:" >&2
    echo "$filtered" >&2
    exit 1
fi

echo "PP-3 PASS — zero hits across plugin"
