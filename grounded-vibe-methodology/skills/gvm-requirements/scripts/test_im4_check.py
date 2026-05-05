"""Tests for P10-C05 — `/gvm-requirements` IM-4 Phase 5 gate.

Pin the contract that every functional requirement (MUST/SHOULD/COULD) must
carry a `[impact-deliverable: D-N]` source tag whose D-N exists in the
project's impact-map.md, per discovery ADR-304. Won't-priority requirements
are exempt (out-of-scope by definition).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

_DS_SCRIPTS = Path(__file__).resolve().parents[3] / "gvm-design-system" / "scripts"
if str(_DS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_DS_SCRIPTS))

from _im4_check import Im4Error, check  # noqa: E402
from _impact_map_parser import (  # noqa: E402
    Actor,
    Deliverable,
    Goal,
    Impact,
    ImpactMap,
    serialise,
)


def _impact_map_with(deliverable_ids: list[str]) -> ImpactMap:
    """Build a minimal valid ImpactMap whose Deliverables carry the requested IDs."""
    goals = (Goal(id="G-1", statement="grow", metric="x", target="10", deadline="Q1"),)
    actors = (Actor(id="A-1", goal_id="G-1", name="Buyer", description="x"),)
    impacts = (
        Impact(
            id="I-1", actor_id="A-1", behavioural_change="returns more", direction="+"
        ),
    )
    deliverables = tuple(
        Deliverable(id=did, impact_id="I-1", title=f"deliverable {did}", type="feature")
        for did in deliverable_ids
    )
    return ImpactMap(
        goals=goals,
        actors=actors,
        impacts=impacts,
        deliverables=deliverables,
        changelog=(),
    )


def _write_map(tmp_path: Path, im: ImpactMap) -> Path:
    p = tmp_path / "impact-map.md"
    p.write_text(serialise(im), encoding="utf-8")
    return p


def _write_reqs(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "requirements.md"
    p.write_text(body, encoding="utf-8")
    return p


def test_unparented_must_requirement_rejected(tmp_path: Path):
    """TC-IM-4-01: a Must requirement with no source tag is refused."""
    im_path = _write_map(tmp_path, _impact_map_with(["D-1"]))
    req_path = _write_reqs(tmp_path, "**RE-1 (Must):** the system shall do thing.\n")
    errors = check(req_path, im_path)
    assert len(errors) == 1
    assert errors[0].requirement_id == "RE-1"
    assert errors[0].code == "IM-4"


def test_parented_must_requirement_accepted(tmp_path: Path):
    """TC-IM-4-02: a Must requirement with a resolvable trace passes."""
    im_path = _write_map(tmp_path, _impact_map_with(["D-3"]))
    req_path = _write_reqs(
        tmp_path, "**RE-1 (Must) [impact-deliverable: D-3]:** thing.\n"
    )
    errors = check(req_path, im_path)
    assert errors == []


def test_unresolved_trace_id_rejected(tmp_path: Path):
    im_path = _write_map(tmp_path, _impact_map_with(["D-1", "D-2"]))
    req_path = _write_reqs(
        tmp_path, "**RE-1 (Must) [impact-deliverable: D-99]:** thing.\n"
    )
    errors = check(req_path, im_path)
    assert len(errors) == 1
    assert "D-99" in errors[0].message
    assert errors[0].requirement_id == "RE-1"


def test_wont_priority_skipped(tmp_path: Path):
    """Won't-priority requirements are out-of-scope; the gate ignores them."""
    im_path = _write_map(tmp_path, _impact_map_with(["D-1"]))
    req_path = _write_reqs(tmp_path, "**RE-9 (Won't):** future work, not now.\n")
    errors = check(req_path, im_path)
    assert errors == []


def test_multiple_deliverables_all_must_resolve(tmp_path: Path):
    """A multi-D tag fails iff any single D-N is unresolved; only the missing one is named."""
    im_path = _write_map(tmp_path, _impact_map_with(["D-3"]))
    req_path = _write_reqs(
        tmp_path, "**RE-1 (Must) [impact-deliverable: D-3, D-7]:** thing.\n"
    )
    errors = check(req_path, im_path)
    assert len(errors) == 1
    assert "D-7" in errors[0].message
    assert "D-3" not in errors[0].message


def test_empty_tag_rejected(tmp_path: Path):
    im_path = _write_map(tmp_path, _impact_map_with(["D-1"]))
    req_path = _write_reqs(tmp_path, "**RE-1 (Must) [impact-deliverable: ]:** thing.\n")
    errors = check(req_path, im_path)
    assert len(errors) == 1
    assert errors[0].requirement_id == "RE-1"


def test_impact_map_parse_failure_surfaces_one_error(tmp_path: Path):
    bad = tmp_path / "impact-map.md"
    bad.write_text("not a valid impact-map\n", encoding="utf-8")
    req_path = _write_reqs(
        tmp_path, "**RE-1 (Must) [impact-deliverable: D-3]:** thing.\n"
    )
    errors = check(req_path, bad)
    assert len(errors) == 1
    assert errors[0].code == "IM-4"
    assert errors[0].requirement_id == "-"


def test_errors_sorted_by_requirement_id(tmp_path: Path):
    im_path = _write_map(tmp_path, _impact_map_with(["D-1"]))
    body = (
        "**RE-3 (Must):** no tag here either.\n"
        "**RE-1 (Must):** no tag here.\n"
        "**RE-2 (Must):** also missing.\n"
    )
    req_path = _write_reqs(tmp_path, body)
    errors = check(req_path, im_path)
    ids = [e.requirement_id for e in errors]
    assert ids == sorted(ids)


@pytest.mark.parametrize(
    "priority", ["Must", "MUST", "Should", "SHOULD", "Could", "could"]
)
def test_priority_variants_accepted_as_in_scope(tmp_path: Path, priority: str):
    """Must/Should/Could variants are all in-scope (any case)."""
    im_path = _write_map(tmp_path, _impact_map_with(["D-1"]))
    req_path = _write_reqs(tmp_path, f"**RE-1 ({priority}):** thing.\n")
    errors = check(req_path, im_path)
    assert len(errors) == 1, f"priority={priority!r} should be in-scope and rejected"


@pytest.mark.parametrize("wont", ["Won't", "won't", "Wont", "WONT"])
def test_wont_variants_skipped(tmp_path: Path, wont: str):
    im_path = _write_map(tmp_path, _impact_map_with(["D-1"]))
    req_path = _write_reqs(tmp_path, f"**RE-1 ({wont}):** out of scope.\n")
    errors = check(req_path, im_path)
    assert errors == [], f"priority={wont!r} should be skipped"


def test_uses_shared_im_tags_parser():
    """Drift guard: _im4_check must use the live `parse_impact_deliverable_tag`
    binding from the shared `_im_tags` module — not a copy of the regex
    (discovery ADR-304 — both `_im4_check` and `_trace_resolver` call the
    same parser so the two skills cannot diverge).
    """
    import _im4_check

    # Live binding — if `_im_tags` is renamed or the function disappears, this
    # raises at import time rather than silently passing on a stale grep.
    assert callable(_im4_check.parse_impact_deliverable_tag)
    assert _im4_check.parse_impact_deliverable_tag("[impact-deliverable: D-3]") == [
        "D-3"
    ]
    # The bracket-content regex (`[D]-\d+(...)`) must live only in _im_tags.
    # _REQ_LINE_RE in _im4_check matches the outer optional bracket span —
    # parsing the inner D-N list is delegated to the shared parser.
    src = (Path(__file__).parent / "_im4_check.py").read_text(encoding="utf-8")
    assert "[D]-\\d+" not in src, (
        "Inline copy of TAG_RE inner pattern detected — the D-N parser lives "
        "in _im_tags.parse_impact_deliverable_tag only."
    )


def test_unrecognised_priority_treated_as_in_scope(tmp_path: Path):
    """A priority outside MoSCoW (typo, custom) must NOT be silently skipped —
    the regex restricts the priority to Must/Should/Could/Won't so a typo
    like 'Wontd' fails to match and the requirement line is ignored
    (out-of-scope by parser miss). Confirm the ignore path: no error AND
    the requirement is not falsely accepted."""
    im_path = _write_map(tmp_path, _impact_map_with(["D-1"]))
    # 'Wontd' is not a recognised MoSCoW priority; line should not match the
    # requirement regex and therefore be ignored entirely (no error, but also
    # not accepted as a tagged requirement).
    req_path = _write_reqs(tmp_path, "**RE-1 (Wontd):** typo here.\n")
    errors = check(req_path, im_path)
    assert errors == []


def test_non_moscow_priority_does_not_match(tmp_path: Path):
    """Prose like `**Note (see PR-1):** ...` must not match the requirement
    regex — only MoSCoW priorities are scanned."""
    im_path = _write_map(tmp_path, _impact_map_with(["D-1"]))
    body = (
        "**Note (Reference): see related work.\n"
        "**FOO-1 (Optional):** non-MoSCoW priority, ignored.\n"
    )
    req_path = _write_reqs(tmp_path, body)
    errors = check(req_path, im_path)
    assert errors == []


def test_numeric_sort_order(tmp_path: Path):
    """Errors sort RE-2 < RE-9 < RE-10 (numeric, not lexicographic)."""
    im_path = _write_map(tmp_path, _impact_map_with(["D-1"]))
    body = "**RE-10 (Must):** ten.\n**RE-2 (Must):** two.\n**RE-9 (Must):** nine.\n"
    req_path = _write_reqs(tmp_path, body)
    errors = check(req_path, im_path)
    assert [e.requirement_id for e in errors] == ["RE-2", "RE-9", "RE-10"]


def test_im4error_is_frozen_dataclass():
    err = Im4Error(code="IM-4", requirement_id="RE-1", message="x")
    with pytest.raises(Exception):
        err.code = "IM-5"  # type: ignore[misc]


def test_non_requirement_lines_ignored(tmp_path: Path):
    """Lines that don't match the bold-id-priority pattern are ignored."""
    im_path = _write_map(tmp_path, _impact_map_with(["D-1"]))
    body = (
        "## Functional Domains\n"
        "Some prose about the domain.\n"
        "**RE-1 (Must) [impact-deliverable: D-1]:** thing.\n"
        "Another paragraph.\n"
    )
    req_path = _write_reqs(tmp_path, body)
    errors = check(req_path, im_path)
    assert errors == []
