---
name: gvm-init
description: Use when initialising the Grounded Vibe Methodology for a new project, especially in specialised domains (financial services, healthcare, regulated industries). Triggered by /gvm-init command or requests to calibrate experts. Optional for general-purpose software — the pipeline discovers and scores experts automatically.
---

# Expert Calibration

The entry point for the Grounded Vibe Methodology on a new project. Calibrates the expert roster for the project's business domain, scores experts, initialises the activation log, and writes a calibration report.

Technology stack and component-level domain experts are not configured here — the stack is unknown before requirements are gathered. Stack specialists activate during `/gvm-tech-spec` when the stack is chosen. Component domains emerge during `/gvm-requirements` and are handled by expert discovery at that point.

**Shared rules:** At the start of this skill, load `~/.claude/skills/gvm-design-system/references/shared-rules.md` and follow all rules throughout execution. Load `~/.claude/skills/gvm-design-system/references/expert-scoring.md` when scoring experts.

## Hard Gates

1. **LOAD EXPERT REFERENCES.** Read `architecture-specialists.md` and the relevant industry domain file BEFORE assessing expert coverage. You cannot assess coverage without knowing what experts exist. Log all loaded experts to activation CSV (per shared rule 1).

2. **SCORE UNSCORED EXPERTS.** If any loaded experts lack scores, score them automatically using the standard scoring process (per shared rule 9). DO NOT leave experts unscored.

3. **EXPERT ROSTER TABLE IS MANDATORY.** The output must include an Expert Roster Summary table. This table is consumed by downstream skills — if it is missing or malformed, downstream expert panels will be wrong.

4. **HTML BEFORE APPROVAL.** Write the init MD file first, then IMMEDIATELY write the HTML file. Both must exist before presenting the init report for user review.

## Pre-check

Before starting, check for signs of prior initialisation:
- Does `~/.claude/gvm/expert-activations.csv` exist and contain entries for the current project (basename of cwd)?
- Are there industry domain files in `~/.claude/skills/gvm-design-system/references/industry/` beyond the defaults (market-risk, credit-risk, model-risk, operational-risk)?
- Do experts in the existing reference files have scores?

If any of these indicate prior setup, ask via AskUserQuestion:

**Question:** "This project has been initialised before. What would you like to do?"
- **Start fresh** — re-run the full init flow
- **Alter** — read the existing init report and expert roster. Present the current roster to the user via AskUserQuestion with options to: (a) add a new expert, (b) rescore an existing expert via `/gvm-experts`, or (c) replace the industry domain file. For each Alter operation, the edit target is: (a) add a new expert — update the Expert Roster Summary table in both files; (b) rescore an existing expert — delegate to `/gvm-experts` (see re-entry below); (c) replace the industry domain file — update the Industry Domain section in both files. For operation (b) rescore, after `/gvm-experts` completes: return to the Alter flow, re-read the expert's entry from the updated reference file, present the updated score to the user, update the Expert Roster Summary table in both init HTML and MD files with the new score, and add a changelog entry: "Rescored [Expert]: [old score] → [new score]." Operations (a) and (c) require editing both init HTML and MD files directly. For Alter mode, edit the existing `init-{NNN}.html` and `.md` files in place using Edit (not Write). Add a changelog entry noting what was altered. Do not create a new numbered pair. The init report records the current state of the roster; the changelog entry is sufficient to track what changed. Creating a new pair would imply a new calibration session.
- **Cancel** — exit without changes

If no prior setup is detected, proceed with the full flow.

## Step 0 — Application Brief (optional)

An Application Brief is a structured one-page justification for a project. It answers: what problem does this solve, for whom, and is it worth doing? The brief feeds into `/gvm-requirements` as seed input — the problem statement becomes the starting point for domain elicitation, the architecture direction constrains the tech spec.

**When to use:** The brief is optional by default. Offer it via AskUserQuestion:

**Question:** "Would you like to create an Application Brief before proceeding?"
- **Yes** — produce a structured brief (recommended for organisations that gate project starts, end-user computing scenarios, or when the project's justification needs approval before committing resources)
- **No** — skip to Step 1 (the project is already approved or the justification is obvious)

**If the user selects Yes:**

Conduct a brief conversation to gather:

1. **Problem Statement** — what problem does this solve, for whom? (Rumelt: diagnosis — identify the actual challenge, not just symptoms)
2. **Proposed Solution** — one paragraph, not a spec. What would we build? (Rumelt: guiding policy)
3. **Value Proposition** — why this solution for this problem? What changes for the user if this exists? (Osterwalder: problem-solution fit from *Value Proposition Design*)
4. **Existing Landscape** — what already exists that addresses this problem? Why is it insufficient? Are there projects in progress that overlap?
5. **High-Level Solution Shape** — NOT a technical specification. Do not name technologies, frameworks, or vendors here. This section describes the shape of the solution at the broadest level only (Brown: C4 system context — what is this system, who uses it, what does it interact with):
   - What type of thing is this? (web application, mobile app, data pipeline, CLI tool, API service, internal tool)
   - Who uses it? (single user, small team, department, enterprise-wide, public)
   - What does it connect to? (name the external systems or data sources, not the integration technology)
   - How big is this? (personal tool, team tool, departmental, enterprise)
   
   **Explicitly out of scope for this section:** programming languages, frameworks, cloud providers, database choices, API designs, architecture patterns. Those decisions belong in `/gvm-tech-spec` after requirements are gathered. The brief constrains the tech spec at the highest level only — "this is a multi-user web application" not "this is a React/Next.js app on Vercel."
6. **Stakeholders & Users** — who cares about this, who uses it, who approves it
7. **Constraints** — budget, timeline, regulatory requirements, team capacity, technology mandates
8. **Possible Outcomes** — inform the proposer that the approval authority may decide to:
   - **Approve** — proceed to `/gvm-requirements`
   - **Approve with conditions** — proceed, but with changes to scope, constraints, or solution shape (e.g., "approved as single-user only," "must integrate with existing system X," "budget capped at Y")
   - **Absorb into existing project** — redirect scope to an existing programme
   - **Defer** — the idea has merit but the timing or resourcing is not right
   - **Decline** — the business case does not justify the investment
   
   The brief documents the case; the approval authority makes the decision. The proposer does not recommend an outcome. If approved with conditions, the conditions become constraints that feed into `/gvm-requirements`.

Write the brief as paired HTML + MD to `init/brief-001.html` and `init/brief-001.md`. The brief is a standalone document — it can be reviewed by an approval authority before any pipeline work begins.

**How the brief feeds downstream:**
- The Problem Statement seeds `/gvm-requirements` domain elicitation
- The Solution Shape constrains `/gvm-tech-spec` at the highest level only (what type of system, not what technology)
- The Constraints become requirements constraints
- The Existing Landscape informs `/gvm-site-survey` if extending an existing project
- The Stakeholders & Users seed persona identification in requirements

**Expert grounding for the brief:**
- **Richard Rumelt** (*Good Strategy Bad Strategy*, *The Crux*) — the kernel structure (diagnosis, guiding policy, coherent actions) shapes sections 1-2. Already in domain-specialists.md.
- **Alexander Osterwalder** (*Value Proposition Design*) — problem-solution fit shapes section 3. Load from domain-specialists.md if scored; if not, use the framework without formal scoring.
- **Simon Brown** (C4 model) — system context level shapes section 5. Already in architecture-specialists.md.
- **George Fairbanks** (*Just Enough Software Architecture*) — risk-driven depth for architecture direction. Already in architecture-specialists.md.

After the brief is written, proceed to Step 1 (Business Domain).

## Step 1 — Business Domain

Ask via AskUserQuestion:

**Question:** "What is the business domain of this project?"

**Options:**
- **Financial services** (banking, insurance, risk management, trading)
- **Healthcare / life sciences**
- **Technology / SaaS**
- **General-purpose software** (no specific industry domain)

The user can also select "Other" and type their domain.

## Step 2 — Expert Roster Assembly

Load `~/.claude/skills/gvm-design-system/references/roster-assembly.md` and run the shared roster assembly process with init inputs:
- **Business domain:** the user's answer from Step 1
- **Tech stack:** not available (deferred to /gvm-tech-spec)
- **Codebase state:** N/A (greenfield)
- **Software patterns:** N/A

The process handles industry domain matching, Tier 1 adjustment for specialised domains, expert discovery, automatic scoring, and roster presentation. Steps 3–4 (Tier 2a/3) are skipped for init because the information is not yet available.

## Step 3 — Automatic Setup

These steps run automatically with no user interaction:

**Bootstrap GVM home directory** per shared rule 14 (creates `~/.claude/gvm/`, initialises activation log, copies plugin guide).

**Write calibration report:** Produce paired HTML and MD output to `init/init-001.html` and `init/init-001.md` (scan for existing files and increment). **HTML generation:** Dispatch the HTML generation as a Haiku subagent (`model: haiku`). Per shared rule 22. Use the Read tool to load `~/.claude/skills/gvm-design-system/references/tufte-html-reference.md` before the first HTML write.

**Report structure:**

1. **Executive Summary** — project name, date, business domain
2. **Process Experts (Tier 1)** — defaults confirmed or replacements created, with rationale
3. **Industry Domain (Tier 2b)** — files selected or created, coverage assessment, any newly discovered experts with scores
4. **Expert Roster Summary** — single table of all active experts: expert name, work, tier, classification, reference file, status (existing / newly added / newly scored). Log cited experts to activation CSV (per shared rule 1).
5. **Activation Log** — confirmation that the log was initialised or already existed
6. **Next Steps** — "Run `/gvm-requirements` to begin gathering requirements. Stack specialists and component-level domains will be configured as they emerge during the pipeline."

The MD version is the primary input for downstream skills — the expert roster summary tells `/gvm-requirements`, `/gvm-tech-spec`, and other skills which experts are active for this project.

## Pipeline Position

This is the precondition for greenfield projects. After `/gvm-init`, the pipeline proceeds to `/gvm-requirements`.

For existing codebases, use `/gvm-site-survey` instead — it diagnoses the codebase and selects experts based on what it finds.

```
/gvm-init → /gvm-requirements → /gvm-test-cases → /gvm-tech-spec → /gvm-design-review (optional) → /gvm-build → /gvm-code-review → /gvm-test → /gvm-doc-write → /gvm-doc-review → /gvm-deploy
```

## Key Rules

1. **Recommended for specialised domains, optional for general-purpose software.** For financial services, healthcare, safety-critical, or regulated industries, run init before requirements to load the right industry experts upfront. For general-purpose software, the pipeline discovers and scores experts automatically.
2. **One question for the common case** — business domain. Tier 1 adjustment only surfaces for specialised domains. Stack and components are deferred to later pipeline phases where the information is available.
3. **Expert discovery delegates to the design system** — per shared rule 2.
4. **Explicitly confirm when no gaps are found** — if the roster already covers everything, tell the user.
5. **Score automatically** — per shared rule 9. Do not ask permission.
