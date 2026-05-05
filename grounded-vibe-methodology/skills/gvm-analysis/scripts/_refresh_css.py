#!/usr/bin/env python3
"""Developer tool: refresh templates/_css.html.j2 from the upstream Tufte HTML reference.

NOT for end-user invocation. Run by the plugin maintainer to keep the skill's
CSS in sync with gvm-design-system's tufte-html-reference.md.

Usage:
    python3 scripts/_refresh_css.py

Environment:
    GVM_TUFTE_HTML_REFERENCE — override path to the Tufte HTML reference Markdown file.
        Defaults to ~/.claude/skills/gvm-design-system/references/tufte-html-reference.md.

Exit codes:
    0 — _css.html.j2 written successfully.
    1 — reference file not found, no css block found, or write failure.

Post-design-review M-11: provenance comment records source file and sha256 of the
reference document at extraction time, so reviewers can verify the CSS matches
the upstream reference.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_REFERENCE = (
    Path.home() / ".claude/skills/gvm-design-system/references/tufte-html-reference.md"
)

# Regex to extract the first ```css ... ``` block (re.DOTALL so . matches newlines).
_CSS_BLOCK_RE = re.compile(r"```css\n(.*?)\n```", re.DOTALL)

# Relative to the cwd when the script is invoked (project root of the skill).
_OUTPUT_PATH = Path("templates/_css.html.j2")


def _resolve_reference_path() -> Path:
    """Return the path to the Tufte HTML reference, honouring the env-var override."""
    env_override = os.environ.get("GVM_TUFTE_HTML_REFERENCE", "")
    if env_override:
        return Path(env_override)
    return _DEFAULT_REFERENCE


def _extract_css(markdown: str, source_path: Path) -> str:
    """Extract the first ```css block from the markdown.

    Exits with a diagnostic if no block is found.
    """
    match = _CSS_BLOCK_RE.search(markdown)
    if match is None:
        print(
            f"ERROR: No ```css code block found in {source_path}.\n"
            f"The reference file must contain a fenced code block tagged 'css'.",
            file=sys.stderr,
        )
        sys.exit(1)
    return match.group(1)


def _provenance_sha256(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def _render_template(css_content: str, source_filename: str, sha256: str) -> str:
    """Wrap the CSS content in a Jinja2-compatible <style> block with provenance."""
    return (
        f"<!-- Source: {source_filename} (sha256: {sha256}) -->\n"
        f"<style>\n"
        f"{css_content}\n"
        f"</style>\n"
    )


def main() -> None:
    ref_path = _resolve_reference_path()
    if not ref_path.exists():
        print(
            f"ERROR: Reference file not found: {ref_path}\n"
            f"Set GVM_TUFTE_HTML_REFERENCE to override the default path.",
            file=sys.stderr,
        )
        sys.exit(1)
    # Single filesystem read: compute the SHA-256 from the same byte sequence
    # the CSS is extracted from, so a concurrent write cannot produce a
    # provenance hash that disagrees with the extracted content.
    raw_bytes = ref_path.read_bytes()
    raw_content = raw_bytes.decode("utf-8")

    css_content = _extract_css(raw_content, ref_path)
    sha256 = _provenance_sha256(raw_bytes)

    output_content = _render_template(css_content, ref_path.name, sha256)

    output_path = _OUTPUT_PATH
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_content, encoding="utf-8")
    except OSError as exc:
        print(
            f"ERROR: Failed to write {output_path}: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Written: {output_path} (sha256: {sha256[:12]}...)", file=sys.stdout)


if __name__ == "__main__":
    main()
