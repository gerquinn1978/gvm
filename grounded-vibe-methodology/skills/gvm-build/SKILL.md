---
name: gvm-build
description: Use when implementing code from a /gvm-tech-spec implementation guide. Triggered by /gvm-build command, requests to build/implement a chunk or phase, or requests to start coding from specs. Reads the implementation guide, generates per-chunk prompts, executes with strict TDD, reviews against best practices, and writes handover files for session resilience.
---

# Build

## Overview

Executes the implementation guide produced by `/gvm-tech-spec`. Takes the spec suite and builds working code — chunk by chunk, with strict TDD, expert-reviewed code, git commits, and handover files for session resilience.

This skill writes code. It does not review or verify the product — those belong to `/gvm-code-review` and `/gvm-test`.

**Pipeline position:** `/gvm-requirements` → `/gvm-test-cases` → `/gvm-tech-spec` → `/gvm-design-review` (optional) → **`/gvm-build`**

The implementation guide defines build phases, chunks (P-C IDs), a dependency network, and test co-location rules. `/gvm-build` reads this guide and executes it as code.

**Shared rules:** At the start of this skill, load `~/.claude/skills/gvm-design-system/references/shared-rules.md` and follow all rules throughout execution. Load `~/.claude/skills/gvm-design-system/references/expert-scoring.md` when scoring experts.

## Hard Gates

These steps are non-negotiable. If you skip any of them, the build output is invalid.

> **Note on step references:** Step references use process flow names. If step numbers shift, the names remain stable.

**PRE-FLIGHT: BOOTSTRAP GVM HOME DIRECTORY.** Per shared rule 14, before writing any output, verify `~/.claude/gvm/` exists and is initialized. Run the bootstrap check even if you believe another skill ran first. This is a mandatory pre-flight step that must complete before any gate below.

1. **LOAD GROUNDING MATERIAL BEFORE GENERATING ANY PROMPT.** Read the relevant sections from `architecture-specialists.md`, `stack-specialists.md`, and the relevant domain specialist files from `~/.claude/skills/gvm-design-system/references/domain/` BEFORE assembling the prompt — these go into the "Review Criteria" section. Load only the domain files relevant to the current chunk's spec references (see `~/.claude/skills/gvm-design-system/references/domain-specialists.md` index for available files and activation signals). Also load framework and API documentation relevant to the chunk's tech stack — these go into the "Framework Reference" section. If you have not loaded both expert references and framework documentation, you are not ready to generate a prompt. The "Review Criteria" section must list which experts were loaded — if it is empty, you skipped this step.

2. **WRITE THE PROMPT FILE.** Every chunk MUST have a prompt file at `build/prompts/P{X}-C{XX}.md` written via the Write tool BEFORE execution begins. If `build/prompts/` does not contain a file for this chunk, you have not completed the GENERATE PROMPT step. DO NOT start writing code without a prompt file.

3. **SELF-REVIEW + INDEPENDENT REVIEW CONVERGENCE LOOP — DO NOT SKIP.** Two distinct phases, both mandatory:

   **Phase 1 — author self-review** (per-deliverable, fast). After writing implementation code, review BOTH the test code and the implementation code against the Review Criteria (expert principles + build checks). Fix → re-test → re-review until clean. The defect-class checklist runs here.

   **Phase 2 — independent review convergence loop** (after lint/credentials/static, before commit). This is an EXPLICIT PASS-COUNTED LOOP, not a single dispatch:

   ```
   pass_log = []
   pass_number = 1
   loop:
       findings = Agent(model=sonnet, prompt="pass {pass_number} review of <files>...")
       pass_log.append((pass_number, count_of_critical_or_important(findings)))
       if count == 0: break          # converged
       if pass_number == 5 and not_decreasing(pass_log): stop and flag user
       fix all Critical/Important; re-test
       pass_number += 1
   ```

   The loop ONLY exits when a pass returns zero Critical/Important findings. A single pass with findings is the EXPECTED first state, not the terminal state. Committing after pass-1 is a failure mode regardless of how clean pass-1 looked.

   **Convergence record is mandatory.** The handover MUST contain `Review passes: [(1, N1), (2, N2), ..., (final, 0)]`. The final tuple's count MUST be 0. A handover lacking this field, or whose final tuple is non-zero, is structurally invalid and Gate 4 MUST refuse it.

   **The user checkpoint fires AFTER convergence**, not after pass-1. Presenting "approve and commit?" between pass-1 and pass-2 short-circuits the discipline; AskUserQuestion is the exit ramp, not the bypass.

   This gate catches hallucinated APIs, wrong call patterns, and design violations that tests cannot see. Skipping it — or terminating the loop after one pass — is the single most damaging execution failure in the pipeline.

4. **WRITE THE HANDOVER FILE.** Every completed chunk MUST have a handover file at `build/handovers/P{X}-C{XX}.md` written via the Write tool AFTER all tests pass. If you finish a chunk without writing a handover, the next session cannot detect what was built.

5. **TEST FIRST, ALWAYS — TDD-1 OUTSIDE-IN ORDERING.** Write the failing test BEFORE writing the implementation code. If you find yourself writing application code without a failing test demanding it, stop and write the test first.

   **TDD-1 (outside-in acceptance test as first deliverable).** For user-facing chunks (CLI tools, web products, anything with a smoke surface that Hard Gate 8 will exercise), the **outside-in acceptance test is the FIRST deliverable in the chunk's TDD Approach** — written before any unit test. The acceptance test specifies the user-facing behaviour the chunk delivers; unit tests fall out from the acceptance test's failures, not the other way around (Freeman & Pryce, *Growing Object-Oriented Software, Guided by Tests*). The acceptance test MUST transition Red → Green during the chunk; both commits are recorded in the handover (Beck Red-Green-Refactor; Fagan author preparation — structured evidence beats narrative claims). The chunk prompt template's `## TDD Approach` ordering enforces this — a template that places unit tests before the acceptance test for a user-facing surface is a TDD-1 violation.

   **Pure-internal-helper exemption (ADR-MH-04).** Chunks whose deliverables are `_shared/`-style internal helpers, test fixtures, or refactors with no user-facing surface change MAY skip the acceptance-test-first ordering by recording the literal line `TDD-1 exempted: <reason>` in the chunk handover. The reason must name the qualifying condition (e.g. `internal helper, no user-facing surface change` / `pure refactor — covered by parent chunk's acceptance test`). Reviewers can challenge the claim during code review — the rationale is the audit trail. A silent skip with no recorded `TDD-1 exempted:` marker is a TDD-1 violation regardless of intent. A marker whose text after the colon is empty or whitespace-only (`TDD-1 exempted:` followed by nothing, or by spaces/tabs only) is treated as absent — the exemption is not granted (Fagan: exemptions without rationale are silent skips), and the executor surfaces a TDD-1 refusal naming the chunk.

6. **READ THE WIRING MATRIX BEFORE STARTING ANY PHASE.** Before generating prompts for any chunk in a phase, locate the "Wiring matrix" section in `specs/implementation-guide.md` (mandated by `/gvm-tech-spec` Hard Gate 6). If the matrix is missing, the impl guide is structurally invalid — stop and tell the user to re-run `/gvm-tech-spec` to add it. If the matrix has any row whose **Wiring chunk** column is empty, the impl guide has a known integration gap — surface it via AskUserQuestion before proceeding ("the wiring matrix declares module X is consumed by entry point Y but no chunk owns the call site — fix the impl guide first or accept building with a known dead-code module"). Do not silently proceed past a hole in the matrix.

7. **PHASE-COMPLETION WIRING AUDIT.** After every phase finishes (PHASE COMPLETION step in the process flow), audit the wiring matrix against the chunks just completed. For each row where the **Wiring chunk** column names a chunk in the just-completed phase: open the chunk's handover and the actual source file it modified, then grep the entry-point file for an import/call of the named module. If the entry point does not invoke the module, the wiring chunk did not deliver its declared seam — flag this as a phase-completion blocker. Acceptance is by code, not by the chunk's claim. This is the rule that catches the "tracer-bullet engine boundary" failure mode where Phase 3/4 chunks built modules with green isolated tests but the Phase-N consumer chunk never imported them.

   The audit's grep is mechanical: for each `(entry_point, module)` in the matrix, run `grep -E "import (\.\.)?{module_name}|from .* import.*{module_name}" {entry_point_file}` and `grep -E "{module_name}\.\w+\s*\(" {entry_point_file}`. Both must return at least one hit. If either is empty, the wiring is missing regardless of what the chunk's tests assert.

   **Inverse audit (P20-C02 hardening — every built module is matrix-tracked).** The grep audit above catches matrix entries whose declared seam was not delivered. It does NOT catch the inverse failure mode: a module that was built but never written into the matrix. Both v2.0.0 wiring bugs (P19 chart producer, P20 aggregation) had this shape — the modules existed and had unit tests, but no consumer chunk had been declared, so the row scan had nothing to verify.

   Run `_module_audit.audit(project_root)` from `gvm-build/scripts/_module_audit.py` after the row-grep audit. **`project_root` is the *target project being built*, not the gvm-build skill directory** — it is the directory that contains `specs/implementation-guide.md` and the project's `scripts/_shared/*.py` modules. A naive interpretation that passes the gvm-build directory itself silently nullifies the gate. Concrete invocation:

   ```bash
   python -c "
   import sys
   sys.path.insert(0, '<path-to-gvm-build>/scripts')
   from pathlib import Path
   from _module_audit import audit
   errs = audit(Path('<target-project-root>'))
   for e in errs: print(f'UNWIRED: {e.module_name} -> {e.path}')
   sys.exit(1 if errs else 0)
   "
   ```

   The function enumerates every built module under `scripts/_shared/*.py` (configurable via `module_globs=`) and compares the set against module references in the wiring matrix's table rows. Any built module whose stem does not appear in the matrix and is not in the project's `.module-allowlist` surfaces as `UnwiredModuleError(module_name, path)`. A non-zero exit code is a phase-completion blocker. The fix is one of:
   - Add a wiring-chunk row that owns the consumer call site, and re-run.
   - If the module is a legitimate internal helper (consumed by other `_shared` modules or by CLI wrappers, not by an entry point), add its stem to `<project_root>/.module-allowlist` with a one-line `#`-prefixed rationale.
   - If the module is genuinely dead code, delete it.

   Both audits must pass before phase completion.

8. **CHUNK-LEVEL ACCEPTANCE SMOKE GATE (Hard Gate 8 — GATE-1).** After the chunk's tests pass and the wiring audits run, but BEFORE the handover is written, run a smoke-test command that exercises the chunk's user-facing surface end-to-end and verifies its structural-contract assertions. The smoke is per-stack — there is no single one-size-fits-all assertion list:

   - **CLI tools** — invoke the chunk's CLI entry point with a representative input and assert structural contracts on the produced HTML/JSON: required keys present, required HTML elements present, required values non-empty. The smoke reads the produced artefact and greps for the asserted contracts.
   - **Web products** — hit the relevant health endpoint and walk the affected UI route end-to-end. Assert the health endpoint reports healthy AND the UI route renders the expected interactive elements.
   - **Library / API chunks (no user-facing surface)** — see exemption rule below.

   **Refusal rule:** if the smoke command's exit code is non-zero, Hard Gate 8 BLOCKS the handover write. The practitioner is shown the literal smoke command, the non-zero exit code, and the captured stderr. Fix the failure or mark the chunk as exempt; do not write the handover with a failing smoke.

   **Carry-over exemption (NFR-1):** Hard Gate 8 reads the chunk's `build/prompts/P{X}-C{XX}.md` mtime and compares it against `_V2_1_0_RELEASE_DATE` declared in the Release Constants section above. If the prompt-file mtime is BEFORE `_V2_1_0_RELEASE_DATE`, the chunk was authored under v2.0.x rules and is exempt from Hard Gate 8 — record the exemption with the literal phrase "v2.0.x carry-over" in the handover and proceed. The mtime check is the audit boundary; pre-release chunks are not retroactively gated.

   **ADR-MH-04 exemption:** chunks whose deliverables are pure internal helpers, test fixtures, or refactors with no user-facing surface change MAY claim exemption by writing the literal line `Hard Gate 8 exempted: <reason>` (with rationale) into the handover under the smoke section. Reviewers can challenge the claim during code review — the rationale is the audit trail. A silent skip with no recorded exemption is a Hard Gate 8 violation regardless of intent.

   **Missing constant:** if `_V2_1_0_RELEASE_DATE` is not declared in this SKILL.md's Release Constants section, Hard Gate 8 refuses with an error naming NFR-1. The constant is mandatory; absence is a SKILL.md authoring bug, not a runtime concern.

9. **MVP-FIRST ORDERING (Hard Gate 9 — MVP-1, where MVP = Minimum Viable Product).** When `/gvm-build` opens an implementation guide, before generating any chunk prompt, verify the first user-facing chunk in the Build Phases section satisfies one of the following:

   (a) the chunk delivers a runnable end-to-end slice — its deliverables include a user-visible interaction (CLI invocation, HTTP route, UI flow) AND its acceptance test exercises that interaction against the walking-skeleton's wired boundaries; OR

   (b) the implementation guide carries the literal marker `MVP-1 exempted: <category> — rationale: <why>` in the Build Phases section header, where `<category>` is one of the four named project shapes (`library`, `refactor`, `performance-driven`, `fully-specified`) and `<why>` is non-empty.

   **Refusal rule:** if neither (a) nor (b) holds — the first user-facing chunk is a layer fragment AND no exemption marker is present — Hard Gate 9 BLOCKS the chunk-prompt generation. The practitioner is shown which chunk was inspected, why it failed (e.g. "first user-facing chunk P1-C03 produces only data-model migrations; no acceptance test exercises a user-visible interaction"), and the four named exemption categories. The fix is either restructure the impl guide so the first user-facing chunk is a thin end-to-end slice, or add the `MVP-1 exempted: ...` marker with a category and rationale. Hard Gate 9 here is the read-side mirror of `/gvm-tech-spec` Phase 5 MVP-1 — both gates compose: tech-spec refuses the impl-guide write; build refuses the impl-guide read. An exemption-with-rationale form passes both gates and survives as the audit trail reviewers can challenge.

   **Exemption format example:**

   ```
   ## Build Phases

   MVP-1 exempted: library — rationale: this project ships a CLI library consumed by other developers; the "first user-facing slice" framing does not apply because the consumer is another build, not an interactive user. Each chunk delivers an importable API surface verified by integration tests against representative consumer scripts.
   ```

   An exemption marker without rationale (or with a category not in the named four) refuses the gate (Fagan: silent skips are not skips). Schema mismatch — neither a runnable first slice nor a properly-formed exemption — is not a silent-pass condition.

Verification: after completing each chunk, confirm all 6 chunk-level gates (1–5 and 8) and the pre-flight bootstrap were satisfied. After completing each phase, confirm Hard Gates 6 and 7 (wiring matrix — both the row-grep audit and the module-audit inverse check). Hard Gate 9 (MVP-1) is verified once, at impl-guide read time, before any chunk prompt is generated. If any were missed, go back and complete them before proceeding to the next chunk or phase.

## Expert Panel

`/gvm-build` loads experts from three tiers per shared rule 17. The roster is chunk-scoped: each chunk's prompt selects the subset relevant to its deliverables. The full table of available experts is in `~/.claude/skills/gvm-design-system/references/`; the entries below describe the role each tier plays during a build. Experts loaded for a chunk are logged to the activation CSV.

| Tier | Source | Loaded for | Role during build |
|---|---|---|---|
| 1 — Architecture | `architecture-specialists.md` | Every chunk | Conceptual integrity (Brooks), risk-driven depth (Fairbanks), C4 system context (Brown), TDD discipline (Beck), code construction (McConnell), formal inspection (Fagan), pragmatic principles (Hunt & Thomas), refactoring (Fowler), clean code (Martin) — applied during the self-review loop, not during construction. |
| 2a — Domain | `domain/*.md` (selective) | Chunks whose spec references a domain (e.g., honesty-triad, walking-skeleton, exploratory testing) | Domain-specific framing — e.g., Adzic for impact mapping, Cagan for discovery, Rumelt for diagnosis. Loaded only for chunks whose spec excerpt names the domain. |
| 3 — Stack | `stack-specialists.md` index → `stack/*.md` | Chunks touching language/framework code | Language idioms, library API correctness, dependency-verification commands. Loaded based on `specs/cross-cutting.md` tech stack and the chunk's actual file list. |

Experts are used *during the self-review loop* (Hard Gate 3) as declarative quality criteria. They are not invoked during code generation — that uses the Framework Reference (procedural knowledge) per Key Rule 23. Experts who find an issue should fix it (shared rule 3); experts discovered for an uncovered domain are documented in the chunk handover (shared rule 2).

## Prerequisites

Before starting any build work, verify:

1. **`specs/implementation-guide.md` must exist.** If it does not, tell the user to run `/gvm-tech-spec` first. Do not proceed without it.
2. **Spec files referenced by chunks must be readable.** For each chunk about to be built, confirm that the spec files and sections referenced in the implementation guide exist in `specs/`. If a referenced spec file is missing, stop and tell the user which file is missing.
3. **Dependency handovers must exist for any chunk with dependencies.** Before generating the prompt for any chunk, check that all dependency handovers exist in `build/handovers/`. If a dependency handover is missing, stop and tell the user: "Chunk [X] depends on [Y] which has not been built yet. Build [Y] first." Do not attempt to build a chunk with missing dependencies.
4. **Load relevant expert sections** from `~/.claude/skills/gvm-design-system/references/` (architecture-specialists.md, stack-specialists.md index, then matching per-stack files from `stack/`) and domain specialist files selectively from `~/.claude/skills/gvm-design-system/references/domain/` before generating chunk prompts. See `domain-specialists.md` index for available domain files and `stack-specialists.md` index for available stack files.
5. **Read `~/.claude/skills/gvm-design-system/references/review-reference.md`** for the Finding Quality Gate -- required before the self-review loop (Gate 3).

## Input

Reads `specs/implementation-guide.md` and `specs/*.md` from the current project. If the implementation guide doesn't exist, tell the user to run `/gvm-tech-spec` first.

**Chunk-to-spec mapping:** The implementation guide must reference specific spec files and sections per chunk (e.g., "Spec: cross-cutting.md, ADR-005" and "Spec: backend-api.md, auth endpoints"). When generating a chunk prompt, resolve these references to actual file paths and extract only the referenced sections. If the implementation guide uses section names rather than filenames, search across `specs/*.md` for the matching section header.

**Spec change detection (hard gate):** Before generating a prompt for any chunk, check whether any spec file referenced by a completed dependency chunk has been modified since that chunk's handover was written. Use `python3 -c "import os; print(int(os.path.getmtime('{file}')))"` for cross-platform timestamp comparison. If a spec has changed: **stop and present the user with options via AskUserQuestion** — "Rebuild affected chunks (re-generate prompts and re-execute)" or "Accept divergence (proceed knowing completed chunks may be inconsistent with the updated spec)." Do not silently proceed — a stale chunk built against an old spec version can produce integration failures that are expensive to debug later.

## Output

- Working code committed to git
- Per-chunk prompts in `build/prompts/P{X}-C{XX}.md`
- Per-chunk handovers in `build/handovers/P{X}-C{XX}.md`

## Release Constants

```
_V2_1_0_RELEASE_DATE = "2026-04-28"
```

This is the v2.1.0 release date — the authority for the NFR-1 carry-over rule. Hard Gate 8 (chunk-acceptance smoke gate, introduced by P25-C01) compares each chunk's `build/prompts/P{X}-C{XX}.md` mtime against this constant. Chunks whose prompt-file mtime is **before** `_V2_1_0_RELEASE_DATE` are exempt from v2.1.0-introduced gates — they were authored under v2.0.x rules and must remain shippable without retroactive enforcement.

Distributed self-versioning: each future major rule release adds its own `_V{MAJOR}_{MINOR}_{PATCH}_RELEASE_DATE` constant in this section. There is no central install-version file — the constant is a literal, grepable declaration co-located with the gates that read it.

## TDD-2 — Mock Budget at the External Boundary

**Rule (mock budget = 1 at the external boundary).** Each test mocks at most one collaborator, and only when that collaborator sits at the external boundary — the network or process edge of the system. Mocking an internal Python class is a TDD-2 violation: the seam the mock pretends to verify is the seam the test is silently bypassing (Metz, *POODR* Ch. 9 — mocks belong at object boundaries; Freeman & Pryce, *GOOS* — internal mocks hide protocol drift).

**Canonical external-boundary allowlist.** This section is the **human-readable specification** of the allowlist — practitioners read it to understand which mocks pass TDD-2. The **runtime authority** is `_PYTHON_STACK_DEFAULTS` in `gvm-design-system/scripts/_ebt_contract_lint.py` plus the project-level `.ebt-boundaries` file (ADR-504 in cross-cutting); the lint does not parse this SKILL.md at runtime. The two SHOULD be kept in sync — when this section's category list changes, the matching change SHOULD also be made in `_PYTHON_STACK_DEFAULTS`. (Surfaced gaps requiring future chunks to close: (1) the original spec promised a SKILL.md regex-parse path so this section would be the single runtime source of truth; P24-C01 implemented hardcoded stack defaults instead. (2) Coverage drift: as of v2.1.0 release, `_PYTHON_STACK_DEFAULTS` mirrors only `requests.*`, `httpx.*`, `psycopg2.*`, `sqlalchemy.engine.*`, `boto3.*` (the last three covered by the third-party SDK rule below); the named categories `urllib`, `aiohttp`, `socket`, `pathlib.Path`, `subprocess`, `os` are NOT in the runtime mirror — practitioners relying on the lint to enforce them today will get false-greens. Treat this section as the specification authority and `_PYTHON_STACK_DEFAULTS` as a partial runtime mirror until both gaps are closed.) The eight named external-boundary categories (plus the third-party SDK rule):

1. `requests` — HTTP transport.
2. `httpx` — async HTTP transport.
3. `urllib` — stdlib HTTP / URL parsing with real I/O.
4. `aiohttp` — async HTTP server / client transport.
5. `socket` — raw TCP/UDP/IP socket I/O.
6. `pathlib.Path` (real I/O — not pure path manipulation) — only the methods that touch disk (`read_text`, `write_text`, `mkdir`, `iterdir`, etc.) count as the external boundary; pure path arithmetic (`/`, `parent`, `name`, `with_suffix`) does NOT.
7. `subprocess` — process-spawn boundary.
8. `os` (env/fs/signal) — `os.environ`, `os.path` real-I/O methods, `os.signal`, etc. Pure constants and pure-arithmetic helpers are not the boundary.

Plus: any **third-party SDK** published outside the project's own codebase counts as an external boundary (e.g. `anthropic`, `openai`, `boto3`, `psycopg2`, `redis`). Internal Python classes — including wrappers around the modules above — are NOT external boundaries.

**Wrapper-as-SUT exemption (ADR-MH-02).** When the test's class under test IS the wrapper around an external module, mocking the external module is correct — the wrapper is the SUT, the external module is the boundary. The lint identifies the wrapper-as-SUT case by checking whether the test file's class under test (inferred from the test filename, e.g. `test_HttpxClient.py` → `HttpxClient`, or from the test's `import` statements) matches the patch target's parent class. Without this exemption a legitimate wrapper unit test would surface a false-positive TDD-2 violation; with it, only mocks of internal collaborators (non-wrapper, non-external) trigger the budget violation.

**Severity escalation rule (ADR-MH-03).** Default severity for a `mock-budget` violation is **Important** (the practitioner judges). If the mock target appears in the project's `.cross-chunk-seams` allowlist file at the project root, severity escalates to **Critical** — the seam list names the cross-chunk protocols whose drift would break production wiring (Freeman & Pryce protocol-drift defect class). The `.cross-chunk-seams` file is opt-in: when it is absent, escalation does not fire and severity stays Important. The opt-in default is the migration path — projects pay zero cost until they adopt the seam list.

## TDD-3 — Realistic-Fixture Catalogue

**Rule (realistic-fixture mandate).** Every chunk's test suite MUST include at least one fixture variant that does not fit the engineer's happy-path mental model. The realistic-fixture variant exists to catch what the engineer's mental model missed, not to confirm what they already believed (Bach & Bolton, *Rapid Software Testing* — synthetic fixtures encode the engineer's mental model; the real input space is bigger). The variant is a SEPARATE test deliverable alongside the synthetic happy-path test, not an acceptance criterion bolted onto it.

**Per-domain catalogue (six named domains).** This section is the canonical specification of the realistic-fixture starter shapes per domain. `/gvm-code-review` Panel C (P26-C03) reads this catalogue and emits an Important finding when a chunk in a known-edge-shape domain ships without a realistic-fixture variant. Practitioners extend per project — the catalogue is a starting point, not a closed set.

1. **Data analysis** — short categorical codes (sex M/F, blood type A/B/O, yes/no Y/N, grade A/B/C/D/F), all-null columns, single-row datasets, identical baseline-vs-actual, no shared columns, all-zero variance columns.
2. **Web/UI** — large request payloads, browser-back navigation mid-form, Unicode in inputs, slow network simulation.
3. **API** — missing required headers, malformed JSON bodies, Unicode in identifiers, very long arrays, integer overflow in numeric fields.
4. **Parsing** — malformed inputs, mixed encodings (UTF-8 BOM, Latin-1), trailing whitespace, very long fields.
5. **Security validation** — escape characters, length-edges (0-byte, just-under-max), Unicode normalization attacks, percent-encoding edge cases.
6. **Concurrency** — race conditions, partial failures, timeout-mid-write, retry-after-success duplication.

**Practitioner-extension clause.** Domains not enumerated above use practitioner judgement plus the principle ("data shapes the engineer didn't anticipate"). Future v2.x releases may extend the catalogue based on field reports. A chunk in a non-catalogued domain is NOT exempt from the rule — it must still ship a realistic-fixture variant; the practitioner names the shape, citing the principle as rationale.

**Defect-class evidence.** The catalogue is grounded in observed defects, not speculation:
- **Defect S6.1** — single-letter category codes (A/B/C) tripped the privacy scan because the synthetic fixture used long descriptive labels. The data-analysis row's short-categorical-codes case (sex M/F, blood type A/B/O) is the direct counter-shape.
- **Defect 3a** — clean ordinal data produced empty headlines because the synthetic fixture always contained outliers. The data-analysis row's all-zero-variance and identical-baseline-vs-actual cases are the direct counter-shapes.

The defect-class entries are the audit trail: if a future practitioner asks "why these shapes and not others", the answer is "these shapes have historically shipped to production undetected by happy-path tests".

**Practitioner override (forward pointer).** A chunk can claim exemption from Panel C's realistic-fixture finding by tagging the chunk handover with `realistic-fixture-not-applicable: <rationale>` (e.g. `pure config refactor` / `internal data structure with no input boundary`). The override is enforced by Panel C in `/gvm-code-review` (P26-C03), not by `/gvm-build`. Silent skip with no recorded tag is a TDD-3 violation.

## Process Flow

```
1. DETECT STATE
   ├── Read specs/implementation-guide.md
   ├── Count total chunks in the implementation guide
   ├── SIMPLE BUILD CHECK: if the guide has a single chunk with no dependencies,
   │   skip the dependency matrix, parallel dispatch, and phase-level integration.
   │   Still generate a prompt and handover — the basic mechanism is always worth it.
   │   **The pre-flight bootstrap and all Hard Gates (1–5) apply on this path** — simple
   │   build skips dependency management and parallel dispatch, not execution discipline.
   │   Grounding material (Gate 1), prompt file (Gate 2), self-review loop (Gate 3),
   │   handover file (Gate 4), and test-first (Gate 5) are all mandatory regardless of
   │   build complexity.
   │   **Model selection:** follows shared rule 22 — see step 5 (EXECUTE CHUNK) for the decision table.
   │   Proceed to the COMPACT CHECK below, then to step 3 (GENERATE PROMPT). The simple
   │   build check skips dependency matrix and parallel dispatch — it does NOT skip the
   │   compact recommendation.
   ├── Scan build/handovers/ for completed chunk handovers
   ├── Scan build/prompts/ for generated but unexecuted prompts
   ├── Build progress map: which chunks are done, partial, or pending
   └── COMPACT CHECK:
       ├── If `build/handovers/` contains any completed chunk files (i.e.,
       │   this is a resumption, not the first chunk of a new build), recommend `/compact`
       │   before proceeding. If the user compacts, re-detect state on resumption.
       └── CONTEXT BUDGET: after each chunk completes, estimate cumulative context consumed
           in this session (prompt tokens + code written + review output + handover).
           Rough estimate: count the chunks completed in this session.
           - After 2 chunks: recommend `/compact` via AskUserQuestion
           - After 3 chunks: strongly recommend — "context is heavy, quality may degrade"
           - After 4 chunks without compacting: make it mandatory — run `/compact` before
             proceeding to the next chunk. Code generation fills context faster than
             other pipeline phases. Better to compact too early than to degrade quality.

2. PRESENT OPTIONS (via AskUserQuestion)
   ├── "Build next chunk (P{X}-C{XX})" — first unbuilt chunk on the critical path
   ├── "Build specific chunk" — user picks from pending chunks
   ├── "Build all of Phase N" — sequential execution of all chunks in a phase
   ├── "Parallel dispatch" — offered when multiple chunks share no dependencies
   └── "Resume partial chunk" — if a chunk was started but not handed over

3. GIT STRATEGY (via AskUserQuestion, per chunk)
   ├── "Current branch" — default for sequential, small/medium chunks
   ├── "Feature branch" — recommended for large chunks or PR-based review
   └── "Git worktree" — auto-recommended for parallel dispatch

4. GENERATE PROMPT
   ├── GUARD: Check that all dependency handovers exist in build/handovers/
   │   └── If a dependency handover is missing → stop and tell the user:
   │       "Chunk [X] depends on [Y] which has not been built yet. Build [Y] first."
   │       Do not attempt to build a chunk with missing dependencies.
   ├── SPEC CHANGE GUARD: For each completed dependency chunk, compare the modification
   │   time of its referenced spec files against the handover's write time. If any spec
   │   is newer than the handover → stop and present options via AskUserQuestion:
   │   "Rebuild affected chunks" or "Accept divergence." Do not silently proceed.
   ├── Read the chunk description from implementation-guide.md
   ├── Read the referenced spec section(s) from specs/*.md
   ├── Read cross-cutting conventions (conventions section only)
   ├── Read handovers of dependency chunks (what they actually built)
   ├── Load relevant expert sections from `~/.claude/skills/gvm-design-system/references/` (architecture, domain, stack specialists) — these go into the Review Criteria section of the prompt
   ├── Load framework documentation relevant to this chunk's deliverables:
   │   ├── Identify language, framework, and libraries from specs/cross-cutting.md tech stack
   │   ├── For well-known frameworks: reference specific API sections this chunk will use
   │   ├── For newer libraries or internal APIs: load actual documentation into the prompt
   │   └── Include in the prompt under "## Framework Reference"
   ├── Load build checks: if `reviews/build-checks.md` exists, read Active Checks section.
   │   Filter to checks relevant to this chunk by review type (code checks → all code chunks,
   │   design checks → architecture-touching chunks, doc checks → documentation-generating chunks).
   │   If the file does not exist, skip — no checks are loaded.
   ├── Log all loaded experts to activation CSV (per shared rule 1)
   ├── **WRITE** the prompt to `build/prompts/P{X}-C{XX}.md` using the Write tool — this file MUST exist before step 5 begins.
   └── Present prompt summary to user for approval

5. EXECUTE CHUNK (strict TDD + review loop)
   ├── **Chunk subagent model (per shared rule 22):** For builds with ≤2 chunks and no cross-chunk dependencies, dispatch with `model: sonnet`. For builds with 3+ chunks or any cross-chunk dependencies, use the primary model. The prompt content is identical — only the model changes.
   ├── TEST RUNNER SETUP (first chunk only, if test runner not yet configured):
   │   ├── Install test framework (pytest/vitest) and configure runner
   │   ├── Verify runner works with a trivial passing test
   │   └── Commit: "chore: configure test framework [P1-C01]"
   ├── DEPENDENCY CHECK:
   │   ├── Run test suites for all dependency chunks (confirms environment + prior work)
   │   └── If any dependency tests fail → stop, report which dependency is broken
   ├── WS-5 SKELETON STATUS GATE (red skeleton refusal — walking-skeleton ADR-406):
   │   │   This gate enforces WS-5: a red walking skeleton blocks new chunks.
   │   │   No-op for projects that have not adopted /gvm-walking-skeleton — the
   │   │   gate keys off `walking-skeleton/.first-run.log`, which only exists
   │   │   after the skill has run. Projects without it skip the gate.
   │   ├── If `walking-skeleton/.first-run.log` does not exist → skip this
   │   │   gate entirely (project has not adopted /gvm-walking-skeleton).
   │   ├── Otherwise: from `gvm-build/scripts/_skeleton_status.py`, call
   │   │   `query_skeleton_status(repo_root)`. The module:
   │   │   ├── Detects the CI provider via `_ci_writer.detect_provider`
   │   │   ├── For GitHub Actions: runs `gh pr checks` (no `--watch` flag)
   │   │   ├── For GitLab: runs `glab ci status` (the canonical subcommand;
   │   │   │   the walking-skeleton spec's earlier `glab pipeline status` is
   │   │   │   not a real glab subcommand — see P11-C05 handover)
   │   │   ├── For CircleCI / generic / no CLI / missing-PR: returns
   │   │   │   `method="needs_manual"`, `result="unknown"`
   │   │   └── Returns a `SkeletonStatus(method, result, timestamp, ci_provider)`
   │   ├── If `status.method == "needs_manual"`: emit AskUserQuestion:
   │   │   "Walking-skeleton CI status unavailable. Run `make walking-skeleton`
   │   │   locally now and confirm the result."
   │   │   Options: "PASSED — proceed with chunk", "FAILED — fix integration
   │   │   first". Build a manual SkeletonStatus from the answer via
   │   │   `make_manual_status(result="passed"|"failed", ci_provider=
   │   │   status.ci_provider)`. (R24 I-4: there is no "Cancel" option —
   │   │   `make_manual_status` rejects any value outside `_VALID_RESULTS`
   │   │   = {passed, failed, unknown}; use the AskUserQuestion dismiss
   │   │   path for cancellation, which halts the build without writing a
   │   │   sidecar and without proceeding to the TDD loop.)
   │   ├── If `is_blocking(status)` (i.e. `result == "failed"`): refuse the
   │   │   chunk with `WS5_REFUSAL_MESSAGE`
   │   │   ("Walking skeleton is red — fix integration before continuing
   │   │   (WS-5). Run skeleton locally: `make walking-skeleton`"). Do not
   │   │   proceed to the TDD loop. Tell the practitioner to fix the red
   │   │   skeleton and re-invoke `/gvm-build`.
   │   └── Always: write the chunk-scoped sidecar via
   │       `write_status_sidecar(Path("build/handovers/P{X}-C{XX}.md"), status)`.
   │       The sidecar (`P{X}-C{XX}.skeleton-status.json`) is the audit trail
   │       `/gvm-test` reads when auditing WS-5 honour-system gates — cap
   │       the verdict at Demo-ready when manual gates were used without
   │       later CI re-confirmation (resolves R3 I-R3-28).
   │
   │   **WS-5 runtime trace (R24 I-5).** Three end-to-end paths through
   │   the gate; each writes the sidecar before the gate decision is
   │   acted on, so the audit trail exists regardless of outcome.
   │
   │   1. **CI says PASSED.** `query_skeleton_status` runs `gh pr checks`
   │      (or `glab ci status`) → parses `walking-skeleton  passed` →
   │      returns `SkeletonStatus(method="ci", result="passed")`.
   │      Sidecar written. `is_blocking → False`. Proceed to TDD loop.
   │   2. **CI says FAILED.** Same query path → parser returns
   │      `result="failed"` → `SkeletonStatus(method="ci", result="failed")`.
   │      Sidecar written. `is_blocking → True`. Refuse with
   │      `WS5_REFUSAL_MESSAGE`. Do not write any chunk code.
   │   3. **Manual fallback.** No CLI / no PR / in-progress run /
   │      CircleCI / generic — `query_skeleton_status` returns
   │      `method="needs_manual"`. Skill emits AskUserQuestion. On
   │      "PASSED": `make_manual_status(result="passed")` → sidecar
   │      written → proceed. On "FAILED": `make_manual_status(result=
   │      "failed")` → sidecar written → refuse. On AskUserQuestion
   │      dismiss: skill halts; no sidecar; no chunk progress.
   ├── For each deliverable in the chunk:
   │   a. Write failing test (use Framework Reference for correct API usage).
   │      If the test cases document tags this requirement with `[PROPERTY]`, also write
   │      a property-based test using the stack's property testing library (see
   │      `~/.claude/skills/gvm-design-system/references/stack-tooling.md` Property-Based Testing section). The property test asserts the
   │      invariant from the test case spec; the example-based test covers the specific scenario.
   │   b. Write minimal code to pass (use Framework Reference, not expert principles)
   │   c. Run per-deliverable test via the Bash tool → **VERIFY** the Bash tool reports
   │   │   success (exit code 0). Do not rely on reading the test output text to determine
   │   │   pass/fail — the exit code from the tool result is the source of truth.
   │   │   If the tool reports failure, the test failed regardless of what the output says.
   │   d. **SELF-REVIEW LOOP (mandatory — do not skip — this is Hard Gate 3):**
   │   │   ├── Review working code against Review Criteria (expert principles — declarative quality)
   │   │   ├── Review against active build checks from reviews/build-checks.md (if any were loaded)
   │   │   ├── Apply the Finding Quality Gate from review-reference.md — only report findings that pass the consumer impact test; discard polish
   │   │   ├── **DEFECT-CLASS CHECKLIST (Fagan: author preparation against inspection criteria):**
   │   │   │   Scan the deliverable against each defect class that `/gvm-code-review` will later inspect.
   │   │   │   Catching these now prevents them from reaching the formal inspection.
   │   │   │   ├── **References:** Does every import, path, and cross-reference resolve to an existing target?
   │   │   │   ├── **Contracts:** Does every function signature match its callers? Do types align at boundaries?
   │   │   │   ├── **Completeness:** Does every conditional have an else? Do error paths return meaningful errors?
   │   │   │   └── **Naming:** Is every concept named consistently with the spec and other files?
   │   │   ├── Fix any issues found (defect-class or expert-principle)
   │   │   ├── Re-test after fixes (tests must still pass)
   │   │   ├── Repeat until clean (no cap as long as issue count is decreasing; stop and flag to user if not converging after 5 iterations)
   │   │   └── Record findings and fixes for the handover (if no findings were recorded, the loop did not run)
   │   e. Refactor if needed → re-review → re-test
   │   f. Continue to step "INDEPENDENT REVIEW CONVERGENCE LOOP" below before committing.
   │      The user checkpoint fires AFTER convergence, not after the first pass —
   │      a single pass with findings is the EXPECTED first state, not the
   │      terminal state. Committing after one pass shortcuts the discipline.
   ├── DEPENDENCY VERIFICATION (after all deliverables, before lint):
   │   ├── Read `~/.claude/skills/gvm-design-system/references/stack-tooling.md` and find the project's stack
   │   ├── Run the **Dependency Verification** command for each NEW import/require in this chunk
   │   ├── If the project's stack is not listed: run the **Discovery Process** at the bottom of
   │   │   `~/.claude/skills/gvm-design-system/references/stack-tooling.md` to identify and add the correct verification command
   │   ├── If any verification fails: the package may be hallucinated.
   │   │   Stop and flag to user before proceeding.
   │   └── This is a hard check, not guidance. A failing import blocks the chunk.
   ├── LINT & FORMAT:
   │   ├── Run the **Lint & Format** commands from `~/.claude/skills/gvm-design-system/references/stack-tooling.md` for the project's stack
   │   ├── If the project's stack is not listed: run the Discovery Process to identify tools
   │   ├── If linter finds issues not caught by review → fix and re-commit
   │   └── Commit: "style: lint and format [P{X}-C{XX}]" (only if changes)
   ├── CREDENTIAL SCANNING (after lint, before static analysis):
   │   ├── Run the **Credential Scanning** command from `~/.claude/skills/gvm-design-system/references/stack-tooling.md` on chunk files
   │   ├── If any secrets, API keys, passwords, or tokens are detected: remove them immediately
   │   │   and replace with environment variable references or config file lookups
   │   ├── This is a hard block — do not proceed with hardcoded credentials in committed code
   │   └── Commit credential fixes: "fix: remove hardcoded credentials [P{X}-C{XX}]"
   ├── STATIC ANALYSIS (after credential scanning, before independent review):
   │   ├── Run the **Static Analysis** commands from `~/.claude/skills/gvm-design-system/references/stack-tooling.md` for the project's stack
   │   │   (security, complexity, and any general analysis commands listed)
   │   ├── If the project's stack is not listed: run the Discovery Process to identify tools
   │   ├── If security findings with severity HIGH or CRITICAL: fix before proceeding
   │   ├── If complexity exceeds threshold: flag to user — may indicate a function that should be split
   │   ├── If tools are not installed: use the install command from `~/.claude/skills/gvm-design-system/references/stack-tooling.md`.
   │   │   If installation fails (permissions, network), note in handover and proceed
   │   └── Commit security fixes: "fix: address static analysis findings [P{X}-C{XX}]"
   ├── INDEPENDENT REVIEW CONVERGENCE LOOP (mandatory — Hard Gate 3 enforcement):
   │   │   This is an EXPLICIT PASS-COUNTED LOOP. "Repeat until clean" is not an
   │   │   aspiration; it is a tool-dispatch loop with a terminating condition.
   │   │   The loop only exits on a pass that returns zero Critical/Important
   │   │   findings. A single pass with findings is the START of the loop, not
   │   │   the end of it.
   │   │
   │   │   Initialise: pass_number = 1, last_findings = "unknown"
   │   │   pass_log = []  ← ordered list of (pass_number, findings_count) tuples
   │   │
   │   │   LOOP:
   │   │   ├── Dispatch a review agent via the Agent tool (model: sonnet) with:
   │   │   │   ├── The list of files created/modified in this chunk
   │   │   │   ├── The Review Criteria from the prompt (expert principles + build checks)
   │   │   │   ├── The spec excerpt this chunk was built from
   │   │   │   ├── A note saying "This is review pass {pass_number}. Prior passes
   │   │   │   │   found and fixed: {summary of last_findings}. Verify those fixes
   │   │   │   │   are correct AND look for new issues a fresh reviewer would catch."
   │   │   │   └── Instruction: "Review this chunk for quality, correctness, and
   │   │   │       spec adherence. Apply the Finding Quality Gate: only report a
   │   │   │       finding if you can complete the sentence 'A consumer of this
   │   │   │       code would [concrete failure].' Discard observations that fail
   │   │   │       this test. Return findings as: Severity, File:Line, Issue,
   │   │   │       Fix. If no Critical or Important findings, say so explicitly.
   │   │   │       Do NOT write files."
   │   │   ├── pass_log.append((pass_number, count_of_critical_or_important_findings))
   │   │   ├── If 0 Critical/Important findings → EXIT LOOP (converged)
   │   │   ├── If pass_number == 5 AND findings_count not decreasing → STOP and
   │   │   │   flag to user; do not proceed to commit
   │   │   ├── Otherwise: fix all Critical/Important findings using the same
   │   │   │   expert framework that surfaced them (rule 19), re-test, then:
   │   │   │   pass_number += 1; last_findings = the findings just fixed; LOOP
   │   │
   │   ├── pass_log MUST contain at least 2 entries to record convergence —
   │   │   pass-1 with N findings, pass-N+1 with 0 findings. A pass_log of
   │   │   length 1 is only valid when pass-1 itself returned 0 findings.
   │   │
   │   ├── On convergence, present the REVIEW CHECKPOINT to the user via
   │   │   AskUserQuestion BEFORE committing:
   │   │   ├── Present: "Independent review converged after {pass_number} pass(es). pass_log: {[(1, N1), (2, N2), ..., (final, 0)]}. {total} findings found and fixed across all passes. Tests passing."
   │   │   ├── List the findings and fixes per pass (summary, not full detail)
   │   │   ├── Options: "Approve and commit" / "I want to review the code first" / "Run another review pass anyway"
   │   │   └── Do not commit until the user approves.
   │   │
   │   └── Record the full pass_log in the handover's "Code Review Findings"
   │       section. The handover MUST include a "Review passes:" subfield with
   │       the per-pass count tuples. A handover that lists only one pass with
   │       non-zero findings is structurally invalid — Gate 4 (write handover)
   │       rejects it. The convergence record is the audit trail; without it,
   │       Hard Gate 3 has no verifiable trace.
   ├── Run chunk-level test suite (all tests in this chunk — after independent review)
   │   └── **VERIFY** test results: run via the Bash tool and check the tool's reported
   │       exit code (0 = pass, non-zero = fail). Then parse the test runner output for
   │       pass/fail counts (e.g., `pytest` → "N passed", `vitest` → "N tests passed").
   │       Record both the exit code and the parsed count in the handover.
   │       If exit code ≠ 0 or parsed count doesn't match expected: treat as failure.
   ├── INTEGRATION SEAM CHECK (after chunk tests pass, if this chunk has dependencies):
   │   ├── For each dependency this chunk consumes:
   │   │   ├── Identify the interface contract (API endpoint, function signature, data shape)
   │   │   │   from the spec excerpt and the dependency's handover
   │   │   ├── Write a lightweight integration test that calls across the seam:
   │   │   │   e.g., import the dependency's module and call with a realistic input,
   │   │   │   or hit the API endpoint and verify the response shape matches the spec contract
   │   │   └── Run via Bash tool, verify exit code 0
   │   ├── This catches: wrong import paths, mismatched function signatures, API response
   │   │   shapes that diverged from spec, missing exports, type mismatches at boundaries
   │   ├── If any seam test fails: flag to user — the interface between chunks is broken.
   │   │   This is cheaper to fix now than after the entire phase completes.
   │   ├── ADAPTER PROTOCOL CONTRACT TEST (when this chunk produces an adapter that is
   │   │   consumed via duck typing — i.e. no formal `Protocol` / ABC enforced by the
   │   │   type system). A duck-typed adapter's contract exists only in its consumers'
   │   │   call sites; Python will not catch a missing method, wrong signature, or
   │   │   wrong return shape until the code actually runs. Write TWO parametrised
   │   │   tests:
   │   │
   │   │   **Signature contract** — for each method the consumer calls, assert:
   │   │     (a) the adapter class has that method
   │   │     (b) the method is async if the consumer awaits it
   │   │     (c) the method's positional parameter names match the consumer's call
   │   │   Example name: `test_<adapter>_satisfies_<consumer>_protocol`.
   │   │
   │   │   **Return-shape contract** — signature alone is not enough. When the
   │   │   consumer reads specific keys out of the returned dict (e.g.
   │   │   `parking_data.get("monthly_cost", 0)`), the adapter must return a dict
   │   │   with those exact keys. Wrong keys produce silent "always zero" results
   │   │   or `NoneType` arithmetic errors downstream, not loud failures. Write a
   │   │   second test that:
   │   │     (a) instantiates the adapter with mocked external deps
   │   │     (b) calls each method with realistic args
   │   │     (c) asserts the returned dict contains every key the consumer reads
   │   │     (d) asserts values the consumer does arithmetic on are numeric (not
   │   │         None)
   │   │   Grep the consumer's source for `<obj>.get("<key>"` and `<obj>["<key>"]`
   │   │   patterns to enumerate expected keys. Example name:
   │   │   `test_<adapter>_return_shapes_match_<consumer>_reads`.
   │   │
   │   │   Both tests must exist. Signature-only contract tests can catch
   │   │   transport method-name drift but miss transport return-key drift —
   │   │   the adapter's method signatures look fine while the returned dict
   │   │   uses one key (e.g. `monthly_tolls`) where the consumer reads
   │   │   another (e.g. `total`). Return-shape mismatches ship silently
   │   │   behind passing signature tests.
   │   └── If no dependencies: skip this step
   └── ON FAILURE (tests fail after 2 attempts):
       ├── Do NOT auto-rollback — the fix may be small
       ├── Present the failing test output clearly
       ├── Offer: "Fix it now" / "Stash and come back later" / "Show diff so far"
       │       "Fix it now" — fix the issue, then return to step 5e (Run test → verify it passes)
       │       and continue the TDD loop.
       │       "Stash and come back later" — run `git stash push -m 'P{X}-C{XX} in progress'`.
       │       Write a partial handover to `build/handovers/P{X}-C{XX}-partial.md` with fields:
       │       Status: Partial, Failing tests (list), Stash ref, Files changed.
       │       The next session detects partial handovers as 'started, not complete' chunks.
       │       When the session resumes and the partial chunk is retried, all Hard Gates (1–5)
       │       apply from the point of continuation. The self-review loop (Gate 3) runs on the
       │       completed deliverables after the failing test is fixed. Gate 4 (Write Handover)
       │       replaces the partial handover file.
       │       Gate 1 (load grounding material) must be re-executed at resumption — the prior
       │       session's context is gone. Gate 2 (prompt file) already exists and need not be
       │       regenerated unless the spec changed.
       └── Never auto-reset or discard work

6. WRITE HANDOVER
   ├── HS-1 GATE (honesty-triad ADR-101 — applies whenever the project has a
   │   `STUBS.md`, i.e. honesty-triad is active). Runs immediately before the
   │   handover is written. Cannot be bypassed without lying in the handover
   │   template's "Files Created" / "Files Modified" sections.
   │   ├── Assemble the explicit file list from the handover template's
   │   │   "Files Created" + "Files Modified" sections. Do NOT call `git`
   │   │   and do NOT walk the working tree — the file list is the list you
   │   │   are about to write into the handover, nothing else.
   │   ├── Resolve `stubs_path` to the project's `STUBS.md` (typically the
   │   │   project root). A missing `STUBS.md` is acceptable input — the
   │   │   gate treats it as an empty registry, so any stub-namespaced file
   │   │   in the chunk's file list will surface as unregistered.
   │   ├── Call `_hs1_check.check(files, stubs_path)` from
   │   │   `gvm-build/scripts/_hs1_check.py`. The function returns a list of
   │   │   `UnregisteredStubError(path=...)` records — empty list = pass.
   │   └── If non-empty: REFUSE the handover. Print one error line per
   │       offending path naming the unregistered stub. Tell the user to
   │       register each path in `STUBS.md` (with reason, real-provider plan,
   │       owner, and ISO-8601 expiry per cross-cutting ADR-004) before
   │       re-running the handover step. DO NOT write the handover file.
   ├── HS-6 RETROACTIVE AUDIT (forward pointer). The HS-1 gate above only
   │   catches stubs introduced by the current chunk. Pre-existing legacy
   │   stubs are caught by the HS-6 retroactive audit hook in
   │   `/gvm-explore-test` (the exploratory-testing skill — distinct from
   │   `/gvm-test`; introduced in Phase 11 — see honesty-triad domain spec,
   │   requirement HS-6; build delivers in P11-C11). When that hook is wired, `/gvm-build`
   │   does NOT run a retroactive sweep itself — it only enforces the
   │   chunk-handover gate. The retroactive audit is owned by exploratory.
   ├── Save build/handovers/P{X}-C{XX}.md
   └── Update project memory with progress

7. PHASE COMPLETION (after all chunks in a phase)
   ├── Run full phase test suite (all tests across all chunks in the phase)
   ├── Flag any cross-chunk integration failures
   └── Present phase summary

8. BUILD SUMMARY
   ├── 8a. BETWEEN PHASES (optional): offer via AskUserQuestion — "Would you like a build
   │   summary?" For multi-session builds, captures progress before compacting.
   ├── 8b. AFTER FINAL PHASE (mandatory): write the build summary. This is not optional
   │   after the last phase completes.
   ├── Before dispatching, use the Read tool to load `~/.claude/skills/gvm-design-system/references/tufte-html-reference.md`. Pass its CSS content to the subagent — not just a reference to "the Tufte CSS shell".
   ├── **HTML generation:** Dispatch the HTML build summary generation as a Haiku subagent (`model: haiku`). The subagent receives the `build-summary.md` content AND the loaded Tufte CSS. Per shared rule 22.
   ├── Write paired HTML + MD to `build/build-summary.html` and `build/build-summary.md`
   ├── Contents:
   │   ├── WHAT WAS BUILT
   │   │   ├── Completed chunks: P-C ID, name, commit SHA, test count
   │   │   ├── Files created/modified per chunk (from handovers)
   │   │   ├── Total: X chunks complete, Y tests passing, Z commits
   │   │   └── NFR-2 diff-budget aggregation: read each handover's
   │   │       `Diff budget delta` field and sum the per-chunk values
   │   │       into a cumulative SKILL.md net-added LOC total. If the
   │   │       cumulative crosses 500, present an `AskUserQuestion` per
   │   │       cross-cutting ADR-CC-03 (the diff-budget is documentation,
   │   │       not a gate — surface-and-track, not refuse). Options:
   │   │       "Defer remaining chunks to v2.1.x" / "Proceed with explicit
   │   │       deferral rationale recorded in the build summary".
   │   ├── WHAT WAS NOT BUILT
   │   │   ├── Remaining chunks: P-C ID, name, dependencies, status (pending/partial/blocked)
   │   │   ├── Blocked chunks: which dependency is missing
   │   │   └── Partial chunks: what failed, stash ref if applicable
   │   ├── OPEN QUESTIONS & SURFACED REQUIREMENTS
   │   │   ├── Scan all handovers for "Surfaced Requirements" entries — collect into one list
   │   │   ├── Scan all handovers for "Deviations from Spec" entries — collect non-"None" items
   │   │   ├── Scan all handovers for "Upstream Fixes" entries — collect non-"None" items
   │   │   ├── For each, note: which chunk surfaced it, recommended action, status (open/addressed)
   │   │   ├── If no surfaced requirements are in "open" status: skip TRIAGE — proceed to the next subsection.
   │   │   ├── PRECONDITION: verify `requirements/requirements.md` exists. If it does not,
   │   │   │   present only the third option below and note the missing source-of-truth file.
   │   │   ├── For each surfaced requirement still in "open" status, run TRIAGE per shared rule 27:
   │   │   │   present via AskUserQuestion with three options:
   │   │   │   ├── "Append as acceptance criterion to an existing requirement" (with changelog entry per rule 11)
   │   │   │   ├── "Add a new requirement entry" (with changelog entry per rule 11)
   │   │   │   └── "Create a new requirements document (next round)" — run `/gvm-requirements` in "New round" mode
   │   │   ├── If the user dismisses the question or selects no option for a surfaced requirement,
   │   │   │   record it as `deferred — awaiting triage` in the build summary and re-prompt at the
   │   │   │   next natural checkpoint (next `/gvm-build` invocation or `/gvm-status`). Do NOT silently park it.
   │   │   ├── Record the chosen option per surfaced requirement in the build summary; mark as "promoted" once `requirements/requirements.md` is updated
   │   │   ├── DO NOT park surfaced requirements in `STUBS.md`. `STUBS.md` is for code-level placeholders only — no `STUB-SR-NN` IDs, no `## Surfaced Requirements` section
   │   │   └── Flag any items still needing `/gvm-requirements` to formalise (a triaged surfaced requirement that the user deferred)
   │   └── EXPERT PANEL ACTIVATION SUMMARY
   │       ├── Which experts were loaded during this build and for which chunks
   │       ├── Group by tier: Tier 1 (architecture — active for all chunks), Tier 2a (domain — which
   │       │   domains activated and for which chunks), Tier 3 (stack — which technologies)
   │       ├── Which experts were cited in self-review loops (not just loaded but actually applied)
   │       ├── Any experts discovered during the build (per shared rule 2)
   │       └── Coverage assessment: were there chunks where no domain or stack expert was available?
   │           If so, flag as a gap for the user.
   ├── Log cited experts to activation CSV (per shared rule 1)
   └── Present summary to user

9. OFFER NEXT STEP (between phases)
   ├── "Build next chunk" → back to step 2
   ├── "Compact first" → mandatory if 4+ chunks completed this session without compacting
   └── "Done for now" → session ends, progress persisted in handovers + build summary

10. HAND OFF TO /gvm-code-review
    ├── Write the final build summary (step 8 — mandatory at this point), then tell the user:
    │   "All build chunks are complete. Run /gvm-code-review for a full codebase review,
    │    then /gvm-test to verify the build works as a product."
    └── /gvm-code-review reviews the entire codebase; /gvm-test then verifies integration,
        smoke-tests the user flow, and audits stubs.
```

## Prompt Format

Pre-build prompts are generated and saved to `build/prompts/P{X}-C{XX}.md`. Each prompt is self-contained — everything a fresh agent needs to execute the chunk.

```markdown
# Build Prompt: P{X}-C{XX} — {Chunk Name}

## Chunk Summary
{Brief description from implementation guide}

## Expert Panel

| Expert | Work | Role in This Chunk |
|--------|------|--------------------|

(Populated from activation CSV — list experts loaded for this chunk per shared rule 17)

## Git Strategy
{Current branch / Feature branch / Worktree — chosen at runtime}

## Dependencies (completed chunks)
{For each dependency chunk: ID, what it built, key files created}
{Sourced from dependency chunk handovers}

## Deliverables
{List of files to create/modify, sourced from implementation guide}
{Includes both code files and test files}

## Spec Excerpt
{Relevant sections from specs/*.md — only what this chunk needs}
{Cross-cutting conventions excerpt}

## API Boundary Contracts (if this chunk produces or consumes an API)
{Exact response shapes from the spec — field names, types, nesting, JSON example}
{Both backend and frontend chunks reference the SAME contract from the spec}
{If no contract exists in the spec for an endpoint this chunk needs, flag it to the user}

## Framework Reference
{Language documentation relevant to this chunk (e.g., Python 3.12 docs, TypeScript 5.x handbook)}
{Framework API sections relevant to this chunk's deliverables (e.g., Django REST serializers, React hooks API)}
{Library-specific method signatures for any library this chunk imports}
{For libraries released after the AI's training cutoff or internal/proprietary APIs: include actual documentation excerpts}
{For well-known frameworks: reference the specific API sections the chunk will use}

## TDD Approach

**For user-facing chunks (CLI tools, web products, anything Hard Gate 8 will smoke-test):** the outside-in acceptance test is the **first deliverable** — written before any unit test (TDD-1). The acceptance test specifies the user-facing behaviour the chunk delivers; unit tests fall out from its failures (Freeman & Pryce, GOOS). The acceptance test MUST transition Red → Green during the chunk; both commit SHAs go in the handover.

**For pure-internal-helper chunks (`_shared/` refactors, test fixtures, no user-facing surface change):** the acceptance-test-first ordering is exempt under ADR-MH-04. Record the literal line `TDD-1 exempted: <reason>` in the handover. Silent skip with no exemption marker is a TDD-1 violation.

**Realistic-fixture variant (TDD-3).** In addition to the synthetic-fixture happy-path test, every chunk MUST list a SEPARATE **realistic-fixture variant** test as its own deliverable — named distinctly from the happy-path test (e.g. `test_compute_with_short_categorical_codes` alongside `test_compute_happy_path`). The realistic-fixture variant draws from the per-domain catalogue in the `## TDD-3 — Realistic-Fixture Catalogue` section above. A single test deliverable that conflates synthetic happy-path and realistic-fixture coverage is a TDD-3 violation. Chunks in domains absent from the catalogue still owe a realistic-fixture variant — name the shape per the practitioner-extension clause. Pure-internal-helper chunks may claim exemption via the `realistic-fixture-not-applicable: <rationale>` tag in the handover (Panel C in `/gvm-code-review` enforces).

Ordering for user-facing chunks:

1. **Write the failing outside-in acceptance test (FIRST deliverable; first listed test).** It specifies the user-facing behaviour end-to-end.
2. Run the acceptance test → confirm Red. Capture the **Red commit SHA** for the handover.
3. For each unit-level deliverable that the acceptance test now demands:
   a. Write failing unit test
   b. Write minimal code to pass — use the Framework Reference above for correct API usage
   c. Run unit test → confirm pass (per-deliverable tests are fast; run before review)
   d. Review against Review Criteria below (fix until clean)
   e. Refactor if needed → re-review
4. Run the acceptance test → confirm Green. Capture the **Green commit SHA** for the handover.
5. Commit with message: "{type}: {description} [P{X}-C{XX}]"

## Review Criteria (for Self-Review Loop — not construction)
{Expert principles loaded from architecture-specialists.md, domain/*.md (selectively), stack/*.md (selectively)}
{These are declarative quality criteria applied AFTER code is written, not during construction}
{Active build checks from reviews/build-checks.md (if any)}
{Known Patterns to Avoid: BC-ID, title, what to check, root cause, expert}
{Omit build checks if no active checks exist or none are relevant to this chunk}
```

## Handover Format

Post-build handovers are written after execution to `build/handovers/P{X}-C{XX}.md`. They record what was actually built.

```markdown
# Handover: P{X}-C{XX} — {Chunk Name}

## Status: {Complete / Partial / Failed}
## Commit: {SHA}
## Branch: {branch name}

## Files Created
{List of files with line counts}

## Files Modified
{List of files modified, with description of changes}

## Tests (verified)
{Count: N tests passing (X unit, Y integration)}
{Verified exit code: 0}
{Test command: e.g., `pytest backend/tests/unit/auth/ -v`}
{Parsed output: "12 passed, 0 failed" — extracted from test runner output, not AI interpretation}

Acceptance test Red commit: {SHA of the commit where the outside-in
acceptance test was first added and FAILED — TDD-1 evidence per Beck
Red-Green-Refactor. CONDITIONAL: MANDATORY for user-facing chunks.
For internal-helper exemptions, write the literal line
`TDD-1 exempted: <reason>` instead — this single line replaces BOTH
this field and the Green commit field below (per ADR-MH-04).}

Acceptance test Green commit: {SHA of the commit where the same acceptance
test first PASSED — proves the Red→Green transition rather than asserting
it. CONDITIONAL: MANDATORY for user-facing chunks; same `TDD-1 exempted:
<reason>` line replaces both fields for internal-helper exemptions.}

## Test Command
{Command to re-run this chunk's tests, e.g., `pytest backend/tests/unit/auth/ -v`}

## Hard Gate 8 (chunk-acceptance smoke — GATE-1)
{This section is mandatory whenever the chunk's `build/prompts/P{X}-C{XX}.md`
mtime is on or after `_V2_1_0_RELEASE_DATE` (NFR-1 carry-over rule).
Pre-release chunks MUST record the literal line
`Hard Gate 8 exempted: v2.0.x carry-over` in the exemption-marker field
below; they may then leave the Smoke command / Exit code / Structural
assertions fields blank. The exemption marker is the audit trail —
silent omission is a Hard Gate 8 violation.

Smoke command: {literal CLI string the gate ran, e.g., `npm run smoke:auth`
or `python -m mypkg.cli --in fixtures/sample.json`. Not "ran the tests" —
the literal command.}

Exit code: {integer; 0 = pass, non-zero = refusal — handover should not have
been written. Record the integer, not "passed".}

Structural assertions verified:
- {asserted contract 1, e.g., "produced HTML contains an `<h1>` and a
  non-empty `<table.findings>`"}
- {asserted contract 2, e.g., "JSON output has required keys
  `summary`, `findings`, `methodology`"}

Hard Gate 8 exempted: {CONDITIONAL — MANDATORY for v2.0.x carry-over
chunks (write exactly `Hard Gate 8 exempted: v2.0.x carry-over`);
OPTIONAL for ADR-MH-04 surface-change exemptions where the reason names
the surface (e.g. "internal helper, no user-facing surface change" /
"pure refactor — covered by existing chunk's smoke"). Silent skip with
no recorded exemption is a Hard Gate 8 violation.}}

## Diff Summary
{Output of `git diff --stat` for this chunk's commits}

Diff budget delta: {literal signed integer — net-added lines (additions
minus deletions) across `*SKILL.md` files in this chunk's diff. Wire
format MUST match the regex `^Diff budget delta:\s*(-?\d+)\s*$` (one
line, single signed integer, no units, no parenthetical detail). Source:
`git diff --stat -- '*SKILL.md'` summary applied to the chunk's commit
range; record `0` for chunks that touch no SKILL.md. The build summary
aggregates these per-chunk values into a cumulative running total per
NFR-2 / cross-cutting § Diff Budget Tracking. Non-conforming values
(decimals, units like `12 lines`, parentheticals like `12 (3 added, 9
deleted)`, or text like `none`) count as `0` and the build-summary
emits a warning naming the offending handover so the divergence is
audit-trailed, not silently absorbed.}

## Code Review Findings
{This section is mandatory — if it is empty or missing, Hard Gate 3 was skipped.

**Review passes:** {ordered list of (pass_number, critical_or_important_findings_count) tuples,
e.g. `[(1, 3), (2, 3), (3, 0)]`}.

The pass_log is structurally constrained:
- The FINAL tuple's count MUST be 0. A non-zero terminator means the loop did not converge.
- A pass_log of length 1 is only valid when its single entry is `(1, 0)` — clean on first pass.
- Any pass_log of length ≥ 2 must show the count strictly decreasing on each pass; otherwise
  the loop stalled and the chunk should not have been committed.

A handover that lists only one pass with non-zero findings is structurally invalid
and the handover write step (Gate 4) MUST refuse it.

For each finding (across all passes):
- What was found (the issue)
- Which expert principle identified it
- Which review pass surfaced it (pass-1 / pass-2 / etc.)
- What was fixed
- Whether re-test passed after the fix

If pass-1 returned 0 findings, state: "Clean on first review pass — no findings;
pass_log: [(1, 0)]." This is a valid outcome but must be explicitly stated and
the pass_log entry recorded.}

## Deviations from Spec
{Any differences from the spec, with rationale. "None" if exact match.}

## Surfaced Requirements
{New requirements or spec gaps discovered during build. These bubble up
through /gvm-requirements — never modify existing specs or chunks silently.

This section is the STAGING GROUND, not the destination. Per shared rule 27,
every surfaced requirement MUST be promoted to `requirements/requirements.md`
during triage (between chunks, at phase completion, or in the BUILD SUMMARY
step). Surfaced requirements MUST NEVER be parked in `STUBS.md`.

For each surfaced requirement, record:
- What was discovered
- Which requirement or spec section it relates to (or "new scope")
- Triage status: "open" (awaiting first prompt) / "promoted to RE-N" / "deferred — awaiting triage" (user dismissed the AskUserQuestion; re-prompt at next checkpoint)

"None" if spec was accurate.}

## Upstream Fixes
{Any changes made to files from prior chunks, with rationale.
E.g., "Modified P1-C04's error handler to support WebSocket errors. P1-C04 tests re-run and passing."}

## Notes for Downstream Chunks
{Anything the next chunk needs to know — shared utilities created,
unexpected patterns, config changes, etc.}

## Retrospective
{What was harder or easier than expected? What would you do differently?
Captures lessons for future chunks and future projects.}
```

## Git Strategy

Offered per chunk via AskUserQuestion. Auto-recommendation logic:

| Scenario | Recommendation |
|---|---|
| Sequential chunk, small/medium | Current branch |
| Large chunk, user wants PR review | Feature branch (`build/P{X}-C{XX}-{name}`) |
| Parallel dispatch (multiple chunks) | Git worktree (one per chunk) |

The user always has final say. For parallel dispatch, worktrees are required (multiple agents can't share a branch).

## Parallel Dispatch

When the dependency matrix shows parallelisable chunks, offer:

```
N chunks are ready to build in parallel:
  P3-C02 (Real Estate Agent)
  P3-C03 (Education Agent)
  ...

Options:
  ○ Build sequentially (one at a time)
  ○ Dispatch all N in parallel (git worktrees, one subagent each)
  ○ Pick specific chunks to parallelise
```

**Parallel flow:**
1. **Guard:** Verify worktree support — run `git worktree list`. If the command fails (shallow clone, bare repo, or unsupported environment), fall back to sequential execution on feature branches and inform the user.
2. Generate prompts for all selected chunks
3. Dispatch each chunk to a subagent via the Agent tool with `isolation: "worktree"`
4. Each subagent: executes its prompt (TDD loop), writes handover, commits to its worktree branch
5. Monitor completion, present results
6. Offer merge strategy: sequential merge into main, combined PR, or manual

## Testing Tiers

| Tier | When | Scope |
|---|---|---|
| **Per-deliverable** | During TDD loop | One test file at a time | Same-context self-review (fast) | Test → Review |
| **Chunk-level** | After all deliverables in a chunk | All tests written in this chunk | Independent agent review (spawned) | Review → Test |
| **Phase-level** | After all chunks in a phase complete | All tests across all chunks in the phase | Full `/gvm-code-review` at end | Review → Test |

Phase-level testing catches cross-chunk integration issues (e.g., auth middleware works with the API endpoints it protects).

**Why tiered review matters:** Self-review during construction is systematically weaker than independent review (Fagan, 1976; confirmed by production observations — see whitepaper Section 9.1). The per-deliverable self-review catches mechanical issues. The chunk-level independent review catches what the builder's own context missed — API misuse, design errors, principle violations that the same agent cannot see in its own output. The full code-review at the phase/project level catches cross-chunk integration and architectural issues.

## Self-Review Loop

**After code is written (and after per-deliverable tests pass), you MUST review the code against expert principles from the Review Criteria section.** This step is not optional — skipping it is the most common execution failure. Expert principles are declarative quality criteria: they define what good code looks like. They are applied during review, not during construction (see Key Rule 23).

The review work splits into two phases that BOTH run before commit:

**Phase 1 — author self-review (per-deliverable, fast).**
1. Review working code against the Review Criteria (expert principles + build checks)
2. Run the defect-class checklist (References / Contracts / Completeness / Naming)
3. If issues found → fix → re-test → re-review

**Phase 2 — independent review convergence loop (Hard Gate 3).**
This is the gate that catches what the author cannot see in their own work — and the gate practitioners (and AIs) most often shortcut. The loop runs an Agent-tool dispatch in a counted loop; it ONLY exits on a pass that returns zero Critical/Important findings.

1. pass_number = 1; pass_log = []
2. Dispatch independent review agent (model: sonnet) with the chunk's files, Review Criteria, spec excerpt, and a note of which prior-pass findings were fixed
3. pass_log.append((pass_number, count_of_critical_or_important))
4. If count == 0 → loop converged; present REVIEW CHECKPOINT to user via AskUserQuestion
5. If pass_number == 5 and count not decreasing → stop and flag user
6. Otherwise: fix all Critical/Important using the same expert framework that surfaced them (rule 19), re-test, increment pass_number, dispatch another review

**Anti-shortcut rules:**
- A single pass with non-zero findings is NOT the terminal state. Pass-1 finding 3 issues and you fixing them is NOT convergence.
- The user checkpoint fires AFTER convergence, not after pass-1. Approving "tests pass and pass-1 findings are fixed" is structurally premature.
- The handover MUST record `Review passes: [(1, N1), (2, N2), ..., (final, 0)]`. The final tuple must be `(K, 0)`. A pass_log without that terminator is invalid.

**For chunk-level and phase-level tests (slower):** review BEFORE running these tests. API contract mismatches and design errors are caught faster by review than by waiting for slow test failures.

Expert quality criteria live in `~/.claude/skills/gvm-design-system/references/`. Read the relevant sections based on the chunk's stack and domain:

| File | Loaded When |
|---|---|
| `architecture-specialists.md` | Always (Tier 1) |
| `domain/*.md` files | Based on chunk's domain (Tier 2a) — load selectively, see `domain-specialists.md` index for activation signals |
| `stack-specialists.md` (index) → `stack/*.md` | Based on chunk's language/framework (Tier 3) — load index for constraints, then matching per-stack files |

## Context Loading

Minimal context per chunk. Load only:

1. **Implementation guide** — the chunk description section only (~30 lines)
2. **Cross-cutting spec** — conventions section only (~200 lines)
3. **Domain spec section** — the specific section referenced by the chunk (~300-500 lines)
4. **Dependency handovers** — what upstream chunks actually built (~50 lines each)
5. **Framework documentation** — relevant API sections for this chunk's tech stack (~100-300 lines)
6. **Expert principles** — relevant sections from architecture/domain/stack specialists for the Review Criteria (~80-130 lines)
7. **Build checks** — active checks from `reviews/build-checks.md` if it exists (~20-50 lines)

Never load the full spec suite. Never load all handovers. Load only what this chunk needs.

## Session Management

### Handover Memory

After every 2-3 chunks, update the project memory file with:
- Which chunks are complete (with commit SHAs)
- Which chunk is next on the critical path
- Any deviations from the implementation guide
- Context budget status (chunks completed this session — compact becomes mandatory at 4)

### Resuming a Session

When `/gvm-build` starts, it detects state by:
1. Reading `build/handovers/*.md` — which chunks have handovers (done)
2. Reading `build/prompts/*.md` — which chunks have prompts but no handover (started, not done)
3. Reading `build/handovers/*-partial.md` — which chunks were stashed in progress (started, tests failing). On resume: run `git stash pop {stash ref from partial handover}` to restore the work-in-progress before continuing. After popping the stash, return to step 5 EXECUTE CHUNK at the sub-step for the first failing deliverable listed in the partial handover. Do not re-run DEPENDENCY CHECK or re-write the prompt.
4. Cross-referencing with the implementation guide dependency matrix

**Multiple handover versions:** When multiple handovers exist for the same chunk (e.g., `P1-C03.md` and `P1-C03-v2.md`), the highest-versioned file is the canonical handover. Earlier versions are historical records only. In the dependency GUARD, use the highest-versioned handover for each dependency.

This lets the user resume from any point — even in a fresh session after context compression.

## Key Rules

### Before you build (rules 1–7)

1. **Spec is the contract** — code follows the spec. If the spec is wrong, flag it to the user; don't silently diverge. Deviations recorded in handover with rationale.
2. **Strict TDD** — write the failing test first. No code without a test that demands it. Red → Green → Refactor.
3. **Review working code, not speculative code** — for per-deliverable unit tests (fast), run the test first, then review working code against the Review Criteria. For chunk-level and phase-level tests (slow), review first — API and design errors are caught faster by review than by slow test execution. Fix iteratively until clean.
4. **Lint and format before commit** — run the lint and format commands from `~/.claude/skills/gvm-design-system/references/stack-tooling.md` for the project's stack after the review loop. Fix any mechanical issues. Commit formatting changes separately.
5. **Chunk-level tests, phase-level integration** — each chunk runs its own tests. After all chunks in a phase, run the full phase suite.
6. **Dependency tests run first** — before executing a chunk, run the test suites of all dependency chunks. This verifies the environment and prior work. If dependency tests fail, stop before writing new code.
7. **One prompt, one handover** — every chunk gets a pre-build prompt and a post-build handover. These are the persistence mechanism.
### During the build (rules 8–17)

8. **Never overwrite prompts or handovers** — these are records of what was planned and what was done. If a chunk needs to be re-done, create a new handover (e.g., `P1-C03-v2.md`) alongside the original. The original is a historical record.
9. **Git strategy is per-chunk** — current branch, feature branch, or worktree. Offered at execution time.
10. **Parallel dispatch is offered, not forced** — when the dependency matrix shows parallelisable chunks, offer the choice.
11. **Context loading is minimal** — implementation guide chunk + cross-cutting conventions + domain spec section + relevant best practices. Never the full spec suite.
12. **Handover memory + context budget** — update project memory after every 2 chunks for session resilience. Context budget: after 2 chunks in a session, recommend `/compact`. After 3, strongly recommend. After 4 without compacting, make it mandatory. Code generation fills context faster than other pipeline phases — quality degrades before you notice it.
13. **No implementation guide, no build** — if `specs/implementation-guide.md` doesn't exist, tell the user to run `/gvm-tech-spec` first.
14. **Commit discipline** — atomic commits per deliverable or logical unit. Format: `{type}: {description} [P{X}-C{XX}]`. Types: `feat:`, `fix:`, `test:`, `refactor:`, `style:`.
15. **Never auto-rollback** — when tests fail, keep the code as-is. Present the failure clearly. Offer: "Fix it now" / "Stash and come back later" / "Show diff so far". The fix may be one line away.
16. **New requirements bubble up, not sideways — and they promote, never park** — if building a chunk surfaces a new requirement or missing spec, do NOT modify existing chunks or specs. Record it in the handover's "Surfaced Requirements" field as the staging ground. Then, on triage (between chunks, at phase completion, or when running `/gvm-build` next), verify `requirements/requirements.md` exists and present via AskUserQuestion three promotion options (per shared rule 27):
    - "Append as acceptance criterion to an existing requirement" (with changelog entry per rule 11)
    - "Add a new requirement entry" (with changelog entry per rule 11)
    - "Create a new requirements document (next round)" — run `/gvm-requirements` in "New round" mode
    If the user dismisses the question or selects no option, mark the surfaced requirement as `deferred — awaiting triage` in the handover and re-prompt at the next checkpoint — do not silently park it. The destination is always `requirements/requirements.md`. Surfaced requirements MUST NEVER be parked in `STUBS.md` under any heading or column — `STUBS.md` is for code-level placeholders only, with no `STUB-SR-NN` IDs and no `## Surfaced Requirements` section. Existing prompts and handovers remain immutable records of what was built; the promoted requirement lives in `requirements/requirements.md` going forward.
17. **Backward modifications go forward** — if building P2-C01 reveals that P1-C04 needs adjustment, do NOT retroactively change P1-C04's handover. Instead: make the fix in the current chunk, record it in the current handover's "Upstream Fixes" field, and re-run P1-C04's tests to verify nothing broke.

### After the build (rule 18)

18. **Hand off to /gvm-code-review then /gvm-test** — when the last chunk in the last phase is done, direct the user to run `/gvm-code-review` for a full codebase review, then `/gvm-test` to verify the build works as a product.

### Cross-cutting (rules 19–21)

19. **Experts who find should fix** — when the self-review loop flags an issue, resolve it using the same expert's framework (per shared rule 3).
20. **Expert discovery for uncovered domains** — per shared rule 2. Document discovered experts in the chunk handover.
21. **API boundary contracts are the source of truth** — when a chunk produces or consumes an API endpoint, the build prompt must include the exact response shape from the spec. Backend chunks implement that shape. Frontend chunks consume that shape. If the spec has no contract for a needed endpoint, stop and flag it — do not invent a shape and hope the other side matches.
22. **Build checks ground the review loop** — when `reviews/build-checks.md` exists with active checks, the self-review loop (Hard Gate 3) includes these checks alongside expert principles. Build checks are process-level checklists (Fagan) derived from past review findings — they prevent recurring defects at the point of creation rather than detecting them again at the point of review (Deming: fix the process, not the output).
23. **Separate construction grounding from review grounding** — during code generation, ground in the Framework Reference (language docs, framework APIs, library method signatures — procedural knowledge). During the self-review loop, ground in the Review Criteria (expert principles, build checks — declarative knowledge). Expert grounding is demonstrably effective during review. Its effectiveness during construction is undemonstrated — preliminary evidence suggests it may be inert for code generation while remaining effective for all other pipeline artefacts (requirements, test cases, specs, documents). This separation is a testable hypothesis, not a proven finding.
