"""Tests for _shared.default_questions (P18-C01).

The deterministic-fallback synthesiser produces exactly three plain-
language comprehension questions from `findings.headline_findings`.
The output replaces the engine-layer placeholder
`_STUB_COMPREHENSION_QUESTIONS` so direct-CLI invocations ship real
content without requiring an LLM in the loop. The SKILL.md
orchestration bridge (P17-C03 step 12b + `_patch_questions.py`) remains
the canonical override path for richer LLM-synthesised content.
"""

from __future__ import annotations

import pytest

from _shared import default_questions
from _shared.methodology import JARGON_FORBIDDEN


def test_generate_returns_exactly_three_entries_with_headlines() -> None:
    headlines = [
        {
            "id": "H-001",
            "kind": "outlier",
            "title": "Five outlier rows in n_b",
            "summary": "The column n_b carries five values far from the rest.",
            "impact": 0.8,
        },
        {
            "id": "H-002",
            "kind": "missingness",
            "title": "Column 'note' is 40% missing",
            "summary": "The note column is empty for 40% of rows.",
            "impact": 0.6,
        },
        {
            "id": "H-003",
            "kind": "time_series",
            "title": "Weekly cadence detected",
            "summary": "The data arrives weekly with no gaps in the last quarter.",
            "impact": 0.5,
        },
    ]
    out = default_questions.generate(headlines)
    assert len(out) == 3
    for entry in out:
        assert set(entry.keys()) == {"question", "answer", "supporting_finding_id"}
        assert all(isinstance(v, str) for v in entry.values())


def test_generate_returns_three_entries_when_fewer_headlines() -> None:
    """Padding case — only one headline available; synthesiser still
    returns three. Padding entries reference the same headline ID rather
    than fabricating IDs (or empty when no headlines)."""
    headlines = [
        {
            "id": "H-001",
            "kind": "outlier",
            "title": "Five outlier rows in n_b",
            "summary": "The column n_b carries five values far from the rest.",
            "impact": 0.8,
        }
    ]
    out = default_questions.generate(headlines)
    assert len(out) == 3
    # First entry must reference the real headline.
    assert out[0]["supporting_finding_id"] == "H-001"


def test_generate_returns_three_entries_when_no_headlines() -> None:
    """Zero-headlines fallback — returns three generic plain-language
    questions with empty supporting_finding_id strings (matches existing
    placeholder schema where IDs are empty strings, not nulls)."""
    out = default_questions.generate([])
    assert len(out) == 3
    for entry in out:
        assert entry["supporting_finding_id"] == ""
        assert entry["question"]  # non-empty
        assert entry["answer"]


def test_generate_avoids_jargon_in_question_bodies() -> None:
    """Question bodies must contain no forbidden statistical jargon
    (case-insensitive). The synthesiser's templates use plain words;
    headline content already passed _jargon_scan at selection time so
    titles/summaries are clean too."""
    headlines = [
        {
            "id": "H-001",
            "kind": "outlier",
            "title": "Outlier rows detected",
            "summary": "Some rows are far from the rest.",
            "impact": 0.8,
        }
    ]
    out = default_questions.generate(headlines)
    for entry in out:
        body_lower = entry["question"].lower()
        for term in JARGON_FORBIDDEN:
            assert term not in body_lower, (
                f"jargon term {term!r} found in question body: {entry['question']!r}"
            )


def test_generate_is_deterministic() -> None:
    """Same input → same output. No RNG, no time-dependent values."""
    headlines = [
        {
            "id": f"H-{i:03d}",
            "kind": "outlier",
            "title": f"H{i}",
            "summary": f"Summary {i}",
            "impact": 0.5,
        }
        for i in range(3)
    ]
    out_a = default_questions.generate(headlines)
    out_b = default_questions.generate(list(headlines))
    assert out_a == out_b


def test_generate_supporting_ids_reference_real_headlines() -> None:
    """When headlines provided, every non-empty supporting_finding_id
    must match a real headline ID. Padding entries with empty IDs are
    permitted and excluded from this check."""
    headlines = [
        {"id": "H-aaa", "kind": "outlier", "title": "A", "summary": "a", "impact": 0.7},
        {"id": "H-bbb", "kind": "outlier", "title": "B", "summary": "b", "impact": 0.6},
    ]
    valid_ids = {h["id"] for h in headlines}
    out = default_questions.generate(headlines)
    for entry in out:
        sid = entry["supporting_finding_id"]
        if sid:
            assert sid in valid_ids


@pytest.mark.parametrize("n_headlines", [0, 1, 2, 3, 5, 10])
def test_generate_length_invariant(n_headlines: int) -> None:
    """Always exactly three entries regardless of input length."""
    headlines = [
        {
            "id": f"H-{i}",
            "kind": "outlier",
            "title": f"T{i}",
            "summary": f"S{i}",
            "impact": 0.5,
        }
        for i in range(n_headlines)
    ]
    assert len(default_questions.generate(headlines)) == 3


# ---------------------------------------------------------------------------
# Clean-data fallback kinds (P21-C02)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kind, expected_phrase",
    [
        ("dataset_summary", "structure of the data"),
        ("completeness_summary", "complete"),
        ("schema_summary", "kinds of columns"),
    ],
)
def test_question_for_clean_data_kinds(kind: str, expected_phrase: str) -> None:
    """The three clean-data headline kinds (P21-C01) get kind-specific
    question templates rather than falling through to the generic
    'What does the data say about {title}?' which produces grammatically
    awkward output when the title is itself a sentence-fragment."""
    headline = {
        "id": f"dataset:{kind.split('_')[0]}",
        "kind": kind,
        "title": "Dataset: 100 rows × 3 columns",
        "summary": "irrelevant for the question phrasing",
    }
    question = default_questions._question_for(headline)
    assert expected_phrase in question.lower(), (
        f"kind={kind!r} did not use the kind-specific template: {question!r}"
    )
    assert "data say about Dataset:" not in question, (
        f"kind={kind!r} fell through to generic template: {question!r}"
    )


def test_unknown_kind_still_uses_generic_template() -> None:
    """Defensive: an unknown kind preserves the existing generic fallback.
    P21-C02 must not break the generic path."""
    headline = {
        "id": "x:1",
        "kind": "some_future_kind",
        "title": "thing",
        "summary": "s",
    }
    question = default_questions._question_for(headline)
    assert "What does the data say about thing" in question


def test_clean_data_kind_templates_avoid_jargon() -> None:
    """The three new templates must not contain any JARGON_FORBIDDEN
    token. Headline titles already get the jargon scan upstream; these
    templates compose surface text on top and need their own check."""
    for kind in ("dataset_summary", "completeness_summary", "schema_summary"):
        question = default_questions._question_for(
            {"kind": kind, "title": "irrelevant", "id": "x", "summary": "s"}
        )
        lower = question.lower()
        for term in JARGON_FORBIDDEN:
            assert term not in lower, (
                f"jargon term {term!r} appears in {kind!r} template: {question!r}"
            )


def test_clean_data_kind_templates_registered_in_template_map() -> None:
    """All three new kinds appear in `_TEMPLATES_BY_KIND` — regression
    guard against a future refactor that drops one entry."""
    for kind in ("dataset_summary", "completeness_summary", "schema_summary"):
        assert kind in default_questions._TEMPLATES_BY_KIND, kind


def test_padding_question_bodies_avoid_jargon() -> None:
    """Pre-existing test blind spot caught by P21-C02 review: padding
    questions and answers (used when there are 0–2 real headlines) had
    no static jargon-substring check, and `_PADDING_QUESTIONS[0]`
    carried 'shape' which contains 'shap' (a JARGON_FORBIDDEN token).

    Drive `generate([])` so all three padding entries appear, then
    scan every question + answer for jargon hits."""
    out = default_questions.generate([])
    assert len(out) == 3
    for entry in out:
        for field in ("question", "answer"):
            text = entry[field].lower()
            for term in JARGON_FORBIDDEN:
                assert term not in text, (
                    f"jargon term {term!r} appears in padding {field}: "
                    f"{entry[field]!r}"
                )
