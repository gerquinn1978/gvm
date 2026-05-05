"""Keyword presence test for `/gvm-code-review` user-guide PP-5 section (TC-PP-5-01 partial).

Pipeline-propagation ADR-605 mandates a "Panel E" section in
`gvm-code-review/docs/user-guide.html`, documenting the Stub Detection panel
(honesty-triad ADR-107) and the first-run migration prompt (ADR-608).

The exact heading text is the contract — also enforced by the cross-cutting
verifier in `gvm-design-system/scripts/_verify_pp_cross_cutting.PP5_GUIDE_HEADINGS`.
"""

from __future__ import annotations

from pathlib import Path

import pytest


USER_GUIDE = (
    Path(__file__).resolve().parents[1] / "docs" / "user-guide.html"
)

PP5_HEADING = "Panel E"

# Supporting keywords proving the section reflects actual Panel E + migration
# behaviour (per SKILL.md and honesty-triad ADR-107/ADR-108/ADR-608).
SUPPORTING_KEYWORDS = (
    "Stub Detection",
    "STUBS.md",
    "allowlist",
    "unregistered",
    "expired",
    "namespace_violation",
    "SD-5",
    "migration",
)


@pytest.fixture(scope="module")
def guide_text() -> str:
    return USER_GUIDE.read_text(encoding="utf-8")


def test_pp5_heading_present(guide_text: str):
    assert PP5_HEADING in guide_text, (
        f"PP-5 heading {PP5_HEADING!r} missing from "
        "gvm-code-review/docs/user-guide.html "
        "(contract: PP5_GUIDE_HEADINGS['gvm-code-review'])"
    )


def test_pp5_heading_is_h2(guide_text: str):
    """Heading must be an H2 — drives the auto-generated TOC and matches the
    visual style of sibling sections."""
    assert f">{PP5_HEADING}</h2>" in guide_text, (
        f"{PP5_HEADING!r} must appear inside an <h2> tag"
    )


@pytest.mark.parametrize("keyword", SUPPORTING_KEYWORDS)
def test_supporting_keyword_present(guide_text: str, keyword: str):
    assert keyword in guide_text, (
        f"PP-5 supporting keyword {keyword!r} missing — section content "
        "must reflect actual Panel E + migration-prompt behaviour, not "
        "just have the heading"
    )


def test_keyword_contract_matches_verifier():
    """Drift guard for the heading literal only.

    The cross-cutting verifier (`_verify_pp_cross_cutting.check_pp5_user_guides`)
    only checks that `PP5_GUIDE_HEADINGS[skill]` appears in the guide text.
    It does NOT enforce `SUPPORTING_KEYWORDS` &mdash; those keywords are
    local to this chunk-level test. So this assertion guards heading drift
    only; a maintainer adding a keyword to `SUPPORTING_KEYWORDS` here is
    NOT thereby adding it to a release gate.
    """
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
        # Remove by value (not position) and evict the module cache so a
        # later test importing a same-named module from a different path
        # is not aliased to this one. (Canonical idiom — see P13-C05.)
        try:
            sys.path.remove(str(verifier_dir))
        except ValueError:
            pass
        sys.modules.pop("_verify_pp_cross_cutting", None)

    assert v.PP5_GUIDE_HEADINGS["gvm-code-review"] == PP5_HEADING, (
        "Drift between this test's PP5_HEADING and the verifier's "
        "PP5_GUIDE_HEADINGS['gvm-code-review'] — fix one of them"
    )
