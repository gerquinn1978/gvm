---
name: gvm-experts
description: Use when the user wants to score, rescore, or manage experts in the GVM roster. Triggered by /gvm-experts command, requests to score experts in a reference file, rescore an expert, evaluate expert authority, add experts, or score all industry domain experts.
---

# Expert Management

Score, rescore, discover, and manage experts in the GVM roster. This is the user-facing skill for expert roster operations — the expert reference files and scoring methodology live in the design system (`~/.claude/skills/gvm-design-system/references/`), and this skill provides the interface for working with them.

This skill manages the expert roster. It does not load experts for pipeline execution — that happens automatically in the skills that use them.

**Shared rules:** At the start of this skill, load `~/.claude/skills/gvm-design-system/references/shared-rules.md` and follow all rules throughout execution. Load `~/.claude/skills/gvm-design-system/references/expert-scoring.md` when scoring experts.

## When to Use

- Score unscored experts in a reference file
- Rescore a specific expert after new information
- Rescore all experts in a file
- Score all industry domain files at once
- Add a new expert to a reference file
- Review expert utilisation data from the activation log

## Operations

Before any scoring operation: Bootstrap GVM home directory per shared rule 14.

When `/gvm-experts` is invoked, load `~/.claude/skills/gvm-design-system/references/expert-scoring.md` and present the user with options via AskUserQuestion:

**1. Score experts in a reference file**
- Ask which file (list available files in `~/.claude/skills/gvm-design-system/references/industry/` and `~/.claude/skills/gvm-design-system/references/`)
- Follow the scoring process in `expert-scoring.md`
- Follow the Batch Scoring Protocol below

**2. Rescore a specific expert**
- Ask which expert (or accept the name if provided)
- Follow the rescore process in `expert-scoring.md`
- Append a record to `~/.claude/gvm/rescore-log.jsonl` so the rescore survives plugin updates

**3. Rescore all experts in a file**
- Ask which file
- Follow the rescore process for each expert sequentially
- Append a record to `~/.claude/gvm/rescore-log.jsonl` for each rescored expert
- Follow the Batch Scoring Protocol below

**4. Score all unscored experts**
- Ask scope via AskUserQuestion: "All files" or "Industry domain files only"
- All files: scan all reference files for experts without score tables
- Industry only: iterate through `~/.claude/skills/gvm-design-system/references/industry/`
- Follow the Batch Scoring Protocol below — process one file at a time, persist before moving to the next. If the protocol stops on an error for a given file, report which file failed and which files remain unscored. Offer: "Resume from next file" or "Abort."

**5. Add a new expert to a reference file**
- Ask which file and which expert (name, work, publisher, year)
- Follow the Expert Discovery and Persistence Process in `shared-rules.md`

**6. Review utilisation data**
- Read `~/.claude/gvm/expert-activations.csv`
- If the file doesn't exist or has no rows, report "No activation data — no GVM skills have been run yet" and exit the operation
- Filter by project (or show all projects)
- Summarise: experts loaded vs cited, tier breakdown, classification breakdown, top-cited experts
- Flag divergence signals per the utilisation feedback thresholds in `expert-scoring.md`

## Batch Scoring Protocol

Scoring must be chunked to stay within context limits and keep each agent's task focused (Fagan: rate of review matters — overloaded reviewers produce lower quality assessments).

### Chunk sizing (Fairbanks: risk-proportional ceremony)

| Scope | Chunk size | Approach |
|-------|-----------|----------|
| 1-3 experts | Score inline | No agents needed — score and verify in the main context |
| 4-8 experts (one file) | 1 primary agent + 1 verification agent | Dispatch both for the file, compare, persist |
| 9+ experts (one file) | Split into groups of ≤8 | One primary + one verification agent per group, persist after each group |
| Multiple files | Process one file at a time | Complete scoring + verification + persistence for file N before starting file N+1 |
| All files ("score everything") | Process sequentially by file | Never dispatch all files in parallel — too many agents, context exhaustion, permission failures |

### Per-file flow

```
1. READ — scan the file for unscored experts (no "Expert score:" table after Source line)
2. COUNT — if 0 unscored, skip with "All experts in [file] are scored"
3. CHUNK — if >8 unscored, split into groups of ≤8
4. For each chunk:
   a. DISPATCH primary scoring agent (model: sonnet) with expert names, works, and scoring methodology
   b. DISPATCH verification agent (model: sonnet) with expert names and works ONLY — no primary scores
   c. COMPARE — check convergence (within 1 point on all dimensions → average; 2+ divergence → flag to user)
   d. PERSIST — write averaged scores to the reference file using a Python script via Bash
      (the files are in ~/.claude/skills/ which requires Bash for writes, not the Edit tool)
   e. VERIFY — run `grep -c 'Expert score:' {file}` and verify the count matches the number of experts that were scored. A count of 0 means no score tables were written. Before retrying: check `test -w ~/.claude/skills/gvm-design-system/references/ && echo writable`. If not writable, report the permission issue — a retry will also fail. If writable: report the write failure to the user and retry the Python script once. If the retry fails, stop scoring this file, present the error to the user. Record the partial state: parse the `grep -c 'Expert score:' {file}` result to determine how many experts in this chunk had their score tables written (N), and report the partial count in the failure message: "Write failure in {file}. Expected {M} experts scored in this chunk; verify pass found {N} score tables — {M - N} may be missing or malformed. Manually verify the file before continuing." Offer: "Skip this file and continue to the next" or "Abort scoring." On skip, proceed to step 6 (NEXT) — the partial count is already in the user-facing message; do not attempt to repair silently.
5. REPORT — show the file's roster summary (see Roster Summary View below)
6. NEXT — proceed to next file or chunk
```

### Why sequential by file

- Each file is self-contained — no cross-file dependencies during scoring
- Persisting after each file means progress is saved even if the session ends
- Parallel dispatch of many files creates 18+ simultaneous agents that exhaust context and hit permission failures
- Sequential processing lets the user see progress file by file and catch issues early (Deming: short feedback loops)

## Roster Summary View

Every scoring operation must end with a roster summary — the user should see the full picture, not just the last expert scored (Doumont: answer "so what?" at every level).

### After scoring a single file

Show a table for that file:

```markdown
## [File Name]

| Expert | Expert Avg | Classification | Top Work | Work Class | Utilisation |
|--------|-----------|---------------|----------|-----------|-------------|
| Martin Fowler | 5.0 | **Canonical** | *PoEAA* | Established (4.25) | No data |
| Steve McConnell | 4.4 | **Established** | *Code Complete* | Established (4.0) | No data |
| Boris Beizer | 3.0 | **Recognised** | *Testing Techniques* | Established (3.75) | cite rate 85% ⬆ |
```

- Sort by expert average descending (highest-classified first)
- **Top Work** = the highest-classified work for that expert
- **Utilisation** column shows:
  - `No data` — if `~/.claude/gvm/expert-activations.csv` doesn't exist or has <3 activations for that expert
  - `cite rate X%` — if data exists with sufficient sample size (n≥3)
  - `⬆` — upward divergence signal (cite rate >80%, classification Recognised or below)
  - `⬇` — downward divergence signal (cite rate <40%, classification Established or above)
  - `(n=X)` — sample size tier indicator for preliminary signals (n=3-9)

### After scoring multiple files ("score all")

Show the per-file table for each file as it completes, then a grand summary at the end:

```markdown
## Grand Summary

| Classification | Count | % |
|---------------|-------|---|
| Canonical | X | X% |
| Established | X | X% |
| Recognised | X | X% |
| Emerging | X | X% |

**Flags:**
- [Expert] scored Emerging — [reason, e.g., no verifiable publications]
- [Expert] work outscores expert by 1+ band — [reason]
- [Expert] has ⬆ utilisation signal — may be underclassified
```

The grand summary surfaces the information the user needs to act on (Doumont: structure by message — lead with what matters).

## Reference Files

This skill reads and writes files owned by the design system:

- `~/.claude/skills/gvm-design-system/references/expert-scoring.md` — scoring methodology
- `~/.claude/skills/gvm-design-system/references/shared-rules.md` — shared rules including discovery process
- `~/.claude/skills/gvm-design-system/references/architecture-specialists.md` — Tier 1
- `~/.claude/skills/gvm-design-system/references/domain-specialists.md` — Tier 2a
- `~/.claude/skills/gvm-design-system/references/stack-specialists.md` — Tier 3 index
- `~/.claude/skills/gvm-design-system/references/stack/*.md` — Tier 3 per-stack files
- `~/.claude/skills/gvm-design-system/references/industry/*.md` — Tier 2b
- `~/.claude/skills/gvm-design-system/references/writing-expert-scoring.md` — writing experts' scoring record (scoring tables previously inline in `writing-reference.md` — split out so `writing-reference.md` stays lean at document-write time)
- `~/.claude/gvm/expert-activations.csv` — activation log
- `~/.claude/gvm/discovered-experts.jsonl` — discovered experts (survives plugin updates)
- `~/.claude/gvm/rescore-log.jsonl` — user-initiated rescores (survives plugin updates)

## Key Rules

1. **Scoring is the primary operation** — most invocations will be scoring or rescoring. Make it fast.
2. **Independent verification** — every scoring operation uses a second agent for verification, per `expert-scoring.md`.
3. **Persist per file, not per batch** — scores are written to reference files as soon as that file's scoring + verification is complete. Never accumulate unpersisted scores across multiple files.
4. **Chunk to stay focused** — never send more than 8 experts to a single scoring agent. Overloaded agents produce lower-quality assessments (Fagan: rate of review). For "score everything" operations, process one file at a time.
5. **Utilisation feedback is advisory** — divergence signals inform review, they don't auto-reclassify.
6. **Always end with a roster summary** — every scoring operation finishes by showing the Roster Summary View. The user should see classifications, not just confirmation that files were edited.
7. **Persist via Bash** — reference files live in `~/.claude/skills/` which is outside the working directory sandbox. Use Python scripts via Bash to insert score tables, not the Edit tool. Verify insertions with grep after writing.
8. **Sequential for reliability, parallel within a file** — process files sequentially (score → verify → persist → next file). Within a single file, the primary and verification agents can run in parallel.
