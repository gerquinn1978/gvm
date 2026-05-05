---
name: gvm-design-review
description: Use when reviewing whether a design (data model, UI/UX, API) correctly fulfils requirements. Triggered by /gvm-design-review command, requests to review a database schema against requirements, check if a UI covers all user journeys, or verify API contracts. Also triggered by /gvm-site-survey when it identifies design concerns. Dispatches parallel defect-class panels as subagents, grounded in the project's spec-declared specialists.
---

# Design Review

## Overview

Reviews whether a design correctly translates requirements into a workable solution — before code is written — by dispatching parallel defect-class subagents. Each subagent scans every spec for a specific *class* of design defect, not a broad domain area. Panels are partitioned so their scanning mandates are orthogonal — minimal overlap, maximum first-pass coverage.

Where `/gvm-doc-review` checks document quality and `/gvm-code-review` checks implementation quality, `/gvm-design-review` checks **design correctness**: does the design cover every requirement? Do interface contracts align across boundaries? Is the architecture structurally sound? Can a developer actually build from this design?

This skill does not review documents for writing quality or code for implementation quality. It reviews designs for requirements coverage and expert-informed best practice.

**Pipeline position:** `/gvm-requirements` → `/gvm-test-cases` → `/gvm-tech-spec` → **`/gvm-design-review`** → `/gvm-build`

The design review sits between spec and build. The specs define the design; the design review validates it against requirements before implementation begins. It can also be triggered by `/gvm-site-survey` when diagnosing an existing codebase.

**Shared rules:** At the start of this skill, load `~/.claude/skills/gvm-design-system/references/shared-rules.md` and follow all rules throughout execution. Load `~/.claude/skills/gvm-design-system/references/expert-scoring.md` when scoring experts.

## Methodological Basis

The panel structure is grounded in published inspection research, not convention:

- **Orthogonal defect partitioning** (Laitenberger, Atkinson, Schlich & El Emam, "An experimental comparison of reading techniques for defect detection in UML design documents", Fraunhofer IESE, *Journal of Systems and Software*, 2000): Perspective-Based Reading (PBR) assigns each reviewer a non-overlapping scanning mandate. PBR teams detected 41% more unique defects than checklist-based teams at 58% lower cost per defect.
- **Satisfaction of Search mitigation** (Drew, Võ & Wolfe, "The Invisible Gorilla Strikes Again", 2013): After finding one defect in a region, the probability of detecting a second drops. The fix: scan the entire artefact once per defect class rather than once for all classes. Each panel makes focused passes for its class.
- **Liberal criterion on first pass** (Signal Detection Theory, Green & Swets, 1966): Set the detection threshold low on R1 (flag borderlines), filter false positives in synthesis. This maximises recall at acceptable precision cost. R2+ raises the bar to strict.
- **Capture-recapture estimation** (Wohlin, Petersson & Aurum, adapted for software inspection): After R1, count panel overlaps to estimate the total defect population and calculate whether R2 is needed rather than guessing.

## Hard Gates

These steps are non-negotiable. If you skip any of them, the review output is invalid.

1. **DISPATCH PANELS IN PARALLEL.** YOU MUST dispatch all panels as concurrent subagents via the Agent tool — all in a single message. If you review sequentially instead of in parallel, you are not executing this skill correctly. Parallel dispatch is the core value of this skill.

2. **LOAD EXPERT REFERENCES BEFORE DISPATCH.** Read `architecture-specialists.md` and the relevant `domain/*.md` files from `~/.claude/skills/gvm-design-system/references/domain/` BEFORE writing the dispatch prompts. Load domain files selectively — see `domain-specialists.md` index for activation signals. Each panel prompt MUST include expert excerpts loaded from these files — generic descriptions are not a substitute for loaded content.

3. **WRITE HTML OUTPUT.** The review MUST produce `design-review/design-review-{NNN}.html`. Review reports are HTML-only — no paired MD is produced (shared rule 13 exception for review reports). Findings are carried forward in `reviews/calibration.md`. The HTML file must exist before presenting findings or offering next steps. DO NOT end the review without the HTML file written.

4. **UPDATE CALIBRATION.** After presenting findings, YOU MUST create or update `reviews/calibration.md`. DO NOT end the review without it.

5. **VERDICT.** Every review must include a verdict using the design-review language from `review-reference.md` (Build from this / Build with caveats / Do not build). The verdict appears in the report and in the text presented to the user. DO NOT end a review without a verdict.

6. **USER OWNS FINDING TRIAGE (shared rule 28 — Review Finding Triage Is User-Owned).** Every Critical or Important finding emitted by panels MUST be presented to the user before any disposition is recorded. This skill MAY recommend "fix / defer / dismiss" per finding but MUST NOT decide. The Finding Quality Gate is the panels' emit threshold under R2+ strict — not a post-synthesis filter for Claude to invoke after panels return. Forbidden patterns (canonical phrasing — match shared-rules.md § 28 verbatim):

   - Recording emitted findings as "filtered under strict criterion" without user input.
   - Recording emitted findings as "deferred to v{N}.{M}.{P} hardening" without user input.
   - Bundling the verdict with the user's first sight of the finding list. Verdict comes after triage, not before.
   - Presenting a summary count that hides which findings were deferred (zero-deferred summaries are permitted).

   See shared-rules.md § 28 for the full permitted list and rationale.

## Prerequisites

Before dispatching panels, verify:

1. **`requirements/requirements.md` must exist.** The design review validates designs against requirements. Without requirements, there is nothing to validate against. If missing, tell the user to run `/gvm-requirements` first.
2. **`specs/` directory must contain at least one spec file.** The designs to review come from the specs. If missing, tell the user to run `/gvm-tech-spec` first.
3. **If invoked from `/gvm-site-survey`**, specs may not exist. In that case, read design artefacts directly from the codebase: schema files for data models, component trees for UI structure, route definitions for API contracts.

## Input

One of:
- **Auto-detect** (no arguments) — scan `specs/` for all design content, dispatch all four defect-class panels
- **Specific focus** — "review the data model" or "review the API contracts" — all four panels still run (they scan by defect class), but the focus narrows which spec sections are emphasised
- **Site survey referral** — `/gvm-site-survey` passes specific concerns to investigate

If invoked without arguments after `/gvm-tech-spec` completes, auto-detect design content from the specs and dispatch all panels.

## Expert Sources

All expert definitions live in `~/.claude/skills/gvm-design-system/references/`:

| File | Tier | When Active |
|---|---|---|
| `architecture-specialists.md` | 1 | Always |
| `domain/*.md` files | 2a | Load selectively — see `domain-specialists.md` index for activation signals. Based on which design domains are present (data modelling, UX/interaction, integration, user documentation) |
| `stack-specialists.md` (index) → `stack/*.md` | 3 | Based on the technology stack in the specs — load index for constraints, then matching per-stack files |
| `writing-reference.md` | — | For user documentation assessment (loaded by UI/UX panel) |

The project's own `specs/` (e.g., `specs/cross-cutting.md`) declare which experts were activated for that specific project and contain project-specific design principles to review against.

**Note:** The main skill does not pre-load full reference files. Each subagent receives the relevant expert excerpts in its dispatch prompt. The main skill reads `specs/cross-cutting.md` to determine which experts were declared for this project.

## Defect-Class Panels

Panels are partitioned by defect class, not by design domain (Basili: orthogonal scanning mandates maximise first-pass detection). Each panel scans **every spec** for a specific *class* of design defect — the experts are still grounded, but the scanning mandate is orthogonal. Every panel sees every spec; partitioning is by defect class, not by domain.

### Panel A: Requirements Coverage

**What to scan:** Every requirement in `requirements/requirements.md`. Does the design address it? Are there requirements with no corresponding design element? Are there design elements with no tracing requirement?

**Experts assigned:** Wiegers (requirements traceability — every requirement must trace to a design element and back), Cohn (INVEST — is every chunk independently implementable from this design?).

**Scanning method:**

**Pass 1 — Systematic scan:** Walk through every MUST and SHOULD requirement. For each, locate the spec section(s) that address it. Record: Covered / Partial / Missing. For partial coverage, state what is missing.

**Pass 2 — Cross-reference scan:** Walk through every design element in the specs. For each, locate the requirement it traces to. Flag orphan design elements — spec content with no tracing requirement (scope creep or undocumented requirement). Check that every requirement chunk is INVEST-compliant: Independent, Negotiable, Valuable, Estimable, Small, Testable.

### Panel B: Interface Contracts

**What to scan:** Every boundary where two components exchange data — API shapes between producer and consumer, data model fields vs the UI that displays them, error response shapes, schema constraints vs business rules.

**Experts assigned:** Keeling (interface contracts — decisions at boundaries must be captured and consistent), Newman (service boundaries — where to draw the lines and what crosses them), Kleppmann (data-intensive contracts — schema evolution, encoding, compatibility — where applicable).

**Scanning method:**

**Pass 1 — Systematic scan:** For each API endpoint, data transfer shape, or integration point in the specs, verify: do field names, types, nesting, and required/optional markers match between producer and consumer? Do error response shapes follow a consistent contract? Do schema constraints (NOT NULL, unique, foreign key) match the business rules in the requirements?

**Pass 2 — Cross-reference scan:** Trace data flows across spec boundaries. Does the backend response shape match what the frontend consumes? Does the database schema support every field the API promises? Are there fields the UI displays that no API provides? Flag every mismatch — these are the bugs that survive to runtime.

### Panel C: Structural Soundness

**What to scan:** The architecture's internal consistency — dependency direction, state management, transaction/consistency boundaries, quality attribute support.

**Experts assigned:** Bass & Kazman (quality attributes — does the architecture support the quality attribute scenarios in the requirements?), Fowler (patterns — are the structural patterns applied correctly and consistently?), Brooks (conceptual integrity — does the design feel like one mind designed it?), Fairbanks (risk-driven — are the architecturally significant, risky parts designed with sufficient thoroughness, or hand-waved?).

**Scanning method:**

**Pass 1 — Systematic scan:** For each component, module, or service in the specs, check: are dependencies acyclic? Is state managed in one place or scattered? Are transaction boundaries explicit? Does each component have a single responsibility? Are quality attribute scenarios (performance, security, availability) addressed by specific architectural decisions, not just stated as goals?

**Pass 2 — Cross-reference scan:** Trace across specs for structural consistency. Do the same patterns appear everywhere, or does each spec invent its own approach? Are there circular dependencies between specs? Does the overall architecture support the non-functional requirements, or does it only address the happy path? Flag any risky area (concurrency, distributed state, complex workflows) that lacks detailed design.

### Panel D: Implementability

**What to scan:** Whether a developer can actually build from this design without guessing. Clarity of abstractions, specificity of specifications, alignment with the tech stack's capabilities.

**Experts assigned:** McConnell (construction clarity — is the design specified to the level where a developer can code without ambiguity?), Hunt & Thomas (tracer bullets — does the design support thin vertical slices that can be built and validated incrementally?), stack specialists (does the design match what the chosen tech stack can actually do?).

**Scanning method:**

**Pass 1 — Systematic scan:** For each design element in the specs, ask: could a developer implement this without asking clarifying questions? Are data types specified or left vague? Are edge cases defined or deferred? Are there abstractions that sound clear but have no concrete specification? Flag any spec section where a builder would be forced to guess.

**Pass 2 — Cross-reference scan:** Trace the design against the tech stack declared in the specs. Does the design assume capabilities the stack does not have? Does it fight the stack's conventions? Can the design be built in thin vertical slices (tracer bullets), or does it require building everything before anything works? Flag any design that requires a big-bang integration.

**Pass 3 — MVP-1 compliance scan:** Check whether the design supports MVP-1 (Minimum Viable Product first ordering). Does the design admit a thin end-to-end vertical slice that delivers user-visible value as the first chunk? Or does it force a horizontal build order — all data layer first, then all service layer, then all UI — that defers user-visible behaviour to the final phase? Flag designs that structurally prevent MVP-1, since `/gvm-tech-spec` Phase 5 will refuse to sequence chunks against them and `/gvm-build` Hard Gate 9 will refuse to start. Exemption is permitted for the four named project shapes (`library`, `refactor`, `performance-driven`, `fully-specified`) — confirm the design declares one if MVP-1 cannot be satisfied. Horizontal architectural consistency across slices is required and is NOT a violation; the rule is about the build *sequence*, not the design *shape*.

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
0. BOOTSTRAP — per shared rule 14, verify ~/.claude/gvm/ exists before writing output.

1. RESOLVE SCOPE
   ├── Read specs/*.md to identify all design content
   ├── If invoked with a specific focus (e.g., "review the data model"),
   │   note the focus but still dispatch all four panels — they scan by defect class, not domain
   ├── If invoked from /gvm-site-survey, read the survey report for specific concerns
   └── If no design content found in specs, tell the user

2. SELECT DEPTH (via AskUserQuestion)
   ├── "Quick scan" — expert panels still run but focus on requirements coverage
   └── "Full review" — coverage plus deep best-practice audit, scores, cross-panel themes

3. ASSIGN EXPERTS TO PANELS
   ├── Read the project's specs/cross-cutting.md to see which experts are declared
   ├── Read relevant domain specs for their declared specialists
   ├── Load expert reference files (architecture-specialists, relevant domain/, relevant stack/)
   ├── Assign each loaded expert to exactly one panel (A/B/C/D) based on their primary defect class
   ├── If any domain has no expert coverage → expert discovery per shared rule 2
   ├── If the project declares specialists not covered by A-D → create Panel E with specific defect-class mandate
   └── Present panel assignments to user for confirmation

4. LOAD CONTEXT
   ├── Bootstrap GVM home directory per shared rule 14
   ├── Read requirements/requirements.md
   ├── Read test-cases/test-cases.md if it exists
   ├── Read ALL spec files — every panel sees every spec (partitioning is by defect class, not by domain)
   ├── Read ~/.claude/skills/gvm-design-system/references/review-reference.md (assessment methodology)
   ├── Read ~/.claude/skills/gvm-design-system/references/writing-reference.md (report writing quality — per shared rule 5)
   ├── Read reviews/calibration.md if it exists (project-level calibration)
   │   ├── Count score history rows — if 2+ prior rounds, dual review applies (shared rule 16)
   │   └── Set criteria: R1 = liberal, R2+ = strict (see Criteria by Round)
   ├── Read reviews/build-checks.md if it exists. Active checks are used to update 'Last triggered' during the calibration update step.
   ├── Load relevant expert sections from gvm-design-system/references/
   ├── Load industry domain file if applicable
   └── Log all loaded experts to activation CSV (per shared rule 1)

5. DISPATCH PARALLEL PANELS
   ├── Use the Agent tool to dispatch panels A, B, C, D (+ E if needed) — ALL IN PARALLEL
   ├── Each agent prompt includes:
   │   ├── Defect class mandate: "You scan for [class]. Do NOT scan for [other classes]."
   │   ├── Expert identities assigned to this panel (names + works — excerpted from canonical reference)
   │   ├── ALL spec files (every panel sees every spec — partitioning is by defect class, not by domain)
   │   ├── Requirements (full)
   │   ├── Test cases (if available)
   │   ├── Criteria: "Liberal — flag borderlines as [BORDERLINE]" (R1) or "Strict — consumer FAIL only" (R2+)
   │   ├── Scanning instruction: "Make two passes through every spec:
   │   │     Pass 1: Systematic scan — read each spec section by section for your defect class
   │   │     Pass 2: Cross-reference scan — trace across specs and against requirements for your defect class"
   │   ├── Depth mode (quick scan or full review)
   │   └── Project calibration data (if available)
   ├── Use model: sonnet for panel agents
   └── DUAL REVIEW (round 3+ per shared rule 16):
       ├── Dispatch a second set of panels IN PARALLEL with the calibrated panels
       ├── Blind panels receive the same specs, requirements, experts, and defect-class mandates
       ├── Blind panels do NOT receive calibration data, anchors, or resolved findings
       ├── **READ-VERIFICATION MANDATE** (every blind and calibrated panel prompt MUST include):
       │   • "You MUST read every input file listed below using the Read tool before writing any finding.
       │     Your report opens with a `## Files Read` section listing each file with its byte count as
       │     returned by Read. If you skip this section or cite a file you didn't read, the synthesis
       │     step will discard your findings as unverifiable."
       │   • "Every finding MUST cite a specific `file.md:line` and quote the offending text verbatim.
       │     Findings without line-anchored citations are treated as noise."
       │   └── Rationale: a panel that did not read its inputs can hallucinate plausible-sounding
       │       findings against spec text that was fixed in an earlier round. Requiring verbatim
       │       quotes and a read manifest makes hallucination detection mechanical rather than manual.
       └── Both sets complete before synthesis

6. SYNTHESISE RESULTS
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
   │   └── If coverage >= 80%: R2 is optional (note in report)
   │   (Wohlin, Petersson & Aurum: capture-recapture adapted for software inspection)
   ├── DUAL REVIEW RECONCILIATION (round 3+ per shared rule 16):
   │   ├── **HALLUCINATION CHECK (first step)**: for each panel, verify:
   │   │   • The panel's report contains a `## Files Read` section listing inputs with byte counts
   │   │   • A sample (at least 3 findings) is spot-checked by grepping the quoted spec text against
   │   │     the actual spec file. If the quote is not present verbatim (allowing for minor whitespace),
   │   │     the panel is flagged as unreliable and ALL its findings are held pending manual review.
   │   │   • If `tool_uses` count is observable (from the task notification): flag any panel with
   │   │     tool_uses ≤ 2 as suspect — it almost certainly did not read all input files.
   │   ├── Classify each blind panel finding as: new, confirmed, regression, rediscovered, or noise
   │   ├── Merge new findings and regressions into the consolidated report
   │   └── Tag merged findings with their blind-review origin
   └── Prioritise: Critical > Important > Minor > Suggestion

7. WRITE REPORT
   ├── Output HTML only to design-review/design-review-{NNN}.html (no paired MD — shared rule 13 exception for review reports)
   ├── Scan for existing files and increment (never overwrite)
   ├── Load tufte-html-reference.md AND tufte-review-components.md before first HTML write
   ├── **HTML generation:** Dispatch the HTML report generation as a Haiku subagent (`model: haiku`). Per shared rule 22.
   ├── Log cited experts to activation CSV (per shared rule 1)
   └── Report contains all sections from the Output structure below

8. PRESENT CONSOLIDATED REVIEW
   ├── Summary table: panels run, findings per severity, capture-recapture estimate (R1)
   ├── Requirements coverage matrix: requirement ID → design coverage (Covered / Partial / Missing)
   ├── Cross-cutting themes
   ├── Critical findings (must fix) with spec location and fix
   ├── Important findings (should fix)
   ├── Minor + suggestions (grouped)
   ├── Borderline filter results (R1): how many kept, how many discarded, filter ratio
   ├── Per-panel detail
   └── Score per defect class (0-10) with rubric anchors (full review only)

9. OFFER NEXT STEPS (via AskUserQuestion)
   ├── "Fix design gaps in specs before building"
   ├── "Proceed to build — gaps are acceptable"
   ├── "Run /gvm-doc-review on the updated specs"
   └── "Re-run site survey to check if fixes resolved the concerns"

   Regardless of which option the user selects, run step 10 (UPDATE CALIBRATION)
   before executing their choice. Calibration update is mandatory after every review.

10. UPDATE CALIBRATION (per `~/.claude/skills/gvm-design-system/references/review-reference.md`)
   ├── Create reviews/calibration.md if it does not exist
   ├── Append a score history row (round, date, type=design, per-dimension scores)
   ├── Record capture-recapture data (R1): estimated total, unique found, coverage %
   ├── Record borderline filter ratio (R1): kept/total
   ├── Update dimension benchmarks (baseline, current, trend)
   ├── Curate anchor examples — for each dimension, keep the 2 best and 2 worst
   │   concrete findings from this project
   ├── Update recurring findings — issues flagged in 2+ consecutive rounds
   ├── Move resolved findings — issues from prior rounds confirmed fixed
   ├── Record dual review metadata (dual review rounds only): findings by source (calibrated-only, blind-only, confirmed-by-both, regressions)
   ├── Promote eligible findings to build checks (per shared rule 21)
   │   ├── Scan recurring findings: if flagged in 3+ consecutive rounds or regressed after resolution, promote
   │   ├── Create or update reviews/build-checks.md with new build checks
   │   ├── Update "Last triggered" round for any active checks that match current findings
   │   └── Retire stale build checks (active checks not triggered in 3 consecutive rounds)
```

## Integration with Site Survey

When `/gvm-site-survey` identifies design concerns in an existing codebase, it can recommend `/gvm-design-review` with specific focus areas. When invoked with a site survey referral, the design review:

1. Reads the site survey report for the specific concerns
2. Dispatches all four defect-class panels (defect classes apply regardless of the concern's domain)
3. For existing codebases without formal specs, reads code artefacts directly: schema files for data models, component trees for UI structure, route definitions for API contracts
4. Reports back with explicit reference to the survey findings: "The site survey flagged X. This review confirms/contradicts the concern."

## Output

Produces an HTML-only report (no paired MD):

```
design-review/design-review-001.html
design-review/design-review-002.html
...
```

Scan for existing files and increment. Use the Read tool to load both `~/.claude/skills/gvm-design-system/references/tufte-html-reference.md` (core) and `~/.claude/skills/gvm-design-system/references/tufte-review-components.md` (verdict + score card + issues) before the first HTML write.

**Report structure:**

0. **Verdict** — Build from this / Build with caveats / Do not build (per review-reference.md). Positioned before the Executive Summary.
1. **Executive Summary** — panels run, overall coverage, critical gaps, capture-recapture estimate (R1)
2. **Requirements Coverage Matrix** — every requirement ID mapped to design coverage status (from Panel A)
3. **Panel A Findings: Requirements Coverage** — requirement-by-requirement traceability, orphan design elements, INVEST compliance
4. **Panel B Findings: Interface Contracts** — contract mismatches, schema-business rule alignment, error contract consistency
5. **Panel C Findings: Structural Soundness** — dependency cycles, state management, quality attribute support, risk coverage
6. **Panel D Findings: Implementability** — ambiguous specs, tech stack mismatches, vertical slice feasibility
7. **Cross-Panel Themes** — issues that span multiple panels (elevate severity for multi-panel findings)
8. **Borderline Filter Results** (R1 only) — how many kept, how many discarded, filter ratio
9. **Scores** — per defect class, 0-10 with rubric anchors and concrete deductions (full review only)
10. **What Prevents a Higher Score** — per `review-reference.md`, state each sub-10 dimension gap. Placement: after scores, before expert panel.

## Severity Definitions

| Severity | Meaning |
|---|---|
| **Critical** | Requirement has no design representation at all — cannot be built from this design |
| **Important** | Design partially covers requirement but with gaps — buildable but incomplete |
| **Minor** | Design covers requirement but violates expert best practice — functional but suboptimal |
| **Suggestion** | Alternative approach that would improve the design — not a gap |
| **[BORDERLINE]** | R1 only. Might be an issue — flagged for synthesis filtering. Converted to a severity or discarded during step 6. |

## Key Rules

1. **Parallel dispatch is the point** — panels run as concurrent subagents, all dispatched in a single message.
2. **Panels are orthogonal by defect class, not by domain** — each panel scans for a specific class of defect across ALL specs. No two panels scan for the same class (Basili: orthogonal mandates maximise unique findings).
3. **Every panel sees every spec** — partitioning is by defect class, not by domain. A spec with both a requirements gap and a contract mismatch is found by Panel A and Panel B respectively.
4. **Named experts activate deeper knowledge** — experts are assigned to the panel whose defect class matches their primary framework. The expert is still grounded; the mandate is orthogonal.
5. **Two passes per panel** — systematic scan (spec by spec) then cross-reference scan (trace across specs and against requirements). This mitigates the satisfaction-of-search effect (Drew & Wolfe: scanning for one class at a time prevents premature termination).
6. **Liberal R1, strict R2+** — R1 uses a low detection threshold to maximise recall (Green & Swets: liberal criterion). R2+ applies the Finding Quality Gate (consumer FAIL only).
7. **Capture-recapture after R1** — estimate remaining defect population from panel overlaps (Wohlin: Lincoln-Petersen estimator). This converts "should we do R2?" from a guess into a calculation.
8. **Requirements are the standard** — the design is reviewed against requirements, not against abstract best practice. A design that violates an expert principle but correctly implements the requirements is noted as a suggestion, not a critical finding.
9. **Coverage matrix is mandatory** — every design review must produce a requirement-by-requirement coverage check. The user should see at a glance which requirements have design coverage and which don't.
10. **Existing codebases work without specs** — when invoked after a site survey, the review reads code artefacts directly (schema files, component trees, route definitions) instead of spec documents.
11. **Experts who find should fix** — per shared rule 3. Design gaps identified by a panel should be resolved using the same experts' principles.
12. **Expert discovery for uncovered domains** — per shared rule 2.
13. **HTML-only output** — per shared rule 13 exception for review reports. No paired MD is produced — findings are carried forward in `reviews/calibration.md`.
14. **Synthesise, don't just aggregate** — identify cross-panel themes, elevate severity for multi-panel findings.
15. **Depth is the user's choice** (Fairbanks: risk-proportional ceremony). On invocation, offer depth via AskUserQuestion:
    - **Quick scan** — expert panels still run but focus on requirements coverage: does every requirement have design representation? Experts assess the coverage through their lens but do not audit best practice in depth. Produces a coverage matrix with expert-informed gap identification. Good for a sanity check before build.
    - **Full review** — coverage matrix plus deep expert best-practice audit across all defect classes. Parallel panel dispatch with full checklists. Scores, findings, cross-panel themes. Good for pre-build quality gate or post-site-survey deep dive.
    Both modes use experts — the difference is depth, not whether experts participate.
