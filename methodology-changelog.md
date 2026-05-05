# GVM Methodology Changelog

This file records every behaviour-changing methodology evolution with mandatory rule reference, defect class addressed, and validation method. Typo / formatting / comment-only edits are NOT entries here — git history covers those.

**Methodology-changelog inclusion heuristic (NFR-3):** "if a chunk that was acceptable yesterday would be refused today (or vice versa), it's a changelog entry." Without rationale, future readers can't tell why the rule exists; without defect-class, they can't tell if the rule's still earning its keep.

---

## v2.2.0 — 2026-04-30

### Added

- `/gvm-tech-spec` Phase 5 MVP-1 (MVP-first ordering, where MVP = Minimum Viable Product) — the first user-facing chunk in the implementation guide MUST constitute the smallest end-to-end shippable slice exercising one user-visible behaviour through every layer it touches; subsequent chunks add slices, not layers. Refusal rule fires at impl-guide write time when the first user-facing chunk is a layer fragment AND no exemption marker is present. Four named exemption categories (`library`, `refactor`, `performance-driven`, `fully-specified`) claim exemption via the literal in-guide form `MVP-1 exempted: <category> — rationale: <why>` in the Build Phases section header. An exemption with no rationale is treated as no exemption (Fagan: silent skips are not skips). A non-gated design-intent paragraph sits beneath the refusal rule directing practitioners to optimise chunk *sequencing* for the earliest runnable MVP — position is not gated because that would force exemption inflation on legitimate infrastructure-first cases (data migration, auth bootstrapping, regulatory setup). A second non-gated paragraph clarifies that MVP-1 governs the *delivery sequence* while the cross-cutting spec (Phase 2) and architecture overview (Phase 4) govern the *patterns* every slice is built against — Brooks's conceptual integrity. Slice-local architecture divergence is a code-review finding regardless of whether each slice individually shipped a green smoke gate.
  - Rule reference: MVP-1 (introduced under Cohn vertical-slicing heading in `/gvm-tech-spec` Phase 5 item 2)
  - Defect class addressed: layer-first ordering that defers user-visible feedback to integration time. A build that produces "all data-model chunks → all service chunks → all UI chunks" can ship green tests across every layer and still discover at integration time that the layers do not compose into the product the user wanted. The MVP-first ordering puts a thin end-to-end slice in front of the user as soon as possible — the same Cohn vertical-slicing argument applied to phase ordering rather than chunk decomposition. Without this rule, vertical slicing applies WITHIN chunks but the IMPL GUIDE could still order chunks layer-first with no gate refusing it.
  - Validation: structural grep test (TC-MVP-1-NN) asserts the SKILL.md prose carries the rule, the four named exemption categories, the `MVP-1 exempted:` literal marker form, and the refusal rule; second test asserts `/gvm-build` Hard Gate 9 names MVP-1 as the read-side mirror.

- `/gvm-build` Hard Gate 9 (MVP-1 read-side mirror) — verifies the first user-facing chunk satisfies (a) runnable end-to-end slice with acceptance test against walking-skeleton boundaries, OR (b) literal `MVP-1 exempted: <category> — rationale: <why>` marker present with one of the four named categories. Refusal blocks chunk-prompt generation when neither holds. The two gates (tech-spec write-side, build read-side) compose: an impl guide that bypasses one is caught by the other.
  - Rule reference: MVP-1 (read-side mirror)
  - Defect class addressed: implementation guides authored before MVP-1 was added, or impl guides that paraphrased the rule away, would otherwise reach `/gvm-build` without the discipline. Hard Gate 9 catches the gap at the consumer side.
  - Validation: structural grep test asserts Hard Gate 9 prose carries the four exemption categories, the literal marker form, and the refusal-rule semantics. Carry-over exemption: impl guides authored before MVP-1's release date are exempt via the existing NFR-1 mtime mechanism (keyed off the v2.2.0 release-date constant when wired).

- TS mock-budget detection in `_ebt_contract_lint._lint_typescript`. New `_TS_STACK_DEFAULTS` external-boundary allowlist (node:* builtins, axios/undici/got/ky/node-fetch, pg/mongodb/redis, AWS/Google/Stripe/Anthropic/OpenAI SDKs); new `_TS_MOCK_TARGET_PATTERNS` recognises `vi.mock`, `jest.mock`, `jest.spyOn`, `vi.spyOn`, `td.replace`, `sinon.stub`, `sinon.replace`. Internal mocks emit `mock-budget` Important; matches in `.cross-chunk-seams` escalate to Critical (ADR-MH-03 parity). Wrapper-as-SUT exemption (ADR-MH-02) implemented via test-file-stem == target-basename equality.
  - Rule reference: REVIEW-1 (Panel B picks up mock-budget violations) extended from Python-only to TS.
  - Defect class addressed: TS test files mocking internal services were silently passing Panel B with no `mock-budget` finding. The protocol drift the rule exists to surface (Freeman & Pryce GOOS) was undetectable on TS projects.
  - Validation: 5 new TC-TDD-2-NN acceptance tests in `test_ebt_contract_lint.py` (12: axios-only=0; 13: internal mock=1 Important; 14: seam_allowlist→Critical; 15: spyOn realistic-fixture variant; 16: wrapper-as-SUT exempt) + 1 structural test on the allowlist constant.

- Go mock-budget detection in `_ebt_contract_lint._lint_go`. New `_GO_STACK_DEFAULTS` external-boundary allowlist (net/http, os, io, database/sql, context, plus AWS/Google/Anthropic/OpenAI/Redis/MongoDB/Postgres SDKs). Go's idiom is interface substitution, not module-level mocking — `_detect_mock_budget_go` counts distinct test-double instances per `func TestXxx(t *testing.T)` body via three orthogonal signals (ADR-TG-02): (a) types matching `*Mock|*Fake|*Stub|*Spy` instantiated as struct literals; (b) `gomock.NewController` invocations (each counts as one); (c) types embedding `mock.Mock` (testify) — registered via `_collect_testify_types` so naming-convention isn't required. Severity escalation via `seam_allowlist` mirrors Python and TS.
  - Rule reference: REVIEW-1 (Panel B picks up mock-budget violations) extended from Python-only to Go.
  - Defect class addressed: Go test files using interface-substituted fakes for internal collaborators were silently passing Panel B. The same Freeman & Pryce protocol-drift defect class as TS, with a different code-shape signal because Go's mocking idiom differs.
  - Validation: 5 new TC-TDD-2-NN acceptance tests (17: boundary fake=0; 18: internal=1 Important; 19: seam_allowlist→Critical; 20: gomock controller + struct fake=2; 21: testify mock.Mock embed) + 1 structural test on the allowlist constant. Combined suite 74→86.

### Changed

- `_lint_go` rainsberger pass restructured. Was a function-level early-return when `net/http` is not imported; now an inner conditional so the mock-budget pass runs unconditionally. Behaviour-equivalent for files that import `net/http` (the rainsberger pass still runs); behaviour-changing for files that do not (mock-budget now runs; previously the function returned `[]`).
  - Defect class addressed: a Go test file with internal fakes but no `net/http` import would have silently passed Panel B even after P29-C02's mock-budget addition, because the function returned early before reaching it.

### Retired

- `STUBS.md` entries `_lint_typescript.seam_allowlist` and `_lint_go.seam_allowlist` (forward-compat parameters since v2.1.0) — both stubs retired as the parameters now flow through to live mock-budget severity escalation in their respective stacks.

---

## v2.1.1 — 2026-04-30

### Changed

- `_PYTHON_STACK_DEFAULTS` in `_ebt_contract_lint.py` extended from 5 entries to 11. The runtime mirror now covers all 8 named TDD-2 external-boundary categories (`requests`, `httpx`, `urllib`, `aiohttp`, `socket`, `pathlib.Path`, `subprocess`, `os`) plus 3 third-party SDKs (`psycopg2`, `sqlalchemy.engine`, `boto3`).
  - Defect class addressed: TDD-2 runtime-mirror gap — v2.1.0 SKILL.md prose specified 8 external-boundary categories but the runtime mirror in `_ebt_contract_lint._PYTHON_STACK_DEFAULTS` covered only 3 of the 8 named categories (plus 2 third-party SDKs). False-greens shipped for tests that mocked `socket`/`subprocess`/`os`/`pathlib.Path` inside `[CONTRACT]` tests. Distinct from the existing TC-TDD-2-02..05 tests which already cover mock-count / internal-class-mock / wrapper-as-SUT / seam-escalation semantics.
  - Validation: 6 new boundary-mocking tests in `test_ebt_contract_lint.py` (`test_stack_defaults_{module}_*`), one per newly-covered category. Each asserts `violations == []` (full-zero contract — pins the boundary-mocking behaviour rather than just one of three possible kinds, per R59 I1). Lint suite green (33/33 after the chunk, was 27 before).

### Added

- TC-NFR-1-01 / TC-NFR-1-03 structural tests — guard the SKILL.md prose that specifies the Hard Gate 8 carry-over runtime check. `test_tc_nfr_1_01_hard_gate_8_names_mtime_comparison` asserts the carry-over procedure paragraph (anchored on `**Carry-over exemption (NFR-1):**`) co-locates `mtime`, `_V2_1_0_RELEASE_DATE`, and the `build/prompts/` path pattern — not merely that the tokens exist somewhere in the file. `test_tc_nfr_1_03_exemption_phrase_is_literal` asserts the literal `"v2.0.x carry-over"` phrase appears in BOTH the Hard Gate 8 section AND the handover template fenced block.
  - Defect class addressed: silent prose drift away from the runtime semantics the executor is expected to apply (the carry-over rule is enforced by the executor reading SKILL.md prose; without structural tests guarding the prose, a paraphrase or migration to an unrelated section could rot the gate undetected)
  - Validation: 2 new tests in `test_methodology_hardening_v2_1_0.py`; structural suite green (41/41 after the chunk, was 39 before). Combined run (lint suite + structural suite): 74/74, was 66 at v2.1.0 release.

---

## v2.1.0 — 2026-04-28

### Changed

- `/gvm-build` Hard Gate 5 reordered (TDD-1) — outside-in acceptance test is the first deliverable in the chunk's TDD Approach for user-facing chunks; pure-internal-helper exemption via `TDD-1 exempted: <reason>` per ADR-MH-04.
  - Defect class addressed: unit-test-green / system-broken (six v2.0.0 defects where chunks shipped passing unit tests with broken end-to-end behaviour)
  - Validation: TC-TDD-1-01, TC-TDD-1-02, TC-TDD-1-04 (TC-TDD-1-03 deferred to P26-C02 — Panel B integration); chunk handover records Red→Green transition on the acceptance test.

### Added

- `/gvm-build` Hard Gate 8 (GATE-1) — chunk-level acceptance smoke gate. The smoke command exercises the chunk's user-facing surface end-to-end and asserts structural contracts before the handover is written. Refusal blocks the handover when exit code is non-zero. NFR-1 carry-over exemption keyed off `_V2_1_0_RELEASE_DATE = "2026-04-28"`.
  - Defect class addressed: chunk-completion smoke gap (chunks shipped with green unit tests but no end-to-end check)
  - Validation: TC-GATE-1-01 through TC-GATE-1-05; smoke exit code recorded in handover.

- `/gvm-build` § TDD-2 — mock budget at the external boundary. Each test mocks at most one collaborator, only at the network/process edge. Eight named external-boundary categories plus third-party SDK rule. Wrapper-as-SUT exemption per ADR-MH-02. Severity escalation per ADR-MH-03 — default Important, escalates Critical when mock target is in `.cross-chunk-seams` allowlist.
  - Defect class addressed: internal-mock proliferation hiding integration seams (Metz POODR Ch. 9; Freeman & Pryce GOOS protocol drift)
  - Validation: TC-TDD-2-01 (P25-C03 acceptance); `_ebt_contract_lint.py` runtime authority emits `mock-budget` LintViolation kind. TC-TDD-2-02..05 deferred to a v2.1.x hardening pass once `_PYTHON_STACK_DEFAULTS` mirrors all eight named external-boundary categories.

- `/gvm-build` § TDD-3 — realistic-fixture catalogue. Six named domains (data-analysis, web/UI, API, parsing, security validation, concurrency) with starter fixture shapes per domain. Practitioner override via `realistic-fixture-not-applicable: <rationale>` tag in the handover. `/gvm-code-review` Panel C (REVIEW-2) names three of the six inline (data-analysis, parsing, security validation) — the highest-ROI subset where defect-class evidence is concrete — and forward-points to this catalogue for the other three.
  - Defect class addressed: synthetic-fixture-only verification (defect S6.1: short categorical codes; defect 3a: clean ordinal data — both shipped to production undetected by happy-path tests)
  - Validation: TC-TDD-3-01, TC-TDD-3-02, TC-TDD-3-03; structural grep against `/gvm-build` SKILL.md prose.

- `/gvm-tech-spec` Hard Gate 6 fourth column "Demanded by" (GATE-2) — wiring-matrix entries must declare which consumer demands the producer module, or carry an explicit `internal helper, no consumer demanded — rationale: ...` exemption row. Refusal rule fires on empty cells.
  - Defect class addressed: declared-but-undemanded modules surviving past phase completion (Freeman & Pryce GOOS — consumer demand precedes producer build)
  - Validation: TC-GATE-2-01 through TC-GATE-2-03; structural grep against `/gvm-tech-spec` SKILL.md prose.

- `/gvm-code-review` Panel B mock-budget integration (REVIEW-1) — Panel B prose names the new `mock-budget` violation kind alongside `rainsberger` / `metz`, runs the EBT contract/collaboration lint on every test file in the chunk diff (not only `[CONTRACT]`-tagged), names the `.cross-chunk-seams` allowlist for ADR-MH-03 severity escalation.
  - Defect class addressed: review-time blind spot for internal-mock proliferation (Panel B previously only inspected `[CONTRACT]`-tagged tests)
  - Validation: TC-REVIEW-1-01 through TC-REVIEW-1-03; structural grep against `/gvm-code-review` SKILL.md Panel B prose.

- `/gvm-code-review` Panel C realistic-fixture mandate (REVIEW-2) — Panel C prose names three known-edge-shape domains (data-analysis, parsing, security validation) with starter fixture shapes, emits an Important finding when a chunk in such a domain ships without a realistic-fixture variant, names the `realistic-fixture-not-applicable` override marker.
  - Defect class addressed: review-time blind spot for synthetic-fixture-only chunks
  - Validation: TC-REVIEW-2-01, TC-REVIEW-2-02; structural grep against `/gvm-code-review` SKILL.md Panel C prose.

- `_V2_1_0_RELEASE_DATE` constant (NFR-1) — declared in `/gvm-build` SKILL.md Release Constants section. Hard Gate 8 reads it for the carry-over exemption mtime check. Distributed self-versioning: future major releases add their own `_V{MAJOR}_{MINOR}_{PATCH}_RELEASE_DATE` constants co-located with the gates that read them.
  - Defect class addressed: retroactive enforcement of new gates against pre-release chunks (would force shippable v2.0.x chunks into v2.1.0 refusal)
  - Validation: TC-NFR-1-02 (constant declaration + carry-over rule); structural grep against `/gvm-build` SKILL.md Release Constants section. TC-NFR-1-01 / TC-NFR-1-03 deferred to v2.1.x — runtime mtime-comparison enforcement is asserted in prose, not yet exercised by a structural test.

- NFR-2 diff-budget tracking — handover template carries `Diff budget delta` field (signed integer, regex-matched wire format). Build summary aggregates per-chunk values into a cumulative running total. Surface-and-track per ADR-CC-03; not a refusal gate.
  - Defect class addressed: SKILL.md prose creep across release tracks (no upper bound on cumulative documentation churn)
  - Validation: TC-NFR-2-01, TC-NFR-2-02; cumulative ≤ 500 for v2.1.0 SKILL.md additions verified via `git diff v2.0.1..HEAD --stat -- '*SKILL.md'`.

- `methodology-changelog.md` (NFR-3) — new file at project root. Each release entry carries rule reference + defect class addressed + validation method per spec § Component 5. `/gvm-status` reads the most recent dated entry and surfaces it in a "Methodology" section. Inclusion heuristic documented in `/gvm-deploy` SKILL.md.
  - Defect class addressed: methodology evolution had no audit trail — practitioners could not tell why a rule existed or whether it was still earning its keep
  - Validation: TC-NFR-3-01 through TC-NFR-3-03; structural grep verifies three dated section headers, inclusion heuristic in SKILL.md, `/gvm-status` read-side prose.

- shared rule 28 — Review Finding Triage Is User-Owned. Added to `shared-rules.md`; enforced via Hard Gate 6 in `/gvm-code-review` and `/gvm-design-review`, Hard Gate 7 in `/gvm-doc-review`. Every Critical or Important finding emitted by review panels MUST be presented to the user before any disposition is recorded. Forbidden patterns (canonical, verbatim across all three skills): recording emitted findings as "filtered under strict criterion" without user input; recording emitted findings as "deferred to v{N}.{M}.{P} hardening" without user input; bundling the verdict with the user's first sight of the finding list; presenting a summary count that hides which findings were deferred (zero-deferred runs are exempt). A "fix all" authorisation does not extend to new Critical findings discovered during the fix — those re-enter triage.
  - Defect class addressed: unilateral triage by the executor (R55 incident: the skill deferred 2 Important findings and filtered 10 Minor findings without user input under cover of "R2+ strict criterion" — converting the panels' emit threshold into a post-synthesis filter)
  - Validation: structural grep tests `test_r28_code_review_hard_gate_names_forbidden_patterns`, `test_r28_design_review_names_rule_28`, `test_r28_doc_review_names_rule_28` enforce that each review skill's Hard Gate names rule 28, the literal phrase "USER OWNS FINDING TRIAGE", and the canonical forbidden-pattern phrases verbatim — preventing silent removal or paraphrase of the gate.

---

## v2.0.1 — 2026-04-28

### Added

- `/gvm-build` Hard Gate 7 inverse audit (P20-C02) — every built `_shared/*.py` module must appear in the wiring matrix or in `.module-allowlist`.
  - Defect class addressed: built-but-unwired module (chart producer P19, aggregation P20 — modules existed with passing unit tests but had no entry-point consumer)
  - Validation: `_module_audit.audit(project_root)` returns empty error list on phase completion; non-zero exit blocks phase completion.

- `/gvm-test` step 6c — CLI Product Smoke parametric over CLI flag values, with structural HTML/JSON contract assertions and real-world fixture variants (including short categorical tokens).
  - Defect class addressed: synthetic-fixture-only verification (defect S6.1 — privacy scan tripped on real-world short categorical codes)
  - Validation: `/gvm-test` Hard Gate 5 verdict in test-008 confirmed Ship-ready with parametric smoke against four `--mode` values.

- `/gvm-explore-test` data-tour patterns — engine-untuned shapes, realistic short-token cases, mode × data-shape combinations, boundary inputs without context.
  - Defect class addressed: practitioner mental-model gaps in exploratory charters
  - Validation: charter prose review confirms each pattern is exercised when the domain has known edge-shape risk.

- `/gvm-status` verdict-aware reporting — reads the highest-numbered `test-*.html`, extracts the verdict from `.verdict-text`, surfaces it with a chain status line `build → code-review → test`.
  - Defect class addressed: "is this shippable?" required hunting through review reports
  - Validation: `/gvm-status` output prominently shows verdict immediately after pipeline state.

### Fixed

- `_build_provenance(input_paths: list[Path])` — closed the post-rename call-site mismatch that crashed `--mode decompose`.
  - Defect class addressed: rename without call-site update
  - Validation: pytest re-run after rename in P20-C01 handover.

---

## v2.0.0 — 2026-04-27

### Added

- `/gvm-tech-spec` Hard Gate 6 — wiring matrix mandatory in implementation guide. Refusal rule blocks impl-guide write when any `_shared/*` module has no consumer chunk.
  - Defect class addressed: build phases produce isolated modules with green tests while no chunk owns the entry-point body that connects them
  - Validation: structural inspection of impl guide confirms wiring matrix presence and no empty wiring-chunk cells.

- `/gvm-build` Hard Gates 6 + 7 — Gate 6 reads the wiring matrix at phase start; Gate 7 mechanically greps each entry-point file for import + call site of every named module. Acceptance is by code, not by the chunk's claim.
  - Defect class addressed: tracer-bullet engine boundary (Phase 3/4 chunks build modules with green isolated tests but Phase-N consumer chunk never imports them)
  - Validation: per-`(entry_point, module)` pair, `grep -E "import .*{module}"` and `grep -E "{module}\.\w+\("` both return ≥1 hit on the entry-point file.

- `/gvm-impact-map` (new skill) — produces `impact-map.md` (four flat tables: Goals, Actors, Impacts, Deliverables). Downstream `/gvm-requirements` Phase 5 (IM-4 trace gate) refuses to finalise any requirement that doesn't trace to a leaf Deliverable.
  - Defect class addressed: requirements without traceable business outcome
  - Validation: `_im4_check.check(...)` returns empty error list at Phase 5 finalisation.

- `/gvm-walking-skeleton` (new skill) — produces a runnable skeleton exercising every external boundary with real or sandbox calls, plus `boundaries.md` registry. Downstream `/gvm-build` WS-5 refuses chunks if the skeleton is red in CI.
  - Defect class addressed: integration failures surface at month 6 instead of hour 1
  - Validation: WS-5 status gate refuses chunk on `result == "failed"`; sidecar audit trail readable by `/gvm-test`.

- `/gvm-explore-test` (new skill) — practitioner-driven exploratory testing skill with timeboxed YAML charter, `AskUserQuestion`-driven defect intake. Downstream `/gvm-test` VV-4(d) audits sandbox-divergence notes.
  - Defect class addressed: exploratory testing missing from the build-verification chain
  - Validation: `/gvm-test` reads `test/explore-NNN.md` and surfaces practitioner-classified severity findings.

- Code review three-verdict taxonomy (Ship-ready / Demo-ready / Not shippable, honesty-triad ADR-105) — emitted by `gvm_verdict.evaluate(inputs)` as a finite state, never as text concatenation.
  - Defect class addressed: ambiguous "Pass with gaps" verdict across rounds
  - Validation: `Verdict` enum has exactly three members; evaluator returns one of them deterministically.

---
