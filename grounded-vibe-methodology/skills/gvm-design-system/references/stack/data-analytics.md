# Data Analytics & Processing Pipelines

### Wes McKinney — Data Processing with Python
**Source:** Wes McKinney, *Python for Data Analysis* (3rd ed.), O'Reilly (2022); creator of pandas and Apache Arrow

> **Expert Score — Wes McKinney**
> Authority=5 · Publication=5 · Breadth=4 · Adoption=5 · Currency=5 → **4.8 — Canonical**
>
> | Work | Specificity | Depth | Currency | Influence | Avg | Tier |
> |---|---|---|---|---|---|---|
> | *Python for Data Analysis* 3rd ed. | 5 | 5 | 5 | 5 | **5.0** | Canonical |
>
> Evidence: Authority — created pandas and Apache Arrow. Adoption — 40M+ monthly downloads.


**Key principles to apply in specs:**
- **DataFrame as the core abstraction** (Ch. 5-7): For tabular data processing, pandas DataFrames are the standard. The spec should define data schemas as column names, types, and relationships.
- **Vectorised operations over loops** (Ch. 4): Never iterate rows in Python. The spec should define transformations as vectorised operations (filter, group, aggregate, join).
- **Memory management** (Ch. 7): For large datasets, specify chunked reading, dtype optimisation, and when to use categorical types. The spec should estimate data volumes.
- **Apache Arrow for interop** (various): Arrow columnar format for zero-copy data sharing between systems. Consider when data crosses process/language boundaries.

### Maxime Beauchemin — Data Pipeline Architecture
**Source:** Maxime Beauchemin (creator of Apache Airflow and Apache Superset), *The Rise of the Data Engineer* (blog), Airflow documentation

> **Expert Score — Maxime Beauchemin**
> Authority=5 · Publication=3 · Breadth=4 · Adoption=5 · Currency=3 → **4.0 — Established**
>
> | Work | Specificity | Depth | Currency | Influence | Avg | Tier |
> |---|---|---|---|---|---|---|
> | blog+docs | 4 | 3 | 4 | 4 | **3.75** | Established |
>
> Evidence: Authority — created Airflow and Superset. Adoption — 35,000+ GitHub stars.


**Key principles to apply in specs:**
- **DAG-based orchestration**: Define data pipelines as directed acyclic graphs — each node is a task, edges are dependencies. The spec should define the DAG structure for any multi-step data processing.
- **Idempotent tasks**: Every pipeline task should be safe to re-run. The spec should define how each task achieves idempotency (overwrite, upsert, or check-and-skip).
- **Backfill capability**: Pipelines should be able to reprocess historical data. The spec should define time partitioning and backfill strategy.
- **Data quality checks**: Define validation steps within the pipeline — row counts, null checks, schema validation, business rule assertions.

### Martin Kleppmann — Stream & Batch Processing
**Source:** Martin Kleppmann, *Designing Data-Intensive Applications*, O'Reilly (2017), Ch. 10-12

> *Expert scored in `domain/data-intensive.md`. Classification: Canonical (avg 4.6).*
>
> *DDIA scored in `domain/data-intensive.md`. Classification: Canonical (avg 4.5). Chapters 10-12 (stream processing, batch processing) are the activation scope for this entry.*


**Key principles to apply in specs:**
- **Batch vs stream** (Ch. 10-11): Batch for periodic aggregation and reporting; stream for real-time updates. The spec should identify which data flows are batch and which are stream.
- **Exactly-once semantics** (Ch. 11): For critical data pipelines, define the exactly-once delivery strategy — idempotent writes, transactional producers, or deduplication.
- **Derived data** (Ch. 12): Distinguish between system-of-record data and derived views. The spec should identify which data stores are authoritative and which are derived/cached.
- **Lambda vs Kappa architecture** (Ch. 11): Lambda uses separate batch and stream paths; Kappa uses stream for everything. Choose based on latency requirements and complexity tolerance.

### Holden Karau & Rachel Warren — Scalable Data Processing
**Source:** Holden Karau & Rachel Warren, *High Performance Spark* (2nd ed.), O'Reilly (2017); Holden Karau, *Learning Spark* (2nd ed., with Damji, Wenig, Das), O'Reilly (2020)

> **Expert Score — Holden Karau**
> Authority=4 · Publication=4 · Breadth=3 · Adoption=4 · Currency=3 → **3.6 — Established**
>
> **Expert Score — Rachel Warren**
> Authority=3 · Publication=3 · Breadth=2 · Adoption=2 · Currency=2 → **2.4 — Emerging**
>
> | Work | Specificity | Depth | Currency | Influence | Avg | Tier |
> |---|---|---|---|---|---|---|
> | *High Performance Spark* | 4 | 4 | 2 | 3 | **3.25** | Recognised |
> | *Learning Spark* 2nd ed. | 4 | 4 | 4 | 4 | **4.0** | Established |
>
> Evidence: Karau — Spark committer. Work(LS) Currency — 2020; Spark 3.0.


**Key principles to apply in specs:**
- **Partition strategy** (Ch. 4-5): For distributed processing, define how data is partitioned — by key, by time, by geography. Partition strategy determines parallelism and data locality.
- **Narrow vs wide transformations**: Narrow (map, filter) don't shuffle data; wide (groupBy, join) do. The spec should minimise shuffles in the pipeline design.
- **Caching strategy**: Identify which intermediate results should be cached/persisted vs recomputed. Especially relevant for iterative analysis.

### Dremio — Lakehouse Query Engine
**Source:** Dremio official documentation (docs.dremio.com), *Apache Arrow and Dremio* technical guides, Tomer Shiran (Dremio founder) talks on data lakehouse architecture

> **Expert Score — Dremio**
> Authority=4 · Publication=3 · Breadth=4 · Adoption=3 · Currency=5 → **3.8 — Established**
>
> | Work | Specificity | Depth | Currency | Influence | Avg | Tier |
> |---|---|---|---|---|---|---|
> | docs | 4 | 3 | 5 | 3 | **3.75** | Established |
>
> Evidence: Authority — Apache Arrow and Iceberg contributors.


**Key principles to apply in specs:**
- **Data lakehouse layer**: Dremio sits between object storage (MinIO/S3) and consumers, providing SQL query federation without moving data. The spec should define which data sources Dremio federates and how reflections are used.
- **Apache Iceberg integration**: Dremio's native Iceberg support enables ACID transactions on data lake tables. The spec should define which tables use Iceberg format and their partition strategy.
- **Reflections for acceleration**: Dremio reflections (materialised aggregations and raw reflections) accelerate queries without denormalising the source data. The spec should identify high-frequency query patterns that warrant reflections.
- **Virtual datasets**: Define virtual datasets (views) as the semantic layer between raw data and consumers. The spec should define the virtual dataset hierarchy — raw → curated → business-ready.
- **Arrow Flight for high-performance access**: For Python/pandas consumers, use Arrow Flight protocol instead of JDBC/ODBC for zero-copy data transfer. The spec should specify the access protocol per consumer.
- **Role-based access**: Define data access policies at the dataset level. The spec should map user roles to dataset visibility.

**When specifying Dremio in the architecture:**
- Define the data sources Dremio federates (MinIO buckets, databases, other storage)
- Specify which datasets are raw, curated, and business-ready
- Identify query patterns that need reflections
- Define the access protocol per consumer (Arrow Flight for analytics, REST for API)
- Specify partition and sort strategies for Iceberg tables

### Jake VanderPlas — Data Visualisation & Scientific Python
**Source:** Jake VanderPlas, *Python Data Science Handbook* (2nd ed.), O'Reilly (2023)

> **Expert Score — Jake VanderPlas**
> Authority=4 · Publication=5 · Breadth=5 · Adoption=5 · Currency=4 → **4.6 — Canonical**
>
> | Work | Specificity | Depth | Currency | Influence | Avg | Tier |
> |---|---|---|---|---|---|---|
> | *Python DS Handbook* 2nd ed. | 5 | 4 | 5 | 5 | **4.75** | Canonical |
>
> Evidence: Authority — created Altair. Publication — O'Reilly 2nd ed 2023; free on GitHub. Adoption — most assigned data science text.


**Key principles to apply in specs:**
- **NumPy for numerical computation** (Ch. 2): For heavy numerical work, specify NumPy arrays over Python lists. The spec should identify computationally intensive operations.
- **Matplotlib/Seaborn for static visualisation** (Ch. 4): For generated reports and brochures, define chart types and data mappings.
- **Scikit-learn patterns** (Ch. 5): For ML-adjacent tasks (ranking, classification, clustering), follow scikit-learn's fit/transform/predict API pattern.
