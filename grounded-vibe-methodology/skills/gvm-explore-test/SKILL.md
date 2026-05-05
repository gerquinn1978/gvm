---
name: gvm-explore-test
description: Use when running a timeboxed exploratory testing charter against built code, before doc-write. Triggered by /gvm-explore-test command or requests to run an exploratory tour, log defects in GWT form, or produce an explore-NNN session report. Writes a charter, drives AskUserQuestion-based defect intake, and produces paired test/explore-NNN.md + .html that /gvm-test reads via VV-4(d).
---

# Explore Test

## Overview

Practitioner-driven exploratory testing skill. The skill writes a YAML
frontmatter charter, asks the practitioner to fill it in, validates it,
times the session, and during the session captures defects through
`AskUserQuestion`-driven prompts (severity → Given → When → Then →
reproduction). On debrief it writes a paired `test/explore-NNN.md` and
`test/explore-NNN.html` artefact that `/gvm-test` reads when evaluating
VV-4(d) (ET-5 tour-completion gate; Critical-blocks-Ship-ready).

This skill is grounded in the *cognitive critique* tradition — Bach &
Bolton's rapid software testing, Hendrickson's *Explore It!*, Whittaker's
tour heuristics. The skill never auto-classifies severity (ADR-205);
the practitioner is the authority. The skill's value is structural —
the charter, the GWT discipline, the artefact contract — not analytic
substitution for the human tester.

**Pipeline position:** after `/gvm-test`, before `/gvm-doc-write`. The
artefact that `/gvm-explore-test` produces is consumed by `/gvm-test`'s
VV-4(d) gate on its *next* invocation; the doc-write phase reads the
artefact for release-note input.

**Shared rules:** at the start of this skill, load
`~/.claude/skills/gvm-design-system/references/shared-rules.md` and follow
all rules throughout execution. Load `~/.claude/skills/gvm-design-system/references/expert-scoring.md`
when scoring experts.

## Hard Gates

These steps are non-negotiable. If you skip any of them, the session
output is invalid.

1. **CHARTER VALIDATED BEFORE THE SESSION STARTS.** Per ADR-202. The skill
   writes a stub at `test/explore-NNN.charter.yml` (NNN zero-padded to
   three digits), the practitioner fills it in, and the skill calls
   `_charter.load(path)` to validate the four ET-2 fields plus
   `schema_version`, `session_id`, and `runner`. On any `CharterError`,
   the skill REFUSES to start the session and reports the offending
   field by name. Implementation: `gvm-explore-test/scripts/_charter.py`
   (this chunk, P11-C06).

2. **PAIRED MD + HTML BEFORE DEBRIEF FINALISED.** Per cross-cutting
   ADR-003 / shared rule 13. Both `test/explore-NNN.md` and
   `test/explore-NNN.html` must exist, atomically, before the skill
   announces the charter closed. Implementation:
   `gvm-explore-test/scripts/_report_writer.py` (delivered by P11-C08;
   not yet built).

3. **DEFECT WITHOUT REPRODUCTION → OBSERVATION.** Per ADR-203 / ET-3.
   Every entry of severity ≥ Minor requires a reproduction path. If the
   practitioner enters blank reproduction at the prompt, the entry is
   re-filed as an Observation (no severity, separate ID space) — not
   rejected, not silently dropped. Implementation: defect intake helpers
   (delivered by P11-C07).

4. **SEVERITY IS THE PRACTITIONER'S CALL.** Per ADR-205. The skill never
   auto-assigns severity. The practitioner picks
   Critical / Important / Minor / Observation through `AskUserQuestion`,
   and `/gvm-test`'s VV-4(d) reads the practitioner's classification
   verbatim. LLM "second-guessing" the practitioner's call is forbidden.

5. **EVERY PRACTITIONER-SUPPLIED STRING HTML-ESCAPED IN THE REPORT.**
   Per TC-ET-3-03 [SECURITY]. The HTML renderer uses `html.escape()`
   (Python stdlib) on every defect, observation, and assessment field
   before substitution. No template-engine raw-string escape hatches.
   Implementation: `_report_writer.py` (delivered by P11-C08).

## Expert Panel

Loaded when `/gvm-explore-test` runs. Activations are logged to the
activation CSV (per shared rule 1).

| Expert | Work | Role in this skill |
|---|---|---|
| **James Bach & Michael Bolton** | *Rapid Software Testing* | Cognitive-critique tradition; charter as the unit of testing; severity as a tester judgement, not a metric |
| **Elisabeth Hendrickson** | *Explore It!* | Charter discipline + tour heuristics; the artefact format draws on her "session sheets" |
| **James Whittaker** | *Exploratory Software Testing* | Tour catalogue (feature, data, money, interruption, configuration) — the five tours in the charter `tour:` enum |
| **Brian Marick** | *Everyday Scripting with Ruby* | Lightweight tooling around exploratory work; the scripts here remain helpers, not frameworks |
| **Cem Kaner, James Bach, Bret Pettichord** | *Lessons Learned in Software Testing* | "Testing is not a phase" / "context-driven" — the skill runs against built code, not against requirements |

**Architecture experts** (loaded for self-review): Brooks, Beck,
McConnell, Martin, Fowler, Hunt & Thomas — applied during the
implementation chunks' self-review loops, not during the practitioner's
session itself.

> The five domain experts above are documented as **discovered experts**
> per shared rule 2. A future
> `~/.claude/skills/gvm-design-system/references/domain/exploratory-testing.md`
> file will consolidate their principles. Until that file exists, the
> grounding lives in this Expert Panel block plus the spec excerpts in
> `specs/gvm-improvements-exploratory.md`.

## Process Flow

```
0. BOOTSTRAP — verify ~/.claude/gvm/ exists (shared rule 14)

1. CHARTER START
   ├─ Read references/charters.md — present charter templates via
   │   AskUserQuestion (charter templates delivered by P11-C10)
   ├─ Practitioner picks a template OR chooses "Start from scratch"
   ├─ Skill computes next free NNN (zero-padded three digits) and writes
   │   the charter buffer to test/explore-NNN.charter.yml
   ├─ Skill emits AskUserQuestion: "Charter file written to
   │   test/explore-NNN.charter.yml. Edit it in your editor, then reply
   │   here with one of: 'Ready — validate' / 'Cancel'."
   ├─ On "Ready", skill calls `_charter.load(path)` (this chunk, P11-C06)
   └─ On CharterError: refuse, name the field, prompt practitioner to fix

2. SESSION (timeboxed; intake helpers delivered by P11-C07)
   ├─ Skill records start time and constructs an `IntakeSession(NNN)` from
   │   `_defect_intake.py` (this chunk, P11-C07)
   ├─ Practitioner explores
   ├─ At any point: practitioner says "found something"
   │     ├─ AskUserQuestion: severity? GWT? reproduction? stub-path?
   │     ├─ Skill calls `session.record(severity, given, when, then,
   │     │   reproduction, stub_path)` — re-files to ObservationEntry per
   │     │   ADR-203 if reproduction is blank at severity ≥ Minor
   │     ├─ Skill calls `write_partial_handover(session, test/handovers/)`
   │     │   for crash recovery (ADR-204; atomic write)
   │     └─ Practitioner continues
   └─ Timebox elapsed OR practitioner says "debrief": go to step 3

3. DEBRIEF
   ├─ Skill prompts for overall assessment paragraph (free text)
   ├─ Skill calls `_report_writer.write_report(charter, session,
   │   session_log, assessment, output_dir=test/)` (P11-C08) — writes
   │   paired test/explore-NNN.md and .html atomically; HTML escapes
   │   every practitioner-supplied string at render time (Hard Gate 5)
   ├─ ONLY after `write_report` returns successfully, skill calls
   │   `_defect_intake.remove_partial_handover(session, test/handovers/)`
   │   to remove `explore-NNN-partial.md`. If `write_report` raises,
   │   leave the partial in place — it is the crash-recovery point;
   │   re-prompt the practitioner to retry the debrief (R24 I-6).
   └─ Skill announces "Charter NNN closed; N defects, M observations"

4. CROSS-SKILL HANDOFF
   └─ /gvm-test on next invocation reads the most recent test/explore-NNN.md
      via the parser delivered by P11-C09 and evaluates VV-4(d):
      Critical defects in non-stub paths block Ship-ready.
```

The above flow is the contract. **This chunk (P11-C06) delivers the
SKILL.md scaffold and the charter validator (`_charter.py`).**
P11-C07 delivers defect-intake helpers. P11-C08 delivers the session-report
writer (paired md + html). P11-C09 wires VV-4(d) into `/gvm-test`. P11-C10
populates `references/charters.md` with the initial library.

## Phase Details

### Phase 0 — Bootstrap

Pre-flight per shared rule 14. Refuse if the GVM home directory is
missing — direct the user to `/gvm-init`.

### Phase 1 — Charter start

Charter file path: `test/explore-NNN.charter.yml` where NNN is the next
free integer, zero-padded to three digits (`001`, `002`, ...). Collision
rule: if `test/explore-NNN.charter.yml` already exists for the proposed
NNN, the skill refuses; the practitioner must close the prior session
first (debrief or remove the file).

The schema is the YAML in ADR-202 (seven top-level keys: `schema_version`,
`session_id`, `mission`, `timebox_minutes`, `target`, `tour`, `runner`).
`tour` is case-insensitive bare word — `data`, `Data`, `DATA` all
accepted; `data tour` rejected with an error naming the allowed values.
`timebox_minutes` is one of 30 / 60 / 90. `runner: unassigned` is
permitted (ET-7 fallback per ADR-207).

Validation is a programmatic check, not a free-text agreement: the skill
calls `_charter.load(path)` and either receives a `Charter` dataclass or
catches a `CharterError(field, reason)` it shows the practitioner.

### Phase 2 — Session

Timeboxed. Defect intake via `AskUserQuestion`. Severity options:
Critical / Important / Minor / Observation. GWT clauses captured one at
a time. Reproduction path required for severity ≥ Minor; if blank, the
entry is re-filed as an Observation per ET-3 (ADR-203).

Implementation: `_defect_intake.py` (P11-C07).
`IntakeSession(NNN).record(...)` returns either a `DefectEntry`
(severities Critical/Important/Minor with non-empty reproduction) or an
`ObservationEntry` (severity=Observation OR re-filed defects). Per
ADR-206 the two types are distinct dataclasses — `DefectEntry` carries
a severity field, `ObservationEntry` does not. Defect IDs are
`D-NNN`; observation IDs are `O-NNN`; the two namespaces increment
independently.

After every intake the skill calls `write_partial_handover(session,
test/handovers/)`, which atomically writes
`test/handovers/explore-NNN-partial.md` so a session can resume after a
crash (per A-9 / ADR-204). Practitioner-supplied strings are stored
verbatim — no escaping happens here. The HTML escape (Hard Gate 5) is
applied at render time by P11-C08's writer.

### Phase 3 — Debrief

Practitioner provides an overall assessment paragraph. Implementation:
`_report_writer.write_report(charter, session, session_log, assessment,
output_dir)` (P11-C08). Emits paired `test/explore-NNN.md` and
`test/explore-NNN.html` atomically (mkstemp + `os.replace`) — both files
become visible together; no half-written state is observable.

HTML escaping is mandatory at render time per Hard Gate 5: every
practitioner-supplied string (charter fields, GWT clauses, reproduction,
stub-path, session-log entries, assessment) passes through `html.escape()`
before substitution. The MD output preserves raw practitioner payload —
that is the artefact `/gvm-test`'s `_explore_parser` (P11-C09) reads, so
the practitioner's authoritative classification flows through unmodified.

Five H2 sections in fixed order: Charter, Session Log, Defects,
Observations, Overall Assessment. Each defect block carries a
`**Stub-path:**` line per ADR-206 (the field `_explore_parser` keys off
to compute `in_stub_path` for the VV-4(d) gate).

### Phase 4 — Cross-skill handoff (P11-C09 wires VV-4(d))

`/gvm-test` on its next invocation reads the most-recent
`test/explore-NNN.md` (highest NNN by lexicographic order — zero-padded
three-digit NNN sorts numerically) and parses its `## Defects` section.
The parser sets `in_stub_path = True` only when the defect's
`**Stub-path:**` line points at an entry in `STUBS.md`. VV-4(d) blocks
Ship-ready when any defect is `severity == Critical and not in_stub_path`.

## Key Rules

1. **Charter first; session never starts without a valid charter.** Per
   Hard Gate 1. The validator names the offending field on failure;
   silent acceptance is forbidden.

2. **Severity stays the practitioner's call.** Per Hard Gate 4 / ADR-205.
   Cognitive critique is the value (Bach & Bolton); auto-classification
   defeats the purpose.

3. **Defect without reproduction → Observation.** Per Hard Gate 3 / ET-3.
   Re-filing is structural — the prompt sequence enforces it.

4. **HTML escaping is universal.** Per Hard Gate 5 / TC-ET-3-03 [SECURITY].
   Every practitioner-supplied string passes through `html.escape()`
   before HTML substitution.

5. **The artefact is the contract.** `/gvm-test` reads
   `test/explore-NNN.md`; there is no shared in-memory state, no JSON
   sidecar, no shared service. Filesystem is the IPC (cross-cutting
   principle).

6. **Tour names are bare words, lowercase, validated.** Per ADR-202.
   Five allowed values: `feature | data | money | interruption |
   configuration`. Case-insensitive on input; the validator returns the
   lowercased value.

   **Data-tour patterns to include in standard charters.** The `data`
   tour is the catch-all for "drive the product against inputs the
   engine wasn't tuned for." Per the post-v2.0.0 audit lessons, every
   data-tour charter should consider — not necessarily exercise all,
   but consciously decide which apply:

   - **Engine-untuned data shapes.** Inputs that don't trigger the
     engine's threshold-firing candidates: clean data with no
     anomalies; uniform / bimodal distributions on columns the engine
     expects to be normal-shaped; constant-value columns; all-null
     columns; single-row datasets.
   - **Realistic short-token cases.** Real-world data routinely has
     short categorical codes (sex M/F, blood type A/B/AB/O, yes/no
     Y/N, agree/disagree A/D, school grades A/B/C/D/F). These trip
     pre-existing string-matching defects that synthetic fixtures
     ("Alice"/"Bob") never exercise. The post-v2.0.0 privacy-scan
     substring-collision defect (S6.1) was found by exactly this
     case.
   - **Mode × data-shape combinations.** When a CLI accepts a `--mode`
     flag (or equivalent), exercise each documented mode against each
     data-shape variant. The motivating example: validate mode plus
     clean ordinal data plus no `--target-column` — a legitimate
     drift-check workflow that single-mode happy-path testing missed.
   - **Boundary inputs without context.** A target column missing
     from the input; a `--baseline-file` whose schema differs from
     `--input`; a multi-sheet xlsx where the engine picks the wrong
     sheet by default.

   These patterns belong in the `objective:` field of a `data`-tour
   charter when the system under test is a data-analysis product. For
   non-data products the tour catalogue's other four values cover the
   equivalent shapes.

7. **`runner: unassigned` is allowed.** Per ADR-207. The ET-7 fallback
   path: a charter with `runner: unassigned` records zero Critical
   findings against VV-4(d) and emits a warning. The dependency loop
   (OQ-4 ↔ ET-7) is avoided structurally.

8. **One charter at a time.** NNN collision is a refusal, not an error
   to reconcile. Practitioner closes the prior session (debrief or
   delete) before starting a new one.

9. **Hand off via the latest artefact.** `/gvm-test` reads the most
   recent `test/explore-NNN.md`; older charters are historical evidence,
   not gates. If multiple charters have run since the last `/gvm-test`,
   the latest is the source of truth.
