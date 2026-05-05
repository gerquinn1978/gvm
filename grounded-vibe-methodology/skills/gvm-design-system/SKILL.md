---
name: gvm-design-system
description: Shared design references for all GVM skills. Not invoked directly by users — other skills load its reference files at runtime. Contains the Tufte/Few HTML design spec, expert reference files, shared rules, pipeline contracts, and scoring methodology. For expert scoring and roster management, use /gvm-experts instead.
---

# Design System

Shared design assets, expert reference files, and cross-cutting rules used by all GVM skills. This skill is a passive shared resource — it is loaded by other skills, not invoked directly by users. For expert scoring and roster management, use `/gvm-experts`.

## References

### Design Assets and Shared Contracts

- `references/tufte-html-reference.md` — Core HTML/CSS design spec following Tufte and Few principles. Includes: base CSS, document structure, TOC script, requirement blocks, priority chips, sidenote patterns, table patterns, cross-cutting section patterns, responsive layout. Skill-specific components are in companion files:
  - `references/tufte-review-components.md` — verdict box, score card, issue blocks, criterion rows (loaded only by review skills)
  - `references/tufte-spec-components.md` — ADR and component-detail CSS (loaded only by `/gvm-tech-spec`)
  - `references/tufte-slide-template.md` — self-contained slide deck template (loaded only by `/gvm-doc-write` for presentations)
- `references/pipeline-contracts.md` — Structural contracts between pipeline phases. Defines required sections, ID formats, and structural elements that downstream consumers depend on. Loaded via shared rule 10.

### Expert Reference Files

- `references/architecture-specialists.md` — Tier 1 architecture panel: process, decomposition, cross-cutting decisions, code quality, testing discipline
- `references/domain-specialists.md` — Tier 2a index file listing all available domain specialist files and their activation signals. Do not load this entire file into context — use it to determine which per-domain files to load.
- `references/domain/` — Per-domain specialist files (20 files). Each contains the experts, principles, and activation signals for one domain. Load selectively based on project needs. Available domains: accessibility, data-intensive, data-presentation, diagramming, dimensional-modelling, document-structure, integration-patterns, interaction-design, layout-typography, legacy-code, newsletter, performance, presentation-design, refactoring, resilience-operations, security, service-boundaries, strategy, training, user-documentation.
- `references/stack-specialists.md` — Tier 3 index file listing all available stack specialist files and their activation signals. Do not load this entire file into context — use it to determine which per-stack files to load.
- `references/stack/` — Per-stack specialist files (8 files). Each contains the experts and principles for one technology area. Load selectively based on project tech stack. Available stacks: python, typescript, databases, ai-agents, data-analytics, object-storage, infrastructure, infrastructure-as-code.

### Industry Domain Specialists (Tier 2b)

Industry domain reference files are curated per application domain. Unlike software domain specialists (Tier 2a) which ship with GVM and are relatively stable, these are **append-only** — new experts discovered during projects are added, never removed. They grow as your understanding of the domain deepens across projects.

Available industry domain files:

- `references/industry/market-risk.md` — Market risk measurement, VaR/ES, derivatives pricing, risk factor modeling
- `references/industry/credit-risk.md` — Credit scoring, PD/LGD/EAD, credit portfolio modeling, counterparty credit risk
- `references/industry/model-risk.md` — Model validation, model governance, SR 11-7/SS1/23 compliance
- `references/industry/operational-risk.md` — RCSA, KRI management, loss event collection, operational risk capital

**Activation:** Industry domain files activate during `/gvm-requirements` (domain correctness of requirements), `/gvm-test-cases` (domain-specific edge cases and scenarios), `/gvm-doc-review` (domain accuracy audit), and can be used for ad-hoc domain review at any pipeline phase. They are selected based on the business domain of the application, not the technology stack.

**Adding new domains:** Create a new file in `references/industry/` following the same structure as the existing files. Each file should contain named experts with full citations, activation signals, and key principles. Because the AI has no prior exposure to your specific industry conventions, these files should be **verbose and self-contained** — full descriptions rather than citation shorthand.

## How Other Skills Use This

Any skill that produces HTML output should load the design reference before its first write:

```
Use the Read tool to load `~/.claude/skills/gvm-design-system/references/tufte-html-reference.md` (core) before the first HTML write. Also load the appropriate companion file: `tufte-review-components.md` (review skills), `tufte-spec-components.md` (tech-spec), or `tufte-slide-template.md` (presentations — self-contained, load INSTEAD of the core file).
```

Skills that need industry domain grounding should load the relevant industry file:

```
Use the Read tool to load `~/.claude/skills/gvm-design-system/references/industry/{domain}.md` when the business domain is identified.
```

This ensures all output documents share a consistent visual identity and all domain reasoning is grounded in named authorities.

**When not to ground:** Not every action within a phase needs expert grounding. Inline bug fixes, simple renames, formatting corrections, and routine housekeeping should just be done. Expert grounding is for decisions — architectural choices, design trade-offs, technique selection, quality judgements. The practitioner (or the AI executing a skill) should use judgement about when a task benefits from citing an expert and when it's overhead without value.

## Other Reference Files

- `references/shared-rules.md` — cross-cutting rules loaded by all skills at startup (activation logging, expert discovery, scoring, pipeline contracts, when-not-to-ground)
- `references/expert-scoring.md` — full scoring methodology loaded on demand by `/gvm-experts`
- `references/roster-assembly.md` — parameterised expert roster assembly process used by `/gvm-init` and `/gvm-site-survey`
- `references/review-reference.md` — assessment methodology (Deming, Cronbach, Gilb, Fagan, Stevens & Levi, Marzano) loaded before all review activities
- `references/source-verification.md` — hallucination prevention protocol for verifying external sources, loaded on demand
- `references/stack-tooling.md` — stack-specific tooling commands for dependency verification, linting, credential scanning, static analysis, and mutation testing. Loaded by `/gvm-build` and `/gvm-test`.
