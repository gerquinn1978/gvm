"""Session-report writer for `/gvm-explore-test` (P11-C08).

Renders a paired `test/explore-NNN.md` and `test/explore-NNN.html`
artefact from a `Charter` (P11-C06) + `IntakeSession` (P11-C07) +
session log + overall assessment. ET-4 mandates five H2 sections in
fixed order:
  Charter / Session Log / Defects / Observations / Overall Assessment

Atomic write per ADR-204 — temp files in the same directory then
`os.replace`. HTML escape applied at render time (TC-ET-3-03 [SECURITY])
on every practitioner-supplied string. The MD output preserves raw
practitioner payload because `/gvm-test`'s `_explore_parser` reads the
practitioner's authoritative classification from there — not an HTML
rendering target.
"""

from __future__ import annotations

import html
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# Same-directory sibling imports require this directory on sys.path. Tests
# rely on conftest.py to inject it; production callers (SKILL.md flows) may
# import from a different working directory. Self-injection makes the
# module robust to both (R24 CR-2).
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _charter import Charter  # noqa: E402
from _defect_intake import DefectEntry, IntakeSession, ObservationEntry  # noqa: E402


class ReportError(Exception):
    """Validation failure during report write."""

    def __init__(self, field: str, reason: str) -> None:
        super().__init__(f"report field {field!r}: {reason}")
        self.field = field
        self.reason = reason


@dataclass(frozen=True)
class _ReportModel:
    """Shared content model — md and html renderers consume this, so the
    iteration logic lives in one place (Hunt & Thomas: DRY)."""

    nnn: str
    charter: Charter
    session_log: tuple[str, ...]
    defects: tuple[DefectEntry, ...]
    observations: tuple[ObservationEntry, ...]
    assessment: str


def write_report(
    charter: Charter,
    session: IntakeSession,
    session_log: Iterable[str],
    assessment: str,
    output_dir: Path,
) -> tuple[Path, Path]:
    """Write paired `explore-NNN.md` and `explore-NNN.html` atomically.
    Returns `(md_path, html_path)` — md first."""
    nnn = _extract_nnn(charter, session)
    output_dir.mkdir(parents=True, exist_ok=True)

    model = _ReportModel(
        nnn=nnn,
        charter=charter,
        session_log=tuple(session_log),
        defects=session.defects,
        observations=session.observations,
        assessment=assessment,
    )

    md_path = output_dir / f"explore-{nnn}.md"
    html_path = output_dir / f"explore-{nnn}.html"
    _atomic_write(md_path, _render_md(model))
    _atomic_write(html_path, _render_html(model))
    return md_path, html_path


# ----------------------------------------------------------------- helpers


def _extract_nnn(charter: Charter, session: IntakeSession) -> str:
    # charter.session_id is "explore-NNN" by construction (P11-C06 validates it)
    suffix = charter.session_id.split("-", 1)[-1]
    if suffix != session.session_nnn:
        raise ReportError(
            "session_nnn",
            f"charter session_id {charter.session_id!r} does not match "
            f"session.session_nnn {session.session_nnn!r}",
        )
    return suffix


def _atomic_write(path: Path, body: str) -> None:
    fd, tmp_path = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(body)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ----------------------------------------------------------------- markdown render


def _md_title(text: str, fallback: str) -> str:
    """Pick a single-line H3 title from a possibly multi-line free-form
    field. The parser's `### D-N: <title>` regex requires a non-empty title;
    `then` is the practitioner's authoritative outcome statement, so use its
    first non-empty line truncated to 80 chars. Fall back to `fallback`
    (typically the id) if `then` is empty.
    """
    for raw in text.splitlines():
        s = raw.strip()
        if s:
            return s[:80]
    return fallback


def _yaml_scalar(value: object) -> str:
    """Render a scalar for the parser's `_parse_scalar_yaml` reader (which
    accepts unquoted strings and ints). Quote only when the value contains
    a colon or a leading/trailing space. Newlines are not allowed in
    scalars — the writer's inputs (charter fields) are validated single-line
    by `_charter.load`, so we don't expect newlines here."""
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    s = str(value)
    if not s:
        return '""'
    if ":" in s or s != s.strip() or s.startswith(("'", '"')):
        # Use double quotes; escape any embedded double-quote.
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def _render_md(m: _ReportModel) -> str:
    """Render the session report in the format `_explore_parser.load_explore`
    consumes: YAML frontmatter, fenced YAML charter block, defect/observation
    blocks with `### {id}: <title>` headings and `**Label:**` field lines
    without leading bullet dashes.
    """
    c = m.charter
    lines: list[str] = [
        "---",
        "schema_version: 1",
        "---",
        "",
        f"# Exploratory Session — explore-{m.nnn}",
        "",
        "## Charter",
        "",
        "```yaml",
        f"schema_version: {c.schema_version}",
        f"session_id: {_yaml_scalar(c.session_id)}",
        f"mission: {_yaml_scalar(c.mission)}",
        f"timebox_minutes: {c.timebox_minutes}",
        f"tour: {_yaml_scalar(c.tour)}",
        f"runner: {_yaml_scalar(c.runner)}",
        "```",
        "",
        "**Target:**",
        "",
    ]
    for t in c.target:
        lines.append(f"- {t}")
    lines.extend(["", "## Session Log", ""])
    if not m.session_log:
        lines.append("_No log entries recorded._")
    else:
        for entry in m.session_log:
            lines.append(f"- {entry}")
    lines.extend(["", "## Defects", ""])
    if not m.defects:
        lines.append("_None recorded._")
    else:
        for d in m.defects:
            title = _md_title(d.then, fallback=d.id)
            lines.extend(
                [
                    f"### {d.id}: {title}",
                    "",
                    f"**Severity:** {d.severity}",
                    f"**Tour:** {c.tour}",
                    f"**Given:** {d.given}",
                    f"**When:** {d.when}",
                    f"**Then:** {d.then}",
                    f"**Reproduction:** {d.reproduction}",
                    f"**Stub-path:** {d.stub_path or ''}",
                    "",
                ]
            )
    lines.extend(["", "## Observations", ""])
    if not m.observations:
        lines.append("_None recorded._")
    else:
        for o in m.observations:
            title = _md_title(o.then, fallback=o.id)
            lines.extend(
                [
                    f"### {o.id}: {title}",
                    "",
                    f"**Tour:** {c.tour}",
                    f"**Given:** {o.given}",
                    f"**When:** {o.when}",
                    f"**Then:** {o.then}",
                    f"**Stub-path:** {o.stub_path or ''}",
                    "",
                ]
            )
    lines.extend(["", "## Overall Assessment", "", m.assessment])
    return "\n".join(lines).rstrip() + "\n"


# ----------------------------------------------------------------- html render


def _e(s: str) -> str:
    """html.escape with quote=True — single source of escape for the
    HTML renderer (TC-ET-3-03)."""
    return html.escape(s, quote=True)


def _render_html(m: _ReportModel) -> str:
    c = m.charter
    parts: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        f"<title>Exploratory Session — explore-{_e(m.nnn)}</title>",
        "</head>",
        "<body>",
        f"<h1>Exploratory Session — explore-{_e(m.nnn)}</h1>",
        "<h2>Charter</h2>",
        "<ul>",
        f"<li><strong>Session ID:</strong> {_e(c.session_id)}</li>",
        f"<li><strong>Mission:</strong> {_e(c.mission)}</li>",
        f"<li><strong>Tour:</strong> {_e(c.tour)}</li>",
        f"<li><strong>Timebox (minutes):</strong> {c.timebox_minutes}</li>",
        f"<li><strong>Runner:</strong> {_e(c.runner)}</li>",
        "<li><strong>Target:</strong><ul>",
    ]
    for t in c.target:
        parts.append(f"<li>{_e(t)}</li>")
    parts.append("</ul></li></ul>")

    parts.append("<h2>Session Log</h2>")
    if not m.session_log:
        parts.append("<p><em>No log entries recorded.</em></p>")
    else:
        parts.append("<ul>")
        for entry in m.session_log:
            parts.append(f"<li>{_e(entry)}</li>")
        parts.append("</ul>")

    parts.append("<h2>Defects</h2>")
    if not m.defects:
        parts.append("<p><em>None recorded.</em></p>")
    else:
        for d in m.defects:
            parts.extend(
                [
                    f"<h3>{_e(d.id)} — {_e(d.severity)}</h3>",
                    "<ul>",
                    f"<li><strong>Given:</strong> {_e(d.given)}</li>",
                    f"<li><strong>When:</strong> {_e(d.when)}</li>",
                    f"<li><strong>Then:</strong> {_e(d.then)}</li>",
                    f"<li><strong>Reproduction:</strong> {_e(d.reproduction)}</li>",
                    f"<li><strong>Stub-path:</strong> {_e(d.stub_path) if d.stub_path else '(none)'}</li>",
                    "</ul>",
                ]
            )

    parts.append("<h2>Observations</h2>")
    if not m.observations:
        parts.append("<p><em>None recorded.</em></p>")
    else:
        for o in m.observations:
            parts.extend(
                [
                    f"<h3>{_e(o.id)}</h3>",
                    "<ul>",
                    f"<li><strong>Given:</strong> {_e(o.given)}</li>",
                    f"<li><strong>When:</strong> {_e(o.when)}</li>",
                    f"<li><strong>Then:</strong> {_e(o.then)}</li>",
                    f"<li><strong>Stub-path:</strong> {_e(o.stub_path) if o.stub_path else '(none)'}</li>",
                    "</ul>",
                ]
            )

    parts.extend(
        [
            "<h2>Overall Assessment</h2>",
            f"<p>{_e(m.assessment)}</p>",
            "</body>",
            "</html>",
        ]
    )
    return "\n".join(parts) + "\n"
