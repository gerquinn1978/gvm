## Edward Tufte & Stephen Few — Data Presentation

**Sources:**
- Edward Tufte, *The Visual Display of Quantitative Information* (2nd ed.), Graphics Press (2001)
- Edward Tufte, *Envisioning Information*, Graphics Press (1990)
- Stephen Few, *Show Me the Numbers* (2nd ed.), Analytics Press (2012)
- Stephen Few, *Information Dashboard Design* (2nd ed.), Analytics Press (2013)

**Expert scores:**

*Edward Tufte scored in Technical Diagramming entry (domain/diagramming.md). Classification: Established (avg 4.4).*

| Expert | A | P | B | Ad | C | Avg | Tier |
|---|---|---|---|---|---|---|---|
| Stephen Few | 4 | 4 | 3 | 4 | 3 | **3.6** | **Established** |

| Work | S | De | C | I | Avg | Tier |
|---|---|---|---|---|---|---|
| Tufte, *Visual Display of Quantitative Information* 2nd ed | 4 | 5 | 2 | 5 | **4.0** | **Established** |
| Few, *Show Me the Numbers* | 5 | 4 | 3 | 4 | **4.0** | **Established** |
| Few, *Information Dashboard Design* | 5 | 4 | 3 | 4 | **4.0** | **Established** |

*Envisioning Information* scored in the Technical Diagramming entry (domain/diagramming.md). Classification: Established (avg 3.5).

**Evidence (Tufte):** *VDQI* Depth — most thorough treatment of statistical graphics. *VDQI* Influence — canonical data vis reference; introduced sparklines.

**Evidence (Few):** Authority — most rigorous practitioner voice post-Tufte. Adoption — standard in BI communities.

**Activation signals:** Data-heavy UI, comparison tables, dashboards, reports, brochure output, any screen showing quantitative data

**Key techniques to apply:**

- **Data-ink ratio** (Tufte): Maximise the share of ink devoted to data. Remove chartjunk — decorative borders, gradients, 3D effects, unnecessary gridlines.
- **Small multiples** (Tufte): When comparing across categories (e.g., candidate areas), use the same visual format repeated. Don't redesign the layout for each area.
- **Tables over charts when precision matters** (Few): If the user needs to read exact values (property prices, tax figures, school ratings), use a table. Charts are for trends and patterns.
- **Comparison is the core task** (Few): The user is comparing locations. Design every data display to facilitate comparison — aligned columns, consistent units, same scale.
- **Sparklines** (Tufte): Small, intense, word-sized graphics for trends (price trajectory, crime trends) embedded in text or tables.

**When specifying data-heavy views:**
- Define what data is compared and how
- Specify table structures: columns, alignment (left for text, right for numbers), sorting
- For trends, specify: time range, granularity, whether absolute or relative
- Reference the shared design system (Tufte/Few patterns are already in the CSS)
