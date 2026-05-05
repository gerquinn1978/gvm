# Pipeline Artefact Contracts

Defines the structural expectations between pipeline phases. Producing skills must write output conforming to these contracts. Consuming skills can rely on these structures being present.

These contracts cover the **markdown** files only — the MD version is the machine-readable artefact consumed by downstream skills. HTML is for human reading and is not parsed by other skills.

---

## Canonical Pipeline

```
/gvm-init (optional) ─┐
                       ├─→ /gvm-requirements → /gvm-test-cases → /gvm-tech-spec ─┐
/gvm-site-survey ──────┘                                                          │
                                                                                  ├─→ /gvm-design-review (optional) → /gvm-build → /gvm-code-review → /gvm-test → /gvm-doc-write (pipeline docs) → /gvm-doc-review → /gvm-deploy
                                                                                  │
                                                                                  └─→ /gvm-doc-review (quality gate, can run at any point)

Standalone: /gvm-doc-write (presentations, newsletters, etc.), /gvm-experts, /gvm-status (read-only)
```

Each skill's "Pipeline position" line shows its local context. This diagram is the authoritative full pipeline.

---

## Changelog Section Contract

**Applies to:** All pipeline artefacts that can be modified after initial creation (requirements, test-cases, specs, handovers).

Every pipeline artefact modified after its initial creation must contain a Changelog section. The changelog is the authoritative record of what changed, when, and why (Hunt & Thomas: single source of truth).

### Required format

```markdown
## Changelog

| Date | Change | Reason | Author |
|------|--------|--------|--------|
| 2026-03-29 | Added RE-15, RE-16 to Search domain | New scope: voice search | user/AI |
| 2026-03-28 | Changed RE-3 priority SHOULD→MUST | User feedback from beta | user |
```

### Rules

1. **Position** — Changelog is the last section of the document.
2. **Append-only** — New entries at the top (most recent first). Never modify or delete existing rows (Keeling: immutability of records).
3. **Absent on creation** — Do not include a Changelog section when first creating a document. It appears only when the first modification occurs.
4. **ID references** — Changes must reference specific artefact IDs affected (requirement IDs, ADR IDs, test case IDs).
5. **Reason is mandatory** — "Updated RE-3" is insufficient. State what changed and why.

### What consumers depend on

- `/gvm-status` reads changelog sections to report recent changes and provide changelog-aware staleness detection.
- Downstream skills read upstream changelogs to identify what changed since they last ran.
- `/gvm-test` checks that documentation reflects changes recorded in changelogs.

---

## Artefact Numbering for Multiple Rounds

When the pipeline is re-entered for new scope (not in-place updates), new artefacts use a sequential numbering suffix:

- `requirements/requirements-002.md` (first round is `requirements.md`, second is `requirements-002.md`)
- `test-cases/test-cases-002.md`
- `specs-002/` (entire directory for the second round's specs)

Previous-round artefacts are immutable historical records (Keeling: decisions are not erased, they are superseded).

**Requirement ID convention for new rounds:** To avoid ID collisions, the second round uses a round prefix: `R2-{DOMAIN}-{N}` (e.g., `R2-VS-1`). Third round uses `R3-`, etc. The first round uses no prefix (backward compatible).

**Test case IDs follow requirements:** `TC-R2-VS-1-01` traces to `R2-VS-1` in `requirements-002.md`.

**Implementation guide:** Each round produces its own `specs-{NNN}/implementation-guide.md` with new phases and chunks. The build system reads whichever implementation guide is specified.

---

## requirements/requirements.md

**Producer:** `/gvm-requirements`
**Consumers:** `/gvm-test-cases`, `/gvm-tech-spec`, `/gvm-doc-review`, `/gvm-code-review`, `/gvm-status`

### Required structure

1. **Expert Panel** — table of experts active during creation: Expert, Work, Role in This Document (per shared rule 17). Placed after subtitle, before first domain section.
2. **Requirement IDs** — format `{DOMAIN}-{N}` where DOMAIN is a short uppercase prefix (e.g., `RE-1`, `PL-3`, `AU-5`). IDs must be unique across the document. Every requirement must have an ID.
2. **MoSCoW priority** — every requirement must have exactly one of: `**[MUST]**`, `**[SHOULD]**`, `**[COULD]**`, `**[WONT]**`.
3. **Domain grouping** — requirements grouped under domain headings (e.g., `## Search`, `## Payments`). Domain headings are H2 level.
4. **Requirements Index** — a markdown table with columns: ID, Domain, Summary, Priority. Must contain every requirement in the document.
5. **Assumptions** — section listing confirmed assumed-true statements.
6. **Constraints** — section listing budget, technology, timeline, and regulatory constraints.
7. **Out of Scope** — section listing explicitly excluded items.
8. **Open Questions** — section listing unresolved items.

### What consumers depend on

- `/gvm-test-cases` parses requirement IDs to build traceability (`TC-{REQ-ID}-{NN}`). If IDs change format, test case IDs break.
- `/gvm-tech-spec` reads domain headings to determine spec decomposition. Domain grouping drives how many specs are produced.
- `/gvm-doc-review` reads the requirements index to cross-check completeness against test cases and specs.
- `/gvm-status` checks file existence and modification timestamp only.

---

## test-cases/test-cases.md

**Producer:** `/gvm-test-cases`
**Consumers:** `/gvm-tech-spec`, `/gvm-doc-review`, `/gvm-status`

### Required structure

1. **Expert Panel** — table of experts active during creation: Expert, Work, Role in This Document (per shared rule 17). Placed after subtitle, before first domain section.
2. **Test case IDs** — format `TC-{REQ-ID}-{NN}` (e.g., `TC-RE-1-01`, `TC-PL-3-02`). The `{REQ-ID}` portion must match a requirement ID from requirements.md.
2. **Given/When/Then format** — every test case must have Given, When, and Then clauses with concrete values (not abstract descriptions).
3. **Requirement traceability** — every test case must include `[Requirement: {ID}]` linking back to the source requirement.
4. **Priority** — inherited from the requirement or explicitly deprioritised with rationale.
5. **Domain grouping** — test cases grouped by domain, matching the domain structure in requirements.md.
6. **Traceability Matrix** — a markdown table mapping every requirement ID to its test case IDs, with a coverage status column.
7. **Health Report** — section documenting requirements issues found and decisions made (fix / proceed / acknowledge).

### What consumers depend on

- `/gvm-tech-spec` reads test case IDs and techniques to link testing strategy to spec sections (e.g., `[Test: TC-RE-1-01]`).
- `/gvm-doc-review` reads the traceability matrix to verify bidirectional coverage between requirements and tests.
- `/gvm-status` checks file existence and modification timestamp only.

### Companion file

- `test-cases/requirements-health-report-decisions.md` — persisted acknowledgements. Format: one line per decision, requirement ID + decision + timestamp. This file is append-only across runs; `/gvm-test-cases` reads it to avoid re-surfacing acknowledged issues.

---

## specs/*.md

**Producer:** `/gvm-tech-spec`
**Consumers:** `/gvm-build`, `/gvm-code-review`, `/gvm-doc-review`, `/gvm-status`

### Required files

- `specs/cross-cutting.md` — shared conventions, tech stack, design principles, project-wide ADRs.
- `specs/{domain}.md` — one per architectural domain (number varies by project complexity).
- `specs/architecture-overview.md` — C4-style overview, system context, container relationships.
- `specs/implementation-guide.md` — the build plan. This is the most structurally critical artefact in the pipeline.

### implementation-guide.md contract

This file has the tightest structural requirements because `/gvm-build` parses it programmatically.

1. **Phase-Chunk IDs** — format `P{phase}-C{chunk}` (e.g., `P1-C01`, `P3-C05`). Two-digit zero-padded chunk numbers.
2. **Chunk descriptions** — each chunk must specify:
   - Chunk ID and name
   - What it delivers (concrete output)
   - Spec references: which spec file and section to read (e.g., `cross-cutting.md, ADR-005`)
   - Dependencies: which other chunks must be complete first
   - Test expectations: what tests this chunk should produce
3. **Dependency matrix** — a table or list showing: chunk → depends on / enables / parallel with.
4. **Build phases** — chunks grouped into sequential phases. All chunks within a phase can run in parallel; phases are sequential.
5. **Critical path** — identified explicitly.

### Domain spec contract

1. **Expert Panel** — table of experts active for this spec: Expert, Work, Role in This Document (per shared rule 17). Placed after subtitle. This is per-spec, not project-wide — a data integration spec lists Kleppmann and Kimball, not Cooper and Krug.
2. **Requirement traceability** — each spec section must reference the requirement IDs it addresses.
2. **ADR format** — Architecture Decision Records must have: ID (ADR-{NNN}), title, status (Accepted / Superseded / Deprecated), context, decision, consequences. When an ADR is superseded, update only the status line to `Superseded by ADR-{NNN}` and add a forward reference. The superseded ADR's content is not modified (Keeling: decisions are immutable records).
3. **Component definitions** — named components with responsibilities, interfaces, and dependencies.
4. **Test references** — where applicable, link to relevant test case IDs from test-cases.md.

### cross-cutting.md contract

1. **Declared experts** — list of which Tier 1/2/3 experts are active for this project. `/gvm-code-review` uses this to assemble review panels.
2. **Tech stack** — languages, frameworks, and key libraries with version constraints.
3. **Conventions** — naming, file structure, error handling, logging patterns. `/gvm-build` extracts this section for every chunk.

### What consumers depend on

- `/gvm-build` parses implementation-guide.md to determine chunk order, reads spec sections by reference, and checks for dependency handovers. If the chunk ID format or dependency matrix changes, build execution breaks.
- `/gvm-code-review` reads cross-cutting.md for declared experts and conventions. If the expert declaration moves or changes format, review panels may be wrong.
- `/gvm-doc-review` reads all spec files for cross-document consistency checks.
- `/gvm-status` checks for implementation-guide.md existence and counts spec files.

---

## build/handovers/P{X}-C{XX}.md

**Producer:** `/gvm-build`
**Consumers:** `/gvm-build` (for dependency resolution), `/gvm-status`

### Required structure

1. **Chunk ID** — must match the `P{X}-C{XX}` format from implementation-guide.md.
2. **What was built** — files created or modified, with paths.
3. **Test command** — the command to run tests for this chunk.
4. **Deviations** — any differences from what the implementation guide specified, with rationale.
5. **Upstream fixes** — any issues found in upstream artefacts (specs, requirements) during build.
6. **Dependencies satisfied** — confirmation that all declared dependencies had handover files.

### What consumers depend on

- `/gvm-build` checks for handover file existence before executing dependent chunks. Missing handover = build refuses to proceed.
- `/gvm-status` counts handover files to calculate build progress (X of Y chunks complete).

---

## build/prompts/P{X}-C{XX}.md

**Producer:** `/gvm-build`
**Consumers:** `/gvm-build` (subagents read prompts to execute chunks), `/gvm-status` (counts prompts to track generation progress)

### Required structure

1. **Chunk ID** — must match the `P{X}-C{XX}` format from implementation-guide.md.
2. **Spec references** — which spec files and sections this chunk reads.
3. **Deliverables list** — files to create or modify, including test files.
4. **TDD instructions** — the red-green-refactor sequence and commit format for this chunk.

### What consumers depend on

- `/gvm-build` subagents read prompts as self-contained execution instructions. If the structure changes, chunk execution breaks.
- `/gvm-status` counts prompt files to calculate how many chunks have been planned vs executed.

---

## code-review/code-review-{NNN}.html

**Producer:** `/gvm-code-review` (parallel subagents, consolidated by the main skill)

**Format:** HTML only. Review reports are not pipeline artefacts — no downstream skill parses an MD version, and `/gvm-status` only checks file existence. Per the shared rule 13 exception for review reports, the MD pair is not produced.
**Consumers:** `/gvm-build` (reads findings as fix requirements), `/gvm-status` (checks existence)

### Required structure

0. **Verdict** — a single verdict statement using the code-review language from `review-reference.md` (Merge / Merge with caveats / Do not merge). Positioned before the review summary.
1. **Review Summary** — panels run, total findings per severity, cross-cutting themes.
2. **Findings** — grouped by severity (Critical → Suggestion), each finding as a structured block.
3. **Summary Table** — a markdown table with columns: #, Severity, File, Issue, Expert, Status.
4. **Surfaced Requirements** (optional, present when the review's SURFACED REQUIREMENT TRIAGE step (synthesis step 5) produced any items) — a per-finding record with: surfaced-requirement description, originating panel + finding ID, triage choice ("append as criterion" / "new requirement" / "new round" / "deferred — awaiting triage"), target requirement ID once promoted (blank until promotion completes). Positioned after the Summary Table. Per shared rule 27, this is the staging ground only — the destination is `requirements/requirements.md`.

### Finding block format

Each finding must contain all of these fields:

```markdown
### [SEVERITY] File:Line — Issue title

**Expert:** Expert Name (*Work*)
**File:** `path/to/file.ext:123`
**Spec:** ADR-005 / cross-cutting.md §conventions (if applicable)

**Issue:** One-sentence description of what is wrong.

**Fix:** Concrete description of what to change.
```

### What consumers depend on

- `/gvm-build` parses findings as fix requirements. It reads the **Expert** field to ground fixes in the same expert's framework (shared rule 3: experts who find should fix). It reads the **File:Line** field to locate the code. It reads the **Fix** field for the remediation instruction. If any of these fields are missing or inconsistently formatted, the fix loop breaks.
- `/gvm-status` checks file existence and counts review files only.

### Subagent output consistency

When `/gvm-code-review` dispatches parallel subagents, each subagent must produce findings in this format. The main skill consolidates, deduplicates, and elevates severity for cross-panel findings. Subagent output that does not follow the finding block format will be reformatted during consolidation — but this adds latency and risks information loss. The dispatch template includes the format specification to prevent this.

---

## design-review/design-review-{NNN}.html

**Producer:** `/gvm-design-review`

**Format:** HTML only. Review reports are not pipeline artefacts — per the shared rule 13 exception for review reports, the MD pair is not produced.
**Consumers:** `/gvm-build` (reads findings as fix requirements), `/gvm-status` (checks existence)

### Required structure

0. **Verdict** — a single verdict statement using the language from `review-reference.md`. Positioned before the review summary.
1. **Review Summary** — domains reviewed, panels dispatched, findings per severity.
2. **Per-Domain Findings** — grouped by domain (Data Model, UI/UX, API/Integration, Performance), each finding as a structured block with Expert, Severity, File/Section, Issue, Spec Reference, Fix.
3. **Cross-Domain Themes** — issues spanning multiple domains.
4. **What Prevents a Higher Score** — for each dimension below 10, state in one sentence the gap and whether closing it is worth the cost. Placement: after scores, before expert panel (per `review-reference.md`).
5. **Summary Table** — columns: #, Severity, Domain, Issue, Expert, Status.

### What consumers depend on

- `/gvm-build` reads findings as fix requirements before implementing design-adjacent chunks.
- `/gvm-status` checks file existence only.

---

## init/brief-{NNN}.md (optional)

**Producer:** `/gvm-init` (Step 0 — Application Brief, when selected by user)
**Consumers:** `/gvm-requirements` (reads as seed input for domain elicitation), `/gvm-tech-spec` (reads architecture direction as constraint), `/gvm-status` (checks existence)

### Purpose

A structured one-page project justification. Answers: what problem does this solve, for whom, and is it worth doing? Optional — used when organisations gate project starts or when the project's justification needs approval before committing resources.

### Required structure

1. **Problem Statement** — what problem, for whom (Rumelt: diagnosis)
2. **Proposed Solution** — one paragraph (Rumelt: guiding policy)
3. **Value Proposition** — why this solution for this problem (Osterwalder: problem-solution fit)
4. **Existing Landscape** — what already exists, why insufficient
5. **High-Level Architecture Direction** — deployment model, user model, key integrations, scale (Brown: C4 system context, Fairbanks: decisions expensive to reverse)
6. **Stakeholders & Users**
7. **Constraints** — budget, timeline, regulatory, team capacity
8. **Possible Outcomes** — a list of possible approval decisions (Approve, Approve with conditions, Absorb, Defer, Decline). The proposer does not recommend an outcome.

### What consumers depend on

- `/gvm-requirements` reads the Problem Statement as the starting point for domain elicitation and the Constraints as requirements constraints.
- `/gvm-tech-spec` reads the Architecture Direction to constrain technology choices.
- `/gvm-status` checks file existence only.

---

## init/init-{NNN}.md

**Producer:** `/gvm-init`
**Consumers:** `/gvm-requirements` (reads expert roster), `/gvm-tech-spec` (reads expert roster), `/gvm-status` (checks existence)

### Required structure

1. **Executive Summary** — project name, date, business domain.
2. **Process Experts (Tier 1)** — defaults confirmed or replacements created, with rationale.
3. **Industry Domain (Tier 2b)** — files selected or created, coverage assessment, any newly discovered experts with scores.
4. **Expert Roster Summary** — a markdown table with columns: Expert Name, Work, Tier, Classification, Reference File, Status (existing / newly added / newly scored). Must contain every active expert for this project.
5. **Activation Log** — confirmation that the log was initialised or already existed.
6. **Next Steps** — recommended next pipeline command.

### What consumers depend on

- `/gvm-requirements` and `/gvm-tech-spec` read the **Expert Roster Summary table** to know which experts are active for this project. If the table format changes (column order, column names), downstream skills may not find the experts.
- `/gvm-status` checks file existence and modification timestamp only.

---

## doc-review/{document-name}-review-{date}.html

**Producer:** `/gvm-doc-review`
**Consumers:** `/gvm-status` (checks existence)

**Format:** HTML only. Review reports are not pipeline artefacts — no downstream skill parses a Markdown version, and `/gvm-status` only checks file existence. Per the shared rule 13 exception for review reports, the MD pair is not produced.

**Derivation rule for `{document-name}`:** use the full basename of the reviewed file without its extension and without path prefix. Do not truncate multi-word basenames — `test-cases.html` produces `test-cases-review-{date}.html`, not `test-review-{date}.html`. For full pipeline reviews (requirements + test-cases + specs reviewed together), use `pipeline` as the document name.

### Required structure

0. **Verdict** — a single verdict statement using the type-specific language from `review-reference.md`. Positioned before the score summary.
1. **Score summary** — overall score (0-10) and per-document scores (requirements, test cases, specs, cross-document consistency) with the weighted formula: requirements 30%, test cases 25%, specs 30%, consistency 15%.
2. **Issues by severity** — Critical, Important, Minor. Each issue must identify the document, the specific ID or section affected, and a concrete fix suggestion.
3. **Per-document review** — criterion-by-criterion assessment for each document type reviewed.
4. **Cross-document consistency** — traceability checks between requirements, test cases, and specs.
5. **What Prevents a Higher Score** — for each dimension below 10, state in one sentence the gap and whether closing it is worth the cost. Placement: after score trajectory (round 2+) or dimension detail (round 1), before expert panel (per `review-reference.md`).
6. **Calibration update metadata** — when `reviews/calibration.md` is updated, note the changes.
7. **Blind Review Findings** (round 3+) — new findings from the uncalibrated reviewer, tagged as blind-review origin.
8. **Regressions** (round 3+) — previously-resolved issues that resurfaced.

### What consumers depend on

- `/gvm-status` checks file existence and modification timestamp to confirm a quality gate has been passed.
- Future pipeline re-entry: if requirements are updated and the pipeline re-runs, the prior doc-review score provides a baseline for the calibration system.
- `/gvm-doc-review` and `/gvm-code-review` update `reviews/calibration.md` after each round.

---

## site-survey/site-survey-{NNN}.md

**Producer:** `/gvm-site-survey`
**Consumers:** `/gvm-requirements` (reads expert roster and diagnosis), `/gvm-tech-spec` (reads expert roster and diagnosis), `/gvm-build` (reads diagnosis for context), `/gvm-status` (checks existence)

### Required structure

1. **Executive Summary** — one-paragraph diagnosis, scenario classification, recommended entry point.
2. **Codebase Profile** — tech stack, size, structure, activity level, contributor count.
3. **Architectural Map** — patterns identified, module boundaries, data flow, conventions.
4. **Health Scorecard** — scored dimensions (Coherence, Currency, Testability, Modularity, Documentation, Dependency Health) as a table with 1–5 scores.
5. **Diagnosis** — one of five scenario classifications (Coherent, Coherent but Outdated, Fractured, Mid-migration, Incoherent) with supporting evidence.
6. **Risk Areas** — hotspots, high-coupling zones, untested areas, prioritised as Critical / Important / Minor.
7. **Diagnostic Experts Used** — which experts conducted the survey and what role each played.
8. **Expert Coverage Assessment** — covered areas (expert name + reference file) and gaps (what was done about each gap).
9. **Recommended Project Experts** — a markdown table with columns: Expert Name, Work, Tier, Classification, Reference File, Status (existing / newly added). Must contain every expert recommended for downstream phases.
10. **Route Recommendation** — recommended pipeline entry point with rationale.
11. **Open Questions** — anything the survey could not determine from code alone.

### What consumers depend on

- `/gvm-requirements` and `/gvm-tech-spec` read the **Recommended Project Experts table** (section 9) to know which experts are active. Same dependency as the init roster table — if the table format changes, downstream skills may not find the experts.
- `/gvm-tech-spec` reads the **Diagnosis** (section 5) and **Health Scorecard** (section 4) to inform architecture decisions and risk calibration.
- `/gvm-build` may read the **Risk Areas** (section 6) for context on known problem areas.
- `/gvm-status` checks file existence and modification timestamp only.

### Shared contract: Expert Roster Summary Table

Both init and site-survey produce an expert roster table consumed by downstream skills. The table format must be consistent across both producers:

| Column | Description |
|---|---|
| Expert Name | The expert's name |
| Work | The specific published work |
| Tier | tier1, tier2a, tier2b, tier3, or discovered (must match the closed set in `shared-rules.md` rule 1 and `log-expert.py`) |
| Classification | Canonical / Established / Recognised / Emerging / Provisional |
| Reference File | Path to the reference file containing this expert |
| Status | existing / newly added / newly scored |

Downstream skills search for this table by looking for a markdown table with "Expert Name" and "Tier" columns. If the column names change, the consumer must be updated.

---

## STUBS.md

**Producer:** `/gvm-build` (HS-1 chunk-handover gate), `/gvm-walking-skeleton` (deferred-stub registration), `/gvm-explore-test` (HS-6 retroactive audit)
**Consumers:** `/gvm-build` (HS-1 enforcement on every handover), `/gvm-test` (VV-2(a) expiry check via `_stubs_parser.check_expiry`), `/gvm-code-review` (Panel E reconciliation — `_panel_e_prompt.assemble_panel_e_prompt` embeds STUBS.md verbatim), `/gvm-status`

### Required structure

1. **YAML frontmatter** — `schema_version: 1` (per cross-cutting ADR-007; loaded via `_schema.load_with_schema(path, "stubs")`).
2. **Stub registry table** — Markdown table with columns: `Path`, `Reason`, `Real-provider Plan`, `Owner`, `Expiry`, and an optional `Requirement` column. Parsed by `_stubs_parser.load_stubs` into `StubEntry(path, reason, real_provider_plan, owner, expiry: datetime.date, requirement: str | None = None)`.
3. **Field rules** (per honesty-triad ADR-101 / ADR-004):
   - `path` — relative repo path, must lie under a directory named `stubs/` (HS-5 namespace gate).
   - `reason` — ≥ `MIN_REASON_LEN` characters of prose explaining why this is a stub, not a placeholder phrase.
   - `real_provider_plan` — concrete plan accepted by `_stubs_parser.validate_plan`; must name the provider/sandbox/integration that will replace the stub.
   - `owner` — accountable individual or team (not "TBD").
   - `expiry` — ISO-8601 date. Stubs with `expiry < today` are flagged by `_stubs_parser.check_expiry`; CI passes on the boundary day (`expiry == today` → not yet expired).
4. **Surfaced requirements MUST NEVER be parked here** — `STUBS.md` is for code-level placeholders only; no `STUB-SR-NN` IDs and no `## Surfaced Requirements` section (per shared rule 27).

### What consumers depend on

- `/gvm-build`'s HS-1 gate (`_hs1_check.check`) refuses any handover whose Files Created/Modified list contains a path under `stubs/` not registered here.
- `/gvm-test`'s VV-2(a) caps the verdict at Demo-ready (or worse) when expired stubs are present in the production-path file set.
- `/gvm-code-review`'s Panel E reconciles unregistered stubs against this file via `_allowlist.load_allowlist` and `_sd5_promotion.apply_sd5`.
- The schema_version is bumped only via an explicit migration; older versions are accepted (consumers handle migration explicitly, never silently — `_schema.SchemaTooNewError` is the only refusal).

---

## impact-map.md

**Producer:** `/gvm-impact-map`
**Consumers:** `/gvm-requirements` (IM-4 trace gate at Phase 5 finalisation via `_im4_check.py`), `/gvm-test-cases` (downstream traceability), `/gvm-doc-review`, `/gvm-status`

### Required structure

1. **YAML frontmatter** — `schema_version: 1` (loaded via `_schema.load_with_schema(path, "impact_map")`).
2. **Four flat Markdown tables** (discovery ADR-302) in this order:
   - `## Goals` — columns: `ID` (`G-N`), `Goal`, `KPI`.
   - `## Actors` — columns: `ID` (`A-N`), `Actor`, `Persona`.
   - `## Impacts` — columns: `ID` (`I-N`), `Goal` (FK to `G-N`), `Actor` (FK to `A-N`), `Impact`.
   - `## Deliverables` — columns: `ID` (`D-N`), `Impact` (FK to `I-N`), `Deliverable`, `Type`.
3. **Referential integrity** — every Impact's `Goal` and `Actor` must resolve to a row in the prior tables; every Deliverable's `Impact` must resolve to a row in `## Impacts`. Violations surface during Phase 6 validation.
4. **Changelog** — appears once the file is first modified after creation (per the Changelog Section Contract above).

### What consumers depend on

- `/gvm-requirements` IM-4 gate (`_im4_check.py`): every `Must`, `Should`, and `Could` requirement must carry an inline `[impact-deliverable: D-N]` tag whose ID resolves to a row in this file. Only `Won't` requirements are exempt. The parser is `_im_tags.py`.
- `/gvm-test-cases` reads the deliverable IDs to anchor traceability (TC tags inherit the upstream `D-N` reference).
- The flat-table form is diff-friendly and mechanically validatable; nested representations are explicitly out of contract.

---

## risks/risk-assessment.md

**Producer:** `/gvm-requirements` (Phase 0 + Phase 5 — discovery ADR-306..308)
**Consumers:** `/gvm-test` (VV-2(b) and VV-4(c) gates), `/gvm-doc-review`, `/gvm-status`

### Required structure

1. **YAML frontmatter** — `schema_version: 1` (loaded via `_schema.load_with_schema(path, "risk_assessment")`).
2. **Four H2 sections in canonical order** (per `_risk_validator.REQUIRED_SECTIONS`): `## Value Risk`, `## Usability Risk`, `## Feasibility Risk`, `## Viability Risk`. All four MUST be present (RA-1).
3. **Per-section content rules** (enforced by `_risk_validator.full_check`):
   - **RA-2** — each non-`*accepted-unknown*` section has ≥ 50 words of prose (`_MIN_WORDS = 50`).
   - **RA-3** — no section may be the bare word `unknown`. The `*accepted-unknown*` form is structurally rigid: the first non-empty line is `*accepted-unknown*`, followed by `Rationale:`, `Validator:`, and `Review date:` lines (any order). The `Review date:` value is ISO-8601 and must satisfy `>= today` (equality permitted).
   - **RA-4** — each prose section contains at least one `questioner:` token (case-insensitive token name; trailing ASCII colon required). Inside `*accepted-unknown*` sections, `Validator:` is accepted as a synonym (per ADR-307 mutual exclusion).

### What consumers depend on

- `/gvm-test` evaluates VV-2(b) (file present and structurally valid) and VV-4(c) (no expired `*accepted-unknown*` sections) against this file. A failed RA-3 review-date check caps the verdict.
- `_risk_validator.full_check(path, today=...)` never raises; it returns `(RiskAssessment | None, list[RiskValidationError])`. Consumers branch on `errors == []`.
- The validator lives in `gvm-design-system/scripts/` per cross-cutting ADR-002 so both `/gvm-requirements` and `/gvm-test` import the same code (Hunt & Thomas: single source of truth).

---

## boundaries.md

**Producer:** `/gvm-walking-skeleton` (Phase 4 generation; Augment mode preserves prior rows)
**Consumers:** `/gvm-walking-skeleton` (WS-1..WS-3 self-validation via `_validator.full_check` on every Augment-mode invocation), `/gvm-build` (WS-5 skeleton-status gate per chunk), `/gvm-test` (VV-3(d) sandbox-divergence audit and VV-4(d) integration-coverage check), `/gvm-explore-test` (charters reference boundary names when scoping integration tours), `/gvm-status`

### Required structure

1. **YAML frontmatter** — `schema_version: 1` (loaded via `_schema.load_with_schema(path, "boundaries")`).
2. **Boundary registry table** — one row per external integration boundary. Columns must match `_boundaries_parser.EXPECTED_COLUMNS` exactly, in order: `name`, `type`, `chosen_provider`, `real_call_status`, `test_credentials_location`, `cost_model`, `sla_notes`, `production_sandbox_divergence`. The parser raises if headers do not match this list. `type` is one of `_boundaries_parser.TYPE_ENUM` (`http_api`, `database`, `filesystem`, `sdk`, …). Parsed by `_boundaries_parser.load_boundaries` into `Boundary` dataclass instances.
3. **`real_call_status` is one of three values** (walking-skeleton ADR-403 / ADR-407):
   - `wired` — production endpoint exercised by the skeleton's runtime test (the test itself is the proof).
   - `wired_sandbox` — sandbox endpoint exercised; production endpoint declared but not called. **Required adjunct:** non-trivial `production_sandbox_divergence` note. The boundaries-parser raises `DivergenceMissingError` if the field is empty or the literal sentinel `"n/a"`.
   - `deferred_stub` — boundary not yet wired; placeholder lives at `walking-skeleton/stubs/<name>.<ext>`. **Required adjunct:** corresponding entry in `STUBS.md` with reason / real-provider plan / owner / ISO-8601 expiry (HS-1 / WS-6 joint contract per honesty-triad ADR-101).

### What consumers depend on

- `/gvm-build`'s WS-5 gate (`_skeleton_status.query_skeleton_status`) refuses chunks while the skeleton is red; the gate keys off `walking-skeleton/.first-run.log`. Projects without that file skip the gate (no-op for non-adopters).
- `/gvm-test`'s VV-3(d) reads the registry to audit sandbox divergence: skeletons that ran wholly against sandbox endpoints, with substantive `production_sandbox_divergence` notes, cap the verdict at Demo-ready until the divergences are reviewed against production.
- `/gvm-explore-test` charters that name a `tour` of `data` / `configuration` / `interruption` reference boundary names from this file when scoping the session.

---

## test/explore-NNN.md

**Producer:** `/gvm-explore-test` (paired md + html via `_report_writer.write_report`; atomic `mkstemp` + `os.replace` ensures both become visible together)
**Consumers:** `/gvm-test` (VV-4(d) tour-completion gate via `_explore_parser.load_explore`), `/gvm-doc-write` (release-note input), `/gvm-status`

### Required structure

1. **Charter section** — schema_version, session_id (`explore-NNN`), mission, timebox_minutes (one of `30`, `60`, `90`), target, tour (one of the five Whittaker tours, case-insensitive bare word), runner (or `unassigned` per ET-7 / ADR-207). Validated pre-session by `_charter.load(path)` against ADR-202.
2. **Defect entries** — `D-NNN` IDs; severity (one of `Critical`, `Important`, `Minor`) chosen by the practitioner via AskUserQuestion (ADR-205 — never auto-classified); Given/When/Then triplet; reproduction path (required for severity ≥ Minor); optional stub path if the defect lives in a deferred boundary.
3. **Observation entries** — `O-NNN` IDs in a separate namespace from defects; no severity field. Defects without reproduction are re-filed as Observations per ADR-203 (`ET-3` rule).
4. **Debrief / overall assessment paragraph** — practitioner-supplied prose written at session end.
5. **HTML escaping** — every practitioner-supplied string in the paired `explore-NNN.html` is run through `html.escape()` before substitution (Hard Gate 5; `TC-ET-3-03 [SECURITY]`). The MD output preserves raw payloads because that is what the downstream parser reads.

### What consumers depend on

- `/gvm-test`'s VV-4(d) reads the most-recent `test/explore-NNN.md` via `_explore_parser.load_explore(...)` and feeds it into the verdict evaluator. Critical defects in non-stub paths block Ship-ready outright. The verdict evaluator never re-classifies severities — the practitioner's call is authoritative (ADR-205).
- The downstream `ET-5` tour-completion gate (Critical-blocks-Ship-ready) lives in `/gvm-test`'s VV-4(d), not in `/gvm-explore-test` — `/gvm-explore-test` produces the artefact; `/gvm-test` evaluates it.
- The `D-NNN` and `O-NNN` ID namespaces increment independently and are never reused.

---

## reviews/calibration.md

**Producer:** `/gvm-code-review`, `/gvm-doc-review`, `/gvm-design-review` (appended after each review round)
**Consumers:** `/gvm-code-review`, `/gvm-doc-review` (loaded before scoring to calibrate reviewers)

### Purpose

Progressive calibration artefact. Accumulates review data across rounds so that each successive review is better calibrated to the project. Addresses Deming's measurement system stability: the first review has high variance; subsequent reviews converge toward a stable measurement.

### Required structure

1. **Score History** — table with columns: Round, Date, Type (code/doc/design), Overall, and per-dimension scores. One row per review round, append-only.
2. **Dimension Benchmarks** — per dimension: baseline (first round score), current (latest round), trend (improving/stable/declining). Updated after each round.
3. **Anchor Examples** — per dimension, concrete examples from this project of what scored high and what scored low. Keep the 2 best and 2 worst examples per dimension (Fagan: calibration through reference artefacts). Replace weaker examples when better ones are found. Selection criteria:

   An anchor example must meet all four tests:

   - **Countable** (Marzano) — the quality level is expressed as a count or ratio, not a judgement. "12/12 contracts have consumer sections" is an anchor. "Good contract coverage" is not.
   - **Verifiable** (Deming) — a reviewer unfamiliar with the project can independently confirm the score by checking the artefact. If two reviewers would disagree about whether the example belongs at that score level, it is not an anchor.
   - **Self-contained** (Fagan) — the example includes enough context to function as a calibration reference without reading the full review. At minimum: the file or section, what was counted, the count, and the score it produced.
   - **Band-demonstrating** (Stevens & Levi) — the example clearly illustrates the rubric descriptor for its score band. A "9" anchor should show what the rubric says a 9 looks like. A "4" anchor should show what a 4 looks like. The anchor *is* the concrete descriptor.

   When selecting from a round's findings, prefer findings with counts over findings with judgements. When replacing an existing anchor, the new one must be more countable, more self-contained, or more clearly band-demonstrating than the one it replaces — not just newer.
4. **Recurring Findings** — issues flagged in 2+ consecutive rounds. These are systemic and should be weighted higher in future reviews.
5. **Resolved Findings** — issues flagged in a previous round and confirmed fixed. These demonstrate improvement and calibrate the reviewer's expectation of what "fixed" looks like.

### Calibration layers

The calibration file is project-level. It works alongside three other calibration layers that are already in the design system:

| Layer | Source | What it calibrates |
|-------|--------|-------------------|
| Universal | Expert reference files (architecture-specialists.md, writing-reference.md) | What "good" means in any software project |
| Domain | Industry domain files (references/industry/*.md) | What "good" means in this industry |
| Stack | Stack specialists (stack-specialists.md) | What "good" means in this technology |
| **Project** | **reviews/calibration.md** | **What "good" means in this specific codebase** |

### Rules

1. **Created on first review** — does not exist before the first review round. The first review creates it with initial scores and anchor examples.
2. **Append-only score history** — new rows added, existing rows never modified (Keeling: immutable records).
3. **Anchor examples are curated, not accumulated** — keep the 2 best and 2 worst per dimension. Replace when a more illustrative example is found. This is the only section where existing content may be replaced.
4. **Recurring findings promote automatically** — if the same issue appears in 3+ rounds, flag it as systemic in the calibration file **and promote to a build check per shared rule 21**.
5. **Resolved findings record the fix** — when a recurring finding is fixed, move it to Resolved with a note on what changed and which round fixed it.

### Calibration Update Procedure

After each review round, the review skill must:

1. Append a score history row — round number, date, type (`code` / `doc` / `design`), overall + per-dimension scores.
2. Update dimension benchmarks — baseline (round 1), current (this round), trend (improving / stable / declining).
3. Curate anchor examples — per dimension, keep the 2 best and 2 worst concrete examples. Replace weaker anchors when more illustrative ones are found.
4. Update recurring findings — if the same issue appears in 2+ consecutive rounds, mark as recurring.
5. Move resolved findings — if a previously recurring issue is confirmed fixed, record the resolution.
6. **Promote to build checks** — scan recurring findings for promotion criteria (per shared rule 21). Create or update `reviews/build-checks.md` with promoted checks. Retire stale checks.

The `type` parameter is the only skill-specific variation. Each review skill references this procedure rather than defining its own.

### What consumers depend on

- `/gvm-code-review` loads this file before dispatching review panels. Each panel receives the project-level calibration alongside expert principles. Reviewers see: "in this project, security scored 5 last round because of X" alongside "McConnell says Y."
- `/gvm-doc-review` loads this file before scoring. The reviewer sees the project's quality trajectory, not just abstract standards.
- Neither skill fails if the file does not exist — they run without project calibration on the first round.

---

## reviews/build-checks.md

**Producer:** `/gvm-code-review`, `/gvm-doc-review`, `/gvm-design-review` (promoted after calibration update per shared rule 21)
**Consumers:** `/gvm-build` (loaded during prompt generation), review skills (update "Last triggered")

### Purpose

Self-improving build mechanism. Recurring review findings are promoted to build checks that `/gvm-build` loads during prompt generation and applies during the code review loop. This creates a feedback path: review findings → build checks → fewer recurring findings.

### Required structure

1. **Header** — file title, expert grounding (Deming, Fagan, Hunt & Thomas), purpose statement.
2. **Active Checks** — build checks currently loaded by `/gvm-build`. Each check has: BC-{NNN} ID, root cause pattern, what to check, expert, originating findings, promoted date/round/reason, review type, last triggered round, status (active).
3. **Retired Checks** — checks no longer active. Same fields plus retirement date/round/reason.

### Build check format

| Field | Description |
|-------|-------------|
| **ID** | `BC-{NNN}` — sequential, zero-padded, never reused |
| **Tier** | `1` (permanent — general practice) or `2` (project-specific — tied to a library, SDK, or domain convention) |
| **Root cause** | The underlying pattern, not the symptom instance |
| **What to check** | Concrete, actionable instruction for the build prompt |
| **Expert** | Name, work, which expert's framework identified this |
| **Originating findings** | Finding IDs and rounds (e.g., "CR-R2-#3, CR-R3-#3, CR-R4-#3") |
| **Promoted** | Date, round number, reason (systemic / regression) |
| **Review type** | code / doc / design — which review type surfaced it |
| **Last triggered** | Round N — last round where this pattern was found |
| **Status** | active / retired |

### Rules

1. **Created on first promotion** — file does not exist until a finding first meets a promotion threshold.
2. **BC IDs are sequential and never reused** — even after retirement.
3. **Active checks are curated** — promoted in and retired out (tier 2 only). The list does not grow without bound.
4. **Tier 1 checks are never retired** — they represent general engineering practice (DRY, resource lifecycle, single source of truth) that applies regardless of recent trigger history.
5. **Tier 2 retirement requires user confirmation** — if a tier 2 check has not been triggered in 3 consecutive review rounds, present it to the user via AskUserQuestion as a retirement candidate. The user decides — they may know the check will be relevant when a dormant feature area is revisited.
6. **Retired checks are historical records** — not deleted, not loaded by consumers.

### What consumers depend on

- `/gvm-build` reads the Active Checks section during step 4 (GENERATE PROMPT). It filters by review type and includes relevant checks in the chunk prompt. If the file does not exist, the build proceeds without checks — no failure.
- Review skills (code-review, doc-review, design-review) read Active Checks during the calibration update to update "Last triggered" fields when current findings match active checks.

---

## .gvm-track2-adopted

**Producer:** `/gvm-init` (when the practitioner opts into the honesty-triad / Track-2 cross-cutting features), `/gvm-walking-skeleton` (creates on first successful skeleton run if absent)
**Consumers:** `/gvm-build` (presence gates the WS-5 skeleton-status check and the HS-1 stub-handover gate), `/gvm-code-review` (presence enables Panel E stub detection), `/gvm-test` (presence enables VV-2(a), VV-3(d), VV-4(c), VV-4(d) gates), `/gvm-status`

### Required structure

1. **YAML frontmatter** — `schema_version: 1` (loaded via `_schema.load_with_schema(path, "gvm_track2_adopted")`). The `gvm_track2_adopted` artefact key is registered in `_schema.CURRENT_SCHEMA_VERSIONS`.
2. **Presence-only marker** — the body may be empty after the frontmatter. The file's existence is the contract; its content beyond the schema_version line is not parsed.
3. **Location** — repository root (sibling to `STUBS.md`). It is a dotfile (no extension) and MUST be committed to source control so that adoption is durable across clones.

### What consumers depend on

- `/gvm-build` reads file existence (not content) to decide whether to run the WS-5 skeleton-status gate and the HS-1 chunk-handover gate. Projects without this marker run the legacy fast path (no Track-2 gates).
- `/gvm-code-review` dispatches Panel E (stub detection) only when this file is present and `gvm-code-review/scripts/_panel_e_prompt.py` exists in the plugin tree.
- `/gvm-test` enables the four honesty-triad / walking-skeleton VV gates only when this marker is present; otherwise the verdict evaluator runs the legacy three-gate path (per honesty-triad ADR-105).
- The schema_version is reserved for future migrations; current consumers do not read the body. Bumping the version requires an explicit migration in `_schema.py` per ADR-007.

---

## Artefact location summary

| Phase | Directory | Primary file | Paired HTML |
|---|---|---|---|
| Init | `init/` | `init-{NNN}.md` | `init-{NNN}.html` |
| Brief (optional) | `init/` | `brief-{NNN}.md` | `brief-{NNN}.html` |
| Requirements | `requirements/` | `requirements.md` (round 2: `requirements-002.md`) | `requirements.html` |
| Test Cases | `test-cases/` | `test-cases.md` (round 2: `test-cases-002.md`) | `test-cases.html` |
| Tech Spec | `specs/` (round 2: `specs-002/`) | `implementation-guide.md` + domain specs | Paired `.html` for each |
| Build | `build/` | `build/handovers/P{X}-C{XX}.md` | None |
| Code Review | `code-review/` | `code-review-{NNN}.html` | HTML only (no MD pair) |
| Design Review | `design-review/` | `design-review-{NNN}.html` | HTML only (no MD pair) |
| Doc Review | `doc-review/` | `{document-name}-review-{date}.html` | HTML only (no MD pair) |
| Site Survey | `site-survey/` | `site-survey-{NNN}.md` | `site-survey-{NNN}.html` |
| Test | `test/` | `test-{NNN}.html` | HTML only (no MD pair) |
| Build Summary | `build/` | `build-summary.md` | `build-summary.html` |
| Calibration | `reviews/` | `calibration.md` | None |
| Build Checks | `reviews/` | `build-checks.md` | None |

---

## GVM Home Directory State Files

User data that survives plugin updates lives in `~/.claude/gvm/`. These are not pipeline artefacts (they don't flow between skills in a pipeline) but they are consumed by skills during reference file loading. Schema and lifecycle defined in `shared-rules.md` rule 14.

| File | Producer | Consumer | Format |
|------|----------|----------|--------|
| `expert-activations.csv` | All GVM skills (append on load/cite) | `/gvm-experts`, `/gvm-status` | CSV, append-only |
| `discovered-experts.jsonl` | Any skill running Expert Discovery (shared rule 2) | Any skill loading a reference file (re-insertion check, shared rule 14) | JSONL, append-only, `schema_version: 1` |
| `rescore-log.jsonl` | `/gvm-experts` (rescore operations) | Any skill loading a reference file (re-insertion check, shared rule 14) | JSONL, append-only, `schema_version: 1` |
| `docs/plugin-guide.html` | Bootstrap (copied from plugin on each run) | User (read-only reference) | HTML |

---

## Contract versioning

These contracts are versioned with the plugin. If a producing skill needs to change its output structure, the corresponding consumer skills must be updated in the same release. The contracts are the coordination point — check here first when modifying any skill's output format.
