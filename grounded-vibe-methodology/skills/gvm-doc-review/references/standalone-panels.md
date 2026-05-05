# Standalone Document Review Panels

Loaded by `/gvm-doc-review` when reviewing standalone documents (whitepapers, strategy, presentations, newsletters, training materials, user documentation). Do not load for pipeline artefacts.

## Six-Test Finding Quality Gate (panel emit threshold)

Per `SKILL.md` Hard Gate 8: panels apply the six-test gate before emitting Critical or Important findings. A finding earns Critical/Important status only if it passes at least one of:

1. **Integrity** — A reader who can verify the claim against a published source would find it wrong, partially wrong, or unsupported. Misquotes, wrong year/edition, fabricated statistic, broken citation chain.
2. **Misdirection (load-bearing)** — A reader could form the wrong understanding of a load-bearing claim (thesis, central section argument, numerical result, methodology decision). Peripheral misdirection is Minor.
3. **Reproducibility** — A researcher attempting to replicate an empirical claim from the document alone would lack a piece of information they need. Applies to methodology and empirical papers.
4. **Honesty of scope** — The document claims more than its evidence supports, OR fails to flag a significant limitation where the unqualified claim would mislead.
5. **Audience hospitality** — The document assumes reader knowledge inconsistent with its stated audience. Reader forms no understanding rather than wrong understanding.
6. **Cut-damage protection** — When a finding *recommends a cut*, the cut must NOT damage orientation, evidence, scope-limits, or honesty disclaimers. A finding that fails this test is rejected — the section stays.

Findings that fail all six tests are emitted as Minor `[POLISH]`. Panels MUST tag each Important/Critical finding with the test(s) it passes (e.g., `[passes: Integrity, Reproducibility]`) so synthesis can verify the gate was applied.

The gate replaces the generic "consumer FAIL" criterion for standalone documents. Pipeline artefacts (requirements, test cases, specs) continue to use consumer-FAIL because their consumers are concrete downstream skills.

## Panel A: Argument & Structure

**What to scan:** Does the argument hold? Is the structure by message, not by topic? Does every section answer "so what?"? Is there a clear thesis or central message? Does the conclusion follow from the evidence?

**Experts assigned:** Doumont (structure by message, answer "so what?" at every level), McKee (narrative arc — progressive complications, inciting incident where applicable).

**Scanning method:**
- **Pass 1 — Systematic scan:** Read each section. For every section heading, verify it states a message, not a topic. For every paragraph, verify it advances the argument. Identify any section that exists for completeness rather than purpose.
- **Pass 2 — Cross-reference scan:** Trace the argument from opening claim through evidence to conclusion. Flag logical gaps, unsupported leaps, and conclusions that don't follow from the presented evidence.

### Type-Specific Argument Criteria

**Strategy documents** (load `domain/strategy.md`):
1. Kernel completeness — diagnosis, guiding policy, coherent actions. Missing any element is Critical.
2. Diagnosis quality — identifies the crux, not just symptoms.
3. Guiding policy clarity — an approach, not an aspiration.
4. Action coherence — actions reinforce each other.
5. Bad strategy signals — fluff, goals masquerading as strategy.

**Presentations** (load `domain/presentation-design.md`):
1. One idea per slide — multi-point slides are Critical.
2. Headlines as sentences — state the point, not the topic.
3. Narrative arc — beginning, middle, end.
4. Visual restraint — signal-to-noise ratio.
5. Data slide clarity — "so what?" in the headline.

**Newsletters** (load `domain/newsletter.md`):
1. Single core message — one message, not everything.
2. Reader utility — the reader can act on this.
3. Hook quality — opening earns the next sentence.

**Training materials** (load `domain/training.md`):
1. Learning objectives — stated at start, each section maps to one.
2. Gap type match — is training the right solution?
3. Practice activities — exercises, not just information.
4. Segmentation — learner-paced units.

## Panel B: Factual Accuracy & Attribution

**What to scan:** Are factual claims verifiable? Are statistics accurately stated? Are expert attributions correct — does the cited expert actually say what's attributed to them? Are dates, names, and publication details correct?

**Experts assigned:** Orwell (never say more than you know to be true), Weinberg (make the problem visible — incorrect attributions hide the real source of an idea).

**Scanning method:**
- **Pass 1 — Systematic scan:** Read each section. For every factual claim, expert citation, statistic, and named result, note whether it is verifiable from the document's own sources or common knowledge. Flag unverifiable claims.
- **Pass 2 — Cross-reference scan:** For each expert attribution, verify the claimed principle matches the cited work. For each statistic, check internal consistency (do the numbers add up?).

## Panel C: Prose Quality & Audience Fit

**What to scan:** Is it clear? Is it written for the stated audience? Does it scan well? Is every word earning its place?

**Experts assigned:** Zinsser (clarity, simplicity, every word earns its place), Williams (subjects near verbs, avoid nominalisations), Orwell (no dying metaphors, no pretentious diction), Redish (write for scanning — headings as questions, front-load paragraphs).

**Scanning method:**
- **Pass 1 — Systematic scan:** Read each paragraph. Check: clarity (Zinsser), directness (Williams), freedom from jargon (Orwell), scannability (Redish). For each paragraph, identify the audience assumption — does it match the stated audience?
- **Pass 2 — Cross-reference scan:** Check tone and register consistency across the document. Flag shifts where the document talks to experts in one section and beginners in another without signposting the transition.

### Type-Specific Prose Criteria

**User documentation** (load `domain/user-documentation.md`):
1. Task-oriented structure — organised by what the user needs to do.
2. Self-contained pages — each page understood independently.
3. Microcopy quality — error messages, button labels, empty states.
4. Accuracy — matches the implemented system.
5. Scannability — headings, numbered steps, bold key terms.

## Panel D: Scoring & Rubric Application

**What to scan:** Score each dimension against the review criteria from `review-criteria.md`. Count rather than judge.

**Experts assigned:** Marzano (count don't judge), Stevens & Levi (analytic rubrics), Gilb (five-component criteria).

**Scanning method:**
- **Pass 1 — Systematic scan:** For each scoring dimension, evaluate the document against the rubric's specific thresholds. Record the evidence.
- **Pass 2 — Cross-reference scan:** Cross-check scores against findings from Panels A-C. A document with Critical argument failures should not score high on argument dimensions.
