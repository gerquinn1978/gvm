# Expert Scoring Methodology

The canonical reference for scoring experts and their works. Load this file when scoring is needed — during `/gvm-experts` direct invocation, `/gvm-init` expert calibration, or `/gvm-site-survey` expert selection.

---

## Score Format in Reference Files

Scores are recorded as a markdown table immediately after the expert's source citation and before the activation signals. Works are scored individually beneath their citation.

```markdown
## Philippe Jorion

**Source:** Philippe Jorion, *Value at Risk* (3rd ed.), McGraw-Hill (2006)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 4 | 5 | 3 | **Established** |

Evidence: foundational VaR text, cited in virtually every market risk publication since 1996; adopted as standard reference by risk management programmes globally; referenced in Basel Committee working papers.

**Work score — *Value at Risk* (3rd ed.):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 5 | 3 | 5 | **Established** |

Evidence: referenced in Alexander, Dowd, Hull, and Rebonato; set text at multiple university risk management programmes; 3 editions over 10 years.

**Activation signals:** ...
```

## Classification Bands

Both expert and work scores use the same classification:

| Classification | Average Score | Meaning |
|----------------|---------------|---------|
| **Canonical** | 4.5+ | Undisputed authority / definitive work |
| **Established** | 3.5–4.4 | Well-regarded, widely adopted |
| **Recognised** | 2.5–3.4 | Known in the field, useful but not definitive |
| **Emerging** | 1.5–2.4 | Newer, limited influence so far |
| **Provisional** | Below 1.5 | Unverified, use with caution |

**Valid classification labels (closed set):** Canonical, Established, Recognised, Emerging, Provisional. These are the ONLY valid labels. Do not use "Authoritative", "Expert", "Senior", or any other label — if the computed average falls in a band, use that band's label exactly as written above. Any label not in this list is an error.

**Dimension scores are integers (1–5). HARD GATE: Do not use half-integer scores (3.5, 2.5, 4.5, etc.). If you are uncertain between two integers, round UP and add an evidence note justifying the higher score. Half-integer scores invalidate the entry — any downstream skill loading the entry will flag it as non-conformant. This rule was added after repeated violations in rounds 1–3; it is non-negotiable.**

When the computed average lands exactly on a boundary (e.g., 4.5), classify upward. When primary and independent agent averages converge to a value within 0.1 of a boundary, flag as a boundary case and note it in the evidence for user review.

### Single Canonical Source

Each expert MUST have exactly one canonical score entry across all reference files. When an expert appears in multiple files (e.g., Fowler in architecture-specialists.md and domain-specialists.md), ONE file is the canonical source. All other files cross-reference it:

"*Expert scored in [canonical file]. Classification: [classification] (avg [N]).*"

The canonical source is the file where the expert's primary role is defined:
- Tier 1 process experts → `architecture-specialists.md`
- Domain specialists → the relevant `domain/{domain}.md` file
- Stack specialists → the relevant `stack/{stack}.md` file
- Industry specialists → the relevant `industry/*.md` file

Work scores for works cited only in a secondary file can appear in that file, but the expert-level scores must be a cross-reference, not a duplicate.

When loading a cross-referenced expert, use the canonical scores. Do not independently re-score.

## Scoring Operations

**Score on discovery:** When any GVM skill discovers a new expert via the self-improving roster, it scores the expert and their works inline, provides evidence for any score of 4 or 5, and dispatches an independent agent for verification (see below).

**Score retroactively:** To score an unscored expert in a reference file:
1. Read the reference file
2. For each expert without scores, assess the five expert dimensions and four work dimensions
3. Provide evidence for scores of 4 or 5
4. Dispatch an independent agent to verify (see below)
5. Edit the reference file to insert the score tables after each expert's citation

**Rescore:** To rescore an expert or work (e.g., a new edition was published, or you want to verify old scores):
1. Read the reference file
2. Assess the dimensions fresh — do not reference the existing scores
3. Dispatch an independent agent to verify
4. If the new scores differ from the old, present both to the user with rationale for the change
5. Update the reference file only with user approval

**Score all:** To score or rescore all experts in a reference file, apply the above process to each expert sequentially. Present a summary table at the end showing all experts, their classifications, and any changes.

## Independent Agent Verification

When scoring (discovery, retroactive, or rescore), dispatch an independent Agent as a subagent with:
- The expert name and works (no existing scores, no original agent's reasoning)
- Instructions to independently assess the expert and work scoring dimensions
- Instructions to provide evidence for any score of 4 or 5

Compare the two assessments:
- **Converge** (within 1 point on each dimension) — high confidence. Use the averaged scores.
- **Diverge** (2+ points on any dimension) — flag to the user. Present both sets of scores with evidence. The user decides.

## Process for Each Expert Scored

```
1. ASSESS — score the 5 expert dimensions and 4 work dimensions per work
2. EVIDENCE — for any score of 4 or 5, cite specific verifiable evidence
3. CLASSIFY — compute average, assign classification (Canonical → Provisional)
4. VERIFY — dispatch independent Agent subagent with:
   - Expert name and works only (no scores, no reasoning)
   - Instructions to independently assess all dimensions
   - Instructions to provide evidence for scores of 4+
5. COMPARE — check convergence/divergence
   - Within 1 point on all dimensions → high confidence, use averaged scores
   - 2+ point divergence on any dimension → flag to user with both assessments
6. UTILISATION — utilisation does not determine classification; it tests it. Classification is assessed from the five expert dimensions. Utilisation produces advisory flags that suggest when a reassessment may be warranted. Read `~/.claude/gvm/expert-activations.csv` and compute:
   - Per expert: total loaded, total cited, cite rate (cited/loaded)
   - Per work: total loaded, total cited, cite rate
   - If no data exists (new expert), note "No usage data — newly added"
   - Apply sample-size tiers to divergence analysis (expert-level activations only):
     - n < 3: report utilisation but label "insufficient data for divergence analysis" — do not flag
     - n = 3–9: flag divergence as "preliminary signal — monitor"
     - n ≥ 10: flag divergence normally — reliable signal
   - Divergence criteria (applied at expert level, not per-work):
     - Upward signal (may be underclassified): cite rate > 80% AND classification is Recognised or below
     - Downward signal (may be overclassified): cite rate < 40% AND classification is Established or above
   - Per-work utilisation is reported for information only; divergence flags are raised at expert level where sample size is sufficient
7. REPORT — write an HTML + MD scoring report (see below)
8. PRESENT — show the user a summary; the full detail is in the report
9. PERSIST — on user approval, edit the reference file
```

## Scoring Report

Every scoring operation produces a paired HTML and MD report following the shared Tufte/Few design system. Load `~/.claude/skills/gvm-design-system/references/tufte-html-reference.md` before the first write.

**Output location:** `scoring-reports/` directory in the current project.
- Paired HTML and MD: `scoring-reports/expert-scoring-001.html` and `scoring-reports/expert-scoring-001.md`, etc.
- Scan for existing files and increment. Never overwrite previous reports.
- The MD version provides a machine-readable record of all scores, classifications, and changes for downstream reference.

**Report structure:**

1. **Executive Summary** — date, scope (which file(s) scored), number of experts assessed, number of works assessed
2. **Expert Scorecard** — one table per expert:
   - Expert name, source citations
   - Expert score table: Authority, Publication, Breadth, Adoption, Currency, Classification
   - Evidence for each dimension scored 4 or 5
   - Expert utilisation (from activation log): total loaded, total cited, cite rate %, sample-size tier (insufficient / preliminary / reliable). If no activation data exists yet, show "No usage data — newly added."
   - Per-work score table: Specificity, Depth, Currency, Influence, Classification (one row per work)
   - Evidence for each work dimension scored 4 or 5
   - Per-work utilisation: loaded count, cited count, cite rate %. Reported per work for information — divergence flags are raised at expert level only.
3. **Independent Verification** — for each expert:
   - Primary agent scores vs independent agent scores (side-by-side table)
   - Convergence/divergence assessment per dimension
   - Overall confidence: High (all converge) / Flagged (any diverge)
4. **Utilisation Analysis** — if activation log data exists:
   - Expert utilisation table: expert name, total loaded, total cited, cite rate, classification, sample-size tier (insufficient < 3 / preliminary 3–9 / reliable ≥ 10)
   - Work utilisation table: expert, work, loaded, cited, cite rate, classification (informational — no divergence flags at work level)
   - Divergence flags (expert level only, gated by sample-size tier):
     - Insufficient (n < 3): no flags raised, table annotated "insufficient data"
     - Preliminary (n = 3–9): flag as "preliminary signal — monitor" with ⚠ marker
     - Reliable (n ≥ 10): flag normally with specific recommendation
   - Divergence criteria:
     - **Upward signal** — cite rate > 80% with classification Recognised or below → "may be underclassified"
     - **Downward signal** — cite rate < 40% with classification Established or above → "may be overclassified"
   - Sorted by cite rate descending — the most-used experts first
5. **Summary Table** — all experts in a single table:
   - Expert name, expert classification, number of works, highest-classified work, verification confidence, cite rate, sample-size tier, divergence flag (if any)
   - Sorted by classification (Canonical first, Provisional last)
6. **Changes** (rescore only) — if rescoring, show:
   - Old classification vs new classification per expert
   - Dimensions that changed by 2+ points highlighted
   - Rationale for significant changes
