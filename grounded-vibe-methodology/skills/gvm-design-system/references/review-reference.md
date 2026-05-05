# Review and Assessment Reference

Apply these experts' principles when designing or executing any review — plugin reviews, document reviews, code reviews, experiment scoring. Load this file before any review activity.

The central problem: uncalibrated reviewers produce inconsistent measurements. The variation is in the measurement system, not the artefact being measured (Deming). Every principle below addresses this.

## Measurement System Integrity

---

### W. Edwards Deming

**Source:** *Out of the Crisis*, MIT Press (1986)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 5 | 5 | 3 | **Canonical** |

Evidence: Authority — father of TQM; Deming Prize named after him; credited with Japan's post-war industrial transformation. Publication — MIT Press. Breadth — principles embedded in ISO 9001, Six Sigma, Lean, DevOps. Adoption — required reading in industrial engineering and quality assurance globally.

**Work score — *Out of the Crisis*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 3 | 5 | 2 | 5 | **Established** |

Evidence: Depth — 507 pages; definitive treatment of common vs special cause variation. Influence — cited in Juran, Humphrey; reproduced in ISO training materials.


- Before improving a process, stabilise the measurement system. If the gauge varies, you cannot tell whether product changes are real.
- Distinguish common-cause variation (inherent in the system) from special-cause variation (something specific changed). Score differences between review rounds are common-cause unless the criteria also changed.
- Operational definitions are everything. "Quality" means nothing until you define how to measure it and what the measurement means.
- Do not compare scores across rounds unless the measurement instrument (criteria, anchors, calibration) is identical.

---

### Lee Cronbach

**Source:** *Coefficient Alpha and the Internal Structure of Tests*, Psychometrika (1951); *Generalizability Theory* (with Gleser, Nanda, Rajaratnam), Wiley (1972)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 4 | 5 | 3 | **Established** |

Evidence: Authority — alpha is the most widely used reliability statistic; 100,000+ Google Scholar citations. Publication — Psychometrika (premier quantitative psychology journal); Wiley. Breadth — adopted in medical education, organisational research, language testing. Adoption — alpha is standard output in SPSS, R, SAS.

**Work score — *Coefficient Alpha and the Internal Structure of Tests*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 4 | 4 | 1 | 5 | **Established** |

Evidence: Specificity — specific formula with derivation and decision rules. Depth — full mathematical derivation connecting to Kuder-Richardson. Influence — 100,000+ citations; mandatory reporting in clinical trial measurement.

*Boundary case: avg 4.4, within 0.1 of Canonical boundary (4.5). Pending rescore deferred — current classification Established is operationally correct. To resolve: run /gvm-experts to confirm Breadth dimension.*

**Work score — *Generalizability Theory*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 4 | 5 | 2 | 4 | **Established** |

Evidence: Specificity — defines G-study/D-study framework with specific variance component procedures. Depth — full mathematical treatment of variance components framework. Influence — standard in medical education and large-scale testing programmes (ETS, ACT).


- Separate the variance: artefact variance (what you want to measure), rater variance (reviewer calibration differences), occasion variance (different day, different context), and error.
- High inter-rater reliability (alpha > 0.8) means the instrument is measuring the artefact, not the rater. Low reliability (alpha < 0.5) means rater variance dominates — the scores tell you more about the reviewer than the artefact.
- Reliability is a property of the instrument, not the artefact. A bad rubric produces unreliable scores on any artefact.
- Report reliability alongside scores. A score of "8.0" with alpha 0.4 carries less information than a score of "7.0" with alpha 0.9.

## Rubric Design

---

### Tom Gilb

**Source:** *Competitive Engineering*, Elsevier (2005)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 4 | 3 | 3 | 3 | 3 | **Recognised** |

Evidence: Authority — originated Evo and Planguage; IEEE Harlan Mills Award recipient.

**Work score — *Competitive Engineering*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 4 | 3 | 3 | **Established** |

Evidence: Specificity — five-component criterion (Scale, Meter, Benchmark, Target, Tolerance) is among the most operationally specific frameworks in requirements literature. Depth — 688 pages of comprehensive quantified requirements treatment.


- Every quality criterion must have five components:
  1. **Scale** — what is being measured (e.g., "percentage of non-data pixels in chart area")
  2. **Meter** — how it is measured (e.g., "reviewer counts decorative elements per panel")
  3. **Benchmark** — current level or baseline (e.g., "ungrounded dashboards average 6.7")
  4. **Target** — desired level (e.g., "above 8.5 under expert review")
  5. **Tolerance** — acceptable range (e.g., "7.5–10")
- If you cannot define all five, the criterion is too vague to measure reliably.
- "Good architecture" is not a criterion. "Number of architectural decisions with documented rationale and reviewed consequences" is.

---

### Dannelle Stevens & Antonia Levi

**Source:** *Introduction to Rubrics* (2nd ed.), Stylus (2013)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 3 | 3 | 3 | 3 | 4 | **Recognised** |

Evidence: Currency — 2nd edition 2013; rubric design problem has not fundamentally changed.

**Work score — *Introduction to Rubrics* (2nd ed.):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 3 | 3 | 3 | **Established** |

Evidence: Specificity — step-by-step rubric construction with concrete good/bad descriptor examples and dimension independence testing.


- **Analytic rubrics** (separate score per dimension) are more reliable than **holistic rubrics** (single overall impression). Always use analytic rubrics for formal review.
- Each score level needs **concrete descriptors** — observable, countable qualities, not vague adjectives.
  - Bad: "7-8: mostly good with minor issues"
  - Good: "7: right-aligned numbers in all tables; one table has inconsistent decimal places. 8: all tables right-aligned, consistent decimal places, subtle zebra striping, totals row visually distinct."
- Fewer dimensions with precise descriptors beat many dimensions with vague ones.
- Rubric dimensions should be independent — if two dimensions always move together, they are measuring the same thing and should be merged.

## Score Reporting

Every review that produces scores must make the deductions transparent. A score without context is just a number — the reader needs to see what the rubric says, what was counted, and what each deduction costs.

### Required for every scored dimension

1. **Show the rubric anchor** — state the score-band thresholds alongside the score. "Score: 8. Rubric: 9-10 requires all artefacts covered; 7-8 allows 1-2 gaps."
2. **Show the count** — state the specific items counted. "12/12 contracts with consumer sections. 1 terminal artefact lacks a contract."
3. **Name the gap** — state exactly what prevents a higher score. "The source verification pattern is duplicated across 3 skills. That 1 unextracted pattern is the difference between 8 and 10."
4. **Distinguish fixable gaps from structural ceilings** — if the deduction is a deliberate design choice or an inherent constraint, say so. A structural ceiling is not a deficiency. Score it at the lower band but flag it as "by design" so the reader knows no action is needed.

### "What Prevents a Higher Score" section (mandatory)

Every review report must include a section titled "What Prevents a Higher Score." For each dimension that scored below 10, state in one sentence what the gap is and why closing it may or may not be worth the cost. This gives the reader a single place to see all deductions and decide which are worth addressing vs which are structural ceilings or acceptable trade-offs.

This section complements the findings: findings say what's wrong, "What Prevents a Higher Score" says what's not wrong but not perfect. A dimension at 9 with a structural ceiling is different from a dimension at 9 with a fixable gap. The reader needs to see which is which.

**Placement:** after the score trajectory table (round 2+) or after dimension detail (round 1), before the expert panel.

### Verdict (mandatory)

Every review must end with a verdict — a clear, actionable statement of whether the artefact is ready for its next use. Define the criteria before scoring (Deming: operational definition before measurement). The verdict is not optional; a review without a verdict forces the reader to interpret scores themselves.

**Thresholds (same across all review types):**

| Verdict tier | Criteria |
|---|---|
| **Ready** | 0 critical findings, ≤3 important findings, no dimension below 6 |
| **Ready with caveats** | 0 critical, 4–6 important, no dimension below 5. Caveats must be stated explicitly — what is accepted and why. |
| **Not ready** | Any critical finding, or >6 important findings, or any dimension below 5 |

**Verdict language is tailored to the artefact type:**

| Review skill | Ready | Ready with caveats | Not ready |
|---|---|---|---|
| `/gvm-doc-review` — pipeline docs | **Proceed** — ready for the next pipeline phase | **Proceed with caveats** — state what the downstream consumer must watch for | **Revise first** — fix before proceeding |
| `/gvm-doc-review` — whitepapers, strategy | **Publish** — ready for external readers | **Publish with revisions** — state what to fix first | **Do not publish** — revise before release |
| `/gvm-doc-review` — presentations | **Present** — ready to deliver | **Present with revisions** — state what to fix first | **Do not present** — revise before delivery |
| `/gvm-doc-review` — newsletters | **Send** — ready for distribution | **Send with revisions** — state what to fix first | **Do not send** — revise before distribution |
| `/gvm-doc-review` — training materials | **Deliver** — ready for learners | **Deliver with revisions** — state what to fix first | **Do not deliver** — revise before use |
| `/gvm-doc-review` — user documentation | **Ship** — accurate and usable | **Ship with caveats** — state the accuracy gaps | **Do not ship** — stale or misleading |
| `/gvm-code-review` | **Merge** — ready to merge | **Merge with caveats** — state the accepted risks | **Do not merge** — fix before merging |
| `/gvm-design-review` | **Build from this** — design supports the requirements | **Build with caveats** — state the design gaps to watch during build | **Do not build** — design gaps will cause structural problems |
| `/gvm-test` | **Ship-ready** — build verified, product works | **Demo-ready** — demonstrable but NOT user-deployable (registered stubs / known limits) | **Not shippable** — integration failures, unregistered stubs, or critical exploratory findings |

**Placement and format:** The verdict box is the first content element before the score card — the reader sees verdict first, then the supporting score detail, then findings. Use the `.verdict` component from `tufte-review-components.md`:

```html
<div class="verdict ready">
  <div class="verdict-label">Verdict</div>
  <div class="verdict-text">Publish</div>
  <div class="verdict-basis">0 critical, 2 important, 1 minor. All fixable in a single editing pass without restructuring.</div>
</div>
```

Three CSS classes match the three tiers: `.verdict.ready` (green), `.verdict.caveats` (orange), `.verdict.not-ready` (red). The `.verdict-text` is the type-specific word (Publish, Merge, Proceed, etc.). The `.verdict-basis` is one sentence stating the threshold result and any caveats. This format is identical across all review skills — the only thing that changes is the verdict word.

---

## Finding Quality Gate

Not every observation is a finding. A review system calibrated to keep discovering issues will always find more — reviewers can generate findings indefinitely by lowering the threshold for what counts. The quality gate defines what counts.

**A finding is real if a consumer of this artefact would misunderstand, take wrong action, or experience failure because of it.** A finding is polish if fixing it makes the author feel better but changes nothing for the consumer.

### Three tests, applied in order

Every finding must pass all three tests to enter the report. If it fails any test, it is not reported.

**1. Consumer impact.** State the consequence as a sentence: "A [consumer] would [concrete outcome]." If you cannot finish that sentence with a specific outcome — misunderstand the argument, implement the wrong thing, hit a bug, cite a wrong source, lose confidence in the evidence — the finding is polish. Discard it.

The consumer varies by artefact type:

| Artefact | Consumer | "Would [consumer]..." |
|----------|----------|----------------------|
| Standalone document (whitepaper, presentation, newsletter) | Reader | ...misunderstand the argument, cite a wrong source, lose trust in the evidence |
| Pipeline artefact (requirements, test cases, specs) | Developer/tester building from it | ...build the wrong thing, test the wrong path, miss a requirement |
| Code | End user or downstream developer | ...hit a bug, encounter a security boundary violation, get wrong data |
| Design (schema, API, architecture) | Developer implementing it | ...build a structure that cannot support the requirements, create an irreversible data model error |

**2. Propagation.** Does the finding cause a downstream problem in another artefact or system? A wrong requirement ID propagates through test cases, specs, and code. A left-aligned number in a sources table propagates nowhere. Higher-propagation artefacts warrant stricter scrutiny:

- **High propagation** (requirements, core architecture, shared code): findings here multiply. A wrong requirement becomes a wrong test becomes a wrong spec becomes wrong code. Scrutinise thoroughly.
- **Medium propagation** (specs, test cases, domain-specific code): findings affect a bounded scope. Scrutinise proportionally.
- **Low propagation** (standalone documents, leaf code, one-off scripts): findings stay local. Apply the consumer impact test strictly — if the consumer is not harmed, discard.

**3. Diminishing returns.** Each review round should hold new findings to a higher bar than the last. The threshold rises because the easy problems are already fixed:

- **Round 1:** Structural problems, missing content, factual errors, design flaws. The bar is low — anything that affects the consumer.
- **Round 2:** Argument gaps, consistency issues, coverage holes. The bar rises — findings should be things Round 1 could not see because major issues were masking them.
- **Round 3+:** Only findings that pass the consumer impact test with a *specific, concrete* consequence. "A reader might be slightly confused" is not concrete. "A developer would implement caching at the wrong layer because the spec contradicts the ADR" is concrete. If a finding was not caught in Rounds 1 or 2, the reviewer must explain why it matters more than its prior invisibility suggests.

### The stop condition

When all remaining observations fail the consumer impact test — when every potential finding is polish — the artefact is done. A review that produces only polish observations should report **"No actionable findings"** rather than dressing up preferences as issues. Reporting a clean review is a valid and valuable outcome. It means the quality system worked.

### Defence-in-depth findings

A finding is theoretical when the failure it prevents is already blocked by a stronger mechanism. State the precondition for failure as a sentence:

- "If a developer edits the config and..." → **Real.** Normal maintenance.
- "If the config contains an invalid value and no schema validation catches it..." → **Real.** Config errors happen.
- "If an attacker gains write access to internal files..." → **Theoretical.** Outside the trust boundary.
- "If the framework violates its own documented contract..." → **Theoretical.** Not a precondition the system should defend against.
- "If someone edits one copy of duplicated logic and not the other..." → **Real.** Duplication makes this inevitable during normal maintenance.

Defence-in-depth is valuable when the inner defence covers a *different failure mode* from the outer one. It is noise when the inner defence covers the *same failure mode* that the outer defence already prevents.

### Application to review skills

This quality gate applies to all GVM review activities:

- **`/gvm-doc-review`** — standalone documents use the low-propagation threshold; pipeline artefacts use medium-to-high
- **`/gvm-code-review`** — code findings must state the consumer impact; security findings in critical paths get the strictest scrutiny
- **`/gvm-design-review`** — design findings propagate to implementation; apply the high-propagation threshold
- **`/gvm-build` code review loop** — findings during the build cycle interrupt flow and cost the most to address; apply the consumer impact test strictly to avoid false interruptions
- **`/gvm-test` audits** — stub and seam audit findings are real when the untested path has different behaviour from the tested path; theoretical when the paths are identical

---

## Reviewer Calibration

---

### Michael Fagan

**Source:** *Design and Code Inspections to Reduce Errors in Program Development*, IBM Systems Journal (1976)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 4 | 5 | 3 | **Established** |

Evidence: Authority — invented structured software inspection; "Fagan Inspection" named after him; IEEE 1028 traceable to his framework. Publication — IBM Systems Journal, premier peer-reviewed computing journal. Breadth — inspection principles adopted in hardware design, document review, medical device review. Adoption — referenced in IEEE 1028, CMMI, SEI frameworks.

**Work score — *Design and Code Inspections to Reduce Errors in Program Development*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 4 | 2 | 5 | **Established** |

Evidence: Specificity — specific roles (moderator, reader, tester, author), meeting structure, entry/exit criteria, rate recommendations (150-200 LOC/hour). Depth — empirical data from IBM production projects on defect detection rates. Influence — foundational to IEEE 1028; cited in every software quality textbook covering inspections.


- Reviewers must **calibrate before scoring**. Calibration means: review a reference artefact with known scores, compare your scores to the reference, adjust your internal scale.
- Provide **anchor examples** — artefacts pre-scored at each level (low, medium, high). Reviewers who have seen what a "4" looks like score more consistently than reviewers working from descriptions alone.
- **Checklists over impressions** — a checklist of specific things to look for produces more consistent results than "evaluate the quality."
- Separate **defect finding** from **defect classification**. First find issues, then classify severity. Mixing the two in one pass reduces detection rates.
- **Rate of review matters** — too fast and reviewers miss things; too slow and they over-scrutinise. For code: 150-200 lines per hour. For documents: calibrate per artefact type.

---

### Robert Marzano

**Source:** *Classroom Assessment and Grading That Work*, ASCD (2006)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 4 | 3 | 2 | 3 | 4 | **Recognised** |

Evidence: Authority — most cited K-12 educational effectiveness researcher; meta-analyses referenced in US federal education policy. Currency — continues to publish actively (*The New Art and Science of Teaching*, 2017).

**Work score — *Classroom Assessment and Grading That Work*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 4 | 3 | 3 | 3 | **Recognised** |

Evidence: Specificity — "score the performance not the performer" and "count rather than judge" are operationally clear with worked examples.


- **Score the performance, not the performer.** Reviewers who form an overall impression first and then score dimensions will produce halo effects (all dimensions shift together). Score each dimension independently, in isolation.
- **Don't score what you can count.** If a criterion can be measured by counting (number of missing labels, number of undocumented ADRs), count rather than judge. Counting is reliable; judging is not.
- **Provide worked examples** of each score level. Show reviewers what a 3, 5, 7, and 9 look like on each dimension. This is the single most effective calibration technique.

## Progressive Calibration

Reviews improve over time. The first review of a project has no project-specific context; subsequent reviews calibrate against accumulated data. This is Deming's measurement system stabilisation applied to AI review.

### The feedback loop

```
Round 1: Load expert references only → Review → Extract scores + anchor examples → Create calibration.md
Round 2: Load expert references + calibration.md → Review → Append scores, update anchors → Update calibration.md
Round N: Load expert references + calibration.md → Review → Append scores, curate anchors → Update calibration.md
```

### Four calibration layers

Each review loads calibration from four layers, most general to most specific:

1. **Universal** — expert reference files (architecture-specialists.md, writing-reference.md). What "good" means in any project.
2. **Domain** — industry domain files (references/industry/*.md). What "good" means in this industry.
3. **Stack** — stack specialists (stack-specialists.md). What "good" means in this technology.
4. **Project** — `reviews/calibration.md`. What "good" means in *this specific codebase*, learned from prior reviews.

Layers 1-3 are pre-loaded by shared rules. Layer 4 is loaded by the review skill if it exists, and created/updated after each review.

### After each review round

The review skill must update `reviews/calibration.md` with:

1. **Append a score history row** — round number, date, type, overall + per-dimension scores.
2. **Update dimension benchmarks** — baseline (round 1), current (this round), trend.
3. **Curate anchor examples** — for each dimension, keep the 2 best and 2 worst concrete examples from this project. Each anchor must be countable (Marzano), verifiable (Deming), self-contained (Fagan), and band-demonstrating (Stevens & Levi). See `pipeline-contracts.md` for the full selection criteria. Replace weaker anchors when more illustrative ones are found.
4. **Update recurring findings** — if the same issue appears in 2+ consecutive rounds, mark it as recurring.
5. **Move resolved findings** — if a previously recurring issue is confirmed fixed, record the resolution.
6. **Promote to build checks** — if any recurring finding meets promotion criteria (flagged in 3+ consecutive rounds, or regressed after resolution), promote it to `reviews/build-checks.md` per shared rule 21. Retire active checks not triggered in 3 consecutive rounds. This creates a feedback path from review to build: findings that keep recurring become build-time checklists.

See `pipeline-contracts.md` for the full structural contract of `reviews/calibration.md`.

### What the reviewer sees

On round 1 (no calibration file):
- Expert principles only: "McConnell says functions should have 3 or fewer parameters."

On round 3+ (calibration file exists):
- Expert principles + project context: "McConnell says 3 or fewer parameters. In this project, the auth module averages 2.1 (good); the search module averages 4.8 (flagged in rounds 1 and 2, partially fixed in round 2)."

This grounds the reviewer in what the experts define as good *and* what this project's actual quality trajectory looks like.

## Applying These Principles to GVM Reviews

### For code reviews (/gvm-code-review)

1. Load `reviews/calibration.md` if it exists. Provide project-level calibration to each expert panel.
2. Fagan's defect-finding checklist: specific items to look for, not general quality impressions.
3. Separate finding from severity classification.
4. Each expert panel gets its own checklist derived from that expert's published principles.
5. After the review, update `reviews/calibration.md` with scores and anchor examples.

### For document reviews (/gvm-doc-review)

1. Load `reviews/calibration.md` if it exists.
2. Use analytic rubrics with concrete descriptors per dimension (Stevens & Levi).
3. Separate finding issues from scoring — first list what is present/missing, then score.
4. Count where possible: "3 of 8 required sections present" is more reliable than "completeness: 5/10."
5. After the review, update `reviews/calibration.md`.

### For ad-hoc reviews (plugin review, experiment scoring)

1. Use the same rubric across all rounds — never change criteria between rounds if you want to compare scores (Deming).
2. Provide anchor examples in the review prompt if available from prior rounds.
3. Report Krippendorff's alpha alongside scores. If alpha < 0.5 on a dimension, flag the dimension as unreliable rather than interpreting the scores.
4. Define dimensions with Gilb's five components (scale, meter, benchmark, target, tolerance) when designing new rubrics.
