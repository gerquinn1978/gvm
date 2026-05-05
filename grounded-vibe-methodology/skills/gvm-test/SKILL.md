---
name: gvm-test
description: Use when verifying a completed build — integration seam audit, full code review, startup verification, smoke testing, and stub audit. Triggered by /gvm-test command, requests to verify the build is complete, or after the last chunk of /gvm-build finishes. This is the acceptance gate between "code exists" and "product works."
---

# Build Verification

Verifies that a completed build actually works as a product. Runs after all build chunks are complete. This is not a test suite — it verifies end-to-end behaviour, catches integration gaps between chunks, and produces an honest audit of what is implemented vs stubbed.

**Shared rules:** At the start of this skill, load `~/.claude/skills/gvm-design-system/references/shared-rules.md` and follow all rules throughout execution. Load `~/.claude/skills/gvm-design-system/references/expert-scoring.md` when scoring experts.

## Modes

**Full mode:** 10+ chunks, greenfield build. All steps run at full depth. Code review prerequisite is required.

**Light mode:** Small targeted fix, ≤2 chunks. Mode is selected via AskUserQuestion at skill start. Integration seam audit and stub audit may be skipped if the change is localised. Code review prerequisite is optional — note its absence in the report. All Hard Gates (1–5) apply in light mode with one modification to Gate 1: in light mode, if no code review file exists, note its absence and proceed (do not stop). If a code review file exists with unresolved critical findings, warn the user and record in the report, but proceed. Gates 2 (RUN ACTUAL COMMANDS), 3 (WRITE HTML OUTPUT), and 4 (WRITE HTML BEFORE PRESENTING) apply without modification.

**Model selection (per shared rule 22):** Light mode uses `model: sonnet` — verification of ≤2 chunks is guided work. Full mode uses the primary model.

**Mode selection trigger:** At skill start, check `build/handovers/` for the number of completed chunks. If ≤2, scan the git diff for Light-mode disqualifiers (below) first. If any disqualifier is found, force Full mode and record the trigger in the report. Otherwise offer mode via AskUserQuestion: 'This looks like a small change (N chunks). Use Light mode or Full mode?' If >2, proceed in Full mode without asking.

**Light mode disqualifiers — use Full mode regardless of chunk count when ANY are true:**

Light mode assumes "small delta = small risk." That's only valid when the delta is self-contained. A small delta that touches factory selection, DI seams, or dormant code paths can *activate thousands of lines of previously-unexercised code* — the risk is in what the delta unblocks, not in what it modifies. Scan the git diff (`git diff $BASE..HEAD --name-only` and targeted grep over changed files) for any of the following before accepting Light mode:

| Signal in the diff | Why it disqualifies Light mode |
|---|---|
| Factory / registry / DI container changes (`_create_*`, `_default_*`, `register(`, container wiring) | Flips which implementations run in production. Dormant providers/services activate simultaneously. |
| Env/config reading changes (`Settings()`, `os.environ`, `.env`) | May unblock code paths that were silently falling back to mocks. |
| New dependency in `pyproject.toml` / `package.json` / `requirements.txt` / `Gemfile` / `go.mod` | Activates an import path that was dead. Static analysis may not have exercised it. |
| Changes to the "real vs mock" boundary — adapter classes, provider registries, feature flags that gate external service use | Tests typically mock one side; flipping the boundary exposes unverified wiring. |
| Schema migrations PLUS code that writes enum/type values | Possible drift between language-level enum and DB enum sets. |

If any of these appear, set Full mode and do not offer the Light option. Record the trigger in the report's Executive Summary as "Full mode forced — {specific trigger observed in diff}." Fairbanks (*Just Enough Software Architecture*): depth is proportional to risk, not to line count.

## Hard Gates

These steps are non-negotiable. If you skip any of them, the verification output is invalid.

1. **VERIFY CODE REVIEW EXISTS.** Use the following decision table:

   | Mode | No code review file | Code review exists, unresolved criticals |
   |------|--------------------|-----------------------------------------|
   | Full | Stop — run /gvm-code-review first | Stop — fix criticals before proceeding |
   | Light | Note absence, proceed | Warn user, record in report, proceed |

2. **RUN ACTUAL COMMANDS.** Every verification step (startup, health checks, smoke tests) MUST execute real commands via the Bash tool. DO NOT claim a service started, a health check passed, or a smoke test succeeded without running the actual command and checking its output. Assumed success is not verification.

3. **WRITE HTML OUTPUT.** The test report MUST produce `test/test-{NNN}.html`. Review/verification reports are HTML-only — no paired MD is produced (shared rule 13 exception for review reports). Findings are carried forward in `reviews/calibration.md`. DO NOT end the verification without the HTML file written.

4. **WRITE HTML BEFORE PRESENTING RESULTS.** The HTML file MUST exist before presenting test results to the user. Load `~/.claude/skills/gvm-design-system/references/review-reference.md` and the Tufte references before the HTML write.

5. **VERDICT.** Use the three-verdict taxonomy (Ship-ready / Demo-ready / Not shippable) emitted by `gvm_verdict.evaluate` (per honesty-triad ADR-105). The verdict appears in the report and in the text presented to the user. Load `~/.claude/skills/gvm-design-system/references/review-reference.md` before writing the report. DO NOT end verification without a verdict.

## Prerequisites

- `specs/implementation-guide.md` must exist
- `build/handovers/` must contain handover files for all chunks in the implementation guide
- `test-cases/test-cases.md` must exist (the acceptance criteria generated by `/gvm-test-cases`)
- `requirements/requirements.md` must exist
- An initialised git repository with build commits

When loading expert references (shared-rules.md, expert-scoring.md, or any specialist reference files), log all loaded experts to activation CSV (per shared rule 1).

If any chunks are incomplete, tell the user to finish the build first with `/gvm-build`. If test cases don't exist, tell the user to run `/gvm-test-cases` — the acceptance criteria are needed for verification.

## Process

```
0. BOOTSTRAP — per shared rule 14, verify ~/.claude/gvm/ exists before writing output.

1. PREREQUISITE CHECK
   ├── Check code-review/ directory for review files
   ├── Check for unresolved critical findings in any existing review
   └── Apply Hard Gate 1 decision table based on current mode (full/light)

2. INTEGRATION SEAM AUDIT
   ├── Grep codebase for NotImplementedError, "TODO", "deferred to integration", "not yet wired"
   ├── For each hit: is this blocking (prevents core user flow) or non-blocking (enhancement)?
   ├── Blocking seams MUST be resolved before proceeding — wire the integration.
   │   If a blocking seam cannot be resolved in this session (requires upstream code
   │   changes, missing dependency, spec ambiguity), stop verification and present via
   │   AskUserQuestion: "Fix the seam and re-run /gvm-test" or "Accept as a known gap
   │   and document in the test report as BLOCKED." Do not proceed to step 3 with an
   │   unresolved blocking seam unless the user explicitly accepts it as a known gap —
   │   record the override in the BLOCKED section of the test report.
   └── Non-blocking items recorded in "known limitations" section

3. STARTUP VERIFICATION
   ├── Start infrastructure (docker compose up -d or equivalent)
   ├── Run database migrations
   ├── Start the backend server — verify it starts without errors
   ├── Start the frontend dev server — verify it compiles and serves
   ├── Hit the health endpoint — verify all services report healthy
   └── If any service fails to start → fix before proceeding

4. ACCEPTANCE TEST VERIFICATION
   ├── Read test-cases/test-cases.md
   ├── For EVERY test case (TC-*), determine whether it passes against the built code:
   │   ├── PASS — the Given/When/Then scenario works end-to-end with real data
   │   ├── FAIL — the scenario does not produce the expected result
   │   ├── BLOCKED — cannot execute (dependency not wired, service not starting, etc.)
   │   └── STUB — the code path exists but uses mock/placeholder data
   ├── For MUST and SHOULD priority test cases, execute the scenario where possible:
   │   ├── API-level tests: use curl/API calls to exercise the Given/When/Then flow
   │   ├── UI-level tests: walk through the user interaction described in the test case
   │   └── Logic-level tests: run the existing unit/integration test suite
   ├── Present results as a table: TC ID, Name, Priority, Status (PASS/FAIL/BLOCKED/STUB)
   ├── Count: X PASS / Y FAIL / Z BLOCKED / W STUB
   └── FAIL and BLOCKED on MUST test cases are blocking issues — fix before proceeding

5. MUTATION TESTING (optional — critical-path code only)
   ├── Offered via AskUserQuestion after acceptance tests pass — skip if user declines
   ├── Identify critical-path files: MUST-priority requirements, security-sensitive code,
   │   business logic with high consequence of failure
   ├── Read `~/.claude/skills/gvm-design-system/references/stack-tooling.md` for mutation testing commands
   ├── Install the mutation testing tool if not present
   ├── Run mutation testing on critical-path files only (not the entire codebase)
   ├── Report mutation score: killed / total mutants (percentage)
   ├── Surviving mutants on MUST requirements → flag as test gaps, suggest additional tests
   ├── Surviving mutants on SHOULD/COULD → note in report, do not block
   └── If no mutation testing tool exists for the stack, note it and skip

6. SMOKE RUN (beyond test cases — user experience verification)
   ├── 6a. REAL-CHAIN INTEGRATION TEST (mandatory)
   │   ├── The unit-test tier in /gvm-build mocks collaborators at the class
   │   │   boundary (e.g. `_create_domain_agent`, repository interfaces).
   │   │   That tier verifies each layer in isolation; it does NOT verify the
   │   │   real wiring between layers. Duck-typed adapters can have missing
   │   │   methods, wrong signatures, or undeclared deps that unit tests
   │   │   cannot see.
   │   ├── Before the UI walkthrough, run or add a "real-chain" integration
   │   │   test that:
   │   │   ├── Instantiates the real production classes from the DI root
   │   │   │   downward — NO mocks at internal Python class boundaries
   │   │   ├── Mocks only the external HTTP / DB boundaries (e.g. Anthropic
   │   │   │   API, Tavily, third-party webhooks) with canned responses
   │   │   │   shaped like real responses
   │   │   ├── Invokes the primary end-to-end flow (e.g. the LangGraph
   │   │   │   pipeline, the main use case) and asserts every stage produced
   │   │   │   output of the expected shape
   │   │   └── Verifies the mocked HTTP boundary was actually called (proves
   │   │   │   the real chain fired, not a silent fallback)
   │   ├── This test catches: protocol drift on duck-typed adapters, missing
   │   │   deps that only appear at runtime, schema drift between ORM and
   │   │   DB, factory selection bugs, and dormant-path activation surprises.
   │   │   Sandi Metz (*POODR*, Ch. 9): mock at boundaries — but the boundary
   │   │   is the external network, not every internal class.
   │   └── If no real-chain test exists, write one now. It is the single
   │       highest-leverage test in the verification suite.
   ├── 6b. UI / USER EXPERIENCE WALKTHROUGH (web/UI products)
   │   ├── Start infrastructure, run migrations, start all services
   │   ├── Hit health endpoints — verify all services report healthy
   │   ├── Walk through every page and interactive element in the UI
   │   ├── Check that navigation, forms, dynamic content, and real-time features work
   │   └── Any placeholder, TODO, or console.log in a user-facing path is a blocking issue
   ├── 6c. CLI PRODUCT SMOKE — PARAMETRIC OVER FLAGS + STRUCTURAL CONTRACTS
   │   │   For products whose primary surface is a CLI that produces files
   │   │   (HTML reports, findings.json, generated artefacts), the equivalent
   │   │   of the UI walkthrough is parametric exercise of every documented
   │   │   flag value PLUS structural-content assertions on the output.
   │   │   This step is mandatory whenever the product is invoked via CLI
   │   │   and emits artefacts that downstream consumers (or end users) read.
   │   │
   │   │   The motivating failures (post-v2.0.0 of /gvm-analysis):
   │   │   - `--mode decompose` crashed with TypeError because a rename
   │   │     mid-build left one call site stale; explore mode worked, so
   │   │     a single-mode smoke missed it.
   │   │   - Clean ordinal data produced `report.html` with empty headline
   │   │     section; the canonical synthetic fixture had outliers, so
   │   │     "headlines populate" was implicitly assumed not asserted.
   │   │   - A 100-row mixed fixture with `category={A,B,C}` tripped a
   │   │     pre-existing privacy-scan substring collision and silently
   │   │     emptied headlines; the synthetic fixture used "Alice"/"Bob"-
   │   │     length tokens, so the real-world short-token case never ran.
   │   │
   │   │   All three would have surfaced if the smoke had: (a) iterated
   │   │   every `--mode`; (b) asserted structural contracts on `report.html`
   │   │   (chart `<img>` count > 0, headline section non-empty); (c) included
   │   │   a fixture variant with realistic data shapes (short categorical
   │   │   codes — sex M/F, blood type A/B/O, grades A/B/C/D/F, yes/no Y/N).
   │   │
   │   ├── PARAMETRIC FLAG COVERAGE: identify every documented value of
   │   │   every CLI flag that selects a code path (mode, strategy, format,
   │   │   etc.). Run the product against a representative fixture for each
   │   │   value. Assert exit 0 for each. A flag value that crashes is a
   │   │   blocking finding regardless of whether unit tests covered it.
   │   ├── STRUCTURAL HTML/JSON CONTRACTS: when the product emits HTML or
   │   │   structured JSON, write asserts on the output STRUCTURE, not just
   │   │   "renderer didn't crash." For HTML reports, examples:
   │   │   - chart `<img src="...">` count > 0 when the input has data
   │   │     suitable for charting
   │   │   - headlines section is non-empty (every fixture, every mode)
   │   │   - no `tracer-bullet` / `placeholder` / `TODO` substring anywhere
   │   │   - comparison block populated for validate-mode invocations with
   │   │     `--baseline-file`
   │   │   - referenced files exist (no broken `<img>`/`<a>` targets)
   │   │   For findings.json or equivalent: every field a downstream
   │   │   consumer reads must be present and of the documented type.
   │   ├── REAL-WORLD FIXTURE VARIANTS: in addition to the canonical
   │   │   synthetic fixture, drive the smoke against at least one fixture
   │   │   shape that REALISTICALLY differs from the engine's tuning. For
   │   │   data-analysis products that's: clean data with no anomalies;
   │   │   data with single-letter categorical codes; data without a target
   │   │   column when one is normally supplied. The synthetic fixture is
   │   │   often engineered to trip thresholds and exercises the happy path
   │   │   only; real-world fixtures exercise edge paths.
   │   ├── DOCUMENT EVERY ASSERTION IN THE TEST REPORT: list every flag
   │   │   value run, every fixture variant exercised, every structural
   │   │   contract checked, and the pass/fail outcome of each.
   │   └── A flag value with no exercise is the same risk class as code
   │       with no test. Skipping a flag because "the unit tests cover it"
   │       is exactly the failure pattern this step exists to prevent.
   ├── This catches UX issues that structured test cases don't cover
   └── If any flow fails → fix the integration before declaring done

7. STUB vs IMPLEMENTED AUDIT
   ├── Read requirements/requirements.md
   ├── Cross-reference with test case results from step 4
   ├── For EVERY requirement, classify as:
   │   ├── IMPLEMENTED — working end-to-end with real data/logic, test cases passing
   │   ├── PARTIAL — code exists but some test cases fail or gaps remain
   │   ├── STUB — architecture in place but uses mock/placeholder data
   │   └── NOT IMPLEMENTED — no code exists
   ├── Present the full audit table — do NOT gloss over stubs
   ├── Mock providers, placeholder LLMs, console.log handlers, and hardcoded
   │   data are STUBS, not implementations — label them honestly
   ├── Count: X IMPLEMENTED / Y PARTIAL / Z STUB / W NOT IMPLEMENTED
   └── List the top 5 gaps by priority (MUST requirements not fully IMPLEMENTED)

8. EVALUATE VERDICT (three-verdict taxonomy)
   ├── Load `reviews/calibration.md` via `_calibration_parser.load_calibration`.
   ├── If `calibration.schema_version == 0` (pre-migration project):
   │   ├── Run VV-6 retrofit (one-time): `plan_retrofit(cal)` from
   │   │   `_vv6_retrofit`. For each `RowDecision` in `plan.manual_required`,
   │   │   emit `AskUserQuestion` ("Round X verdict was 'Pass with gaps'; reclassify
   │   │   as Demo-ready or Not shippable?"). Build `manual_choices: dict[int, Verdict]`.
   │   ├── `apply_retrofit(cal, manual_choices)` → `write_calibration(...)`.
   │   ├── Non-interactive (CI) path: skip retrofit; record
   │   │   `Criterion("VV-6", "FAIL:non-interactive", evidence="...")` and proceed
   │   │   with the unmigrated calibration for read-only purposes.
   │   └── If `plan.already_applied`: emit "VV-6 retrofit already applied; skipping."
   ├── Load evaluator inputs:
   │   ├── `_stubs_parser.load_stubs(STUBS.md)` then `check_expiry(stubs, today)`.
   │   ├── `_explore_parser.load(latest_charter_path)` for VV-2(c)/VV-3(c)/VV-4(d).
   │   ├── `_boundaries_parser.load(boundaries.md)` for VV-3(d).
   │   ├── `_review_parser.load(latest_findings_json)` if a code-review report exists
   │   │   — drives VV-4(a). If no report, VV-4(a) is N/A.
   │   └── `_risk_validator.full_check(risks/risk-assessment.md)` for VV-2(b)/VV-4(c).
   ├── Build `VerdictInputs(...)` from those records.
   ├── Call `gvm_verdict.evaluate(inputs)` → `VerdictResult(verdict, criteria)`.
   │   `verdict` is one of `Verdict.SHIP_READY` / `Verdict.DEMO_READY` /
   │   `Verdict.NOT_SHIPPABLE`. The evaluator never produces any other value
   │   (per honesty-triad ADR-105 — the three-verdict taxonomy is encoded as a
   │   finite state, never as text concatenation).
   ├── Render via the verdict HTML component (per P8-C02) into the report's
   │   Verdict section.
   └── Append a new row to `calibration.score_history` capturing this round's
       outcome and write back via `write_calibration`.

9. DECLARE COMPLETE or SURFACE REMAINING WORK
   ├── If all verification passes → build is complete
   ├── If stubs remain → present the audit table and ask user whether to
   │   wire real implementations or ship with documented limitations
   ├── The build is only "complete" when the user explicitly accepts the
   │   current state — do not self-declare completion with stubs unmarked
   └── Handoff: Run `/gvm-doc-write` to create project documentation
       (README, CHANGELOG, user guides, API docs), then `/gvm-doc-review`
       to verify documentation quality
```

## Output

Produces an HTML-only report (no paired MD):

```
test/test-001.html
test/test-002.html
...
```

Each run produces a new numbered HTML report. The report contains:

1. **Executive Summary** — overall pass/fail, counts of issues found and resolved
2. **Integration Seam Audit** — blocking seams found and resolved, non-blocking items documented
3. **Code Review Status** — verdict from `/gvm-code-review` and count of unresolved critical findings (from Hard Gate 1 check). Do not summarise internal code-review concepts (fix loop iterations, etc.) — only report what the prerequisite check observed.
4. **Acceptance Test Results** — test case pass/fail/blocked/stub table from test-cases.md, with counts
5. **Mutation Testing Results** (if run) — mutation score per critical-path file, surviving mutants flagged as test gaps
6. **Smoke Run Results** — user experience verification outcomes, issues found
7. **Requirement Coverage Audit** — the full IMPLEMENTED/PARTIAL/STUB/NOT IMPLEMENTED table, cross-referenced with test case results
8. **Verdict** — Ship-ready / Demo-ready / Not shippable, per honesty-triad ADR-105 (emitted by `gvm_verdict.evaluate`). Use the `.verdict` HTML component.

**HTML generation:** Dispatch the HTML report generation as a Haiku subagent (`model: haiku`). Per shared rule 22.

Use the Read tool to load three files before the first HTML write: `~/.claude/skills/gvm-design-system/references/tufte-html-reference.md` (core), `~/.claude/skills/gvm-design-system/references/tufte-review-components.md` (verdict box), and `~/.claude/skills/gvm-design-system/references/review-reference.md` (verdict language and Finding Quality Gate — per shared rule 5, /gvm-test is a quality-review skill).

## Pipeline Position

```
/gvm-requirements → /gvm-test-cases → /gvm-tech-spec → /gvm-design-review (optional) → /gvm-build → /gvm-code-review → /gvm-test → /gvm-doc-write → /gvm-doc-review → /gvm-deploy
```

`/gvm-test` sits after code review in the pipeline. The build produced code, `/gvm-code-review` reviewed it for quality, and `/gvm-test` verifies the reviewed code works as a product. Fix code quality issues before investing in integration testing and smoke runs — that's why code review comes first.

## Key Rules

1. **Steps are mandatory but depth is proportional to risk** (Fairbanks). For a full build (10+ chunks, greenfield), run every step at full depth. For a targeted fix (1-2 chunks in a coherent codebase), offer a light verification: skip the integration seam audit (step 2) and stub audit (step 7) if the change is localised — see Modes section for the decision criteria, and run a targeted smoke test rather than a full product walkthrough. In light mode, the code-review prerequisite is optional — if `/gvm-code-review` has not been run for this fix, note it in the report but do not block verification. If `/gvm-code-review` has been run and has unresolved critical findings, still warn the user in light mode — do not block, but record the unresolved criticals in the Executive Summary. Ask the user via AskUserQuestion which mode to use when the build scope is small.
2. **Stubs are stubs** — mock providers, placeholder data, console.log handlers, and hardcoded responses are not implementations. Label them honestly.
3. **The user decides what ships** — present the audit table and let the user decide. Do not self-declare completion.
4. **Critical code review findings** — behaviour depends on mode. See the Hard Gate 1 decision table for the authoritative rule.
5. **Smoke tests verify user experience** — this is not a test suite. It verifies the product works as a user would experience it.
6. **Expert discovery for uncovered domains** — per shared rule 2. Document discovered experts in the test report.
7. **Score automatically** — per shared rule 9.
