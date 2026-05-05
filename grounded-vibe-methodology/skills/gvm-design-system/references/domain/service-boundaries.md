## Sam Newman — Service Boundaries & API Design

**Sources:**
- Sam Newman, *Building Microservices* (2nd ed.), O'Reilly (2021)
- Sam Newman, *Monolith to Microservices*, O'Reilly (2019)

**Expert scores:**

| Expert | A | P | B | Ad | C | Avg | Tier |
|---|---|---|---|---|---|---|---|
| Sam Newman | 4 | 4 | 4 | 4 | 5 | **4.2** | **Established** |

| Work | S | De | C | I | Avg | Tier |
|---|---|---|---|---|---|---|
| Newman, *Building Microservices* 2nd ed | 4 | 4 | 5 | 4 | **4.25** | **Established** |
| Newman, *Monolith to Microservices* | 5 | 4 | 4 | 3 | **4.0** | **Established** |

**Evidence:** Currency — 2nd ed 2021 most current microservices text. *Monolith to Microservices* Specificity — focused on migration patterns.

**Activation signals:** Multi-service architecture, API design, service boundary decisions

**Key techniques to apply:**

- **Start with a monolith** (Ch. 3): Don't start with microservices. Start with a well-structured monolith and extract services only when the boundaries are proven. The spec should define logical boundaries (modules) that *could* become services later.
- **Domain-driven boundaries** (Ch. 3-4): Service boundaries should align with business domains, not technical layers. "Real estate service" not "database service."
- **API design** (Ch. 5): APIs are contracts. Define request/response formats, error responses, versioning strategy. Use established conventions (REST, JSON:API, or similar).
- **When NOT to split** (Ch. 1): If two things change together, they should live together. Don't create distributed systems complexity for components that are tightly coupled anyway.

**When specifying service boundaries:**
- Start by defining logical modules within a monolith
- Identify which modules have genuinely independent lifecycles
- Define API contracts between modules (even within a monolith — this enables future extraction)
- Be explicit about what's a module boundary vs a service boundary
