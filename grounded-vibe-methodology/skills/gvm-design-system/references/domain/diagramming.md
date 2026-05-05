## Edward Tufte & Martin Fowler — Technical Diagramming

**Sources:**
- Edward Tufte, *Visual Explanations: Images and Quantities, Evidence and Narrative*, Graphics Press (1997)
- Edward Tufte, *Envisioning Information*, Graphics Press (1990)
- Martin Fowler, *UML Distilled* (3rd ed.), Addison-Wesley (2004)


**Expert scores:**

| Expert | A | P | B | Ad | C | Avg | Tier |
|---|---|---|---|---|---|---|---|
| Edward Tufte | 5 | 5 | 4 | 5 | 3 | **4.4** | **Established** |

*Note: Tufte avg=4.4; within 0.1 of the Canonical boundary (4.5). If an independent rescore confirms any dimension increase, reclassifies to Canonical.*

*Martin Fowler scored in `architecture-specialists.md`. Classification: Canonical (avg 4.8).*

| Work | S | De | C | I | Avg | Tier |
|---|---|---|---|---|---|---|
| Tufte, *Visual Explanations* | 4 | 4 | 2 | 4 | **3.5** | **Established** |
| Tufte, *Envisioning Information* | 3 | 4 | 2 | 5 | **3.5** | **Established** |

*Fowler, *UML Distilled* work score canonical in `architecture-specialists.md`: Established (avg 3.5). Load canonical scores from that file; do not re-score independently.*

**Evidence (Tufte):** Authority=5 — Professor Emeritus of Political Science, Statistics, and Computer Science at Yale; four self-published works under Graphics Press; presidential appointment to Recovery Independent Advisory Panel (2010). Adoption=5 — assigned at Columbia data journalism programme; embedded in Observable/D3 documentation; NASA and CDC visualisation guidelines reference *The Visual Display* directly; "data-ink ratio" and "chartjunk" are standard vocabulary in data science and UX. *Envisioning Information* Influence — introduced small multiples.

**Additional theoretical sources:**
- Helen Purchase, *Experimental Research on Graph Drawing Aesthetics*, various papers (2000s) — empirical research on what makes diagrams readable
- Giuseppe Di Battista, Peter Eades, Roberto Tamassia, Ioannis Tollis, *Graph Drawing: Algorithms for the Visualization of Graphs*, Prentice Hall (1998) — the foundational textbook on graph layout algorithms
- Colin Ware, *Information Visualization: Perception for Design* (4th ed.), Morgan Kaufmann (2021) — perceptual science behind visual design


| Expert | A | P | B | Ad | C | Avg | Tier |
|---|---|---|---|---|---|---|---|
| Helen Purchase | 4 | 3 | 2 | 3 | 3 | **3.0** | **Recognised** |
| Di Battista et al. | 4 | 4 | 3 | 3 | 2 | **3.2** | **Recognised** |
| Colin Ware | 5 | 4 | 4 | 4 | 5 | **4.4** | **Established** |

*Note: Colin Ware avg=4.4; within 0.1 of the Canonical boundary (4.5). If an independent rescore confirms any dimension increase, reclassifies to Canonical.*

| Work | S | De | C | I | Avg | Tier |
|---|---|---|---|---|---|---|
| Purchase, papers | 5 | 4 | 3 | 4 | **4.0** | **Established** |
| Di Battista et al., *Graph Drawing* | 5 | 5 | 2 | 4 | **4.0** | **Established** |
| Ware, *Information Visualization* 4th ed | 4 | 5 | 5 | 5 | **4.75** | **Canonical** |

**Evidence (Purchase):** Authority — primary empirical researcher on graph drawing aesthetics. Work Specificity — directly measures which aesthetics affect comprehension.

**Evidence (Di Battista et al.):** Authority — definitive academic reference on graph layout algorithms. Work Depth — comprehensive mathematical treatment.

**Evidence (Ware):** Authority — leading perceptual science of visualisation. Currency — 4th ed 2021. Work Depth — rigorous perceptual science, 500+ pages. Work Influence — scientific foundation practitioners cite.

**Activation signals:** Always active when diagrams are being created. Every spec that contains a diagram triggers this specialist.

**Key principles from the theoretical foundations:**

- **Purchase's aesthetics hierarchy** (empirical research): Edge crossings are the strongest predictor of diagram comprehension errors. Minimising crossings matters more than minimising bends, which matters more than symmetry. Layout priority: (1) minimise crossings, (2) minimise bends, (3) maximise symmetry, (4) minimise area.
- **Orthogonal routing** (Di Battista et al.): Connectors should use horizontal and vertical segments only (orthogonal routing). Diagonal lines are harder to trace visually. Route connectors around obstacles, not through them.
- **Preattentive processing** (Ware, Ch. 5): Colour, size, orientation, and motion are processed preattentively (before conscious attention). Use these channels deliberately — a red box is noticed before a label is read. Don't waste preattentive channels on decoration.
- **Gestalt grouping** (Ware, Ch. 6): Elements that are close together are perceived as a group (proximity). Elements that look similar are perceived as related (similarity). Use spatial grouping and consistent visual style to convey architectural boundaries.

**Key principles from the practical experts:**

- **Smallest effective difference** (Tufte, *Envisioning Information*): Use the minimum visual distinction necessary to convey meaning. Don't use thick borders when thin ones suffice. Don't use colour where position already conveys the relationship.
- **No chartjunk in diagrams** (Tufte): No decorative shadows, gradients, 3D effects, or ornamental elements. Every pixel should convey information.
- **Layered information** (Tufte, *Visual Explanations*): Diagrams should work at multiple zoom levels — overview at a glance, detail on inspection. Use colour coding, line styles, and annotations for layers.
- **Only the diagrams that matter** (Fowler, *UML Distilled*, Ch. 1): Don't create diagrams for everything. A diagram should exist only when it communicates something that prose cannot. Fowler: "The most important thing about diagrams is that they should be useful."
- **Enough detail, no more** (Fowler, *UML Distilled*, Ch. 2-3): Show the relevant attributes and relationships, not every field. A diagram that shows everything shows nothing.

**Diagram review checklist (apply after every diagram is created):**

**Layout & Topology (checks 1–5):**

1. **No connector-box intersections** — trace every connector path segment against every box boundary mathematically, not by eyeballing. For each path segment, verify the x,y coordinates do not pass through any box's x-range AND y-range simultaneously. Orthogonal routing eliminates most issues — diagonal connectors are the primary source of accidental intersections. If a connector must cross another connector, mark the crossing clearly (gap or bridge).
2. **Hub nodes at centre** — if one node has significantly more connections than others (3+), place it centrally and arrange connected nodes radially around it (Purchase: radial layouts for star topologies). Do not force a hub node into a linear flowchart position — it creates congestion on one side.
3. **Each connection exits a different side of hub nodes** — when a box has multiple outgoing connections, they should exit from different sides or at least different positions on the same side. Never have multiple connectors emerging from the same point. This is the primary cause of visual congestion and apparent crossings.
4. **Minimal crossings** — if two connectors cross, the box positions are wrong. Rearrange boxes first, don't just reroute connectors. Per Purchase: crossing minimisation is the #1 predictor of diagram readability, more important than any other aesthetic.
5. **Orthogonal routing** — all connectors use horizontal and vertical segments only (Di Battista et al.). No diagonal connectors except for simple, short, unambiguous direct connections with no other connectors nearby. Orthogonal connectors are easier to trace and less likely to create visual ambiguity about which boxes they connect.

**Spatial Organisation (checks 6–8):**

6. **Consistent flow direction** — information should flow in one primary direction (top-to-bottom or left-to-right). Feedback/return paths flow in the opposite direction and should be visually distinct (dashed, different colour). Don't mix primary flow directions.
7. **Aligned elements** — boxes at the same logical level should share a common baseline. Use consistent spacing between rows/columns. Uneven spacing creates false grouping signals (Ware: Gestalt proximity).
8. **Connectors don't overlap** — two connectors should not share the same visual space for any significant length. If two connectors must run parallel, offset them by at least 10px. Overlapping connectors look like a single line and hide relationships.

**Labels & Notation (checks 9–12):**

9. **Readable labels** — minimum 12px for connector labels, 13px for entity/state names. Labels at 9-10px are consistently too small when diagrams render at typical screen sizes. Test readability at the diagram's `max-width` render size.
10. **Labels on straight segments, not corners** — position connector labels on the midpoint of a straight segment, never at a bend/corner where they overlap the turn and become ambiguous about which connector they describe.
11. **No label-label overlaps** — check every label's bounding box against every other label. Two labels must not occupy the same visual space even partially. Common where connectors run close together (e.g., a forward transition label overlapping a nearby resume path label). Fix by repositioning along the connector or shifting perpendicular.
12. **Consistent notation with legend** — same line style means the same type of relationship throughout. If the diagram uses more than one line style, colour, or dash pattern, include a legend. Don't rely on the caption alone — the legend should be inside the SVG.
13. **Caption** — every diagram has a figure number and descriptive caption below it. Reference the design rationale where applicable (e.g., "Purchase: radial layout for hub nodes").

**Overall Quality (checks 14–16):**

14. **Colour conveys meaning, not decoration** — if colour is used, it must encode information (e.g., status states, risk levels, domain boundaries). Every colour used must appear in the legend or caption. Don't use colour for visual interest alone.
15. **Self-contained** — the diagram must be understandable without reading the surrounding text. A colleague who sees only the diagram should understand the structure.
16. **Size proportional to complexity** — a 3-entity ERD doesn't need 800px width. A 10-entity ERD does. Scale to content. But err on the side of more space — cramped diagrams cause all the other problems (crossings, overlaps, small labels).
