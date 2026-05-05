"""Keyword presence test for `/gvm-build` user-guide PP-5 section (TC-PP-5-01 partial).

Pipeline-propagation ADR-605 mandates a new "Working with STUBS.md" section in
`gvm-build/docs/user-guide.html`. The exact heading text is the contract — it
is also enforced by the cross-cutting verifier in
`gvm-design-system/scripts/_verify_pp_cross_cutting.PP5_GUIDE_HEADINGS`.

This chunk-level test covers the gvm-build side specifically. The full PP-5
verifier (P13-C03) sweeps every affected user guide.
"""

from __future__ import annotations

from pathlib import Path

import pytest


USER_GUIDE = (
    Path(__file__).resolve().parents[1] / "docs" / "user-guide.html"
)

# The literal heading text — single source of truth is the cross-cutting
# verifier's `PP5_GUIDE_HEADINGS["gvm-build"]`. Drift in either direction
# is a regression.
PP5_HEADING = "Working with STUBS.md"

# Supporting keywords proving the section reflects actual HS-1 behaviour
# (per SKILL.md and honesty-triad ADR-101/004).
SUPPORTING_KEYWORDS = (
    "HS-1",
    "expiry",
    "real-provider plan",
)


@pytest.fixture(scope="module")
def guide_text() -> str:
    return USER_GUIDE.read_text(encoding="utf-8")


def test_pp5_heading_present(guide_text: str):
    assert PP5_HEADING in guide_text, (
        f"PP-5 heading {PP5_HEADING!r} missing from gvm-build/docs/user-guide.html "
        "(contract: PP5_GUIDE_HEADINGS['gvm-build'])"
    )


def test_pp5_heading_is_h2(guide_text: str):
    """Heading must be an H2 — drives the auto-generated TOC and matches the
    visual style of sibling sections. A `<p>` or `<h3>` would still satisfy
    the substring grep but break the document structure."""
    assert f">{PP5_HEADING}</h2>" in guide_text, (
        f"{PP5_HEADING!r} must appear inside an <h2> tag (a `<p>` or `<h3>` "
        "would still satisfy a substring grep but break the document structure)"
    )


@pytest.mark.parametrize("keyword", SUPPORTING_KEYWORDS)
def test_supporting_keyword_present(guide_text: str, keyword: str):
    assert keyword in guide_text, (
        f"PP-5 supporting keyword {keyword!r} missing — section content "
        "must reflect actual HS-1 behaviour, not just have the heading"
    )


def test_keyword_contract_matches_verifier():
    """The heading literal MUST match the cross-cutting verifier's table.
    DRY: one source of truth — the verifier — and this test re-imports it."""
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
        try:
            sys.path.remove(str(verifier_dir))
        except ValueError:
            pass
        sys.modules.pop("_verify_pp_cross_cutting", None)

    assert v.PP5_GUIDE_HEADINGS["gvm-build"] == PP5_HEADING, (
        "Drift between this test's PP5_HEADING and the verifier's "
        "PP5_GUIDE_HEADINGS['gvm-build'] — fix one of them"
    )
