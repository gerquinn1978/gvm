---
name: gvm-walking-skeleton
description: Use when wiring a thin end-to-end execution thread through every external integration boundary before feature work begins. Triggered by /gvm-walking-skeleton command or requests to set up a walking skeleton, wire integration boundaries, or create boundaries.md. Produces a runnable skeleton that exercises real (or sandbox) calls, plus a boundaries.md registry that downstream /gvm-build and /gvm-test gate against (WS-5 red-skeleton refusal, VV-4(d) sandbox-divergence check).
---

# Walking Skeleton

## Overview

Discovery + scaffolding skill that produces a `walking-skeleton/` directory and a project-root `boundaries.md` registry. The skeleton is a runnable program that exercises every external boundary the project touches — HTTP outbound, database, cloud SDK, filesystem, subprocess, email — through real or sandbox calls. The point is to surface integration failure modes (auth, CORS, rate limits, connection strings) at hour 1, not month 6.

Freeman & Pryce's *Growing Object-Oriented Software, Guided by Tests* is the structural model: ship the shape, not the meat. Cockburn's *Crystal Clear* names the discipline — the skeleton is intentionally minimal, an architectural spike, not production code. Reinertsen names the failure mode that WS-1..5 mechanically prevent: horizontal slicing defers integration risk.

**Pipeline position:** `/gvm-init` → `/gvm-impact-map` → `/gvm-requirements` → `/gvm-test-cases` → `/gvm-tech-spec` → **`/gvm-walking-skeleton`** → `/gvm-build` → `/gvm-code-review` → `/gvm-test` → `/gvm-explore-test` → `/gvm-doc-write` → `/gvm-doc-review` → `/gvm-deploy`

**Shared rules:** At the start of this skill, load `~/.claude/skills/gvm-design-system/references/shared-rules.md` and follow all rules throughout execution. Load `~/.claude/skills/gvm-design-system/references/expert-scoring.md` when scoring experts.

## Hard Gates

These steps are non-negotiable. If you skip any of them, the walking-skeleton output is invalid.

1. **EVERY EXTERNAL DEPENDENCY REGISTERED IN `boundaries.md`.** Per walking-skeleton ADR-403. The source-scan in Phase 2 produces draft rows; the practitioner confirms each via AskUserQuestion. No undeclared boundary may be left unregistered when the skill exits. Implementation: `_discovery.scan(...)` (delivered by P11-C01) drives discovery; the `_validator.full_check(...)` (P11-C02) enforces completeness.

2. **EVERY BOUNDARY EITHER WIRED OR DEFERRED — NO IN-BETWEEN.** Each row in `boundaries.md` carries `real_call_status ∈ {wired, wired_sandbox, deferred_stub}`. `wired_sandbox` requires a non-trivial `production_sandbox_divergence` note (the parser raises `DivergenceMissingError` otherwise). `deferred_stub` requires a corresponding `STUBS.md` entry with expiry per HS-1 / WS-6 (joint with honesty-triad ADR-101). Implementation: `_validator` (P11-C02) + the existing `_boundaries_parser` (P7-C04) + the existing `_stubs_parser` (P7).

3. **MOCKED-BOUNDARY REFUSAL AT VALIDATION.** Per ADR-404, a wired boundary must be exercised by a real (or sandbox) runtime call. The skill writes `walking-skeleton/test_skeleton.{py,ts,go}` exercising every wired boundary; the validator (P11-C02) refuses skeletons whose tests mock instead of calling. Implementation: `_validator` AST/regex inspection of the skeleton test file.

4. **PAIRED MD + HTML BEFORE APPROVAL.** Per cross-cutting ADR-003 and shared rule 13, `boundaries.md` is paired with `boundaries.html`. Both files must exist at project root before the AskUserQuestion approval prompt fires.

5. **CI HOOK INSTALLED ON COMPLETION.** Per ADR-406, the skill writes (or amends) a CI job in the project's existing CI configuration (GitHub Actions / GitLab / CircleCI) or falls back to a Makefile + RUNBOOK. Implementation: `_ci_writer` (P11-C04). The hook is what makes WS-5 (red-skeleton refusal in `/gvm-build`) enforceable downstream.

## Expert Panel

Loaded when `/gvm-walking-skeleton` runs. Activations are logged to the activation CSV (per shared rule 1).

| Expert | Work | Role in this skill |
|---|---|---|
| **Steve Freeman & Nat Pryce** | *Growing Object-Oriented Software, Guided by Tests* | Walking-skeleton purpose — shape not meat. The skill's outcome is "the integration thread runs end-to-end", not "the feature works". |
| **Alistair Cockburn** | *Crystal Clear* | Architectural spike vs production code — keeps the skeleton intentionally thin. |
| **Michael Nygard** | *Release It!* (2nd ed.) | Stability patterns at boundaries — circuit breakers, timeouts, bulkheads. The first-run debug exposes which boundaries need them. |
| **Mike Cohn** | *Agile Estimating and Planning* | Vertical-slice discipline — the skeleton is the canonical vertical slice. |
| **Donald Reinertsen** | *Principles of Product Development Flow* | Names the horizontal-slicing failure mode WS-1..5 mechanically prevent. |
| **Dave Farley & Jez Humble** | *Continuous Delivery* | Pipeline-as-truth — once the skeleton is green, staying green is the integration health metric. |
| **J.B. Rainsberger** | *Integrated Tests Are A Scam* | Why mocked boundaries hide integration failures — the policy basis for ADR-404 (real-call validation). |
| **Marty Cagan** | *Inspired* | Provider selection (WS-7) framed as bounded feasibility-risk evaluation. |

Stack specialists (e.g., Python, TypeScript, Go) load when the skeleton-generator (P11-C03) writes the runnable test file in the project's language.

## Process Flow

```
0. BOOTSTRAP
   ├── Verify ~/.claude/gvm/ exists (shared rule 14)
   ├── Verify the project root is writable
   └── Load expert references (architecture-specialists.md, walking-skeleton domain spec)

1. PREREQ CHECK
   ├── specs/cross-cutting.md exists (run /gvm-tech-spec first if not)
   ├── requirements/requirements.md and impact-map.md exist
   └── If walking-skeleton/ already exists: confirm overwrite via AskUserQuestion

2. DISCOVERY  (P11-C01 — this scaffold; AskUserQuestion confirmation arrives in P11-C02)
   ├── Scan source via _discovery.scan() using boundary-discovery.md heuristics
   ├── Each candidate becomes a draft boundaries.md row
   └── (P11-C02) Present each via AskUserQuestion: "Real boundary? (Yes/Skip/Other)"
       Then ask: "Any other boundaries?" (free-text capture)

3. PROVIDER SELECTION  (P11-C02 — per boundary, ADR-408 flow)
   ├── For each draft boundary: AskUserQuestion for provider, endpoints, cost, SLA
   ├── Mark wired / wired_sandbox / deferred_stub
   ├── For wired_sandbox: prompt for divergence note (required, non-trivial)
   └── Write boundaries.md row after each boundary (resumable if interrupted)

4. SKELETON GENERATION  (P11-C03)
   ├── Generate walking-skeleton/test_skeleton.{py,ts,go} — one runnable test per boundary
   ├── Generate per-boundary client wrappers (real auth wired)
   ├── Generate walking-skeleton/stubs/<name>.{ext} for deferred boundaries
   │     (HS-1 namespace per ADR-407; STUBS.md Path = walking-skeleton/stubs/<name>.py)
   ├── Write paired boundaries.md + boundaries.html at PROJECT ROOT (ADR-403)
   └── Run _single_flow_check.lint(); refuse if > N tests (N=3 default, ADR-405)

5. CI INTEGRATION  (P11-C04)
   ├── Detect CI provider via filesystem markers (ADR-406 — first-match wins)
   ├── AskUserQuestion: "Add walking-skeleton CI job? (Recommended)"
   └── On confirm: write/amend CI config or write Makefile + RUNBOOK

6. FIRST RUN  (P11-C04)
   ├── Practitioner executes skeleton locally (skill provides command)
   ├── Skill records first-run pass/fail in walking-skeleton/.first-run.log
   └── On fail: practitioner debugs auth/CORS/rate-limits — the actual point of WS-3

7. APPROVAL  (P11-C04)
   ├── Skill presents skeleton summary via AskUserQuestion
   └── On approval: skill exits; /gvm-build can proceed (subject to WS-5 CI status check, P11-C05)
```

The Process Flow above is the contract. **P11-C01 (this chunk) delivers Phase 2's source-scan implementation, the SKILL.md scaffold, and the `boundary-discovery.md` heuristics file.** P11-C02 delivers the `boundaries.md` validator and the AskUserQuestion confirmation flow. P11-C03 delivers the skeleton generator and single-flow lint. P11-C04 delivers the CI writer. P11-C05 wires the `/gvm-build` red-skeleton refusal hook.

## Phase Details

### Phase 0 — Bootstrap

Pre-flight per shared rule 14. Refuse to run if the GVM home directory is missing — direct the user to `/gvm-init`.

### Phase 1 — Prereq check

The skeleton's purpose is to wire boundaries declared in the cross-cutting spec; running it before `/gvm-tech-spec` would produce a skeleton against undeclared targets. The prereq check refuses to start when `specs/cross-cutting.md` is missing.

If `walking-skeleton/` already exists, the skill confirms overwrite via AskUserQuestion ("Replace existing walking-skeleton? Options: Replace, Augment (add new boundaries), Cancel"). Augment mode preserves existing rows in `boundaries.md` and only adds new candidates surfaced by Phase 2.

### Phase 2 — Discovery

Source-scan + practitioner-confirm hybrid per ADR-402.

**Source-scan (delivered by P11-C01).** `_discovery.scan(project_root, language)` walks every source file matching the language's extensions and matches each line against tokens from `~/.claude/skills/gvm-design-system/references/boundary-discovery.md`. Matches surface as `BoundaryCandidate(name, type, file, line)` records sorted by file then line. The scan is a discovery aid — false positives are practitioner-rejected at confirmation time; false negatives are added via the "Any other boundaries?" follow-up. Binary and unreadable files are skipped silently (McConnell — defensive programming; the scan must not abort because one source file has unusual encoding).

**Confirmation (delivered by P11-C02).** Each candidate is presented via AskUserQuestion: "Real boundary? Yes / Skip (false positive) / Other". Confirmed candidates progress to Phase 3; skipped ones are dropped without a row.

### Phase 3 — Provider selection

Per ADR-408. For each confirmed boundary the skill emits up to 4 AskUserQuestion calls (chosen provider, cost model, sandbox endpoint, production endpoint, SLA). Answers populate the `boundaries.md` row, which is written immediately so an interrupted session can resume from the next boundary.

For boundaries marked `wired_sandbox`, the practitioner must supply a non-trivial `production_sandbox_divergence` note (e.g., "Test cards only; no Apple Pay; rate limit 25 req/s vs prod 100"). The boundaries-parser (P7-C04) raises `DivergenceMissingError` if the divergence is empty or the literal sentinel `"n/a"`.

For boundaries marked `deferred_stub`, the skill writes a corresponding `STUBS.md` row per HS-1, with `path = walking-skeleton/stubs/<name>.{ext}` (the second permitted prefix, alongside `stubs/`). The practitioner is prompted for an expiry date.

### Phase 4 — Skeleton generation

Per ADR-404 / ADR-405. The skeleton is a runnable program; for each wired (or wired_sandbox) boundary, the test file calls the boundary and asserts success (HTTP 200, query returns row, file read returns bytes). Mocked calls are refused by the validator. The single-flow lint (ADR-405) caps the test file at N=3 functions; an Nth+1 attempt triggers an AskUserQuestion ("Move to /gvm-build / Raise floor / Cancel") — there is no silent config-file override.

### Phase 5 — CI integration

Per ADR-406. Provider detection in order: `.github/workflows/` → GitHub Actions; `.gitlab-ci.yml` → GitLab; `.circleci/config.yml` → CircleCI; otherwise Makefile + RUNBOOK. CircleCI requires two edits — the job under `jobs:` and a workflow entry under `workflows:` — to ensure reachability. YAML editing is text-level (no `pyyaml` dep), with limitations documented in the RUNBOOK.

### Phase 6 — First run

The practitioner runs the skeleton locally; the skill records the result in `walking-skeleton/.first-run.log`. The first failure is the *point* — the practitioner debugs the actual integration issues (auth, CORS, rate limits) that would otherwise emerge later.

### Phase 7 — Approval

Skill presents the summary (boundaries registered, wired vs wired_sandbox vs deferred_stub counts, CI job added). On approval, the skill exits. `/gvm-build` can then proceed; per WS-5, `/gvm-build` reads the latest CI status before each chunk and refuses new chunks while the skeleton is red (delivered by P11-C05).

## Key Rules

1. **Shape, not meat.** The skeleton wires every boundary end-to-end; it does not implement the feature. Feature work is `/gvm-build`'s job. Adding a second feature flow to the skeleton is rejected by the single-flow lint (ADR-405).

2. **Real (or sandbox) calls only.** Mocked boundaries are refused (ADR-404). Sandbox endpoints qualify, but only if the row carries a non-trivial `production_sandbox_divergence` note (ADR-403).

3. **Every boundary declared.** Source-scan + practitioner confirmation produces a complete boundary registry (Hard Gate 1). Undeclared boundaries are how integration failures hide; the registry is the cure.

4. **Deferred boundaries route through `STUBS.md`.** Per ADR-407 / WS-6, joint with HS-1. There is one mechanism for deferred work with expiry — the cross-cutting `_stubs_parser` accepts both `stubs/` and `walking-skeleton/stubs/` prefixes. No parallel system for "boundaries we'll wire later."

5. **CI is the standing integration test.** Once green, the skeleton's CI job is the integration health metric. `/gvm-build` refuses new chunks when the skeleton is red (WS-5, delivered by P11-C05). The pipeline tells the truth even when the practitioner wishes it didn't (Farley).

6. **Provider selection is interactive, not config-driven.** Per ADR-408, each boundary's provider is chosen via AskUserQuestion. The answers persist to `boundaries.md` for audit. Practitioner agency at decision points is preserved (Theme 3).

7. **Hand off to `/gvm-build`.** When the skeleton is approved, direct the user to run `/gvm-build` next. `/gvm-build`'s WS-5 hook (P11-C05) reads the CI status and refuses chunks while the skeleton is red.

8. **Project-extensible heuristics.** The discovery patterns ship in `~/.claude/skills/gvm-design-system/references/boundary-discovery.md`. Projects with unusual libraries surface boundaries via the "Any other boundaries?" follow-up (Phase 2); permanent additions are made by editing the heuristics file (PP-1 covers the propagation path as new patterns emerge).

9. **Pairs with MVP-1 (Minimum Viable Product first ordering).** The walking skeleton is the mechanical enabler of MVP-1: the first vertical slice through every boundary. `/gvm-tech-spec` Phase 5 sequences chunks so the first user-visible flow lands first; this skill produces the wiring that flow runs on. `/gvm-build` Hard Gate 9 mirrors the rule on the read side, and `/gvm-design-review` Panel D Pass 3 flags designs that structurally prevent it.
