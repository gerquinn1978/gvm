*Process reference file — no expert scoring applies. Defines the source verification dispatch protocol.*

# Source Verification Protocol

Shared agent dispatch pattern for verifying GVM output against external seed documents. Used by `/gvm-requirements` (Phase 4b), `/gvm-test-cases` (Phase 4b), and `/gvm-tech-spec` (Phase 6b) when the skill's input was derived from a user-provided external document.

Extracted per Fowler's Rule of Three — three skills had near-identical verification prompts.

---

## When to Run

Only when the skill received an external document as seed input. If the user provided requirements/test cases/specs from another tool or process, verify that the GVM output faithfully represents the source before finalising.

## Agent Dispatch

Dispatch an independent verification agent that has **not** seen the elicitation/generation conversation. The agent compares source to output with fresh eyes.

**Agent prompt template** (substitute `{artefact_type}`, `{artefact_plural}`, and `{fourth_check}` per skill):

```
You are verifying GVM {artefact_plural} against the original {artefact_type} document they were derived from. Read both documents and produce a verification report covering:

1. **Completeness** — every item in the source must appear in the GVM output (as a {artefact_type}, or explicitly noted as out of scope). List any source items with no corresponding GVM entry.
2. **Accuracy** — for each mapped item, check that the GVM version preserves the intent. Flag any where meaning, scope, or technical approach has changed without justification.
3. **Hallucination** — identify any GVM items that have no basis in the source document and were not introduced during the expert-guided conversation. These may be valid additions from expert analysis, but they must be flagged for user confirmation.
4. {fourth_check}

Present findings as a table: Source item | GVM ID/location | Status (mapped/missing/altered/added) | Notes.
```

### Skill-specific fourth check

| Skill | `{artefact_type}` | `{artefact_plural}` | `{fourth_check}` |
|-------|--------------------|----------------------|-------------------|
| `/gvm-requirements` | requirement | requirements | **Priority alignment** — if the source has priorities, severity levels, or MoSCoW tags, check consistency. Flag mismatches. |
| `/gvm-test-cases` | test case | test cases | **Traceability** — check that requirement traceability tags are consistent between source and GVM output. |
| `/gvm-tech-spec` | specification | technical specifications | **Consistency** — check that technology choices, naming conventions, and component boundaries are consistent between source and GVM output. |

## Resolution Pattern

After the agent returns, resolve findings with the user:

1. **Missing items** — ask the user whether each was intentionally excluded or should be added. Add confirmed items.
2. **Altered items** — present the source wording alongside the GVM wording. User confirms which is correct.
3. **Hallucinated items** — present them: "These were added during elicitation and don't appear in your original document. Confirm they should stay, or remove them."
4. **Fourth-check mismatches** — present both versions and let the user decide.

**Repeat threshold:** If changes are substantial (>20% of items modified), re-run the verification loop. Otherwise, proceed to the finalise phase.
