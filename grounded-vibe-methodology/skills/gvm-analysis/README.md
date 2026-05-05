# gvm-analysis

Privacy-preserving exploratory data analysis as a Claude Code skill. Reads
a CSV / TSV / xlsx / parquet / JSON file, produces a grounded findings
report with headline insights, real provenance, and a methodology
appendix. Raw rows never enter Claude's context.

The package is the engine and renderer behind the `/gvm-analysis` GVM
slash command. `pip install` is supported so downstream CI and tests can
import the skill's modules directly.

## When to use

- You have a tabular dataset (CSV / TSV / xlsx / parquet / JSON) and want
  a fast, opinionated read on shape, outliers, time-series cadence, and
  drivers — without writing notebook code yourself.
- The data is sensitive or cannot leave the machine. The privacy boundary
  (NFR-1, below) keeps raw rows out of the LLM context.
- You want the analysis to be reproducible. Provenance (SHA-256 of input,
  library versions, deterministic seed) ships in every report.

Skip if the dataset is tiny enough to eyeball, the question is purely
qualitative, or you need a hand-tuned model — `/gvm-analysis` is an
exploratory triage tool, not a modelling pipeline.

## Modes

| Mode | When to use |
|------|-------------|
| Explore | Default. No target column — runs descriptive statistics, outliers, time-series, and the privacy-safe duplicate summary across every column. |
| Decompose | A target column is supplied. Runs driver decomposition (variance + partial correlation + RF importance with three-way agreement) on top of the Explore battery. |
| Validate | A target column AND a baseline-comparison column are supplied. Runs the Decompose battery and reports per-driver effect deltas against the baseline. |
| Run-everything | Every analytical block fires unconditionally. Slowest mode; useful for full-corpus batch runs where coverage matters more than runtime. |

## What it produces

End-to-end run produces:

- `findings.json` — a schema-versioned dataclass carrying real per-column
  statistics with bootstrap confidence intervals, outlier detection
  agreement matrix, time-series block, driver decomposition (when a
  target column is supplied), privacy-safe duplicate summary, three
  plain-language comprehension questions, and full provenance
  (SHA-256 of input, library versions, deterministic seed).
- `report.html` — a self-contained HTML hub rendered from
  `findings.json` using the Tufte / Few CSS shell. No external assets;
  opens in any browser.

## Privacy boundary (NFR-1)

The engine writes only aggregates to `findings.json`. Raw cell values
never appear in output artefacts. The privacy boundary is enforced
end-to-end by `tests/integration/test_privacy_audit.py`, which drives
the engine against a sentinel-string fixture across every mode and
asserts no sentinel substring leaks into any output file.

The orchestrator never reads the user's input file. It reads
`findings.json`, which carries aggregates only.

## Layout

```
gvm-analysis/
├── scripts/
│   ├── analyse.py                # Engine CLI entrypoint
│   ├── render_report.py          # Renderer CLI entrypoint
│   ├── anonymise.py              # Token-pattern anonymisation pipeline
│   ├── de_anonymise.py           # Reverse anonymisation
│   ├── _patch_questions.py       # Orchestration-layer comprehension synthesiser
│   └── _shared/                  # Engine modules
│       ├── findings.py           # Schema + atomic write
│       ├── provenance.py         # SHA-256, lib versions, timestamp, prefs hash
│       ├── stats.py              # Per-column statistics + bootstrap CI
│       ├── outliers.py           # IQR + MAD + iForest + LOF
│       ├── time_series.py        # Cadence, gaps, trend, seasonality, forecast
│       ├── drivers.py            # Variance + partial correlation + RF importance
│       ├── duplicates.py         # Privacy-safe duplicate summariser
│       ├── headline.py           # Cross-section finding selector
│       ├── default_questions.py  # Deterministic Q/A synthesiser
│       └── ...                   # missing, type_drift, rounding, palette, charts, …
├── templates/                    # Jinja2 templates for the HTML hub
├── tests/
│   ├── unit/                     # Module-level unit tests
│   └── integration/              # End-to-end engine + renderer tests
├── gvm_analysis/                 # Package marker
└── pyproject.toml
```

## Installation

```bash
pip install -e .
```

For testing, install the optional `test` extras:

```bash
pip install -e ".[test]"
playwright install   # one-time, downloads the browser Playwright drives
```

The `[test]` extras include `playwright>=1.40` for the WCAG audit.
Playwright browser binaries are not bundled with `pip` and must be
installed once per environment.

For heavier analytics (SHAP driver explanations, ARIMA forecasting,
LTTB time-series downsampling), install the `full` extras:

```bash
pip install -e ".[full]"
```

## Running the engine

The engine is normally driven by the `/gvm-analysis` Claude skill, but
can be invoked directly:

```bash
# Explore mode — descriptive analysis only
python3 scripts/analyse.py \
    --input path/to/input.csv \
    --output-dir /tmp/analysis \
    --mode explore

# Decompose mode — adds driver decomposition for a chosen target
python3 scripts/analyse.py \
    --input path/to/input.csv \
    --output-dir /tmp/analysis \
    --mode decompose \
    --target-column outcome

# Run-everything — every analytical pass against the full input
python3 scripts/analyse.py \
    --input path/to/input.csv \
    --output-dir /tmp/analysis \
    --mode run-everything \
    --target-column outcome

python3 scripts/render_report.py \
    --findings /tmp/analysis/findings.json \
    --out /tmp/analysis
```

The engine derives a deterministic 31-bit seed from the input file's
SHA-256 when `--seed` is omitted, so the same input always produces the
same findings without an explicit seed.

## Running tests

```bash
python3 -m pytest tests/ -v
```

Unit tests run offline and fast. Integration tests invoke `analyse.py`
and `render_report.py` directly via the in-process `main(argv)`
contract and verify end-to-end behaviour, including the privacy
boundary.

Two test groups are environment-gated to keep the default suite quick:

```bash
GVM_RUN_PERF_TESTS=1 python3 -m pytest tests/integration/test_perf_budget.py
GVM_RUN_WCAG_TESTS=1 python3 -m pytest tests/integration/test_wcag_audit.py
```

The perf budget test synthesises a 1M-row × 10-column fixture and
asserts the engine completes inside the NFR-2 budget (5 minutes wall
clock, 6 GiB peak RAM). The WCAG audit launches headless Chromium and
runs axe-core against the rendered hub.

## Comprehension questions

Every `findings.json` carries exactly three plain-language Q/A pairs.
The engine produces deterministic baseline questions from the headline
findings; the SKILL.md orchestration layer overwrites them with richer
LLM-synthesised questions when an orchestrator is in the loop.

This means a direct-CLI invocation (no orchestrating LLM) ships
structurally valid questions tied to real headline IDs, not placeholder
text. The orchestration path enhances; it doesn't fix a placeholder.

## Provenance

Every `findings.json` carries:

- SHA-256 of every input file
- ISO-8601 UTC timestamp
- Resolved seed (explicit `--seed` or deterministic derivation from
  input SHA-256)
- Sub-seeds for every analytical module that uses RNG (per ADR-202 — the decision record governing deterministic sub-seed derivation)
- Library versions captured via `importlib.metadata`
- Preferences hash
- AN-40 anonymisation flag (when input matches token patterns; AN-40 is the spec rule defining the detection heuristic)

## License

MIT. See the top-level `Grounded Vibe Methodology` repository
for licensing terms.
