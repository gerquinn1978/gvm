"""Shared parser for the inline impact-deliverable source tag (discovery ADR-304).

A requirement line in `requirements.md` carries the tag in the form::

    **RE-N (Must) [impact-deliverable: D-3, D-7]:** the system shall ...

Both ``_im4_check.py`` (`/gvm-requirements` Phase 5 gate) and
``_trace_resolver.py`` (`/gvm-test-cases` test-tag emitter) call
:func:`parse_impact_deliverable_tag` so the two skills cannot diverge.

Public surface: :func:`parse_impact_deliverable_tag`.
"""

from __future__ import annotations

import re

TAG_RE = re.compile(r"\[impact-deliverable:\s*([D]-\d+(?:\s*,\s*[D]-\d+)*)\s*\]")


def parse_impact_deliverable_tag(line: str) -> list[str]:
    """Return the list of deliverable IDs (e.g. ``["D-3", "D-7"]``) from *line*.

    Returns an empty list when no tag is present, when the tag is empty
    (``[impact-deliverable: ]``), or when the inner text does not match the
    ``D-<digits>`` shape. Only the first tag on a line is recognised.
    """
    m = TAG_RE.search(line)
    if m is None:
        return []
    inner = m.group(1)
    return [part.strip() for part in inner.split(",")]
