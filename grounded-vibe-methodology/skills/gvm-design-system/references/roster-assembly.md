# Expert Roster Assembly Process

A parameterised process for assembling the expert roster for a project. Used by both `/gvm-init` (greenfield, user-declared domain) and `/gvm-site-survey` (existing codebase, diagnosed domain). Other skills invoke parts of this process via shared rules (expert discovery, automatic scoring) but do not run the full assembly.

## Inputs

The calling skill provides:

| Input | From /gvm-init | From /gvm-site-survey |
|---|---|---|
| **Business domain** | User declares via AskUserQuestion | Diagnosed from codebase (config, domain models, naming) |
| **Tech stack** | Not available (deferred to /gvm-tech-spec) | Identified from package files, frameworks, dependencies |
| **Codebase state** | N/A (greenfield) | Scenario classification (Coherent → Incoherent) |
| **Software patterns** | N/A | Identified from code structure (data-intensive, event-driven, etc.) |

## Steps

### Step 1 — Tier 2b: Industry Domain Specialists

1. Scan `~/.claude/skills/gvm-design-system/references/industry/` for files matching the business domain.
2. If matches found, list them and ask the user (via AskUserQuestion) to confirm which to activate. Multiple files may apply.
3. If no matches found but the domain is identifiable, offer to run the **Expert Discovery and Persistence Process** (shared rule 2) with the business domain as input.
4. If "General-purpose software" or no identifiable domain, confirm no industry domain is needed and move on.

### Step 2 — Tier 1: Process Experts

1. Load `~/.claude/skills/gvm-design-system/references/architecture-specialists.md`.
2. **If called from site-survey:** select experts based on the diagnosed scenario — match the codebase state to the experts' roles and activation signals in the reference file. Different scenarios emphasise different experts (refactoring for Fractured, migration patterns for Mid-migration, etc.).
3. **If called from init:** use the defaults for the common case. Only surface a follow-up question about adjusting Tier 1 experts if the domain is specialised (safety-critical, regulated) and the defaults may not be appropriate. For most domains, skip this step.

### Step 3 — Tier 2a: Software Domain Specialists

1. Load `~/.claude/skills/gvm-design-system/references/domain-specialists.md`.
2. **If called from site-survey:** match the codebase's software patterns to specialists (data-intensive → Kleppmann, service boundaries → Newman, legacy code → Feathers, etc.).
3. **If called from init:** skip — software domain specialists activate conditionally during downstream pipeline phases based on what emerges in requirements and tech spec.

### Step 4 — Tier 3: Stack Specialists

1. Load `~/.claude/skills/gvm-design-system/references/stack-specialists.md` (index file). Read the stack constraints and the stack files table.
2. **If called from site-survey:** match the identified tech stack to the stack files table, then load only the matching per-stack files from `~/.claude/skills/gvm-design-system/references/stack/`.
3. **If called from init:** skip — stack is unknown before requirements. Stack specialists activate during `/gvm-tech-spec` when the stack is chosen.

### Step 5 — Expert Discovery (mandatory)

Run the **Expert Discovery and Persistence Process** (shared rule 2) with all identified domains, technologies, and patterns as input. Assess coverage against the loaded reference files, identify gaps, research candidate experts, present them to the user with scores and evidence, persist approved experts.

**If called from init:** the input is narrower (business domain only). Discovery may find fewer gaps because stack and software domain are not yet known.

**If called from site-survey:** the input is comprehensive (every technology, pattern, framework, and business domain from Phases 1–2). Discovery is mandatory, not conditional.

### Step 6 — Score Unscored Experts

Per shared rule 9: score automatically, do not ask permission. Scan all loaded reference files for experts without scores. Run the standard scoring process with independent verification. Persist scores.

### Step 7 — Present Roster

Present the assembled roster to the user. Show:
- Which existing experts from reference files are relevant and why
- Any gaps where no existing expert covers an identified area
- Any newly discovered experts with their scores and verification results
- The user may add, remove, or adjust experts

### Step 8 — Write to Report

Write the roster to the calling skill's output document (init report or site-survey report). The roster summary table should contain: expert name, work, tier, classification, reference file, status (existing / newly added / newly scored).

## What the Calling Skill Still Owns

This process handles roster assembly. The calling skill owns:

- **gvm-init:** the business domain question (Step 1 input), the pre-check for prior initialisation, the calibration report structure, the activation log initialisation
- **gvm-site-survey:** the reconnaissance (Phases 1–2), the architectural mapping (Phase 3), the diagnosis (Phase 3), the route recommendation (Phase 5), the survey report structure, the existing documentation detection (Phase 1.6)
