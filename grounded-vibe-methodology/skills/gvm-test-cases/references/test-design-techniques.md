# Test Design Techniques — Expert Reference

This file is actively consulted during test case generation. It provides techniques organized by expert, with citations to authoritative works so Claude can draw on its training knowledge of these sources.

---

## Expert Panel

### Lee Copeland

**Source:** *A Practitioner's Guide to Software Test Design*, Auerbach Publications (2004)

**Role in this skill:** Technique selection — matching requirement types to the right test design technique.

**Key techniques to apply:**

- **Equivalence class partitioning** (Ch. 4): Divide input data into classes where all values in a class should behave the same. Test one value from each class. Apply when requirements specify data inputs with ranges or categories.
- **Boundary value analysis** (Ch. 5): Test at the edges of equivalence classes — the minimum, maximum, just inside, just outside. Apply to any requirement with numeric ranges, size limits, or count constraints.
- **Decision table testing** (Ch. 7): For requirements with multiple conditions that interact to produce different outcomes. Build a table of all condition combinations and expected actions. Apply when you see "if X and Y then Z" patterns.
- **State transition testing** (Ch. 8): For requirements describing workflows, multi-step processes, or screens/pages with navigation. Model the states and transitions, then generate tests for each valid transition and key invalid transitions.
- **Use case testing** (Ch. 10): For requirements expressed as user stories or workflows. Generate tests for the main success scenario, then for each alternate/exception flow.
- **Pairwise testing** (Ch. 9): When multiple independent parameters interact (e.g., browser + OS + screen size). Test all pairs of values rather than all combinations — dramatically reduces test count while maintaining coverage.

**Technique selection guide:**

| Requirement Pattern | Primary Technique | Secondary Technique |
|---|---|---|
| "If X then Y", conditional logic | Decision table | Equivalence class |
| Workflow, multi-step process | State transition | Use case testing |
| User performs action, expects result | Use case testing | — |
| Numeric input with range/limit | Boundary value | Equivalence class |
| Multiple parameters interact | Pairwise | Decision table |
| Categories of input (dropdown, type) | Equivalence class | Boundary value |
| Simple declarative ("system must X") | Single Given/When/Then scenario | — |
| Reversible, idempotent, or order-preserving operation | Property-based (MacIver) | Boundary value |
| Calculation with algebraic properties | Property-based (MacIver) | Boundary value |
| Accepts user input, renders content, handles files | Security testing (OWASP) | Equivalence class |
| Exposes API endpoints, manages auth/sessions | Security testing (OWASP) | State transition |

**When to reference:** At the start of Phase 2 for each domain. Read the requirements, identify patterns, select techniques before generating test cases.

---

### Boris Beizer

**Source:** *Software Testing Techniques* (2nd ed.), Van Nostrand Reinhold (1990)

**Role in this skill:** Thoroughness — ensuring comprehensive coverage when deepening is warranted.

**Key techniques to apply:**

- **Boundary value analysis (rigorous)** (domain testing chapters): For each boundary:
  - Test the boundary value itself (on point)
  - Test just inside the boundary (in point)
  - Test just outside the boundary (out point)
  - For ranges: test min, min-1, min+1, max-1, max, max+1
  - For string lengths: empty, 1 char, max-1, max, max+1
- **Equivalence partitioning (thorough)** (domain testing chapters): Identify ALL equivalence classes, not just obvious ones:
  - Valid classes (expected inputs that should succeed)
  - Invalid classes (inputs that should be rejected gracefully)
  - Special values (zero, empty, null, whitespace, negative)
  - Format violations (wrong type, wrong encoding)
- **Error guessing** (syntax and semantic testing chapters): Based on common failure patterns:
  - Off-by-one errors
  - Empty/null handling
  - Duplicate submissions
  - Concurrent access
  - Unicode and special characters
  - Maximum length inputs
  - Negative numbers where positive expected
- **Cause-effect graphing** (logic-based testing chapters): For complex conditional logic — model the relationships between inputs (causes) and outputs (effects) as a graph, then derive test cases that exercise each relationship. Use when decision tables become unwieldy due to many interacting conditions.

**When to reference:** During Phase 3 (deepening) when the user wants full boundary analysis on a specific requirement. Also consult for the error guessing heuristics when generating negative test cases in Phase 2.

---

### Dan North (BDD)

**Sources:**
- Dan North, "Introducing BDD" (2006, dannorth.net)
- Gojko Adzic, *Specification by Example*, Manning (2011) — extends North's BDD concepts
- Matt Wynne & Aslak Hellesoy, *The Cucumber Book*, Pragmatic Bookshelf (2012)

**Role in this skill:** Output format and requirements traceability.

**Key techniques to apply:**

- **Given-When-Then structure** (North): Every test case uses this format:
  ```
  Given [a precondition or context]
  When [an action is performed]
  Then [an observable outcome is expected]
  ```
  Multiple Given/When/Then clauses can be chained with And:
  ```
  Given a user with budget $500k
  And seeking single family homes
  When the system analyses candidate areas
  Then 3-5 areas are identified
  And each area matches the budget constraint
  ```

- **Scenario naming** (North): Test names should describe the behaviour, not the mechanism:
  - Good: "Candidate areas match budget constraint"
  - Bad: "Test RE-1 validation"

- **Specification by example** (Adzic): Use concrete values, not abstract descriptions:
  - Good: "Given a budget of $500,000"
  - Bad: "Given a valid budget"

- **Requirement traceability**: Tag every scenario with the requirement ID(s) it verifies:
  ```
  [Requirement: RE-1] [Priority: MUST]
  ```

**When to reference:** Throughout Phase 2 and 3 — every test case produced uses this format.

---

### David MacIver (Property-Based Testing)

**Sources:**
- David MacIver, *Hypothesis documentation and research papers* (2015–present, hypothesis.works)
- Coblenz et al., "An Empirical Evaluation of Property-Based Testing in Python", OOPSLA/PACMPL (2025)
- John Hughes, "QuickCheck: A Lightweight Tool for Random Testing of Haskell Programs", ICFP (2000)

**Role in this skill:** Identifying requirements where invariant-based tests are more effective than example-based tests.

**Key concept:** Property-based tests assert *what must always be true* for any valid input, then generate hundreds of random inputs automatically. They complement Given/When/Then tests — examples verify specific scenarios, properties verify universal invariants.

**When to apply property-based tests:**

- **Reversible operations**: encode/decode, serialize/deserialize, encrypt/decrypt → `decode(encode(x)) == x`
- **Idempotent operations**: formatting, normalization, deduplication → `f(f(x)) == f(x)`
- **Ordering/sorting**: any sort, rank, or ordering operation → output is ordered, same length, same elements
- **Mathematical relationships**: calculations, conversions, aggregations → known algebraic properties hold
- **Data preservation**: any transform that shouldn't lose data → input elements are all present in output
- **Constraint satisfaction**: validation, filtering → output always satisfies the stated constraint
- **Commutativity**: operations where order shouldn't matter → `f(a, b) == f(b, a)`
- **Round-trip consistency**: save/load, import/export, API request/response → data survives the round trip

**Technique selection addition:**

| Requirement Pattern | Primary Technique | Secondary Technique |
|---|---|---|
| Reversible operation (encode/decode) | Property-based (round-trip) | Boundary value |
| Data transformation preserving content | Property-based (preservation) | Equivalence class |
| Sorting, ranking, ordering | Property-based (ordering + preservation) | Boundary value |
| Calculation with known mathematical properties | Property-based (algebraic) | Boundary value |
| Validation or filtering | Property-based (constraint satisfaction) | Equivalence class |
| Idempotent operation (format, normalize) | Property-based (idempotency) | Single scenario |

**Output format in test cases document:**

Property-based test cases use a different format from Given/When/Then:

```
TC-RE-X-NN: [Descriptive name] [PROPERTY]
Property: For all valid [input type], [invariant that must hold]
Counterexample strategy: [what kinds of edge-case inputs the generator should target]
[Requirement: RE-X] [Priority: MUST]
```

Example:
```
TC-RE-3-04: Currency conversion round-trip preserves value [PROPERTY]
Property: For all amounts (0.01 to 999999.99) and currency pairs,
  convert(convert(amount, A, B), B, A) is within 0.01 of amount
Counterexample strategy: very small amounts, very large amounts,
  currencies with extreme exchange rates
[Requirement: RE-3] [Priority: MUST]
```

**When to reference:** Phase 2 — after identifying requirement patterns, check whether any match the property-based patterns above. If so, generate property-based test specifications alongside Given/When/Then cases. Tag them with `[PROPERTY]` so `/gvm-build` knows to use a property-based testing library.

---

### OWASP Foundation (Security Testing)

**Sources:**
- OWASP, *Testing Guide v4.2* (2023, owasp.org)
- OWASP, *AI Testing Guide v1* (2025, owasp.org)
- OWASP, *Top 10 for LLM Applications* (2025, genai.owasp.org)
- OWASP, *Top 10 for Agentic Applications* (2026, genai.owasp.org)
- Pearce et al., "Asleep at the Keyboard?", IEEE S&P (2022)
- Veracode, *2025 GenAI Code Security Report* (2025)

**Role in this skill:** Identifying requirements that need security-specific test cases because AI-generated code has demonstrated, measurable failure patterns in these categories.

**Key concept:** AI-generated code contains 2.74x more vulnerabilities than human-written code. Injection attacks account for 33.1% of all confirmed AI code vulnerabilities. Security test cases must be generated proactively for any requirement that involves user input, data storage, authentication, API endpoints, or file operations — these are the categories where AI consistently fails.

**When to generate security test cases:**

- **User input accepted** → injection tests (SQL, command, code, LDAP, XPath)
- **HTML/content rendered** → XSS tests (reflected, stored, DOM-based)
- **File paths handled** → path traversal tests (../../etc/passwd, null bytes, encoding bypasses)
- **Authentication/sessions** → session fixation, credential storage, brute force, token handling
- **API endpoints exposed** → SSRF, mass assignment, broken access control, rate limiting
- **Data stored/transmitted** → encryption at rest/transit, PII exposure, logging of sensitive data
- **Configuration/secrets** → hardcoded credentials, API keys in client-side code, .env exposure
- **File upload/download** → unrestricted upload, content-type validation, malicious file execution
- **Redirects/forwards** → open redirect, unvalidated forward

**Technique selection addition:**

| Requirement Pattern | Primary Technique | Secondary Technique |
|---|---|---|
| Accepts user text input | Injection testing (SQLi, XSS, command) | Boundary value |
| Renders user-provided content | XSS testing (reflected, stored, DOM) | Equivalence class |
| Handles file paths or uploads | Path traversal + upload testing | Boundary value |
| Exposes API endpoints | SSRF + access control testing | Decision table |
| Stores or transmits sensitive data | Encryption + PII exposure testing | — |
| Manages authentication/sessions | Auth bypass + session testing | State transition |
| Uses configuration or secrets | Credential exposure testing | — |

**Output format in test cases document:**

Security test cases use the `[SECURITY]` tag:

```
TC-RE-X-NN: [Descriptive name] [SECURITY]
Attack vector: [OWASP category — e.g., A03:2021 Injection]
Given [a precondition with malicious input]
When [the malicious input is submitted]
Then [the system rejects/sanitises/escapes the input]
[Requirement: RE-X] [Priority: MUST]
```

Example:
```
TC-RE-5-03: Search query resists SQL injection [SECURITY]
Attack vector: A03:2021 Injection
Given a search form accepting user text
When the input contains "'; DROP TABLE users; --"
Then the query is parameterised and the input is treated as literal text
And no SQL error is returned to the client
[Requirement: RE-5] [Priority: MUST]

TC-RE-5-04: Search results resist stored XSS [SECURITY]
Attack vector: A07:2021 Cross-Site Scripting
Given a user has previously saved a record with name "<script>alert(1)</script>"
When another user views search results containing that record
Then the script tag is escaped in the rendered HTML
And no script executes in the browser
[Requirement: RE-5] [Priority: MUST]
```

**When to reference:** Phase 2 — after identifying requirement patterns, check whether any involve user input, data storage, authentication, API endpoints, or file operations. If so, generate `[SECURITY]` test cases targeting the relevant OWASP categories. These are mandatory for Must/Should requirements with web or API exposure, not optional deepening.

---

### Cem Kaner

**Sources:**
- *Testing Computer Software* (2nd ed., with Falk & Nguyen), Wiley (1999)
- *Lessons Learned in Software Testing* (with Bach & Pettichord), Wiley (2002)

**Role in this skill:** Risk-based prioritization, consumer app realism, testing what matters.

**Key techniques to apply:**

- **Risk-based test prioritization** (Ch. 4, *Lessons Learned*): Not all tests are equally important. Prioritize based on:
  - Severity of failure (what happens if this breaks?)
  - Likelihood of failure (is this area complex or fragile?)
  - Visibility to user (will the user notice immediately?)
  - MoSCoW priority of the underlying requirement
  - Apply: Must requirements with high-severity failures get the most thorough testing.

- **Consumer software heuristics** (*Testing Computer Software*, Ch. 1-5):
  - Test on real platforms the user will use (not just the developer's machine)
  - Test with realistic data volumes (not just 3 records)
  - Test the first-time user experience (onboarding, empty states)
  - Test interrupted workflows (back button, refresh, close mid-process)
  - Test with slow/unreliable network (for web/mobile)

- **Testing what the requirements don't say** (*Lessons Learned*, Ch. 7):
  - What happens when the user does something unexpected?
  - What are the implicit requirements? (app shouldn't crash, data shouldn't be lost)
  - What platform-specific behaviours matter? (mobile keyboard, screen rotation, notifications)

- **Test case priority alignment with MoSCoW:**

  | Requirement Priority | Happy Path Test Priority | Edge Case Test Priority |
  |---|---|---|
  | Must | Must | Should |
  | Should | Should | Could |
  | Could | Could | Won't (defer) |
  | Won't | Won't | Won't |

**When to reference:** Phase 1 (health report — risk assessment), Phase 2 (priority assignment), Phase 4 (coverage audit — are we testing what matters?).
