## Martin Kleppmann — Data-Intensive Applications

**Source:** Martin Kleppmann, *Designing Data-Intensive Applications*, O'Reilly (2017)

**Expert scores:**

| Expert | A | P | B | Ad | C | Avg | Tier |
|---|---|---|---|---|---|---|---|
| Martin Kleppmann | 5 | 5 | 4 | 5 | 4 | **4.6** | **Canonical** |

| Work | S | De | C | I | Avg | Tier |
|---|---|---|---|---|---|---|
| Kleppmann, *Designing Data-Intensive Applications* | 4 | 5 | 4 | 5 | **4.5** | **Canonical** |

**Evidence:** Authority — DDIA universally cited. Adoption — required reading at Stripe, Airbnb, Cloudflare. Work Depth — B-trees, LSM-trees, linearisability from first principles.

**Activation signals:** Data model spec, storage decisions, caching strategy, consistency requirements, data flow between components

**Key techniques to apply:**

- **Data model fit** (Ch. 2): Relational (structured, relationships matter), document (self-contained aggregates, flexible schema), or graph (highly connected data)? The data model should match the access patterns, not the other way around.
- **Storage engine trade-offs** (Ch. 3): OLTP (many small reads/writes, low latency) vs OLAP (few large reads, analytical queries). Most web apps are OLTP.
- **Caching strategy** (Ch. 5, 11): Cache-aside, read-through, write-through, write-behind. Each has consistency and complexity trade-offs. Define TTLs per data type (property listings change daily, school ratings change annually).
- **Data flow** (Ch. 11-12): How does data move through the system? REST APIs, message queues, event logs? What are the consistency guarantees at each step?
- **Schema evolution** (Ch. 4): How will the data model change over time? Forward and backward compatibility in serialisation formats.

**When specifying data model and storage:**
- Define entities, relationships, and access patterns
- Specify which data is mutable vs immutable
- Define the caching strategy with TTLs per data type
- Specify consistency requirements: is eventual consistency acceptable? Where?
- Define the data lifecycle: creation, caching, expiry, deletion
