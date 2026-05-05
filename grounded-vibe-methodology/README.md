# Grounded Vibe Methodology (GVM) — Reference Implementation

The reference implementation of the Grounded Vibe Methodology as a Claude Code plugin. Each pipeline phase activates named authorities — requirements experts, test design specialists, architecture practitioners — rather than drawing on undifferentiated training data. In blind experiments, fully grounded output scored significantly higher than ungrounded output across multiple quality dimensions.

## Installation

### Quickest: two commands

```bash
git clone <repository-url>
claude plugin add grounded_vibe_methodology/grounded-vibe-methodology
```

That's it. Run `/gvm-status` in Claude Code to verify — if it responds, the plugin is working.

### Alternative installation methods

<details>
<summary>Install from GitHub marketplace (auto-updates)</summary>

Add the marketplace to your Claude Code settings file (`~/.claude/settings.json` for global, or `.claude/settings.json` for a single project):

```json
{
  "extraKnownMarketplaces": {
    "gvm-marketplace": {
      "source": "github",
      "repo": "<owner/repository>"
    }
  }
}
```

Then enable the plugin in the same file:

```json
{
  "enabledPlugins": {
    "grounded-vibe-methodology@gvm-marketplace": true
  }
}
```

</details>

<details>
<summary>Install from a downloaded zip</summary>

Download and unzip the repository, then install from the local path:

```bash
claude plugin add /path/to/grounded-vibe-methodology
```

The path must point to the `grounded-vibe-methodology/` directory containing `.claude-plugin/plugin.json`.

</details>

<details>
<summary>Manual copy (no plugin manager)</summary>

Copy the skill directories directly:

```bash
cp -R grounded-vibe-methodology/skills/gvm-* ~/.claude/skills/
```

</details>

### Verify installation

Run `/gvm-status` in Claude Code. If the plugin is installed correctly, it will report the pipeline state for your current directory. If the command is not recognised, the plugin is not loaded — check that `plugin.json` is at the expected path and restart Claude Code.

## Quick Start

**New project:** Run `/gvm-requirements` with your project idea. For specialised domains (financial services, healthcare, regulated industries), run `/gvm-init` first to load industry experts before requirements start.

**Existing codebase:** Run `/gvm-site-survey` to diagnose the codebase and get a recommended entry point.

See the [overarching user guide](skills/gvm-design-system/docs/plugin-guide.html) (copied to `~/.claude/gvm/docs/plugin-guide.html` on first run) for detailed walkthroughs.

## Skills

| Command | Phase | Description |
|---------|-------|-------------|
| `/gvm-init` | Expert Calibration (optional, recommended for specialised domains) | Selects industry domain experts and scores the roster before requirements start |
| `/gvm-site-survey` | Codebase diagnosis & health assessment | Scores an existing codebase across multiple dimensions, diagnoses architectural state, selects experts, routes to the appropriate pipeline phase |
| `/gvm-impact-map` | Discovery (greenfield, optional) | Produces an impact-map.md artefact (Goals → Actors → Impacts → Deliverables) that downstream `/gvm-requirements` gates against for traceability |
| `/gvm-requirements` | Requirements elicitation | Expert-guided conversation to produce structured, prioritised requirements |
| `/gvm-test-cases` | Test case generation | Generates acceptance tests from requirements using test design techniques |
| `/gvm-tech-spec` | Technical specification | Produces focused spec documents with adaptive decomposition based on complexity; Phase 5 enforces MVP-1 (chunk sequence builds a thin end-to-end vertical slice first) |
| `/gvm-design-review` | Design validation | Reviews data models, UI/UX, and API contracts against requirements before build; Panel D Pass 3 flags designs that structurally prevent MVP-1 |
| `/gvm-walking-skeleton` | Integration scaffolding (pre-build, optional) | Produces a runnable skeleton exercising every external boundary and a `boundaries.md` registry that downstream `/gvm-build` and `/gvm-test` gate against |
| `/gvm-build` | Implementation | Executes the implementation guide chunk by chunk with strict TDD; wiring-matrix Hard Gates ensure every built module has a consumer call site; Hard Gate 9 mirrors MVP-1 on the read side |
| `/gvm-code-review` | Code review | Dispatches parallel expert panels as subagents to review implementation code |
| `/gvm-test` | Build verification | Integration seam audit, smoke testing, stub audit; produces a Ship-ready / Demo-ready / Not-shippable verdict |
| `/gvm-explore-test` | Exploratory testing (post-test, optional) | Practitioner-driven timeboxed charter; captures defects in Given/When/Then form; produces an artefact `/gvm-test` reads via VV-4(d) |
| `/gvm-doc-write` | Document creation | Pipeline mode (README, CHANGELOG, user guides, API docs) and standalone mode (presentations, strategy, newsletters, training, status reports, whitepapers) |
| `/gvm-doc-review` | Quality audit | Cross-cutting review that scores documents against expert criteria |
| `/gvm-deploy` | Release preparation | Version bump, release notes, documentation accuracy check, changelog, and git tag |
| `/gvm-analysis` | Privacy-preserving data analysis (standalone) | Reads CSV / xlsx / parquet / JSON; produces a grounded findings report with real per-column stats, outliers, time-series, drivers, and a self-contained HTML hub. Raw rows never enter Claude's context. |
| `/gvm-status` | Pipeline diagnostic | Shows pipeline progress, staleness detection, and expert engagement summary |
| `/gvm-experts` | Expert management | Score, rescore, discover, and manage experts in the roster |
| `/gvm-design-system` | Shared design assets | Tufte/Few-styled HTML and Markdown templates used by all document-producing skills |

## Pipeline

```
Greenfield (entry points: pick one)

  /gvm-init           (optional — specialised domains; calibrates expert roster)
  /gvm-impact-map     (optional — outcome-framing first; produces impact-map.md)
          ↓
  /gvm-requirements → /gvm-test-cases → /gvm-tech-spec → /gvm-design-review →
  /gvm-walking-skeleton (optional — wires external boundaries before build) →
  /gvm-build → /gvm-code-review → /gvm-test →
  /gvm-explore-test (optional — practitioner-driven exploratory tour) →
  /gvm-doc-write → /gvm-doc-review → /gvm-deploy
                                              ↕
                                    /gvm-doc-review (any phase)


Existing Codebases:

  /gvm-site-survey
          ↓ routes based on diagnosis + work type
  /gvm-requirements  or  /gvm-tech-spec  or  /gvm-build  or  /gvm-doc-review
          ↓                     ↓                  ↓
          → continues through pipeline as above →

Standalone (outside the pipeline):

  /gvm-doc-write → presentations, strategy, newsletters, training, status reports, whitepapers
  /gvm-doc-review → reviews any document type (pipeline or standalone)
  /gvm-analysis  → privacy-preserving exploratory data analysis on any tabular file
```

Each phase reads the output of the previous phase, activates the relevant expert panel, and produces paired HTML + Markdown output — one for human review, one for AI consumption downstream.

## How It Works

GVM organises expertise in three tiers:

- **Tier 1 — Process Experts (Always Active)** — govern the methodology for each phase
- **Tier 2 — Domain Specialists (Conditional)** — activate when specific software or industry domains are encountered
- **Tier 3 — Stack Specialists (Post-Decision)** — activate after technology choices are made

Expert definitions live in reference files, not hardcoded in skills. You can swap, add, or score experts without modifying any skill logic using `/gvm-experts`. Pipeline skills discover and score experts automatically as needed. For specialised domains, `/gvm-init` loads industry experts upfront; for existing codebases, `/gvm-site-survey` selects experts based on what it finds.

GVM also blends with organisational knowledge. Published experts are activated via citation keys (the model already has their work). Internal standards — coding conventions, house style guides, compliance frameworks — are provided as verbatim reference files.

## User Data

GVM stores user-specific data in `~/.claude/gvm/`, separate from the plugin install path. This directory is created automatically on the first invocation of any GVM skill and is never overwritten by plugin updates.

```
~/.claude/gvm/
├── docs/
│   └── plugin-guide.html        ← overarching user guide (copied from plugin on each run)
├── expert-activations.csv       ← which experts were loaded/cited per project (append-only)
├── discovered-experts.jsonl     ← experts discovered during pipeline runs (append-only)
└── rescore-log.jsonl            ← user-initiated rescores (append-only)
```

Discovered experts and rescores survive plugin updates. When a plugin update overwrites the canonical reference files, the next skill invocation re-inserts any discovered experts and re-applies any user rescores from these logs.

## User Guides

| Skill | Guide |
|-------|-------|
| **Overarching Guide** | `~/.claude/gvm/docs/plugin-guide.html` (source: `skills/gvm-design-system/docs/plugin-guide.html`) |
| `/gvm-init` | `skills/gvm-init/docs/user-guide.html` |
| `/gvm-site-survey` | `skills/gvm-site-survey/docs/user-guide.html` |
| `/gvm-impact-map` | `skills/gvm-impact-map/docs/user-guide.html` |
| `/gvm-requirements` | `skills/gvm-requirements/docs/user-guide.html` |
| `/gvm-test-cases` | `skills/gvm-test-cases/docs/user-guide.html` |
| `/gvm-tech-spec` | `skills/gvm-tech-spec/docs/user-guide.html` |
| `/gvm-design-review` | `skills/gvm-design-review/docs/user-guide.html` |
| `/gvm-walking-skeleton` | `skills/gvm-walking-skeleton/docs/user-guide.html` |
| `/gvm-build` | `skills/gvm-build/docs/user-guide.html` |
| `/gvm-code-review` | `skills/gvm-code-review/docs/user-guide.html` |
| `/gvm-test` | `skills/gvm-test/docs/user-guide.html` |
| `/gvm-explore-test` | `skills/gvm-explore-test/docs/user-guide.html` |
| `/gvm-doc-write` | `skills/gvm-doc-write/docs/user-guide.html` |
| `/gvm-doc-review` | `skills/gvm-doc-review/docs/user-guide.html` |
| `/gvm-deploy` | `skills/gvm-deploy/docs/user-guide.html` |
| `/gvm-analysis` | `skills/gvm-analysis/docs/user-guide.html` |
| `/gvm-status` | `skills/gvm-status/docs/user-guide.html` |
| `/gvm-experts` | `skills/gvm-experts/docs/user-guide.html` |
| Design System (internals) | `skills/gvm-design-system/docs/user-guide.html` |

## Directory Structure

```
grounded-vibe-methodology/
├── .claude-plugin/
│   └── plugin.json
├── README.md
└── skills/
    ├── gvm-init/              # Expert Calibration (greenfield entry point)
    │   ├── SKILL.md
    │   └── docs/
    ├── gvm-site-survey/       # Codebase diagnosis & health assessment
    │   ├── SKILL.md
    │   └── docs/
    ├── gvm-impact-map/        # Discovery (Goals → Actors → Impacts → Deliverables)
    │   ├── SKILL.md
    │   ├── docs/
    │   └── references/
    ├── gvm-requirements/      # Requirements elicitation
    │   ├── SKILL.md
    │   ├── docs/
    │   └── references/
    ├── gvm-test-cases/        # Test case generation
    │   ├── SKILL.md
    │   ├── docs/
    │   └── references/
    ├── gvm-tech-spec/         # Technical specification
    │   ├── SKILL.md
    │   ├── docs/
    │   └── references/
    ├── gvm-design-review/     # Design validation
    │   ├── SKILL.md
    │   └── docs/
    ├── gvm-walking-skeleton/  # Integration scaffolding (boundaries.md + runnable skeleton)
    │   ├── SKILL.md
    │   ├── docs/
    │   ├── references/
    │   └── scripts/
    ├── gvm-build/             # Implementation
    │   ├── SKILL.md
    │   ├── docs/
    │   └── references/
    ├── gvm-doc-review/        # Quality audit
    │   ├── SKILL.md
    │   ├── docs/
    │   └── references/
    ├── gvm-code-review/       # Code review
    │   ├── SKILL.md
    │   └── docs/
    ├── gvm-status/            # Pipeline diagnostic
    │   ├── SKILL.md
    │   └── docs/
    ├── gvm-test/              # Build verification (integration, smoke, stub audit)
    │   ├── SKILL.md
    │   └── docs/
    ├── gvm-explore-test/      # Practitioner-driven exploratory testing
    │   ├── SKILL.md
    │   ├── docs/
    │   └── scripts/
    ├── gvm-deploy/            # Release preparation (version, changelog, tag)
    │   ├── SKILL.md
    │   └── docs/
    ├── gvm-doc-write/         # Standalone document creation
    │   ├── SKILL.md
    │   ├── docs/
    │   └── references/
    ├── gvm-experts/           # Expert management (scoring, discovery, roster)
    │   ├── SKILL.md
    │   └── docs/
    ├── gvm-analysis/          # Privacy-preserving exploratory data analysis
    │   ├── SKILL.md
    │   ├── docs/
    │   ├── scripts/
    │   ├── templates/
    │   ├── tests/
    │   └── pyproject.toml
    └── gvm-design-system/     # Shared design assets & reference files
        ├── SKILL.md
        ├── docs/
        └── references/
```

## Authors

Conor Brennan & Gerard Quinn

## License

MIT
