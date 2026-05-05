"""HTML renderer for `VerdictResult` (honesty-triad ADR-105, VV-5).

Renders the three-verdict taxonomy plus the structured criterion table that
satisfies VV-5. The renderer rejects anything that is not a `Verdict` enum
instance — `Verdict` is the only legal verdict shape (ADR-105 closing line:
"the HTML renderer rejects an unknown enum value at render time. PP-3 grep is
a backstop, not the only defence").

Public surface:
- :func:`render_verdict`
- :func:`validate_rationale` (TC-VV-5-02 gate)
- :class:`InvalidVerdictError`
- :class:`FreeTextOnlyRationaleError`
"""

from __future__ import annotations

from html import escape

from gvm_verdict import Verdict, VerdictResult


class InvalidVerdictError(ValueError):
    """The renderer was passed something other than a `Verdict` enum."""


class FreeTextOnlyRationaleError(ValueError):
    """VV-5 validator: rationale lacks a structured criterion table."""


_DEMO_LINE = "NOT user-deployable"


def _status_label(status: str) -> str:
    return "N/A" if status == "NA" else status


def _row(name: str, status: str, evidence: str) -> str:
    return (
        f"<tr><td>{escape(name)}</td>"
        f"<td>{escape(_status_label(status))}</td>"
        f"<td>{escape(evidence)}</td></tr>"
    )


def render_verdict(result: VerdictResult, *, free_text_rationale: str = "") -> str:
    """Render the verdict + structured rationale table as an HTML fragment."""
    if not isinstance(result.verdict, Verdict):
        raise InvalidVerdictError(
            f"verdict must be a Verdict enum instance; got {type(result.verdict).__name__}"
        )

    rows = "".join(_row(c.name, c.status, c.evidence) for c in result.criteria)
    table = (
        '<table class="vv-rationale">'
        "<thead><tr><th>Criterion</th><th>Status</th><th>Evidence</th></tr></thead>"
        f"<tbody>{rows}</tbody>"
        "</table>"
    )

    demo_line = (
        f'<p class="vv-demo-warning">{_DEMO_LINE}</p>'
        if result.verdict is Verdict.DEMO_READY
        else ""
    )

    free_text_block = (
        f'<p class="vv-free-text">{escape(free_text_rationale)}</p>'
        if free_text_rationale
        else ""
    )

    return (
        '<section class="vv-verdict">'
        f'<h2 class="vv-headline">Verdict: {escape(result.verdict.value)}</h2>'
        f"{demo_line}"
        f"{table}"
        f"{free_text_block}"
        "</section>"
    )


def validate_rationale(html_fragment: str) -> None:
    """Raise FreeTextOnlyRationaleError if `html_fragment` lacks the structured table."""
    if 'class="vv-rationale"' not in html_fragment:
        raise FreeTextOnlyRationaleError(
            'rationale is missing the structured <table class="vv-rationale"> element'
        )
