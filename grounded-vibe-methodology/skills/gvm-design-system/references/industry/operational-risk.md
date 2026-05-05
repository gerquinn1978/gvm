---
domain_name: operational_risk
activation_signals:
  - loss_event_id
  - loss_amount
  - event_type
  - basel_category
  - business_line
  - kri
  - kri_value
  - rcsa_id
  - control_id
  - control_effectiveness
  - incident_id
  - incident_date
  - root_cause
  - frequency
  - severity
strong_signals:
  - basel_op_risk
  - sma
  - ama
---

# Industry Domain Specialists — Operational Risk

> **Append-only file.** New experts discovered during projects should be added to this file, never removed. The file grows as domain understanding deepens across projects.

## Activation Signals

Activate this file for any application dealing with: loss event collection, RCSA (Risk and Control Self-Assessment), KRI (Key Risk Indicator) management, scenario analysis, operational risk capital calculation, incident management, business continuity, third-party risk management, fraud detection, or regulatory compliance for operational risk.

---

## Marcelo Cruz

**Source:** Marcelo Cruz, *Modeling, Measuring and Hedging Operational Risk*, Wiley (2002)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 3 | 4 | 2 | 3 | 2 | **Recognised** |

Evidence: Publication — Wiley Finance.

**Work score — *Modeling, Measuring and Hedging Operational Risk*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 4 | 2 | 3 | **Established** |

Evidence: Specificity — dedicated to quantitative op risk: LDA, frequency-severity, EVT. Depth — mathematical derivations of compound distributions and tail estimation.

**Activation signals:** Loss distribution approach, frequency-severity modeling, operational risk capital, quantitative operational risk

**Key principles:**

- **Loss Distribution Approach (LDA)** — model operational risk as a compound distribution: frequency (how many events) × severity (how large each event). Poisson-LogNormal is the common starting point.
- **Data scarcity** — operational risk has few data points for severe losses. Internal data must be supplemented with external data and scenario analysis.
- **Heavy tails** — operational loss severity distributions are heavy-tailed. LogNormal, Pareto, and Generalised Pareto distributions. Underestimating the tail is the primary model risk.
- **Correlation between loss types** — operational risk events are not independent across categories. Copulas or other dependency structures needed for aggregation.

---

## Philippa Girling

**Source:** Philippa Girling, *Operational Risk Management: A Complete Guide to a Successful Operational Risk Framework* (2nd ed.), Wiley (2022)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 4 | 4 | 4 | 4 | 5 | **Established** |

Evidence: Authority — senior op risk roles at major institutions. Publication — Wiley Finance 2nd edition. Breadth — full framework: RCSA, KRI, governance, three lines, capital. Adoption — used in PRMIA and IRM training. Currency — 2022; most current practitioner text; covers SMA and operational resilience.

**Work score — *Operational Risk Management* (2nd ed.):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 3 | 5 | 4 | **Established** |

Evidence: Specificity — complete practitioner framework reference. Currency — 2022; post-SMA, post-COVID. Influence — go-to text for op risk framework design.

**Activation signals:** RCSA, KRI frameworks, operational risk governance, three lines of defence, risk appetite, op risk framework design

**Key principles:**

- **RCSA process** — structured self-assessment where business units identify risks, assess inherent and residual risk levels, and evaluate control effectiveness. The backbone of qualitative operational risk management.
- **KRI design** — Key Risk Indicators must be leading (predictive), not just lagging (after the fact). Good KRIs have defined thresholds (green/amber/red) and escalation procedures.
- **Three lines of defence** — business units own risk (1st line), operational risk function provides oversight and challenge (2nd line), internal audit provides independent assurance (3rd line).
- **Risk appetite** — operational risk appetite must be defined in measurable terms, not just "we have low appetite for operational risk." Link appetite to specific metrics and thresholds.
- **Governance structure** — clear committee structure, escalation paths, and reporting lines. The operational risk function must have sufficient authority and independence.

---

## Ariane Chapelle

**Source:** Ariane Chapelle, *Operational Risk Management: Best Practices in the Financial Services Industry*, Wiley (2019)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 4 | 4 | 4 | 4 | 4 | **Established** |

Evidence: Authority — UCL professor; trains ECB and NBB supervisors. Breadth — risk culture, behavioural risk, scenario analysis, control effectiveness. Adoption — referenced in IRM and PRMIA training. Currency — 2019; post-SMA.

**Work score — *Operational Risk Management: Best Practices*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 3 | 4 | 4 | **Established** |

Evidence: Specificity — financial services scoped. Influence — risk culture frameworks referenced in regulatory reviews.

**Activation signals:** Risk culture, scenario analysis, practical op risk implementation, behavioural aspects of risk management

**Key principles:**

- **Risk culture** — the single most important determinant of operational risk outcomes. A strong risk culture means people report incidents, challenge unsafe practices, and escalate concerns without fear.
- **Scenario analysis** — structured workshops to assess plausible but severe operational risk events. Scenarios bridge the gap between historical loss data (which is backward-looking) and emerging risks.
- **Practical implementation** — operational risk frameworks fail when they are bureaucratic checkbox exercises. Focus on utility: does this process change decisions?
- **Behavioural risk** — human factors (cognitive biases, incentive structures, fatigue, pressure) are root causes of operational risk events. Systems must account for how people actually behave, not how they should behave.
- **Control effectiveness** — a control that exists on paper but is not followed in practice provides no risk reduction. Control testing must verify actual operation, not just design.

---

## Anna Chernobai, Svetlozar Rachev & Frank Fabozzi

**Source:** Anna Chernobai, Svetlozar Rachev & Frank Fabozzi, *Operational Risk: A Guide to Basel II Capital Requirements, Models, and Analysis*, Wiley (2007)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 4 | 4 | 2 | 3 | 2 | **Recognised** |

Evidence: Authority — Rachev is a leading heavy-tailed distribution academic; Fabozzi has 100+ books. Publication — Wiley Finance.

**Work score — *Operational Risk* (2007):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 5 | 2 | 3 | **Established** |

Evidence: Specificity — quantitative op risk under Basel II AMA exclusively. Depth — rigorous statistical treatment: truncated distributions, MLE, copula aggregation.

**Activation signals:** AMA approaches, loss data collection, quantitative operational risk, Basel II operational risk

**Key principles:**

- **Basel event types** — seven categories: internal fraud, external fraud, employment practices, clients/products/business practices, damage to physical assets, business disruption, execution/delivery/process management. Systems must classify events into these categories.
- **Loss data collection** — data quality is everything. Completeness, accuracy, and timeliness of loss event data determine the quality of any quantitative model built on it.
- **Threshold effects** — loss collection thresholds (e.g., only collecting losses above £10,000) create a truncated dataset. Models must account for this truncation.
- **External data** — consortia data (ORX) and public loss databases supplement internal data. Scaling external losses to the firm's size and risk profile is a non-trivial modeling decision.

---

## James Lam

**Source:** James Lam, *Enterprise Risk Management: From Incentives to Controls* (2nd ed.), Wiley (2014)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 4 | 5 | 4 | 3 | **Established** |

Evidence: Authority — first CRO on record (GE Capital, 1993); advises Fortune 500 boards. Publication — Wiley Finance 2nd edition. Breadth — integrates operational, market, credit, strategic, reputational risk. Adoption — standard in ERM training; referenced in IIA, COSO, NACD guidance.

**Work score — *Enterprise Risk Management* (2nd ed.):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 3 | 3 | 3 | 4 | **Recognised** |

Evidence: Influence — cited in NACD Blue Ribbon Commission reports; referenced in FSB risk appetite guidance.

**Activation signals:** ERM frameworks, risk appetite, integrating operational risk into enterprise risk, board-level risk governance

**Key principles:**

- **ERM integration** — operational risk should not be managed in a silo. It must be integrated with market risk, credit risk, and strategic risk into an enterprise view.
- **Risk appetite framework** — cascading from board-level risk appetite statements to business-unit-level risk limits. Operational risk appetite expressed in terms of loss tolerances and KRI thresholds.
- **Incentive alignment** — risk management fails when incentives reward risk-taking without accountability. Compensation structures should incorporate risk-adjusted performance.
- **Risk reporting** — board and executive risk reports should be concise, forward-looking, and decision-oriented. Not a data dump — a prioritised view of what needs attention.

---

## Regulatory & Standards References

### Basel Committee (BCBS) — Operational Risk

**Sources:**
- *Principles for the Sound Management of Operational Risk* (BCBS 195), June 2011
- *Basel III: Finalising post-crisis reforms* (SMA for operational risk), December 2017

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 4 | 5 | 4 | **Canonical** |

Evidence: Authority — global standard-setter; standards implemented into law. Adoption — mandatory for all Basel-regulated banks. Currency — SMA (2017) is current operative standard.

**Work score — *Principles for the Sound Management of Operational Risk* (BCBS 195):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 3 | 3 | 5 | **Established** |

Evidence: Specificity — 11 principles for sound op risk management. Influence — referenced in every bank's op risk framework.

**Work score — *Basel III SMA* (2017):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 4 | 5 | 5 | **Canonical** |

Evidence: Currency — current operative capital standard. Influence — eliminated AMA globally; mandatory for all banks.

**Activation signals:** Regulatory capital for operational risk, standardised measurement approach, operational risk principles

**Key principles:**

- **Standardised Measurement Approach (SMA)** — replaces all previous approaches (BIA, TSA, AMA). Capital based on the Business Indicator Component (BIC) and an Internal Loss Multiplier (ILM).
- **No more AMA** — Advanced Measurement Approaches are no longer permitted for regulatory capital. Internal models can still be used for risk management but not for minimum capital.
- **Sound management principles** — board and senior management responsibility, risk identification and assessment, change management, monitoring and reporting. These principles apply regardless of capital approach.
- **Operational resilience** — increasingly linked to operational risk. The ability to prevent, adapt to, respond to, recover from, and learn from disruptions.

### IRM — Operational Risk Guidance

**Source:** Institute of Risk Management, *Operational Risk Sound Practice Guidance*, IRM (2010)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 3 | 2 | 2 | 2 | 1 | **Emerging** |

**Work score — *Operational Risk Sound Practice Guidance*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 4 | 2 | 1 | 2 | **Emerging** |

Note: Source dated 2010, classified Emerging (Currency=1). Activate for historical context only — do not use as primary authority for current operational risk practices. Prefer Basel II/III guidance or COSO ERM (2017) for current standards.

**Activation signals:** Operational risk good practice, risk management maturity

**Key principles:**

- **Maturity model** — operational risk management maturity ranges from reactive (Level 1) to optimised (Level 5). Assessment of current maturity guides improvement priorities.
- **Embedding** — operational risk management is effective when it is embedded in business processes, not layered on top as an afterthought.

### COSO — Enterprise Risk Management

**Source:** Committee of Sponsoring Organizations of the Treadway Commission, *Enterprise Risk Management — Integrating with Strategy and Performance*, COSO (2017)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 4 | 5 | 5 | 4 | **Canonical** |

Evidence: Authority — de facto standard-setter for internal control and ERM; SEC references COSO. Breadth — full ERM: governance, culture, strategy, performance, review. Adoption — dominant ERM framework; adopted by Fortune 500 and government. Currency — 2017 update addressed strategy-risk integration.

**Work score — *ERM — Integrating with Strategy and Performance*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 3 | 3 | 4 | 5 | **Established** |

Evidence: Influence — cited in SEC guidance; mandatory in government risk frameworks; underpins Big Four ERM engagements.

**Activation signals:** Enterprise risk framework, risk and strategy alignment, risk governance

**Key principles:**

- **Risk and strategy** — risk management is not separate from strategy. Risk considerations should inform strategic decisions, and strategic choices create risk exposures.
- **Five components** — governance and culture, strategy and objective-setting, performance, review and revision, information/communication/reporting.
- **Risk appetite** — the amount of risk an entity is willing to accept in pursuit of value. Must be defined, communicated, and monitored.
