---
name: gvm-status
description: Use when the user wants to know where they are in the GVM pipeline, what phases are complete, what's next, or the overall health of their project's methodology state. Triggered by /gvm-status command or questions like "where am I?", "what's done?", "what's next?".
---

# Pipeline Status

Shows where the user is in the GVM pipeline. Checks file system artefacts, detects staleness, queries the expert activation log, and presents a clear "you are here" view. Grounded in Nielsen's visibility of system status heuristic.

This skill produces conversational output only — no HTML/MD documents. It reads state; it changes nothing.

**Shared rules:** At the start of this skill, load `~/.claude/skills/gvm-design-system/references/shared-rules.md`. This is a diagnostic skill — no expert grounding applies (per shared rule 7).

## Data Sources

### 1. Artefact Detection

Check for the existence of output files from each pipeline phase. A phase is **complete** if its primary output files exist. A phase is **in progress** if its directory exists but primary outputs are missing or partial.

| Phase | Directory | Primary Artefacts | Complete When |
|-------|-----------|-------------------|---------------|
| Init | `init/` | `init-*.html` + `init-*.md` | At least one paired set exists |
| Requirements | `requirements/` | `requirements.html` + `requirements.md` | Both files exist |
| Test Cases | `test-cases/` | `test-cases.html` + `test-cases.md` | Both files exist |
| Tech Spec | `specs/` | `implementation-guide.md` + at least one domain spec | Implementation guide exists |
| Build | `build/` | `build/handovers/` directory with chunk files | At least one handover file exists |
| Code Review | `code-review/` | `code-review-*.html` | At least one HTML file exists (review reports are HTML-only per shared rule 13) |
| Test | `test/` | `test-*.html` | At least one HTML file exists (review reports are HTML-only per shared rule 13). **Verdict-aware reporting (post-v2.0.0 hardening):** read the highest-numbered `test-*.html` and extract the verdict from its `.verdict-text` element (one of `Ship-ready`/`Demo-ready`/`Not shippable`). Report it prominently in the status output. A "Test phase complete" line without the verdict is incomplete — the file existence proves a run happened, the verdict tells the user whether the build is shippable. |
| Design Review | `design-review/` | `design-review-*.html` | At least one HTML file exists (review reports are HTML-only per shared rule 13) |
| Site Survey | `site-survey/` | `site-survey-*.html` + `site-survey-*.md` | At least one paired set exists |
| Doc Write | `docs/`, root | `README.md`, `docs/*.html` | `README.md` exists |
| Deploy | root | `RELEASE-NOTES.html`, git tag | `RELEASE-NOTES.html` exists and `git tag -l 'v*'` has entries |

**Alternative entry:** If `site-survey/` exists with artefacts, the project entered via `/gvm-site-survey` instead of `/gvm-init`.

**Doc reviews:** Check `doc-review/` for any review artefacts — these are quality gates, not pipeline phases, so show them separately.

### 2. Staleness Detection

Compare modification timestamps of upstream vs downstream artefacts. Flag when upstream has changed after downstream was generated:

- `requirements.md` newer than `test-cases.md` → test cases may be stale
- `requirements.md` newer than specs → specs may be stale
- `test-cases.md` newer than specs → specs may be stale
- Spec files newer than build handovers → build may be against outdated specs

Use the cross-platform timestamp command from shared rule 19 to compare timestamps. Only flag staleness for phases that have actually been completed — don't flag missing downstream artefacts as "stale".

**Changelog-aware staleness:** When an upstream artefact has a Changelog section, read it to provide specific guidance:
- "requirements.md changed RE-3 priority on 2026-03-29 — test-cases.md and specs may need update" is more actionable than "requirements.md is newer than test-cases.md"
- If the Changelog identifies which IDs changed, name them in the staleness report

### 3. Requirements Rounds

Scan `requirements/` for numbered artefacts:
- `requirements.md` = round 1
- `requirements-002.md` = round 2, etc.

Report which round is current and list all rounds with creation dates. For each round, check whether corresponding downstream artefacts exist:
- Round 2 requirements exist but no `test-cases-002.md` → "Round 2: test cases not yet generated"
- Round 2 requirements and test cases exist but no `specs-002/` → "Round 2: specs not yet generated"

### 4. Changelog Summary

Read Changelog sections from the most recent version of each pipeline artefact. Collect all entries, sort by date, and present the 5 most recent:

```
Recent changes
--------------
2026-03-29  requirements.md    Changed RE-3 priority SHOULD→MUST
2026-03-28  requirements-002   Created: voice search (R2-VS-1 through R2-VS-8)
2026-03-27  cross-cutting.md   ADR-003 superseded by ADR-012 (Redis→Valkey)
```

If no changelogs exist in any artefact, skip this section silently.

### 5. Expert Activation Log

Read `~/.claude/gvm/expert-activations.csv` and filter rows where `project` matches the basename of the current working directory.

Summarise:
- Total experts loaded and cited, grouped by skill
- Expert tier breakdown (Tier 1 / 2a / 2b / discovered)
- Classification breakdown (Canonical / Established / Recognised / Emerging / Provisional)
- Most-cited experts (top 5 by `cited` event count)

If the CSV doesn't exist or has no rows for this project, say so — it means no GVM skills have been run yet.

### 6. Methodology-changelog inclusion heuristic (NFR-3)

When `methodology-changelog.md` exists at the project root, read the most recent dated entry and surface it in a new **Methodology** section of the status report alongside the existing pipeline-state report. Recency is determined by the highest `## v{MAJOR}.{MINOR}.{PATCH} — {YYYY-MM-DD}` header in the file (line-anchored; in-prose mentions of a version string do not count).

For the most recent entry, surface the three audit fields named verbatim in the changelog header — **rule reference**, **defect class addressed**, and **validation method** — per spec § Component 5. The labels match the per-entry sub-bullets in `methodology-changelog.md` so a reader can navigate from the status report straight to the source entry.

This subsection is **read-only** — no enforcement, no refusal. When `methodology-changelog.md` is absent (the project has not adopted the methodology audit trail), skip the Methodology section silently. When the file is present but contains no `## v{...}` dated headers (e.g. only the preamble has been written, no release entries yet), skip the Methodology section and surface a single one-line note: "methodology-changelog.md found but contains no versioned entries." Refusal lives in the skills that own each gate; `/gvm-status` reports.

### 7. Build Progress (when in build phase)

If `specs/implementation-guide.md` exists, parse it for the full build picture:

1. **Parse the implementation guide** for all phase/chunk IDs (`P{X}-C{XX}`) and the dependency matrix (which chunks depend on which).
2. **Cross-reference against file system state:**
   - `build/handovers/P{X}-C{XX}.md` exists → chunk is **done**
   - `build/prompts/P{X}-C{XX}.md` exists but no handover → chunk is **started but not complete**
   - Neither exists → chunk is **pending**
3. **Classify pending chunks by readiness:**
   - A pending chunk is **ready** if all its dependency chunks have handover files
   - A pending chunk is **blocked** if any dependency chunk is not yet done
4. **Identify parallelisable work** — ready chunks with no dependencies on each other can be built in parallel.

**Present the dependency graph visually:**

```
Build Progress: 3/8 chunks complete

Phase 1
  [done] P1-C01  Project setup
  [done] P1-C02  Database schema          (depends on: P1-C01)
  [done] P1-C03  API framework            (depends on: P1-C01)

Phase 2
  [ready]  P2-C01  Auth endpoints         (depends on: P1-C02, P1-C03)
  [ready]  P2-C02  Search service         (depends on: P1-C02) ← parallel with P2-C01
  [blocked] P2-C03  Search API            (depends on: P2-C01, P2-C02)

Phase 3
  [blocked] P3-C01  Frontend shell        (depends on: P2-C01)
  [blocked] P3-C02  Search UI             (depends on: P2-C03, P3-C01)

Next: P2-C01 and P2-C02 are both ready and can be built in parallel.
```

Mark each chunk with its status (`[done]`, `[ready]`, `[blocked]`), its dependencies, and flag which ready chunks can run in parallel.

## Output Format

Present status conversationally with clear visual structure. Use a pipeline diagram showing completed, current, and upcoming phases.

**Example output:**

Legend: `[done]` = complete, `[partial]` = directory exists but primary artefacts missing or incomplete, `[ ]` = not yet started.

```
Project: example-app

Pipeline (Round 1)
------------------
[done]  /gvm-init         — init/init-001 (2026-03-20)
[done]  /gvm-requirements — requirements/requirements.md (2026-03-21)
[done]  /gvm-test-cases   — test-cases/test-cases.md (2026-03-22)
[done]  /gvm-tech-spec    — 4 domain specs + implementation guide (2026-03-23)
[done]  /gvm-build        — 8/8 chunks complete (2026-03-25)
[done]  /gvm-code-review  — code-review-001 (2026-03-26)
[done]  /gvm-test         — test-001 (2026-03-26)

Pipeline (Round 2)
------------------
[done]  /gvm-requirements — requirements/requirements-002.md (2026-03-28)
[ ]     /gvm-test-cases
[ ]     /gvm-tech-spec

Recent changes
--------------
2026-03-29  requirements.md    Changed RE-3 priority SHOULD→MUST
2026-03-28  requirements-002   Created: voice search (R2-VS-1 through R2-VS-8)

Staleness
---------
⚠ requirements.md changed RE-3 on 2026-03-29 — test-cases.md and specs may need update

Quality gates
-------------
doc-review/requirements-review-2026-03-22.html — requirements review (2026-03-22)
test/test-008.html — Ship-ready (latest verdict, 2026-04-28)
chain status: build → code-review (R50) → test (Ship-ready) ✓

Experts (this project)
----------------------
18 loaded across 4 phases, 11 cited in output
Tier 1: 6 | Tier 2a: 5 | Tier 2b: 4 | Discovered: 3
Top cited: Wiegers (5), Bass (3), Kleppmann (3), Cohn (2), Nygard (2)
```

Adapt the output to what actually exists. If only one round exists, show a single pipeline section without the "Round 1" label. If nothing has been run, say so and suggest `/gvm-requirements` or `/gvm-site-survey` as entry points. Show recent changes only if changelogs exist.

## Process

1. Get the project name from `basename` of cwd
2. Run artefact detection checks (use Bash for file existence checks (`test -f`, `ls`) and `python3` for timestamps (per shared rule 19), Glob for file patterns)
3. Detect requirements rounds (scan `requirements/` for numbered files)
4. Run staleness checks if multiple phases are complete (changelog-aware if changelogs exist). Using the rounds identified in step 3, run staleness checks per round — each round's requirements artefact is checked against its corresponding downstream artefacts.
5. Read changelog sections from recent artefacts (if they exist)
6. Read and summarise activation log if it exists
7. If build phase is active, parse build progress
8. **Verdict + chain reporting (post-v2.0.0 hardening).** When `test/` contains at least one `test-*.html`:
   a. Read the highest-numbered file. Extract the verdict text from the `<p class="verdict-text">` element (regex `<p class="verdict-text">\s*([^<]+?)\s*</p>` is sufficient; the contents are one of `Ship-ready` / `Demo-ready` / `Not shippable`).
   b. Surface the verdict in the **Quality gates** section as `test/test-NNN.html — {verdict} (latest verdict, {date})`.
   c. Compute a **chain status** line that lists the canonical pipeline gates and their freshness: `build → code-review → test`. A gate is ✓ when its artefact exists AND is newer than the upstream gate's artefact (or there is no upstream). Use the latest commit SHA on each gate's artefact directory if available; otherwise modification time.
   d. Annotate the chain when `test` verdict is non-Ship-ready: `chain status: build → code-review (R{N}) → test (Demo-ready) ⚠ verdict below Ship-ready`.
   e. When a gate is missing (e.g. `code-review/` empty but `test/` has artefacts), the chain shows `→ code-review (skipped) →` and the line ends `⚠ gate skipped`.
   The verdict is read-only — `/gvm-status` does not enforce or refuse anything; it reports. Refusal lives in the skills that own each gate (e.g. `/gvm-deploy` Hard Gate 1 reads the verdict and refuses to tag if the verdict isn't Ship-ready). The post-v2.0.0 lesson: surfacing the verdict prominently in `/gvm-status` makes "is this shippable?" a one-glance answer, not a hunt through review reports.
8. Present the combined status view

Run the file system checks in parallel where possible — they're all independent reads.

## Key Rules

1. **Read-only** — this skill never creates, modifies, or deletes anything
2. **No expert grounding** — this is a diagnostic tool, not a decision-making skill (per shared rule 7: when not to ground)
3. **Fast** — minimise tool calls, parallelise checks, no unnecessary reads
4. **Honest** — if artefacts exist but look incomplete (e.g., empty files, missing paired MD), say so
5. **Actionable** — always end with what the user should do next
