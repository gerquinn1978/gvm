# Shared Rules — Operational Detail

Loaded on demand by specific skills, not on every invocation. The core rules are in `shared-rules.md`.

## Rule 14 Detail: Home Directory File Schemas and Lifecycle

**Directory contents:**

| File | Purpose | Format |
|------|---------|--------|
| `docs/plugin-guide.html` | User guide — how to use the GVM plugin | HTML, copied from plugin on bootstrap |
| `expert-activations.csv` | Activation log — experts loaded and cited per project | CSV, append-only |
| `discovered-experts.jsonl` | Experts discovered during pipeline runs | JSONL, append-only |
| `rescore-log.jsonl` | User-initiated rescores overriding canonical scores | JSONL, append-only |

**Discovered experts (`discovered-experts.jsonl`) schema:**

```json
{"schema_version":1,"timestamp":"2026-03-25T14:32:00Z","project":"example-app","expert":"Jane Smith","work":"Domain Modelling for Financial Systems","publisher":"O'Reilly","year":2024,"file":"industry/fintech.md","classification":"Recognised","expert_avg":3.2,"scored_by":"gvm-requirements"}
```

**Rescore log (`rescore-log.jsonl`) schema:**

```json
{"schema_version":1,"timestamp":"2026-03-26T10:15:00Z","expert":"Martin Fowler","file":"architecture-specialists.md","old_classification":"Canonical","new_classification":"Canonical","old_avg":5.0,"new_avg":4.8,"reason":"User-initiated rescore after review","scored_by":"gvm-experts"}
```

**Re-insertion lifecycle** (runs when any write-capable skill loads a reference file during rules 4 or 5):

1. Read the reference file as normal.
2. Check `~/.claude/gvm/discovered-experts.jsonl` for experts targeting that file. If any are missing, re-insert with recorded scores.
3. Check `~/.claude/gvm/rescore-log.jsonl` for rescored experts. If the plugin ships a score that the user has rescored, apply the user's most recent rescore (user judgement takes precedence).

If neither file exists or has no relevant entries, proceed — no action needed.

**Migration:** If `~/.claude/skills/gvm-design-system/expert-activations.csv` exists but `~/.claude/gvm/expert-activations.csv` does not, the bootstrap script (`scripts/gvm-bootstrap.py`) moves (not copies) the old file to the new location automatically. No manual action required.

**Self-heal of clobbered activation log:** if `~/.claude/gvm/expert-activations.csv` exists but the first line is not the canonical header (the file was overwritten by an external process — e.g., `git init` reset, a script that used `>` instead of `>>`, or a copy-paste of the old shell-snippet bootstrap's right-hand side), both `gvm-bootstrap.py` and `log-expert.py` atomically prepend the canonical header on next invocation. Existing rows are preserved; the log resumes accumulating new rows on the next skill invocation. No manual recovery is required.

## Rule 21 Detail: Build Check Promotion Procedure

**Promotion procedure (runs after the calibration update step in each review skill):**

1. Scan the Recurring Findings section of `calibration.md`.
2. For each recurring finding, count consecutive rounds. If count >= 3 and no existing build check covers it, promote.
3. Scan Resolved Findings for any finding that was resolved but reappeared in Recurring. If found and no existing build check covers it, promote.
4. For each promoted finding:
   - Assign the next `BC-{NNN}` ID (sequential, zero-padded, never reused).
   - Rewrite as a root cause pattern (what to avoid), not a symptom instance.
   - Record the originating expert, finding IDs, rounds, and promotion reason (systemic or regression).
   - Append to Active Checks in `reviews/build-checks.md`. Create the file if it does not exist.
   - Update `calibration.md` Recurring Findings: "Promoted to build check BC-{NNN}."
   - Record `tier: 1` or `tier: 2` per the tier definitions in rule 21.
5. For each active build check, if any current-round finding matches it, update "Last triggered" to the current round.

**Retirement (runs after promotion):**

Tier 1 checks are never retired. For tier 2: if `current_round - last_triggered_round >= 3`, present to the user via AskUserQuestion: "Build check BC-{NNN} ({description}) has not triggered in 3 rounds. Retire it?" If confirmed, set status to `retired`. Retired checks remain as historical records but are not loaded by `/gvm-build`.

**Build consumption (in `/gvm-build`):**

- Step 4 (GENERATE PROMPT): if `reviews/build-checks.md` exists, load Active Checks. Filter by review type (code → all code chunks, design → architecture chunks, doc → documentation chunks). Include under `## Known Patterns to Avoid`.
- Step 5d (SELF-REVIEW LOOP): review against active build checks alongside expert principles.
- If the file does not exist, omit.
