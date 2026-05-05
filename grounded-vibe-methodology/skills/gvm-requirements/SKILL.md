---
name: gvm-requirements
description: Use when gathering, refining, or fleshing out requirements for a new project or feature. Triggered by /gvm-requirements command, rough project descriptions needing structure, or requests to create a requirements document.
---

# Requirements Gathering

## Overview

A structured, expert-driven requirements elicitation skill. Takes rough input (or starts from scratch) and produces a complete, implementation-agnostic requirements document through adaptive conversation. Outputs paired HTML (Tufte/Few design) and Claude-friendly Markdown files, always in sync.

**This skill produces requirements only.** It does not make architecture, implementation, or decomposition decisions. Those belong to downstream commands (`/gvm-test-cases`, `/gvm-tech-spec`, `/gvm-build`).

**Shared rules:** At the start of this skill, load `~/.claude/skills/gvm-design-system/references/shared-rules.md` and follow all rules throughout execution. Load `~/.claude/skills/gvm-design-system/references/expert-scoring.md` when scoring experts.

## Hard Gates

1. **LOAD SHARED RULES AND EXPERT REFERENCES AT SESSION START.** Read `shared-rules.md` and `~/.claude/skills/gvm-requirements/references/elicitation-techniques.md` BEFORE starting elicitation. If you begin asking the user questions without loading expert references, your questions are ungrounded.

2. **WRITE MD THEN HTML BEFORE APPROVAL.** Write the MD content first, then immediately write the HTML for the same content. Both files must exist before any approval checkpoint (shared rule 13). DO NOT batch all MD writes before all HTML writes.

3. **ONE QUESTION AT A TIME in free-text conversation.** DO NOT dump a list of 10 questions. When using AskUserQuestion for structured decisions with known options, up to 4 questions per call is acceptable (per Phase 2). But in open-ended exploration, ask one question per message.

4. **USER APPROVAL PER DOMAIN.** Each domain section must be presented to the user for confirmation before moving to the next domain. DO NOT batch-write all domains without approval checkpoints.

## Change Detection

Before starting the elicitation flow, check for existing requirements to determine the change mode.

**Promotion of surfaced requirements (shared rule 27).** When invoked to promote a surfaced requirement from a build handover, code review, doc review, or design review, this skill is the destination — `STUBS.md` is never the destination for a requirement gap. The promotion uses one of the three modes below (append as acceptance criterion / new requirement entry / new round) per the calling skill's `AskUserQuestion` triage.

### Detection logic

1. **Check if `requirements/requirements.md` exists.** If not, proceed with normal flow (Phase 1 onward).

2. **If requirements exist, check pipeline completeness** using Bash:
   - Does `test-cases/test-cases.md` exist?
   - Does `specs/implementation-guide.md` exist?
   - Does `build/handovers/` contain files?

3. **Determine change mode:**

   **Pipeline incomplete** (requirements exist but downstream artefacts are missing or partial):
   - Default to **append mode**. Tell the user: "Requirements exist and the pipeline is still in progress. I'll append new requirements to the existing document."
   - Hard Gates 1 (load references), 2 (MD before HTML before approval), and 4 (user approval per domain) apply unconditionally on this path. Hard Gate 3 (one question at a time) applies when eliciting new domain content.
   - Use Edit (not Write) to add to the existing `requirements.md`.
   - New requirement IDs continue the existing sequence (if last ID was RE-7, next is RE-8).
   - Add a Changelog entry for each domain section added (per shared rule 11).

   **Pipeline complete** (build handovers exist or user confirms the pipeline has completed):
   - Ask via AskUserQuestion:
     - **"New round"** — new feature or epic. Creates `requirements-002.md` (or next number). Requirement IDs use round prefix (`R2-{DOMAIN}-{N}`). Previous documents are immutable. Include a "Relationship to Previous Rounds" section. All Hard Gates (1--4) apply -- this path runs the full flow on a new file.
     - **"Update existing"** — decision reversal, platform change, component swap. Edits `requirements.md` in place with changelog entries. Removed requirements are marked `**[REMOVED]**` with rationale, not deleted. Address each requested change and present the updated section to the user for confirmation via AskUserQuestion.

       Hard Gates 1, 2, and 4 apply unconditionally on this path. Hard Gate 3 (one question at a time in free-text conversation) applies whenever the update requires asking the user open-ended questions — including per-domain confirmation of changed sections.

       **SYNC GATE:** Before proceeding to Phase 5, regenerate `requirements/requirements.html` from the updated `requirements.md`. Both files must be in sync. If the HTML regeneration produces content that does not match the MD, stop and report the sync failure to the user with the specific section that diverged. Then present via AskUserQuestion: "Re-generate HTML for the diverging section" or "Manually review and accept the divergence." On re-generation, re-write only the diverging section and re-run the sync check for that section. On manual acceptance, record the accepted divergence in the document's changelog entry and proceed. Do not proceed to Phase 5 without one of these resolutions.

       After the user confirms changes are complete (via AskUserQuestion), proceed to Phase 5. The transition requires explicit user confirmation — do not auto-advance.

       After completing the update, notify the user: "Downstream artefacts may be stale. Run `/gvm-status` to check." Then proceed to Phase 5 (Finalize) to confirm MoSCoW priorities and regenerate the requirements index. Do not re-run Phases 1–3 for sections that were not changed.

## Expert Panel

All expert definitions live in the reference file, not in this skill file. Use the Read tool to load `~/.claude/skills/gvm-requirements/references/elicitation-techniques.md` at the start of the session. The reference file defines the always-active experts (with roles: classification, questioning, journey mapping, personas, job framing) and conditionally-activated experts (with activation signals). Follow the roles and techniques defined there.

Announce activations transparently when they occur.
Log all loaded experts to activation CSV (per shared rule 1).

**Industry domain specialists (Tier 2b):**

At the start of the requirements session, check whether the application's business domain has an industry domain reference file in `~/.claude/skills/gvm-design-system/references/industry/`. If a matching file exists, load it with the Read tool. These experts ground requirements in the authoritative frameworks of the application's industry — ensuring domain correctness, appropriate terminology, and coverage of domain-specific concerns (regulatory, methodological, or otherwise). If no file exists but the domain is identifiable, flag it to the user: "No industry domain reference file found for [domain]. Would you like me to identify authoritative experts for this domain?"

**Component-level domain specialists:**

As requirements elicitation reveals distinct sub-domains within the project (e.g., a relocation platform has property valuation, school catchment, and local authority components), check whether each sub-domain has a matching industry domain file. If not, offer to scaffold a component-level reference file by running the **Expert Discovery and Persistence Process** with that sub-domain as input. Component-level files have narrower activation signals scoped to their specific area of the application.

## Process Flow

```
0. BOOTSTRAP — per shared rule 14, verify ~/.claude/gvm/ exists and is initialized before writing any output

1. SEED CHECK
   ├── Seed provided → Analyze seed: identify gaps, ambiguities, domain signals
   └── No seed → Discovery questions (Gause & Weinberg context-free)
       Both paths → Activate expert lenses, announce to user

2. ELICIT (per domain, one question at a time)
   ├── Domain sufficiently explored?
   │   ├── No → continue eliciting
   │   └── Yes → write section to HTML + MD, present for confirmation
   └── User confirms section?
       ├── Yes → next domain (if more) or Phase 4
       ├── Minor changes → revise section → re-confirm
       ├── Rethink domain → discard this domain section only and re-elicit from the beginning of this domain
       └── Start over / major rework → discard all sections written so far and restart from Phase 1 step 1

3. SAFETY NET AUDIT (elicitation-checklist.md)
   ├── Gaps found → probe uncovered areas → re-audit
   └── No gaps → proceed

4. SOURCE VERIFICATION (external document seeds only)
   ├── External seed? No → skip to Phase 5
   └── External seed? Yes → run source verification (independent agent)
       ├── Verification issues → resolve with user, update requirements
       │   ├── Substantial changes → re-verify
       │   └── Resolved → proceed to Phase 5
       └── No issues → proceed to Phase 5

5. FINALIZE
   ├── Confirm MoSCoW priorities
   ├── Generate requirements index
   ├── Write priority model & executive summary
   ├── Application naming (name / brainstorm / skip)
   ├── Final HTML ↔ MD sync check
   └── Present complete document for approval
```

## Phase Details

### Phase 0 — Bootstrap & RA-1 prerequisite

This phase runs before any elicitation. Two checks gate entry:

1. **GVM home bootstrap** — per shared rule 14, verify `~/.claude/gvm/` exists and is initialised before writing any output. Run the bootstrap check even if you believe another skill ran first.

2. **RA-1 risk-assessment prerequisite (discovery ADR-306).** Before Phase 1 begins, the project root must contain a well-formed `risks/risk-assessment.md`. Invoke `_risk_validator.full_check` from `gvm-design-system/scripts/_risk_validator.py`:

   ```python
   from _risk_validator import full_check
   from datetime import date
   risk_assessment, errors = full_check("risks/risk-assessment.md", today=date.today())
   ```

   If `errors` is non-empty (file missing, sections out of order, sections empty, etc.), refuse to proceed with elicitation. Present the errors to the practitioner via AskUserQuestion with these options:

   - **"Create `risks/risk-assessment.md` now (template)"** — emit a four-section template with the headers `## Value Risk`, `## Usability Risk`, `## Feasibility Risk`, `## Viability Risk` (in that exact order), each populated with `[TODO: write the prose evaluation here. End with `questioner: <name>`]` placeholders, plus the `---\nschema_version: 1\n---` frontmatter. Tell the practitioner to fill in the prose, then re-run `/gvm-requirements`.
   - **"Pause — I'll create it manually, then re-run /gvm-requirements"** — exit cleanly without writing requirements files. The practitioner returns when ready.
   - **"Continue without risk assessment (NOT RECOMMENDED — disables RA-3 finalisation gate)"** — the skill proceeds to Phase 1 but the Phase 5 RA-3 gate is also skipped. Use only when the project legitimately has no risk surface (e.g. internal scratch tools); otherwise the discipline is being bypassed.

   The default route is the first option. Do not advance to Phase 1 until the practitioner has chosen explicitly.

### Phase 1 — Seed Analysis or Discovery

**Model selection (per shared rule 22):** Greenfield elicitation (no seed document) uses the primary model — open-ended discovery requires deep reasoning. Seed-based elicitation (existing document provided) uses `model: sonnet` — clarifying and extracting from an existing document is guided work, not discovery.

**Auto-detect Application Brief:** Before asking for a seed, check if `init/brief-*.md` exists. If found, read the most recent brief and tell the user: "Found Application Brief — using it as a seed for requirements elicitation." Then ask via AskUserQuestion: "Do you have any additional seed documents to include alongside the brief?" Options: "No, proceed with the brief only" / "Yes, I have additional documents." If yes, the user provides paths to additional files (existing requirements, notes, competitor analysis, meeting notes — any format). All seed documents including the brief are loaded together.

The brief's Problem Statement starts domain elicitation, the Solution Shape constrains high-level scope, the Constraints become requirements constraints, and the Stakeholders & Users seed persona identification. Additional seed documents are analysed for requirements content alongside the brief.

**If seed provided (including brief and/or additional documents):** Read all inputs. Seeds can be anything from a one-line idea to an existing requirements document from another tool or process, an Application Brief from `/gvm-init`, or multiple documents combined. If the seed is too brief to extract any draft requirements (e.g., just a topic name), treat it as a topic hint and proceed with discovery questions. Otherwise, identify:
- What's already clear (extract as draft requirements)
- What's ambiguous (flag for probing)
- What's missing (map against expert coverage areas)
- Domain signals for expert activation

**External documents as seed:** If the user provides an existing requirements document (any format — Word, PDF, Confluence export, plain text, spreadsheet), read it and treat the entire content as a rich seed. Extract what can be mapped to GVM requirement structure, flag what needs clarification, and identify gaps against the expert coverage areas. The goal is to produce a GVM-quality requirements document through the normal elicitation flow, not to accept the external document as-is. Ask the user via AskUserQuestion: "I've extracted N draft requirements from your document. Should I proceed with the elicitation flow to refine and complete them, or would you prefer to review the extracted drafts first?"

**If no seed:** Use context-free questions from the questioning expert in the loaded panel:
- "What problem are you trying to solve?"
- "Who is this for?"
- "What would a highly successful solution look like?"
- "What environment will this operate in?"

In both cases, establish early:
- The job statement from the job framing expert: "When [situation], I want to [motivation], so I can [outcome]"
- A lightweight persona from the persona expert: name, role, primary goal, context

### Phase 2 — Seed-and-Branch Elicitation

Ask questions **one at a time**. Branch from what's known into what's unknown.

**Question strategy:**
- **Use AskUserQuestion for all structured decisions** — whenever the question has known options (multiple choice, yes/no, approve/revise, priority selection), present it via the AskUserQuestion tool instead of free-text conversation. This gives the user a clean submit-based UI. Present one question at a time or batch related questions (up to 4 per call).
- For open-ended exploration (e.g., "tell me about a typical use"), use normal conversation — AskUserQuestion is for decisions with discrete options.
- Use the workflow discovery technique from the panel to surface workflows
- Use the questioning expert's probes when language is vague
- Use the job framing expert's "tell me about the last time" technique for context
- Apply the classification expert's taxonomy as requirements emerge (business / user / functional)

**Adaptive depth:** Start at Level 1 (core). When signals appear, announce the escalation and probe deeper using the conditional expert's categories. The reference file defines when each expert and technique activates.

If the user says "that's not relevant" or "keep it simple" — respect it, note in Assumptions, move on.

**Cross-cutting items:** Log assumptions, open questions, and out-of-scope items as they surface — don't batch them for later.

**Mid-flight Impact-Map Edits (IM-5, discovery ADR-305).** When the practitioner's free-text input matches a mid-flight intent, pause the current elicitation turn and route through `_im5_handler`. The flow is:

1. Call `_im5_handler.classify_intent(user_text)`. A return of `None` means no mid-flight intent — continue elicitation as normal. A non-None `Intent` carries an `action` of `"add_impact"`, `"add_actor"`, or `"add_deliverable"`.
2. Confirm via `AskUserQuestion` (e.g. "Add Impact I-X (Actor A-N: <behavioural change>) to the impact-map now?"). The classifier is liberal by design — the confirmation step is what catches false positives.
3. On confirmation, call the matching `_im5_handler.append_impact` / `append_actor` / `append_deliverable`. The function performs an atomic write via `.tmp` + re-load validation + `os.replace`; it never raises. The return value is `AppendResult(success: bool, error: str | None)`.
4. **Success path** — announce the append (it has already added a Changelog entry to `impact-map.md`), then resume the previous elicitation turn ("OK, you were saying about RE-N's acceptance criteria...").
5. **Failure path** — report `result.error` verbatim. Tell the practitioner that `impact-map.md` is unchanged and they **do not reference** the would-be Impact/Actor/Deliverable ID in any subsequent requirement (the would-be ID was never written). Resume the previous elicitation turn. Phase 5's IM-4 gate will catch any references to unwritten IDs at finalisation.

The atomic-write pattern means a crash mid-append cannot corrupt `impact-map.md`. The in-memory elicitation state must NOT be updated on the failure path — the practitioner is the source of truth for what they referenced.

### Phase 3 — Incremental Writing

After each domain is sufficiently explored:

1. Create document scaffold on first write (both HTML and MD with skeleton structure)
2. Use the Read tool to load both `~/.claude/skills/gvm-design-system/references/tufte-html-reference.md` and `~/.claude/skills/gvm-design-system/references/writing-reference.md` before the first write (only needed once each — the patterns stay in context).
3. Write the matching MD section first (per shared rule 13 and Hard Gate 2: MD before HTML)
4. Write the HTML section immediately after, using the Tufte/Few patterns (per shared rule 5)
   **HTML generation:** For each domain section: after writing the MD section, dispatch HTML generation for that section as a Haiku subagent (`model: haiku`). The subagent receives the domain section's MD content and the Tufte CSS shell. Do not wait for the full requirements.md to be complete. Per shared rule 22.
5. Present a summary for user confirmation
6. If revision needed — **edit just that section**, don't rewrite the whole file
7. Both files must stay in sync at every step

**Output location:** `requirements/` directory in the current project.
- `requirements/requirements.html`
- `requirements/requirements.md`

### Phase 4 — Safety Net Audit

When all domains are explored, use the Read tool to load `~/.claude/skills/gvm-requirements/references/elicitation-checklist.md` and run through it:
- Check each item against what was gathered
- For relevant uncovered items — ask the user
- For items that don't apply — note as N/A (don't ask about them)
- Be transparent: "I'm running through a completeness checklist. A few things we haven't covered..."

### Phase 4b — Source Verification (external document seeds only)

When requirements were derived from an external document, run the source verification protocol defined in `~/.claude/skills/gvm-design-system/references/source-verification.md`. Use `artefact_type=requirement`, `artefact_plural=requirements`, fourth check = **Priority alignment**. Follow the resolution pattern and repeat threshold from the shared reference.

### Phase 5 — Finalize

1. Confirm MoSCoW priorities on all requirements with the user
2. **IM-4 Trace Gate (discovery ADR-304).** If `impact-map.md` exists at the project root, run the IM-4 finalisation check by invoking `scripts/_im4_check.py`:

   ```python
   from _im4_check import check
   errors = check("requirements/requirements.md", "impact-map.md")
   ```

   Paths are relative to the project root; resolve absolute paths via `Path` if invoking from another working directory. The function returns `list[Im4Error]` — empty list = pass. Each error names a requirement that is in-scope (priority Must / Should / Could) but either lacks an inline `[impact-deliverable: D-N]` source tag or references a `D-N` not present in `impact-map.md`. The source-tag format on the priority line is:

   ```markdown
   **RE-1 (Must) [impact-deliverable: D-3]:** the system shall ...
   ```

   Multiple deliverables are permitted as a comma-separated list inside the brackets (`[impact-deliverable: D-3, D-7]`).

   **Sentinel branch — `requirement_id == "-"`.** When the impact-map itself cannot be loaded, the function returns a single error with `requirement_id == "-"` and the message names the parser failure. In that case, do NOT present per-requirement options — instead ask the practitioner via AskUserQuestion to fix `impact-map.md` (typically by re-running `/gvm-impact-map`) and re-run the gate. The per-requirement options below apply only to errors whose `requirement_id` matches a real requirement ID.

   For each `Im4Error` returned with a real `requirement_id`, present the offending requirement to the practitioner via AskUserQuestion with options:
   - **"Add `[impact-deliverable: D-N]` source tag"** — practitioner names the trace; the skill edits the requirement line in place.
   - **"Downgrade to Won't (out of scope)"** — practitioner accepts that the requirement is not in this round; the skill rewrites the priority to `Won't`. IM-4 then skips it.
   - **"Edit impact-map.md to add the missing Deliverable, then re-check"** — practitioner runs `/gvm-impact-map` mid-flight to add the deliverable; on return the skill re-runs `_im4_check.check(...)`.

   Loop until `check(...)` returns an empty list. Do not advance to step 5 (Generate the requirements index table) until clean. If the impact map cannot be loaded, the check returns a single error with `requirement_id == "-"`; surface that to the practitioner and ask them to fix `impact-map.md` (typically by re-running `/gvm-impact-map`) before re-trying.

3. **RA-3 Risk Validation Gate (discovery ADR-306).** Re-run `_risk_validator.full_check` from Phase 0:

   ```python
   from _risk_validator import full_check
   from datetime import date
   risk_assessment, errors = full_check("risks/risk-assessment.md", today=date.today())
   ```

   The function returns `(risk_assessment, errors)`. Pass condition: `len(errors) == 0`. Skip this step only if Phase 0 was bypassed via the "Continue without risk assessment" option. Otherwise loop until clean — do not advance until empty.

   Each `RiskValidationError` carries `(code, section, message)` where `code ∈ {RA-1, RA-2, RA-3, RA-4}` and `section` is one of `Value Risk`, `Usability Risk`, `Feasibility Risk`, `Viability Risk` (or `-` for the parse-failure sentinel). For each error, present the section name and message via AskUserQuestion with these options:

   - **"Edit `risks/risk-assessment.md` to address"** — practitioner writes the missing prose, adds the `questioner: <name>` line, fixes the review date, etc. The skill re-runs `full_check` after the edit.
   - **"Use `*accepted-unknown*` form for this risk"** — practitioner converts the section to the rigid four-line shape: `*accepted-unknown*` on its own line, then `Rationale:`, `Validator:`, and `Review date: <YYYY-MM-DD ≥ today>` lines. The validator's RA-3 path then accepts the section.
   - **"Skip this risk (downgrade requirements that depend on it to Won't)"** — accept that the risk surface is not in this round; the practitioner downgrades the affected requirements via the IM-4 mechanism, and this section can use `*accepted-unknown*` with a future review date that explicitly says "deferred to next round".

   Sentinel branch — `section == "-"`. The file could not be parsed (missing frontmatter, IO error). Present only the "Edit `risks/risk-assessment.md`" option; the other two depend on a parseable file.

4. **IM-6 Persona/Actor Coupling Check (discovery ADR-311).** Run `_im6_check.persona_actor_coupling`:

   ```python
   from _im6_check import persona_actor_coupling
   warnings = persona_actor_coupling("requirements/requirements.md", "impact-map.md")
   ```

   Returns `list[Im6Warning]` — each warning carries `persona_name` and `message`. The check is **non-blocking** (per IM-6: flagged for review, not rejected). For each warning, surface the message to the practitioner so they can decide whether to (a) update `impact-map.md` to add the missing Actor, (b) rename the persona in `requirements.md` to match an existing Actor, or (c) accept the gap.

   Sentinel branch — `persona_name == "-"`. Either file failed to load; the message names the cause. Report to the practitioner and continue to step 5; the IM-6 check is advisory and a parse failure here is not blocking.

5. **Generate the requirements index table** — for each MUST / SHOULD / COULD requirement (Won't is skipped), populate a "Related Risks" column via the RA-6 trace helpers (discovery ADR-310):

   ```python
   from _ra6_trace import risks_for_deliverable, render_risks_cell
   from _im_tags import parse_impact_deliverable_tag

   tag_ids = parse_impact_deliverable_tag(req_priority_line)
   risks = risks_for_deliverable("impact-map.md", tag_ids[0]) if tag_ids else ()
   cell = render_risks_cell(risks)
   ```

   `cell` is `""` when the deliverable has no risks set, or when the impact-map omits the optional `risks` column entirely. When the requirement's `[impact-deliverable: D-N]` tag carries multiple deliverables, look up each and union the risks (canonical `V, U, F, Va` order is preserved by `render_risks_cell`).

6. Write the priority model section
7. Write executive summary (Purpose & Vision) last — now that the full picture is clear
8. **Application naming** — via AskUserQuestion: "Do you have a name for this application?" with options:
   - "Yes — I have a name" → user provides the name, update the document title/subtitle
   - "Help me brainstorm" → generate 4-5 name suggestions based on the requirements content (the application's purpose, target user, and key differentiator). Present via AskUserQuestion with descriptions explaining why each name fits. The user picks one or provides their own.
   - "Skip — I'll name it later" → proceed without naming

   The name, once chosen, is applied to the document title and becomes the project name used by downstream skills.
9. Final sync check between HTML and MD
10. Log cited experts to activation CSV (per shared rule 1).
11. Present completed document for approval

## Document Structure

Both HTML and MD follow this section order. The title/subtitle/date are structural header elements, not numbered sections. Omit sections that have no content — don't include empty sections.

1. **Expert Panel** — table of experts active during creation: Expert, Work, Role in This Document (per shared rule 17 and pipeline-contracts.md)
2. **Purpose & Vision** — the job statement, why this exists
3. **Target User** — Cooper persona
4. **User Journeys** — Patton workflow narratives (when applicable)
5. **Functional Domains** — grouped by domain, each with:
   - Domain introduction
   - Numbered requirements (XX-1, XX-2) with MoSCoW priorities
   - Sidenote annotations for caveats, sources, cross-references
6. **Non-Functional Requirements** — when Volere activated
7. **User Scenarios** — representative profiles and usage patterns
8. **Assumptions** — confirmed assumed-true statements
9. **Constraints** — budget, technology, timeline, regulatory
10. **Out of Scope** — explicitly excluded items
11. **Open Questions** — unresolved items for downstream commands
12. **Requirements Index** — summary table (ID, domain, summary, priority)
13. **Priority Model** — MoSCoW definitions (Must, Should, Could, Won't)

## HTML Design

The HTML output follows Tufte/Few design philosophy. Full CSS, structural patterns, and component templates are in `~/.claude/skills/gvm-design-system/references/tufte-html-reference.md` (shared across all skills). Key elements:

- Floating TOC on the **left**
- Sidenote annotations on the **right**
- Requirement blocks with ID and priority chip
- Tables following Few's principles (minimal gridlines, zebra striping)
- Responsive layout (TOC and sidenotes reflow on narrow screens)

## Markdown Design

The MD output mirrors the HTML content exactly:

- Same sections, same order, same requirement IDs
- Sidenotes rendered as `> blockquote` beneath the relevant requirement
- Standard markdown tables
- Priority shown as `**[MUST]**`, `**[SHOULD]**`, `**[COULD]**`, `**[WONT]**`
- Designed for Claude consumption in downstream commands

## Context Window Management

- Write sections incrementally per shared rule 18 — scaffold first, then one domain section per Edit operation
- Use Edit tool to modify sections, not Write tool to rewrite files
- When presenting sections for confirmation, summarize — don't echo the full HTML/MD back
- Cross-cutting sections (assumptions, open questions) are appended with small edits, not rewritten
- If the conversation is long, reference requirement IDs rather than re-reading full requirement text

## Key Rules

1. **One question at a time** — never overwhelm with multiple questions
2. **Implementation-agnostic** — no architecture, no tech stack, no decomposition decisions
3. **Paired HTML and MD output** — per shared rule 13.
4. **Announce expert activations** — transparent about why certain questions are being asked
5. **Respect de-escalation** — if the user says "not relevant", note it and move on
6. **All requirements need IDs and priorities** — no exceptions
7. **Testable requirements** — if you can't describe how to verify it, it's too vague
8. **Expert discovery for uncovered domains** — per shared rule 2. Document discovered experts in the requirements output.
