"""PP-5 keyword presence test for the three NEW-skill user guides
(TC-PP-5-01 partial — covers /gvm-impact-map, /gvm-walking-skeleton,
/gvm-explore-test).

Pipeline-propagation ADR-605 mandates a `docs/user-guide.html` file for each
new skill. The cross-cutting verifier `_verify_pp_cross_cutting.
check_new_skill_guides` enforces file existence only — content fidelity is
asserted here.

Each per-skill keyword set is grounded in the relevant SKILL.md so that
documentation drift surfaces as a test failure.
"""

from __future__ import annotations

from pathlib import Path

import pytest


SKILLS_ROOT = Path(__file__).resolve().parents[2]


# Per-skill content contract. Each tuple is (skill_dir, supporting_keywords).
# Keywords are literals lifted from each SKILL.md / domain spec — drift in
# the guide will surface as a test failure here.
GUIDES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "gvm-impact-map",
        (
            "impact-map.md",
            "Goals",
            "Actors",
            "Impacts",
            "Deliverables",
            "IM-4",
            "Adzic",
            "schema_version",
        ),
    ),
    (
        "gvm-walking-skeleton",
        (
            "boundaries.md",
            "wired",
            "wired_sandbox",
            "deferred_stub",
            "WS-5",
            "single-flow",
            "Freeman",
            "Pryce",
            "production_sandbox_divergence",
        ),
    ),
    (
        "gvm-explore-test",
        (
            "charter",
            "explore-NNN",
            "Critical",
            "Important",
            "Minor",
            "Observation",
            "VV-4(d)",
            "Bach",
            "Hendrickson",
            "html.escape",
        ),
    ),
)


@pytest.fixture(scope="module")
def guide_texts() -> dict[str, str]:
    """Load each new-skill user guide.

    Missing files store ``""`` so dependent parametrised tests run and
    surface which keyword they expected; ``test_user_guide_file_exists``
    reports the root cause separately.
    """
    out: dict[str, str] = {}
    for skill, _ in GUIDES:
        path = SKILLS_ROOT / skill / "docs" / "user-guide.html"
        if not path.exists():
            out[skill] = ""
            continue
        out[skill] = path.read_text(encoding="utf-8")
    return out


@pytest.mark.parametrize("skill", [g[0] for g in GUIDES])
def test_user_guide_file_exists(skill: str):
    path = SKILLS_ROOT / skill / "docs" / "user-guide.html"
    assert path.exists(), (
        f"PP-5 user guide missing for new skill {skill!r} at {path} "
        "(contract: _verify_pp_cross_cutting.NEW_SKILL_GUIDES)"
    )


@pytest.mark.parametrize("skill", [g[0] for g in GUIDES])
def test_user_guide_has_table_of_contents(skill: str, guide_texts: dict[str, str]):
    text = guide_texts[skill]
    assert "<nav" in text or "Contents" in text, (
        f"{skill}/docs/user-guide.html should expose a table of contents — "
        "found neither <nav> nor 'Contents' marker"
    )


@pytest.mark.parametrize(
    "skill,keyword",
    [(skill, kw) for skill, kws in GUIDES for kw in kws],
)
def test_supporting_keyword_present(
    skill: str, keyword: str, guide_texts: dict[str, str]
):
    text = guide_texts[skill]
    assert keyword in text, (
        f"PP-5 supporting keyword {keyword!r} missing from "
        f"{skill}/docs/user-guide.html — guide must reflect actual skill "
        "behaviour, not a TOC stub"
    )


@pytest.mark.parametrize("skill", [g[0] for g in GUIDES])
def test_no_deferred_placeholder(skill: str, guide_texts: dict[str, str]):
    """The P10-C01 scaffold for /gvm-impact-map shipped with
    `<em>Deferred to P13-C09.</em>` — this chunk IS P13-C09, so the
    placeholder must be gone. Same guard for the other two new skills."""
    text = guide_texts[skill]
    assert "Deferred to P13-C09" not in text, (
        f"{skill}/docs/user-guide.html still contains the "
        "'Deferred to P13-C09' placeholder — flesh out the content"
    )


def test_keyword_contract_matches_verifier():
    """DRY guard: this test's GUIDES list and the cross-cutting verifier's
    NEW_SKILL_GUIDES tuple must reference the same three skills.

    Canonical sys.path idiom (see P13-C04..C08 handovers): insert + try /
    finally with `sys.path.remove(value)` + `sys.modules.pop(name, None)` so
    a later test importing a same-named module from a different path is
    not aliased to this one.
    """
    import sys

    verifier_dir = SKILLS_ROOT / "gvm-design-system" / "scripts"
    sys.path.insert(0, str(verifier_dir))
    try:
        import _verify_pp_cross_cutting as v
    finally:
        try:
            sys.path.remove(str(verifier_dir))
        except ValueError:
            pass
        sys.modules.pop("_verify_pp_cross_cutting", None)

    expected = tuple(g[0] for g in GUIDES)
    assert v.NEW_SKILL_GUIDES == expected, (
        f"Drift between this test's GUIDES ({expected!r}) and the "
        f"verifier's NEW_SKILL_GUIDES ({v.NEW_SKILL_GUIDES!r}) — fix one"
    )
