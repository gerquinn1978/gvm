"""HS-4 marker validator (honesty-triad ADR-103).

Asserts that an output's stub marker is consistent with the caller-supplied
``stub_active`` flag. Three formats:

* ``html``: ``data-stub-active`` attribute on a ``<main>`` element.
* ``json``: top-level ``"_stub_active": true``.
* ``cli``: stderr line containing ``STUB ACTIVE`` or ``[stub data]``.

The validator is an assertion tool, not a scanner — it doesn't try to decide
whether a code path "is" stub-active. The caller (the rendering layer that
already imported from ``stubs/``) computes the boolean and passes it in.
"""

from __future__ import annotations

import json
import re
from typing import Literal

_HTML_MAIN_WITH_MARKER = re.compile(r"<main\b[^>]*\bdata-stub-active\b", re.IGNORECASE)


class HS4MarkerError(AssertionError):
    """Raised when output marker presence does not match `stub_active`."""


def _html_marker_present(output: str) -> bool:
    return bool(_HTML_MAIN_WITH_MARKER.search(output))


def _json_marker_present(output: str | dict) -> bool:
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except json.JSONDecodeError:
            return False
    if not isinstance(output, dict):
        return False
    return output.get("_stub_active") is True


def _cli_marker_present(output: str) -> bool:
    return "STUB ACTIVE" in output or "[stub data]" in output


def assert_marker_consistent(
    output: str | dict,
    stub_active: bool,
    format: Literal["html", "json", "cli"],
) -> None:
    """Assert the HS-4 marker is present iff ``stub_active`` is True.

    Raises :class:`HS4MarkerError` on mismatch, :class:`ValueError` on an
    unknown format.
    """

    if format == "html":
        if not isinstance(output, str):
            raise ValueError("HTML format requires str output")
        present = _html_marker_present(output)
    elif format == "json":
        present = _json_marker_present(output)
    elif format == "cli":
        if not isinstance(output, str):
            raise ValueError("CLI format requires str output")
        present = _cli_marker_present(output)
    else:
        raise ValueError(
            f"unknown format: {format!r} (expected 'html' | 'json' | 'cli')"
        )

    if stub_active and not present:
        raise HS4MarkerError(
            f"HS-4 marker missing for stub-active output (format={format})"
        )
    if not stub_active and present:
        raise HS4MarkerError(
            f"HS-4 marker present on non-stub output (format={format})"
        )
