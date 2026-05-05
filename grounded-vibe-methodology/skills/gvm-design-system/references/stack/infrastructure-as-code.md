# Infrastructure as Code

> **Activation signals:** Cloud infrastructure specification, infrastructure-as-code, Terraform, Pulumi, CDK, CloudFormation, cloud resource provisioning

### Yevgeniy Brikman — Infrastructure as Code
**Source:** *Terraform: Up and Running* (3rd ed.), O'Reilly (2022)

> **Expert Score — Yevgeniy Brikman**
> Authority=4 · Publication=5 · Breadth=3 · Adoption=4 · Currency=4 → **4.0 — Established**
>
> | Work | Specificity | Depth | Currency | Influence | Avg | Tier |
> |---|---|---|---|---|---|---|
> | *Terraform: Up and Running* 3rd ed. | 5 | 4 | 4 | 5 | **4.5** | Canonical |
>
> Evidence: Authority — co-founder Gruntwork; former LinkedIn, TripAdvisor; active speaker and blogger. Publication — O'Reilly top-tier. Breadth — Terraform-focused; narrower domain. Adoption — de facto Terraform learning resource; Gruntwork modules used by hundreds of companies; referenced in HashiCorp's own learning resources. Currency — 3rd ed. 2022, Terraform 1.x. Work Specificity — modules, state management, testing, team workflows each treated as discrete practice. Work Influence — most recommended Terraform book.


**Key principles to apply in specs:**
- **Infrastructure as code** (Ch. 1): Define all infrastructure in version-controlled code. The spec should reference the IaC tool and repository location; no manual console configuration.
- **State management** (Ch. 3): Remote state with locking is the critical complexity. The spec should define the state backend (S3 + DynamoDB locking, Terraform Cloud, etc.) and workspace isolation strategy.
- **Modules as the unit of reuse** (Ch. 4): Modules should be small, composable, and independently versionable. The spec should define the module boundaries — what is a reusable module vs inline resource.
- **Testing infrastructure code** (Ch. 9): Validate with `terraform plan` in CI, policy-as-code (Sentinel/OPA) for guardrails, and integration tests against ephemeral environments. The spec should define which policies are enforced and what integration tests cover.
- **Environment isolation** (Ch. 3, 5): Separate environments via workspaces or directory structure, never via manual configuration drift. The spec should define the environment topology and how it is enforced.
