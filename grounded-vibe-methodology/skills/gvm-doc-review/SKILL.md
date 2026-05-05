---
name: gvm-doc-review
description: Use when reviewing documents for quality. Triggered by /gvm-doc-review command, requests to review or audit a document, or requests to check document quality. Dispatches parallel defect-class panels (Structure, Traceability, Content Quality, Scoring) as subagents. Auto-detects document types, presents multi-select when multiple types found, scores out of 10, and outputs a Tufte/Few styled HTML report with prioritised issues.
---

# Document Review

## Overview

Reviews project documents by dispatching parallel defect-class subagents. Each subagent scans for a specific *class* of defect, not a broad area of quality. Panels are partitioned so their scanning mandates are orthogonal — minimal overlap, maximum first-pass coverage. Covers both pipeline artefacts (requirements, test cases, specs) and standalone documents (presentations, strategy, newsletters, training materials, user documentation). Auto-detects document types, presents a multi-select when multiple types are found, and outputs a scored HTML report with prioritised issues.

**This skill is a quality gate.** It catches problems before they propagate downstream in the pipeline: `/gvm-requirements` → `/gvm-test-cases` → `/gvm-tech-spec` → `/gvm-build`.

**Shared rules:** At the start of this skill, load `~/.claude/skills/gvm-design-system/references/shared-rules.md` and follow all rules throughout execution. Load `~/.claude/skills/gvm-design-system/references/expert-scoring.md` when scoring experts.

## Methodological Basis

The panel structure is grounded in published inspection research, not convention:

- **Orthogonal defect partitioning** (Laitenberger, Atkinson, Schlich & El Emam, "An experimental comparison of reading techniques for defect detection in UML design documents", Fraunhofer IESE, *Journal of Systems and Software*, 2000): Perspective-Based Reading (PBR) assigns each reviewer a non-overlapping scanning mandate. PBR teams detected 41% more unique defects than checklist-based teams at 58% lower cost per defect.
- **Satisfaction of Search mitigation** (Drew, Võ & Wolfe, "The Invisible Gorilla Strikes Again", 2013): After finding one defect in a region, the probability of detecting a second drops. The fix: scan the entire artefact once per defect class rather than once for all classes. Each panel makes focused passes for its class.
- **Liberal criterion on first pass** (Signal Detection Theory, Green & Swets, 1966): Set the detection threshold low on R1 (flag borderlines), filter false positives in synthesis. This maximises recall at acceptable precision cost. R2+ raises the bar to strict.
- **Capture-recapture estimation** (Wohlin, Petersson & Aurum, adapted for software inspection): After R1, count panel overlaps to estimate the total defect population and calculate whether R2 is needed rather than guessing.

## Hard Gates

These steps are non-negotiable. If you skip any of them, the review output is invalid.

1. **DISPATCH PANELS IN PARALLEL.** YOU MUST dispatch all panels (A, B, C, D) as concurrent subagents via the Agent tool — all in a single message. If you review sequentially instead of in parallel, you are not executing this skill correctly. Parallel dispatch is the core value of defect-class partitioning.

2. **LOAD REVIEW CRITERIA BEFORE SCORING.** YOU MUST read:
   - (1a) `~/.claude/skills/gvm-doc-review/references/review-criteria.md` (this skill's local scoring rubrics)
   - (1b) `~/.claude/skills/gvm-design-system/references/review-reference.md` (design system assessment methodology — per shared rule 5)

   These are two distinct files; both are required. DO NOT score documents without loading both criteria files first.

3. **MULTI-SELECT WHEN MULTIPLE TYPES FOUND.** When multiple document types are detected, YOU MUST present a multi-select via AskUserQuestion. DO NOT auto-review all documents — the user decides which types to review.

4. **WRITE HTML BEFORE PRESENTING.** The review report is HTML-only — the user reads the HTML to make approval decisions, and no downstream skill parses a Markdown version. The HTML must exist before presenting findings or offering next steps (shared rule 13 exception for review reports).

5. **UPDATE CALIBRATION.** After presenting scores, YOU MUST create or update `reviews/calibration.md`. DO NOT end the review without it.

6. **VERDICT.** Every review must include a verdict using the type-specific language from `review-reference.md`. The verdict appears in the score summary section of the report and in the text presented to the user. DO NOT end a review without a verdict.

7. **USER OWNS FINDING TRIAGE (shared rule 28 — Review Finding Triage Is User-Owned).** Every Critical or Important finding emitted by panels MUST be presented to the user before any disposition is recorded. This skill MAY recommend "fix / defer / dismiss" per finding but MUST NOT decide. The Finding Quality Gate is the panels' emit threshold under R2+ strict — not a post-synthesis filter for Claude to invoke after panels return. Forbidden patterns (canonical phrasing — match shared-rules.md § 28 verbatim):

   - Recording emitted findings as "filtered under strict criterion" without user input.
   - Recording emitted findings as "deferred to v{N}.{M}.{P} hardening" without user input.
   - Bundling the verdict with the user's first sight of the finding list. Verdict comes after triage, not before.
   - Presenting a summary count that hides which findings were deferred (zero-deferred summaries are permitted).

   See shared-rules.md § 28 for the full permitted list and rationale.

8. **STANDALONE DOCUMENT FINDING QUALITY GATE — six-test emit threshold.** When reviewing standalone documents (whitepapers, blog posts, strategy, training, newsletters, presentations, user documentation), panels MUST apply the six-test gate before emitting Critical or Important findings. A finding earns Critical/Important status only if it passes at least one of the six tests below. Findings that pass none are tagged `[POLISH]` and recorded as Minor. The gate replaces the generic "consumer FAIL" criterion (which fits code/spec review but is too vague for prose).

   The six tests:

   1. **Integrity** — A reader who can verify the claim against a published source would find the claim wrong, partially wrong, or unsupported. (Misquoted source, wrong year, wrong edition, wrong attribution, fabricated statistic, broken citation chain.)
   2. **Misdirection (load-bearing)** — A reader could come away with the wrong understanding of a *load-bearing claim* (the thesis, a section's central argument, a numerical result, a methodology decision). Peripheral misdirection is Minor, not Important.
   3. **Reproducibility** — A researcher attempting to replicate an empirical claim from the document alone would lack a piece of information they need. (Unstated multipliers, undisclosed prompts, effect sizes without their measurement rubric, dataset details absent.) Applies primarily to methodology and empirical papers.
   4. **Honesty of scope** — The document claims more than its evidence supports, OR fails to flag a significant limitation where the unqualified claim would mislead. The "Brooks well-tested-scaffolding" failure mode applied to the paper itself: a paper that implicitly oversells while explicitly disclosing elsewhere is still a paper that oversells.
   5. **Audience hospitality** — The document assumes reader knowledge inconsistent with its stated audience. Distinct from Misdirection: the reader doesn't form a *wrong* understanding, they form *no* understanding. (Unflagged jargon, undefined acronyms, implicit prior knowledge of a specialist field.)
   6. **Cut-damage protection (inverted thesis-contribution test)** — When a finding *recommends a cut*, the cut must NOT damage orientation, evidence, scope-limits, or honesty disclaimers. A finding that fails this test is rejected — the section stays. This is a guard against over-trimming, not a license for it. Aggressive thesis-contribution cutting strips the things that protect the paper's credibility.

   Findings that fail all six tests are recorded as Minor `[POLISH]` and do not block publication. Findings that pass at least one are Critical or Important and require user triage per Hard Gate 7.

   The gate applies to standalone documents only. Pipeline artefacts (requirements, test cases, specs) continue to use the generic consumer-FAIL criterion because their consumers are concrete downstream skills.

## Input

Auto-detects document type by scanning the project for known file patterns:

### Pipeline Documents

| Document Type | Detection Pattern | Criteria Source |
|---|---|---|
| Requirements | `requirements/requirements.md` or `.html` | Requirements criteria from `~/.claude/skills/gvm-doc-review/references/review-criteria.md` |
| Test Cases | `test-cases/test-cases.md` or `.html` | Test case criteria from `~/.claude/skills/gvm-doc-review/references/review-criteria.md` + test quality criteria below |
| Specs (any) | `specs/*.md` or `.html` | Spec criteria from `~/.claude/skills/gvm-doc-review/references/review-criteria.md` |

### Standalone Documents

| Document Type | Detection Pattern | Criteria Source |
|---|---|---|
| User Documentation | `README.md`, `docs/*.md`, `docs/*.html`, help pages | User documentation criteria below + `domain/user-documentation.md` |
| Presentations | `presentations/*.html` | Presentation criteria below + `domain/presentation-design.md` + `domain/data-presentation.md` |
| Strategy | `strategy/*.md` or `.html` | Strategy criteria below + `domain/strategy.md` |
| Newsletters | `newsletters/*.md` or `.html` | Newsletter criteria below + `domain/newsletter.md` |
| Training Materials | `training/*.md` or `.html` | Training criteria below + `domain/training.md` |

### Multi-Select

When multiple document types are detected, present a multi-select via AskUserQuestion — do not auto-review all. The user selects which types to review:

**Question:** "I found the following documents. Which would you like me to review?"

List each detected type with a checkbox. Pre-check pipeline documents (requirements, test cases, specs) since they're the primary quality gate. Leave standalone documents unchecked by default. The user can select any combination.

If only one document type is detected, skip the multi-select and review it directly. If the user specifies a path, review that file only regardless of what else is detected.

Cross-document consistency checks apply only to pipeline documents (requirements ↔ test cases ↔ specs). Standalone documents are reviewed independently.

### Test Case Quality Criteria (applied when reviewing test cases)

In addition to the standard document quality criteria, test case documents are reviewed for:

1. **Technique appropriateness** — are the test techniques proportional to the risk? High-risk requirements should use boundary value analysis, equivalence partitioning, and edge case testing. Low-risk requirements can use simple positive/negative tests.
2. **Boundary value correctness** — for boundary-based tests, are the boundary values correct? A boundary test for "age must be 18-65" should test 17, 18, 65, 66 — not just 18 and 65.
3. **Coverage completeness** — does the test suite cover all requirements? Are there requirements with no corresponding test cases? Are there requirement paths (error cases, edge cases) that have no tests?
4. **Redundancy** — are there multiple tests covering the same path while leaving other paths untested? Redundant tests waste effort without improving coverage.
5. **Testability** — can each test case actually be executed as written? Are the preconditions achievable? Are the expected results observable and verifiable?

### User Documentation Criteria (applied when reviewing user docs)

User documentation is reviewed using user documentation specialists from `domain/user-documentation.md` and writing specialists from `writing-reference.md`:

1. **Task-oriented structure** — is the documentation organised by what the user needs to do, not by what the software features are? "How to create a project" is task-oriented; "The Projects Screen" is feature-oriented.
2. **Self-contained pages** — can each page be understood on its own, or does it assume the reader has read previous pages? Users arrive via search, not via sequential reading.
3. **Microcopy quality** — are error messages helpful? Do button labels describe the action? Are empty states used as onboarding opportunities?
4. **Accuracy** — does the documentation match the current state of the implemented system? Stale screenshots, wrong navigation paths, and missing features are Critical findings.
5. **Scannability** — can users find what they need by scanning? Are headings descriptive? Are steps numbered? Are key terms bold?

### Presentation Criteria (applied when reviewing presentations)

Presentations are reviewed using presentation design specialists from `domain/presentation-design.md` and data presentation specialists from `domain/data-presentation.md`, plus document structure specialists from `domain/document-structure.md`:

1. **One idea per slide** — does each slide carry a single, clear message? Multi-point slides are a Critical finding.
2. **Headlines as sentences** — are slide headlines complete sentences that state the point, not topic labels? "Revenue increased 23% in Q3" vs "Q3 Revenue."
3. **Narrative arc** — does the presentation have a clear beginning, middle, and end? Does it alternate between "what is" and "what could be"?
4. **Visual restraint** — is the signal-to-noise ratio high? No decorative clipart, no template chrome, no gratuitous animation. Every element earns its place.
5. **Data slide clarity** — do data slides state the "so what?" in the headline? Is the visualisation appropriate (tables for precision, charts for trends)? Data-ink ratio?

### Strategy Document Criteria (applied when reviewing strategy docs)

Strategy documents are reviewed using strategy specialists from `domain/strategy.md`:

1. **Kernel completeness** — does the document contain all three elements: diagnosis, guiding policy, and coherent actions? Missing any element is a Critical finding.
2. **Diagnosis quality** — does the diagnosis identify the actual challenge (the crux), or does it describe symptoms? A diagnosis that lists problems without identifying the critical one is weak.
3. **Guiding policy clarity** — is there a clear approach, or are goals and aspirations substituted for strategy? "Become the market leader" is an aspiration, not a guiding policy.
4. **Action coherence** — do the actions reinforce each other, or do they pull in different directions? Incoherent actions are an Important finding.
5. **Bad strategy signals** — check for fluff (buzzwords), failure to face the challenge, goals masquerading as strategy, and incoherent objectives.

### Newsletter Criteria (applied when reviewing newsletters)

Newsletters are reviewed using newsletter and content writing specialists from `domain/newsletter.md`:

1. **Single core message** — does the newsletter have one clear message, or does it try to cover everything?
2. **Reader utility** — can the reader do something with this information? Utility over abstraction.
3. **Specificity** — are claims supported with concrete examples, real numbers, and named things? Generic content is an Important finding.
4. **Hook quality** — does the opening earn the next sentence? The first paragraph determines whether the reader continues.
5. **Scannability** — short paragraphs, subheadings, bold key phrases. Can a scanner extract the core message in 10 seconds?

### Training Material Criteria (applied when reviewing training content)

Training materials are reviewed using training and instructional design specialists from `domain/training.md`:

1. **Learning objectives** — are objectives stated clearly at the start? Does each section map to an objective?
2. **Gap type match** — is training the right solution? If the problem is motivation or environment, training won't fix it.
3. **Practice activities** — does the material include practice (exercises, scenarios, decision-making), not just information presentation? Passive reading is not learning.
4. **Multimedia principles** — are words and relevant images used together? Is extraneous material removed? Are related text and graphics spatially contiguous?
5. **Segmentation** — is complex content broken into learner-paced segments, or presented as a continuous wall of text?

## Industry Domain Grounding (Tier 2b)

When reviewing, check whether the application's business domain has an industry domain reference file in `~/.claude/skills/gvm-design-system/references/industry/`. If a matching file exists, load it with the Read tool. Industry domain experts add a domain accuracy lens to the review — are the requirements using correct domain terminology? Do test cases cover the domain-specific scenarios that matter? Do specs make domain-appropriate architectural decisions? Flag domain inaccuracies as issues alongside the standard quality criteria.

## Defect-Class Panels

Panels are partitioned by defect class, not by document (Basili: orthogonal scanning mandates maximise first-pass detection). Every panel sees every document — partitioning is by defect class, not by document. Each panel makes two passes through every document.

**Panel definitions are in separate files, loaded based on document type:**

| Document category | Panel definition file | When loaded |
|---|---|---|
| Pipeline (requirements, test cases, specs) | `~/.claude/skills/gvm-doc-review/references/pipeline-panels.md` | Detected document is a pipeline artefact |
| Standalone (whitepapers, strategy, presentations, newsletters, training, user docs) | `~/.claude/skills/gvm-doc-review/references/standalone-panels.md` | Detected document is standalone |

**Why the split:** Pipeline documents need *mechanical* scanning — ID format compliance, traceability chains, contract structure. Standalone documents need *argumentative* scanning — does the reasoning hold, are citations accurate, does the prose work for the audience. Loading both wastes context on panel definitions that do not apply.

**Loading rule:** After step 1b (document selection), determine the category. If the selected documents are all pipeline artefacts, load `pipeline-panels.md`. If all standalone, load `standalone-panels.md`. If mixed (pipeline + standalone selected together), load both — but dispatch separate panel sets for each category. Do not apply pipeline panels to standalone documents or vice versa.

**Both panel files define the same four slots (A, B, C, D):**
- Pipeline: A = Structure & Contract Compliance, B = Traceability, C = Content Quality & Domain Accuracy, D = Scoring
- Standalone: A = Argument & Structure, B = Factual Accuracy & Attribution, C = Prose Quality & Audience Fit, D = Scoring

Panel D (Scoring) uses the same experts in both categories. Panels A-C use different experts and scanning methods appropriate to the document type.

## Criteria by Round

Detection threshold varies by round (Green & Swets, Signal Detection Theory: liberal criterion maximises recall on early passes):

**Round 1 (no calibration):** Liberal threshold. Flag anything that *might* be an issue, including borderline cases. Tag borderline findings as `[BORDERLINE]`. False positives are filtered during synthesis — the cost of a false positive is low (one extra finding to review), the cost of a false negative is high (missed defect propagates downstream). The goal is maximum recall.

**Round 2+ (calibration exists):** Strict threshold. Only findings where a consumer would FAIL or an executor would take WRONG ACTION. Apply the Finding Quality Gate from `review-reference.md`. For standalone documents (whitepapers, blog posts, strategy, training, newsletters, presentations, user docs), apply the six-test gate from Hard Gate 8 instead of the generic consumer-FAIL criterion. The first pass caught the bulk; now the signal-to-noise ratio matters more than coverage.

## Stopping Rule and Publication-Readiness (Standalone Documents)

Standalone-document review can run indefinitely on diminishing returns. The methodology is designed to keep finding things; without a stopping rule it becomes anxiety-driven, not quality-driven. The rule below converts "should we run another round?" from a feeling into a calculation.

A round is **terminal** (the document is publication-ready, further review is opt-in polish) when ALL of the following hold:

1. **Zero Critical findings** that pass the six-test gate (Hard Gate 8).
2. **Zero Important findings** on the four reader-impact tests: Integrity, Misdirection (load-bearing), Reproducibility, Honesty of Scope. (Audience Hospitality and Cut-damage Protection produce findings that need attention but do not by themselves block publication.)
3. **Both calibrated and blind Panel D scores meet the document's score threshold.** Default thresholds:
   - **Public-facing whitepaper** (named methodology, public release): ≥9.3
   - **Standard whitepaper, strategy doc, training material**: ≥9.0
   - **Newsletter, status report, internal blog**: ≥8.0
   The user can override per document.

   **Refinement — design-decision recurrence clause.** Condition 3 is satisfied when: calibrated ≥ threshold AND (blind ≥ threshold OR every blind-only concern below the threshold is *confirmed-recurring* across two or more rounds AND is explicitly addressed in the document by caveat, scope-disclaimer, or design-decision documentation). The clause exists because dual review by design does not show the blind panel prior fixes or the calibration story; once a deliberate scoping or caveat has been added to the document, the blind panel will keep surfacing the same architectural concern as if new. Without this clause, dual review will keep finding the same recurring concerns and the stopping rule will never trigger on documents that have done the work of scoping their claims. The clause is recorded in the calibration row's stopping-rule notes — the practitioner declares which specific blind concerns are design-decision-documented and where the documentation lives.
4. **The forcing function:** no more than two consecutive rounds may be verification-only. If round N is fix-and-verify and round N+1 is fix-and-verify, then round N+2 may verify, but round N+3 must declare the document either publication-ready or send it for restructure. This prevents indefinite polish loops.

When all four hold, the verdict in the report is **Publication-ready** and the user is told the cycle can stop. Subsequent rounds become opt-in polish, not quality gates.

When some hold but not all, the verdict reflects what's missing: *Proceed with named fixes* if Critical or Important findings remain; *Restructure* if the score threshold is far off and the gap is structural rather than fixable through edits.

### Pre-Publication Integrity Pass (recommended for high-stakes documents)

For any document at the ≥9.3 threshold (public-facing whitepaper), run a dedicated Integrity-only pass *after* the regular terminal round. This pass exists for one purpose: catch credibility-killers that survived earlier rounds.

The pass scans only for findings that pass the **Integrity** test from Hard Gate 8. Specifically:

1. **Direct-quotation verification.** Every direct quotation in the document is verified against the actual cited source via WebFetch or independent agent. Misquotes (wrong wording, wrong year, wrong attribution) are surfaced.
2. **Statistic verification.** Every specific statistic (e.g., "p < 0.001", "21.7%", "41% more defects") is checked against its cited source. Numbers that don't match the source, or that aren't traceable to a source at all, are surfaced.
3. **BC-3 extended scope.** Run the build-checks BC-3 audit at full scope: body prose, table cells, pipeline-phase descriptions, sidenotes, captions, appendix evidence blocks. Every body-named author appears in References; every References entry has body citations; no duplicates; companion-papers tracked.
4. **Title/topic match.** For every external paper cited, verify that the cited title matches what the source actually says it is about. (R76 caught a PRISM citation where the title didn't match the paper's actual topic; this is the failure mode this check is designed for.)
5. **Edition / date precision.** For every cited book, verify the edition cited contains the cited content. (The Brooks misquote went 1995 vs 1975 with edition-specific content; this check catches that class.)

The pass produces a single-page report listing only Integrity findings. It is mechanical and inspectable — a document that passes this pass with zero findings is one credibility-killer-free, by construction, against the checks that pass tests.

The pass is opt-in: invoke via `/gvm-doc-review` with the `--integrity-pass` flag (or its equivalent in conversational invocation: "run the integrity pass on this whitepaper"). It is recommended before any public release.

## Process

> **Sub-step convention:** Steps use lettered sub-steps (e.g., 1b, 2c). All sub-steps within a step are sequential and always run unless the sub-step heading states a condition.

0. **Bootstrap** — per shared rule 14, verify `~/.claude/gvm/` exists before writing output.
1. **Detect documents** — Use the Glob tool to scan for all document types in standard locations (pipeline + standalone)
1b. **Select documents** — if multiple types detected, present multi-select via AskUserQuestion (see Multi-Select above). If one type, proceed directly. If user specified a path, skip detection — Hard Gate 3 (multi-select) is structurally inapplicable on the explicit-path branch; all other Hard Gates (1, 2, 4, 5, 6) still apply.

1c. **Branch mode decision** — if the user specified a single document path OR only one document type was detected, this is a TARGETED review (light mode). If multiple types were detected and selected, this is a FULL review. In light mode, step 4 (cross-document consistency) is skipped. Hard Gates 1, 2, 4, 5, 6 remain mandatory in light mode (per shared rule 20: branch paths must re-state applicable gates). Hard Gate 3 applies only when multiple document types were present to select between.
2. **Load panel definitions and criteria** — determine document category (pipeline or standalone) from step 1b results. Load the matching panel definition file:
   - Pipeline artefacts → load `~/.claude/skills/gvm-doc-review/references/pipeline-panels.md`
   - Standalone documents → load `~/.claude/skills/gvm-doc-review/references/standalone-panels.md`
   - Mixed selection → load both; dispatch separate panel sets per category
   Then load `~/.claude/skills/gvm-doc-review/references/review-criteria.md`. For standalone documents, load type-specific domain specialist files from `~/.claude/skills/gvm-design-system/references/domain/` as specified in the panel definition file (e.g., `domain/strategy.md` for strategy docs). Always load `domain/document-structure.md`.
2b. **Load industry domain** — if an industry domain file exists, load it for domain accuracy checks
2c. **Load review methodology** — use the Read tool to load `~/.claude/skills/gvm-design-system/references/review-reference.md` (assessment methodology)
2d. **Load writing reference** — use the Read tool to load `~/.claude/skills/gvm-design-system/references/writing-reference.md` (report writing quality — per shared rule 5)
2e. **Log all loaded experts to activation CSV (per shared rule 1).**
2f. **Load project calibration** — if `reviews/calibration.md` exists, load it. Count the number of score history rows to determine the current round number. Extract per-dimension benchmarks, anchor examples, and recurring findings. Set criteria: R1 = liberal, R2+ = strict (see Criteria by Round). If 2+ prior rows, dual review applies (shared rule 16).
2g. **Load build checks** — if `reviews/build-checks.md` exists, load it. Active checks are used to update 'Last triggered' during the calibration update step.
3. **Dispatch panels** — dispatch Panels A, B, C, D as parallel subagents via the Agent tool — ALL IN A SINGLE MESSAGE. Each panel prompt includes:
   - Defect class mandate: "You scan for [class]. Do NOT scan for [other classes]."
   - Expert identities assigned to this panel (names + works — excerpted from loaded reference files)
   - ALL documents to review (every panel sees every document — partitioning is by defect class, not by document)
   - Relevant criteria excerpts (from `review-criteria.md` and type-specific criteria)
   - Scanning instruction: "Make two passes through every document:
     Pass 1: Systematic scan — read each document section by section for your defect class
     Pass 2: Cross-reference scan — trace relationships between documents for your defect class"
   - Criteria: "Liberal — flag borderlines as `[BORDERLINE]`" (R1) or "Strict — consumer FAIL only" (R2+)
   - Output format: Expert, Severity, Document:Section, Issue, Criteria Source, Fix (six fields — matches the canonical finding block in `pipeline-contracts.md`)

   **Subagent model (per shared rule 22):** Dispatch all panel subagents with `model: sonnet`. They are reading and classifying, not synthesizing.

   **DUAL REVIEW (round 3+ per shared rule 16):**
   - Dispatch a second set of panels IN PARALLEL with the calibrated panels
   - Blind panels receive the same documents, experts, and defect-class mandates
   - Blind panels do NOT receive calibration data, anchors, or resolved findings
   - Both sets complete before synthesis

3b. **Synthesise results** — after all panels complete:
   - Collect findings from all panels
   - Deduplicate (same issue found by multiple panels — keep most specific fix)
   - Filter `[BORDERLINE]` findings (R1 only):
     - Apply the consumer impact test to each borderline finding
     - Keep findings that pass; discard findings that fail
     - Record the filter ratio (borderlines kept / borderlines total) for calibration
     - A borderline that multiple panels independently flagged is promoted to confirmed
   - Cross-reference themes (issues that span multiple panels)
   - Elevate severity if 2+ panels independently flagged the same issue
   - **CAPTURE-RECAPTURE ESTIMATION (R1 only):**
     - Count overlapping findings between panel pairs
     - For panels i and j with n_i and n_j findings and m_ij shared:
       estimated total = (n_i x n_j) / m_ij (Lincoln-Petersen)
     - Average across panel pairs for robustness
     - Compare: unique findings found vs estimated total
     - Report: "Estimated N total defects; found M unique (coverage: M/N)"
     - If coverage < 80%: recommend R2
     - If coverage >= 80%: R2 is optional (note in report)
     - (Wohlin, Petersson & Aurum: capture-recapture adapted for software inspection)

3c. **Reconcile** (round 3+ only, when dual review ran) — classify each blind panel finding:

   - **New** — not present in the calibrated findings AND not in the resolved findings history. This is a genuine blind spot that calibration missed. **Merge into the final report** with a tag indicating it came from the blind review.
   - **Confirmed** — independently found by both reviewers. Increases confidence in the finding. **Keep the calibrated version** (it has better context) and note the independent confirmation.
   - **Rediscovered** — matches a finding already in the calibrated report. **Discard** — the calibrated reviewer already caught it.
   - **Regression** — matches a finding in the resolved findings history (was fixed in a prior round, now flagged again). **Merge into the final report** as a regression finding. The calibrated reviewer may have trusted the prior resolution and not re-checked.
   - **Noise** — matches an acknowledged decision (from `requirements-health-report-decisions.md`) or a finding the calibrated reviewer correctly excluded based on project context. **Discard**.

   The reconciliation produces a single merged findings list. The practitioner sees one report, not two.

4. **Cross-document consistency** — check traceability across documents (Panel B covers cross-references, but this step validates the full traceability matrix across all document types)
5. **Score** — rate each document 0-10 and compute an overall score. Panel D provides the rubric-based scoring; this step synthesises Panel D's output with findings from Panels A-C to produce final scores. Where possible, count rather than judge (Marzano: "don't score what you can count"). Separate finding issues from scoring (Fagan).
5b. **Source verification (externally-supplied documents only)** — for documents not auto-detected as pipeline artefacts: if factual accuracy scored below 7, run the source verification protocol from `~/.claude/skills/gvm-design-system/references/source-verification.md` for claims that scored poorly. If the file does not exist, skip and note in the report.
6. **Write report** — log cited experts to activation CSV (per shared rule 1). Output HTML only to `doc-review/{document-name}-review-{date}.html`. The `{document-name}` is derived from the reviewed file's name (e.g., `whitepaper` from `whitepaper-grounded-vibe-methodology.html`, `requirements` from `requirements/requirements.html`). For multi-document reviews, use the primary document's name. For full pipeline reviews (requirements + test-cases + specs), use `pipeline` as the document name. For two-document reviews, use the upstream document's name. When two documents are from the same pipeline tier or both standalone, use the first document selected as the name. Append `-r2`, `-r3` etc. for subsequent reviews of the same document on the same date. Include a summary table: panels run, findings per severity, capture-recapture estimate (R1). Include borderline filter results (R1): how many kept, how many discarded, filter ratio. When dual review was used, include a "Blind Review Findings" section listing findings that only the uncalibrated panels caught, and a "Regressions" section for previously-resolved issues that resurfaced.
7. **Update calibration** — create or update `reviews/calibration.md` per the calibration contract in `pipeline-contracts.md`:
   - Append score history row (round, date, type=doc, per-dimension scores)
   - Record capture-recapture data (R1): estimated total, unique found, coverage %
   - Record borderline filter ratio (R1): kept/total
   - Update dimension benchmarks (baseline, current, trend)
   - Curate anchor examples (2 best + 2 worst per dimension from this project)
   - Update recurring findings (issues in 2+ consecutive rounds)
   - Move resolved findings (issues from prior rounds confirmed fixed)
   - Record dual review metadata: how many findings came from each source (calibrated-only, uncalibrated-only, confirmed-by-both, regressions). This data reveals whether calibration is developing blind spots over time.
   - Promote eligible findings to build checks (per shared rule 21): scan recurring findings for 3+ rounds or regression; create/update `reviews/build-checks.md`; update "Last triggered" for matching active checks; retire stale checks.

## Dual Review: Calibrated + Blind

This skill implements shared rule 16 (Dual Review). See `shared-rules.md` for the full mechanism, reconciliation categories, and research basis. The key points for doc-review:

- **Automatic trigger** — from round 3 onwards, when `calibration.md` contains score history rows for at least 2 completed prior rounds (per shared rule 16)
- **Two parallel sets of panels** — calibrated panels (A-D with full project history) and blind panels (A-D with same criteria and experts, no calibration data). Both sets dispatched in the same parallel message.
- **Reconciliation** (step 3c) classifies each blind panel finding as new, confirmed, regression, rediscovered, or noise — only new and regression findings merge into the final report
- **Report includes** "Blind Review Findings" and "Regressions" sections when dual review runs
- **Metadata recorded** in calibration file to track calibration bias over time

## Scoring

Each document is scored 0-10 based on weighted criteria. The score reflects quality relative to what the relevant experts would expect.

| Score | Meaning |
|---|---|
| 9-10 | Publication quality. Could be used as a teaching example. |
| 7-8 | Strong. Minor issues that don't affect usability. |
| 5-6 | Adequate. Some issues that should be addressed before building. |
| 3-4 | Weak. Significant gaps that will cause problems downstream. |
| 1-2 | Incomplete. Missing critical content. |
| 0 | Document doesn't exist or is empty. |

The overall project score is the weighted average: requirements (30%), test cases (25%), specs (30%), cross-document consistency (15%).

## Issue Priority

Issues are categorised into three tiers:

| Tier | Label | Meaning | HTML Colour |
|---|---|---|---|
| **Critical** | Must fix before building | Blocks the pipeline. Missing requirements, untraceable tests, contradictory specs. | `#c0392b` (red) |
| **Important** | Should fix soon | Weakens quality but doesn't block. Vague requirements, missing edge case tests, light spec sections. | `#e67e22` (orange) |
| **Minor** | Nice to improve | Polish items. Wording improvements, optional coverage gaps, style inconsistencies. | `#7f8c8d` (grey) |

## Cross-Document Consistency Checks

When multiple document types exist, check:

- **Requirements → Test Cases:** Every requirement ID has at least one test case. Flag uncovered requirements.
- **Requirements → Specs:** Every requirement ID appears in at least one spec section. Flag unspecified requirements.
- **Test Cases → Specs:** Test cases reference spec sections where relevant. Flag tests that can't be implemented from the specs.
- **Specs → Requirements:** Every spec section traces to requirement IDs. Flag spec sections with no requirement basis (scope creep).
- **Vocabulary consistency:** Are the same concepts named consistently across documents?

## Review Criteria by Document Type

All review criteria are defined in `~/.claude/skills/gvm-doc-review/references/review-criteria.md`. Load it at the start of the review. The reference file defines scoring rubrics (10 criteria per document type, 1 point each) with specific score thresholds for full/partial/missing. Apply the criteria for each document type as defined there.

### Pipeline document types (rubrics in `~/.claude/skills/gvm-doc-review/references/review-criteria.md`):
- **Requirements** — 10 quality criteria covering completeness, correctness, feasibility, necessity, prioritisation, unambiguity, verifiability, consistency, traceability, and structure
- **Test Cases** — 10 criteria covering requirement coverage, traceability, technique selection, boundary values, negative cases, consumer realism, priority alignment, concrete values, behaviour naming, and document quality
- **Specs** — 10 criteria covering decomposition, architecture clarity, risk-proportional depth, decision capture, quality attributes, conceptual integrity, requirement traceability, implementation guide, expert activation, and document quality

### Standalone document types (criteria defined in this skill):
- **User Documentation** — 5 criteria: task-oriented structure, self-contained pages, microcopy quality, accuracy, scannability
- **Presentations** — 5 criteria: one idea per slide, headlines as sentences, narrative arc, visual restraint, data slide clarity
- **Strategy** — 5 criteria: kernel completeness, diagnosis quality, guiding policy clarity, action coherence, bad strategy signals
- **Newsletters** — 5 criteria: single core message, reader utility, specificity, hook quality, scannability
- **Training Materials** — 5 criteria: learning objectives, gap type match, practice activities, multimedia principles, segmentation

## Output

**Report saved to:** `doc-review/{document-name}-review-YYYY-MM-DD.html` (HTML only — review reports are not parsed by downstream skills, so no paired MD is produced; see shared rule 13 exception).

**HTML generation:** Dispatch the HTML report generation as a Haiku subagent (`model: haiku`). Per shared rule 22.

Uses the shared design system. Use the Read tool to load both `~/.claude/skills/gvm-design-system/references/tufte-html-reference.md` (core) and `~/.claude/skills/gvm-design-system/references/tufte-review-components.md` (verdict box, score card, issue blocks, criterion rows) before writing.

### Report Structure

```html
<!-- Verdict before score card — use the three-child canonical form per review-reference.md -->
<div class="verdict ready"><!-- use class .ready | .caveats | .not-ready per verdict severity -->
  <div class="verdict-label">Verdict</div>
  <div class="verdict-text"><!-- type-specific verdict string from review-reference.md (e.g. "Proceed", "Revise first") --></div>
  <div class="verdict-basis"><!-- one-to-two sentences on why this verdict --></div>
</div>

<!-- Score summary at top -->
<div class="score-card">
  <div class="overall-score">7.2 / 10</div>
  <div class="score-breakdown">
    <div class="score-item">Requirements: 8/10</div>
    <div class="score-item">Test Cases: 7/10</div>
    <div class="score-item">Specs: 6/10</div>
    <div class="score-item">Consistency: 8/10</div>
  </div>
</div>

<!-- Issues by tier -->
<h2>Critical Issues (3)</h2>
<!-- issue blocks -->

<h2>Important Issues (7)</h2>
<!-- issue blocks -->

<h2>Minor Issues (4)</h2>
<!-- issue blocks -->

<!-- Per-document detailed review -->
<h2>Requirements Review — 8/10</h2>
<!-- criteria-by-criteria assessment -->

<h2>Test Cases Review — 7/10</h2>
<!-- ... -->

<h2>Specs Review — 6/10</h2>
<!-- ... -->

<h2>What Prevents a Higher Score</h2>
<!-- for each dimension below 10, one sentence: the gap and whether closing it is worth the cost -->

<h2>Cross-Document Consistency — 8/10</h2>
<!-- traceability matrix, vocabulary check -->
```

**"What Prevents a Higher Score"** — for each dimension below 10, state in one sentence the gap and whether closing it is worth the cost. Distinguishes fixable gaps from structural ceilings. Placement: after score trajectory (round 2+) or dimension detail (round 1), before expert panel (per `review-reference.md`).

The `<div class='verdict'>` element appears before the `<div class='score-card'>` in the HTML output.

### CSS

The CSS for review components (`.verdict`, `.score-card`, `.overall-score`, `.score-breakdown`, `.issue`, `.issue.critical/important/minor`, `.criterion`) lives in `tufte-review-components.md`. Append those rules to the core CSS from `tufte-html-reference.md` in your HTML output.

## Context Window Management

- Read each document once, fully
- Load review criteria reference once
- Write the report incrementally per shared rule 18 — scaffold first, then score card, issues by tier, per-document reviews, each as a separate Edit operation
- For cross-document checks, read requirement IDs from the requirements index, then scan test cases and specs for those IDs — don't re-read full documents

## Key Rules

1. **Parallel dispatch is the point** — panels run as concurrent subagents, all dispatched in a single message.
2. **Panels are orthogonal by defect class, not by document** — each panel scans for a specific class of defect across ALL documents. No two panels scan for the same class (Basili: orthogonal mandates maximise unique findings).
3. **Every panel sees every document** — partitioning is by defect class, not by document. A document with both a structure gap and a traceability error is found by Panel A and Panel B respectively.
4. **Two passes per panel** — systematic scan (section-by-section enumeration) then cross-reference scan (relationship tracing). This mitigates the satisfaction-of-search effect (Drew & Wolfe: scanning for one class at a time prevents premature termination).
5. **Liberal R1, strict R2+** — R1 uses a low detection threshold to maximise recall (Green & Swets: liberal criterion). R2+ applies the Finding Quality Gate (consumer FAIL only).
6. **Capture-recapture after R1** — estimate remaining defect population from panel overlaps (Wohlin: Lincoln-Petersen estimator). This converts "should we do R2?" from a guess into a calculation.
7. **Depth is proportional to risk** (Fairbanks). Light mode is determined at step 1c, not repeated here. Full reviews run every step; targeted (light) reviews skip step 4 only. Refer to step 1c for the branch mode decision and gate applicability.
8. **Auto-detect then multi-select** — scan standard paths for all document types (pipeline + standalone). When multiple types found, present a multi-select via AskUserQuestion — do not auto-review all. Pre-check pipeline documents. The user chooses.
9. **Always check cross-document consistency** when multiple document types exist (skip in light mode)
10. **Score every document** — 0-10 with clear criteria
11. **Prioritise issues** — Critical/Important/Minor with actionable descriptions
12. **Be specific** — cite the requirement ID, test case ID, or spec section where the issue lives
13. **Be constructive** — every issue should suggest how to fix it
14. **Don't re-review acknowledged items** — if requirements-health-report-decisions.md exists, respect acknowledged decisions
15. **Use AskUserQuestion** only if the review finds ambiguities that need user input — otherwise the review runs autonomously and produces the report
16. **Experts who find should fix** — per shared rule 3.
17. **Expert discovery for uncovered domains** — per shared rule 2. Include discovered experts in the review findings.
18. **HTML-only output** — review reports are HTML only. No downstream skill parses review MD, so no paired MD is produced (shared rule 13 exception for review reports).
19. **Dual review is automatic** — do not ask the practitioner whether to run dual review. Dual review triggers per shared rule 16. See `shared-rules.md` for the canonical trigger condition. The cost (one extra parallel set of panels + reconciliation) is justified by the systematic blind spots that calibration introduces. The practitioner sees one merged report, not two.
20. **Synthesise, don't just aggregate** — identify cross-panel themes, elevate severity for multi-panel findings.
