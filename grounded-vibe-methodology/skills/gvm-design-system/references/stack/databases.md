# Databases

### Markus Winand — SQL Performance
**Sources:**
- Markus Winand, *SQL Performance Explained*, self-published (2012)
- use-the-index-luke.com

> **Expert Score — Markus Winand**
> Authority=5 · Publication=4 · Breadth=4 · Adoption=5 · Currency=3 → **4.2 — Established**
>
> | Work | Specificity | Depth | Currency | Influence | Avg | Tier |
> |---|---|---|---|---|---|---|
> | *SQL Performance Explained* | 5 | 5 | 2 | 5 | **4.25** | Established |
> | use-the-index-luke.com | 5 | 4 | 4 | 5 | **4.5** | Canonical |
>
> Evidence: Authority — definitive SQL indexing voice. Adoption — de facto SQL performance reference.


**Key principles to apply in specs:**
- **Index-first design** (Ch. 1-3): Design indexes alongside the schema, not as an afterthought. The spec should define key indexes based on query patterns.
- **Access patterns drive schema** (Ch. 2): Understand the queries before designing the tables. The spec should list the key query patterns.
- **Avoid N+1** (Ch. 4): Join where possible, avoid querying in loops. The spec should identify relationships that will be queried together.
- **Pagination design** (Ch. 6): For list views (search history), specify keyset pagination over offset pagination.

### Brandur Leach — PostgreSQL Patterns
**Source:** Brandur Leach, blog posts (brandur.org) on PostgreSQL, transactional patterns, idempotency

> **Expert Score — Brandur Leach**
> Authority=3 · Publication=2 · Breadth=4 · Adoption=3 · Currency=4 → **3.2 — Recognised**
>
> | Work | Specificity | Depth | Currency | Influence | Avg | Tier |
> |---|---|---|---|---|---|---|
> | blog | 4 | 4 | 4 | 3 | **3.75** | Established |
>
> Evidence: Work Specificity — implementation-specific schema designs and code patterns.


**Key principles to apply in specs:**
- **ACID as a feature** (various posts): Use database transactions for consistency. Don't reinvent transactional guarantees in application code.
- **Transactional outbox** (various posts): For reliable event publishing, write events to an outbox table within the same transaction as the data change.
- **Idempotency keys** (various posts): For operations that may be retried (API calls, background jobs), use idempotency keys to prevent double-processing.
- **Advisory locks** (various posts): For operations that must not run concurrently (cache refresh, analysis runs per user), use PostgreSQL advisory locks.

### Itzik Ben-Gan — Microsoft SQL Server
**Source:** Itzik Ben-Gan, *T-SQL Fundamentals* (4th ed.), Microsoft Press (2023); *T-SQL Querying*, Microsoft Press (2015)

> **Expert Score — Itzik Ben-Gan**
> Authority=5 · Publication=5 · Breadth=2 · Adoption=5 · Currency=5 → **4.4 — Established**
>
> | Work | Specificity | Depth | Currency | Influence | Avg | Tier |
> |---|---|---|---|---|---|---|
> | *T-SQL Fundamentals* 4th ed. | 5 | 5 | 5 | 5 | **5.0** | Canonical |
> | *T-SQL Querying* | 5 | 5 | 2 | 4 | **4.0** | Established |
>
> Evidence: Authority — foremost T-SQL authority; MVP since 1999. Work(Fund) Currency — 4th ed 2023; SQL Server 2022.
>
> *Boundary case: avg 4.4, within 0.1 of Canonical boundary (4.5). If an independent rescore confirms any dimension increase, reclassifies to Canonical.*


**Key principles to apply in specs:**
- **Window functions** (*T-SQL Querying*, Ch. 4): Use window functions for ranking, running totals, and analytical queries rather than correlated subqueries. The spec should identify where analytical queries are needed.
- **Set-based thinking** (throughout): SQL Server performs best with set-based operations, not row-by-row cursors. The spec should define operations as set transformations.
- **Temporal tables** (*T-SQL Fundamentals*, Ch. 9): For data that needs history tracking (search runs, cached data versions), consider system-versioned temporal tables.
- **Execution plan awareness** (*T-SQL Querying*, Ch. 3): Key queries should be designed with the execution plan in mind. The spec should flag complex queries that need plan review.

### Baron Schwartz — MySQL
**Source:** Baron Schwartz, Peter Zaitsev, Vadim Tkachenko, *High Performance MySQL* (4th ed.), O'Reilly (2021)

> **Expert Score — Baron Schwartz**
> Authority=5 · Publication=5 · Breadth=3 · Adoption=5 · Currency=4 → **4.4 — Established**
>
> | Work | Specificity | Depth | Currency | Influence | Avg | Tier |
> |---|---|---|---|---|---|---|
> | *High Performance MySQL* 4th ed. | 5 | 5 | 4 | 5 | **4.75** | Canonical |
>
> Evidence: Authority — Percona creator. Work Depth — InnoDB source-code level. Work Influence — cited in MySQL docs.
>
> *Boundary case: avg 4.4, within 0.1 of Canonical boundary (4.5). If an independent rescore confirms any dimension increase, reclassifies to Canonical.*


**Key principles to apply in specs:**
- **Schema design for performance** (Ch. 4): Choose data types carefully — smaller is faster. Use appropriate integer sizes, avoid TEXT/BLOB where VARCHAR suffices.
- **Indexing strategy** (Ch. 5): Understand clustered vs secondary indexes in InnoDB. Design composite indexes to cover common query patterns (leftmost prefix rule).
- **Query optimization** (Ch. 6): Structure queries to leverage indexes. The spec should define expected query patterns and their index coverage.
- **Replication and scaling** (Ch. 10-11): For read-heavy workloads, consider read replicas. The spec should identify read vs write patterns.
- **InnoDB specifics** (Ch. 1): Understand InnoDB's MVCC, row-level locking, and clustered index structure. These affect schema and transaction design.

### Joe Celko — SQL Design Patterns
**Source:** Joe Celko, *SQL for Smarties* (5th ed.), Morgan Kaufmann (2014); *Trees and Hierarchies in SQL*, Morgan Kaufmann (2012)

> **Expert Score — Joe Celko**
> Authority=5 · Publication=5 · Breadth=5 · Adoption=4 · Currency=2 → **4.2 — Established**
>
> | Work | Specificity | Depth | Currency | Influence | Avg | Tier |
> |---|---|---|---|---|---|---|
> | *SQL for Smarties* | 4 | 5 | 2 | 4 | **3.75** | Established |
> | *Trees and Hierarchies* | 5 | 5 | 2 | 4 | **4.0** | Established |
>
> Evidence: Authority — ANSI SQL standards committee; originated nested sets.


**Key principles to apply in specs:**
- **Declarative thinking** (throughout): Express what you want, not how to get it. The spec should define data requirements declaratively.
- **Hierarchical data** (*Trees and Hierarchies*): For tree structures (geographic scope: country → state → county → town), choose the right model: adjacency list, nested sets, or materialised path based on read/write patterns.
- **Temporal data patterns** (*SQL for Smarties*, Ch. 29): For time-varying data (property prices, market trends), define how time dimensions are modelled in the schema.
- **Constraint-driven design** (throughout): Use CHECK constraints, UNIQUE constraints, and foreign keys to encode business rules in the schema, not just in application code.
