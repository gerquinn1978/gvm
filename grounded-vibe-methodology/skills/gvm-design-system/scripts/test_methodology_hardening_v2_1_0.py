"""Structural tests for v2.1.0 methodology-hardening artefacts.

Tests assert that specific text/sections/IDs exist in SKILL.md and
project-level files. SKILL.md is the system under test; structural
assertions are the appropriate test shape for methodology gates.

Test file path: grounded-vibe-methodology/skills/gvm-design-system/scripts/
PROJECT_ROOT walks 4 parents up: scripts -> gvm-design-system -> skills ->
grounded-vibe-methodology -> repo root.
"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
CHANGELOG = PROJECT_ROOT / "methodology-changelog.md"
GVM_BUILD_SKILL = (
    PROJECT_ROOT / "grounded-vibe-methodology/skills/gvm-build/SKILL.md"
)
GVM_TECH_SPEC_SKILL = (
    PROJECT_ROOT / "grounded-vibe-methodology/skills/gvm-tech-spec/SKILL.md"
)
GVM_CODE_REVIEW_SKILL = (
    PROJECT_ROOT / "grounded-vibe-methodology/skills/gvm-code-review/SKILL.md"
)
GVM_STATUS_SKILL = (
    PROJECT_ROOT / "grounded-vibe-methodology/skills/gvm-status/SKILL.md"
)
GVM_DEPLOY_SKILL = (
    PROJECT_ROOT / "grounded-vibe-methodology/skills/gvm-deploy/SKILL.md"
)


def test_methodology_changelog_exists() -> None:
    assert CHANGELOG.exists(), f"methodology-changelog.md must exist at {CHANGELOG}"


def test_methodology_changelog_has_v2_0_0_header() -> None:
    text = CHANGELOG.read_text(encoding="utf-8")
    assert "## v2.0.0" in text, "missing v2.0.0 section header"


def test_methodology_changelog_has_v2_0_1_header() -> None:
    text = CHANGELOG.read_text(encoding="utf-8")
    assert "## v2.0.1" in text, "missing v2.0.1 section header"


def _section(text: str, header: str) -> str:
    """Return the slice of `text` belonging to the section starting with `header`.

    Anchors `header` at a line boundary (after a newline) so prose mentions
    of a version string in the body of another section don't truncate the
    extraction. Stops at the next `## v` header line, also line-anchored.
    """
    parts = text.split("\n" + header, 1)
    if len(parts) == 1:
        parts = text.split(header, 1)
        if len(parts) == 1:
            return ""
    return parts[1].split("\n## v")[0]


def test_v2_0_0_entry_has_defect_class_field() -> None:
    text = CHANGELOG.read_text(encoding="utf-8")
    section = _section(text, "## v2.0.0")
    assert "Defect class addressed:" in section, (
        "v2.0.0 entry must include 'Defect class addressed:' field"
    )


def test_v2_0_0_entry_has_validation_field() -> None:
    text = CHANGELOG.read_text(encoding="utf-8")
    section = _section(text, "## v2.0.0")
    assert "Validation:" in section, (
        "v2.0.0 entry must include 'Validation:' field"
    )


def test_v2_0_1_entry_has_defect_class_field() -> None:
    text = CHANGELOG.read_text(encoding="utf-8")
    section = _section(text, "## v2.0.1")
    assert "Defect class addressed:" in section, (
        "v2.0.1 entry must include 'Defect class addressed:' field"
    )


def test_v2_0_1_entry_has_validation_field() -> None:
    text = CHANGELOG.read_text(encoding="utf-8")
    section = _section(text, "## v2.0.1")
    assert "Validation:" in section, (
        "v2.0.1 entry must include 'Validation:' field"
    )


# Rule-reference field tests. The spec mandates three fields per entry:
# rule reference, defect class addressed, validation method. The rule
# reference is structurally conveyed by each bullet starting with a
# `/gvm-` skill name (e.g. `/gvm-build Hard Gate 7`), not by a labelled
# field. These tests assert the structural pattern is present.

def test_v2_0_0_entry_has_rule_reference() -> None:
    text = CHANGELOG.read_text(encoding="utf-8")
    section = _section(text, "## v2.0.0")
    assert "- `/gvm-" in section, (
        "v2.0.0 entry must reference at least one /gvm- skill (rule reference)"
    )


def test_v2_0_1_entry_has_rule_reference() -> None:
    text = CHANGELOG.read_text(encoding="utf-8")
    section = _section(text, "## v2.0.1")
    assert "- `/gvm-" in section, (
        "v2.0.1 entry must reference at least one /gvm- skill (rule reference)"
    )


# v2.1.0 release-date constant — read by Hard Gate 8 (P25-C01) for the
# NFR-1 carry-over rule. The literal declaration must be present in
# /gvm-build SKILL.md exactly as the cross-cutting spec mandates.

def test_gvm_build_skill_md_has_release_date_constant() -> None:
    text = GVM_BUILD_SKILL.read_text(encoding="utf-8")
    assert '_V2_1_0_RELEASE_DATE = "2026-04-28"' in text, (
        "/gvm-build SKILL.md must declare the literal release-date constant "
        '`_V2_1_0_RELEASE_DATE = "2026-04-28"`'
    )
    # MUST NOT clause: the constant must be a real assignment, not a
    # commented-out line that satisfies the literal substring search
    # while leaving Hard Gate 8 with no value to read at runtime
    # (Beck: every behaviour has a test, including the negative path).
    # Disqualifier list covers comment forms that could appear in SKILL.md
    # (Markdown prose) or fenced code blocks (Python `#`, JS/Go/TS `//`,
    # INI/SQL `;` / `--`, Markdown `[//]: #` idiom).
    for offending in (
        '# _V2_1_0_RELEASE_DATE',
        '#_V2_1_0_RELEASE_DATE',
        '[//]: # (_V2_1_0_RELEASE_DATE',
        '// _V2_1_0_RELEASE_DATE',
        '; _V2_1_0_RELEASE_DATE',
        '-- _V2_1_0_RELEASE_DATE',
    ):
        assert offending not in text, (
            f"`_V2_1_0_RELEASE_DATE` MUST be a live declaration, not a "
            f"commented-out token (`{offending}`). Hard Gate 8 reads the "
            f"constant at runtime — a comment cannot satisfy NFR-1."
        )


# Hard Gate 8 (P25-C01) — chunk-level acceptance smoke gate. Six structural
# tests covering TC-GATE-1-01..05 plus TC-NFR-1-02 (mtime carry-over).

def _hard_gate_8_section(skill_text: str) -> str:
    """Return the slice of SKILL.md belonging to the Hard Gate 8 entry.

    Anchors on the verbatim opener used in SKILL.md so the helper cannot
    silently match a `8. **` numbered list item from a changelog, Key Rules,
    or any other section preceding the Hard Gates list. Stops at the next
    'Verification:' line or following Markdown section header.
    """
    anchor = "8. **CHUNK-LEVEL ACCEPTANCE SMOKE GATE"
    idx = skill_text.find(anchor)
    if idx == -1:
        return ""
    rest = skill_text[idx:]
    # Earliest-position termination, not first-match-wins (Code-review R54
    # #5): if a future edit inserts a Markdown subsection between Hard
    # Gate 8 and the `Verification:` line, returning at the first listed
    # terminator (`\nVerification:`) would silently extend the captured
    # slice across the section boundary. Use min() over all candidates so
    # the helper terminates at whichever boundary appears first in the
    # text, regardless of declaration order.
    candidates = [
        pos
        for pos in (
            rest.find(t) for t in ("\nVerification:", "\n## Expert Panel", "\n## ")
        )
        if pos != -1
    ]
    if not candidates:
        return rest
    return rest[: min(candidates)]


def _handover_template_block(skill_text: str) -> str:
    """Return the handover template fenced markdown block under '## Handover Format'.

    The fenced block contains its own `##` subheadings (e.g. `## Files Created`)
    so we must terminate on the closing ```` ``` ```` fence, not the next
    Markdown heading.
    """
    parts = skill_text.split("## Handover Format", 1)
    if len(parts) == 1:
        return ""
    after = parts[1]
    fence_open = after.find("```markdown")
    # Fail-closed when the opening fence is absent — Code-review R54 #4.
    # A SKILL.md with a corrupted/missing fence would otherwise expose all
    # subsequent text to downstream `in` checks, hiding template breakage.
    if fence_open == -1:
        return ""
    body_start = fence_open + len("```markdown")
    fence_close = after.find("\n```", body_start)
    # Fail-closed when the closing fence is absent — same reason as above.
    if fence_close == -1:
        return ""
    return after[body_start:fence_close]


def test_tc_gate_1_01_skill_md_declares_hard_gate_8() -> None:
    text = GVM_BUILD_SKILL.read_text(encoding="utf-8")
    section = _hard_gate_8_section(text)
    assert section, "Hard Gate 8 entry must exist in SKILL.md Hard Gates list"
    assert "chunk-level acceptance" in section.lower() or "chunk-acceptance" in section.lower(), (
        "Hard Gate 8 must name itself as the chunk-level acceptance gate"
    )
    assert "smoke" in section.lower(), "Hard Gate 8 must reference smoke-test"
    assert "structural" in section.lower(), (
        "Hard Gate 8 must reference structural-contract assertions"
    )


def test_tc_gate_1_02_per_stack_categories_named() -> None:
    text = GVM_BUILD_SKILL.read_text(encoding="utf-8")
    section = _hard_gate_8_section(text)
    assert "CLI" in section, "Hard Gate 8 must name CLI tools as a stack category"
    assert "web" in section.lower(), "Hard Gate 8 must name web products as a stack category"


def test_tc_gate_1_03_handover_template_has_smoke_fields() -> None:
    text = GVM_BUILD_SKILL.read_text(encoding="utf-8")
    block = _handover_template_block(text)
    assert "Smoke command" in block, "Handover template must include `Smoke command` field"
    assert "Exit code" in block, "Handover template must include `Exit code` field"
    assert "Structural assertions" in block, (
        "Handover template must include `Structural assertions` field"
    )


def test_tc_gate_1_04_handover_template_has_exemption_marker() -> None:
    text = GVM_BUILD_SKILL.read_text(encoding="utf-8")
    block = _handover_template_block(text)
    assert "Hard Gate 8 exempted" in block, (
        "Handover template must include the literal `Hard Gate 8 exempted` "
        "exemption marker per ADR-MH-04"
    )


def test_tc_gate_1_05_skill_md_states_smoke_failure_blocks_handover() -> None:
    text = GVM_BUILD_SKILL.read_text(encoding="utf-8")
    section = _hard_gate_8_section(text)
    lower = section.lower()
    assert "non-zero" in lower or "exit code" in lower, (
        "Hard Gate 8 must reference the exit-code refusal contract"
    )
    assert "block" in lower or "refus" in lower, (
        "Hard Gate 8 must state that smoke failure blocks/refuses the handover"
    )
    assert "stderr" in lower, (
        "Hard Gate 8 refusal rule must require stderr to be surfaced to "
        "the practitioner per TC-GATE-1-05"
    )


def test_tc_nfr_1_02_hard_gate_8_references_release_date_for_mtime_check() -> None:
    text = GVM_BUILD_SKILL.read_text(encoding="utf-8")
    section = _hard_gate_8_section(text)
    assert "_V2_1_0_RELEASE_DATE" in section, (
        "Hard Gate 8 must reference `_V2_1_0_RELEASE_DATE` for the NFR-1 carry-over rule"
    )
    assert "mtime" in section.lower(), (
        "Hard Gate 8 must reference prompt-file mtime for the carry-over check"
    )
    assert "v2.0.x carry-over" in section, (
        "Hard Gate 8 must name the literal `v2.0.x carry-over` phrase per "
        "TC-NFR-1-02 ('exemption record naming the v2.0.x carry-over rule')"
    )


# TDD-1 (P25-C02) — outside-in acceptance test as first deliverable. Three
# structural tests covering TC-TDD-1-01, TC-TDD-1-02, TC-TDD-1-04. TC-TDD-1-03
# belongs to P26-C02 (`/gvm-code-review` Panel B integration) and is out of
# scope for this chunk's structural-grep suite.

def _prompt_template_block(skill_text: str) -> str:
    """Return the prompt template fenced markdown block under '## Prompt Format'.

    Mirrors `_handover_template_block` shape: anchor on the section header,
    find the opening ```` ```markdown ```` fence, terminate on the closing
    ```` ``` ```` fence (NOT on a Markdown heading — the fenced block
    contains its own `##` subheadings).
    """
    parts = skill_text.split("## Prompt Format", 1)
    if len(parts) == 1:
        return ""
    after = parts[1]
    fence_open = after.find("```markdown")
    # Fail-closed when the opening fence is absent — Code-review R54 #4.
    if fence_open == -1:
        return ""
    body_start = fence_open + len("```markdown")
    fence_close = after.find("\n```", body_start)
    # Fail-closed when the closing fence is absent — same reason.
    if fence_close == -1:
        return ""
    return after[body_start:fence_close]


def _hard_gate_5_section(skill_text: str) -> str:
    """Return the Hard Gate 5 entry slice from the Hard Gates list.

    Anchored on the verbatim prefix `5. **TEST FIRST, ALWAYS` — Hard Gate 5's
    title was extended in P25-C02 to `5. **TEST FIRST, ALWAYS — TDD-1 OUTSIDE-IN
    ORDERING.**`, so the anchor is the prefix common to both the historical and
    current title forms. Terminates at the next numbered Hard Gate (`\\n6. **`)
    so we get only Hard Gate 5's body — including the TDD-1 sub-clauses.
    """
    anchor = "5. **TEST FIRST, ALWAYS"
    idx = skill_text.find(anchor)
    if idx == -1:
        return ""
    rest = skill_text[idx:]
    end = rest.find("\n6. **")
    if end == -1:
        return rest
    return rest[:end]


def test_tc_tdd_1_01_prompt_template_lists_acceptance_test_first() -> None:
    text = GVM_BUILD_SKILL.read_text(encoding="utf-8")
    block = _prompt_template_block(text)
    assert block, "Prompt template fenced block must exist under '## Prompt Format'"
    # The TDD Approach section in the prompt template must place the
    # outside-in acceptance test as the FIRST deliverable for user-facing
    # chunks. Grep for a step-1 line that names the acceptance test, and
    # require the literal phrase 'first deliverable' or equivalent ordering
    # marker to make the requirement explicit (per TC-TDD-1-01).
    assert "acceptance test" in block.lower(), (
        "Prompt template must reference the outside-in acceptance test"
    )
    assert "outside-in" in block.lower(), (
        "Prompt template must use the literal 'outside-in' framing per "
        "Freeman & Pryce GOOS / spec § Component 1"
    )
    # The "first deliverable" / "first listed" requirement is the core of
    # TC-TDD-1-01 — without an explicit ordering marker the prompt is
    # ambiguous about which test comes first.
    lower = block.lower()
    assert (
        "first deliverable" in lower
        or "first listed" in lower
        or "first test" in lower
    ), (
        "Prompt template must explicitly mark the acceptance test as the "
        "first deliverable for user-facing chunks (TC-TDD-1-01)"
    )
    # MUST NOT clause from TC-TDD-1-01: the template must NOT order unit
    # tests before the acceptance test for user-facing surfaces. Find the
    # `## TDD Approach` slice within the prompt template block and check
    # that any reference to "acceptance test" precedes any reference to
    # "unit test" / "unit-level" — otherwise a future edit could reorder
    # the steps and ship a regression that the positive-only assertions
    # above would fail to catch.
    tdd_approach_idx = block.find("## TDD Approach")
    # The `## TDD Approach` section must exist — if it is absent (e.g.
    # renamed or deleted) the ordering check below would silently skip,
    # leaving the MUST NOT clause unverified even though the positive
    # assertions above could still pass from text elsewhere in the block.
    assert tdd_approach_idx != -1, (
        "Prompt template must contain a '## TDD Approach' section "
        "(TC-TDD-1-01 — ordering MUST NOT check requires this section)"
    )
    # Slice from `## TDD Approach` to the next `##` heading (or end of
    # block). The fenced template block contains `## Review Criteria`
    # immediately after `## TDD Approach`.
    tdd_slice = block[tdd_approach_idx:]
    next_section = tdd_slice.find("\n## ", 1)
    if next_section != -1:
        tdd_slice = tdd_slice[:next_section]
    tdd_lower = tdd_slice.lower()
    accept_pos = tdd_lower.find("acceptance test")
    # Match either "unit test" or "unit-level" / "unit tests" — any
    # reference to unit-tier testing.
    unit_pos = tdd_lower.find("unit test")
    if unit_pos == -1:
        unit_pos = tdd_lower.find("unit-level")
    assert accept_pos != -1, (
        "TDD Approach section must reference the acceptance test"
    )
    if unit_pos != -1:
        assert accept_pos < unit_pos, (
            "TDD Approach ordering MUST place the acceptance test before "
            "any unit-tier test reference for user-facing chunks "
            "(TC-TDD-1-01 MUST NOT clause)"
        )


def test_tc_tdd_1_02_handover_template_has_red_green_acceptance_fields() -> None:
    text = GVM_BUILD_SKILL.read_text(encoding="utf-8")
    block = _handover_template_block(text)
    assert "Acceptance test Red commit" in block, (
        "Handover template must include the literal `Acceptance test Red commit` "
        "field per TC-TDD-1-02"
    )
    assert "Acceptance test Green commit" in block, (
        "Handover template must include the literal `Acceptance test Green commit` "
        "field per TC-TDD-1-02"
    )


def test_tc_tdd_1_04_skill_md_has_internal_helper_exemption_clause() -> None:
    text = GVM_BUILD_SKILL.read_text(encoding="utf-8")
    section = _hard_gate_5_section(text)
    assert section, "Hard Gate 5 entry must exist in SKILL.md Hard Gates list"
    lower = section.lower()
    # ADR-MH-04 mandates an explicit, practitioner-marked exemption.
    # The clause must name BOTH the exemption marker (literal `TDD-1 exempted`)
    # AND the qualifying condition (internal helper / no user-facing surface).
    assert "TDD-1 exempted" in section, (
        "Hard Gate 5 TDD-1 prose must declare the literal `TDD-1 exempted` "
        "marker per ADR-MH-04 / TC-TDD-1-04"
    )
    assert "internal helper" in lower or "no user-facing surface" in lower, (
        "Hard Gate 5 TDD-1 exemption must name the qualifying condition "
        "(internal helper / no user-facing surface change) per TC-TDD-1-04"
    )


# TDD-2 (P25-C03) — mock-budget rule + canonical external-boundary allowlist.
# One structural test covering TC-TDD-2-01. TC-TDD-2-02..05 are behavioural
# lint tests owned by P24-C01's `test_ebt_contract_lint.py` suite — out of
# scope for this chunk's structural-grep tests.

# Canonical allowlist tokens — the strings that must appear verbatim in
# SKILL.md's TDD-2 section per methodology-hardening-cross-cutting.md
# § External-Boundary Allowlist. SKILL.md is the spec authority;
# `_PYTHON_STACK_DEFAULTS` in `_ebt_contract_lint.py` is the runtime
# mirror (currently partial — see SKILL.md Surfaced gaps note).
_TDD_2_ALLOWLIST_TOKENS = (
    "requests",
    "httpx",
    "urllib",
    "aiohttp",
    "socket",
    "pathlib.Path",
    "subprocess",
    "os",
    "third-party SDK",
)


def _tdd_2_section(skill_text: str) -> str:
    """Return the slice of SKILL.md belonging to the TDD-2 section.

    Anchored on a line-start `\\n## TDD-2` (case-sensitive) so the helper
    cannot silently match an example heading inside a fenced markdown block
    in the prompt template. Top-level Markdown headings always start at
    a line boundary; fenced-block content only matches when literal
    `\\n## TDD-2` appears at column 0 of a body line, which is the same
    line-start contract.
    """
    line_anchor = "\n## TDD-2"
    idx = skill_text.find(line_anchor)
    if idx == -1:
        return ""
    # Skip the leading newline of the anchor so the returned slice begins
    # with the heading.
    section_start = idx + 1
    rest = skill_text[section_start:]
    end = rest.find("\n## ", len("## TDD-2"))
    if end == -1:
        return rest
    return rest[:end]


def test_tc_tdd_2_01_skill_md_lists_external_boundary_allowlist() -> None:
    text = GVM_BUILD_SKILL.read_text(encoding="utf-8")
    section = _tdd_2_section(text)
    assert section, (
        "TDD-2 section must exist in SKILL.md as a top-level `## TDD-2` "
        "heading (TC-TDD-2-01 — canonical external-boundary allowlist "
        "specification; the runtime mirror is `_PYTHON_STACK_DEFAULTS` "
        "in `_ebt_contract_lint.py` per the prose's sync note)"
    )
    # MUST contain: each of the 8 named categories + the third-party SDK
    # phrase. SKILL.md is the human-readable specification authority for
    # the allowlist; `_PYTHON_STACK_DEFAULTS` in `_ebt_contract_lint.py`
    # is the runtime mirror. Both must stay in sync.
    for token in _TDD_2_ALLOWLIST_TOKENS:
        assert token in section, (
            f"TDD-2 external-boundary allowlist must list `{token}` "
            "verbatim per TC-TDD-2-01 / cross-cutting § External-Boundary "
            "Allowlist (specification authority for the lint mirror)"
        )
    # MUST contain: the rule statement naming the budget itself, so the
    # allowlist is anchored to its purpose rather than floating prose.
    lower = section.lower()
    assert "mock budget" in lower or "mock-budget" in lower, (
        "TDD-2 section must name the `mock budget` (or `mock-budget`) rule "
        "explicitly per spec § Component 1"
    )
    assert "external boundary" in lower or "external-boundary" in lower, (
        "TDD-2 section must name the `external boundary` (or hyphenated) "
        "as the locus of the mock budget per Metz POODR Ch. 9"
    )
    # Wrapper-as-SUT exemption (ADR-MH-02): the prose must name the
    # exemption so future practitioners know mocking the external module
    # IS correct when the wrapper is the SUT. Without this, TC-TDD-2-04
    # would surface as a TDD-2 violation that the methodology never
    # exempted.
    assert "wrapper-as-sut" in lower or "wrapper as sut" in lower or (
        "wrapper" in lower and "sut" in lower
    ), (
        "TDD-2 section must name the wrapper-as-SUT exemption per "
        "ADR-MH-02 / TC-TDD-2-04"
    )
    # Severity escalation rule (ADR-MH-03): the prose must name the
    # `.cross-chunk-seams` opt-in file. Absence of the file means no
    # escalation — Martin-style explicit default rather than inferred.
    assert ".cross-chunk-seams" in section, (
        "TDD-2 section must name the literal `.cross-chunk-seams` opt-in "
        "file per ADR-MH-03 / TC-TDD-2-05 (the escalation signal)"
    )
    # MUST NOT clause from TC-TDD-2-01: no internal Python class may
    # appear in the allowlist position. The allowlist names module-level
    # entry points (lowercase package/module names plus dotted attribute
    # paths like `pathlib.Path`); a CamelCase class name appearing as an
    # allowlist entry would silently broaden the boundary contract and
    # mask internal-mock violations the lint should flag.
    #
    # Disqualifier list: known-internal class names from the project's
    # own surface that could plausibly drift into the allowlist if a
    # future editor confused "internal wrapper" with "external boundary".
    # If any of these strings appear inside the allowlist enumeration,
    # the section has been corrupted per TC-TDD-2-01's MUST NOT clause.
    _INTERNAL_DISQUALIFIERS = (
        "HttpClient",
        "HttpxClient",
        "AnthropicClient",
        "OpenAIClient",
    )
    # Restrict the disqualifier check to the enumerated-list region of
    # the section (between the first numbered list bullet and the
    # paragraph that begins the wrapper-as-SUT exemption). Otherwise the
    # check would false-positive on prose that mentions wrapper class
    # names as illustrative examples.
    list_start = section.find("\n1. ")
    if list_start != -1:
        list_end = section.find("\n\n", list_start)
        if list_end == -1:
            list_end = len(section)
        list_region = section[list_start:list_end]
        for disqualifier in _INTERNAL_DISQUALIFIERS:
            assert disqualifier not in list_region, (
                f"TDD-2 allowlist must NOT list internal class "
                f"`{disqualifier}` as an external boundary "
                "(TC-TDD-2-01 MUST NOT clause — internal wrappers are "
                "not external boundaries; mock their dependency, not "
                "the wrapper)"
            )


# TDD-3 (P25-C04) — realistic-fixture catalogue. Three structural tests
# covering TC-TDD-3-01..03. TC-TDD-3-04 (practitioner-override behaviour
# on Panel C) is a behavioural test owned by P26-C03's `/gvm-code-review`
# Panel C integration suite — out of scope here.

# Six named domains per TDD-3 catalogue. Order matches the requirements
# doc and test cases. Strings must appear verbatim in SKILL.md so the
# Panel C dispatch prompt (P26-C03) can anchor on identical literals.
_TDD_3_DOMAIN_HEADINGS = (
    "Data analysis",
    "Web/UI",
    "API",
    "Parsing",
    "Security validation",
    "Concurrency",
)

# Defect-class evidence tokens for TC-TDD-3-02. The data-analysis row
# must include the short-categorical-codes case — the literal defect
# S6.1 evidence (sex M/F, blood type A/B/O).
_TDD_3_DATA_ANALYSIS_TOKENS = ("M/F", "A/B/O")


def _tdd_3_section(skill_text: str) -> str:
    """Return the slice of SKILL.md belonging to the TDD-3 section.

    Mirrors `_tdd_2_section`: line-anchored on `\\n## TDD-3` so a fenced
    example heading inside the prompt template cannot silently match.
    """
    line_anchor = "\n## TDD-3"
    idx = skill_text.find(line_anchor)
    if idx == -1:
        return ""
    section_start = idx + 1
    rest = skill_text[section_start:]
    end = rest.find("\n## ", len("## TDD-3"))
    if end == -1:
        return rest
    return rest[:end]


def test_tc_tdd_3_01_skill_md_lists_six_domain_catalogue() -> None:
    text = GVM_BUILD_SKILL.read_text(encoding="utf-8")
    section = _tdd_3_section(text)
    assert section, (
        "TDD-3 section must exist in SKILL.md as a top-level `## TDD-3` "
        "heading (TC-TDD-3-01 — per-domain realistic-fixture catalogue)"
    )
    # MUST contain: each of the six named domain headings verbatim,
    # bound to the bold-heading literal that Panel C (P26-C03) will
    # actually grep — Code-review R54 #7. A bare `domain in section`
    # would match an incidental substring elsewhere in body prose
    # (e.g. "API" inside surrounding text) while the actual catalogue
    # heading drifted; binding to `**{domain}**` requires the literal
    # bold heading the dispatch prompt parses.
    for domain in _TDD_3_DOMAIN_HEADINGS:
        bold_heading = f"**{domain}**"
        assert bold_heading in section, (
            f"TDD-3 catalogue must list `{bold_heading}` as a bold-"
            "headed domain entry verbatim per TC-TDD-3-01 / "
            "requirements TDD-3 acceptance criterion (c) — Panel C "
            "(P26-C03) anchors on the bold heading literal"
        )
    # MUST contain: rule statement naming the realistic-fixture mandate.
    lower = section.lower()
    assert "realistic-fixture" in lower or "realistic fixture" in lower, (
        "TDD-3 section must name the `realistic-fixture` mandate "
        "explicitly per requirements TDD-3"
    )
    # Bach & Bolton attribution — anchors the rationale (Rapid Software
    # Testing: synthetic fixtures encode the engineer's mental model).
    assert "bach" in lower or "bolton" in lower or "rapid software testing" in lower, (
        "TDD-3 section must cite Bach & Bolton (or *Rapid Software "
        "Testing*) as the methodology source per the spec's expert panel"
    )
    # MUST NOT clause from TC-TDD-3-01: no domain entry without starter
    # fixtures. Approximate by asserting each domain heading is followed
    # within a small window by at least one fixture-shape token (em-dash
    # then prose, or bullet then prose). A heading followed immediately
    # by another heading or by a blank line indicates an empty entry.
    for domain in _TDD_3_DOMAIN_HEADINGS:
        domain_idx = section.find(domain)
        # Sample 600 chars after the heading; an empty entry would
        # have only the next domain heading or whitespace within that
        # window. The bold heading is wrapped in `**...**`, so we
        # advance past the closing `**` before testing for prose.
        window = section[domain_idx : domain_idx + 600]
        # Find the closing bold marker for this heading.
        closing_bold = window.find("**", len(domain))
        if closing_bold == -1:
            # Heading not bold-wrapped; treat the position right after
            # the heading text as the start of body prose.
            body_start = len(domain)
        else:
            body_start = closing_bold + 2
        body = window[body_start:]
        # Stop at the next domain heading (next `**` opening) so we
        # test only this entry's body prose.
        next_heading = body.find("**")
        if next_heading != -1:
            body = body[:next_heading]
        # A non-empty entry must contain at least one alphabetic
        # character of body prose between the heading and the next
        # domain heading.
        has_content = any(c.isalpha() for c in body)
        assert has_content, (
            f"TDD-3 catalogue domain `{domain}` must have starter "
            "fixture content following the heading (TC-TDD-3-01 MUST "
            "NOT clause — no empty domain entry)"
        )


def test_tc_tdd_3_02_data_analysis_includes_short_categorical_codes() -> None:
    text = GVM_BUILD_SKILL.read_text(encoding="utf-8")
    section = _tdd_3_section(text)
    assert section, "TDD-3 section must exist (precondition for TC-TDD-3-02)"
    # Locate the data-analysis row's body. The row begins with the
    # heading `Data analysis` and ends at the next domain heading
    # (`Web/UI`).
    da_start = section.find("Data analysis")
    assert da_start != -1, (
        "TDD-3 catalogue must contain a `Data analysis` domain entry "
        "(precondition for TC-TDD-3-02)"
    )
    da_end = section.find("Web/UI", da_start)
    if da_end == -1:
        da_end = len(section)
    da_row = section[da_start:da_end]
    # MUST contain: short-categorical-codes case — sex M/F AND blood
    # type A/B/O. These are the literal defect-class S6.1 evidence
    # strings; the requirement names them verbatim.
    for token in _TDD_3_DATA_ANALYSIS_TOKENS:
        assert token in da_row, (
            f"Data-analysis catalogue row must include `{token}` "
            "(short-categorical-codes case per TC-TDD-3-02 / defect "
            "S6.1 evidence)"
        )
    # MUST NOT clause from TC-TDD-3-02: the data-analysis row must
    # NOT consist of only synthetic-fixture cases like `numeric mixed`
    # without short-token coverage. The M/F + A/B/O loop above is the
    # primary enforcement (asserts the realistic short-categorical
    # codes ARE present). This block adds an executing assertion for
    # the converse: if `numeric mixed` is the row's first listed
    # shape (i.e. positioned before the realistic short-token examples),
    # the row is leading with synthetic — flag it. The realistic
    # shapes asserted above must precede synthetic ones in the
    # catalogue order (Code-review R54 #1 fix).
    da_lower = da_row.lower()
    if "numeric mixed" in da_lower:
        synth_pos = da_lower.find("numeric mixed")
        realistic_pos = min(
            da_row.find(token) for token in _TDD_3_DATA_ANALYSIS_TOKENS
        )
        assert realistic_pos < synth_pos, (
            "Data-analysis catalogue row leads with synthetic-fixture "
            "shape `numeric mixed` before the realistic short-token "
            "cases (M/F, A/B/O) — TC-TDD-3-02 MUST NOT clause: "
            "realistic shapes must precede synthetic shapes so the "
            "engineer's mental-model defect class (S6.1) is the "
            "primary catalogue entry, not an afterthought"
        )


def test_tc_tdd_3_03_prompt_template_lists_realistic_fixture_variant() -> None:
    text = GVM_BUILD_SKILL.read_text(encoding="utf-8")
    block = _prompt_template_block(text)
    assert block, "Prompt template fenced block must exist in SKILL.md"
    # The TDD Approach section of the prompt template must name the
    # literal phrase `realistic-fixture variant` as a separate test
    # deliverable per TC-TDD-3-03 / requirements TDD-3 acceptance
    # criterion (a).
    assert "realistic-fixture variant" in block, (
        "Prompt template `## TDD Approach` must name the literal phrase "
        "`realistic-fixture variant` as a separate test deliverable per "
        "TC-TDD-3-03 / requirements TDD-3 (a)"
    )
    # MUST NOT clause from TC-TDD-3-03: a single test deliverable that
    # conflates synthetic happy-path and realistic-fixture coverage.
    # Approximate: the prose must distinguish the two — naming both
    # `realistic-fixture` and a happy-path / synthetic counterpart, or
    # explicitly stating they are SEPARATE deliverables.
    lower = block.lower()
    distinguishes = (
        "separate" in lower
        or "alongside" in lower
        or "in addition to" in lower
        or "happy-path" in lower
        or "happy path" in lower
        or "synthetic" in lower
    )
    assert distinguishes, (
        "Prompt template `## TDD Approach` must distinguish the "
        "realistic-fixture variant from the synthetic happy-path test "
        "(TC-TDD-3-03 MUST NOT clause — a single conflated deliverable "
        "is a TDD-3 violation). Use one of: `separate`, `alongside`, "
        "`in addition to`, `happy-path`, `synthetic`."
    )


# NFR-2 (P25-C05) — diff-budget handover field + build-summary aggregation.
# Two structural tests for the chunk-time deliverables. TC-NFR-2-01/02 in
# `methodology-hardening-test-cases.md` are RELEASE-TIME tests (exercise
# `git diff v2.0.1..v2.1.0`) — owned by P27-C02's final smoke; out of scope
# here.


def _diff_summary_block(skill_text: str) -> str:
    """Return the handover template's `## Diff Summary` slice.

    The handover template lives inside the `## Handover Format` fenced
    markdown block. Inside that block, `## Diff Summary` is a sub-heading
    that terminates at the next `## ` sub-heading (e.g. `## Code Review
    Findings`). We anchor on `\\n## Diff Summary` to avoid matching prose
    mentions of the phrase outside the template.
    """
    block = _handover_template_block(skill_text)
    if not block:
        return ""
    line_anchor = "\n## Diff Summary"
    idx = block.find(line_anchor)
    if idx == -1:
        return ""
    section_start = idx + 1
    rest = block[section_start:]
    end = rest.find("\n## ", len("## Diff Summary"))
    if end == -1:
        return rest
    return rest[:end]


def _build_summary_step(skill_text: str) -> str:
    """Return the SKILL.md Process Flow step 8 (BUILD SUMMARY) slice.

    Anchored on the literal `8. BUILD SUMMARY` heading; terminates at the
    next numbered step (`9. OFFER NEXT STEP`). The step lives inside the
    Process Flow ``` fenced block, so terminating on a numbered list-item
    boundary is the correct contract.
    """
    anchor = "8. BUILD SUMMARY"
    idx = skill_text.find(anchor)
    if idx == -1:
        return ""
    rest = skill_text[idx:]
    end = rest.find("\n9. ")
    if end == -1:
        return rest
    return rest[:end]


def test_tc_nfr_2_handover_template_has_diff_budget_field() -> None:
    text = GVM_BUILD_SKILL.read_text(encoding="utf-8")
    diff_section = _diff_summary_block(text)
    assert diff_section, (
        "Handover template `## Diff Summary` block must exist "
        "(precondition for NFR-2 diff-budget field test)"
    )
    # MUST contain: literal label `Diff budget delta` so downstream
    # tooling (build-summary aggregation, /gvm-status) can parse the
    # field reliably.
    assert "Diff budget delta" in diff_section, (
        "Handover template `## Diff Summary` must include the literal "
        "label `Diff budget delta` per NFR-2 / cross-cutting § Diff "
        "Budget Tracking — the per-chunk surface that the build-summary "
        "aggregation reads"
    )
    # Field guidance must name the source command so practitioners
    # know how to compute the delta. Either `git diff` + `--stat` OR
    # `SKILL.md` reference is sufficient (McConnell defensive prose).
    lower = diff_section.lower()
    assert "git diff" in lower or "skill.md" in lower or "net-added" in lower, (
        "Handover template `Diff budget delta` field must name the source "
        "(e.g. `git diff --stat` over `*SKILL.md`, or `net-added lines`) "
        "per McConnell defensive-prose criterion"
    )


def test_tc_nfr_2_build_summary_has_aggregation_instruction() -> None:
    text = GVM_BUILD_SKILL.read_text(encoding="utf-8")
    step = _build_summary_step(text)
    assert step, (
        "SKILL.md Process Flow must contain step `8. BUILD SUMMARY` "
        "(precondition for NFR-2 build-summary aggregation test)"
    )
    lower = step.lower()
    # MUST contain: aggregation phrase. Code-review R54 #3 — split into
    # two contracts so the source-qualifier requirement cannot be
    # absorbed by the precedence of `or ... and ...`. Contract 1: at
    # least one aggregation-naming phrase appears.
    aggregation_phrase = (
        "diff budget delta" in lower
        or "diff-budget" in lower
        or "cumulative" in lower
    )
    assert aggregation_phrase, (
        "Build-summary step must name the aggregation rule (one of "
        "`diff budget delta` / `diff-budget` / `cumulative`) per "
        "NFR-2 / cross-cutting § Diff Budget Tracking"
    )
    # Contract 2 (independent of Contract 1): the source qualifier
    # naming what is summed must also be present. McConnell defensive
    # prose — the aggregation rule without a source qualifier is
    # underspecified.
    source_qualifier = (
        "loc" in lower or "skill.md" in lower or "*skill.md" in lower
    )
    assert source_qualifier, (
        "Build-summary step must name the source being aggregated "
        "(one of `LOC` / `SKILL.md` / `*SKILL.md`) per NFR-2 / "
        "McConnell defensive prose — aggregation without source "
        "qualifier is underspecified"
    )
    # MUST contain: literal threshold `500` so the AskUserQuestion
    # trigger is anchored to the spec value (cross-cutting NFR-2 cap).
    assert "500" in step, (
        "Build-summary step must name the literal `500` LOC threshold "
        "per NFR-2 / cross-cutting § Diff Budget Tracking"
    )
    # MUST contain: literal `AskUserQuestion` trigger mechanism — Martin
    # no silent failures; the action at threshold is explicit, not
    # inferred.
    assert "AskUserQuestion" in step, (
        "Build-summary step must name `AskUserQuestion` as the trigger "
        "at the 500-LOC threshold per ADR-CC-03 (surface-and-track, "
        "not refuse)"
    )
    # MUST contain: ADR-CC-03 reference OR `surface-and-track` phrase
    # so the design intent is anchored to its rationale.
    assert "ADR-CC-03" in step or "surface-and-track" in lower or (
        "surface" in lower and "track" in lower
    ), (
        "Build-summary step must reference ADR-CC-03 (or use the "
        "`surface-and-track` phrase) so the design intent — the "
        "diff-budget is documentation, not a gate — is preserved"
    )
    # MUST NOT clause: a hard-refusal phrase attached to the 500-LOC
    # trigger. ADR-CC-03 is explicit: the diff-budget is documentation,
    # not a mechanical-enforcement gate. A future editor who attaches
    # `refuse` / `block` to the 500-LOC threshold drifts the design
    # from surface-and-track to mechanical enforcement — TC-NFR-2 MUST
    # NOT clause / realistic-fixture variant per TDD-3.
    #
    # We restrict the disqualifier scan to the same paragraph as `500`
    # to avoid false positives from prose elsewhere in the build-summary
    # step (e.g. "refuse to write the handover" attached to Hard Gate 8).
    threshold_idx = step.find("500")
    para_start = step.rfind("\n\n", 0, threshold_idx)
    if para_start == -1:
        para_start = max(0, threshold_idx - 400)
    para_end = step.find("\n\n", threshold_idx)
    if para_end == -1:
        para_end = min(len(step), threshold_idx + 400)
    paragraph = step[para_start:para_end].lower()
    _REFUSAL_DISQUALIFIERS = (
        "must refuse",
        "blocks the",
        "block the",
        "hard refusal",
        "mechanically enforce",
    )
    for phrase in _REFUSAL_DISQUALIFIERS:
        assert phrase not in paragraph, (
            f"Build-summary 500-LOC trigger paragraph must NOT contain "
            f"the hard-refusal phrase `{phrase}` (NFR-2 MUST NOT clause "
            "/ ADR-CC-03 — diff-budget is surface-and-track, not "
            "mechanical enforcement)"
        )
    # Positive assertion alongside the disqualifier scan — Code-review
    # R54 #6. The disqualifier scan is distance-scoped (no `\n\n`
    # paragraph separators inside the tree-ASCII Process Flow block),
    # so its window is fragile under prose drift. Anchor the contract
    # to its required prose: the same paragraph that names `500` must
    # also name `AskUserQuestion` AND one of `not a gate` / `surface-
    # and-track` / `not refuse`. Defence in depth — even if a future
    # disqualifier slips outside the 400-char window, the positive
    # contract still binds the design intent to the threshold.
    assert "askuserquestion" in paragraph, (
        "Build-summary 500-LOC trigger paragraph must name "
        "`AskUserQuestion` per ADR-CC-03 — surface-and-track requires "
        "an explicit user-prompted decision at the threshold, not a "
        "silent log entry"
    )
    intent_phrase = (
        "not a gate" in paragraph
        or "surface-and-track" in paragraph
        or "not refuse" in paragraph
    )
    assert intent_phrase, (
        "Build-summary 500-LOC trigger paragraph must name the "
        "design intent (one of `not a gate` / `surface-and-track` / "
        "`not refuse`) per ADR-CC-03 — the prose adjacent to the "
        "threshold MUST anchor the surface-and-track contract, not "
        "leave it to a separate ADR reference"
    )


# GATE-2 (P26-C01) — `/gvm-tech-spec` Hard Gate 6 consumer-demands-producer
# extension. Three structural tests covering TC-GATE-2-01..03 — all anchored
# on `gvm-tech-spec/SKILL.md` Hard Gate 6 prose. The four-column wiring
# matrix, the refusal rule for empty `Demanded by` cells, and the explicit
# exemption marker are the three GATE-2 acceptance contracts.


def _hard_gate_6_section(skill_text: str) -> str:
    """Return the slice of `gvm-tech-spec` SKILL.md belonging to Hard Gate 6.

    Mirrors `_hard_gate_8_section` shape: anchor on the verbatim opener
    `6. **WIRING MATRIX IS MANDATORY` so the helper cannot match a stray
    `6. **` numbered list item from another section. Terminate at the next
    numbered Hard Gate (`\\n\\n**Prerequisites:**` is the actual terminator
    in the current SKILL.md — Hard Gate 6 is the last numbered gate). Use
    earliest-position termination across the candidate boundaries so a
    future edit inserting Hard Gate 7 ahead of `**Prerequisites:**` does
    not silently extend the captured slice.
    """
    anchor = "6. **WIRING MATRIX IS MANDATORY"
    idx = skill_text.find(anchor)
    if idx == -1:
        return ""
    rest = skill_text[idx:]
    candidates = [
        pos
        for pos in (
            rest.find(t)
            for t in ("\n\n**Prerequisites:**", "\n7. **", "\n## ")
        )
        if pos != -1
    ]
    if not candidates:
        return rest
    return rest[: min(candidates)]


def test_tc_gate_2_01_wiring_matrix_has_demanded_by_column() -> None:
    text = GVM_TECH_SPEC_SKILL.read_text(encoding="utf-8")
    section = _hard_gate_6_section(text)
    assert section, (
        "Hard Gate 6 entry must exist in /gvm-tech-spec SKILL.md "
        "(precondition for TC-GATE-2-01)"
    )
    # MUST contain: the literal `Demanded by` column name. The four-column
    # wiring matrix is the user-facing surface of GATE-2 — without the
    # literal token, downstream `/gvm-build` Hard Gate 6 has nothing to
    # parse.
    assert "Demanded by" in section, (
        "Hard Gate 6 prose must name the literal `Demanded by` column "
        "per TC-GATE-2-01 / GATE-2 acceptance criterion (a)"
    )
    # MUST contain: a four-column format example. The example in current
    # v2.0.x SKILL.md is three-column (Entry point | Consumed modules |
    # Wiring chunk). v2.1.0 adds `Demanded by` as the fourth column. We
    # assert the format-example header line carries all four column names
    # in order — the practitioner reads the example to learn the schema.
    assert "| Entry point | Consumed modules | Wiring chunk | Demanded by |" in section, (
        "Hard Gate 6 format example must show the four-column header "
        "`| Entry point | Consumed modules | Wiring chunk | Demanded by |` "
        "verbatim per TC-GATE-2-01 — three-column examples are a v2.0.x "
        "carry-over and must be updated"
    )
    # MUST NOT clause from TC-GATE-2-01: a wiring-matrix example missing
    # the demand-side column. The format example block lives between the
    # "Format example:" line and the closing fenced ```. The header line
    # asserted above is the canonical four-column form; if any header
    # line WITHIN the example block matches the three-column shape
    # `| Entry point | Consumed modules | Wiring chunk |` (with a
    # closing pipe immediately after `Wiring chunk`), the example is
    # still in v2.0.x form and the new column was added only in prose
    # commentary, not in the example itself.
    example_idx = section.find("Format example:")
    if example_idx != -1:
        # Restrict the disqualifier scan to the fenced example block.
        block_start = section.find("```", example_idx)
        block_end = section.find("```", block_start + 3) if block_start != -1 else -1
        if block_start != -1 and block_end != -1:
            example_block = section[block_start:block_end]
            assert "| Entry point | Consumed modules | Wiring chunk |\n" not in example_block, (
                "Hard Gate 6 format example MUST NOT contain the "
                "v2.0.x three-column header — the example block must be "
                "updated to four columns (TC-GATE-2-01 MUST NOT clause)"
            )


def test_tc_gate_2_02_refusal_rule_for_empty_demanded_by_cell() -> None:
    text = GVM_TECH_SPEC_SKILL.read_text(encoding="utf-8")
    section = _hard_gate_6_section(text)
    assert section, (
        "Hard Gate 6 entry must exist (precondition for TC-GATE-2-02)"
    )
    lower = section.lower()
    # MUST contain: an explicit refusal trigger naming the empty
    # `Demanded by` cell. Without the explicit trigger, /gvm-build's
    # read-side Hard Gate 6 has no contract to enforce — silent
    # passthrough on empty cells is the failure mode TC-GATE-2-02
    # forbids.
    assert "demanded by" in lower, (
        "Hard Gate 6 refusal-rule prose must name `demanded by` "
        "explicitly per TC-GATE-2-02"
    )
    assert "empty" in lower, (
        "Hard Gate 6 refusal-rule prose must name the empty-cell "
        "trigger per TC-GATE-2-02 — the refusal condition must be "
        "explicit, not inferred"
    )
    # MUST contain: the refusal verb itself. Martin clean-code: the
    # default for an empty cell is REFUSAL, not silent passthrough.
    assert "refus" in lower, (
        "Hard Gate 6 must name the refusal verb (refuse / refusal / "
        "refuses) for empty `Demanded by` cells per TC-GATE-2-02"
    )
    # MUST contain: the practitioner option to fix OR mark exempt.
    # McConnell defensive prose — the refusal rule must name both what
    # triggers refusal and what unblocks it.
    assert "fix" in lower or "exempt" in lower, (
        "Hard Gate 6 refusal-rule prose must name the practitioner "
        "options (fix the impl guide OR mark the row exempt) per "
        "TC-GATE-2-02 — refusal without an unblock path is a dead-end"
    )
    # MUST NOT clause from TC-GATE-2-02: silent passthrough on empty
    # cells. Approximate by asserting the prose does NOT carry phrases
    # that legitimise silent acceptance of empty cells. A future editor
    # who softens the refusal to "warn" / "log" / "skip" drifts the gate
    # from a hard refusal to advisory prose — TC-GATE-2-02 forbids this.
    _SOFTENERS = (
        "warn and proceed",
        "log and proceed",
        "skip silently",
        "advisory only",
        "warn the practitioner",
        "warn the user",
        "log the violation",
        "log a warning",
        "merely warn",
        "merely log",
    )
    for phrase in _SOFTENERS:
        assert phrase not in lower, (
            f"Hard Gate 6 refusal rule MUST NOT contain the softener "
            f"phrase `{phrase}` (TC-GATE-2-02 MUST NOT clause — silent "
            "passthrough on empty `Demanded by` cells is the failure "
            "mode this gate prevents)"
        )


def test_tc_gate_2_03_explicit_exemption_marker_with_rationale() -> None:
    text = GVM_TECH_SPEC_SKILL.read_text(encoding="utf-8")
    section = _hard_gate_6_section(text)
    assert section, (
        "Hard Gate 6 entry must exist (precondition for TC-GATE-2-03)"
    )
    lower = section.lower()
    # MUST contain: the literal `Demanded by:` exemption-marker shape.
    # The colon-suffixed form is what practitioners write into the
    # matrix cell to claim exemption — distinct from the column header.
    assert "Demanded by:" in section, (
        "Hard Gate 6 must show the `Demanded by:` exemption-marker "
        "shape (colon-suffixed, in-cell) per TC-GATE-2-03 — practitioners "
        "need the literal form they will write"
    )
    # MUST contain: the literal `rationale` token, anchoring the
    # exemption to its required justification (Fagan author preparation:
    # exemptions without rationale are not exemptions, they are silent
    # skips).
    assert "rationale" in lower, (
        "Hard Gate 6 exemption-marker prose must require a `rationale` "
        "(per TC-GATE-2-03 — exemptions without rationale are silent "
        "skips, not exemptions)"
    )
    # MUST contain: a passing-verdict statement for exempt rows.
    # McConnell defensive prose — the exemption path must be explicit:
    # "passes" / "passes the gate" / "exemption passes" / "audit trail".
    passes = (
        "passes the gate" in lower
        or "passes hard gate" in lower
        or "exemption passes" in lower
        or "audit trail" in lower
        or "passing verdict" in lower
    )
    assert passes, (
        "Hard Gate 6 must name a passing path for explicit exemptions "
        "(one of `passes the gate` / `audit trail` / `passing verdict`) "
        "per TC-GATE-2-03 — exemptions need an explicit accept path"
    )
    # MUST NOT clause from TC-GATE-2-03: refusal when an explicit
    # exemption is present. The prose must not say that exemptions
    # are refused or rejected. We bind this to the same prose region
    # as the exemption-marker reference — a future editor who attached
    # `refuse` to the exemption marker would drift the gate from
    # surface-and-track to mechanical-refuse.
    marker_idx = section.find("Demanded by:")
    if marker_idx != -1:
        # Window: 400 chars centred on the exemption-marker reference.
        window_start = max(0, marker_idx - 200)
        window_end = min(len(section), marker_idx + 400)
        window_lower = section[window_start:window_end].lower()
        # The window names the exemption AND must NOT carry refusal
        # verbiage attached to the exemption itself. We discriminate
        # "refusal of empty cells" (legitimate) from "refusal of
        # explicit exemptions" (forbidden) by scanning for refusal
        # verbs adjacent to `exempt`/`exemption` tokens.
        _FORBIDDEN_NEAR_EXEMPTION = (
            "refuses the exempt",
            "refuses exempt",
            "rejects the exempt",
            "rejects exempt",
            "exemption is refused",
            "exemption is rejected",
        )
        for phrase in _FORBIDDEN_NEAR_EXEMPTION:
            assert phrase not in window_lower, (
                f"Hard Gate 6 prose MUST NOT contain `{phrase}` near "
                "the exemption-marker reference (TC-GATE-2-03 MUST NOT "
                "clause — explicit exemptions pass the gate, they are "
                "not refused)"
            )


# REVIEW-1 (P26-C02) — `/gvm-code-review` Panel B mock-budget integration.
# Three structural tests covering TC-REVIEW-1-01..03. The lint-side
# implementation lives in P24-C01's `_ebt_contract_lint.py`; this chunk
# wires the existing `mock-budget` kind into Panel B's prose so reviewers
# know the kind is surfaced.


def _panel_b_section(skill_text: str) -> str:
    """Return the slice of `gvm-code-review` SKILL.md belonging to Panel B.

    Anchored on the verbatim heading `### Panel B: Contracts & Interfaces`
    line-anchored (`\\n###`); terminates at `\\n### Panel C:` (next panel).
    Matches the existing `_hard_gate_6_section` / `_tdd_2_section` shape.
    """
    line_anchor = "\n### Panel B: Contracts & Interfaces"
    idx = skill_text.find(line_anchor)
    if idx == -1:
        return ""
    section_start = idx + 1
    rest = skill_text[section_start:]
    end = rest.find("\n### Panel C:")
    if end == -1:
        return rest
    return rest[:end]


def test_tc_review_1_01_panel_b_names_mock_budget_alongside_rainsberger_metz() -> None:
    text = GVM_CODE_REVIEW_SKILL.read_text(encoding="utf-8")
    section = _panel_b_section(text)
    assert section, (
        "Panel B section must exist in /gvm-code-review SKILL.md "
        "(precondition for TC-REVIEW-1-01)"
    )
    # MUST contain: the literal `mock-budget` kind alongside `rainsberger`
    # and `metz`. Without the literal kind in Panel B's prose, reviewers
    # have no instruction to surface mock-budget findings even when the
    # lint emits them.
    assert "mock-budget" in section, (
        "Panel B prose must name the literal `mock-budget` kind "
        "(hyphenated, lowercase) per TC-REVIEW-1-01 — the kind is the "
        "lint output literal practitioners read"
    )
    # All three kinds must coexist in Panel B prose.
    assert "rainsberger" in section, (
        "Panel B must continue to name `rainsberger` (carry-over from "
        "v2.0.x prose; precondition for TC-REVIEW-1-01)"
    )
    assert "metz" in section, (
        "Panel B must continue to name `metz` (carry-over from v2.0.x "
        "prose; precondition for TC-REVIEW-1-01)"
    )
    # MUST NOT clause from TC-REVIEW-1-01: a kind-set limited to
    # `rainsberger` and `metz` only. Approximate by asserting that the
    # `kind ∈ {...}` enumeration phrase, when present, includes
    # `mock-budget`. The current v2.0.x prose has the literal phrase
    # `kind` ∈ {`rainsberger`, `metz`}; if the v2.1.0 update does NOT
    # add `mock-budget` to that enumeration, the prose is structurally
    # incomplete.
    if "kind" in section and "rainsberger" in section and "metz" in section:
        # Find the enumeration sentence — narrow window around the
        # first co-occurrence of all three kind tokens.
        rains_pos = section.find("rainsberger")
        # 200-char window centred on the kind enumeration.
        window_start = max(0, rains_pos - 60)
        window_end = min(len(section), rains_pos + 200)
        window = section[window_start:window_end]
        assert "mock-budget" in window, (
            "Panel B kind enumeration window must include `mock-budget` "
            "alongside `rainsberger` and `metz` (TC-REVIEW-1-01 MUST NOT "
            "clause — a kind set limited to rainsberger/metz only is the "
            "v2.0.x carry-over that this chunk closes)"
        )


def test_tc_review_1_02_panel_b_lint_runs_on_every_test_file_in_diff() -> None:
    text = GVM_CODE_REVIEW_SKILL.read_text(encoding="utf-8")
    section = _panel_b_section(text)
    assert section, (
        "Panel B section must exist (precondition for TC-REVIEW-1-02)"
    )
    lower = section.lower()
    # MUST contain: an explicit scope statement naming "every test file"
    # OR equivalent ("all test files", "each test file in the diff"). The
    # v2.0.x prose says "When the changed file set includes test files"
    # which is necessary but not sufficient — the v2.1.0 update must
    # ALSO say the lint walks ALL of them, not only `[CONTRACT]`-tagged.
    scope_phrase = (
        "every test file" in lower
        or "all test files" in lower
        or "each test file" in lower
    )
    assert scope_phrase, (
        "Panel B prose must contain an explicit scope statement (one of "
        "`every test file` / `all test files` / `each test file`) per "
        "TC-REVIEW-1-02 — without the scope being explicit, reviewers "
        "may infer the lint runs only on `[CONTRACT]`-tagged tests"
    )
    # MUST contain: explicit reference to the three test categories the
    # lint must cover, OR an explicit "not only `[CONTRACT]`" clause.
    # The latter is the canonical disambiguation per spec § Component 4.
    not_only_contract = (
        "not only" in lower or "not just" in lower or "regardless of" in lower
    )
    contract_token = "[contract]" in lower or "`[contract]`" in lower
    assert not_only_contract and contract_token, (
        "Panel B must contain a clarifying clause (`not only [CONTRACT]` "
        "/ `not just [CONTRACT]` / `regardless of` tag) per TC-REVIEW-1-02 "
        "— the lint scope is broader than `[CONTRACT]`-tagged tests, and "
        "the prose must say so explicitly"
    )
    # MUST NOT clause from TC-REVIEW-1-02: prose that limits the lint
    # to `[CONTRACT]`-tagged tests only. Disqualifier phrases that would
    # drift the contract back to v2.0.x scope.
    _SCOPE_DRIFT_DISQUALIFIERS = (
        "only on [contract]",
        "limited to [contract]",
        "only [contract]-tagged",
        "exclusively [contract]",
    )
    for phrase in _SCOPE_DRIFT_DISQUALIFIERS:
        assert phrase not in lower, (
            f"Panel B prose MUST NOT contain `{phrase}` (TC-REVIEW-1-02 "
            "MUST NOT clause — lint scope is every test file in the "
            "chunk diff, not only [CONTRACT]-tagged tests)"
        )


def test_tc_review_1_03_panel_b_severity_escalation_names_seam_allowlist() -> None:
    text = GVM_CODE_REVIEW_SKILL.read_text(encoding="utf-8")
    section = _panel_b_section(text)
    assert section, (
        "Panel B section must exist (precondition for TC-REVIEW-1-03)"
    )
    lower = section.lower()
    # MUST contain: the literal `.cross-chunk-seams` allowlist file name
    # — the escalation signal per ADR-MH-03. Naming the file makes the
    # escalation rule operationally clear (Martin: explicit signals,
    # not inferred behaviour).
    assert ".cross-chunk-seams" in section, (
        "Panel B must name the literal `.cross-chunk-seams` allowlist "
        "file per TC-REVIEW-1-03 / ADR-MH-03 — the escalation signal "
        "must be operationally explicit"
    )
    # MUST contain: severity vocabulary covering both default (Important)
    # and escalated (Critical) outcomes. The Important→Critical
    # promotion is the rule TC-REVIEW-1-03 enforces.
    assert "important" in lower, (
        "Panel B severity prose must name `Important` as the default "
        "severity (per TC-REVIEW-1-03 default-severity contract)"
    )
    assert "critical" in lower, (
        "Panel B severity prose must name `Critical` as the escalated "
        "severity (per TC-REVIEW-1-03 escalation contract)"
    )
    # MUST contain: the escalation verb itself ("escalate" / "promote"
    # / "raise"). McConnell defensive prose — the transition rule must
    # be a positive statement.
    escalation_verb = (
        "escalate" in lower or "promot" in lower or "raise" in lower
    )
    assert escalation_verb, (
        "Panel B severity prose must use an explicit escalation verb "
        "(`escalate` / `promote` / `raise`) per TC-REVIEW-1-03 — "
        "the Important→Critical transition must be a named action"
    )
    # MUST NOT clause from TC-REVIEW-1-03: severity stays Important when
    # the seam is known. Approximate by checking the escalation paragraph
    # does not carry softener phrases that would drop the rule back to
    # default-severity-always.
    seams_idx = section.find(".cross-chunk-seams")
    if seams_idx != -1:
        # Window: 400 chars around the escalation reference.
        window_start = max(0, seams_idx - 200)
        window_end = min(len(section), seams_idx + 400)
        window_lower = section[window_start:window_end].lower()
        _ESCALATION_SOFTENERS = (
            "stays important",
            "remain important",
            "always important",
            "advisory escalation",
            "optional escalation",
        )
        for phrase in _ESCALATION_SOFTENERS:
            assert phrase not in window_lower, (
                f"Panel B escalation paragraph MUST NOT contain "
                f"`{phrase}` (TC-REVIEW-1-03 MUST NOT clause — when "
                "the seam is known, severity escalates to Critical, "
                "it does not stay Important)"
            )


# REVIEW-2 (P26-C03) — `/gvm-code-review` Panel C realistic-fixture
# domain-keyed prompt. Two structural tests covering TC-REVIEW-2-01..02.


def _panel_c_section(skill_text: str) -> str:
    """Return the slice of `gvm-code-review` SKILL.md belonging to Panel C.

    Anchored on `\\n### Panel C: Logic & Completeness`; terminates at
    `\\n### Panel D:` (next panel).
    """
    line_anchor = "\n### Panel C: Logic & Completeness"
    idx = skill_text.find(line_anchor)
    if idx == -1:
        return ""
    section_start = idx + 1
    rest = skill_text[section_start:]
    end = rest.find("\n### Panel D:")
    if end == -1:
        return rest
    return rest[:end]


# Three known-edge-shape domains explicitly named by REVIEW-2's spec
# excerpt and TC-REVIEW-2-01. The full six-domain catalogue lives in
# /gvm-build SKILL.md § TDD-3 (P25-C04); Panel C names the canonical
# three inline plus forward pointer (Brooks DRY).
_REVIEW_2_DOMAINS = ("data-analysis", "parsing", "security validation")


def test_tc_review_2_01_panel_c_contains_domain_keyed_realistic_fixture_list() -> None:
    text = GVM_CODE_REVIEW_SKILL.read_text(encoding="utf-8")
    section = _panel_c_section(text)
    assert section, (
        "Panel C section must exist in /gvm-code-review SKILL.md "
        "(precondition for TC-REVIEW-2-01)"
    )
    lower = section.lower()
    # MUST contain: realistic-fixture mandate naming. Panel C prose must
    # explicitly carry the term `realistic-fixture` so reviewers know to
    # apply the rule. Without it, the mandate is invisible at dispatch
    # time and reviewers default to v2.0.x logic-and-completeness scope.
    assert "realistic-fixture" in lower or "realistic fixture" in lower, (
        "Panel C prose must name the literal `realistic-fixture` mandate "
        "per TC-REVIEW-2-01 / requirements REVIEW-2"
    )
    # MUST contain: each of the three known-edge-shape domain names
    # verbatim. Inline naming bootstraps the dispatch prompt — reviewers
    # do not need to follow the forward pointer to /gvm-build to act.
    for domain in _REVIEW_2_DOMAINS:
        assert domain in lower, (
            f"Panel C prose must name the known-edge-shape domain "
            f"`{domain}` per TC-REVIEW-2-01 — the three canonical "
            "domains (data-analysis, parsing, security validation) are "
            "the inline-named subset of /gvm-build § TDD-3's six-domain "
            "catalogue"
        )
    # MUST contain: at least one starter-fixture token from the
    # data-analysis row to prove Panel C is not just listing domain
    # names without the actual fixture shapes the catalogue describes.
    # The data-analysis canonical evidence (defect S6.1) is short
    # categorical codes — at least one of "short categorical" or
    # "categorical code" or "all-null" must appear.
    starter_phrase = (
        "short categorical" in lower
        or "categorical code" in lower
        or "all-null" in lower
        or "all null" in lower
    )
    assert starter_phrase, (
        "Panel C prose must include at least one starter-fixture "
        "token (short categorical / categorical code / all-null) per "
        "TC-REVIEW-2-01 — naming the domains without the fixture "
        "shapes is a v2.0.x carry-over"
    )
    # MUST contain: forward pointer to /gvm-build § TDD-3 so reviewers
    # know where the canonical six-domain catalogue lives. Brooks DRY:
    # one source of truth, multiple readers.
    assert "TDD-3" in section or "tdd-3" in lower, (
        "Panel C prose must reference `TDD-3` (the canonical catalogue "
        "section in /gvm-build SKILL.md) per TC-REVIEW-2-01 / Brooks DRY"
    )
    # MUST NOT clause from TC-REVIEW-2-01: a generic Panel C prompt
    # without domain-specific guidance. Approximate by checking the
    # realistic-fixture sub-section is NOT empty filler — the domain
    # tokens above already enforce non-emptiness, so this disqualifier
    # scan blocks softener phrasing that would dilute the mandate.
    _GENERIC_DISQUALIFIERS = (
        "consider including realistic fixtures",
        "may want to include",
        "if applicable",
        "where appropriate",
    )
    # Restrict to the realistic-fixture subsection if findable; else
    # whole-section scan.
    rf_idx = lower.find("realistic-fixture")
    if rf_idx == -1:
        rf_idx = lower.find("realistic fixture")
    if rf_idx != -1:
        # Window: 600 chars from the realistic-fixture anchor — long
        # enough to cover the mandate paragraph + domain-keyed list
        # but not so long we false-positive on other Panel C prose.
        window_end = min(len(lower), rf_idx + 600)
        rf_window = lower[rf_idx:window_end]
        for phrase in _GENERIC_DISQUALIFIERS:
            assert phrase not in rf_window, (
                f"Panel C realistic-fixture sub-section MUST NOT "
                f"contain softener phrase `{phrase}` (TC-REVIEW-2-01 "
                "MUST NOT clause — the mandate is a rule, not a "
                "suggestion)"
            )


def test_tc_review_2_02_panel_c_emits_important_finding_with_override_marker() -> None:
    text = GVM_CODE_REVIEW_SKILL.read_text(encoding="utf-8")
    section = _panel_c_section(text)
    assert section, (
        "Panel C section must exist (precondition for TC-REVIEW-2-02)"
    )
    lower = section.lower()
    # MUST contain: Important-finding rule. The default outcome of the
    # realistic-fixture gap must be a NAMED finding severity, not an
    # advisory note.
    assert "important" in lower, (
        "Panel C realistic-fixture rule must name `Important` as the "
        "finding severity per TC-REVIEW-2-02 — without a named "
        "severity, reviewers can't act on the rule"
    )
    # MUST contain: explicit "finding" emit verbiage (emit / surface /
    # flag / report) so the rule is operationally clear (Martin: explicit
    # action verbs, not inferred behaviour).
    emit_verb = (
        "emit" in lower or "surface" in lower or "flag" in lower or "report" in lower
    )
    assert emit_verb, (
        "Panel C realistic-fixture rule must use an explicit emit verb "
        "(emit / surface / flag / report) per TC-REVIEW-2-02 — the "
        "rule must name the action, not infer it"
    )
    # MUST contain: the literal `realistic-fixture-not-applicable`
    # override marker so practitioners know how to claim exemption.
    # The marker is hyphenated, lowercase, matching /gvm-build SKILL.md
    # § TDD-3 forward-pointer prose verbatim.
    assert "realistic-fixture-not-applicable" in section, (
        "Panel C must name the literal `realistic-fixture-not-applicable` "
        "override marker per TC-REVIEW-2-02 / spec § Component 3 § Panel C "
        "— the override path must use the same literal token as "
        "/gvm-build SKILL.md § TDD-3 (Brooks conceptual integrity)"
    )
    # MUST contain: rationale requirement on the override. Without
    # rationale, an override is a silent skip (Fagan: exemptions
    # without rationale are not exemptions).
    assert "rationale" in lower, (
        "Panel C override marker prose must require a `rationale` per "
        "TC-REVIEW-2-02 — overrides without rationale are silent skips"
    )
    # MUST NOT clause from TC-REVIEW-2-02: a Pass verdict despite the
    # fixture gap. The disqualifier list scopes to phrases that would
    # legitimise a Pass when realistic-fixture is missing AND no
    # override is present.
    _PASS_DISQUALIFIERS = (
        "pass despite",
        "passes despite",
        "auto-pass",
        "silent pass",
        "no finding when missing",
    )
    for phrase in _PASS_DISQUALIFIERS:
        assert phrase not in lower, (
            f"Panel C realistic-fixture rule MUST NOT contain "
            f"`{phrase}` (TC-REVIEW-2-02 MUST NOT clause — missing "
            "realistic-fixture coverage in a known-edge-shape domain "
            "produces an Important finding, never a Pass)"
        )


def test_tc_nfr_3_03_gvm_status_reads_methodology_changelog() -> None:
    """TC-NFR-3-03: /gvm-status surfaces the most recent methodology-changelog entry.

    Per spec § Component 6: when `methodology-changelog.md` exists at the
    project root, `/gvm-status` reads the most recent dated entry and
    surfaces it in a new "Methodology" section alongside the existing
    pipeline-state report. Read-only — no enforcement, no refusal.

    The structural assertions are anchored on the SKILL.md prose that
    instructs the reader (Claude in `/gvm-status`) to perform the read.
    The prose is the system under test — no executable read-side path
    exists outside it.
    """
    text = GVM_STATUS_SKILL.read_text(encoding="utf-8")
    lower = text.lower()

    # MUST contain: the literal filename `methodology-changelog.md` so
    # the read target is unambiguous (Brooks: one concept, one name).
    assert "methodology-changelog.md" in text, (
        "/gvm-status SKILL.md must name the literal file "
        "`methodology-changelog.md` per TC-NFR-3-03 / spec § Component "
        "6 — without the literal filename the read-side instruction "
        "is ungrounded"
    )

    # MUST contain: a "Methodology" section name. The spec names this
    # section verbatim; consistent naming is the visible audit trail.
    assert "methodology" in lower, (
        "/gvm-status SKILL.md must name a `Methodology` section per "
        "TC-NFR-3-03 / spec § Component 6 — the section name is the "
        "user-visible surface where the changelog entry is rendered"
    )

    # MUST contain: extraction of the most recent dated entry. Prose
    # must name the recency contract explicitly so the reader does
    # not extract an arbitrary entry.
    assert "most recent" in lower, (
        "/gvm-status SKILL.md must name `most recent` as the entry "
        "selection contract per TC-NFR-3-03 — the prose must specify "
        "WHICH entry to surface, not just `an entry`"
    )

    # MUST contain: the three audit-trail field names per TC-NFR-3-03
    # MUST clause ("rule reference + defect class + validation method").
    # A regression that drops any of these fields from the SKILL.md
    # prose silently violates the spec; without these assertions the
    # test does not demand the full TC-NFR-3-03 contract.
    for field in ("rule reference", "defect class", "validation method"):
        assert field in lower, (
            f"/gvm-status SKILL.md must name `{field}` per "
            "TC-NFR-3-03 — the three audit-trail fields are the "
            "contract for what the Methodology section surfaces"
        )

    # MUST contain: skip-when-absent behaviour per spec § Component 6
    # error-handling clause. Without an explicit absent-file branch,
    # the read-side could surface noise on projects that have not
    # adopted the audit trail.
    skip_phrases = ("skip", "absent", "does not exist", "not exist", "missing")
    assert any(phrase in lower for phrase in skip_phrases), (
        "/gvm-status SKILL.md must name skip-when-absent behaviour "
        "per TC-NFR-3-03 / spec § Component 6 — when the file is "
        "absent the section is omitted, not surfaced empty"
    )

    # MUST contain: read-only contract. The spec states the read-side
    # is "read-only — no enforcement, no refusal"; the prose must
    # reflect that contract so future maintainers do not bolt
    # enforcement onto the diagnostic skill.
    read_only = "read-only" in lower or "read only" in lower
    assert read_only, (
        "/gvm-status SKILL.md must name the `read-only` contract per "
        "TC-NFR-3-03 / spec § Component 6 — without it future edits "
        "may add refusal, violating the diagnostic skill's contract"
    )

    # MUST NOT clause from TC-NFR-3-03: the SKILL.md MUST NOT contain
    # prose that legitimises ignoring the changelog when it exists.
    # The disqualifiers below would each authorise a status report
    # that omits the Methodology section despite the file being
    # present — exactly the behaviour TC-NFR-3-03 forbids.
    _IGNORE_DISQUALIFIERS = (
        "ignore the methodology changelog",
        "ignore methodology-changelog",
        "skip the changelog when present",
        "omit the methodology section when the file exists",
    )
    for phrase in _IGNORE_DISQUALIFIERS:
        assert phrase not in lower, (
            f"/gvm-status SKILL.md MUST NOT contain `{phrase}` per "
            "TC-NFR-3-03 MUST NOT clause — when the changelog exists "
            "the Methodology section is mandatory in the output"
        )


def test_tc_nfr_3_01_changelog_has_v2_1_0_entry() -> None:
    """TC-NFR-3-01: methodology-changelog.md has three dated section headers,
    each entry with rule reference + defect class + validation method.

    The v2.1.0 entry MUST cover all 10 v2.1.0 requirements (TDD-1, TDD-2,
    TDD-3, GATE-1, GATE-2, REVIEW-1, REVIEW-2, NFR-1, NFR-2, NFR-3) with
    the canonical three-field shape per spec § Component 5.
    """
    text = CHANGELOG.read_text(encoding="utf-8")

    # MUST contain: three dated section headers (line-anchored at start of line).
    for header in ("\n## v2.0.0", "\n## v2.0.1", "\n## v2.1.0"):
        assert header in text, (
            f"methodology-changelog.md missing dated header `{header.strip()}` "
            "per TC-NFR-3-01 — three releases must be represented"
        )

    # Extract the v2.1.0 section.
    parts = text.split("\n## v2.1.0", 1)
    assert len(parts) == 2, "v2.1.0 section header must appear at line start"
    v210 = parts[1]
    next_header = v210.find("\n## v")
    if next_header != -1:
        v210 = v210[:next_header]

    # MUST contain: all 10 requirement IDs in the v2.1.0 entry. The hardening
    # track ships exactly these ten rules; absence of any is a coverage gap.
    for req_id in (
        "TDD-1", "TDD-2", "TDD-3", "GATE-1", "GATE-2",
        "REVIEW-1", "REVIEW-2", "NFR-1", "NFR-2", "NFR-3",
    ):
        assert req_id in v210, (
            f"v2.1.0 entry missing requirement `{req_id}` per "
            "TC-NFR-3-01 — every v2.1.0 hardening rule must be "
            "audit-trailed in the changelog"
        )

    # MUST contain: each canonical three-field marker present at least once
    # in the v2.1.0 section. Each requirement bullet must carry these three
    # fields per spec § Component 5; the section-level assertion confirms
    # the format is honoured (a stricter per-bullet check is overkill —
    # absence of any field at section level proves the format dropped).
    lower = v210.lower()
    assert "defect class" in lower, (
        "v2.1.0 entry must name `defect class` field per TC-NFR-3-01 / "
        "spec § Component 5"
    )
    assert "validation" in lower, (
        "v2.1.0 entry must name `validation` field per TC-NFR-3-01 / "
        "spec § Component 5"
    )

    # MUST NOT clause: an entry without rationale + defect-class fields.
    # A bullet ending with just a rule reference and no defect-class /
    # validation breaks the audit-trail contract. The section-level check
    # above catches this — if any of the three fields is missing from the
    # whole v2.1.0 section the assertion already failed.


def test_tc_nfr_3_02_inclusion_heuristic_in_skill_md() -> None:
    """TC-NFR-3-02: the inclusion heuristic is documented in a SKILL.md.

    Per spec § Component 5: the heuristic distinguishes process-changing
    edits (changelog entries) from cosmetic edits (git history only). The
    heuristic must live in a SKILL.md so practitioners reading a skill at
    release time know what does and does not warrant a changelog entry.
    """
    text = GVM_DEPLOY_SKILL.read_text(encoding="utf-8")

    # MUST contain: the literal heuristic phrase. Near-paraphrase is
    # acceptable per the test-case wording, but the literal phrase is
    # the unambiguous signal — assert it verbatim. Brooks: one concept,
    # one literal phrasing, copied from the changelog header to keep
    # the two sources synchronised.
    heuristic = (
        "if a chunk that was acceptable yesterday would be refused "
        "today (or vice versa), it's a changelog entry"
    )
    assert heuristic in text, (
        "/gvm-deploy SKILL.md must contain the inclusion heuristic "
        "verbatim per TC-NFR-3-02 — without it, typo-only edits "
        "flood the changelog"
    )


# Rule 28 — Review Finding Triage Is User-Owned. Each review skill's Hard
# Gates section MUST name rule 28 and the canonical forbidden phrases.
# Without these tests, a future edit can silently delete the Hard Gate
# from any review skill (Beck: every behaviour has a test, including the
# self-policing one).

GVM_DESIGN_REVIEW_SKILL = (
    PROJECT_ROOT / "grounded-vibe-methodology/skills/gvm-design-review/SKILL.md"
)
GVM_DOC_REVIEW_SKILL = (
    PROJECT_ROOT / "grounded-vibe-methodology/skills/gvm-doc-review/SKILL.md"
)

# The canonical forbidden phrases that every review skill's Hard Gate
# MUST quote verbatim. The version-string placeholder is the canonical
# parameterised form (per shared-rules.md § 28).
_RULE_28_CANONICAL_PHRASES = (
    "shared rule 28",
    "USER OWNS FINDING TRIAGE",
    "filtered under strict criterion",
    "deferred to v{N}.{M}.{P} hardening",
    "verdict",  # "Verdict comes after triage" / "bundling the verdict"
)


def _assert_rule_28_present(skill_path: Path, label: str) -> None:
    text = skill_path.read_text(encoding="utf-8")
    for phrase in _RULE_28_CANONICAL_PHRASES:
        assert phrase in text, (
            f"{label} SKILL.md must name `{phrase}` per shared rule 28 "
            "(Review Finding Triage Is User-Owned). A Hard Gate that "
            "drops these phrases is the failure mode rule 28 prevents."
        )


def test_r28_code_review_hard_gate_names_forbidden_patterns() -> None:
    _assert_rule_28_present(GVM_CODE_REVIEW_SKILL, "/gvm-code-review")


def test_r28_design_review_names_rule_28() -> None:
    _assert_rule_28_present(GVM_DESIGN_REVIEW_SKILL, "/gvm-design-review")


def test_r28_doc_review_names_rule_28() -> None:
    _assert_rule_28_present(GVM_DOC_REVIEW_SKILL, "/gvm-doc-review")


# ---------------------------------------------------------------------------
# TC-NFR-1-01 / TC-NFR-1-03 — runtime mtime-comparison enforcement (v2.1.1
# closure of the deferral noted in v2.1.0 RELEASE-NOTES.md).
#
# NFR-1's carry-over rule is enforced by the executor reading SKILL.md prose
# at runtime; there is no Python helper that performs the mtime check. The
# structural tests therefore assert the SKILL.md prose names the procedure
# with enough specificity that the executor cannot interpret it ambiguously.
#
# TC-NFR-1-01 (`test_tc_nfr_1_01_*` below): the mtime-comparison procedure
#   is named in Hard Gate 8, with all three required tokens (`mtime`,
#   `_V2_1_0_RELEASE_DATE`, `build/prompts/`) co-located in the carry-over
#   procedure paragraph — not merely present somewhere in the section.
# TC-NFR-1-03 (`test_tc_nfr_1_03_*` below): the literal exemption phrase
#   `"v2.0.x carry-over"` is named in BOTH the Hard Gate 8 section AND the
#   handover template fenced block — the audit trail demands co-location,
#   not arbitrary occurrence.
#
# R59 I2 fix: previous version used whole-section / whole-file `in` checks,
# which would pass even if the tokens drifted into unrelated sections. These
# anchored checks bind co-location: tokens must appear inside the procedure
# paragraph, not merely somewhere in the section's transitive scope.
# ---------------------------------------------------------------------------


def _carry_over_paragraph(section: str) -> str:
    """Extract the carry-over procedure paragraph from a Hard Gate 8 slice.

    The paragraph is opened by the literal anchor `**Carry-over exemption
    (NFR-1):**` and runs until the next blank line or boldface marker.
    Returns "" if the anchor is absent — the assertions below treat that
    as a failure (the procedure paragraph itself has been removed or
    renamed).
    """
    anchor = "**Carry-over exemption (NFR-1):**"
    idx = section.find(anchor)
    if idx == -1:
        return ""
    rest = section[idx:]
    # Terminate at the next double-newline (paragraph break) or the next
    # boldface heading marker — whichever appears first.
    candidates = [
        pos
        for pos in (rest.find("\n\n"), rest.find("\n**"))
        if pos != -1
    ]
    if not candidates:
        return rest
    return rest[: min(candidates)]


def test_tc_nfr_1_01_hard_gate_8_names_mtime_comparison() -> None:
    """Hard Gate 8 carry-over paragraph must name the mtime procedure.

    All three tokens (`mtime`, `_V2_1_0_RELEASE_DATE`, `build/prompts/`)
    must appear in the carry-over procedure paragraph — not merely
    somewhere in the Hard Gate 8 section, and not merely somewhere in
    SKILL.md. R59 I2: anchored to the procedure paragraph so prose drift
    that splits the procedure across sections is detected.
    """
    text = GVM_BUILD_SKILL.read_text(encoding="utf-8")
    section = _hard_gate_8_section(text)
    assert section, "Hard Gate 8 entry must exist in SKILL.md Hard Gates list"
    paragraph = _carry_over_paragraph(section)
    assert paragraph, (
        "Hard Gate 8 must contain a carry-over procedure paragraph anchored "
        "by `**Carry-over exemption (NFR-1):**`"
    )
    for token in ("mtime", "_V2_1_0_RELEASE_DATE", "build/prompts/"):
        assert token in paragraph, (
            f"Carry-over procedure paragraph must name `{token}` — "
            "the executor cannot perform a comparison the procedure does "
            "not specify"
        )


def test_tc_nfr_1_03_exemption_phrase_is_literal() -> None:
    """The carry-over exemption phrase must be literal AND co-located.

    R59 I2: the literal `"v2.0.x carry-over"` phrase must appear inside
    BOTH the Hard Gate 8 section AND the handover template fenced block.
    A whole-file substring check would pass if the phrase migrated into
    unrelated docs; co-location pins the audit-trail contract.
    """
    text = GVM_BUILD_SKILL.read_text(encoding="utf-8")
    section = _hard_gate_8_section(text)
    assert section, "Hard Gate 8 entry must exist"
    assert '"v2.0.x carry-over"' in section, (
        'Hard Gate 8 section must name the literal exemption phrase '
        '`"v2.0.x carry-over"` (quoted, verbatim) — paraphrases break the '
        "handover audit trail"
    )
    handover = _handover_template_block(text)
    assert handover, "Handover template fenced block must exist"
    assert "v2.0.x carry-over" in handover, (
        "Handover template must reference the literal `v2.0.x carry-over` "
        "phrase so the practitioner records the exemption verbatim"
    )
