# Elicitation Safety Net Checklist

Run through this checklist before finalizing the requirements document. For each item, either confirm it was covered during elicitation or explicitly note it as not applicable (with reason) in the Assumptions section.

This checklist synthesizes coverage areas from all panel experts. It is a gap-finder, not a questionnaire — if a topic was already thoroughly explored during conversation, check it off without re-asking.

---

## Core Coverage (Every Project)

### Purpose & Framing
- [ ] Job statement defined (JTBD: "When [situation], I want to [motivation], so I can [outcome]")
- [ ] Target user/persona established (Cooper: at minimum — name, goal, context)
- [ ] Problem being solved is clear (Gause & Weinberg: "What would a highly successful solution look like?")
- [ ] Push/pull forces identified (Moesta: why now? what's broken about the current approach?)

### Functional Requirements
- [ ] All major user workflows identified (Patton: story mapping backbone)
- [ ] Each workflow decomposed into tasks (Patton: activities → tasks → details)
- [ ] Requirements classified: business / user / functional (Wiegers)
- [ ] Every requirement has a unique ID and MoSCoW priority
- [ ] Ambiguous terms clarified (Gause & Weinberg: "What do you mean by X?")
- [ ] Each requirement is testable (Gause & Weinberg: "How would you know if this was satisfied?")

### Prioritization
- [ ] MoSCoW applied to all requirements (Wiegers)
- [ ] "Now vs later" slice identified for user journeys (Patton)
- [ ] Must-haves trace to the core job (JTBD)
- [ ] User confirmed priorities

### Cross-Cutting Sections
- [ ] Assumptions documented and confirmed with user
- [ ] Open questions logged (unresolvable in this conversation)
- [ ] Out of scope explicitly stated
- [ ] "Is there anything else?" asked (Gause & Weinberg)

---

## Escalated Coverage (When Triggered)

Only probe these if activation signals were detected during the conversation. Note "N/A" for categories that don't apply.

### Security & Privacy (Volere)
- [ ] Authentication / authorization model
- [ ] Data privacy requirements
- [ ] Sensitive data handling (storage, transmission, retention)
- [ ] Audit / logging requirements

### Compliance & Legal (Volere)
- [ ] Regulatory requirements (GDPR, HIPAA, PCI-DSS, etc.)
- [ ] Terms of service / user agreements
- [ ] Data residency constraints

### Performance (Volere)
- [ ] Response time expectations (with fit criteria)
- [ ] Capacity / load expectations
- [ ] Availability requirements

### Integration (Volere)
- [ ] Third-party APIs / services identified
- [ ] Failure handling for external dependencies
- [ ] Rate limits / quotas
- [ ] Data format / protocol requirements

### Platform & Environment (Volere)
- [ ] Target platforms (web, desktop, mobile — which?)
- [ ] Browser / OS / device constraints
- [ ] Offline / sync requirements
- [ ] Responsive / adaptive design needs

### Accessibility (Volere)
- [ ] WCAG conformance level
- [ ] Assistive technology support
- [ ] Keyboard navigation requirements

### Payments & Financial (Volere)
- [ ] Payment processing requirements
- [ ] Currency handling
- [ ] Refund / dispute flows
- [ ] Financial reporting / audit trail

---

## Final Quality Gate

Before declaring the document complete (adapted from Wiegers Ch. 18 and Robertsons Ch. 15):

- [ ] Every requirement traces to a persona goal (Cooper)
- [ ] Every requirement has exactly one MoSCoW priority
- [ ] No requirement uses unquantified terms ("fast", "user-friendly", "secure") without a fit criterion
- [ ] No duplicate or contradictory requirements
- [ ] HTML and MD versions are in sync
- [ ] Requirements index table is complete and accurate
- [ ] User has confirmed the final document
