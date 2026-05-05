# Domain Specialists — Tier 2a Reference Index

Load individual domain files based on what the project needs. Do not load this entire index into context.

## Activation Rules

Tier 2a specialists activate based on signals in the domain being specified. Load only the files whose activation signals match the current project. (Industry-domain specialists are Tier 2b — see `industry/` files.)

## Domain Files

| File | Experts | Activation Signal | ~Tokens |
|------|---------|-------------------|---------|
| `domain/diagramming.md` | Tufte, Fowler, Purchase, Ware | Specs contain diagrams | 2,000 |
| `domain/interaction-design.md` | Cooper, Krug | UI/UX requirements | 600 |
| `domain/data-presentation.md` | Tufte, Few | Data-heavy UI, dashboards, reports | 550 |
| `domain/layout-typography.md` | Muller-Brockmann, Bringhurst | Brochure spec, designed output | 400 |
| `domain/integration-patterns.md` | Hohpe, Woolf | Service integration, message passing | 500 |
| `domain/data-intensive.md` | Kleppmann | Data model spec, storage decisions | 400 |
| `domain/resilience-operations.md` | Nygard | External API dependencies, deployment | 400 |
| `domain/service-boundaries.md` | Newman | Multi-service architecture, API design | 400 |
| `domain/refactoring.md` | Fowler | Code smells, refactoring, enterprise patterns | 300 |
| `domain/legacy-code.md` | Feathers | Legacy codebase, testability, seams | 450 |
| `domain/security.md` | Anderson, Zalewski, Hoffman, OWASP | Auth, input handling, credentials | 1,000 |
| `domain/accessibility.md` | Pickering, W3C WCAG, Deque | Frontend UI, forms, interactive components | 950 |
| `domain/dimensional-modelling.md` | Kimball, Ross | Analytical data models, data warehousing | 500 |
| `domain/user-documentation.md` | Baker, Podmajersky | User docs, help systems, microcopy | 800 |
| `domain/performance.md` | Gregg, Grigorik | Performance requirements, load testing | 750 |
| `domain/document-structure.md` | Minto | Document structure, business writing | 450 |
| `domain/presentation-design.md` | Atkinson, Duarte, Reynolds | Presentations, slide decks, keynotes | 1,250 |
| `domain/strategy.md` | Rumelt, Lafley & Martin, Osterwalder | Strategy documents, competitive analysis | 1,200 |
| `domain/newsletter.md` | Handley | Newsletters, email content, web copy | 450 |
| `domain/training.md` | Clark & Mayer, Dirksen | Training materials, instructional design | 1,000 |

## Loading Instructions

Load individual files using: `~/.claude/skills/gvm-design-system/references/domain/{filename}.md`

For tech-spec Phase 3: load `domain/diagramming.md` (always for specs) + domain files matching the project's requirements domains.
For code-review: load domain files matching the changed code's domain.
For doc-write: load `domain/document-structure.md` (always) + type-specific file (presentation-design, strategy, newsletter, or training).
