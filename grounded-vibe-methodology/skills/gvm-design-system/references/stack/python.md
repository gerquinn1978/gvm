# Python

### Luciano Ramalho — Pythonic Patterns
**Source:** *Fluent Python* (2nd ed.), O'Reilly (2022)

> **Expert Score — Luciano Ramalho**
> Authority=5 · Publication=5 · Breadth=4 · Adoption=5 · Currency=5 → **4.8 — Canonical**
>
> | Work | Specificity | Depth | Currency | Influence | Avg | Tier |
> |---|---|---|---|---|---|---|
> | *Fluent Python* 2nd ed. | 4 | 5 | 5 | 5 | **4.75** | Canonical |
>
> Evidence: Authority — definitive idiomatic Python; praised by Guido. Adoption — top Python book on O'Reilly Learning. Work Depth — covers internals, not surface usage.


**Key principles to apply in specs:**
- **Data model leverage** (Part I): Use Python's data model (`__repr__`, `__eq__`, `__hash__`, protocols) rather than fighting it. Specify domain objects that work naturally with Python builtins.
- **Type hints as documentation** (Ch. 8, 15): All public interfaces should have type annotations. The spec should define key types and protocols.
- **Iterators and generators** (Part V): For data processing pipelines, prefer lazy evaluation. Don't load entire datasets into memory when streaming would work.
- **Async/await** (Ch. 21): For I/O-bound work (API calls, database queries), use async. The spec should identify which operations are async and which are sync.
- **Dataclasses and named tuples** (Ch. 5): For data transfer objects and value types, prefer dataclasses or named tuples over plain dicts.

### Harry Percival & Bob Gregory — Architecture Patterns with Python
**Sources:**
- Harry Percival & Bob Gregory, *Architecture Patterns with Python*, O'Reilly (2020)
- Harry Percival, *Test-Driven Development with Python* (3rd ed.), O'Reilly (2024)

> **Expert Score — Harry Percival**
> Authority=4 · Publication=4 · Breadth=4 · Adoption=4 · Currency=5 → **4.2 — Established**
>
> **Expert Score — Bob Gregory**
> Authority=4 · Publication=4 · Breadth=3 · Adoption=3 · Currency=3 → **3.4 — Recognised**
>
> | Work | Specificity | Depth | Currency | Influence | Avg | Tier |
> |---|---|---|---|---|---|---|
> | *Architecture Patterns with Python* | 5 | 4 | 3 | 4 | **4.0** | Established |
> | *TDD with Python* 3rd ed. | 5 | 4 | 5 | 4 | **4.5** | Canonical |
>
> Evidence: Currency — TDD 3rd ed 2024. Work(APP) Specificity — repository, service layer, unit of work implementations. Work(TDD) Currency — 2024.


**Key principles to apply in specs:**
- **Repository pattern** (Ch. 2): Abstract the data access layer behind a repository interface. The spec should define repository interfaces for each data domain.
- **Service layer** (Ch. 4): Business logic lives in service functions, not in web handlers or repositories. The spec should define the service layer API.
- **Unit of Work** (Ch. 6): Group related database operations into atomic units. Specify where transactional boundaries fall.
- **Domain model** (Ch. 1): Core business logic should be framework-independent. The spec should distinguish between domain logic and infrastructure.
- **TDD workflow** (Percival): Tests are written before implementation. The spec should reference test cases from `/test-cases` and note which tests apply to which components.

### Sebastian Ramirez — FastAPI
**Source:** FastAPI official documentation (fastapi.tiangolo.com), creator's design philosophy

> **Expert Score — Sebastian Ramirez**
> Authority=5 · Publication=4 · Breadth=3 · Adoption=5 · Currency=5 → **4.4 — Established**
>
> | Work | Specificity | Depth | Currency | Influence | Avg | Tier |
> |---|---|---|---|---|---|---|
> | FastAPI docs | 5 | 4 | 5 | 5 | **4.75** | Canonical |
>
> Evidence: Authority — created FastAPI. Adoption — Microsoft, Netflix, Uber. Work Specificity — DI, Pydantic, async, OAuth2.


**Key principles to apply in specs:**
- **Dependency injection** (docs: Dependencies): Use FastAPI's DI system for shared resources (database sessions, auth, external clients). The spec should identify injectable dependencies.
- **Pydantic models for validation** (docs: Body): Request/response schemas as Pydantic models. The spec should define these models.
- **Async endpoints** (docs: Async): External API calls should use async endpoints. The spec should mark which endpoints are async.
- **Background tasks** (docs: Background Tasks): For long-running operations, use background tasks or a task queue. The spec should define which operations run in the background.
- **OpenAPI integration** (docs: API docs): FastAPI auto-generates API docs. The spec's API definitions will map directly to the OpenAPI schema.

### Miguel Grinberg — Flask
**Source:** Miguel Grinberg, *Flask Web Development* (2nd ed.), O'Reilly (2018); blog posts (blog.miguelgrinberg.com)

> **Expert Score — Miguel Grinberg**
> Authority=4 · Publication=4 · Breadth=3 · Adoption=4 · Currency=3 → **3.6 — Established**
>
> | Work | Specificity | Depth | Currency | Influence | Avg | Tier |
> |---|---|---|---|---|---|---|
> | *Flask Web Dev* 2nd ed. | 4 | 4 | 3 | 4 | **3.75** | Established |
>
> Evidence: Authority — most prominent Flask educator. Work Depth — covers Flask internals.


**Key principles to apply in specs:**
- **Application factory** (Ch. 7): Use the application factory pattern for configuration flexibility and testing. The spec should define factory parameters.
- **Blueprints for modularity** (Ch. 7): Organise routes into blueprints by domain. The spec should define blueprint boundaries.
- **Extensions over custom code**: Use established Flask extensions (Flask-SQLAlchemy, Flask-Login, Flask-Migrate) rather than reinventing. The spec should list required extensions.
- **Context locals** (Ch. 2): Understand Flask's request/application context model. The spec should identify what lives in each context.
- **Flask with HTMX** (blog): For server-rendered interactive UI without a JavaScript framework. Evaluate whether this fits the requirements vs a full SPA.
