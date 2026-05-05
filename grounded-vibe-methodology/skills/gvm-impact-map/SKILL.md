---
name: gvm-impact-map
description: Use when discovering goals, actors, impacts, and deliverables for a new project or feature, before requirements gathering. Triggered by /gvm-impact-map command or requests to map impact, identify outcomes, or trace a goal to deliverables. Produces impact-map.md (four linked tables) that downstream /gvm-requirements gates against (IM-4 traceability).
---

# Impact Mapping

## Overview

Discovery skill that produces an `impact-map.md` artefact: four flat tables (Goals, Actors, Impacts, Deliverables) linked by parent-ID columns per discovery ADR-302. The artefact is the single source of truth for downstream traceability — `/gvm-requirements` Phase 5 (IM-4) refuses to finalise any requirement that does not trace to a leaf Deliverable in this file.

Adzic's *Impact Mapping* (Goal → Actor → Impact → Deliverable) is the structural model. Cagan's *Inspired* discovery framing (outcome-first, not output-first) shapes the elicitation order: the practitioner starts from a measurable Goal and works downward.

**Pipeline position:** `/gvm-init` → **`/gvm-impact-map`** → `/gvm-requirements` → `/gvm-test-cases` → `/gvm-tech-spec` → `/gvm-walking-skeleton` → `/gvm-build` → `/gvm-code-review` → `/gvm-test` → `/gvm-explore-test` → `/gvm-deploy`

**Shared rules:** At the start of this skill, load `~/.claude/skills/gvm-design-system/references/shared-rules.md` and follow all rules throughout execution. Load `~/.claude/skills/gvm-design-system/references/expert-scoring.md` when scoring experts.

## Hard Gates

These steps are non-negotiable. If you skip any of them, the impact-map output is invalid.

1. **FOUR-LEVEL TREE VALIDATED BEFORE SAVE.** Every Actor's `Goal-ID` must point at a row in `Goals`; every Impact's `Actor-ID` must point at a row in `Actors`; every Deliverable's `Impact-ID` must point at a row in `Impacts`. This is a foreign-key check (IM-2: implicit-parent rejection). Implementation: `_validator.full_check()` — delivered by P10-C02. If a referential-integrity error fires, the file does NOT save.

2. **GOAL PASSES AMBIGUITY SCAN.** The Goal statement is checked against an extensible denylist of aspirational verbs (IM-3). Hits pass only if a numeric quantity is on the same line. Implementation: `_validator.scan_goal()` against `references/ambiguity-indicators.md` — delivered by P10-C03.

3. **EVERY LEVEL EXPLICIT (NO IMPLICIT PARENTS).** No row may carry a blank parent-ID column. The validator refuses to save the file rather than fabricating parents.

4. **PAIRED MD + HTML BEFORE APPROVAL.** Per cross-cutting ADR-003 (and shared rule 13), every user-facing artefact is written as paired `impact-map.md` + `impact-map.html`. Both files exist before the AskUserQuestion approval prompt fires.

## Expert Panel

Loaded when `/gvm-impact-map` runs. Activations are logged to the activation CSV (per shared rule 1).

| Expert | Work | Role in this skill |
|---|---|---|
| **Gojko Adzic** | *Impact Mapping* | Four-level Goal → Actor → Impact → Deliverable structure. The artefact schema is his model. |
| **Marty Cagan** | *Inspired*, *Empowered* | Outcome-first framing. Goals are measurable user/business outcomes, not feature lists. |
| **Richard Rumelt** | *Good Strategy Bad Strategy*, *The Crux* | Diagnosis discipline. Forces "what is the actual challenge?" before listing actions. |
| **Frederick Brooks** | *The Mythical Man-Month*, *No Silver Bullet* | Conceptual integrity. The four-level structure is enforced consistently across every project. |
| **Edward Tufte** | *The Visual Display of Quantitative Information* | HTML rendering: data-rich, low-chrome, paired with the shared Tufte CSS shell. |

Domain and stack specialists are not loaded by this skill — impact mapping is technology-agnostic. Stack specialists activate downstream in `/gvm-tech-spec`.

## Process Flow

```
0. BOOTSTRAP
   ├── Verify ~/.claude/gvm/ exists (shared rule 14)
   ├── Verify the project root is writable
   └── Load expert references (architecture-specialists.md only — no domain/stack at this stage)

1. DISCOVERY  (P10-C04)
   ├── AskUserQuestion: "What outcome are you trying to move? (one measurable metric)"
   ├── Practitioner replies — skill drafts the G-1 row
   └── Validate via _validator.scan_goal() — Hard Gate 2

2. ACTORS  (P10-C04)
   ├── AskUserQuestion: "Whose behaviour change moves G-1?"
   ├── Practitioner replies — skill drafts A-N rows (1..5)
   └── Each Actor row gets Goal-ID = G-1

3. IMPACTS  (P10-C04, per actor)
   ├── AskUserQuestion: "What behavioural change in [Actor.name] moves G-1?"
   └── Practitioner replies — skill drafts I-N rows (1..3 per actor)

4. DELIVERABLES  (P10-C04, per impact)
   ├── AskUserQuestion: "What deliverable enables that impact?"
   └── Practitioner replies — skill drafts D-N rows (1..N per impact)

5. VALIDATION  (P10-C02)
   ├── Run _validator.full_check()
   │   ├── implicit-parent foreign-key check (IM-2 — Hard Gate 1)
   │   ├── Goal ambiguity scan (IM-3 — Hard Gate 2)
   │   └── schema_version present
   └── If errors: report each, practitioner edits, repeat

6. APPROVAL
   ├── Write paired impact-map.md and impact-map.html (Hard Gate 4)
   └── AskUserQuestion: "Approve?"
```

The Process Flow above is the contract. P10-C04 delivers the AskUserQuestion-driven elicitation that walks a practitioner through Phases 1–4. P10-C02 delivers the validator behind Phase 5. P10-C03 ships the ambiguity word list and scan logic.

## Phase Details

### Phase 0 — Bootstrap

Pre-flight per shared rule 14. Refuse to run if the GVM home directory is missing — direct the user to `/gvm-init`.

### Phase 1 — Discovery

Elicit one Goal at a time. The practitioner may declare multiple Goals, but each Goal flows through the same elicitation cycle (Phases 1 → 5) before another Goal begins. This keeps the four-level tree simple per Goal and avoids cross-Goal interference during validation.

A Goal row carries: `ID` (`G-N`), `Statement`, `Metric`, `Target`, `Deadline` (ISO-8601 or empty). The ambiguity scan (Hard Gate 2) runs against `Statement + Metric + Target` combined per discovery ADR-303.

**Elicitation pattern.** Three-step sequence; each step is a separate AskUserQuestion:

1. *Outcome statement.* "What outcome are you trying to move? Outcomes are measurable changes in user or business behaviour, not features." Options: "Single measurable metric (e.g., +20% WAU in 6 months)", "Multiple outcomes — pick the first to map", "Reuse existing impact-map.md".
2. *Metric and target.* "What numeric metric and target value will you measure?" Options: examples like "Weekly Active Users / +20%", "p95 latency / under 200ms", "Trial-to-paid conversion / 8%". The practitioner may free-text. **The Goal row is NOT drafted until the practitioner supplies both a non-empty Metric AND a non-empty Target.** A blank Metric or Target is rejected with a follow-up AskUserQuestion that re-asks for the missing field; do not advance to Phase 2 with either column empty.
3. *Deadline.* "By when must this outcome land? (ISO-8601 date, or 'no fixed date')." Optional; leave blank if the practitioner declines.

After all three replies are in hand, draft the `G-1` row (Statement, Metric, Target, Deadline) into the working buffer and confirm with a final AskUserQuestion ("Approve this Goal row, edit a field, or restart?"). Then run `_ambiguity_scan.scan_goal(...)` against the draft. On any IM-3 hit, present the disqualifying word(s) and loop back to step 1 — do NOT save the row until the scan returns no errors AND both Metric and Target are non-empty. The Metric/Target check is mechanical (string length > 0) and runs BEFORE the ambiguity scan; the ambiguity scan alone cannot catch a verb-only goal whose Statement, Metric, and Target are all empty (combined text is empty → no denylist hits → scan passes vacuously).

### Phase 2 — Actors

For the current Goal, elicit 1..5 Actors. Each Actor carries: `ID` (`A-N`), `Goal-ID` (foreign key into Goals), `Name`, `Description`. The cardinality cap (5) is a soft guideline; the skill warns above 5 but does not refuse.

**Elicitation pattern.** AskUserQuestion: "Whose behaviour change moves Goal G-1?" with options seeding common patterns (`Buyer`, `Seller`, `Operator`, `Internal user`) — the practitioner may add their own via the free-text fallback. Repeat until the practitioner declines to add another Actor. After the fifth Actor, surface a warning ("You've named 5 Actors — Adzic recommends ≤ 5 per Goal to keep the impact map navigable") but accept the next addition. Refusal would block legitimate complex domains; the warning is sufficient.

### Phase 3 — Impacts

For each Actor, elicit 1..3 behavioural changes. An Impact row carries: `ID` (`I-N`), `Actor-ID`, `Behavioural change`, `Direction` (`+` or `-`). The Direction column captures whether the desired change is an increase or a decrease in the behaviour.

**Elicitation pattern.** Loop over each Actor `A-k` in order. For each, dispatch one AskUserQuestion: "What behavioural change in [Actor.name] moves Goal G-1?" Options include direction-paired examples (`Increase return-visit frequency`, `Decrease abandonment at search step`, `Increase save-to-shortlist actions`) plus free-text. The agent infers `Direction` from the verb (`increase` → `+`, `decrease` / `reduce` → `-`); when ambiguous, ask a follow-up AskUserQuestion with `+` and `-` as the two options.

### Phase 4 — Deliverables

For each Impact, elicit 1..N Deliverables (no upper cap). A Deliverable row carries: `ID` (`D-N`), `Impact-ID`, `Title`, `Type` (`feature`, `content`, `process`, `tool`), and an optional `risks` column (per discovery ADR-310).

**Elicitation pattern.** Loop over each Impact `I-k`. For each, dispatch one AskUserQuestion: "What deliverable enables Impact [I-k.behavioural-change]?" Options: `feature`, `content`, `process`, `tool` (the four `Type` enum values), plus free-text for the title. The `risks` column is left blank during P10-C04; P10-C09 wires the persona/Actor-coupled trace generation that populates it.

### Phase 5 — Validation

Run `_validator.full_check(path)` (P10-C02 + P10-C03). The function returns `(impact_map, errors)` where `impact_map` is `ImpactMap | None` and `errors` is `list[ValidationError]`. On a non-empty `errors` list, walk the errors and present each `code: message` to the practitioner — the IDs in the message (e.g., `Goal G-1`, `Actor A-3`) anchor the fix. The skill loops back into Phase 5 (re-validate) after each correction; do not advance to Phase 6 until the validator returns an empty error list.

**`impact_map is None` branch.** When parsing fails outright (malformed Markdown, unknown column header, missing schema_version), `impact_map` is `None` and `errors` carries the parse failure. In that case do NOT navigate by row ID — present the raw `errors` list and ask the practitioner to fix file-level syntax (e.g., column header typos, broken table separators) before re-running validation.

For each error class, dispatch a targeted AskUserQuestion rather than re-running the whole elicitation: an `IM-2` orphan-Actor error becomes "Actor A-3 has no Impacts — add one or remove the Actor"; an `IM-3` ambiguity error becomes "Goal G-1 uses 'launch' without a numeric target — rephrase or add a quantity".

### Phase 6 — Approval

Write paired `impact-map.md` + `impact-map.html` (Hard Gate 4). The HTML embeds the Tufte CSS shell from `~/.claude/skills/gvm-design-system/references/tufte-html-reference.md` (per cross-cutting ADR-003). Then AskUserQuestion: "Approve impact-map.md and impact-map.html?" with options `Approve`, `Edit a row`, `Reject and restart`. On approve: append a Changelog row carrying today's ISO date, the change summary, and the rationale. The artefact is then consumable by `/gvm-requirements`.

### Phase 7 — Mid-flight edits (deferred to P10-C08)

`/gvm-requirements` may dispatch a mid-flight edit back into `/gvm-impact-map` per IM-5 (discovery ADR-305). The atomic-append handler is delivered by P10-C08; the skeleton hook in this scaffold is a placeholder.

## Key Rules

1. **Outcome before output.** A Goal is a measurable user or business outcome (Cagan). It is never a feature list. The ambiguity scan (Hard Gate 2) enforces this by rejecting verb-only goals like "launch the mobile app".

2. **Four levels only.** Goals → Actors → Impacts → Deliverables. No nesting beyond this — additional structure goes into `/gvm-requirements` as personas, scenarios, or acceptance criteria.

3. **Flat tables, parent-ID linked.** Per discovery ADR-302, the artefact is four flat tables. Nested YAML/tree formats are forbidden — they are hostile to git diffs and to mechanical validation.

4. **No implicit parents.** Every row must declare its parent. The validator refuses to save a file with blank parent-IDs (Hard Gate 3) rather than guessing.

5. **Paired HTML + MD, always.** Per shared rule 13 and cross-cutting ADR-003, every approval writes both files. The HTML rendering reconstructs the tree visually; the MD remains the canonical machine-readable source.

6. **Project-extensible ambiguity list.** The default denylist ships in `references/ambiguity-indicators.md` (delivered by P10-C03). Projects may override via `.gvm-impact-map.allowlist` and `.gvm-impact-map.denylist` at the project root.

7. **Mid-flight edits route through `/gvm-requirements`.** When `/gvm-requirements` is running, the practitioner adds new Impacts via that skill's intent-classifier handler (IM-5), not by re-invoking `/gvm-impact-map` from scratch. The atomic append (P10-C08) preserves the four-level invariant.

8. **Hand off to `/gvm-requirements`.** When the impact-map is approved, direct the user to run `/gvm-requirements` next. The IM-4 Phase 5 gate (P10-C05) will refuse to finalise any requirement that does not trace to a leaf Deliverable in this file.
