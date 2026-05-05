# Shared Rules for All GVM Skills

Cross-cutting rules that apply to every GVM skill. Loaded once at the start of each skill's execution.

## 1. Expert Activation Logging

Append a row to the activation log every time a GVM skill loads or cites an expert.

**File:** `~/.claude/gvm/expert-activations.csv`

**Use the helper script** — do not generate CSV rows manually. The script is Python 3 (cross-platform: macOS, Linux, Windows) and handles timestamping, project path, CSV quoting, and creating the file with a header if it does not exist:

```bash
python3 ~/.claude/skills/gvm-design-system/scripts/log-expert.py \
  <skill> <phase> <expert> <work> <classification> <tier> <event>
```

On Windows where `python3` may not be on PATH, use `python` instead:

```bash
python ~/.claude/skills/gvm-design-system/scripts/log-expert.py ...
```

Example:

```bash
python3 ~/.claude/skills/gvm-design-system/scripts/log-expert.py \
  /gvm-requirements elicitation "Karl Wiegers" \
  "Software Requirements (3rd ed.)" Canonical tier1 loaded
```

**Fields:**
- `skill` — e.g. `/gvm-requirements`, `/gvm-doc-review`
- `phase` — e.g. `elicitation`, `scoring`, `review`
- `expert` — author/expert name
- `work` — primary work cited
- `classification` — `Canonical` | `Established` | `Recognised` | `Emerging` | `Provisional` | `unscored` (closed set from `expert-scoring.md`; `unscored` is a lifecycle sentinel before a score has been assigned)
- `tier` — `tier1` | `tier2a` | `tier2b` | `tier3` | `discovered`
- `event` — `loaded` (reference file read into context) | `cited` (expert named as source in output)

Append only, all skills must log. One row per expert per event.

## 2. Expert Discovery

When a domain, technology, or pattern is encountered with no matching expert, run the **Expert Discovery and Persistence Process**:

1. Assess coverage against loaded reference files — identify which domains or technologies have no expert.
2. Research candidate experts — find authorities with published, peer-recognised work in the gap area.
3. Score candidates using the standard scoring process with independent verification (per `~/.claude/skills/gvm-design-system/references/expert-scoring.md`).
4. Present candidates to the user with scores and evidence.
5. Persist approved experts to the appropriate reference file (`architecture-specialists.md`, the relevant `domain/{domain}.md` file, the relevant `stack/{stack}.md` file, or an industry file).
6. Persist the discovered expert to `~/.claude/gvm/discovered-experts.jsonl` per rule 14.
7. Document discovered experts in the current skill's output.

This is the canonical definition of expert discovery. `roster-assembly.md` Step 5 invokes this process during roster assembly.

## 3. Experts Who Find Should Fix

When expert-grounded review identifies issues, the same experts' frameworks should guide the fix. An architectural concern surfaced by the architecture panel should be resolved using the same architectural principles. The diagnosing expert's framework defines not just what is wrong but what "right" looks like.

## 4. Industry Domain Loading

At the start of any skill that needs domain grounding, check whether the application's business domain has an industry domain reference file in `~/.claude/skills/gvm-design-system/references/industry/`. If a matching file exists, load it with the Read tool. If no file exists but the domain is identifiable, flag it to the user: "No industry domain reference file found for [domain]. Would you like me to identify authoritative experts for this domain?"

## 5. Document Output Loading

Before the first document write, use the Read tool to load:

1. `~/.claude/skills/gvm-design-system/references/tufte-html-reference.md` — core HTML/CSS design patterns (Tufte & Few). **Always load this before any HTML write.**
2. `~/.claude/skills/gvm-design-system/references/writing-reference.md` — writing quality standards following Doumont, Williams, Zinsser, and Orwell for clear, direct prose.

**Companion files — load ONLY when writing that output type:**

| Output | Companion file | Relationship |
|---|---|---|
| Review report (doc-review, code-review, design-review, test) | `~/.claude/skills/gvm-design-system/references/tufte-review-components.md` — verdict box, score card, issue blocks, criterion rows | Extends core (load alongside `tufte-html-reference.md`) |
| Tech spec with ADRs or component-detail disclosures | `~/.claude/skills/gvm-design-system/references/tufte-spec-components.md` | Extends core (load alongside `tufte-html-reference.md`) |
| Presentation slide deck | `~/.claude/skills/gvm-design-system/references/tufte-slide-template.md` — self-contained template (named `-template` because it replaces the core file rather than extending it) | Replaces core (load INSTEAD of `tufte-html-reference.md`) |

Loading a companion file when the skill does not need it is wasted context. Use the table above, not intuition.

**Before any document write:** load the core file and the appropriate companion file before writing any document output, and before evaluating any existing document.

**Before any quality review** (`/gvm-doc-review`, `/gvm-code-review`, `/gvm-design-review`, `/gvm-test`, or any ad-hoc quality review): additionally load `~/.claude/skills/gvm-design-system/references/review-reference.md`. It contains assessment methodology from Deming, Cronbach, Gilb, Fagan, Stevens & Levi, and Marzano — covering measurement reliability, rubric design, and reviewer calibration. This applies to subjective quality assessments, not to expert scoring (which has its own structured methodology in `expert-scoring.md`).

**Scope:** This rule applies to all document-producing and document-reviewing skills. Skills that produce only conversational output (e.g., `/gvm-status`) are exempt.

## 6. AskUserQuestion Usage

Use AskUserQuestion for all structured decisions (approve/revise, select priorities, confirm/reject, choose between alternatives). Reserve free-text conversation for open-ended exploration (applying Norman's affordance principle from *The Design of Everyday Things* — a selection task needs selection affordances, not a text field). This gives the user a clean submit-based UI instead of requiring typed responses for yes/no/choice questions.

## 7. When Not to Ground

Not every action needs expert grounding (Fowler: "the simplest thing that could possibly work" — grounding a typo fix is ceremony without value). Inline bug fixes, simple renames, formatting corrections, and routine housekeeping should just be done. Expert grounding is for decisions — architectural choices, design trade-offs, technique selection, quality judgements. The practitioner (or the AI executing a skill) should use judgement about when a task benefits from citing an expert and when it's overhead without value.

## 8. What to Surface vs What to Keep Invisible

The user should see which experts are active and why. They should not see the machinery that manages them.

**Surface to the user:**
- Which experts are active for this project, their names, works, and classifications
- When an expert's framework is being applied -- cite them in the output
- When a gap is found -- "no expert covers [domain], would you like me to find one?"
- Expert coverage assessments (covered vs gaps)
- Discovered expert candidates with their proposed classifications and evidence
- Expert names and classifications in all report outputs

**Keep invisible (do not narrate to the user):**
- CSV append commands and activation log mechanics
- Independent agent verification dispatch details
- Score convergence/divergence calculations
- Sample-size tier computations for utilisation
- The step-by-step scoring process internals
- Reference file loading operations (just load them, don't announce "I am now loading shared-rules.md")

## 9. Automatic Scoring

Scoring is a system operation, not a user decision (Deming, *Out of the Crisis*: quality built into the process, not inspected in afterwards). When any skill loads a reference file and finds unscored experts, score them automatically — run the standard scoring process with independent verification and persist the scores. Do not ask the user for permission. The methodology should never be less effective because a user forgot to score their experts. The user can explicitly request rescoring via `/gvm-experts` if they want to review or adjust scores.

## 10. Pipeline Artefact Contracts

Skills that produce documents consumed by downstream phases must conform to the structural contracts defined in `~/.claude/skills/gvm-design-system/references/pipeline-contracts.md` (Parnas, "On the Criteria To Be Used in Decomposing Systems into Modules", 1972: information hiding — each module conceals a design decision that could change, exposing only a stable interface). The contracts specify required sections, ID formats, and structural elements that downstream consumers depend on. When writing output, check the contract for your artefact type. When reading upstream input and something looks wrong, check the contract to determine whether the upstream producer is non-conformant or the consumer's expectations are outdated.

## 11. Changelog Recording

Every modification to a pipeline artefact after its initial creation must include a changelog entry. The changelog is a section within the artefact itself, not a separate file (Fowler: simplest approach that works).

**When to record:**
- Adding requirements, test cases, or spec sections to an existing document
- Modifying existing content (priority changes, wording changes, decision reversals)
- ADR supersession (the superseding ADR records the change; the superseded ADR gets a status update)

**When NOT to record:**
- Initial document creation (the document's existence is the record)
- Typo fixes, formatting corrections, or other non-semantic changes (per rule 7: not every action needs ceremony)

**Format:** Use the Changelog Section Contract from `pipeline-contracts.md`. Append new rows at the top. Never modify or delete existing rows (change records are append-only — modifying history makes the record untrustworthy).

## 12. Documentation Maintenance

Project documentation is created by `/gvm-doc-write` (pipeline docs mode) after `/gvm-test` passes. This rule covers maintenance of that documentation on subsequent pipeline rounds.

**README.md:** Must reflect the current state of the project (Redish, *Letting Go of the Words*: documentation describes what exists now, not what was planned — users arrive via search and need current truth). After any subsequent build phase that changes user-visible behaviour, features, setup instructions, or configuration, update the README. The README describes what exists now, not what was planned. On the first pipeline round, `/gvm-doc-write` creates it; on subsequent rounds, this rule ensures it stays current.

**CHANGELOG.md (project-level):** Required when multiple pipeline rounds have been run (i.e., `requirements-002.md` or later exists). Summarises user-visible changes across rounds. This is a user-facing document — describe what changed from the user's perspective, not development internals. Created by `/gvm-doc-write` when the second round's artefacts are detected; maintained per this rule on subsequent rounds.

**User-facing docs:** If requirements specify user documentation (help pages, API docs, guides), these must match implemented behaviour after every build phase. Created by `/gvm-doc-write` (pipeline docs mode); kept current per this rule. Stale user docs are a `/gvm-doc-review` finding.

## 13. Paired HTML and Markdown Output

Every skill that produces document output must write both an HTML file and a Markdown file, always in sync (Clements, *Documenting Software Architectures*: different views serve different stakeholders — the HTML serves the practitioner reading the document, the MD serves the downstream skill parsing it). The HTML version is for human reading (Tufte/Few design). The MD version is the machine-readable artefact consumed by downstream skills. Every write touches both files — if you update one, update the other in the same operation.

**Ordering: MD first, then HTML immediately after.** Write the MD file, then write the HTML file for the same content. Both files MUST exist before any approval checkpoint. The user reads the HTML to make approval decisions — if the HTML does not exist when approval is requested, the user cannot evaluate the output.

**Never batch HTML writes.** DO NOT write all MD files first and then generate all HTML files afterwards. The correct sequence for multi-document skills is: write spec-1.md → write spec-1.html → present spec-1 for approval → write spec-2.md → write spec-2.html → present spec-2 for approval. Each document is complete (both formats) before the next begins.

Exception: `/gvm-doc-write` standalone documents (presentations, strategy documents, newsletters, training materials) are not pipeline artefacts — no downstream skill parses their MD. The MD version is optional and user-controlled for these document types. Presentations are HTML-only.

Exception: **all review/verification reports are HTML-only** — this covers `/gvm-doc-review`, `/gvm-code-review`, `/gvm-design-review`, and `/gvm-test`. The reports are read by the practitioner, not parsed by downstream skills (`/gvm-status` only checks file existence, which works against HTML). Review findings are carried forward in `reviews/calibration.md`, not in the report MD. Producing a paired MD is duplicate output with no consumer. The distinction is: **pipeline artefacts that Claude reads downstream** (requirements, test cases, specs, init, site-survey, build handovers, build-summary) remain paired MD + HTML; **reviews that only humans read** are HTML-only.

## 14. GVM Home Directory Bootstrap

User data lives in `~/.claude/gvm/`, outside the plugin install path, so it survives plugin updates. On the first invocation of any write-capable skill, run the bootstrap script — it is idempotent and safe to re-invoke on every skill run. `/gvm-status` is read-only and does not bootstrap.

```bash
python3 ~/.claude/skills/gvm-design-system/scripts/gvm-bootstrap.py
```

That single command:

1. Creates `~/.claude/gvm/` and `~/.claude/gvm/docs/` if missing.
2. Creates `expert-activations.csv` with the canonical header if missing.
3. **Self-heals a clobbered file** — if `expert-activations.csv` exists but lacks the canonical header (i.e., another process overwrote it with `>` or appended raw rows without a header), the script atomically prepends the header. No rows are lost.
4. Copies `plugin-guide.html` from the plugin's `docs/` into `~/.claude/gvm/docs/` if present.
5. Migrates a legacy log file from `~/.claude/skills/gvm-design-system/expert-activations.csv` to the new location if the new file does not yet exist.

**Why this replaces the previous shell snippet:** the prior bootstrap (`mkdir -p ... && [ -f ... ] || echo 'header' > file`) was vulnerable to copy-paste — copying just the right-hand side of the `||` clobbered any existing log with a header line. The new single-script pattern eliminates that failure mode. As an additional belt-and-braces safeguard, `log-expert.py` also self-heals the header on every call.

**Which skills bootstrap:** `/gvm-init`, `/gvm-requirements`, `/gvm-test-cases`, `/gvm-tech-spec`, `/gvm-build`, `/gvm-code-review`, `/gvm-doc-review`, `/gvm-design-review`, `/gvm-doc-write`, `/gvm-site-survey`, `/gvm-experts`, `/gvm-test`, `/gvm-deploy`.

For discovered-experts.jsonl schema, rescore-log.jsonl schema, re-insertion lifecycle, and migration instructions, see `shared-rules-operations.md` (load only when performing bootstrap, expert discovery, or build check promotion).

## 15. Hallucination Prevention

Treat the AI as a generator inside a verification loop, not as an oracle. Verification cost is proportional to risk — a hallucinated requirement propagates through the entire pipeline; a hallucinated code review comment does not.

**Cross-cutting techniques (apply in every phase):**

1. **Structured output resists hallucination** — require specific IDs, traceability links, concrete values, and named sources. Pipeline artefact contracts (rule 10) enforce this structurally.
2. **Independent verification for claims of authority** — when the AI asserts credentials, publication existence, or framework provenance, verify independently. Applied to expert scoring; apply to any factual claim downstream phases depend on.
3. **Source verification** — dispatch an independent agent via `source-verification.md` to verify cited sources exist and attributed claims are accurate. Apply to requirements, test cases, and tech specs.

**Phase-specific techniques:**

| Phase | Hallucination Risk | Technique |
|-------|-------------------|-----------|
| **Requirements** | Fabricated domain facts, invented regulations | Chain of Verification: plan verification questions for domain claims, answer independently, revise. Source verification for cited standards. |
| **Test Cases** | Invented boundary values, fabricated API behaviours | Trace every test case to a specific requirement. Flag preconditions assuming unstated capabilities. |
| **Tech Spec** | Hallucinated framework capabilities, invented APIs | Verify framework claims against official docs. Flag unverifiable "supports X" assertions. API boundary contracts must match on both sides. |
| **Build** | Non-existent packages (slopsquatting), invented APIs | TDD catches hallucinated code — failing tests surface non-existent methods. Verify package existence before importing. |
| **Reviews** | Hallucinated findings, missed real issues | Independent parallel panels. Every finding must cite a specific file and line. |
| **Expert Scoring** | Fabricated credentials, invented publications | Independent agent verification with convergence/divergence flagging. Any dimension scored 4+ requires verifiable evidence. |

## 16. Dual Review (Calibration Bias Correction)

Calibration introduces systematic bias: areas that scored well receive less scrutiny, resolved findings are trusted without re-verification.

**Applies to:** `/gvm-doc-review`, `/gvm-code-review`, `/gvm-design-review`.

**Trigger:** automatic when the calibration file contains score history for 2+ completed prior rounds (round 3 or later).

**Mechanism:**

1. **Dispatch two parallel reviewers:** a calibrated reviewer (receives calibration file, resolved findings, anchors, recurring findings) and an uncalibrated blind reviewer (same documents and expert references, no calibration data). 
2. **Reconcile findings:** classify each blind finding as New (merge), Confirmed (keep calibrated version), Regression (merge), Rediscovered (discard), or Noise (discard). Record dual review metadata in calibration.

**Why automatic:** practitioners with developed blind spots are least likely to think they need a blind review. The cost (one extra subagent + reconciliation) is proportional to the value.

For reconciliation category details, see each review skill's SKILL.md.

## 17. Expert Panel Attribution in Pipeline Artefacts

Pipeline artefacts must include an **Expert Panel** section recording which experts were active and what each governed.

**Applies to:** `/gvm-requirements`, `/gvm-test-cases`, `/gvm-tech-spec`, `/gvm-build` output documents.

**Position:** after the subtitle/metadata block, before the first content section.

**Format (MD):**

```markdown
## Expert Panel

| Expert | Work | Role in This Document |
|--------|------|-----------------------|
| Karl Wiegers | *Software Requirements* (3rd ed.) | Elicitation methodology, requirement classification |
| Jeff Patton | *User Story Mapping* | Journey mapping, persona-grounded requirements |
```

**Rules:**

1. List only experts actually loaded and applied — match `loaded` events in the activation log.
2. The "Role" column is specific to this document, not a generic expert description.
3. Tier 1 experts appear on every document for their phase; tier 2/3 specialists appear only when activated.
4. Update on revision — the panel reflects who shaped the current version.

## 18. Incremental Document Writing

All HTML documents must be written incrementally — section by section — not as a single monolithic write. Writing an entire document in one pass risks truncation, lost sections, and degraded quality in later sections as context fills. Incremental writing also produces better results per section because each section gets the AI's full attention.

**How to chunk:**

1. **Write the scaffold first** — use the Write tool to create the file with the document shell: DOCTYPE, head, CSS, nav, opening `<main>` tag, and the closing script/body/html. This is the skeleton that sections will be appended into.
2. **Write each major section using Edit** — append one section at a time into the document using the Edit tool (replacing the closing tags, writing the section, then re-adding the closing tags). Each section gets the AI's full attention.
3. **Verify after each section** — read back the last few lines of the document to confirm the section landed correctly before writing the next one.

**Section granularity:** one H2-level section per write operation is the default. For very large sections (e.g., a domain with 20+ requirements), sub-chunk at the H3 level. The goal is that each write operation produces a coherent, complete unit that does not depend on what comes next.

**Applies to:** all document-producing skills — `/gvm-requirements`, `/gvm-test-cases`, `/gvm-tech-spec`, `/gvm-doc-review`, `/gvm-code-review`, `/gvm-design-review`, `/gvm-site-survey`, `/gvm-doc-write`, `/gvm-init`, `/gvm-build`, `/gvm-test`, `/gvm-deploy`. Always write HTML incrementally regardless of expected size.

## 19. Cross-Platform Shell Commands

When skills need file modification timestamps, use a cross-platform approach:

```bash
python3 -c "import os; print(int(os.path.getmtime('FILE')))"
```

Do not use `stat -f %m` (macOS-only) or `stat -c %Y` (Linux-only) directly — these fail silently on the wrong platform.

## 20. Gate Preservation on Branch Paths

When a process flow creates a short-circuit path (simple build, update-existing, light mode, or any early exit), ALL Hard Gates from the standard flow still apply unless explicitly waived on the branch (Fagan, 1976: inspection requires defined entry and exit criteria — undefined criteria are inconsistently applied). The branch instruction must re-state which gates apply:

"Hard Gates [N–M] still apply — this branch skips [X], not execution discipline."

If a branch does not mention Hard Gates, an executor may assume they are skipped. This has caused repeated critical findings across review rounds 1–3. Every shortcut path must be self-contained: an executor reading only the branch must know which gates to enforce.

## 21. Build Check Promotion (Self-Improving Build)

Recurring review findings are common-cause variation — fix the process once, not the output repeatedly (Deming). Inspection checklists should evolve from prior findings (Fagan).

When a review finding recurs enough to indicate a systemic pattern, it is promoted to a **build check** — a concrete instruction that `/gvm-build` loads during prompt generation and applies during the code review loop.

**Applies to:** `/gvm-code-review`, `/gvm-doc-review`, `/gvm-design-review` (producers). `/gvm-build` (consumer).

**Storage:** `reviews/build-checks.md` — created on first promotion, not on first review.

**Promotion thresholds (either triggers promotion):**

- **Threshold A (systemic):** recurring finding flagged in 3+ consecutive rounds.
- **Threshold B (regression):** a resolved finding reappeared.

**Build check tiers:**

- **Tier 1 (permanent):** general engineering practice (DRY, resource lifecycle, naming consistency). Never retired. Test: useful on a completely different project?
- **Tier 2 (project-specific):** tied to a particular library, SDK, API, or domain convention. Retirement candidate if not triggered for 3 rounds.

For the detailed promotion procedure (steps 1-5), retirement procedure, and build consumption instructions, see `shared-rules-operations.md` (load when performing build check promotion).

## 22. Cost-Optimized Model Selection

Match the model to the cognitive demand of the task.

**Model tiers:**

| Tier | Model | When to use |
|------|-------|-------------|
| **Opus** | Primary model | Architecture decisions, greenfield requirements, complex builds (3+ chunks), strategy documents, review synthesis, tech spec design, expert scoring |
| **Sonnet** | `model: sonnet` | Review panels, simple builds (≤2 chunks), seed-based requirements, light-mode verification, newsletters/training/status reports, dual review subagents |
| **Haiku** | `model: haiku` | HTML generation from structured data, activation/citation logging, calibration file updates, changelog entries, file scanning and format conversion |

**HTML generation rule:** Dispatch a Haiku subagent for HTML immediately after writing each section's or document's MD (per rule 13 timing). Always specify the `model:` parameter explicitly when dispatching subagents.

**Override:** The user can always request a specific model.

**Operational detail** for rules 14 and 21 (file schemas, promotion procedures, retirement logic) is in `shared-rules-operations.md`. Load it only when performing bootstrap, expert discovery, or build check promotion — not on every skill invocation.

## 23. Mechanical Cross-Spec Parity Enforcement

Review-driven detection of cross-spec drift is high-latency: drift enters during spec edits and surfaces only on the next review. Inspection reveals defects but does not prevent them (Deming, *Out of the Crisis*).

**Applies to:** `/gvm-tech-spec`, `/gvm-design-review`, `/gvm-build`. Any project with 3+ spec files.

**Requirement:** projects with 3+ spec files SHOULD provide a parity script (default location: `scripts/spec-parity-check.py`, or equivalent for the project's language). The script mechanically enforces cross-spec invariants that are expensive to check manually. Suggested rules:

- **R1** Same class / equivalent type in 2+ specs has matching field sets
- **R2** Every type referenced as an annotation is defined somewhere (or is a whitelisted framework type)
- **R3** Database ENUM value sets match code-side enum / Literal / union value sets
- **R4** REST / gRPC / MQ endpoints consumed in one spec are declared in another
- **R5** Shared namespaces (e.g. a project-wide prefix on cache keys) are applied consistently
- **R6** Shared key patterns (cache keys, topic names) have identical format strings
- **R7** Every NOT NULL DDL column has a specified writer (UPDATE/INSERT, request-model field, or prose mention)

**When to run:**

1. **`/gvm-tech-spec`:** after any spec edit, run the parity script and surface failures to the user before marking the edit complete. Do not auto-fix — present findings for user decision (intentional drift may exist that the script cannot know about).
2. **`/gvm-design-review`:** run the parity script BEFORE dispatching panels. Treat its output as a free zero-cost panel. Findings it surfaces do not need to be re-discovered by panels — panels focus on what humans do well (requirements interpretation, architectural judgment, ambiguous algorithms).
3. **`/gvm-build`:** run the parity script before each chunk dispatch. Block the chunk if new parity findings appear relative to the last clean baseline.

**If the script does not exist:** the skill still runs but flags it: *"No spec-parity script found. Projects with 3+ specs should provide one to prevent cross-spec drift."* Propose creating one.

**Why mechanical enforcement:** human reviewers cannot reliably keep the full cross-spec reference graph in working memory — the pairwise check count grows combinatorially. A pragmatic regex-based script runs in seconds and catches the drift classes that consume the most review bandwidth. The script is not a substitute for expert review — it is a prerequisite, enforcing mechanical invariants so expert review can focus on semantic questions.

**Script design principles:**

- Stdlib-only where possible (portable, no dependency management).
- Exit code 0 = clean, 1 = findings, 2 = script error.
- Findings must cite `file:line` for every location.
- Rules are additive and scope-configurable (e.g. `--rules R1,R3`).
- False positives are an acceptable cost; tighten heuristics over time based on project-specific patterns.
- Document each rule with a comment explaining the regression pattern it prevents.

**Record in calibration:** after running, append a `## Parity Check History` row to `reviews/calibration.md` with date, total count, per-rule count, and `Δ` versus previous run. A rising count is a leading indicator that spec discipline is slipping.

## 24. Fix-Propagation Discipline

A spec edit is not complete when the target file is updated. It is complete when every spec that references the changed symbol is updated, or the divergence is explicitly documented. Unpropagated fixes are a common source of regression findings in subsequent review rounds.

**Applies to:** `/gvm-tech-spec`, `/gvm-design-review` (when dispatching fix agents), `/gvm-build` (when a build change touches a shared contract).

**Rule:** When editing a shared symbol — a class name, ENUM value set, REST endpoint, key pattern, state machine transition, or cross-spec reference — the editor MUST grep the entire spec corpus for the symbol and either update every reference in the same edit, or explicitly document why the reference is intentionally divergent.

**Before claiming a spec edit complete:**

1. `grep -n "<symbol>" specs/*.md` — locate every mention.
2. For each match: decide whether it needs updating. Update in the same edit.
3. If any spec is intentionally left divergent, add a comment explaining why (e.g., `mirrors` comment: intentionally lags pending a decision).
4. Run the parity check script (rule 23). It must pass, or fail for known reasons that are recorded.

**What counts as a shared symbol:**

- Any class / type name used as a type annotation in 2+ specs
- Any database ENUM or code-side enum / Literal / union value set
- Any REST / gRPC / MQ endpoint path
- Any shared key pattern or channel / topic name
- Any state machine transition rule
- Any ADR decision that replaces / supersedes an earlier ADR (the earlier ADR must be marked Superseded)
- Any shared constant (timeouts, retry counts, TTLs) named in multiple specs

**What this rule is not:**

- Not a rule against intentional divergence — consumers sometimes lag a canonical spec deliberately over a multi-day effort. Divergence is permissible if documented in a changelog entry or `mirrors` comment.
- Not a rule against rename refactors — renaming a shared symbol is a valid edit, but it must be applied to every reference in the same commit / edit sequence.

**Dispatch-prompt discipline:** when `/gvm-design-review` dispatches a fix agent to update a spec, the dispatch prompt MUST include: *"After editing, grep the spec corpus for every shared symbol you changed. Update cross-references in the same edit. Run the project's parity check script and verify no new findings before returning."*

**Why this matters:** a fix that stops at one file and surfaces the same pattern in the next review round is pure re-work — the same defect rediscovered at higher cost. Discipline at edit time is an order of magnitude cheaper than discipline at review time.

## 25. No Silent Skip, Defer, or Stub

25. **No silent skip, defer, or stub.** When a skill is about to skip a requirement, defer implementation to a later chunk, or leave code in a stub state, it MUST surface the decision via `AskUserQuestion` before proceeding. Options presented:
    - "Implement now"
    - "Defer and record as surfaced requirement"
    - "Leave as stub and record in handover / STUBS.md"

    The user decides; the skill records the decision in the handover's Deviations + Surfaced Requirements sections.

**Applies to:** every GVM skill that may take any of the three actions — most notably `/gvm-build` (defer / stub at chunk execution), `/gvm-code-review`, `/gvm-test`, `/gvm-requirements`, `/gvm-test-cases`.

**Why:** silent skips, deferrals, and stubs are the dominant cause of "looks complete, isn't" outcomes (pipeline-propagation ADR-602). Surfacing the decision lifts it from a hidden choice to a recorded one. The user retains agency; the handover retains evidence.

## 26. Attribution of GVM-Produced Artefacts

Every artefact produced by a GVM skill carries a subtle attribution identifying the methodology. This applies to commits and to documents.

**Applies to:** every GVM skill that produces output.

### Commit trailer

Any `git commit` executed by a GVM skill MUST include the trailer line:

```
🌱 Developed using Grounded Vibe Methodology
```

**Placement:** in the commit message trailer block, adjacent to (above or below) the `🤖 Generated with [Claude Code]` line. Both attributions appear together; ordering does not matter.

**Example commit structure:**

```
<concise subject>

<body>

🌱 Developed using Grounded Vibe Methodology
🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Scope:** any skill that runs `git commit` — including `/gvm-build` (per-chunk commits), `/gvm-deploy` (release commits), and the fix-cycle commits produced by `/gvm-code-review`, `/gvm-doc-review`, `/gvm-design-review`, `/gvm-doc-write`. If you are the GVM-skill executor and you are about to invoke `git commit`, include the trailer.

**Do not:** mention the GVM source repository URL in the trailer. The attribution names the methodology only.

### Document footer

Every GVM-produced document (HTML or MD) MUST end with a subtle attribution footer.

**MD format** — append at the end of the file:

```markdown
---

*Developed using the Grounded Vibe Methodology*
```

**HTML format** — append as the last element inside `<main>`, before the closing tag:

```html
<p class="gvm-attribution">Developed using the Grounded Vibe Methodology</p>
```

The `.gvm-attribution` CSS class is defined in `tufte-html-reference.md` and ships with every HTML document — no inline styling is needed. The class produces a small, low-contrast, centred italic line with a top margin that separates it from the document body.

**Scope:** every artefact from every GVM skill. Requirements, test cases, specs, init reports, site-survey reports, build summaries, review reports (doc / code / design / test), doc-write outputs, release notes, scoring reports. Both HTML and MD formats.

**Exclusions:**

- Calibration files (`reviews/calibration.md`) — internal state, not a deliverable.
- Build handovers / prompts (`build/handovers/`, `build/prompts/`) — internal skill plumbing.
- Expert activation CSV, discovered-experts.jsonl, rescore-log.jsonl — internal logs.
- Configuration files (`CLAUDE.md`, `.claude/settings*.json`) — not skill output.

**Do not:** mention the GVM source repository URL in the footer. The attribution names the methodology only.

**Rationale:** the attribution identifies the methodology that shaped the artefact without intruding on the reader's experience or promoting a specific repository. It appears subtly enough to be ignored by casual readers and recognisable by practitioners.

## 27. Surfaced Requirements: promote, never park

A surfaced requirement — a gap in `requirements/requirements.md` discovered during build, code review, doc review, design review, or test — MUST be promoted to `requirements/requirements.md`. It MUST NOT be parked in `STUBS.md`.

**Precondition.** Before presenting the three options below, verify that `requirements/requirements.md` exists. If it does not, the project skipped `/gvm-requirements` and only the third option ("create a new requirements document") is available; tell the user that the source-of-truth file is missing.

**The rule.** When a skill surfaces a requirement gap and the user has agreed to act on it (rule 25, option 2), present the user with three options via `AskUserQuestion`:

- **"Append as acceptance criterion to an existing requirement"** — extend an existing requirement with a new bullet/criterion. Add a changelog entry per rule 11.
- **"Add a new requirement entry"** — introduce a new requirement under the appropriate domain. New ID continues the existing sequence. Add a changelog entry per rule 11.
- **"Create a new requirements document (next round)"** — when the change is substantial enough to warrant a separate round (e.g. `requirements-002.md`). Run `/gvm-requirements` in "New round" mode.

If the user dismisses the question or selects no option, record the finding as `deferred — awaiting triage` in the handover's `Surfaced Requirements` section and re-prompt at the next natural checkpoint (next chunk start, next `/gvm-build` invocation, or `/gvm-status`). Do not silently park it.

The handover's `Surfaced Requirements` section is the staging ground (a record of what was discovered and where), not the destination. The destination is always `requirements/requirements.md`.

**Forbidden:**

- Parking a surfaced requirement in `STUBS.md` under any heading or column. `STUBS.md` tracks code-level placeholders only.
- Inventing IDs like `STUB-SR-NN` or `## Surfaced Requirements` sections inside `STUBS.md`.
- Recording the surfaced requirement only in the handover and never promoting it. The handover is staging; promote the requirement to `requirements/requirements.md` before `/gvm-test-cases` or `/gvm-design-review` consumes it.

**Linking stubs to requirements.** A `STUBS.md` entry MAY include an optional `Requirement` column that names the requirement ID the stub satisfies (e.g. `GS-2`). The link is one-way — from stub to requirement, never the reverse — so `requirements/requirements.md` remains the single source of truth for what the system must do, and `STUBS.md` remains the single source of truth for which placeholders exist in the code.

**Applies to:** every GVM skill that may surface a requirement gap — `/gvm-build`, `/gvm-code-review`, `/gvm-doc-review`, `/gvm-design-review`, `/gvm-test`, `/gvm-test-cases`.

**Why:** `STUBS.md` and `requirements/requirements.md` have different audiences and lifecycles. `requirements/requirements.md` is consumed by `/gvm-test-cases` (acceptance test generation) and `/gvm-design-review` (coverage check). A surfaced requirement parked in `STUBS.md` is invisible to those pipelines and undertested. Each artefact must hide one design decision and expose a stable interface (Parnas, "On the Criteria To Be Used in Decomposing Systems into Modules", 1972: information hiding); mixing requirement records into a stub registry couples decisions that should be independent.

## 28. Review Finding Triage Is User-Owned

28. **Review finding triage is user-owned, not skill-owned.** When a review skill (`/gvm-code-review`, `/gvm-design-review`, `/gvm-doc-review`) emits Critical or Important findings, every emitted finding MUST be presented to the user before any disposition decision. The skill MAY recommend a disposition (fix now / defer with rationale / dismiss as false positive) but MUST NOT decide unilaterally. Rule 25 covers requirement and execution-level silent skips; this rule extends the same principle to review findings, which are a separate artefact class with their own failure mode.

**Required surfacing.** After the synthesise step and before the "next steps" gate, the skill presents findings via `AskUserQuestion` (or an explicit numbered list with the same options when AskUserQuestion is unavailable):
- "Fix now"
- "Defer with rationale" — captured into the review report's Deferred Findings section
- "Dismiss as false positive" — captured into the report with reviewer reasoning
- "I'll decide each one" — surfaces findings one at a time

Minor findings MAY be batched ("12 minor findings — fix all / skip all / let me pick") but each finding still surfaces. None silently drop.

**The Finding Quality Gate is a panel-side emit threshold, not a post-synthesis filter.** Under R2+ strict criterion, panels apply the consumer-impact test BEFORE emitting a finding (the gate keeps the panel's signal-to-noise ratio high). Once a finding is emitted, the synthesis step does not re-apply the gate to suppress it. Filtering by [BORDERLINE] tag is sanctioned (it is the panel's own labelling) — filtering by Claude's post-emit reinterpretation of the gate is not.

**Forbidden:**

- Filing emitted Critical/Important findings as "filtered under R2+ strict" without user input.
- Recording emitted findings as "deferred to v{N}.{M}.{P} hardening" without user input — even when the rationale is technically defensible.
- Bundling a "Verdict: Merge with caveats" with the user's first sight of the finding list. The verdict comes after triage, not before.
- Presenting only a summary count ("12 findings, 8 fixed, 4 deferred") that hides which findings were deferred. (A summary count IS permitted when there are zero deferred findings — "N findings, all fixed" is accurate and hides nothing.)

**Permitted:**

- Recommending disposition per finding alongside the surfaced list ("Recommend defer — pre-existing scope; recommend fix — 1-line edit").
- Pre-fixing trivial findings during a single "fix all" turn the user explicitly authorises. If a NEW Critical or Important finding arises during the fix pass (e.g. a regression introduced by the fix or surfaced by the changed code), the executor MUST pause, surface the new finding, and await a fresh disposition before continuing. The original "fix all" authorisation does not extend to findings discovered during the fix.
- Filtering [BORDERLINE]-tagged findings during R1 synthesis (panels self-labelled them as candidates for filtering — this is panel-side, not Claude-side).

**Applies to:** `/gvm-code-review`, `/gvm-design-review`, `/gvm-doc-review`. Each review skill's Hard Gates section MUST name this rule and its forbidden actions explicitly.

**Why:** review findings are evidence the user paid for. The user's ability to disagree with a panel's emission, or to weigh deferral cost against fix cost, depends on seeing the finding. Filtering or deferring without the user creates a corpus of "things Claude decided didn't matter" that the user has no audit trail for — exactly the failure mode rule 25 prevents at the requirement level. Auto mode reduces interruptions for routine actions; it does not transfer triage authority.
