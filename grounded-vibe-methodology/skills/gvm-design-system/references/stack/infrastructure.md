# Infrastructure & DevOps

### Charity Majors — Observability
**Sources:**
- Charity Majors, Liz Fong-Jones, George Miranda, *Observability Engineering*, O'Reilly (2022)

> **Expert Score — Charity Majors**
> Authority=5 · Publication=5 · Breadth=3 · Adoption=4 · Currency=4 → **4.2 — Established**
>
> | Work | Specificity | Depth | Currency | Influence | Avg | Tier |
> |---|---|---|---|---|---|---|
> | *Observability Engineering* | 4 | 4 | 4 | 5 | **4.25** | Established |
>
> Evidence: Authority — co-founder Honeycomb; coined modern observability. Work Influence — shifted industry practice.


**Key principles to apply in specs:**
- **Structured events over logs** (Ch. 4): Emit structured events with high cardinality fields, not printf-style log lines. The spec should define key event schemas.
- **Traces for distributed systems** (Ch. 5): For multi-component systems, define trace propagation. Each request should be traceable across services/agents.
- **SLOs over uptime** (Ch. 9): Define Service Level Objectives rather than vague "high availability" requirements.

### Kelsey Hightower — Container Patterns
**Sources:**
- Kelsey Hightower, *Kubernetes Up and Running* (with Burns & Beda), O'Reilly
- Conference talks on simplicity and platform engineering

> **Expert Score — Kelsey Hightower**
> Authority=5 · Publication=4 · Breadth=4 · Adoption=5 · Currency=3 → **4.2 — Established**
>
> | Work | Specificity | Depth | Currency | Influence | Avg | Tier |
> |---|---|---|---|---|---|---|
> | *K8s Up and Running* | 4 | 3 | 3 | 5 | **3.75** | Established |
>
> Evidence: Authority — most influential K8s educator. Adoption — standard introductory K8s text. Work Influence — canonical; co-authored by K8s creators.


**Key principles to apply in specs:**
- **Containers as deployment unit**: Each component should be containerisable. The spec should define what runs in each container.
- **12-Factor App** (12factor.net): Configuration via environment variables, stateless processes, disposable instances.
- **Don't overcomplicate**: If a single container with a database is sufficient, don't add Kubernetes. Match infrastructure complexity to actual needs.
