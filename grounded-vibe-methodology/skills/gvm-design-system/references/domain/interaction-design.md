## Alan Cooper & Steve Krug — Interaction Design

**Sources:**
- Alan Cooper, *About Face: The Essentials of Interaction Design* (4th ed.), Wiley (2014)
- Steve Krug, *Don't Make Me Think, Revisited* (3rd ed.), New Riders (2014)

**Expert scores:**

| Expert | A | P | B | Ad | C | Avg | Tier |
|---|---|---|---|---|---|---|---|
| Alan Cooper | 5 | 4 | 4 | 4 | 3 | **4.0** | **Established** |
| Steve Krug | 4 | 4 | 3 | 5 | 3 | **3.8** | **Established** |

| Work | S | De | C | I | Avg | Tier |
|---|---|---|---|---|---|---|
| Cooper, *About Face* 4th ed | 4 | 4 | 3 | 5 | **4.0** | **Established** |
| Krug, *Don't Make Me Think, Revisited* | 4 | 3 | 3 | 5 | **3.75** | **Established** |

**Evidence (Cooper):** Authority — inventor of personas and goal-directed design. Work Influence — defined interaction design as profession.

**Evidence (Krug):** Adoption — 600,000+ copies. Work Influence — trunk test is standard usability vocabulary.

**Activation signals:** Frontend spec, user-facing forms, navigation flows, progress views, interactive UI, agent interaction UI

**Key techniques to apply:**

- **Goal-directed design** (Cooper, Ch. 6): Design from the user's goal, not the system's structure. The form should ask what the user wants to achieve, not expose internal parameters.
- **Personas drive UI decisions** (Cooper, Ch. 3-4): Reference the personas from the requirements document. How would Alex (outsider making a first relocation decision) experience this UI vs Sam (estate agent running for multiple clients)?
- **Don't make me think** (Krug, Ch. 1-3): Every screen should be self-evident. Labels, not icons. Conventions over originality. If a user has to stop and think about how something works, the design has failed.
- **Progressive disclosure** (Cooper, Ch. 10): Show the most important options first, reveal complexity on demand. The form should have sensible defaults with advanced options available but not overwhelming.
- **Error prevention over error handling** (Cooper, Ch. 14): Constrain inputs to valid values. Don't let the user submit a form that will fail — disable the submit button, validate inline.
- **Trunk test** (Krug, Ch. 6): On any page, the user should be able to answer: what site is this, what page am I on, what are the major sections, what are my options at this level, where am I in the scheme of things?

**When specifying frontend:**
- Define the information architecture (what pages/views exist and how they connect)
- For each view, specify: purpose, user goal, key interactions, data displayed, state transitions
- For forms, specify: fields, validation rules, defaults, what happens on submit
- For real-time views (progress, agent transparency), specify: what updates, how often, what interactions are available
