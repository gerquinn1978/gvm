"""Keyword presence test for `/gvm-test` user-guide PP-5 section (TC-PP-5-01 partial).

Pipeline-propagation ADR-605 mandates a "Verdict Vocabulary" section in
`gvm-test/docs/user-guide.html`, rewritten for the three-verdict taxonomy
per honesty-triad ADR-105. PP-3 retires the "Pass with gaps" vocabulary;
this test enforces both the new heading + verdict labels AND the absence
of the retired phrase.
"""

from __future__ import annotations

from pathlib import Path

import pytest


USER_GUIDE = (
    Path(__file__).resolve().parents[1] / "docs" / "user-guide.html"
)

PP5_HEADING = "Verdict Vocabulary"

VERDICT_LABELS = ("Ship-ready", "Demo-ready", "Not shippable")

# PP-3 retired vocabulary — must not appear anywhere in the guide.
RETIRED_PHRASE = "Pass with gaps"


@pytest.fixture(scope="module")
def guide_text() -> str:
    return USER_GUIDE.read_text(encoding="utf-8")


def test_pp5_heading_present(guide_text: str):
    assert PP5_HEADING in guide_text, (
        f"PP-5 heading {PP5_HEADING!r} missing from gvm-test/docs/user-guide.html"
    )


def test_pp5_heading_is_h2(guide_text: str):
    assert f">{PP5_HEADING}</h2>" in guide_text, (
        f"{PP5_HEADING!r} must appear inside an <h2> tag"
    )


@pytest.mark.parametrize("label", VERDICT_LABELS)
def test_verdict_label_present(guide_text: str, label: str):
    assert label in guide_text, (
        f"Three-verdict taxonomy label {label!r} missing — section must "
        "describe the actual gvm_verdict.evaluate output (ADR-105)"
    )


def test_oq5_callout_present(guide_text: str):
    """Guards the OQ-5 manual-gate override callout. Without this, the
    callout could be silently removed and the doc would mis-promise that
    'VV-2 all pass' is sufficient for Ship-ready (it isn't, on the
    OQ-5 branch — see gvm_verdict.evaluate lines 111–116)."""
    assert "OQ-5 manual-gate override" in guide_text, (
        "OQ-5 callout missing — Ship-ready gating cannot be described "
        "honestly without it (see gvm_verdict.evaluate OQ-5 branch)"
    )


def test_retired_pass_with_gaps_absent(guide_text: str):
    """PP-3: 'Pass with gaps' is retired vocabulary plugin-wide. The
    user-guide must not reintroduce it, even in commentary."""
    assert RETIRED_PHRASE not in guide_text, (
        f"PP-3 violation: retired phrase {RETIRED_PHRASE!r} appears in the "
        "user-guide. The three-verdict taxonomy replaces it."
    )


def test_keyword_contract_matches_verifier():
    """DRY: re-import PP5_GUIDE_HEADINGS from the cross-cutting verifier."""
    import sys

    verifier_dir = (
        Path(__file__).resolve().parents[2]
        / "gvm-design-system"
        / "scripts"
    )
    sys.path.insert(0, str(verifier_dir))
    try:
        import _verify_pp_cross_cutting as v
    finally:
        # Remove by value (not position): another import may have
        # inserted at index 0 in the meantime. Also evict the cached
        # module so a later test importing a same-named module from
        # a different path is not aliased to this one.
        try:
            sys.path.remove(str(verifier_dir))
        except ValueError:
            pass
        sys.modules.pop("_verify_pp_cross_cutting", None)

    assert v.PP5_GUIDE_HEADINGS["gvm-test"] == PP5_HEADING, (
        "Drift between this test's PP5_HEADING and the verifier's "
        "PP5_GUIDE_HEADINGS['gvm-test']"
    )
