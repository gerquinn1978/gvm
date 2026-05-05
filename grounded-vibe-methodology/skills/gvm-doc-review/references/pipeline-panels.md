# Pipeline Document Review Panels

Loaded by `/gvm-doc-review` when reviewing pipeline artefacts (requirements, test cases, specs). Do not load for standalone documents.

## Panel A: Structure & Contract Compliance

**What to scan:** Are all required sections present per `pipeline-contracts.md`? Are IDs formatted correctly (requirement IDs, test case IDs, ADR IDs)? Is the requirements index complete? Are headings hierarchically correct? Does the document match its pipeline contract structure?

**Experts assigned:** Doumont (structure by message — every section must answer "so what?"), Fagan (entry/exit criteria — required sections must be present).

**Scanning method:**
- **Pass 1 — Systematic scan:** Read each section. For every required section (per document type in `pipeline-contracts.md`), verify it exists, is correctly placed, and is non-empty. Verify all IDs follow the specified format.
- **Pass 2 — Cross-reference scan:** Check that the document's index/summary table matches actual content. Verify all IDs in the index appear in the body and vice versa.

## Panel B: Traceability & Cross-Reference

**What to scan:** Does every requirement ID in test-cases trace to a real requirement? Do spec references point to real sections? Are cross-document links valid? Is the traceability matrix complete and bidirectional?

**Experts assigned:** Keeling (decision capture — traceability between decisions and their rationale), Hunt & Thomas (DRY — single source of truth, no contradictory duplicates).

**Scanning method:**
- **Pass 1 — Systematic scan:** Read each document and enumerate every ID reference, cross-document link, and traceability claim.
- **Pass 2 — Cross-reference scan:** For each reference found in Pass 1, verify the target exists in the referenced document. Flag dangling references, broken links, and ID mismatches. Check bidirectional coverage: every requirement has tests, every test traces to a requirement.

## Panel C: Content Quality & Domain Accuracy

**What to scan:** Are requirements unambiguous and testable? Are test case Given/When/Then values concrete? Are spec decisions justified? Are domain terms used correctly? Is the prose clear?

**Experts assigned:** Doumont (answer "so what?"), Zinsser (every word earns its place), Williams (subjects near verbs), domain specialists (from industry domain file if loaded).

**Scanning method:**
- **Pass 1 — Systematic scan:** Read each section. For every requirement, check testability. For every test case, check concreteness of values. For every spec decision, check that rationale exists.
- **Pass 2 — Cross-reference scan:** Check that the same concept is described consistently across documents. Flag contradictory claims.

## Panel D: Scoring & Rubric Application

**What to scan:** Score each dimension against the review criteria from `review-criteria.md`. Count rather than judge.

**Experts assigned:** Marzano (count don't judge), Stevens & Levi (analytic rubrics — score against defined criteria), Gilb (five-component criteria).

**Scanning method:**
- **Pass 1 — Systematic scan:** For each scoring dimension, evaluate the document against the rubric's specific thresholds (full/partial/missing). Record the evidence.
- **Pass 2 — Cross-reference scan:** Cross-check scores against findings from Panels A-C. A document with Critical structure findings should not score high on structure dimensions.

## Cross-Document Consistency (post-panel synthesis)

After all panels complete, the main skill runs cross-document consistency checks:
- **Requirements → Test Cases:** Every requirement ID has at least one test case. Flag uncovered requirements.
- **Requirements → Specs:** Every requirement ID appears in at least one spec section. Flag unspecified requirements.
- **Test Cases → Specs:** Test cases reference spec components that exist.

## Type-Specific Criteria

### Test Cases (additional to standard panels)
1. Technique appropriateness — proportional to risk
2. Boundary value correctness — test 17, 18, 65, 66 not just 18 and 65
3. Coverage completeness — all requirements have tests
4. Redundancy — no duplicate coverage with gaps elsewhere
5. Testability — preconditions achievable, results observable
