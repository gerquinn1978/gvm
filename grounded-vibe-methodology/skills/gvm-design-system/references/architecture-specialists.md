# Architecture Specialists — Tier 1 Reference

These experts are always active. They govern process, decomposition, cross-cutting decisions, code quality, and testing discipline across all phases and all stacks.

---

## Activation Rules

Tier 1 specialists are active for every spec, every build chunk, and every code review. No activation signal required.

---

## Paul Clements — Specification Decomposition

**Source:** *Documenting Software Architectures: Views and Beyond* (2nd ed.), Addison-Wesley (2010)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 4 | 4 | 3 | **Established** |

Evidence: Authority — SEI principal; V&B canonical. Publication — Addison-Wesley 2nd ed. *Software Architecture in Practice* reached a 4th edition in 2021; *Documenting Software Architectures* stopped at 2nd edition in 2010 — this drives the Currency difference (Clements=3, Bass/Kazman=4).

**Work score — *Documenting Software Architectures*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 5 | 2 | 4 | **Established** |

Evidence: Work Specificity — entire scope is arch documentation. Work Depth — exhaustive view types.

**Role:** Drives decomposition — determines which specs/views are needed based on requirements complexity and stakeholder concerns.

---

## Simon Brown — Architecture Visualisation

**Source:** *Software Architecture for Developers*, Leanpub; C4 Model (c4model.com)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 4 | 3 | 3 | 4 | 5 | **Established** |

Evidence: Authority — creator C4 model. Adoption — C4 in Structurizr, PlantUML, Mermaid, IcePanel. Currency — actively maintained.

**Work score — *Software Architecture for Developers*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 4 | 3 | 5 | 4 | **Established** |

**Role:** Structures the architecture overview; defines container boundaries; provides zoom-level framework (context → containers → components).

---

## George Fairbanks — Risk-Driven Architecture

**Source:** *Just Enough Software Architecture*, Marshall & Brainerd (2010)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 4 | 4 | 3 | 3 | 3 | **Recognised** |

Evidence: Authority — PhD CMU; risk-driven model. Publication — SEI pedigree.

**Work score — *Just Enough Software Architecture*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 4 | 4 | 2 | 3 | **Recognised** |

**Role:** Calibrates depth per domain — thorough where risky, light where well-understood. Risk-driven architecture.

---

## Michael Keeling — Decision Capture

**Source:** *Design It!: From Programmer to Software Architect*, Pragmatic Bookshelf (2017)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 3 | 4 | 3 | 3 | 4 | **Recognised** |

Evidence: Publication — Pragmatic Bookshelf. Currency — ADRs increasingly relevant.

**Work score — *Design It!*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 4 | 3 | 4 | 3 | **Established** |

**Role:** ADR-style decision capture within each spec; identifies Architecturally Significant Requirements (ASRs) from the requirements document.

---

## Bass, Clements, Kazman — Quality Attributes

**Source:** *Software Architecture in Practice* (4th ed.), Addison-Wesley (2021)

**Expert score — Len Bass:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 4 | 5 | 4 | **Canonical** |

**Expert score — Rick Kazman:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 4 | 5 | 4 | **Canonical** |

*Paul Clements scored above.*

Evidence: Bass Authority — SEI principal across 4 editions. Kazman Authority — co-developer of ATAM. Work Depth — 650+ pages most comprehensive arch treatment. Work Currency — 4th ed 2021. Work Influence — standard text globally.

**Work score — *Software Architecture in Practice* (4th ed.):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 4 | 5 | 5 | 5 | **Canonical** |

**Role:** Quality attribute scenarios for non-functional requirements; architectural tactics.

---

## Frederick Brooks — Conceptual Integrity

**Sources:**
- *The Mythical Man-Month*, Addison-Wesley (1975, anniversary ed. 1995)
- *The Design of Design*, Addison-Wesley (2010)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 5 | 5 | 3 | **Canonical** |

Evidence: Authority — Turing Award. Adoption — "Brooks's Law" universal. Work Influence — most influential SE book.

**Work score — *The Mythical Man-Month*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 3 | 4 | 2 | 5 | **Established** |

**Work score — *The Design of Design*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 3 | 4 | 3 | 3 | **Recognised** |

**Role:** Conceptual integrity review — does the full system cohere as if designed by one mind?

---

## Martin Fowler — Pragmatic Patterns

**Source:** *Patterns of Enterprise Application Architecture*, Addison-Wesley (2002); various articles (martinfowler.com)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 5 | 5 | 5 | **Canonical** |

Evidence: Authority — Chief Scientist ThoughtWorks; Agile Manifesto. Breadth — refactoring, patterns, UML, DSLs, microservices. Adoption — Active Record, Repository in Rails, Django, Spring. Work Depth — 533 pages 65 patterns.

**Work score — *Patterns of Enterprise Application Architecture*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 5 | 2 | 5 | **Established** |

**Work score — *UML Distilled* (3rd ed.):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 4 | 3 | 3 | 4 | **Established** |

Evidence: *UML Distilled* Influence — standard pragmatic UML introduction; teaches enough UML to be useful without deep formalism.

**Work score — *Refactoring: Improving the Design of Existing Code* (2nd ed.):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 5 | 4 | 5 | **Canonical** |

Evidence: Specificity — systematic catalogue of named refactorings with before/after code. Depth — 418 pages covering 60+ refactorings with full worked examples. Currency — 2nd edition (2018) rewritten in JavaScript, actively maintained online catalogue. Influence — "refactoring" as a named discipline traces to this work; IDE refactoring tools implement Fowler's named operations.

**Role:** Pragmatic patterns; keeps specs lightweight and maintainable; anti-bloat lens.

---

## Steve McConnell — Code Construction

**Source:** *Code Complete* (2nd ed.), Microsoft Press (2004)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 4 | 5 | 3 | **Established** |

Evidence: Authority — contributing editor and columnist for IEEE Software; Construx Software founder. Adoption — 1M+ copies. Work Depth — 960 pages backed by empirical research.

*Boundary case: avg 4.4, within 0.1 of Canonical boundary (4.5). If an independent rescore confirms any dimension increase, reclassifies to Canonical.*

**Work score — *Code Complete* (2nd ed.):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 4 | 5 | 2 | 5 | **Established** |

**Key principles:**
- **Defensive programming** (Ch. 8): Fail on missing configuration. Crash at startup with a clear error rather than falling back to defaults that mask problems.
- **Intention-revealing names** (Ch. 11): The name should describe what the function does, not how. Avoid uncommon abbreviations.
- **Minimal parameters** (Ch. 7): 3 or fewer per function. Group into a data class or config object if more.
- **Single responsibility** (Ch. 7): Each function does one thing. If describing it requires "and", split it.

---

## Robert C. Martin — Clean Code

**Source:** *Clean Code: A Handbook of Agile Software Craftsmanship*, Prentice Hall (2008)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 4 | 4 | 4 | 5 | 4 | **Established** |

Evidence: Adoption — SOLID universal in OOP. Publication — Prentice Hall / Robert C. Martin Series (6+ titles). Breadth — *Clean Code*, *Clean Architecture*, *Clean Agile*, *The Clean Coder* — covering code craft, architecture, project management, and professional conduct. Stack Overflow Developer Survey consistently lists *Clean Code* among top recommended books.

**Work score — *Clean Code*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 4 | 3 | 3 | 5 | **Established** |

**Key principles:**
- **Functions should do one thing** (Ch. 3): Do it well, do it only. Under 25 lines is a strong signal.
- **No swallowed errors** (Ch. 7): Never empty catch blocks. Every error is handled meaningfully or propagated.
- **Structured error handling** (Ch. 7): Errors carry context: what failed, why, and whether it's retryable.

---

## Andrew Hunt & David Thomas — Pragmatic Programming

**Source:** *The Pragmatic Programmer* (20th anniversary ed.), Addison-Wesley (2019)

**Expert score — Andrew Hunt:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 4 | 5 | 4 | 5 | 4 | **Established** |

**Expert score — David Thomas:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 4 | 5 | 4 | 5 | 4 | **Established** |

Evidence: Adoption — "DRY" universal. Work Currency — 2019 anniversary ed rewritten. Work Influence — most cited in professional SE.

**Work score — *The Pragmatic Programmer* (20th anniversary ed.):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 4 | 3 | 4 | 5 | **Established** |

**Key principles:**
- **DRY — Don't Repeat Yourself** (Tip 11): Knowledge should have a single, unambiguous, authoritative representation. But DRY is about knowledge, not code — three similar lines are better than a premature abstraction.
- **No hardcoded secrets** (Tip 51): API keys, passwords, connection strings — all via environment variables.
- **Tracer bullets** (Ch. 2): Build end-to-end thin slices first to validate architecture, then fill in.

---

## Kent Beck — Test-Driven Development

**Source:** *Test-Driven Development: By Example*, Addison-Wesley (2002)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 4 | 5 | 4 | **Canonical** |

Evidence: Authority — creator XP, JUnit, TDD. Adoption — TDD is standard practice. Breadth=4 — XP principles adopted across software engineering, agile product management, and coaching; JUnit spawned the xUnit framework family across Java, .NET, Python, Ruby, and JavaScript. Work Specificity — entire book is worked TDD example. Work Influence — defining text on TDD.

**Work score — *Test-Driven Development: By Example*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 4 | 3 | 5 | **Established** |

**Key principles:**
- **Test first, always** (Ch. 1): Write the failing test before the implementation. The test defines the behaviour; the code fulfils it.
- **One behaviour per test cycle**: Each red-green-refactor cycle tests one specific behaviour.
- **The test must fail first**: A test that passes before you write the code is testing nothing.
- **Test the interface, not the implementation**: Internal refactoring should never break tests.

---

## Sandi Metz — Testing Philosophy

**Source:** *Practical Object-Oriented Design* (2nd ed.), Addison-Wesley (2018)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 4 | 4 | 3 | 4 | 4 | **Established** |

Evidence: Authority — conference talks widely viewed. Publication — Addison-Wesley 2nd ed. Work Specificity — explicit testing rules.

**Work score — *Practical Object-Oriented Design* (2nd ed.):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 4 | 4 | 4 | 3 | **Established** |

**Key principles:**
- **Test the public API, not internals** (Ch. 9): If tests break when you refactor without changing behaviour, they're coupled to implementation.
- **Mock outgoing messages, test incoming messages**: Mock at boundaries only — external APIs, databases, file systems. Never mock the code you own.
- **Test names describe behaviour**: `test_expired_token_returns_401` not `test_token_1`.

---

## Boris Beizer — Testing Techniques

**Source:** *Software Testing Techniques* (2nd ed.), Van Nostrand Reinhold (1990)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 4 | 4 | 3 | 3 | 1 | **Recognised** |

Evidence: Authority=4 — BVA and equivalence partitioning techniques widely attributed to Beizer in academic software engineering curricula. Publication=4 — Van Nostrand Reinhold (academic technical imprint); primary academic reference for structured testing techniques.

**Work score — *Software Testing Techniques* (2nd ed.):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 5 | 1 | 4 | **Established** |

Evidence: Authority — recognised academic authority on software testing; boundary value analysis (BVA) technique widely attributed to Beizer; taught in university software engineering curricula. Publication — *Software Testing Techniques* published by Van Nostrand Reinhold (academic imprint); primary academic reference for BVA and equivalence partitioning. Work Specificity — formal definitions per technique. Work Depth — most rigorous practitioner testing text. Work Influence — BVA as taught derives from Beizer.

Note: Currency=1 reflects 1990 publication date — core technique definitions (BVA, equivalence partitioning) remain valid and are taught unchanged; tooling examples are outdated.

**Key principles:**
- **Bugs cluster at boundaries and error paths**: Edge cases, empty inputs, null values, off-by-one — test boundary values explicitly.
- **Structural coverage is necessary but not sufficient**: 100% coverage with meaningless assertions is worse than 80% with meaningful tests.

---

## Cem Kaner — Exploratory Testing

**Source:** *Lessons Learned in Software Testing*, Wiley (2001)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 4 | 4 | 3 | 3 | 2 | **Recognised** |

Evidence: Authority — coined "exploratory testing"; Context-Driven Testing founder.

**Work score — *Lessons Learned in Software Testing*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 4 | 3 | 2 | 3 | **Recognised** |

**Key principles:**
- **Realistic test data catches realistic bugs**: Don't mock APIs to return `{"data": "test"}`. Use realistic shapes matching actual contracts.
- **Consumer realism**: Test from the perspective of a first-time user, an interrupted workflow, a realistic data volume.

---

## Mike Cohn — Work Decomposition and Vertical Slicing

**Source:** *Agile Estimating and Planning*, Prentice Hall (2005); *User Stories Applied*, Addison-Wesley (2004)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 4 | 5 | 4 | 5 | 3 | **Established** |

Evidence: Authority — founder Mountain Goat Software; Certified Scrum Trainer; prominent agile practitioner. (Authority=4, not 5: Cohn was not an Agile Manifesto signatory — that attribution was incorrect and has been removed.) Publication — Prentice Hall and Addison-Wesley. Breadth — estimation, planning, user stories, sprint structure; adopted across Scrum, XP, SAFe. Adoption — INVEST criteria (originated by Bill Wake, 2003; popularised by Cohn) are standard vocabulary in agile teams globally; story point estimation (rooted in XP/Jeffries; popularised by Cohn) is the default estimation unit in Jira, Azure DevOps, and Linear. Currency=3: 2005 publication; core principles unchanged but tooling context is dated.

**Work score — *Agile Estimating and Planning*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 4 | 2 | 5 | **Established** |

Evidence: Specificity — INVEST criteria, story point estimation, velocity-based planning, vertical slicing — each a discrete, actionable technique. Depth — full planning lifecycle from release to iteration level. Influence — INVEST criteria cited in virtually every agile training programme; story points are the default estimation unit in Jira, Azure DevOps, and Linear.

**Work score — *User Stories Applied*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 3 | 2 | 4 | **Established** |

Evidence: Specificity — story-writing templates, splitting patterns, acceptance criteria format. Influence — "As a [role], I want [goal], so that [benefit]" template traces to this work.

**Role:** Drives implementation guide decomposition — determines chunk sizing, vertical slicing strategy, dependency-aware sequencing, and parallel work identification.

**Key principles:**
- **INVEST criteria for chunk sizing** (Ch. 2, *User Stories Applied*): each chunk should be Independent (minimal dependencies), Negotiable (scope can be adjusted), Valuable (delivers testable functionality), Estimable (clear enough to scope), Small (fits in a context window), Testable (includes its own tests). A chunk that fails INVEST should be re-sliced.
- **Vertical slicing over horizontal layering** (Ch. 8): slice through all layers (frontend, backend, database) per feature rather than building all of one layer first. A vertical chunk produces a working thin slice; a horizontal chunk produces an untestable layer.
- **Split by data variations, not by operations** (Ch. 12): when a chunk is too large, split by the data it handles (e.g., "agent for real estate" vs "agent for education") rather than by CRUD operations (e.g., "create agents" vs "read agents"). Data-variation splits produce independent chunks; operation splits produce coupled chunks.
- **Dependency-aware sequencing** (Ch. 15): when chunks have dependencies, build the depended-upon chunk first. When multiple chunks depend on the same foundation, build the foundation as its own chunk (a "walking skeleton" or "tracer bullet" — Hunt & Thomas). Then the dependent chunks can run in parallel.
- **Spike chunks for uncertainty** (Ch. 12): when a chunk involves technology or domain uncertainty, create a time-boxed spike chunk that answers the question without delivering production code. The spike's output is knowledge, not software — it informs the real chunk's design.
