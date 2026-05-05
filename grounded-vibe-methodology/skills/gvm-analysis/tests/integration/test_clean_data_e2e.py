"""End-to-end clean-data report integrity (P21-C02).

A real-world `/gvm-analysis` run against clean ordinal data — no
missingness, no outliers, no time-series anomalies, no significant
drivers — used to ship a report whose headline section was empty and
whose comprehension questions were three padding entries with empty
`supporting_finding_id` fields. P21-C01 closed the empty-headlines
gap; this test asserts the full chain end-to-end:

1. ``analyse.main`` exits 0 against a clean fixture.
2. ``findings.headline_findings`` is non-empty (the fallback fired and
   produced at least a `dataset_summary` entry).
3. ``findings.comprehension_questions`` has exactly three entries.
4. At least one entry's ``supporting_finding_id`` is non-empty AND
   matches a real headline ID — proves the synthesiser anchored
   against the fallback's IDs rather than padding with blanks.
5. No entry contains the literal "tracer-bullet" substring (the
   pre-P18-C01 placeholder text is fully retired on this path).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def _build_clean_fixture(out_path: Path) -> None:
    """Build a 50-row fixture with three columns spanning numeric +
    categorical dtypes. No missingness, no extreme outliers, no
    timestamp column. Designed so every existing candidate source
    returns []."""
    rows = []
    for i in range(50):
        rows.append(
            {
                "score": float(i % 5 + 1),
                "rating": float(i % 4 + 1),
                "category": ["alpha", "bravo", "charlie", "delta"][i % 4],
            }
        )
    pd.DataFrame(rows).to_csv(out_path, index=False)


def _run_engine(tmp_path: Path) -> dict:
    import analyse
    from _shared import findings

    csv = tmp_path / "clean.csv"
    _build_clean_fixture(csv)
    out = tmp_path / "out"
    rc = analyse.main(
        [
            "--input",
            str(csv),
            "--output-dir",
            str(out),
            "--mode",
            "explore",
            "--seed",
            "42",
        ]
    )
    assert rc == 0, "analyse.main failed on clean fixture"
    return findings.read_findings(out / "findings.json")


def test_clean_data_run_produces_non_empty_headlines(tmp_path: Path) -> None:
    """Headline fallback (P21-C01) fires; section is non-empty."""
    data = _run_engine(tmp_path)
    headlines = data.get("headline_findings") or []
    assert headlines, (
        "headline_findings is empty on clean data — P21-C01 fallback did "
        "not fire end-to-end"
    )


def test_clean_data_run_anchors_questions_to_real_headlines(
    tmp_path: Path,
) -> None:
    """At least one comprehension question references a real headline
    ID (the P21-C02 path, not the padding-with-empty-IDs path)."""
    data = _run_engine(tmp_path)
    headlines = data.get("headline_findings") or []
    questions = data.get("comprehension_questions") or []

    assert len(questions) == 3, f"expected 3 questions, got {len(questions)}"

    headline_ids = {h["id"] for h in headlines}
    referencing_entries = [
        q for q in questions if q.get("supporting_finding_id") in headline_ids
    ]
    assert referencing_entries, (
        f"no comprehension question references a real headline; "
        f"headline IDs: {sorted(headline_ids)}, "
        f"supporting_finding_ids: {[q.get('supporting_finding_id') for q in questions]}"
    )


def test_clean_data_run_carries_no_tracer_bullet_text(tmp_path: Path) -> None:
    """The pre-P18-C01 placeholder text is fully retired on the
    clean-data path. No comprehension question or headline contains
    the literal `tracer-bullet` substring."""
    data = _run_engine(tmp_path)
    questions = data.get("comprehension_questions") or []
    headlines = data.get("headline_findings") or []

    for q in questions:
        for field in ("question", "answer"):
            assert "tracer-bullet" not in q.get(field, "").lower(), (
                f"placeholder text in comprehension_questions[{field}]: {q}"
            )
    for h in headlines:
        for field in ("title", "summary"):
            assert "tracer-bullet" not in h.get(field, "").lower(), (
                f"placeholder text in headline[{field}]: {h}"
            )


def test_clean_data_question_uses_kind_specific_template(tmp_path: Path) -> None:
    """The first question (anchored to dataset_summary, the highest
    deterministic id among fallback kinds when sorted by impact=0.0
    then id asc) reads naturally — not the awkward generic-template
    output 'What does the data say about Dataset: 50 rows × 3 columns?'.
    This proves P21-C02's template entries are wired through the full
    chain."""
    data = _run_engine(tmp_path)
    questions = data.get("comprehension_questions") or []
    assert questions, "no comprehension questions produced"

    full_text = " | ".join(q.get("question", "") for q in questions).lower()
    # At least one of the kind-specific phrases must appear.
    expected_any = ["structure of the data", "complete", "kinds of columns"]
    matched = [phrase for phrase in expected_any if phrase in full_text]
    assert matched, (
        "no kind-specific template phrase appears in comprehension "
        f"questions; saw: {full_text!r}"
    )
