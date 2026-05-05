---
name: gvm-doc-write
description: Use when creating or revising documents — presentations, strategy documents, newsletters, training materials, status reports, whitepapers, any prose document, or pipeline documentation (README, CHANGELOG, user guides, API docs). Triggered by /gvm-doc-write command, requests to create documentation, write a presentation, revise a document, or address review findings. Expert-grounded document creation and revision. Has both pipeline and standalone modes.
---

# Document Write

## Overview

Creates and revises documents grounded in named experts. Where the pipeline skills (`/gvm-requirements` → `/gvm-build`) produce software artefacts, `/gvm-doc-write` produces and maintains documents that communicate about, support, or complement the software.

Two modes of operation:
- **Pipeline docs** — invoked after `/gvm-test` to create project documentation (README, CHANGELOG, user guides, API docs) grounded in build artefacts. Output flows to `/gvm-doc-review` for quality gate.
- **Standalone** — invoked at any point to create presentations, strategy documents, newsletters, training materials, status reports, whitepapers, or any prose document. Output is independent of the pipeline.

Within each mode, the skill operates in Create or Revise sub-mode.

This skill handles any prose document that needs expert-grounded quality — whitepapers, origin stories, blog posts, and other written content, not just the typed categories below. The document types table provides structured guidance for common formats; documents outside these types still get writing experts, domain experts, and the full quality process.

**Shared rules:** At the start of this skill, load `~/.claude/skills/gvm-design-system/references/shared-rules.md` and follow all rules throughout execution. Load `~/.claude/skills/gvm-design-system/references/expert-scoring.md` when scoring experts.

**Pipeline position (pipeline docs mode):** `/gvm-requirements` → `/gvm-test-cases` → `/gvm-tech-spec` → `/gvm-design-review (optional)` → `/gvm-build` → `/gvm-code-review` → `/gvm-test` → **`/gvm-doc-write`** → `/gvm-doc-review` → `/gvm-deploy`

In pipeline docs mode, `/gvm-doc-write` sits after `/gvm-test`. The build is verified, and now the project needs documentation that reflects what was actually built and tested — not what was planned.

In standalone mode, `/gvm-doc-write` has no pipeline position — it can be invoked at any point.

## Hard Gates

1. **LOAD EXPERT REFERENCES BEFORE WRITING.** Read `writing-reference.md`, the relevant domain specialist files from `~/.claude/skills/gvm-design-system/references/domain/`, and the appropriate Tufte design file BEFORE writing any document content. Tufte file selection: for **presentations** load `tufte-slide-template.md` (self-contained — do NOT also load `tufte-html-reference.md`); for all other types load `tufte-html-reference.md`. Load `domain/document-structure.md` always. For presentations: additionally load `domain/presentation-design.md`. For strategy: `domain/strategy.md`. For newsletters: `domain/newsletter.md`. For training: `domain/training.md`. For user documentation: `domain/user-documentation.md`. If you start writing without loading experts, the prose quality and structure will be ungrounded.

2. **DETECT MODE CORRECTLY.** If an existing document is provided or referenced, this is Revise mode (the request references an existing document + a fix or improvement). Read the document and the review findings before writing. DO NOT create a new document when the user asked to fix an existing one.

3. **INCREMENTAL WRITING FOR LARGE DOCUMENTS.** If the document will exceed approximately 300 lines of HTML, write it section by section using the Edit tool, not as a single monolithic Write. Verify each section landed correctly before writing the next.

4. **USER APPROVAL OF EXPERT PANEL.** Present the selected experts to the user before writing. The user must know which experts are shaping the document.

5. **HTML BEFORE APPROVAL.** Write HTML for every major section written incrementally. If the user answered Yes in step 5 (ASK ABOUT MD VERSION), also write the matching MD section immediately after each HTML section. If the user answered No or the question was skipped (presentations), write HTML only. Before presenting any section for approval, the HTML for that section must exist. The user reads the HTML to evaluate the document. Exception: presentations are HTML-only (per Key Rule 8) — this gate applies to HTML completeness only; no MD check is performed for presentations.

## Document Types

| Type | Expert Roster | Output Format |
|---|---|---|
| Presentations | `domain/document-structure.md` + `domain/presentation-design.md` + `domain/data-presentation.md` | HTML slides (self-contained slide template from `tufte-slide-template.md`) |
| Strategy | `domain/document-structure.md` + `domain/strategy.md` | HTML + MD (standard Tufte/Few) |
| Newsletters | `domain/document-structure.md` + `domain/newsletter.md` + writing reference | HTML + MD (standard Tufte/Few) |
| Training materials | `domain/document-structure.md` + `domain/training.md` | HTML + MD (standard Tufte/Few) |
| Status reports | Document structure + writing reference | HTML + MD (standard Tufte/Few) |

All types load `domain/document-structure.md` (Minto's Pyramid Principle) as a cross-cutting foundation. All types load the writing reference for prose quality. Specific type experts are loaded from individual domain files in `~/.claude/skills/gvm-design-system/references/domain/` — the roster file determines who participates.

**Model selection by document type (per shared rule 22):**

| Document type | Model | Rationale |
|---|---|---|
| Strategy documents | Primary model | Diagnosis/guiding policy/action coherence requires deep reasoning |
| Whitepapers, origin stories | Primary model | Argument construction and narrative structure need judgement |
| Presentations | Sonnet | Structure predetermined by user; slide content is template-filling |
| Newsletters | Sonnet | Structure and tone are expert-guided but execution is mechanical |
| Training materials | Sonnet | Learning objectives drive structure; content generation is guided |
| Status reports | Sonnet | Situation-complication-resolution is formulaic |
| Pipeline docs (README, CHANGELOG) | Sonnet | Extracting from build artefacts, not creating |

## Expert Sources

All expert definitions live in `~/.claude/skills/gvm-design-system/references/`:

| File | When Loaded |
|---|---|
| `domain/*.md` files | Always load `domain/document-structure.md`. Load type-specific files: `domain/presentation-design.md`, `domain/strategy.md`, `domain/newsletter.md`, `domain/training.md`, `domain/user-documentation.md` as needed. See `domain-specialists.md` index for activation signals. |
| `writing-reference.md` | Always — prose quality (Doumont, Zinsser, Orwell, Williams) |
| `tufte-html-reference.md` | For all non-presentation types (strategy, newsletter, training, status, whitepapers, etc.) |
| `tufte-slide-template.md` | For presentations only (self-contained; do NOT also load `tufte-html-reference.md`) |

No expert names are hardcoded in this skill. The roster files are the single source of truth for which experts exist and their scores.

## Input

### Create mode

- **Explicit type** — "create a presentation about X" or "write a strategy document for Y"
- **Auto-detect from context** — if the user describes what they need, detect the document type from the description
- **No type specified** — ask via AskUserQuestion

### Revise mode

Triggered when the request references an existing document + an issue to fix:
- **With review findings** — "fix the critical issue in the whitepaper review" → read the review findings file, identify the issues, load the experts who found them
- **With explicit issue** — "fix the structure of section 3 in the whitepaper" → read the document, load relevant experts for the problem type
- **With general request** — "improve the whitepaper" → read the document, run a quick expert assessment to identify what needs fixing, then fix

If the document concerns a project with pipeline artefacts (requirements, specs), read those for context. The document should be consistent with the project's established terminology and decisions.

## Branding

Before writing any document, check for a branding file at `branding/branding.md` in the project directory. If it exists, load it with the Read tool.

**Branding file contract:**

The branding file specifies identity elements only. It does not override the design system's body typography, spacing, or layout — those are governed by the Tufte/Few design principles in `tufte-html-reference.md`.

| Element | Branding Controls | Design System Controls |
|---|---|---|
| Logo | Path, placement, size | — |
| Header colours | Background colour, text colour for headers and title slides | — |
| Font stack | Primary font family for headings (body font stays `et-book` or system serif) | Body typography, line-height, measure |
| Accent colour | Links, highlights, emphasis borders | Colour usage principles (data-ink ratio, no decoration) |
| Body text colour | — | Semantic: `#111` for readability |
| Layout | — | Grid, margins, spacing |
| Data visualisation colours | — | Tufte/Few principles govern chart design |

If no branding file exists, use the default design system styling. Never ask the user to create a branding file — it's optional.

## Process — Create Mode

```
0. BOOTSTRAP — per shared rule 14, verify ~/.claude/gvm/ exists before writing output.

1. DETERMINE DOCUMENT TYPE
   ├── From explicit request, or
   ├── From context clues in the user's message, or
   └── Via AskUserQuestion: "What type of document?"
       ├── Presentation (slide deck)
       ├── Strategy document
       ├── Newsletter
       ├── Training material
       ├── Status report
       └── Other (whitepaper, blog post, origin story, etc.)

2. GATHER CONTEXT (via AskUserQuestion)
   ├── Subject/topic of the document
   ├── Audience — who will read/view this? (Minto: the reader's knowledge determines the structure)
   ├── Purpose — what should the reader do or know after? (Doumont: answer "so what?" at every level)
   ├── Scope — how detailed? Key points to cover?
   ├── For presentations: approximate slide count, delivery context (live, async, print)
   └── For strategy: what decision is this informing?

3. LOAD EXPERTS
   ├── Read writing-reference.md (always)
   ├── Read Tufte file: `tufte-slide-template.md` for presentations (self-contained); `tufte-html-reference.md` for all other types
   ├── Read domain/document-structure.md (always)
   ├── Read type-specific domain file(s) if a typed document (e.g., domain/presentation-design.md, domain/strategy.md)
   ├── Assess document content/topic for additional expert needs:
   │   ├── Data presentation? → load domain/data-presentation.md
   │   ├── Diagrams? → load domain/diagramming.md
   │   ├── Security topic? → load domain/security.md
   │   ├── Specific industry domain? → load matching industry file (per shared rule 4)
   │   └── Any domain without expert coverage? → discover experts per shared rule 2
   │       (e.g., a whitepaper on cognitive biases may need Kahneman/Tversky — not in any roster file)
   │       Discovered experts are scored automatically (shared rule 9) and persisted to the
   │       appropriate reference file, making them available to all future skills.
   ├── Read branding/branding.md if it exists
   └── Log all loaded experts to activation CSV (per shared rule 1)

4. STRUCTURE THE DOCUMENT
   ├── Apply pyramid structure: answer first, then supporting evidence
   ├── For presentations: one message per slide, headlines as sentences
   ├── For strategy: diagnosis → guiding policy → coherent actions
   ├── For newsletters: utility × inspiration × empathy; one reader, one message
   ├── For training: identify the gap type; segment into learner-paced units
   ├── For status reports: lead with the headline, then supporting detail
   └── Present the proposed structure to the user via AskUserQuestion for approval

5. ASK ABOUT MD VERSION
   ├── IF document type = Presentation → skip (HTML-only — Key Rule 8)
   └── OTHERWISE → ask via AskUserQuestion: "Would you like a Markdown version alongside the HTML?"
       ├── Yes → write both HTML and MD during document writing (step 6)
       └── No → write HTML only
       Default: No (HTML-only) unless the user explicitly says Yes.

6. WRITE THE DOCUMENT
   ├── Apply type-specific expert principles throughout
   ├── Apply writing reference throughout (Doumont structure, Zinsser economy, Orwell clarity, Williams grace)
   ├── Apply branding if branding file exists
   ├── Write HTML (and MD alongside if user confirmed yes in step 5)
   ├── For presentations: use the slide template from tufte-slide-template.md
   │   ├── One idea per slide
   │   ├── Headlines are sentences, not topic labels
   │   ├── Data slides include a clear "so what?" (Tufte/Few for data visualisation)
   │   ├── Visual restraint — signal-to-noise ratio, no decoration
   │   └── Full-bleed images as CSS background where appropriate
   ├── For strategy: kernel structure (diagnosis, guiding policy, coherent actions)
   │   ├── Five cascading choices if operationalising
   │   └── Identify the crux explicitly
   ├── For newsletters: conversational, specific, reader-centric
   ├── For training: multimedia + contiguity + coherence + segmenting principles
   │   ├── Practice activities, not just information
   │   ├── Job aids where reference is more appropriate than memorisation
   │   └── Assessment aligned with learning objectives
   └── For status reports: situation-complication-resolution; highlight risks and decisions needed

7. REVIEW AGAINST EXPERTS (perform on draft content before writing to disk)
   ├── Self-review the draft against loaded expert principles
   ├── Fix any violations found (per shared rule 3: experts who find should fix)
   ├── Factual claims check:
   │   ├── Identify every factual claim in the document (statistics, dates, attributions, named results)
   │   ├── For each claim: can you verify it from the loaded source material or project artefacts?
   │   ├── If YES → keep it
   │   ├── If UNCERTAIN → flag it to the user: "I stated X but cannot verify it — please confirm"
   │   └── If NO source → remove the claim or replace with what you can verify
   │       (Orwell: never say more than you know to be true)
   └── Iterate until clean (max 3 passes)
   After review is clean, proceed to step 8 (WRITE OUTPUT).

8. WRITE OUTPUT
   ├── Presentations: write to {type}/{filename}.html (HTML-only always)
   ├── Other types: write HTML to {type}/{filename}.html
   │   └── If MD confirmed in step 5: also write {type}/{filename}.md
   ├── Scan for existing files — increment if name collision
   ├── Log cited experts to activation CSV
   └── Present the document to the user
   **HTML generation:** For each section or document written, dispatch the HTML generation as a Haiku subagent (`model: haiku`) immediately after writing that section's MD. Do not wait for the full document to be complete. For non-presentation types the subagent receives the CSS/document shell from `tufte-html-reference.md`. For presentations the subagent receives the self-contained shell from `tufte-slide-template.md` instead (and presentations are HTML-only — no MD step, so this dispatch does not fire for them). Per shared rule 22.

9. OFFER NEXT STEPS (via AskUserQuestion)
   ├── "Review and revise" — iterate on specific sections
   ├── "Create another document" — back to step 1
   ├── "Run /gvm-doc-review on this document" — quality gate (recommended for substantial documents)
   └── "Done" — session ends
```

## Process — Revise Mode

```
0. BOOTSTRAP — per shared rule 14, verify ~/.claude/gvm/ exists before writing output.

1. READ THE DOCUMENT
   ├── Read the existing document in full
   └── Identify the document type and subject matter from its content

2. IDENTIFY THE ISSUES
   ├── If review findings file provided → read it, extract findings with severity and source expert
   ├── If explicit issue described → note it
   ├── If general "improve" request → run a quick assessment:
   │   ├── Structure (Doumont: does every section answer "so what?")
   │   ├── Prose quality (Zinsser: clutter; Orwell: dying metaphors; Williams: nominalisations)
   │   ├── Argument (McKee: progressive complication; does the conclusion match the buildup?)
   │   └── Present identified issues to user via AskUserQuestion for confirmation
   └── Prioritise: critical → important → minor (address in order)

3. LOAD EXPERTS
   ├── Read writing-reference.md (always — prose quality applies to every revision)
   ├── Read the appropriate Tufte file (if the document contains visual elements or will be HTML): for presentations load `tufte-slide-template.md` (self-contained — do NOT also load `tufte-html-reference.md`); for all other types load `tufte-html-reference.md`
   ├── Load the experts who found the issues (per shared rule 3):
   │   ├── Review finding says "Weinberg" → load Weinberg's principles
   │   ├── Review finding says "Orwell" → load Orwell from writing-reference.md
   │   ├── Review finding says "Tufte" → load Tufte from domain/data-presentation.md or domain/diagramming.md
   │   └── The diagnosing expert defines what "right" looks like, not just what's wrong
   ├── Assess document content for additional expert needs:
   │   ├── Contains data/charts? → load domain/data-presentation.md
   │   ├── Contains diagrams? → load domain/diagramming.md
   │   ├── Covers a specific industry? → load matching industry file (per shared rule 4)
   │   ├── Contains security claims? → load domain/security.md
   │   ├── Contains narrative/argument structure? → load McKee from writing-reference.md
   │   └── Domain without expert coverage? → discover experts per shared rule 2
   │       Discovered experts are scored (shared rule 9) and persisted to the roster.
   └── Log all loaded experts to activation CSV (per shared rule 1)

4. FIX THE ISSUES
   ├── Work through issues in priority order (critical first)
   ├── For each issue:
   │   ├── Apply the finding expert's framework to determine the fix
   │   ├── Apply writing experts to ensure the fix maintains prose quality
   │   ├── Edit the document directly (this is revision, not rewrite — preserve what works)
   │   └── Note what was changed and why
   ├── Do NOT rewrite sections that aren't broken (King: kill your darlings, but only YOUR darlings)
   └── Do NOT add features, structure, or content beyond what the findings require

5. SELF-REVIEW
   ├── Re-read changed sections against the expert principles that motivated the fix
   ├── Check that fixes didn't introduce new problems (Zinsser: rewriting is writing)
   ├── Verify the document still coheres after the changes (Brooks: conceptual integrity)
   ├── Factual claims check on changed sections:
   │   ├── Any new factual claims introduced by the fix? Verify against source material.
   │   ├── UNCERTAIN claims → flag to user rather than assert
   │   └── (Orwell: never say more than you know to be true)
   └── Iterate if needed (max 2 passes — revision should be targeted, not endless)

6. PRESENT CHANGES
   ├── Summarise what was changed and which expert principles guided each fix
   ├── For each finding addressed: finding → expert framework applied → what changed
   ├── Termination: once every finding from the step 2 list has been addressed, the
   │   "Continue with remaining findings" option is REMOVED from the offer. Do not
   │   loop back to re-assess the full document after all step-2 findings are resolved.
   └── Offer next steps via AskUserQuestion:
       ├── "Continue with remaining findings" — return to step 4 with the NEXT unresolved finding (offer this only while the step-2 list has unresolved items)
       ├── "Run /gvm-doc-review on the updated document" — verify the fixes
       └── "Done" — session ends
```

## Process — Pipeline Docs Mode

Triggered when invoked after `/gvm-test` in the pipeline, or when the user explicitly requests pipeline documentation and build artefacts exist.

```
0. BOOTSTRAP — per shared rule 14, verify ~/.claude/gvm/ exists before writing output.

1. DETECT PIPELINE CONTEXT
   ├── Check for build artefacts: build/handovers/, specs/, build/build-summary.md
   ├── Check for test report: test/test-{NNN}.md
   ├── Check for requirements: requirements/requirements.md
   ├── If none exist → fall back to standalone Create mode
   └── If artefacts exist → proceed in pipeline docs mode

2. DETERMINE WHAT TO DOCUMENT (via AskUserQuestion)
   ├── Read build/build-summary.md (if exists) for scope of what was built
   ├── Read the latest test/test-{NNN}.md for verification status
   ├── Read requirements/requirements.md for user-visible features
   ├── Read specs/cross-cutting.md for tech stack and conventions
   ├── Present a checklist:
   │   ├── README.md — setup instructions, features, architecture overview
   │   ├── CHANGELOG.md — user-visible changes (pre-checked if requirements-002.md+ exists)
   │   ├── User guide — if requirements specify user documentation
   │   └── API docs — if the build includes API endpoints
   └── User selects which to create

3. LOAD EXPERTS
   ├── Read writing-reference.md (always — per shared rule 5)
   ├── Read tufte-html-reference.md (always — per shared rule 5)
   ├── Read domain/user-documentation.md (if user guide selected)
   ├── Read branding/branding.md if it exists
   └── Log all loaded experts to activation CSV (per shared rule 1)

4. WRITE EACH DOCUMENT
   ├── For each selected document type:
   │   ├── Draft content grounded in build artefacts, specs, and test results
   │   ├── README: project name, description, features (from requirements),
   │   │   setup (from specs/cross-cutting), architecture overview,
   │   │   known limitations (from test report)
   │   ├── CHANGELOG: user-visible changes described from the user's perspective
   │   ├── User guide: task-oriented, matches implemented behaviour (not planned)
   │   ├── API docs: endpoints, request/response shapes, authentication
   │   ├── Apply writing-reference.md principles throughout
   │   └── Self-review against expert principles (max 2 passes)
   ├── README.md and CHANGELOG.md are MD-only (standard convention)
   ├── User guide and API docs follow shared rule 13 (paired HTML + MD in docs/)
   └── Present each document to user for approval before proceeding to next

5. HANDOFF
   ├── Present summary of created documents
   └── Recommend: "Run /gvm-doc-review to verify documentation quality"
```

## Type-Specific Guidance

### Presentations

**Output format:** Self-contained HTML using the slide template from `tufte-slide-template.md`. The template provides:

- CSS-based slide separation (`section.slide` elements)
- Page breaks for print (`@media print`)
- Keyboard navigation (arrow keys, spacebar)
- Slide counter
- Presenter notes (hidden by default, toggled with 'N' key)

**Structure principles:**

The presentation experts define complementary aspects of a good deck:

- **Content structure** — story-first, three-act structure, one idea per slide, headlines as sentences (presentation content structure specialists from roster)
- **Narrative arc** — sparkline between "what is" and "what could be," audience as hero, contrast creates meaning (presentation narrative specialists from roster)
- **Visual design** — simplicity, signal-to-noise ratio, full-bleed images, restraint over decoration (presentation visual specialists from roster)
- **Data slides** — data-ink ratio, small multiples, tables for precision, charts for trends (data presentation specialists from roster)
- **Document structure** — lead with the answer, pyramid structure, MECE grouping (document structure specialists from roster)

**Slide count guidance:**

| Context | Slides per Minute | Example |
|---|---|---|
| Live keynote | 1-2 slides/min | 20 min talk ≈ 20-40 slides |
| Technical walkthrough | 0.5-1 slide/min | 30 min demo ≈ 15-30 slides |
| Async/read-ahead | N/A — reader-paced | As many as needed, one idea each |
| Executive briefing | 1 slide/2-3 min | 15 min slot ≈ 5-8 slides |

### Strategy Documents

**Structure follows the kernel:**

1. **Diagnosis** — what is going on? What is the critical challenge (the crux)?
2. **Guiding policy** — the approach to dealing with the challenge. Not goals — an actual approach.
3. **Coherent actions** — coordinated, mutually reinforcing steps that implement the policy.

If the strategy needs operationalisation, layer in the five cascading choices: winning aspiration → where to play → how to win → capabilities required → management systems.

**Bad strategy checks** — review for: fluff (buzzwords), failure to face the challenge, goals masquerading as strategy, incoherent actions pulling in different directions. Flag these explicitly.

### Newsletters

**Structure principles:**

- Open with a hook that earns the next sentence
- One core message per newsletter — don't try to cover everything
- Utility: the reader should be able to do something with this information
- Specific over generic — concrete examples, real numbers, named things
- Close with a clear call to action or takeaway
- Keep it scannable: short paragraphs, subheadings, bold key phrases

### Training Materials

**Structure principles:**

- Start with the learning objectives — what will the learner be able to do?
- Identify the gap type: knowledge, skill, motivation, or environment. Training only fixes the first two.
- Segment into modules — each module covers one objective
- Each module: concept → example → practice → assessment
- Apply multimedia principles: words + relevant images, spatial contiguity, no extraneous content
- Include practice activities — not just information. The learner must do something with the knowledge.
- Provide job aids where reference is better than memorisation (checklists, quick-reference cards)

### Status Reports

**Structure principles:**

- Lead with the headline: what is the most important thing the reader needs to know?
- Situation-complication-resolution for the overall status
- Traffic light (red/amber/green) for at-a-glance status where appropriate
- Risks and decisions needed — prominently positioned, not buried
- Progress against milestones — specific, countable (Marzano: count rather than judge)
- Next steps with owners and dates

## Output Locations

| Type | Directory | File Pattern |
|---|---|---|
| Presentations | `presentations/` | `{name}.html` |
| Strategy | `strategy/` | `{name}.html` (+ `{name}.md` if requested) |
| Newsletters | `newsletters/` | `{name}.html` (+ `{name}.md` if requested) |
| Training | `training/` | `{name}.html` (+ `{name}.md` if requested) |
| Status reports | `status-reports/` | `{name}.html` (+ `{name}.md` if requested) |
| Other documents | project root or appropriate subdirectory | `{name}.html` (+ `{name}.md` if requested) |

Scan for existing files and increment to avoid overwriting. In revise mode, edit the existing file in place — do not create a new copy.

## Key Rules

1. **Expert grounding is the value** — every document operation has named experts whose principles guide the output. This is what distinguishes `/gvm-doc-write` from "just write me a document" or "just fix this."
2. **Writing reference always loaded** — Doumont for structure, Zinsser for economy, Orwell for clarity, Williams for grace. These experts apply to all prose in both create and revise modes.
3. **Content drives expert loading** — read the document (or seed content) and load experts relevant to its subject matter. A whitepaper about financial risk loads the market-risk experts. A document with charts loads Tufte and Few. Don't limit expert loading to the writing experts alone.
4. **Experts who find should fix** — in revise mode, the expert who identified a problem defines what "right" looks like (shared rule 3). If Weinberg found the issue, Weinberg's framework guides the fix. If Orwell found it, Orwell's rules apply. Load those specific experts.
5. **Revise means edit, not rewrite** — preserve what works. Change only what the findings require. Do not restructure sections that aren't broken, add new content unprompted, or "improve" prose the experts didn't flag (King: kill your darlings, but only your darlings).
6. **Structure before writing** (create mode) — propose and get approval on the document structure before writing content. The structure determines the quality more than the prose.
7. **Branding is identity, not design** — the branding file controls logo, header colours, and heading font. The design system controls body typography, layout, spacing, and data visualisation.
8. **Presentations are HTML-only** — no MD pair. The slide format does not have a meaningful plain-text representation.
9. **MD pair is optional for non-pipeline documents** — shared rule 13 mandates paired HTML + MD for pipeline artefacts (requirements, specs, test cases) because downstream skills consume the MD. Documents produced by `/gvm-doc-write` are not pipeline artefacts — nothing consumes the MD programmatically. Ask the user via AskUserQuestion whether they want an MD version alongside the HTML. Default to HTML-only unless they say yes. Exception: in pipeline docs mode, documents in `docs/` (user guides, API docs) follow shared rule 13 and produce paired HTML + MD. README.md and CHANGELOG.md are MD-only (standard convention).
10. **One idea per slide** — for presentations, this is non-negotiable. If a slide has two ideas, it's two slides.
11. **Pipeline docs mode is a pipeline step; standalone mode is not** — in pipeline docs mode, `/gvm-doc-write` sits between `/gvm-test` and `/gvm-doc-review` and produces project documentation grounded in build artefacts. In standalone mode, documents do not flow through the pipeline.
12. **Expert discovery for uncovered domains** — per shared rule 2. If the document covers a domain with no matching expert, flag it.
13. **Audience determines structure** — Minto: the reader's existing knowledge determines whether to use deductive (answer first) or inductive (evidence first) ordering. Ask about the audience.
14. **Any document type** — the typed categories (presentations, strategy, etc.) provide structured guidance for common formats. But this skill handles any prose document — whitepapers, blog posts, origin stories, READMEs, proposals. Documents outside the typed categories still get the full expert treatment.
15. **Revise mode is the designated consumer of `/gvm-doc-review` findings.** When `/gvm-doc-review` identifies issues, `/gvm-doc-write` Revise mode applies the fixes — not a re-run of doc-review.
