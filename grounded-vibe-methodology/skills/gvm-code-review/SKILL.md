---
name: gvm-code-review
description: Use when reviewing implementation code for quality, security, and spec adherence. Triggered by /gvm-code-review command, requests to review code, or after completing a build phase. Dispatches parallel defect-class panels as subagents, grounded in the project's spec-declared specialists.
---

# Code Review

## Overview

Reviews implementation code by dispatching parallel defect-class subagents. Each subagent scans for a specific *class* of defect, not a broad area of expertise. Panels are partitioned so their scanning mandates are orthogonal — minimal overlap, maximum first-pass coverage.

**Pipeline position:** `/gvm-requirements` → `/gvm-test-cases` → `/gvm-tech-spec` → `/gvm-design-review (optional)` → `/gvm-build` → **`/gvm-code-review`** → `/gvm-test` → `/gvm-doc-write` → `/gvm-doc-review` → `/gvm-deploy`

This skill reviews code, not documents. For document review (requirements, test cases, specs), use `/gvm-doc-review`.

**Shared rules:** At the start of this skill, load `~/.claude/skills/gvm-design-system/references/shared-rules.md` and follow all rules throughout execution. Load `~/.claude/skills/gvm-design-system/references/expert-scoring.md` when scoring experts.

## Methodological Basis

The panel structure is grounded in published inspection research, not convention:

- **Orthogonal defect partitioning** (Laitenberger, Atkinson, Schlich & El Emam, "An experimental comparison of reading techniques for defect detection in UML design documents", *Journal of Systems and Software*, 2000): Perspective-Based Reading (PBR) assigns each reviewer a non-overlapping scanning mandate. PBR teams detected 41% more unique defects than checklist-based teams at 58% lower cost per defect — each reviewer found defects the others structurally could not see because their scanning mandates were non-overlapping.
- **Satisfaction of Search mitigation** (Drew, Võ & Wolfe, "The Invisible Gorilla Strikes Again", 2013): After finding one defect in a region, the probability of detecting a second drops. The fix: scan the entire artefact once per defect class rather than once for all classes. Each panel makes focused passes for its class.
- **Liberal criterion on first pass** (Signal Detection Theory, Green & Swets, 1966): Set the detection threshold low on R1 (flag borderlines), filter false positives in synthesis. This maximises recall at acceptable precision cost. R2+ raises the bar to strict.
- **Capture-recapture estimation** (Wohlin, Petersson & Aurum, adapted for software inspection): After R1, count panel overlaps to estimate the total defect population and calculate whether R2 is needed rather than guessing.

## Hard Gates

These steps are non-negotiable. If you skip any of them, the review output is invalid.

1. **DISPATCH PANELS IN PARALLEL.** YOU MUST dispatch all panels as concurrent subagents via the Agent tool — all in a single message. If you review sequentially instead of in parallel, you are not executing this skill correctly. Parallel dispatch is the core value of this skill.

2. **LOAD EXPERT REFERENCES BEFORE DISPATCH.** Read the relevant expert sections from `architecture-specialists.md`, the relevant `domain/*.md` files, and `stack-specialists.md` BEFORE writing the dispatch prompts. Load domain files selectively from `~/.claude/skills/gvm-design-system/references/domain/` — see `domain-specialists.md` index for activation signals. Each panel prompt MUST include expert excerpts from these loaded files — if the experts in the prompts are generic descriptions rather than content loaded from the reference files, you skipped this step.

3. **WRITE HTML OUTPUT.** The review MUST produce `code-review/code-review-{NNN}.html`. Review reports are HTML-only — no paired MD is produced (shared rule 13 exception for review reports). The user reads the HTML report; findings are carried forward in `reviews/calibration.md`, not in the report MD. The HTML file must exist before presenting findings or offering next steps. DO NOT end the review without the HTML file written.

4. **UPDATE CALIBRATION.** After presenting findings, YOU MUST create or update `reviews/calibration.md`. This is the UPDATE CALIBRATION step in the process flow — DO NOT end the review without it.

5. **VERDICT.** Every review must include a verdict using the code-review language from `review-reference.md` (Merge / Merge with caveats / Do not merge). The verdict appears in the report and in the text presented to the user. DO NOT end a review without a verdict.

6. **USER OWNS FINDING TRIAGE (shared rule 28 — Review Finding Triage Is User-Owned).** Every Critical or Important finding emitted by panels MUST be presented to the user before any disposition is recorded. This skill MAY recommend "fix / defer / dismiss" per finding but MUST NOT decide. The Finding Quality Gate is the panels' emit threshold under R2+ strict — it is NOT a post-synthesis filter for Claude to invoke after panels return. A finding that survives the panel's gate has earned the user's attention; suppressing it under "R2+ strict means I should re-apply the gate to filter" is a triage breach. Forbidden patterns:

   - Recording emitted findings as "filtered under strict criterion" without user input.
   - Recording emitted findings as "deferred to v{N}.{M}.{P} hardening" without user input.
   - Bundling "Verdict: Merge with caveats" with the user's first sight of the finding list. Verdict comes after triage, not before.
   - Presenting a summary count that hides which findings were deferred. A summary count IS permitted when zero findings are deferred — "N findings, all fixed" hides nothing.

   Permitted: per-finding disposition recommendations alongside the surfaced list ("recommend defer — pre-existing scope; recommend fix — 1-line edit"); pre-fixing trivial findings during a single user-authorised "fix all" turn (if a NEW Critical/Important finding arises during the fix pass, pause and surface it — the original authorisation does not extend to new findings); filtering [BORDERLINE]-tagged findings during R1 synthesis (panel-side label).

## Prerequisites

Before dispatching panels, verify:

1. **`specs/` directory exists and contains at least one spec file.** If not, tell the user to run `/gvm-tech-spec` first.
2. **Git repository is initialized with history.** Run `git log -1` to verify. If git is not initialized or has no commits, tell the user to initialize a git repository and make at least one commit before running code review.
3. **If auto-detecting from `build/handovers/`**, verify the handover directory exists and contains files. If not, ask the user for explicit input (git range or directory).
4. **First-run migration hook (calibration schema migration).** Inspect `reviews/calibration.md`. If the file exists AND the file has no frontmatter, OR the frontmatter is present but declares no `schema_version` field, the calibration is on the legacy schema (pre-`schema_version: 0`). Emit `AskUserQuestion`:

   *"`reviews/calibration.md` has no schema version — run migration?"*

   Options (verbatim):
   - **"Yes, run gvm-migrate-calibration now"** — execute `python -m gvm_migrate_calibration reviews/calibration.md` (the script is at `~/.claude/skills/gvm-code-review/scripts/gvm_migrate_calibration.py`; the module name `gvm_migrate_calibration` uses underscores). Handle the exit code:
     - **Exit 0** — success or already-migrated. Re-load `reviews/calibration.md` (now carries `schema_version: 0` frontmatter) and continue with the review.
     - **Exit 1** — file not found despite the existence check above. Indicates a race or permission issue. Surface the stderr message to the user and stop; do not proceed with the review.
     - **Exit 2** — refused. Either the allowlist/marker check failed, or `_calibration_parser` could not be imported (broken plugin installation). Surface the stderr message and treat the result as if the user had picked "Skip" (see below); the migration cannot be auto-resolved.
   - **"Skip (legacy calibration retained)"** — proceed with the review on the legacy calibration. Do NOT write a new "migration_deferred" field — the absence of `schema_version` in the frontmatter IS the deferred state. Downstream `/gvm-test` reads the schema version via `_calibration_parser.load_calibration`; on `schema_version == 0` the VV-6 retrofit (`_vv6_retrofit.plan_retrofit` / `apply_retrofit`, gvm-test SKILL.md step 8) prompts the practitioner to reclassify any rows that carry the retired pre-v2.0 verdict vocabulary. There is no automatic verdict cap in `gvm_verdict.evaluate` — the evaluator is stateless over calibration schema. The retrofit is the enforcement.

   The hook fires once per project lifetime — once `schema_version` is present in frontmatter the prompt does not appear again. If `reviews/calibration.md` does not exist at all, skip this hook (no prior calibration to migrate).

## Input

One of:
- **Git range:** `BASE_SHA..HEAD_SHA` — reviews all changes in that range
- **Phase/chunk:** `P5` or `P5-C03` — resolves to git commits from `build/handovers/`
- **Current diff:** reviews uncommitted changes
- **Directory:** reviews all code in a directory

If invoked without arguments after a `/gvm-build` phase completes, auto-detect the phase from `build/handovers/` and review it.

## Expert Sources

All expert definitions live in `~/.claude/skills/gvm-design-system/references/`:

| File | Tier | When Active |
|---|---|---|
| `architecture-specialists.md` | 1 | Always |
| `domain/*.md` files | 2a | Load selectively — see `domain-specialists.md` index for activation signals |
| `stack-specialists.md` (index) → `stack/*.md` | 3 | Based on the language/framework of changed files — load index for constraints, then matching per-stack files |

The project's own `specs/` (e.g., `specs/cross-cutting.md`) declare which experts were activated for that specific project and contain project-specific design principles to review against.

## Defect-Class Panels

Panels are partitioned by defect class, not by expert domain (Basili: orthogonal scanning mandates maximise first-pass detection). Each panel receives the named experts whose principles are relevant to its defect class — the experts are still grounded, but the scanning mandate is orthogonal.

### Panel A: References & Dependencies

**What to scan:** Every file path, import, require, load instruction, cross-reference, dependency declaration, and URL. Does the target exist? Is the path correct? Is the version compatible?

**Experts assigned:** Hunt & Thomas (DRY — single source of truth for references), McConnell (defensive programming — fail on missing configuration), stack specialists (dependency verification commands).

**Scanning method:** Enumerate every reference in every file. For each: verify the target exists, check the path is absolute where required, confirm version constraints. This is exhaustive enumeration, not sampling.

### Panel B: Contracts & Interfaces

**What to scan:** Every function signature, API endpoint, data structure, producer/consumer pair, and verdict string. Does the output match what the consumer expects? Do types align? Are error contracts honoured?

**Experts assigned:** Keeling (decision capture — interface contracts), Clements (architectural views — producer/consumer alignment), Beck (test interface — mock at boundaries only), domain specialists relevant to the API.

**Scanning method:** For each public interface, trace both the producer and consumer. Verify structural agreement: field names, types, required vs optional, error shapes. Flag any interface where producer and consumer specifications diverge.

**EBT contract / collaboration lint (testing-mandates ADR-503, ADR-504, ADR-508).** When the changed file set includes test files, Panel B MUST also run the shared contract/collaboration linter:

1. Detect the project's primary test stack (Python / TypeScript / Go) from `specs/cross-cutting.md` or by extension.
2. Resolve `ebt_boundaries_path` as `<project_root>/.ebt-boundaries`. Pass `None` if the file does not exist (the linter falls back to stack defaults from `~/.claude/skills/gvm-design-system/references/ebt-boundaries-defaults.md`).
3. For each changed test file, compute its source root via `_ebt_contract_lint.detect_source_root(test_file_path, stack)` from `~/.claude/skills/gvm-design-system/scripts/_ebt_contract_lint.py`. If detection returns `None`, pass `None` forward (fail-closed: any non-allowlisted import is treated as internal).
4. Call `_ebt_contract_lint.lint(test_file_path, ebt_boundaries_path, source_root, stack=<detected stack>)`. The same shared helper `/gvm-test-cases` Phase 4 calls — DRY, one heuristic, two callers (Brooks: conceptual integrity).
5. Each returned `LintViolation` has `kind` ∈ {`rainsberger`, `metz`, `mock-budget`} and a `file_line` pointer. Emit each as a Panel B finding using the canonical six-field shape (Expert, Severity, File:Line, Issue, Spec Reference, Fix). Expert is `Rainsberger` for `kind="rainsberger"`, `Metz` for `kind="metz"`, and `Metz` (mock-budget grounding — *POODR* Ch. 9: mocks belong at object boundaries) for `kind="mock-budget"`. Severity: Important by default — these are test-design defects that mask product behaviour, not cosmetic issues.

   - **`rainsberger`** — HTTP transport patched in the consumer (e.g., `patch("requests.get")`, `vi.mock("axios")`, raw URL outside `httptest.New`). Recommended fix: replace with a contract test against a real fake server, or retag as `[COLLABORATION]` if the boundary is genuinely internal.
   - **`metz`** — internal-class mock inside a `[CONTRACT]`-tagged test. Recommended fix: instantiate the real production class from the DI root downward, or extend the project's `.ebt-boundaries` allowlist if the dependency is legitimately external from this project's perspective (per ADR-504).
   - **`mock-budget`** — TDD-2 violation: more than one mock in a test, or a mock target that is an internal Python class rather than an external boundary (per the canonical allowlist in `/gvm-build` SKILL.md § TDD-2). Internal mocks hide protocol drift (Freeman & Pryce, *GOOS*) — the seam the mock pretends to verify is the seam the test silently bypasses. Recommended fix: collapse to one external-boundary mock, or instantiate the real internal class. Wrapper-as-SUT exemption (ADR-MH-02) applies when the test's class under test IS the wrapper around the external module.

   **Lint scope (REVIEW-1 explicit).** The lint runs against **every test file** in the chunk diff, regardless of tag — `[CONTRACT]`-tagged, `[COLLABORATION]`-tagged, AND untagged tests are all in scope. Panel B does not narrow the scope to `[CONTRACT]` only; the v2.0.x prose's `[CONTRACT]`-only scope was a coverage gap that this rule closes. The `mock-budget` kind in particular surfaces violations regardless of tag, because TDD-2 applies to all test files (per /gvm-build SKILL.md § TDD-2).

   **Severity escalation (ADR-MH-03).** Default severity for `mock-budget` is **Important** — the practitioner judges. If the mock target appears in the project's `.cross-chunk-seams` allowlist file at the project root, severity escalates to **Critical** — these are the cross-chunk protocols whose drift would break production wiring (Freeman & Pryce protocol-drift defect class). The `.cross-chunk-seams` file is opt-in: when it is absent, escalation does not fire and severity is the default value. When present, Panel B promotes the matching findings to Critical before emitting.

6. Panel B is an independent post-implementation backstop. `/gvm-test-cases` Phase 4 may have surfaced the same violation pre-build, but its findings are not persisted to a machine-readable store, so Panel B does not attempt cross-skill deduplication. After emitting EBT violations in the report, surface a note to the user at synthesis time (step 5 of the Process flow): "If any of the above EBT violations were already addressed during `/gvm-test-cases` Phase 4, annotate the relevant finding's `Fix` column with `[acknowledged via /gvm-test-cases Phase 4]` before closing the review." Detection is the user's responsibility — they have the session context Panel B does not.

### Panel C: Logic & Completeness

**What to scan:** Every conditional branch, loop, error handler, and process flow. Is every if matched with an else? Do loops terminate? Are error paths explicit? Are gate re-statements present on branch paths?

**Experts assigned:** Fagan (entry/exit criteria — every path must be defined), Beck (TDD — every behaviour has a test), McConnell (code construction — defensive programming, single responsibility), Martin (clean code — structured error handling).

**Scanning method:** For each function/process, trace every execution path. Identify: unhandled branches, missing error returns, unbounded loops, implicit fallthrough. This is path coverage analysis, not line coverage.

**Realistic-fixture mandate (TDD-3, REVIEW-2).** Panel C also assesses realistic-fixture coverage on chunks whose diff touches a known-edge-shape domain. The canonical inline list of known-edge-shape domains is **data-analysis**, **parsing**, and **security validation** (the three highest-ROI domains from the six-domain catalogue in `/gvm-build` SKILL.md § TDD-3 — Bach & Bolton, *Rapid Software Testing*: synthetic fixtures encode the engineer's mental model). Starter fixture shapes per domain (full catalogue lives in `/gvm-build` SKILL.md § TDD-3):

- **data-analysis** — short categorical codes (sex M/F, blood type A/B/O), all-null columns, single-row datasets, identical baseline-vs-actual.
- **parsing** — malformed inputs, mixed encodings (UTF-8 BOM, Latin-1), trailing whitespace, very long fields.
- **security validation** — escape characters, length-edges (0-byte, just-under-max), Unicode normalization attacks, percent-encoding edges.

**Rule:** when a chunk's diff touches one of these domains AND the chunk's tests cover only synthetic happy-path fixtures (no realistic-fixture variant alongside), Panel C MUST emit an Important finding naming the missing variant. The default outcome is the Important finding — there is no implicit pass when a fixture gap is observed in a known-edge-shape domain.

**Out-of-catalogue domains.** When a chunk's domain is NOT one of the three canonical known-edge-shape domains (data-analysis, parsing, security validation), Panel C does not apply the realistic-fixture mandate at review time — no fixture-gap finding is emitted. The TDD-3 mandate to ship a realistic-fixture variant still applies at build time per `/gvm-build` SKILL.md § TDD-3 practitioner-extension clause, but Panel C's automated check is scoped to the three named domains where the defect-class evidence is concrete (defect S6.1, defect 3a). Reviewers may still emit a finding by judgement when an out-of-catalogue chunk visibly relies on a synthetic-fixture-only test against an obvious edge-shape domain.

**Practitioner override (ADR-MH-04 forward pointer).** A chunk can claim exemption from the Important finding by tagging its handover with the literal line `realistic-fixture-not-applicable: <rationale>` (e.g. `pure config refactor` / `internal data structure with no input boundary`). Override without rationale is treated as no override (Fagan: exemptions without rationale are silent skips). Reviewers can challenge the rationale during synthesis — the rationale is the audit trail.

### Panel D: Naming & Specification Compliance

**What to scan:** Every named concept, term, variable, and convention. Is it called the same thing everywhere? Does it match the spec? Are patterns consistent?

**Experts assigned:** Brooks (conceptual integrity — one concept, one name), Fowler (refactoring — intention-revealing names), project-specific experts from `specs/cross-cutting.md` conventions.

**Scanning method:** Build a glossary of every named concept from the spec. For each concept, verify it appears with the same name in every file that references it. Flag divergences.

### Panel E: Stub Detection (honesty-triad)

**What to scan:** Every function, method, or constant whose body is suggestive of a placeholder but whose name implies production behaviour. Three `violation_type` categories:

- `unregistered` — heuristic match present, no entry in `STUBS.md`
- `expired` — `STUBS.md` entry exists but `today > expiry`
- `namespace_violation` — stub body present in a file whose path does not lie under a `stubs/` directory (HS-5)

**Experts assigned:** project-specific stub-detection rules from `gvm-code-review/references/stub-detection.md` (the heuristic file is loaded verbatim into the panel prompt, per honesty-triad ADR-107).

**Scanning method:** Panel E receives a mechanically-assembled prompt from `_panel_e_prompt.assemble_panel_e_prompt(...)` containing `STUBS.md` (verbatim), the `.stub-allowlist` (verbatim), and the `stub-detection.md` section for the project's primary language. Findings are reconciled in synthesis: allowlist suppression via `_allowlist.load_allowlist(...)`, severity promotion via `_sd5_promotion.apply_sd5(...)`.

Panel E is dispatched in parallel with A, B, C, D every round when `gvm-code-review/scripts/_panel_e_prompt.py` exists in the plugin tree (i.e., honesty-triad is active for this project) — this is rule **SD-1** (honesty-triad ADR-107). On projects without honesty-triad, Panel E is omitted.

**Out of scope for Panel E:** surfaced requirements. A code-level stub is *not* a record of a requirement gap; the two artefacts are distinct (shared rule 27). Panel E never emits a `surfaced_requirement` violation type and never proposes parking a finding in `STUBS.md` under a `## Surfaced Requirements` heading or a `STUB-SR-NN` ID. If Panel C (Logic & Completeness) or Panel D (Naming & Spec Compliance) surfaces a requirement gap, that finding is triaged separately during synthesis (step 5) and promoted to `requirements.md` via the three-option flow described there.

### Expert Assignment Rules

1. Each expert is assigned to exactly one panel based on the primary defect class their framework addresses.
2. The panel assignment determines what the expert scans for — an expert assigned to Panel B (Contracts) applies their framework to interface contract verification, not to general quality.
3. If the project declares domain or stack specialists not covered by panels A-D, create a supplementary Panel E with a clear defect-class mandate (not "review for [domain] quality" — specify what class of defect to scan for).

## Criteria by Round

Detection threshold varies by round (Green & Swets, Signal Detection Theory: liberal criterion maximises recall on early passes):

**Round 1 (no calibration):** Liberal threshold. Flag anything that *might* be an issue, including borderline cases. Tag borderline findings as `[BORDERLINE]`. False positives are filtered during synthesis — the cost of a false positive is low (one extra finding to review), the cost of a false negative is high (missed defect propagates downstream). The goal is maximum recall.

**Round 2+ (calibration exists):** Strict threshold. Only findings where a consumer would FAIL or an executor would take WRONG ACTION. Apply the Finding Quality Gate from `review-reference.md`. The first pass caught the bulk; now the signal-to-noise ratio matters more than coverage.

## Process

```
1. RESOLVE SCOPE
   ├── Determine git range (BASE_SHA..HEAD_SHA)
   ├── List changed files: git diff --name-only BASE..HEAD
   ├── Categorise by file type and domain
   └── Count: files changed, lines added/removed

2. ASSIGN EXPERTS TO PANELS
   ├── Read the project's specs/cross-cutting.md to see which experts are declared
   ├── Read relevant domain specs for their declared specialists
   ├── Load expert reference files (architecture-specialists, relevant domain/, relevant stack/)
   ├── Assign each loaded expert to exactly one panel (A/B/C/D) based on their primary defect class
   ├── If any domain has no expert coverage → expert discovery per shared rule 2
   ├── If changed code covers a domain not in A-D → create Panel E with specific defect-class mandate
   └── Present panel assignments to user for confirmation

3. LOAD CONTEXT
   ├── Bootstrap GVM home directory per shared rule 14
   ├── Read ~/.claude/skills/gvm-design-system/references/review-reference.md (assessment methodology)
   ├── Read ~/.claude/skills/gvm-design-system/references/writing-reference.md (per shared rule 5)
   ├── Read reviews/calibration.md if it exists (project-level calibration)
   ├── Read reviews/build-checks.md if it exists
   │   ├── Determine round number from COMPLETED score history rows (rows with a non-empty verdict field). Rows missing a verdict are partial (session crashed before UPDATE CALIBRATION) — do not count.
   │   ├── Set criteria: R1 = liberal, R2+ = strict (see Criteria by Round)
   │   └── If 2+ completed prior rows → dual review applies (shared rule 16). A partial row does not satisfy the trigger — to be safe, if any partial row is detected, alert the user and ask whether to treat the prior round as complete for dual-review purposes.
   ├── Read relevant project spec sections (design principles, ADRs, conventions)
   ├── If reviewing a build phase: read the build prompt and handover
   └── Log all loaded experts to activation CSV (per shared rule 1)

4. DISPATCH PARALLEL AGENTS
   ├── Use the Agent tool to dispatch panels A, B, C, D — ALL IN PARALLEL
   ├── Add Panel E (Stub Detection) to the parallel dispatch when honesty-triad
   │   is active for this project (i.e., `gvm-code-review/scripts/_panel_e_prompt.py`
   │   exists). Panel E's prompt is assembled mechanically by
   │   `_panel_e_prompt.assemble_panel_e_prompt(...)` — STUBS.md and the
   │   `.stub-allowlist` are embedded verbatim, plus the language section from
   │   `references/stub-detection.md`. Panel E findings are reconciled in
   │   step 5 via `_allowlist.load_allowlist(...)` (suppression) and
   │   `_sd5_promotion.apply_sd5(...)` (severity promotion).
   ├── Each agent prompt includes:
   │   ├── Defect class mandate: "You scan for [class]. Do NOT scan for [other classes]."
   │   ├── Expert identities assigned to this panel (names + works — excerpted from canonical reference)
   │   ├── ALL files to review (every panel sees every file — partitioning is by defect class, not by file)
   │   ├── Relevant spec excerpts (design principles, ADRs, conventions)
   │   ├── Criteria: "Liberal — flag borderlines as [BORDERLINE]" (R1) or "Strict — consumer FAIL only" (R2+)
   │   ├── Scanning instruction: "Make two passes through every file:
   │   │     Pass 1: Systematic scan — read each file line by line for your defect class
   │   │     Pass 2: Cross-reference scan — check relationships between files for your defect class"
   │   └── Output format: Expert, Severity, File:Line, Issue, Spec Reference, Fix
   ├── Use model: sonnet for panel agents (breadth over depth)
   └── DUAL REVIEW (round 3+ per shared rule 16):
       ├── Dispatch a second set of panels IN PARALLEL with the calibrated panels
       ├── Blind panels receive the same files, experts, and defect-class mandates
       ├── Blind panels do NOT receive calibration data, anchors, or resolved findings
       └── Both sets complete before synthesis

5. SYNTHESISE RESULTS
   ├── Collect findings from all panels
   ├── Deduplicate (same issue found by multiple panels — keep most specific fix)
   ├── Filter [BORDERLINE] findings (R1 only):
   │   ├── Apply the consumer impact test to each borderline finding
   │   ├── Keep findings that pass; discard findings that fail
   │   ├── Record the filter ratio (borderlines kept / borderlines total) for calibration
   │   └── A borderline that multiple panels independently flagged is promoted to confirmed
   ├── Cross-reference themes (issues that span multiple panels)
   ├── Elevate severity if 2+ panels independently flagged the same issue
   ├── CAPTURE-RECAPTURE ESTIMATION (R1 only):
   │   ├── Count overlapping findings between panel pairs
   │   ├── For panels i and j with n_i and n_j findings and m_ij shared:
   │   │   estimated total = (n_i × n_j) / m_ij (Lincoln-Petersen)
   │   ├── Average across panel pairs for robustness
   │   ├── Compare: unique findings found vs estimated total
   │   ├── Report: "Estimated N total defects; found M unique (coverage: M/N)"
   │   ├── If coverage < 80%: recommend R2
   │   └── If coverage ≥ 80%: R2 is optional (note in report)
   │   (Wohlin, Petersson & Aurum: capture-recapture adapted for software inspection)
   ├── DUAL REVIEW RECONCILIATION (round 3+ per shared rule 16):
   │   ├── Classify each blind panel finding as: new, confirmed, regression, rediscovered, or noise
   │   ├── Merge new findings and regressions into the consolidated report
   │   └── Tag merged findings with their blind-review origin
   ├── Prioritise: Critical > Important > Minor > Suggestion
   ├── EBT PHASE-4 ACKNOWLEDGEMENT (testing-mandates ADR-508):
   │   ├── If Panel B emitted any EBT contract/collaboration violations
   │   │   (`kind="rainsberger"`, `kind="metz"`, or `kind="mock-budget"`), surface a note to the
   │   │   user: "If any of the above EBT violations were already
   │   │   addressed during `/gvm-test-cases` Phase 4, annotate the
   │   │   relevant finding's `Fix` column with `[acknowledged via
   │   │   /gvm-test-cases Phase 4]` before closing the review."
   │   └── Detection is the user's responsibility — they have the
   │       session context Panel B does not. Panel B does not attempt
   │       cross-skill deduplication (no persisted store).
   └── SURFACED REQUIREMENT TRIAGE (per shared rule 27):
       ├── Identify any Panel C (Logic & Completeness) or Panel D (Naming & Spec
       │   Compliance) finding whose root cause is a missing or incomplete entry in
       │   `requirements/requirements.md` — i.e. the code is correct against current
       │   requirements but the requirements themselves are silent on the case.
       ├── If no findings qualify: this subflow is a no-op — proceed to step 6.
       ├── PRECONDITION: verify `requirements/requirements.md` exists. If it does not,
       │   present only the third option ("Create a new requirements document") and
       │   note the missing source-of-truth file in the review report.
       ├── For each qualifying finding, present via AskUserQuestion with three options
       │   (label each option with the finding's severity so the user triages with
       │   prioritised information):
       │   ├── "Append as acceptance criterion to an existing requirement" (with changelog entry per rule 11)
       │   ├── "Add a new requirement entry" (with changelog entry per rule 11)
       │   └── "Create a new requirements document (next round)" — run `/gvm-requirements` in "New round" mode
       ├── If the user dismisses the question or selects no option: record the finding
       │   as `deferred — awaiting triage` in the review report's Surfaced Requirements
       │   section and re-prompt at the next natural checkpoint (next `/gvm-code-review`
       │   or `/gvm-status`). Do NOT silently park it.
       ├── DO NOT park the surfaced requirement in `STUBS.md` under any heading or column.
       │   `STUBS.md` is for code-level placeholders only. There is no `STUB-SR-NN` ID
       │   and no `## Surfaced Requirements` section in `STUBS.md`.
       └── Record the chosen option in the review report's Surfaced Requirements section
           and follow through — promote the requirement before closing the review.

6. WRITE REPORT
   ├── **Compute NNN ONCE here, before any file is written.** Call
   │   `_findings_serialiser.find_next_review_number(code_review_dir)` and bind the
   │   result as the review's NNN. Use the same NNN for the HTML in this step AND
   │   the JSON sidecar in step 7. Do NOT call `find_next_review_number` again —
   │   by then the HTML at NNN exists and the function would return NNN+1.
   ├── Load design references before first HTML write: `~/.claude/skills/gvm-design-system/references/tufte-html-reference.md` (core) AND `~/.claude/skills/gvm-design-system/references/tufte-review-components.md` (verdict box, score card, issue blocks, criterion rows). Append the review-component CSS to the core CSS block in the output HTML.
   ├── **HTML generation:** Dispatch the HTML report generation as a Haiku subagent (`model: haiku`). Per shared rule 22. Write the HTML at `code-review/code-review-NNN.html` using the NNN bound above.

   PRESENT CONSOLIDATED REVIEW
   ├── Summary table: panels run, findings per severity, capture-recapture estimate (R1)
   ├── Cross-cutting themes
   ├── Critical findings (must fix) with file:line and fix
   ├── Important findings (should fix)
   ├── Minor + suggestions (grouped)
   ├── Borderline filter results (R1): how many kept, how many discarded, filter ratio
   ├── Per-panel detail
   └── Log cited experts to activation CSV (per shared rule 1)

7. SERIALISE FINDINGS — write the JSON sidecar (only when Panel E ran)
   ├── If Panel E was NOT in this dispatch, skip — no sidecar is written
   ├── Else, for each Panel E finding produced in step 5:
   │   ├── Compute the stable signature via `_sd5_promotion.compute_signature(file_path, symbol, heuristic_class, violation_type)`
   │   ├── Construct a `PanelEFinding` (9 fields per honesty-triad ADR-104):
   │   │   `expert, severity, file_line, issue, spec_reference, fix, violation_type, symbol, signature`
   │   └── `violation_type` is one of `unregistered`, `expired`, `namespace_violation`
   ├── Use the NNN already bound in step 6 — do NOT call `find_next_review_number`
   │   again. By this point `code-review-NNN.html` exists and a fresh call would
   │   return NNN+1, mispairing the sidecar with the HTML.
   ├── Call `_findings_serialiser.serialise_findings(findings, path)` to write
   │   `code-review/code-review-NNN.findings.json` (NDJSON — one JSON object per line)
   ├── If no Panel E findings: write a zero-byte sidecar so the consumer's
   │   "missing report" branch is preserved (an empty file still PASSes VV-4(a))
   └── The sidecar is consumed by `/gvm-test`'s `_review_parser.load(...)` for VV-4(a)

8. OFFER NEXT STEPS (via AskUserQuestion)
   ├── "Fix critical issues now"
   ├── "Fix all issues"
   ├── "Create fix plan"
   └── "Continue to next build phase"

   If the user selects 'Fix critical issues now' or 'Fix all issues': after fixing,
   re-run the affected panels on changed files only (not a full re-review). If the
   re-review finds new Critical findings, offer another fix cycle. After 3 fix cycles —
   regardless of whether the count is decreasing — stop and present the situation to
   the user via AskUserQuestion. Do not loop indefinitely; convergence within 3 cycles
   or escalate.

   Regardless of which option the user selects, run step 9 (UPDATE CALIBRATION)
   before executing their choice. Calibration update is mandatory after every review.

9. UPDATE CALIBRATION (per ~/.claude/skills/gvm-design-system/references/review-reference.md)
   ├── Create reviews/calibration.md if it does not exist
   ├── Append a score history row (round, date, type=code, per-dimension scores)
   ├── Record capture-recapture data (R1): estimated total, unique found, coverage %
   ├── Record borderline filter ratio (R1): kept/total
   ├── Update dimension benchmarks (baseline, current, trend)
   ├── Curate anchor examples — for each dimension, keep the 2 best and 2 worst
   │   concrete findings from this project
   ├── Update recurring findings — issues flagged in 2+ consecutive rounds
   ├── Move resolved findings — issues from prior rounds confirmed fixed
   ├── Promote eligible findings to build checks (per shared rule 21)
```

## Panel Dispatch Template

Each subagent receives a prompt structured as:

```
You are scanning [Project] code for **[defect class]** defects.

Your defect class: [class description — what you scan for]
Do NOT scan for: [other classes — those are handled by other panels]

## Experts Guiding This Scan
- **[Expert Name]** (*[Work]*) — [how their framework applies to this defect class]
  [Excerpt from canonical reference — read at dispatch time, not hardcoded]

## Scanning Method (two passes)

**Pass 1 — Systematic scan:** Read each file line by line. For every [defect class target]
(e.g., every file path, every function signature, every conditional branch), verify it
against the criteria below. Do not skip any instance — this is exhaustive enumeration.

**Pass 2 — Cross-reference scan:** For each [defect class target] found in Pass 1, trace
its relationships to other files. Does the reference resolve? Does the interface match
its consumer? Does the branch path re-state its gates?

## Context
[Relevant spec excerpts, ADRs, design principles — from project's specs/]

## Project Calibration (if reviews/calibration.md exists)
[Per-dimension benchmarks and anchor examples for this project]

## Criteria
[R1: "Flag anything that might be an issue. Include borderline cases tagged [BORDERLINE]."]
[R2+: "Only findings where a consumer would FAIL or an executor would take WRONG ACTION."]

## Files to Review
[FULL file list — every panel sees every file. Partitioning is by defect class, not by file.]

## Output Format

Return your structured findings. DO NOT write output files.

### Finding format (one per issue):

| Field | Required | Description |
|-------|----------|-------------|
| **Expert** | Yes | Which expert's framework identified this issue |
| **Severity** | Yes | Critical / Important / Minor / Suggestion / [BORDERLINE] (R1 only) |
| **File:Line** | Yes | Exact file path and line number |
| **Issue** | Yes | What is wrong, in one sentence |
| **Spec Reference** | If applicable | Which ADR, spec section, or convention is violated |
| **Fix** | Yes | Concrete fix description |

### MD finding block format:

```markdown
### [SEVERITY] File:Line — Issue title

**Expert:** Expert Name (*Work*)
**File:** `path/to/file.ext:123`
**Spec:** ADR-005 / cross-cutting.md §conventions (if applicable)

**Issue:** One-sentence description of what is wrong.

**Fix:** Concrete description of what to change.
```

### Summary table:

A markdown table with columns: #, Severity, File, Issue, Expert, Status (open).
```

## Severity Definitions

| Severity | Meaning |
|---|---|
| **Critical** | Security vulnerability, spec violation breaking functionality, dead code at architecture level |
| **Important** | Type safety gap, missing accessibility, test coverage hole, design system violation |
| **Minor** | Inconsistency, style issue, small coverage gap |
| **Suggestion** | Alternative approach, optimization, future-proofing |
| **[BORDERLINE]** | R1 only. Might be an issue — flagged for synthesis filtering. Converted to a severity or discarded during step 5. |

## Key Rules

1. **Parallel dispatch is the point** — panels run as concurrent subagents, all dispatched in a single message.
2. **Panels are orthogonal by defect class, not by expertise** — each panel scans for a specific class of defect across ALL files. No two panels scan for the same class (Basili: orthogonal mandates maximise unique findings).
3. **Every panel sees every file** — partitioning is by defect class, not by file. A file with both a path error and a logic error is found by Panel A and Panel C respectively.
4. **Named experts activate deeper knowledge** — experts are assigned to the panel whose defect class matches their primary framework. The expert is still grounded; the mandate is orthogonal.
5. **Two passes per panel** — systematic scan (line-by-line enumeration) then cross-reference scan (relationship tracing). This mitigates the satisfaction-of-search effect (Drew & Wolfe: scanning for one class at a time prevents premature termination).
6. **Liberal R1, strict R2+** — R1 uses a low detection threshold to maximise recall (Green & Swets: liberal criterion). R2+ applies the Finding Quality Gate (consumer FAIL only).
7. **Capture-recapture after R1** — estimate remaining defect population from panel overlaps (Wohlin: Lincoln-Petersen estimator). This converts "should we do R2?" from a guess into a calculation.
8. **Findings must be actionable** — every finding needs a specific fix with file:line.
9. **Spec is the standard** — review against the project's own spec and ADRs.
10. **Synthesise, don't just aggregate** — identify cross-panel themes, elevate severity for multi-panel findings.
11. **No self-review** — subagents get fresh context, preventing confirmation bias.
12. **Experts who find should fix** — per shared rule 3.
13. **Expert discovery for uncovered domains** — per shared rule 2.
14. **HTML-only output** — per shared rule 13 exception for review reports. No paired MD is produced — findings are carried forward in `reviews/calibration.md`.
