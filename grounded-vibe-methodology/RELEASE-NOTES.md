# v2.2.0 — 2026-04-30 (cumulative since v1.0.0)

This release rolls up everything shipped on the v2.x track since v1.0.0: four new skills, methodology hardening, runtime gap closures, and cumulative quality improvements. The v2.2.0 point itself closes the last open known issue from v2.1.x — TS and Go `mock-budget` runtime detection.

## What's New since v1.0.0

### Four new skills (v2.0.0)

- **`/gvm-impact-map`** — discovery skill producing `impact-map.md` (Adzic + Cagan model: Goals → Actors → Impacts → Deliverables). Foreign-key validator across all four levels; goals pass an ambiguity-verb scan. Downstream `/gvm-requirements` Phase 5 gate (IM-4) refuses any requirement that doesn't trace to a leaf Deliverable.
- **`/gvm-walking-skeleton`** — discovery + scaffolding skill producing a runnable skeleton that exercises every external boundary (HTTP, DB, cloud SDK, filesystem, subprocess, email) plus `boundaries.md` registry. Surfaces integration failure at hour 1, not month 6. Gates: `/gvm-build` WS-5 refuses chunks if the skeleton is red in CI; `/gvm-test` VV-4(d) audits sandbox-divergence notes.
- **`/gvm-explore-test`** — practitioner-driven exploratory testing with YAML charter (mission, tour, scope, duration), timed sessions, `AskUserQuestion`-driven defect intake. Severity is the practitioner's call. Produces a paired session report that `/gvm-test` reads via VV-4(d).
- **`/gvm-analysis`** — privacy-preserving exploratory data analysis. Claude orchestrates a Python engine over CSV / TSV / xlsx / parquet / JSON; raw rows never enter Claude's context. Produces real per-column statistics with bootstrap CIs, outliers, time-series, drivers (Decompose / Validate / Run-everything modes), privacy-safe duplicate summary, deterministic comprehension-question synthesis, full provenance per ADR-202, and rendered SVG charts with graceful degradation per ADR-201.

### Methodology hardening (v2.1.0)

- **`/gvm-build` Hard Gate 8 (NFR-1 / GATE-1)** — chunk-level acceptance smoke gate; refuses the handover when smoke exit code is non-zero. Carry-over exemption keyed off `_V2_1_0_RELEASE_DATE = "2026-04-28"`. ADR-MH-04 internal-helper exemption.
- **TDD-1 outside-in ordering** — outside-in acceptance test is the first deliverable for user-facing chunks. Pure-internal-helper exemption via `TDD-1 exempted: <reason>` marker.
- **TDD-2 mock budget at the external boundary** — eight named external-boundary categories plus third-party SDK rule. Wrapper-as-SUT exemption (ADR-MH-02). Severity escalation (ADR-MH-03) — opt-in via `.cross-chunk-seams` allowlist; default Important, escalates Critical when target is listed.
- **TDD-3 realistic-fixture catalogue** — six named domains (data-analysis, web/UI, API, parsing, security validation, concurrency) with starter fixture shapes. Override via `realistic-fixture-not-applicable: <rationale>`.
- **`/gvm-tech-spec` Hard Gate 6 / GATE-2** — wiring matrix gains "Demanded by" fourth column; refusal on empty cells; explicit exemption row format for legitimate internal helpers.
- **REVIEW-1** — `/gvm-code-review` Panel B integrates `mock-budget` violation kind alongside `rainsberger` / `metz`; runs on every test file (not only `[CONTRACT]`-tagged).
- **REVIEW-2** — `/gvm-code-review` Panel C realistic-fixture mandate.
- **NFR-2 diff-budget tracking** — handover template `Diff budget delta` field; cumulative aggregation; user prompt at 500-LOC crossing per ADR-CC-03 (surface-and-track, not refusal gate).
- **NFR-3 methodology-changelog** — new `methodology-changelog.md` at project root; `/gvm-status` reads most recent dated entry.
- **shared rule 28** — Review Finding Triage Is User-Owned. Hard Gate 6 in `/gvm-code-review` and `/gvm-design-review`; Hard Gate 7 in `/gvm-doc-review`.

### Wiring-matrix audit pair (v2.0.0 + v2.0.1)

- **`/gvm-tech-spec` Hard Gate 6** — every implementation guide must contain a "Wiring matrix" section (entry point → consumed modules → wiring chunk).
- **`/gvm-build` Hard Gates 6 + 7** — Gate 6 refuses to start a phase if the impl guide lacks a wiring matrix; Gate 7 runs at phase completion: for every (entry_point, module) row, mechanically grep the entry-point file for both an import and a call site. Inverse audit (added in v2.0.1) closes the dual failure mode where a module is built but never written into the matrix.

### `/gvm-test` step 6c — CLI Product Smoke (v2.0.1)

Parametric over CLI flags, structural HTML/JSON contracts, real-world fixture variants. Surfaces failure modes that synthetic happy-path fixtures miss.

### `/gvm-status` verdict-aware reporting (v2.0.1)

Reads the latest test-verification verdict and surfaces it with a chain status line.

### TS/Go mock-budget runtime (v2.2.0)

- **TS mock-budget detection.** `_lint_typescript` emits `mock-budget` via `_detect_mock_budget_ts`. `_TS_STACK_DEFAULTS` external-boundary allowlist (node:* builtins, axios / undici / got / ky / node-fetch, pg / mongodb / redis / mongoose, AWS / Google / Stripe / Anthropic / OpenAI SDKs). Mock detection covers `vi.mock`, `vi.spyOn`, `jest.mock`, `jest.spyOn`, `td.replace`, `sinon.stub`, `sinon.replace`. Internal mocks emit Important; matches in `.cross-chunk-seams` escalate Critical (ADR-MH-03 parity). Wrapper-as-SUT exemption (ADR-MH-02) fires on basename equality, not substring.
- **Go mock-budget detection.** `_lint_go` emits `mock-budget` via `_detect_mock_budget_go`. Three orthogonal signals per `func TestXxx(t *testing.T)` body (ADR-TG-02): `*Mock|*Fake|*Stub|*Spy` naming, `gomock.NewController` invocations, and types embedding `mock.Mock` (testify, recognised independent of struct name). `_GO_STACK_DEFAULTS` covers `net/http`, `net/url`, `os`, `os/exec`, `io`, `io/fs`, `database/sql`, `context`, plus major cloud / DB / AI SDK package paths.

## Improvements

- **`/gvm-build` self-review loop** — review passes mandatory; `Review passes: [(1, N1), (2, N2), ..., (final, 0)]` recorded in handover. Distinct from independent chunk review.
- **Cost-optimized model selection** (shared rule 22): Opus for deep reasoning, Sonnet for guided work, Haiku for HTML generation.
- **Selective expert loading**: domain specialists split into per-domain files, stack specialists into per-stack files. Loaded on activation signal, not at session start.
- **Expert citations in shared rules** (Fagan, Parnas, Deming, Norman, Fowler, Clements, Keeling, Redish).
- **`_PYTHON_STACK_DEFAULTS` runtime mirror complete (v2.1.1)** — extended from 5 to 11 entries, covering all 8 named TDD-2 external-boundary categories plus 3 high-frequency third-party SDKs. Closes the v2.1.0 known-issue where mocking `socket` / `subprocess` / `os` / `pathlib.Path` inside `[CONTRACT]` tests produced false-positive metz violations.
- **Branding file contract** — optional `branding/branding.md` for logo, header colours, font stack, accent colour. Body typography stays under design-system control.

## Fixes (v2.0.1)

- `_build_provenance(input_path)` rename to `input_paths: list[Path]` — closed post-rename call-site mismatch that crashed `--mode decompose`.
- `_candidates_comparison` reports unique-row counts, not (row, column) pair counts.
- `_privacy_scan` word-boundary hardening (`(?<!\w)token(?!\w)` regex replaces substring containment) — eliminates false-positive class on short categorical tokens.
- Empty-headlines fallback in `headline.select` — three descriptive headline kinds (`dataset_summary`, `completeness_summary`, `schema_summary`) surface when no threshold-firing candidate exists.
- Validate-mode comparison — `_shared/comparison.py` populates `findings.comparison.per_file_differences` and `file_vs_file_outliers`; comparison headline now surfaces.

## Known Limitations (carried in v2.2.0)

- TS detection does not handle multi-line `vi.mock(` declarations where the module string is on a continuation line (text-line heuristic, ADR-TG-03).
- Go test-function body extraction uses brace-depth counting that does not parse strings or comments. A `}` inside a string literal could misalign function bodies; documented limitation.
- Go conservative recall: a struct used as a fake but named without `*Mock|*Fake|*Stub|*Spy` and without testify's `mock.Mock` embed will not be detected. Practitioner workaround: rename or extend `.ebt-boundaries`.

## Experts and patterns grounding the work

Every rule added across v1.0.0 → v2.2.0 cites both an expert (or named pattern) and the defect class it addresses. The NFR-3 inclusion heuristic enforces this — if a rule has no defect class, it doesn't earn a changelog entry.

| Domain | Expert / pattern | What it grounds |
|---|---|---|
| Defect-class review panels | Laitenberger, Atkinson, Schlich & El Emam (Perspective-Based Reading, 2000) | Orthogonal scanning mandates — 41% more defects detected vs. checklist panels. Restructured all review skills at v1.0.0. |
| Capture-recapture estimation | Wohlin, Petersson & Aurum (Lincoln-Petersen) | After-R1 defect-population estimate — converts "should we run R2?" from a guess into a calculation. |
| Two-pass scanning | Drew, Võ & Wolfe (Satisfaction of Search, 2013) | Systematic scan + cross-reference scan — prevents premature termination after first find. |
| R1/R2 thresholds | Green & Swets (Signal Detection Theory, 1966) | Liberal R1 / strict R2+. |
| Outside-in TDD (TDD-1) | Freeman & Pryce — *Growing Object-Oriented Software, Guided by Tests* | Acceptance test as first deliverable; consumer demand precedes producer build. |
| Red-Green-Refactor | Beck | Both transitions recorded in handover. |
| Self-review loop discipline | Fagan — author preparation against inspection criteria | Per-deliverable self-review before independent review. |
| Mock budget (TDD-2) | Sandi Metz — *POODR* Ch. 9 | Mocks belong at object boundaries; budget = 1 at the network/process edge. |
| Internal-mock protocol drift | Freeman & Pryce — *GOOS* | Internal mocks hide the seam they pretend to verify (defect class for `mock-budget` violation kind, Panel B). |
| Realistic fixtures (TDD-3) | Bach & Bolton — *Rapid Software Testing* | Synthetic fixtures encode the engineer's mental model; realistic ones expose the gap. Six-domain catalogue. |
| Wiring matrix "Demanded by" | Michael Feathers — *Working Effectively with Legacy Code* | Consumer-side seam: every producer must name the demanding consumer. |
| Conceptual integrity | Fred Brooks — *The Mythical Man-Month* | One audit trail per built module; one canonical name per concept. |
| Impact mapping | Gojko Adzic — *Impact Mapping* | Four-level model (Goals → Actors → Impacts → Deliverables). |
| Outcome-first framing | Marty Cagan — *Inspired* | Goals stated as outcomes, not features. |
| Walking skeleton | Alistair Cockburn (skeleton metaphor); Freeman & Pryce (boundaries) | Wire every external boundary before feature work. |
| Architectural views | Paul Clements et al. — *Documenting Software Architectures* | C4 container scope; producer/consumer alignment. |
| Decision capture (ADR) | Michael Keeling — *Design It!* | Every architecturally significant decision carries an ADR. |
| Process discipline | W. Edwards Deming — *Out of the Crisis* | Variance reduction; review calibration. |
| Information hiding | David Parnas | Module boundary discipline; STUBS.md honesty register. |
| Refactoring | Martin Fowler — *Refactoring* | Intention-revealing names; no premature abstraction. |
| Designing for users | Don Norman — *The Design of Everyday Things* | Affordances; error tolerance in microcopy. |
| Writing for the web | Janice Redish — *Letting Go of the Words* | Task-oriented user docs; scannable structure. |
| Document writing | Doumont (structure-by-message), Minto (pyramid principle), Weinberg (reader's problem visible), Zinsser (clutter), Williams (clarity & grace), Orwell (politics of language), King (kill darlings) | All `/gvm-doc-write` and `/gvm-doc-review` output. |

## Defect classes the rules address

Every rule was added in response to a concrete defect observed in practice. The defect class is named in `methodology-changelog.md` per entry; below is the cross-release roll-up.

| Defect class | Source incident | Rule that addresses it |
|---|---|---|
| Unit-test-green / system-broken | Multiple chunks shipping with passing unit tests but broken end-to-end behaviour | TDD-1 outside-in ordering + Hard Gate 8 chunk-acceptance smoke (v2.1.0) |
| Internal-mock proliferation hides protocol drift | Multi-mock tests on internal classes silently passing | TDD-2 + Panel B `mock-budget` (v2.1.0 Python; v2.2.0 TS/Go) |
| Synthetic-fixture-only verification | Privacy scan tripped on real-world short categorical codes; clean ordinal data produced empty headlines — both shipped to production undetected by happy-path tests | TDD-3 catalogue + Panel C realistic-fixture mandate (v2.1.0) |
| Tracer-bullet engine boundary | Build phases produced isolated modules with green tests while no consumer chunk imported them | Wiring matrix + Hard Gates 6/7 (v2.0.0); inverse audit (v2.0.1) |
| Built-but-undemanded modules | Modules existed with passing unit tests but no entry-point consumer | "Demanded by" column (v2.1.0 GATE-2) |
| Unilateral triage by the executor | Review skill silently deferred Important findings and filtered Minor findings under cover of "R2+ strict criterion" | Shared rule 28 + Hard Gate 6/7 (v2.1.0) |
| TDD-2 runtime-mirror gap | v2.1.0 prose specified 8 boundary categories; runtime mirror covered only 5 — false-greens shipped on `socket`/`subprocess`/`os`/`pathlib.Path` mocks | `_PYTHON_STACK_DEFAULTS` extension to 11 entries (v2.1.1) |
| Methodology evolution had no audit trail | Practitioners couldn't tell why a rule existed or whether it was still earning its keep | NFR-3 methodology-changelog (v2.1.0) |
| Retroactive enforcement of new gates | Pre-release chunks would fail under v2.1.0 rules | NFR-1 carry-over via `_V2_1_0_RELEASE_DATE` constant (v2.1.0) |
| Silent prose drift away from runtime semantics | Carry-over rule was prose-only; paraphrase or section migration could rot the gate undetected | Structural tests anchoring on the canonical phrase (v2.1.1) |
| Rename without call-site update | Provenance helper renamed; stale call sites crashed one CLI mode | `/gvm-test` step 6c parametric flag smoke (v2.0.1) |
| Privacy-scan substring false-positives | Real-world short categorical tokens (M/F, A/B/O) tripped containment check | Word-boundary regex `(?<!\w)token(?!\w)` (v2.0.1) |

## Compatibility

Non-breaking across the v1.0.0 → v2.2.0 track. The methodology hardening makes some rules stricter — chunks built before `_V2_1_0_RELEASE_DATE = "2026-04-28"` are exempt from v2.1.0 gates as "v2.0.x carry-over" (per NFR-1).

## Closed Known Issues

| Source | Issue | Closed in |
|---|---|---|
| v2.0.0 | Empty-headlines on clean-data runs | v2.0.1 |
| v2.0.0 | `--mode decompose` TypeError on multi-file input | v2.0.1 |
| v2.0.0 | Privacy-scan substring false-positives on short tokens | v2.0.1 |
| v2.1.0 | `_PYTHON_STACK_DEFAULTS` runtime mirror partial (5 of 8 categories) | v2.1.1 |
| v2.1.0 | Hard Gate 8 carry-over runtime mtime structural test owed | v2.1.1 |
| v2.1.x | TS mock-budget detection not yet wired | v2.2.0 |
| v2.1.x | Go mock-budget detection not yet wired | v2.2.0 |
| v2.1.x | `_lint_typescript.seam_allowlist` / `_lint_go.seam_allowlist` STUBS.md entries | v2.2.0 |
