"""Deterministic comprehension-question synthesiser (P18-C01).

Closes the engine-layer placeholder gap surfaced by /gvm-test R45:
under direct-CLI invocations, the engine used to ship literal
``[tracer-bullet stub question N]`` text in
``findings.comprehension_questions`` because the LLM-synthesis bridge
fires only under SKILL.md orchestration.

This module produces three plain-language Q/A pairs from
``findings.headline_findings`` deterministically — same input always
returns the same output, no RNG, no time-dependent state. The output
is structurally-real (matches ADR-201 schema, references real headline
IDs, avoids the JARGON_FORBIDDEN word list) even when no orchestrator
is in the loop.

The SKILL.md orchestration layer (P17-C03 step 12b +
``scripts/_patch_questions.py``) remains the canonical override path
for richer LLM-synthesised content. The bridge stub in ``analyse.py``
is preserved as the literal placeholder list overwritten in the
populate-findings step — its purpose has shifted from "engine emits
placeholder until orchestration arrives" to "engine emits deterministic
baseline, orchestration enhances".
"""

from __future__ import annotations

from typing import Any

# Plain-language templates per headline kind. The phrasing is generic
# enough that it composes cleanly with any title/summary the headline
# carries, and avoids every term in JARGON_FORBIDDEN. Headlines whose
# kind is not in this map fall through to the generic template.
_TEMPLATES_BY_KIND: dict[str, str] = {
    "outlier": "What stands out in {title}?",
    "missingness": "What does the data say about {title}?",
    "time_series": "What pattern over time shows up in {title}?",
    "drivers": "What appears to influence the result in {title}?",
    "comparison": "How does the data differ in {title}?",
    # P21-C02: clean-data fallback kinds (P21-C01) carry sentence-fragment
    # titles like "Dataset: 100 rows × 3 columns" or "Column mix: 2 numeric,
    # 1 categorical". The interpolating templates above produce awkward
    # output ("What does the data say about Dataset: 100 rows × 3 columns?")
    # so these three kinds use NON-INTERPOLATED templates that read
    # naturally without the title appended.
    "dataset_summary": "What is the overall structure of the data?",
    "completeness_summary": "How complete are the columns in the data?",
    "schema_summary": "What kinds of columns are in the data?",
}

_GENERIC_QUESTION_TEMPLATE: str = "What does the data say about {title}?"

# Padding entries when fewer than three headlines are available.
# Plain-language only; no jargon. supporting_finding_id is empty
# string (matches the existing schema where stub IDs are blank).
_PADDING_QUESTIONS: tuple[tuple[str, str], ...] = (
    (
        "What is the overall structure of the data?",
        (
            "The report's data-quality and distributions sections "
            "describe the overall structure; see the per-column tables "
            "for detail."
        ),
    ),
    (
        "Which findings should be reviewed first?",
        (
            "The headline findings section lists the most important items "
            "in order; review those first."
        ),
    ),
    (
        "Where can I find more detail about a specific column?",
        (
            "Each column has its own row in the data-quality and "
            "distributions tables; the methodology appendix documents the "
            "techniques used to derive each value."
        ),
    ),
)


def _question_for(headline: dict[str, Any]) -> str:
    """Build a plain-language question for a single headline."""
    template = _TEMPLATES_BY_KIND.get(
        str(headline.get("kind", "")), _GENERIC_QUESTION_TEMPLATE
    )
    title = str(headline.get("title", "this finding"))
    return template.format(title=title)


def _entry_from_headline(headline: dict[str, Any]) -> dict[str, str]:
    """Build a comprehension-question entry from one headline.

    The headline's `summary` becomes the answer (already passed
    through `_jargon_scan` at headline selection time, so it is
    plain-language by construction). `supporting_finding_id` references
    the headline's `id` directly.
    """
    return {
        "question": _question_for(headline),
        "answer": str(headline.get("summary", "See the report sections for detail.")),
        "supporting_finding_id": str(headline.get("id", "")),
    }


def _padding_entry(index: int, fallback_id: str) -> dict[str, str]:
    """Return a padding entry for index N when not enough headlines.

    `fallback_id` is the first available headline ID; padding entries
    point at it when one exists, or an empty string otherwise. Padding
    questions are generic and never reference statistical terms.
    """
    pad = _PADDING_QUESTIONS[index % len(_PADDING_QUESTIONS)]
    return {
        "question": pad[0],
        "answer": pad[1],
        "supporting_finding_id": fallback_id,
    }


def generate(headlines: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Return exactly three comprehension-question entries.

    When `headlines` has at least 3 items, the first three (already sorted
    by impact in `headline.select`) become the questions. When fewer,
    the available headlines are used and the remainder are padded with
    generic plain-language questions whose `supporting_finding_id`
    points at the first headline (or empty when no headlines).
    """
    out: list[dict[str, str]] = []
    fallback_id = ""
    for h in headlines[:3]:
        out.append(_entry_from_headline(h))
        if not fallback_id:
            fallback_id = str(h.get("id", ""))
    while len(out) < 3:
        out.append(_padding_entry(len(out), fallback_id))
    return out
