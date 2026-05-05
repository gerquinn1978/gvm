# Elicitation Techniques — Expert Reference

This file is actively consulted during requirements conversations. It provides techniques organized by expert, with citations to authoritative works so Claude can draw on its training knowledge of these sources.

---

## Always-Active Experts

### Karl Wiegers

**Source:** *Software Requirements* (3rd ed., with Joy Beatty), Microsoft Press

**Role in this skill:** Requirements classification, prioritization, document structure.

**Key techniques to apply:**

- **Requirements classification** (Ch. 1-2): Distinguish between business requirements (why), user requirements (who/what), and functional requirements (how the system behaves). Every requirement gathered should be classified.
- **MoSCoW prioritization** (Ch. 16): Must / Should / Could / Won't. Apply to every requirement. Ask the user: "If this were missing at launch, would the product fail its purpose?" Use "Won't" for items explicitly deferred to future versions (distinct from "Out of Scope" which means never).
- **Ambiguity indicators** (Ch. 12): Watch for words like "appropriate", "reasonable", "user-friendly", "fast", "flexible". These signal requirements that need quantification or clarification.
- **Elicitation interviews** (Ch. 7): Context-free questions first (scope, goals, users), then context-sensitive (features, constraints, interactions). Move from open to closed questions.
- **Requirements attributes** (Ch. 18): Each requirement should be traceable — unique ID, priority, source (which conversation turn it emerged from), stability (is this likely to change?).

**When to reference:** Structure and classify requirements as they emerge. Apply prioritization before finalizing each section.

---

### Gause & Weinberg

**Source:** *Exploring Requirements: Quality Before Design*, Dorset House

**Role in this skill:** Questioning technique, surfacing hidden assumptions, ambiguity resolution.

**Key techniques to apply:**

- **Context-free questions** (Ch. 4-5): Questions that work regardless of domain. Use these especially at the start and when entering new territory:
  - "Who is the client for this?"
  - "What would a highly successful solution look like?"
  - "What problems does this solve?"
  - "What problems could this create?"
  - "What environment will this operate in?"
- **The "is there anything else?" probe** (Ch. 6): After exploring a domain, always ask what was missed. Users often hold back their most important requirement because they assume it's obvious.
- **Naming ambiguity** (Ch. 8): When the user uses a term, ask what they mean by it. "Fast" to a user might mean 100ms or 5 seconds. Never assume shared vocabulary.
- **Test case heuristic** (Ch. 10): "How would you know if this requirement was satisfied?" If neither you nor the user can describe a test, the requirement is too vague.
- **Assumption surfacing** (Ch. 9): Explicitly ask "What are we assuming here?" after each major domain. Unstated assumptions are the #1 source of requirements defects.

**When to reference:** Throughout the conversation, especially when probing new domains, encountering vague language, or sensing the user is holding back.

---

### Jeff Patton

**Source:** *User Story Mapping*, O'Reilly Media

**Role in this skill:** User journey discovery, workflow decomposition, broad-to-specific elicitation.

**Key techniques to apply:**

- **Story mapping backbone** (Ch. 1-3): Start with the big activities the user performs (left to right = time). Then decompose each activity into tasks. Then decompose tasks into details/variations. This gives the conversation a natural structure: broad first, then drill down.
- **"Tell me about a typical day"** (Ch. 5): Ask the user to walk through how they (or their target user) would use the app from start to finish. This surfaces workflows, pain points, and priorities naturally.
- **The "now" vs "later" slice** (Ch. 8): For each workflow, identify what's needed for the first usable version vs. what can come later. This feeds directly into MoSCoW prioritization.
- **Output is understanding, not documentation** (Ch. 4): The goal of story mapping is shared understanding. If the user and Claude agree on the journey, the documentation follows. Don't over-formalize during discovery.

**When to reference:** When exploring user-facing functionality, discovering workflows, and deciding how to sequence requirements by priority.

---

### Alan Cooper

**Source:** *About Face: The Essentials of Interaction Design* (4th ed.), Wiley

**Role in this skill:** Persona creation, goal-directed requirements — answering "who is this for?"

**Key techniques to apply:**

- **Lightweight persona** (Ch. 3-5): Create a one-paragraph persona: name, role, primary goal, context, key frustration. This doesn't need to be elaborate — the point is to force specificity. "A user" is not a persona. "Sarah, a busy parent who needs to compare school districts while commuting" is.
- **Goal-directed requirements** (Ch. 6): Requirements should trace to persona goals. For each requirement, you should be able to answer: "Which persona goal does this serve?" If it serves none, challenge whether it belongs.
- **Three levels of goals** (Ch. 6):
  - Experience goals: how the user wants to feel (confident, not overwhelmed)
  - End goals: what the user wants to accomplish (find a house in a good school district)
  - Life goals: who the user wants to be (a responsible parent)
  - Requirements should primarily serve end goals but not violate experience goals.
- **The "elastic user" problem** (Ch. 3): Without a persona, "the user" becomes whoever is convenient for the current argument. A persona keeps requirements consistent.

**When to reference:** Early in discovery — establish the persona before diving into functional requirements. Revisit when a requirement seems disconnected from any user goal.

---

### JTBD — Jobs to Be Done

**Sources:**
- Clayton Christensen, *Competing Against Luck*, Harper Business
- Bob Moesta, *Demand-Side Sales 101*, Lioncrest

**Role in this skill:** Job framing — answering "why would anyone use this?" and surfacing emotional/social requirements.

**Key techniques to apply:**

- **The job statement** (Christensen, Ch. 2): Frame the core purpose as: "When [situation], I want to [motivation], so I can [expected outcome]." This becomes the anchor for the entire requirements document.
- **Four forces of progress** (Moesta, Ch. 3-4):
  - Push: frustration with current situation
  - Pull: attraction of new solution
  - Anxiety: fear of the new (learning curve, risk, migration)
  - Habit: comfort with the status quo
  - Requirements should amplify push/pull and reduce anxiety/habit.
- **Functional, emotional, social dimensions** (Christensen, Ch. 3): Every job has all three. Functional: "find a house." Emotional: "feel confident I'm making the right choice." Social: "show my family I did thorough research." The emotional and social dimensions often drive design decisions more than the functional ones.
- **"Tell me about the last time..."** (Moesta): Instead of asking what the user wants the app to do, ask about the last time they tried to solve this problem. What did they use? Where did it fail? This surfaces real requirements, not hypothetical ones.

**When to reference:** At the very start — establish the job before diving into features. Also when prioritizing: requirements that serve the core job are Must-haves; those that don't are Should/Could.

---

## Conditionally-Activated Expert

### Suzanne & James Robertson (Volere)

**Source:** *Mastering the Requirements Process* (3rd ed.), Addison-Wesley

**Role in this skill:** Completeness categories for complex systems. Activated when signals indicate non-trivial non-functional concerns.

**Activation signals:** Authentication/authorization, payments, third-party API integrations, personal/sensitive data, offline/sync requirements, multi-platform targets, accessibility needs, regulatory/compliance mentions.

**Key techniques to apply:**

- **Volere requirement categories** (Ch. 9-12): Use as a checklist to probe areas the conversation hasn't covered:
  - Look and feel requirements
  - Usability and humanity requirements
  - Performance requirements (speed, precision, capacity)
  - Operational and environmental requirements
  - Maintainability and support requirements
  - Security requirements (access, integrity, privacy, audit)
  - Cultural requirements
  - Compliance requirements (legal, standards)
- **Fit criteria** (Ch. 14): Every non-functional requirement needs a measurable fit criterion. "The system should be fast" → "Page load under 2 seconds on 3G." This makes requirements testable.
- **Requirement quality gateway** (Ch. 15): Before finalizing a requirement, check: Is it traceable? Is there a fit criterion? Is it achievable? Is it non-redundant?

**When to reference:** After core functional requirements are established, when complexity signals have been detected. Run through relevant Volere categories as a gap analysis.
