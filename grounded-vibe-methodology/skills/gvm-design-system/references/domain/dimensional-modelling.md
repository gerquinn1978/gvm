## Ralph Kimball — Dimensional Modelling & Data Warehousing

**Source:** Ralph Kimball & Margy Ross, *The Data Warehouse Toolkit* (3rd ed.), Wiley (2013)

**Expert scores:**

| Expert | A | P | B | Ad | C | Avg | Tier |
|---|---|---|---|---|---|---|---|
| Ralph Kimball | 5 | 5 | 4 | 5 | 3 | **4.4** | **Established** |
| Margy Ross | 4 | 3 | 2 | 4 | 3 | **3.2** | **Recognised** |

| Work | S | De | C | I | Avg | Tier |
|---|---|---|---|---|---|---|
| Kimball & Ross, *The Data Warehouse Toolkit* 3rd ed | 5 | 5 | 3 | 5 | **4.5** | **Canonical** |

**Evidence (Kimball):** Authority — originator of dimensional modelling. Adoption — implemented in Snowflake, BigQuery, Redshift; dbt references Kimball. Work Depth — 600+ pages with 21 case studies. Work Influence — dbt built on Kimball principles.

*Boundary case: avg 4.4, within 0.1 of Canonical boundary (4.5).*

**Evidence (Ross):** Authority — Kimball Group President; co-taught methodology workshops.

**Activation signals:** Analytical data models, reporting schemas, data warehousing, dimensional modelling, star schemas, fact tables, slowly changing dimensions, business intelligence data layers

**Key techniques to apply:**

- **Star schema** (Ch. 1-3): Fact tables (events, measurements) surrounded by dimension tables (who, what, where, when). Identify facts vs dimensions for any analytical data model.
- **Grain definition** (Ch. 1): Every fact table must have a clearly defined grain — what one row represents. The grain must be defined before any other design decisions.
- **Slowly changing dimensions** (Ch. 5): For dimensions that change over time, define the SCD type: Type 1 (overwrite), Type 2 (versioned), or Type 3 (previous value column). The choice affects both storage and query complexity.
- **Conformed dimensions** (Ch. 4): Shared dimension tables across fact tables ensure consistent reporting. Identify which dimensions are shared across analytical domains.
- **Bus architecture** (Ch. 4): The enterprise data warehouse is built incrementally by conforming dimensions across subject areas. Each new fact table reuses existing conformed dimensions rather than creating new ones.

**When specifying analytical data models:**
- Define the grain for each fact table before designing columns
- Classify every entity as a fact or a dimension
- Identify which dimensions are shared (conformed) across fact tables
- Define SCD strategy for each dimension that changes over time
- Separate staging, integration, and presentation layers
