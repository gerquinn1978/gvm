# Stack Specialists — Tier 3 Reference Index

Load individual stack files based on the project's technology. Do not load this entire index into context.

## Stack Constraints

When a project's tech stack is identified (from `specs/cross-cutting.md` or user input), load only the matching stack files. A Python FastAPI project loads `stack/python.md` and `stack/databases.md` — not TypeScript, not object storage.

These constraints are enforced during spec generation. Do not propose stacks that violate them.

- **TypeScript only, never JavaScript.** All frontend and Node.js code must use TypeScript with strict mode enabled. Do not propose JavaScript as an option. When referencing React, Next.js, Express, or any JS ecosystem tool, always specify TypeScript configuration.
- **Preferred languages: Python and TypeScript.** These are the two primary languages. Python for backends, data processing, and agents. TypeScript for frontends, full-stack frameworks (Next.js), and Node.js services. Do not propose other languages unless explicitly requested by the user.

## Stack Files

| File | Technologies | ~Tokens |
|------|-------------|---------|
| `stack/python.md` | Python, FastAPI, Django, Flask, pytest | 1,465 |
| `stack/typescript.md` | TypeScript, React, Next.js, Node.js, Vitest | 1,287 |
| `stack/databases.md` | PostgreSQL, SQLite, Redis, MongoDB, Prisma, SQLAlchemy | 1,724 |
| `stack/ai-agents.md` | Anthropic SDK, OpenAI SDK, LangChain, agent frameworks | 943 |
| `stack/data-analytics.md` | pandas, Spark, dbt, Airflow, data pipelines | 2,118 |
| `stack/object-storage.md` | S3, GCS, Azure Blob, MinIO | 550 |
| `stack/infrastructure.md` | Docker, Kubernetes, CI/CD, monitoring | 544 |
| `stack/infrastructure-as-code.md` | Terraform, Pulumi, CloudFormation | 565 |

## Loading Instructions

Load via: `~/.claude/skills/gvm-design-system/references/stack/{filename}.md`

Match the project's tech stack from `specs/cross-cutting.md` or the detected language/framework. Most projects need 1-3 stack files.

## Adding New Stack Specialists

Create a new file in `stack/` following the structure of existing files. Include: expert name, source work, expert score table, work score table, key principles, and activation signals.

The key requirement: cite authoritative sources that Claude has training data on. Named experts with specific works activate deeper knowledge than generic "best practices."

Template:

```markdown
# [Technology Name]

### [Expert Name] — [Area of Expertise]
**Source:** [Book/resource title], [publisher] ([year])

**Key principles to apply in specs:**
- **[Principle name]** ([reference]): [Description of the principle and how it applies to spec writing]
- ...

**When specifying [technology area]:**
- [Guidance for what the spec should define]
- ...
```
