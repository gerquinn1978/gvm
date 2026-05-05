# Architecture Techniques — Expert Reference

This file is consulted during Phase 1 (assessment) and throughout spec writing. It provides techniques from the Tier 1 architecture panel with citations.

---

## Architecturally Significant Requirements (ASRs)

**Source:** Michael Keeling, *Design It!*, Ch. 4-5

ASRs are requirements that have a measurable effect on the software architecture. Not all requirements are architecturally significant — most functional requirements can be satisfied by many architectures.

**How to identify ASRs from a requirements document:**

1. **Quality attribute requirements** — performance targets, security constraints, availability needs. E.g., "must complete within 20 minutes" (PL-5) forces async processing with incremental persistence.
2. **Constraint requirements** — mandated technologies, standards, or integration points. E.g., "must support US and UK data sources" (GS-1, GS-1a) forces a locale-abstraction layer.
3. **High-business-value functional requirements** — features central to the value proposition. E.g., "user can interject on any agent at any time" (PL-16) forces bidirectional real-time communication.
4. **Requirements that are hard to change later** — decisions that, once implemented, are expensive to reverse. E.g., database choice, authentication model, API contract format.

**ASR template:**
```
ASR: [short name]
Source: [requirement ID(s)]
Stimulus: [what triggers the quality attribute concern]
Response: [what the system must do]
Measure: [how to verify the response is adequate]
Architectural impact: [what design decisions this forces]
```

---

## Complexity Assessment

**Source:** George Fairbanks, *Just Enough Software Architecture*, Ch. 1-3

The amount of architecture (and specification) a project needs is proportional to the risk it carries.

**Risk categories:**
- **Technical risk** — novel technology, unfamiliar domain, complex integrations
- **Domain risk** — unclear requirements, evolving business rules
- **Project risk** — team size, distributed development, long timeline
- **Operational risk** — high availability needs, data sensitivity, compliance

**Fairbanks' rule of thumb:**
- Low risk (CRUD app, well-understood domain) → 1-2 specs, light depth
- Medium risk (multi-component app, some novel parts) → 3-4 specs, moderate depth
- High risk (distributed system, novel domain, many integrations) → 5-8 specs, thorough depth

**Calibrating depth within a spec:**
- Well-understood patterns (REST API, CRUD operations) → describe the pattern name and any project-specific variations. Don't re-explain REST.
- Novel or risky areas (custom orchestration, complex caching strategy, unusual data flow) → full detail: ADR, component design, sequence diagram in prose, error handling.
- The test: "If a competent developer read just this section, could they implement it correctly without guessing?" If yes, the depth is right.

---

## C4 Model — Zoom Levels

**Source:** Simon Brown, *Software Architecture for Developers*, C4 Model (c4model.com)

Four levels of zoom for describing software architecture:

### Level 1: System Context
- What is this system? Who uses it? What external systems does it interact with?
- Audience: everyone (stakeholders, developers, operations)
- In spec terms: the "Purpose" section of the architecture overview

### Level 2: Containers
- What are the major deployable units? (web app, API server, database, message queue, etc.)
- How do they communicate? (HTTP, WebSocket, message bus, database)
- Audience: developers and operations
- In spec terms: the "Container Diagram" section of the architecture overview

### Level 3: Components
- Within a container, what are the major structural building blocks?
- What are their responsibilities and interfaces?
- Audience: developers working on that container
- In spec terms: the "Component Design" section of each domain spec

### Level 4: Code
- Classes, functions, modules — the actual implementation
- Audience: the developer (or Claude) writing the code
- In spec terms: this level belongs in `/build`, not `/tech-spec`

**Key principle:** Each level answers different questions. Don't mix levels — a diagram (or spec section) that shows both containers and code-level detail serves nobody.

---

## Architecture Decision Records (ADRs)

**Source:** Michael Keeling, *Design It!*, Ch. 13; Michael Nygard's original ADR format

An ADR captures one significant architecture decision: what was decided, why, and what alternatives were considered.

**ADR format for specs:**

```
Decision: [what was decided — one sentence]
Status: [Proposed | Accepted | Deprecated | Superseded by ADR-XXX]

Context:
[Why this decision needed to be made. What requirements or constraints drive it.
Reference requirement IDs.]

Options Considered:
1. [Option A] — [brief description, pros, cons]
2. [Option B] — [brief description, pros, cons]
3. [Option C] — [brief description, pros, cons]

Decision:
[Which option was chosen and why. Be specific about the reasoning.]

Consequences:
[What follows from this decision — both positive and negative.
What new constraints does this create? What becomes easier? What becomes harder?]
```

**When to write an ADR:**
- Technology choice (language, framework, database, hosting)
- Architectural pattern choice (monolith vs microservices, sync vs async, REST vs GraphQL)
- Data model decisions (schema design, caching strategy, consistency model)
- Integration decisions (how systems communicate, API contracts)
- Security decisions (auth model, encryption approach, data protection)

**When NOT to write an ADR:**
- Obvious choices with no real alternatives ("use HTTPS" doesn't need an ADR)
- Implementation details ("use a for loop vs map" is code, not architecture)
- Decisions already made in requirements (the spec explains *how* to fulfil them, not whether to)

---

## Quality Attribute Scenarios

**Source:** Bass, Clements, Kazman, *Software Architecture in Practice* (4th ed.), Ch. 4-7

Quality attribute scenarios make non-functional requirements testable and precise.

**Scenario template:**
```
Source: [who/what generates the stimulus]
Stimulus: [what happens]
Artifact: [what part of the system is affected]
Environment: [under what conditions]
Response: [what the system does]
Response Measure: [how to verify — must be measurable]
```

**Common quality attributes and their architectural tactics:**

| Quality Attribute | Example Tactic | When to Apply |
|---|---|---|
| **Performance** | Caching, async processing, resource pooling | Time-budget requirements, latency targets |
| **Availability** | Redundancy, graceful degradation, health checks | Uptime requirements, external dependency failure |
| **Security** | Authentication, authorization, encryption, input validation | Data protection requirements, user data handling |
| **Modifiability** | Loose coupling, information hiding, dependency injection | Systems expected to evolve, multiple data source support |
| **Testability** | Dependency injection, interface segregation, observable state | Complex business logic, integration-heavy systems |
| **Usability** | Progressive disclosure, undo, feedback, error prevention | User-facing applications, real-time interaction |

---

## Expert Discovery Protocol

When a domain, technology, or problem area is encountered that has no matching specialist in the reference files, do not proceed with generic knowledge. Instead:

1. **Identify the gap** — name the domain or technology that lacks a specialist (e.g., "GraphQL API design", "WebRTC real-time communication", "CQRS/Event Sourcing")
2. **Research authoritative figures** — identify 1-3 experts who are widely recognised authorities in this area. Prefer authors of definitive books, creators of the technology, or recognised thought leaders with substantial published work.
3. **Cite specific works** — for each expert, identify their most authoritative publication (book, official documentation, seminal paper/article) with title, publisher, and year.
4. **Extract key principles** — list 3-6 principles from their work that are relevant to specification writing, following the same format as existing specialist entries.
5. **Document in the output** — add the discovered expert and their principles as a clearly marked section in the document being produced (requirements, test cases, or spec). Use this format:

```markdown
### Expert Discovery: [Domain]

The following specialist was identified for [domain] guidance:

**[Expert Name]** — *[Work Title]*, [Publisher] ([Year])
- **[Principle 1]**: [Description and how it applies]
- **[Principle 2]**: [Description and how it applies]
```

6. **Flag for reference file update** — at the end of the session, note which experts were discovered so they can be added to the permanent reference files for future use.

**The goal:** every domain in every spec should have authoritative backing. If the existing roster doesn't cover it, expand it on the fly and make the expansion visible and traceable.

---

## Conceptual Integrity Review

**Source:** Frederick Brooks, *The Mythical Man-Month*, Ch. 4; *The Design of Design*, Ch. 4-6

Conceptual integrity means the system appears to have been designed by a single mind — consistent patterns, unified vocabulary, coherent mental model.

**Review checklist (apply in Phase 4):**

1. **Consistent vocabulary** — are the same concepts named the same way across all specs? (e.g., "candidate area" is always "candidate area", never "search result" in one spec and "target location" in another)
2. **Consistent patterns** — if errors are handled one way in the backend spec, are they handled the same way in the frontend spec?
3. **No contradictions** — does the data model spec agree with what the API spec says about data structures?
4. **Unified mental model** — could someone read the architecture overview and then predict what they'd find in each domain spec?
5. **Proportional complexity** — are similar things similarly complex? Or is one domain over-engineered while another is hand-waved?
