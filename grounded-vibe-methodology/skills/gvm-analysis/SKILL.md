---
name: gvm-analysis
description: Privacy-preserving exploratory data analysis. Claude orchestrates a Python engine that reads the user's data, produces a grounded findings report with headline insights, provenance, and a methodology appendix. Raw rows never enter Claude's context.
---

# Analysis

## Overview

`/gvm-analysis` produces a grounded, reproducible data-analysis report for a CSV / TSV / xlsx / parquet / JSON input. The Python engine at `scripts/analyse.py` computes findings; the renderer at `scripts/render_report.py` emits an HTML hub. Claude orchestrates the flow (mode selection, preferences, progress narration, comprehension questions) but never reads raw rows.

**Pipeline position:** standalone skill. The user hands Claude a file path; Claude runs this skill end-to-end and hands back an HTML report path.

## Hard Gates

These are non-negotiable. Skipping any one invalidates the output.

1. **Privacy boundary.** Claude never reads the user's raw rows. All data processing happens inside the Python subprocess. Claude only reads `findings.json` (aggregated, privacy-cleared) and the engine's stderr diagnostics. If you find yourself about to `Read` the input file or echo its contents, stop — that violates ASR-1 / AN-4 / NFR-1.
2. **Dispatch Python; never inline analysis.** Statistical methods, distribution checks, outlier detection, forecasting — none of these run in Claude's reasoning. They run in `scripts/analyse.py`. If a step needs a number, call the engine.
3. **Fail fast on missing deps.** Step 0 (Dependency check) is blocking. If `python3 scripts/_check_deps.py` exits non-zero, show its stderr and stop. Do not "try anyway".
4. **Structured decisions only.** Every user decision in the process flow goes through `AskUserQuestion` with enumerated options. Never ask the user to type free-text where a discrete choice is appropriate (ADR-102).
5. **Diagnostic passthrough.** If any subprocess exits non-zero, surface its stderr verbatim. Do not paraphrase engine errors — they are written to be user-facing.

## Modes

Per ADR-103: modes add report emphasis, they do not change *which* statistical methods run. Every mode runs the full data-quality + distribution + outlier passes.

| Mode | Engine behaviour | Renderer behaviour |
|---|---|---|
| **Explore** | Full pass; no driver decomposition | Headline findings = top data-quality issues + striking distributions |
| **Decompose** | Full pass + driver decomposition on a user-named target column | Headline emphasises drivers; comprehension questions framed around drivers |
| **Validate** | Full pass on the current file; full pass on a baseline file; differential between the two | Headline emphasises divergences; report includes a side-by-side delta section |
| **Not sure — run everything** | Full pass + driver decomposition on the top 5 numeric columns by variance | Hub shows every section; user navigates via the TOC |

## Process Flow

Sections below follow ADR-102 numbering. Each section is a bounded region; downstream build chunks (P5-C01b / P5-C02 / P5-C03 / P5-C04 / P5-C05) extend the matching section without touching others.

### 0. Dependency check (blocking)

Run:

```bash
python3 scripts/_check_deps.py
```

Interpret the result strictly by exit code (not by parsing stderr):

- **Exit 0** — proceed to step 1. If stderr contains an `ADVISORY:` line about optional packages, pass that advisory through to the user verbatim; do not stop.
- **Exit non-zero** — surface the script's stderr to the user verbatim. Do not paraphrase, do not truncate, do not add commentary. The script already emits the `ERROR / What went wrong / What to try` diagnostic with an `INSTALL:` line derived from its own `REQUIRED` list. Stop — do not run any other step.
- **Bash invocation itself fails** (Python not on PATH, script unreadable, parent dir permission denied): the subprocess stderr is captured by the shell. Present it under the standard ERROR header with the fallback guidance from ADR-106 (confirm `python3 --version` ≥ 3.9, confirm `~/.claude/skills/gvm-analysis/` is readable, check for restricted execution environments). Stop.

`_check_deps.py` is the monolithic gate for every REQUIRED dependency (engine + renderer). A failure here cannot leak into the analysis path — fail-fast per ADR-106.

### 1. Initialise GVM home directory

Silent. Per shared rule 14, verify `~/.claude/gvm/` exists before any output.

### 2. Mode selection

Dispatch `AskUserQuestion` with exactly four options:

- `Explore`
- `Decompose`
- `Validate`
- `Not sure — run everything`

No analysis runs until the user selects one. The selection becomes the engine's `--mode` flag.

### 3. Multi-sheet xlsx prompt

If the input is `.xlsx` with more than one sheet, dispatch `AskUserQuestion` listing every sheet name. Accept single-sheet, multi-sheet, or all-sheets selection. No sheet is silently chosen.

### 4. Multi-file strategy

If the user passed more than one file, dispatch `AskUserQuestion` with three options:

- `Aggregate (concatenate on shared columns)`
- `Separate report per file`
- `Comparative analysis across files`

Special case: if the user passed exactly two files AND selected `Validate` mode in step 2, the second file is auto-assigned as the baseline; skip this prompt and announce `second file '<name>' treated as baseline (no prompt)`.

### 5. Domain detection

Run:

```bash
python3 scripts/domain_detect_cli.py --input "$INPUT"
```

Repeat `--input "$FILE"` once per file for multi-file invocations (step 4). The CLI reads header rows only — it never touches row values (ASR-1).

**Success (exit 0):** stdout is a JSON object with exactly three keys (ADR-105):

```json
{
  "matched": "string|null",
  "signals": ["string", ...],
  "candidate_domain": "string|null"
}
```

Branch on the parsed object:

- **Match — `matched != null`.** Let `industry_file` be `~/.claude/skills/gvm-design-system/references/industry/{matched}.md`. Announce `Domain detected: {matched} — loaded {industry_file}.` using the fully-resolved path, then load that file via the `Read` tool. Subsequent steps cite its experts. (Per ADR-105, `matched` is the `domain_name` slug from the industry file's frontmatter — it is display-ready.)
- **Identifiable but no file — `matched == null` AND `candidate_domain != null`.** Dispatch `AskUserQuestion` with two options:
  - `Run Expert Discovery for {candidate_domain}` — triggers shared rule 2 (expert discovery). On completion, persist the new `industry/{candidate_domain}.md` and load it.
  - `Proceed in general-purpose mode` — skip industry loading.
- **Unidentifiable — `matched == null` AND `candidate_domain == null`.** Announce `No domain detected — proceeding in general-purpose mode.` Skip industry loading. No prompt.
- **`--domain <name>` override (AN-9).** If the user's invocation included a `--domain` argument, bypass the CLI entirely. Load `~/.claude/skills/gvm-design-system/references/industry/{name}.md` directly via `Read`. If that file does not exist, list the contents of `~/.claude/skills/gvm-design-system/references/industry/` (directory listing, not CLI stderr — the CLI is not invoked on this path), include the available `*.md` file stems in a diagnostic ("available domains: credit_risk, real_estate, …"), and stop.

**Failure (exit non-zero):** surface the CLI's stderr verbatim. The CLI already emits the `ERROR / What went wrong / What to try` block for malformed industry frontmatter (`MalformedIndustryFileError`) and for unsupported file formats. Do not paraphrase.

Under no circumstances does Claude read the user's input file to "confirm" the match — the CLI has already done the only read permitted (header row only, via pandas/pyarrow).

### 6. Preferences load / customise

Canonical path: `~/.claude/gvm/analysis/preferences.yaml` (`$PREFS_PATH` hereafter).

Dispatch all reads and writes through the CLI — never `Read` the YAML file directly. The CLI handles validation, migration (AN-44), and atomic writes:

```bash
python3 scripts/prefs_cli.py load --path "$PREFS_PATH"
python3 scripts/prefs_cli.py save --path "$PREFS_PATH" --prefs-json "$JSON"
```

Interpret the load result strictly by exit code:

- **0** — stdout is `{"prefs": {...}, "warnings": [...]}`. Use the `prefs` object as `$PREFS`.
- **2** — validation error. Surface stderr verbatim; stop.
- **3** — migration refused (file newer than the skill supports). Surface stderr verbatim; stop.
- **4** — malformed YAML. Surface stderr verbatim; stop.
- **1** — I/O error. Surface stderr verbatim; stop.

**State machine (ADR-104):**

- **A. `$PREFS_PATH` does not exist** (CLI returns defaults with empty warnings). Dispatch `AskUserQuestion`:
  - `Customise preferences now`
  - `Use shipped defaults`
  On `Use shipped defaults`, set `$PREFS` to the `prefs` object returned by the `load` stdout (the CLI returns defaults when the file is missing).
  On `Customise preferences now`, walk each overridable key via a series of `AskUserQuestion` prompts (`headline_count`, `data_quality_checks.*`, `trend_alpha`, `seasonal_strength_threshold`, `outlier_methods`, `bootstrap_n_iter`, `bootstrap_confidence`, `time_series_gap_threshold`, `time_series_stale_threshold_days`, `fuzzy_duplicate_threshold`) and build the customised `$PREFS`. Then `prefs_cli.py save --path "$PREFS_PATH" --prefs-json "$PREFS"`. On `Use shipped defaults`, still `save` so the next run announces a file and the file is hand-editable (AN-34).
- **B. `$PREFS_PATH` exists** (CLI parsed and merged — file may have been rewritten on disk already if it was version-less; AN-44). Announce the loaded preferences as plain `key: value` lines (schema keys only — never invent keys). Dispatch `AskUserQuestion`:
  - `Edit preferences`
  - `Use loaded preferences as-is`
  On `Edit preferences`, walk the same keys via `AskUserQuestion` (seeding each prompt's default with the loaded value). Call `prefs_cli.py save` with the edited `$PREFS`. On `Use loaded preferences as-is`, proceed with the loaded `$PREFS`.

**Announcement on migration (AN-44):** if the stdout's `warnings` array is non-empty, surface each entry to the user before the AskUserQuestion — a version-less file rewritten to v1 is a common case and the user should know the file was modified.

**Privacy boundary.** `preferences.yaml` contains only settings (thresholds, toggles, method names). It is not raw data. The load CLI may rewrite the file on disk when migrating (AN-44) — this is the only disk write orchestration triggers in this step.

Pass `--prefs "$PREFS_PATH"` to the engine in step 10 so the engine re-validates (defence in depth) and sources its runtime configuration from the same file.

### 7. Sampling offer

If the loaded dataset has `n ≥ 10_000` rows, dispatch `AskUserQuestion` with two options:

- `Sample (with seed)`
- `Run on full data`

### 7b. Multi-datetime resolution

If the dataset has more than one datetime-typed column AND no `--time-column` flag was passed, dispatch `AskUserQuestion` listing every datetime column so the user selects the time axis. Otherwise auto-select the single datetime column. The choice is recorded as `provenance.time_column`.

### 8. Decompose mode: target column

If the mode is `Decompose`, dispatch `AskUserQuestion` listing the dataset's column names (headers only — the header row is metadata, not raw data, and is already read by `scripts/domain_detect_cli.py` for step 5). The user picks one; it becomes the engine's `--target-column` flag. Do not proceed to step 10 until a target column is supplied.

### 9. Validate mode: baseline file

If the mode is `Validate` and the user passed only one file, dispatch `AskUserQuestion` asking for the baseline file path. Refuse to proceed if none is supplied. (Two-file invocation already resolved this in step 4.)

### 10. Engine invocation

Run the bash invocation template from the *Bash Invocation Template* section below, with `$INPUT`, `$OUT`, `$MODE`, `$SEED` resolved from earlier steps. Extend the command line with the mode-specific flags gathered in steps 7, 7b, 8, and 9 (`--sample-n`, `--time-column`, `--target-column`, `--baseline-file`, `--prefs`).

Interpret the result strictly by exit code:

- **Exit 0** — read `$OUT/findings.json`. Do NOT read any other file produced by the engine; `findings.json` is the only privacy-cleared channel (ASR-1 / AN-4). Do not read the input file at any point — success does not relax this prohibition (ASR-1 / AN-4 / NFR-1).
- **Exit non-zero** — surface the engine's stderr verbatim (per ADR-107 the engine owns its diagnostics: encrypted xlsx refusal, malformed file, etc.). Do not retry, do not reinvoke with different flags, do not read the input file to "help" diagnose. Stop.

Under no circumstances may Claude `Read` the user's input file to inspect or preview its contents — the engine is the only actor authorised to touch raw rows.

### 11. Forecast offer

Per ADR-108, the forecast is a conditional second pass. Read only the `time_series` block from `$OUT/findings.json` — do NOT re-read the input file on any branch of this step (ASR-1 / AN-4 / NFR-1: the input file must not be opened by Claude under any circumstances, success or failure).

**Guard.** Evaluate in this order, short-circuiting on the first false:

1. `findings.time_series is not None` — if the dataset had no temporal column, there is nothing to forecast. Skip silently to step 13. (HIGH-T28 post-R4 fix: the previous spec omitted this null-guard and would raise `TypeError` on non-temporal data.)
2. Either `findings.time_series.trend.significant` is `true` **or** `findings.time_series.seasonality.strength > $PREFS.seasonal_strength_threshold`. The nested field paths are load-bearing — the flat forms do not exist in the engine schema and would silently evaluate falsy (ADR-108 post-C1 fix). The seasonality threshold comes from the `seasonal_strength_threshold` key on the `$PREFS` object loaded in step 6 (TC-AN-22-08: user-overridable via preferences); do not hardcode a literal.

**If the guard is false**, proceed directly to step 13 (render). The framing note depends on which sub-clause failed:

- Null branch (`time_series is None`): "no temporal data — forecast not applicable".
- Flagged-false branch (trend and seasonality both below threshold): "no trend or seasonality detected — forecast not offered".

Under no circumstances may Claude `Read` the user's input file on this branch either — skipping the forecast does not relax the privacy boundary (ASR-1 / AN-4 / NFR-1).

**If the guard is true**, dispatch `AskUserQuestion`:

- Question: "A trend or seasonality was detected. Offer a short-horizon forecast?"
- Options: `Forecast` / `Skip`

On `Skip`: leave `findings.json` unmodified (TC-AN-22-05 — off by default) and proceed directly to step 13 (render). Claude must not read the user's input file on the Skip path (ASR-1 / AN-4 / NFR-1 — the user dismissing the forecast does not relax the boundary).

On `Forecast`, dispatch a second `AskUserQuestion` for the method:

- Options: `linear` (linear projection) / `ARIMA` / `exponential smoothing`

Bind the chosen method to `$METHOD` and proceed to step 12. Claude must never read the user's input file at any point on this step — the `time_series` block from `findings.json` is the only privacy-cleared source.

### 12. Re-invoke engine for forecast

Run the forecast pass against `findings.json`. Claude must not re-read the user's input file on this step — `findings.json` is the only privacy-cleared channel (ASR-1 / AN-4 / NFR-1), and the engine itself re-derives whatever it needs.

```bash
python3 scripts/analyse.py \
  --forecast-only \
  --in-file "$OUT/findings.json" \
  --forecast-method "$METHOD" \
  --prefs "$PREFS_PATH"
```

`$METHOD` is the method chosen by the user in step 11 (`linear` / `ARIMA` / `exponential smoothing`). `$PREFS_PATH` is the preferences file resolved in step 6. Per ADR-209, the forecast pass patches `findings.json` in place via the atomic-write protocol (write to `findings.json.tmp`, then `os.replace`) — so a non-zero exit leaves the original file untouched and safe to re-read.

Interpret the result strictly by exit code:

- **Exit 0** — the forecast block is appended. Proceed to step 13 (render).
- **Exit non-zero** — surface the engine's stderr verbatim. Do not retry, do not re-read the input file to diagnose, do not silently fall back to the non-forecast render. Stop.

Under no circumstances may Claude `Read` the user's input file to inspect or preview its contents on the forecast pass — the engine is the only actor authorised to touch raw rows.

### 12b. Invoke comprehension-question bridge (mandatory, before render)

After the engine has written `findings.json` (step 10) and any forecast pass has completed (step 12), invoke the **Comprehension-Question Bridge** described below (the dedicated section). This is not an optional embellishment — the engine emits literal placeholder text in `findings.comprehension_questions` by design (bridge stub per STUBS.md), and the bridge is what overwrites those placeholders with real LLM-synthesised questions tied to `findings.headline_findings[].id` values.

Do not proceed to step 13 until the bridge has run successfully (exit 0) or the recovery path described in the Bridge section has been exercised. Skipping this step ships placeholder text in the rendered hub — TC-NFR-4-01b fails by inspection.

### 13. Render report

Run `python3 scripts/render_report.py --findings "$OUT/findings.json" --out "$OUT"`. The renderer reads mode emphasis from `findings.json::provenance.mode` (per ADR-103) — no `--mode` flag needed. Show stderr verbatim on non-zero exit.

### 14. Present report path

Announce the hub path and the three-to-ten headline findings as a short summary. Stop.

## Bash Invocation Template

```bash
python3 scripts/analyse.py \
  --input "$INPUT" \
  --output-dir "$OUT" \
  --mode "$MODE" \
  --seed "$SEED"
```

Flags extended by downstream phases: `--target-column` (Decompose), `--baseline-file` (Validate), `--time-column` (multi-datetime), `--forecast-only` (forecast pass), `--prefs` (preferences), `--sample-n` (sampling).

On non-zero exit, surface stderr verbatim and stop. Do not retry, do not paraphrase.

## Diagnostic Passthrough

The engine writes diagnostics in a fixed `ERROR / What happened / What to try` format (cross-cutting Error Handling Conventions). Pass these to the user unchanged. Do not re-word, do not summarise, do not invent additional context — the engine owns its error messages.

## Comprehension-Question Bridge

After the main engine pass exits 0 and before the renderer (step 13):

1. Read `findings.json::headline_findings` (already privacy-cleared per ADR-211 — safe for Claude's context).
2. Compose exactly three plain-language comprehension questions, each a dict with string fields `question`, `answer`, `supporting_finding_id`. Each `supporting_finding_id` MUST reference an existing `headline_findings[].id`. Use plain language only — no statistical method names. Column names are acceptable in questions and answers; raw row-level values from the dataset are not.
3. Write the questions array to `<out>/findings.questions.tmp.json`.
4. Run:

   ```bash
   python3 scripts/_patch_questions.py \
     --findings "$OUT/findings.json" \
     --questions "$OUT/findings.questions.tmp.json"
   ```

5. Wrapper exit codes drive the retry policy:
   - `0` — success. Proceed to step 13 (render).
   - `2` — structural failure (wrong count, missing field, malformed JSON). Retry with corrected shape.
   - `3` — referential integrity (a `supporting_finding_id` does not match a headline). Retry with valid ids.
   - `4` — jargon violation. Rephrase in plain language and retry.
   - `5` — privacy boundary violation (should not occur; escalate).
   - `1` — I/O failure (disk, permissions, cross-volume write). Not retryable without operator intervention.

6. **Retry policy:** max 3 attempts. On each non-zero exit, stderr contains the canonical ERROR/What/What-to-try block naming the offending field or term — surface it verbatim and regenerate questions with the correction applied. The temp file is preserved on failure (deleted only on exit 0).

7. **Recovery on exhaustion:** after three failed attempts, halt and show the user:

   > The analysis findings have been preserved at `$OUT/findings.json`. To recover without re-running the full analysis, author three comprehension questions by hand (each with `question`, `answer`, `supporting_finding_id` referencing a `headline_findings[].id` value), save them as `questions.json`, then run `python3 scripts/_patch_questions.py --findings $OUT/findings.json --questions questions.json` followed by the renderer. Or re-invoke `/gvm-analysis` to retry the auto-generated questions from scratch.

## Notes for Future Chunks

| Chunk | Section it extends |
|---|---|
| P5-C01b | Comprehension-Question Bridge (wrapper script) |
| P5-C02 | Dependency check (step 0) + engine invocation (step 10) |
| P5-C03 | Domain detection (step 5) |
| P5-C04 | Preferences load / customise (step 6) |
| P5-C05 | Forecast offer (step 11) + re-invocation (step 12) |

Each downstream chunk edits its section boundary only. Do not reorder the process flow — ADR-102 step ordering is the contract.

---

*Developed using the Grounded Vibe Methodology*
