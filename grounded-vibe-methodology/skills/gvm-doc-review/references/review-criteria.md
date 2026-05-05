# Review Criteria — Scoring Reference

This file defines the scoring rubric for each document type. Load once at the start of a review.

---

## Requirements Scoring (10 criteria, 1 point each)

| # | Criterion | Source | Score 1 (full) | Score 0.5 (partial) | Score 0 (missing) |
|---|---|---|---|---|---|
| 1 | **Completeness** | Wiegers Ch. 4 | All domains covered, assumptions/constraints/out-of-scope explicit | Some domains thin, cross-cutting partially covered | Major domains missing |
| 2 | **Correctness** | Wiegers Ch. 4 | Requirements clearly reflect user needs, JTBD job statement present | Most requirements sound right but some feel assumed | Requirements feel disconnected from users |
| 3 | **Feasibility** | Wiegers Ch. 4 | All requirements implementable with stated constraints | Some requirements may be challenging but noted as open questions | Requirements that cannot be built as stated |
| 4 | **Necessity** | Wiegers Ch. 4 | Every requirement traces to a user need or persona goal | Most do, a few feel speculative | Many requirements lack justification |
| 5 | **Prioritised** | Wiegers Ch. 16 | Every requirement has MoSCoW priority | Most prioritised, some missing | No prioritisation |
| 6 | **Unambiguous** | Wiegers Ch. 4 | Each requirement testable, single interpretation | Some vague language ("user-friendly", "fast") | Widespread ambiguity |
| 7 | **Verifiable** | Wiegers Ch. 4 | Acceptance criteria clear for every requirement | Most verifiable, some need interpretation | Many requirements can't be verified |
| 8 | **Consistent** | Wiegers Ch. 4 | No contradictions between requirements | Minor overlaps or unclear relationships | Direct contradictions exist |
| 9 | **Traceable** | Wiegers Ch. 4 | Every requirement has unique ID, index table present | IDs present but index incomplete | No IDs or broken references |
| 10 | **Structured** | Wiegers Ch. 1 | Clear domain organisation, easy to navigate, modifiable | Reasonable structure with some awkward groupings | Flat or disorganised |

**Total: sum / 10 = score**

---

## Test Cases Scoring (10 criteria, 1 point each)

| # | Criterion | Source | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|---|---|
| 1 | **Requirement coverage** | North/BDD | Every requirement ID has ≥1 test | >80% covered | <80% covered |
| 2 | **Traceability** | North/BDD | Every test traces to a requirement, no orphans | Minor gaps | Widespread missing traces |
| 3 | **Technique selection** | Copeland | Right technique for each requirement type (BVA for ranges, decision tables for conditionals, etc.) | Mostly appropriate but some missed opportunities | Generic use-case only throughout |
| 4 | **Boundary values** | Beizer | Numeric constraints have boundary tests (min, max, on, off) | Some boundaries tested | No boundary testing |
| 5 | **Negative cases** | Beizer/Kaner | Invalid inputs, error conditions, empty states tested | Some negative cases | Happy path only |
| 6 | **Consumer realism** | Kaner | Realistic data, interrupted workflows, first-time user considered | Some realistic scenarios | Trivial test data throughout |
| 7 | **Priority alignment** | Kaner | Must requirements have most thorough coverage, edge cases deprioritised | Mostly aligned | Uniform coverage regardless of priority |
| 8 | **Concrete values** | North/BDD | Given/When/Then with specific values ("$500,000" not "a valid budget") | Mostly concrete | Abstract descriptions |
| 9 | **Behaviour naming** | North/BDD | Test names describe behaviour ("Areas match budget") not mechanism ("Test RE-1") | Mostly behavioural | Mechanism-focused names |
| 10 | **Document quality** | — | HTML and MD in sync, health report present, traceability matrix complete | Minor sync issues | Significant gaps |

---

## Specs Scoring (10 criteria, 1 point each)

| # | Criterion | Source | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|---|---|
| 1 | **Decomposition** | Clements | Right number of specs for complexity, clear boundaries | Reasonable but some specs too broad/narrow | Single monolithic spec for complex system, or over-decomposed |
| 2 | **Architecture clarity** | Brown/C4 | System understandable at a glance, clear containers and communication | Architecture present but unclear in places | No architecture overview |
| 3 | **Risk-proportional depth** | Fairbanks | Risky parts thorough, obvious parts light | Somewhat calibrated | Uniform depth (either all shallow or all over-detailed) |
| 4 | **Decision capture** | Keeling | Significant decisions in ADR format with context and rationale | Some decisions documented but missing rationale | Decisions stated without context |
| 5 | **Quality attributes** | Bass/Clements/Kazman | Non-functional requirements addressed with scenarios and tactics | Some quality attributes mentioned | Non-functional requirements ignored |
| 6 | **Conceptual integrity** | Brooks | Consistent vocabulary, patterns, mental model across specs | Mostly consistent, minor deviations | Specs feel like different authors with different assumptions |
| 7 | **Requirement traceability** | Clements | Every spec section references requirement IDs | Most sections traced | No traceability |
| 8 | **Implementation guide** | — | Build phases, dependencies, chunking, test co-location defined | Partial guidance | No implementation ordering |
| 9 | **Expert activation** | — | Right domain and stack specialists applied (visible in the spec) | Some specialist knowledge applied | Generic patterns only |
| 10 | **Document quality** | — | HTML and MD in sync, details toggles work, cross-cutting referenced | Minor issues | Significant format or sync problems |

---

## Cross-Document Consistency Scoring (10 criteria, 1 point each)

| # | Criterion | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|---|
| 1 | **Req → Test coverage** | Every requirement ID has ≥1 test case | >80% | <80% |
| 2 | **Req → Spec coverage** | Every requirement ID in ≥1 spec section | >80% | <80% |
| 3 | **Test → Req tracing** | Every test traces to a requirement | >90% | <90% |
| 4 | **Spec → Req tracing** | Every spec section cites requirements | >80% | <80% |
| 5 | **Vocabulary consistency** | Same terms used across all docs | Minor deviations | Different terms for same concepts |
| 6 | **Priority consistency** | Test/spec depth matches requirement priority | Mostly aligned | No alignment |
| 7 | **No contradictions** | Docs agree on system behaviour | Minor ambiguities | Direct contradictions |
| 8 | **Open questions tracked** | OQs in requirements referenced in specs as decisions or deferred | Most tracked | OQs dropped |
| 9 | **Acknowledged gaps respected** | Health report decisions not contradicted by tests/specs | Mostly | Gaps re-introduced |
| 10 | **Pipeline completeness** | All expected docs exist for the project's stage | Missing one doc | Multiple docs missing |

---

## Issue Classification

**Critical (must fix):**
- Requirement with no test coverage AND no spec coverage
- Direct contradiction between documents
- MUST requirement that is untestable or unspecified
- Missing document entirely (e.g., no test cases when requirements exist)

**Important (should fix):**
- Requirement with test coverage but no spec coverage (or vice versa)
- Vague requirement that could cause implementation ambiguity
- Missing boundary value tests for numeric constraints
- Spec section with no ADR for a non-obvious decision
- Inconsistent vocabulary between documents

**Minor (nice to improve):**
- COULD requirement with minimal test coverage
- Wording improvements for clarity
- Style inconsistencies between HTML and MD
- Missing sidenotes or cross-references
- Test names that are mechanism-focused rather than behaviour-focused
