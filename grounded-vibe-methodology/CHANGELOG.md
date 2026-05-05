# Changelog

## [v2.2.0] — 2026-04-30

### Added — methodology
- **MVP-1 (Minimum Viable Product first ordering).** New rule: chunk sequence must build a thin end-to-end vertical slice first, then add slices; horizontal architecture stays consistent across slices.
  - `/gvm-tech-spec` Phase 5 chunk decomposition — refusal at impl-guide write time.
  - `/gvm-build` Hard Gate 9 — read-side mirror; refusal at impl-guide read time.
  - `/gvm-design-review` Panel D Pass 3 — flags designs that structurally prevent MVP-1.
  - `/gvm-walking-skeleton` SKILL.md — new Key Rule naming MVP-1 as the sequencing rule the skeleton enables.
  - Four exempted project shapes (`library`, `refactor`, `performance-driven`, `fully-specified`) declared via the literal handover marker `MVP-1 exempted: <category> — rationale: <why>`; override without rationale does not count.

### Added — lint engine
- **TS mock-budget detection** in `_ebt_contract_lint._lint_typescript` (P29-C01). `_TS_STACK_DEFAULTS` external-boundary allowlist (node:* builtins, axios/undici/got/ky/node-fetch, pg/mongodb/redis, AWS/Google/Stripe/Anthropic/OpenAI SDKs); `_TS_MOCK_TARGET_PATTERNS` covers `vi.mock`, `jest.mock`, `jest.spyOn`, `vi.spyOn`, `td.replace`, `sinon.stub`, `sinon.replace`. Internal mocks emit `mock-budget` Important; matches in `.cross-chunk-seams` escalate to Critical (ADR-MH-03 parity). Wrapper-as-SUT exemption fires when test-file stem equals mocked target's basename.
- **Go mock-budget detection** in `_ebt_contract_lint._lint_go` (P29-C02). Counts distinct test-double instances per `func TestXxx(t *testing.T)` body via three signals (ADR-TG-02): `*Mock|*Fake|*Stub|*Spy` naming convention, `gomock.NewController` invocations, and types embedding `mock.Mock` (testify, recognised independent of naming via `_collect_testify_types`). `_GO_STACK_DEFAULTS` covers `net/http`, `net/url`, `os`, `os/exec`, `io`, `io/fs`, `database/sql`, `context`, plus major cloud / DB / AI SDK package paths.

### Changed
- `_lint_go` rainsberger pass restructured. The `net/http` import check is now an inner conditional rather than a function-level early return, so the mock-budget pass runs unconditionally regardless of whether the test file imports `net/http`.

### Retired
- `STUBS.md` entries `_lint_typescript.seam_allowlist` and `_lint_go.seam_allowlist` (forward-compat parameters since v2.1.0) — both retired as the parameters now flow through to live mock-budget severity escalation.

### Quality
- Lint suite (`test_ebt_contract_lint.py`): 45 tests pass (was 33; +10 TC-TDD-2-12..21 acceptance tests + 2 structural tests for the TS/Go allowlist constants).
- Combined run (lint + structural): 86/86, was 74 at v2.1.1.
- All review findings closed via practitioner-authorised "fix all". Independent review converged at 0 Critical / 0 Important by pass 3 on each chunk.

### Closes from v2.1.x Known Issues
- The TS/Go `seam_allowlist` forward-compat stubs and the underlying mock-budget detection gap — both closed.

### Known limitations
- TS multi-line `vi.mock(` declarations are not parsed (text-line heuristic limitation, ADR-TG-03).
- Go brace-depth counter does not parse strings or comments (a `}` inside a string literal could misalign function bodies; documented limitation).
- Go conservative recall: structs used as fakes without `*Mock|*Fake|*Stub|*Spy` naming and without testify `mock.Mock` embed are not detected. Practitioner workaround: rename or extend `.ebt-boundaries`.

## [v2.1.1] — 2026-04-30

### Fixed
- **TDD-2 runtime-mirror gap closed.** `_PYTHON_STACK_DEFAULTS` extended from 5 to 11 entries. Runtime mirror now covers all 8 named TDD-2 external-boundary categories plus 3 high-frequency third-party SDKs. Closes the v2.1.0 known-issue where mocking `socket`/`subprocess`/`os`/`pathlib.Path` inside `[CONTRACT]` tests produced false-positive metz violations. Distinct from the existing TC-TDD-2-02..05 tests, which already cover mock-count / internal-class-mock / wrapper-as-SUT / seam-escalation — those concerns are unrelated to the runtime mirror.
- **TC-NFR-1-01 / TC-NFR-1-03 structural tests added.** Guard the Hard Gate 8 carry-over runtime semantics against silent prose drift. The new tests anchor on the `**Carry-over exemption (NFR-1):**` paragraph (TC-NFR-1-01) and the handover template fenced block (TC-NFR-1-03) — not whole-file substring checks — so a paraphrase or section migration is detected.

### Quality
- Lint suite (`test_ebt_contract_lint.py`): 33 tests pass (was 27; +6 new boundary-mocking tests).
- Structural suite (`test_methodology_hardening_v2_1_0.py`): 41 tests pass (was 39; +2 new NFR-1 tests).
- Combined run: 74/74, was 66 at v2.1.0 release.
- TDD-1 exempted: pure internal helper / test module changes (ADR-MH-04).

### Closes from v2.1.0 Known Issues
- The "TDD-2 runtime-mirror partial" known issue (covered 5 of 8 named categories at v2.1.0 ship time) — closed by the `_PYTHON_STACK_DEFAULTS` extension above.
- The "Hard Gate 8 carry-over runtime mtime test" deferred from v2.1.0 — closed by the two new structural tests above.

### Known issues
- TS/Go `seam_allowlist` runtime wiring remains outstanding — gated by TS/Go mock-budget detection, which is genuine new design work and warrants a separate `/gvm-tech-spec` → `/gvm-build` cycle.

## [v2.1.0] — 2026-04-30

### Added — methodology hardening
- **Hard Gate 8 (NFR-1 / GATE-1)** — `/gvm-build` chunk-level acceptance smoke gate. Refuses the handover when smoke exit code is non-zero. NFR-1 carry-over exemption keyed off `_V2_1_0_RELEASE_DATE = "2026-04-28"`. ADR-MH-04 internal-helper exemption.
- **TDD-1 outside-in ordering** — `/gvm-build` Hard Gate 5 reorder: outside-in acceptance test is the first deliverable for user-facing chunks. Pure-internal-helper exemption via `TDD-1 exempted: <reason>` marker; blank reason treated as no exemption.
- **TDD-2 mock budget at the external boundary** — eight named external-boundary categories plus third-party SDK rule. Wrapper-as-SUT exemption (ADR-MH-02). Severity escalation (ADR-MH-03) — opt-in via `.cross-chunk-seams` allowlist; default Important, escalates Critical when target is listed.
- **TDD-3 realistic-fixture catalogue** — six named domains (data-analysis, web/UI, API, parsing, security validation, concurrency) with starter fixture shapes. Practitioner override via `realistic-fixture-not-applicable: <rationale>` in the handover.
- **Hard Gate 6 / GATE-2** — `/gvm-tech-spec` wiring matrix gains "Demanded by" fourth column; refusal on empty cells; explicit exemption row format for legitimate internal helpers.
- **REVIEW-1** — `/gvm-code-review` Panel B integrates `mock-budget` violation kind alongside `rainsberger` / `metz`; runs on every test file (not only `[CONTRACT]`-tagged); names `.cross-chunk-seams` for severity escalation.
- **REVIEW-2** — `/gvm-code-review` Panel C realistic-fixture mandate; emits Important finding for chunks in data-analysis / parsing / security-validation domains shipping without realistic-fixture variant; names `realistic-fixture-not-applicable` override marker.
- **NFR-2 diff-budget tracking** — handover template `Diff budget delta` field; build-summary cumulative aggregation; user prompt at 500-LOC crossing per ADR-CC-03 (surface-and-track, not refusal gate).
- **NFR-3 methodology-changelog** — new `methodology-changelog.md` at project root; rule reference + defect class + validation method per entry; `/gvm-status` reads most recent dated entry; inclusion heuristic in `/gvm-deploy`.
- **shared rule 28** — Review Finding Triage Is User-Owned. Hard Gate 6 in `/gvm-code-review` and `/gvm-design-review`; Hard Gate 7 in `/gvm-doc-review`. Forbidden patterns canonical and verbatim; structural tests guard against silent removal or paraphrase.
- **Forward-compat parameters** — `_lint_typescript.seam_allowlist` and `_lint_go.seam_allowlist` registered in STUBS.md (expiry 2026-12-31); accepted and silently dropped today; Python escalation is the v2.1.0 runtime authority.

### Changed
- `/gvm-build` Hard Gate 5 reordered to put outside-in acceptance test first for user-facing chunks (TDD-1).

### Quality
- 66/66 structural tests pass (was 36 pre-hardening; +30 across the v2.1.0 chunks, including 3 self-policing rule-28 tests).
- Code review R56: **Merge** (8.5) — 17 findings closed via "fix all".
- Test verification test-009: **Ship-ready** (9.0).
- Doc review R58: **Proceed** (8.5).

### Known issues
- TC-TDD-2-02 through TC-TDD-2-05 deferred to v2.1.x — `_PYTHON_STACK_DEFAULTS` is a partial runtime mirror (covers `requests`, `httpx`, `psycopg2`, `sqlalchemy.engine`, `boto3`); the named categories `urllib`, `aiohttp`, `socket`, `pathlib.Path`, `subprocess`, `os` are spec'd but not yet enforced at runtime.
- TC-NFR-1-01 / TC-NFR-1-03 deferred — Hard Gate 8 carry-over runtime mtime-comparison is asserted in prose; structural test for the runtime path is owed.

## [v2.0.1] — 2026-04-28

### Added — gvm-analysis post-v2.0.0 fixes
- **P20-C01** — `_shared/aggregation.py` wired into `analyse.main`. Multi-file `--input` (action='append') with `concat` strategy. New `--sheet` flag for explicit multi-sheet xlsx selection. Per-input SHA-256 in `provenance.input_files`.
- **P21-C01** — Empty-headlines fallback in `headline.select`. Three descriptive headline kinds (`dataset_summary`, `completeness_summary`, `schema_summary`) surface when no threshold-firing candidate exists. Factual, not interpretative.
- **P21-C02** — Question templates for the three new headline kinds. Real `supporting_finding_id` values on clean-data runs. Fixed pre-existing `shap`-in-`shape` jargon collision in padding entries.
- **P21-C03** — `_shared/comparison.py` for validate-mode baseline-vs-current delta surfacing. `findings.comparison` populates with `per_file_differences` + `file_vs_file_outliers`. Comparison headline now surfaces.
- **P22-C01** — `_privacy_scan` word-boundary hardening. `(?<!\w)token(?!\w)` regex replaces substring containment. Eliminates false-positive class on short categorical tokens.

### Added — methodology hardening
- **P20-C02** — `/gvm-build` Hard Gate 7 mechanical "every built module is matrix-tracked" check via `_module_audit.py`. Catches the inverse failure mode of the existing row-grep audit.
- `/gvm-test` step 6c (CLI Product Smoke) — parametric over CLI flags, structural HTML/JSON contracts, real-world fixture variants.
- `/gvm-explore-test` — data-tour patterns documenting engine-untuned shapes, short-token cases, mode × data-shape combinations, boundary inputs.
- `/gvm-status` — verdict-aware reporting; reads latest `test-*.html` verdict and surfaces it with a chain status line.

### Fixed
- `_build_provenance(input_path)` rename to `input_paths: list[Path]` — closed the post-rename call-site mismatch that crashed `--mode decompose`.
- `_candidates_comparison` now reports unique-row counts, not (row, column) pair counts.
- Three test sites in `test_analyse.py` updated for the renamed `_build_provenance` parameter.

### Quality
- 1111 tests pass (was 1037 at v2.0.0 release; +74 new across the seven v2.0.1 chunks).
- Code review R50: Merge (P19 + R50 fixes); build-time independent review loops documented per chunk for P20–P22 work.
- Test verification test-008: Ship-ready (verdict-aware reporting confirms).

## [v2.0.0] — 2026-04-27

### Added — New skills (post-v1.0.0)

Four skills shipped after v1.0.0. None of them existed in the v1.0.0 release.

- **`/gvm-impact-map`** — discovery skill that produces an `impact-map.md` artefact (four flat tables: Goals, Actors, Impacts, Deliverables, linked by parent-ID columns). Adzic's impact-mapping model with Cagan's outcome-first framing. Goals pass an ambiguity-verb scan; foreign-key validator across all four levels. Downstream `/gvm-requirements` Phase 5 (IM-4 gate) refuses to finalise any requirement that doesn't trace to a leaf Deliverable.
- **`/gvm-walking-skeleton`** — discovery + scaffolding skill that produces a runnable skeleton exercising every external boundary (HTTP, DB, cloud SDK, filesystem, subprocess, email) through real or sandbox calls, plus a project-root `boundaries.md` registry. Surfaces integration failure modes at hour 1 instead of month 6. Downstream `/gvm-build` WS-5 refuses chunks if the skeleton is red in CI; `/gvm-test` VV-4(d) audits sandbox-divergence notes.
- **`/gvm-explore-test`** — practitioner-driven exploratory testing skill. Writes a YAML charter (mission, tour, scope, duration), times the session, captures defects through `AskUserQuestion`-driven prompts (severity, Given/When/Then, reproduction). Severity is the practitioner's call — the skill never auto-classifies. Produces paired `test/explore-NNN.md` + `.html` that `/gvm-test` reads via VV-4(d).
- **`/gvm-analysis`** — privacy-preserving exploratory data analysis. Claude orchestrates a Python engine that reads any CSV / TSV / xlsx / parquet / JSON file, produces real per-column statistics with bootstrap CIs, outliers, time-series, drivers (Decompose / Validate / Run-everything modes), privacy-safe duplicate summary, deterministic comprehension-question synthesis, full provenance per ADR-202 — the decision record governing deterministic seed derivation — covering SHA-256, library versions, and the resolved seed, **and rendered SVG charts** (per-column histograms and boxplots, outlier scatters, driver bar charts, time-series lines and decompositions) referenced from the report HTML via `<figure>` blocks. Chart producer failures degrade gracefully per ADR-201: the chart path stays null, a `chart_render_failed: kind=<canonical>, ...` warning is appended to provenance, and the run never crashes. Raw rows never enter Claude's context. Standalone skill (not part of the build pipeline).

### Added — gvm-analysis Ship-ready

- **gvm-analysis** skill ships at Ship-ready, verified at doc-review round R46 — the data-analysis engine + renderer is wired end-to-end, produces real findings against any CSV / TSV / xlsx / parquet / JSON, and ships the report as a self-contained Tufte/Few HTML hub
- Per-column statistics with bootstrap confidence intervals (BCa) — column-isolated reproducibility via per-column sub-seeds (ADR-202)
- Outlier detection: IQR + MAD always; IsolationForest + LOF when n ≥ 1000; three-way agreement matrix with confidence labels
- Time-series block: cadence inference, gap / stale-period detection, multi-window outliers with regime-shift labels, Mann-Kendall trend, STL seasonality detection, optional forecast (linear / ARIMA / exponential smoothing)
- Driver decomposition (Decompose / Validate / Run-everything modes): variance + partial correlation + RF importance with three-way agreement, top-K confidence labels, target-not-found / zero-variance refusal
- Privacy-safe duplicates summariser (P17-C01) — `_shared.duplicates.summarise(df)` returns aggregates only (group counts, row indices, similarity scores). NFR-1 sentinel-string privacy audit verifies zero leakage across every mode
- Deterministic comprehension-question synthesiser (P18-C01) — engine ships three plain-language Q/A pairs from real `headline_findings` under direct-CLI invocation, no placeholder text. SKILL.md orchestration overwrites with richer LLM content via `_patch_questions.py`
- Real provenance: SHA-256 of every input file, ISO-8601 timestamp, deterministic seed (derived from input SHA-256 when `--seed` is omitted), library versions via `importlib.metadata`, preferences hash, AN-40 anonymisation flag (AN-40 is the spec rule that flags inputs whose values match anonymisation token patterns)
- Anonymisation pipeline: `scripts/anonymise.py` token-pattern anonymisation; `scripts/de_anonymise.py` reverse round-trip; AN-40 detection in the engine flags anonymised inputs in the provenance footer
- Tufte/Few HTML hub renderer with WCAG AA contrast (axe-core audit gates SHOULD-priority); print stylesheet pending as P18+ candidate
- 1005 tests passing (980 unit, 25 integration), 2 env-gated (perf budget + WCAG audit)

### Added — GVM skill hardening

- **/gvm-tech-spec Hard Gate 6** — every implementation guide must contain a "Wiring matrix" section (entry point → consumed modules → wiring chunk). Refuses to write the impl guide if any module-building chunk has no consumer chunk. Audit trail proving every built module has a path to the running product.
- **/gvm-build Hard Gates 6 + 7** — Gate 6 refuses to start a phase if the impl guide lacks a wiring matrix; Gate 7 runs at phase completion: for every (entry_point, module) row, mechanically grep the entry-point file for both an import and a call site. Acceptance is by code, not by chunk-handover claim.

### Added — User guides

- New canonical user guides for `/gvm-impact-map`, `/gvm-walking-skeleton`, `/gvm-explore-test` (replacing 100-line skeleton-CSS placeholders with full Tufte HTML matching the rest of the user-guide collection)
- New user guide for `/gvm-analysis` (the only skill previously without one)

## [v1.0.0] — 2026-04-11

### Added
- Defect-class review panels: all review skills (code, doc, design) now use orthogonal defect-class panels instead of expertise-based panels. Grounded in Laitenberger et al.'s PBR research (41% more defects detected). Code review: References, Contracts, Logic, Naming. Doc review: pipeline vs standalone panel sets loaded selectively. Design review: Requirements Coverage, Interface Contracts, Structural Soundness, Implementability.
- Capture-recapture estimation (Wohlin): after R1, panels estimate remaining defect population from overlap counts — converts "should we do R2?" from a guess into a calculation
- Liberal R1 / strict R2+ criteria (Green & Swets, Signal Detection Theory): first pass flags borderlines for maximum recall; subsequent passes apply strict consumer-impact bar
- Two-pass scanning per panel (Drew & Wolfe, Satisfaction of Search): systematic scan then cross-reference scan prevents premature termination after first find
- Defect-class checklist in build self-review loop (Fagan: author preparation against inspection criteria)
- Doc review panel split: `pipeline-panels.md` for requirements/test cases/specs, `standalone-panels.md` for whitepapers/strategy/presentations/newsletters/training
- Cost-optimized model selection (shared rule 22): Opus for deep reasoning, Sonnet for guided work, Haiku for HTML generation
- Selective expert loading: domain specialists split into 20 per-domain files, stack specialists into 8 per-stack files
- Expert citations in shared rules: Fagan, Parnas, Deming, Norman, Fowler, Clements, Keeling, Redish
- Build verification verdicts: `/gvm-test` Hard Gate 5 (Pass / Pass with gaps / Do not release)
- "What Prevents a Higher Score" mandatory section in all review reports
- Expert Panel section in build prompts and tech-spec domain specs
- Finding Quality Gate in independent chunk review dispatch
- Landing page (index.html) and quick reference card (quick-reference.html)
- Training documents: Getting Started, Expert Grounding Workshop, Review Calibration
- Case study: building Assay with GVM end-to-end
- Experiment results CSVs for reproducibility

### Changed
- shared-rules.md compressed from ~10K to ~5.5K tokens (operational detail extracted to shared-rules-operations.md)
- All pipeline position lines now show the full canonical pipeline
- Build self-review loop renamed to "SELF-REVIEW LOOP" (distinct from independent chunk review)
- Build Hard Gates renumbered: bootstrap is pre-flight, quality gates 1-5
- Deploy blocking verdict list expanded to all 9 not-ready strings
- Deploy version bump rules restructured as pre-1.0/post-1.0 decision table
- All branch paths re-state applicable Hard Gates per shared rule 20
- Dual review trigger wording unified: "2 completed prior rounds = round 3+"
- Shared-rules boilerplate reduced from ~60 words to 2 sentences across all skills
- Calibration update procedure references pipeline-contracts.md
- Doc-review expert discovery aligned with other review skills (shared rule 2)

### Fixed
- Relative skill-local paths that would fail at runtime (requirements, test-cases, tech-spec, doc-review)
- stack-tooling.md references without install path prefix in build step 5
- Pipeline contracts diagram: doc-review now shown before deploy
- Application Brief contract mismatch: "Recommendation" → "Possible Outcomes"
- Code-review pipeline contract: verdict added as required field
- Review-reference.md verdict placement: "after score card" → "before score card"
- Expert persistence paths updated for domain/stack split
- Inaccurate expert citations corrected (Fagan rule 3, Keeling rule 11, Deming rule 14, Hunt & Thomas rule 21)

## [v0.1.0] — 2026-04-05

### Added
- Initial release: 15 skills implementing the GVM pipeline
- Expert grounding with tiered activation (architecture, domain, stack, industry)
- Progressive calibration with dual review from round 3
- Build check promotion (self-improving build)
- 5 whitepapers documenting the methodology
- Blog post introducing GVM
