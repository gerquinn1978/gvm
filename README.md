# Grounded Vibe Methodology

Citation-based expert grounding for AI-assisted software development. Name the expert, cite the work, get focused output instead of undifferentiated training data.

## What's in this repository

### The plugin

`grounded-vibe-methodology/` — a Claude Code plugin that implements GVM as a phased pipeline. Install it and every pipeline phase activates named authorities for requirements, test design, architecture, build, and review.

See [`grounded-vibe-methodology/README.md`](grounded-vibe-methodology/README.md) for installation and usage.

### Whitepapers

All whitepapers are in `whitepapers/`. Open in a browser. Suggested reading order:

| # | Paper | What it covers |
|---|-------|----------------|
| 1 | **The Grounded Vibe Methodology** | The full thesis: citation-based grounding, expert model, pipeline, experiment, attribution argument |
| 2 | **Well-Engineered Software Needs an End-to-End Pipeline** | The structural decisions and durable artefacts that distinguish the GVM pipeline, independent of expert grounding |
| 3 | **Grounding Produces Measurably Better Output** | The controlled experiment: 180 dashboards, three models (Claude, GPT, Gemini), 1,080 blind reviews, dose-response results |
| 4 | **Why Citation-Based Activation Works** | Transformer-level mechanism: why naming an expert changes what the model produces |
| 5 | **Verifying AI-Generated Code** | Five-layer verification architecture: property-based testing, mutation testing, security testing, stack-aware tooling |
| 6 | **Beyond the Pipeline** | Where the methodology goes once the pipeline is working: standalone tools, document types beyond pipeline artefacts, Tier 2b cross-project compounding, the reflexive case study, and worked sketches in non-software disciplines |

Each paper includes a "This paper in context" guide linking to the others.

### The experiment

180 market risk dashboards across three models (Claude, GPT, Gemini), three grounding conditions, 1,080 blind reviews. The experiment paper is in `whitepapers/`. The experiment configs (exact prompts, grounding conditions, review rubrics) are in `experiments/`. The results CSVs (scores and group mappings for all three models under both review conditions) are in `experiments/results/`.

### Case study

`case-studies/case-study-assay.html` — a full end-to-end case study of building Assay (the experiment runner) with GVM. Covers requirements through release, with expert patterns traceable in the production code.

### Training

Eight training documents in `training/`:

| Document | What it covers |
|----------|----------------|
| **Getting Started** | Install, pipeline walkthrough, quick reference |
| **Expert Grounding Workshop** | Why citations work, practice exercises, where grounding is effective |
| **Review Calibration Training** | Progressive calibration, dual review, build check tiers, practice exercises |
| **Triage Workshop** | Practising the Finding Quality Gate across document, code, and design reviews; fix/defer/dismiss decisions with worked examples |
| **Writing Requirements That Pass** | Acceptance-criteria-first requirements that survive `/gvm-test-cases` Phase 4; five common failure modes with before/after examples |
| **Standalone /gvm-doc-write** | Producing presentations, strategy, newsletters, and prose grounded in named experts — outside the pipeline |
| **Engineering Leader's Guide to GVM** | Adopting the methodology — what it changes, what it costs, how to roll it out |
| **/gvm-analysis Training** | Privacy-preserving exploratory data analysis with Tukey, Cleveland, Hyndman & Athanasopoulos grounding |

### Blog

`blog-announcing-gvm.html` — a short introduction to the methodology for engineers who want the argument before the detail.

## Quick start

Install the plugin:

```bash
git clone <repository-url>
claude plugin add grounded_vibe_methodology/grounded-vibe-methodology
```

Verify it works:

```
/gvm-status
```

Start a project:

```
/gvm-requirements
```
