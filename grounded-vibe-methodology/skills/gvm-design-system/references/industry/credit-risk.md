---
domain_name: credit_risk
activation_signals:
  - pd
  - pd_pit
  - pd_ttc
  - lgd
  - ead
  - default_indicator
  - default_flag
  - credit_score
  - fico_score
  - rating
  - exposure_at_default
  - ecl
  - ifrs9_stage
  - cva
  - dva
  - counterparty_id
strong_signals:
  - rwa
  - basel_iii
  - basel_iv
  - irb
---

# Industry Domain Specialists — Credit Risk

> **Append-only file.** New experts discovered during projects should be added to this file, never removed. The file grows as domain understanding deepens across projects.

## Activation Signals

Activate this file for any application dealing with: credit scoring, PD/LGD/EAD estimation, credit portfolio modeling, counterparty credit risk, CVA/DVA/FVA, expected credit loss calculation (IFRS 9/CECL), credit limit management, rating systems, credit derivatives, or regulatory capital for credit risk.

---

## Edward Altman

**Source:** Edward Altman, *Corporate Financial Distress, Restructuring, and Bankruptcy* (4th ed.), Wiley (2019)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 4 | 5 | 4 | **Canonical** |

Evidence: Authority — Z-Score is the most cited quantitative default-prediction model. Publication — 4th edition Wiley (2019). Adoption — embedded in Bloomberg, Moody's RiskCalc; referenced in Basel papers. Currency — 4th edition incorporates post-GFC data.

**Work score — *Corporate Financial Distress* (4th ed.):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 5 | 4 | 5 | **Canonical** |

Evidence: Specificity — focused on bankruptcy and distress prediction. Depth — discriminant analysis, cross-country adaptation, LGD estimation. Influence — cited in virtually every PD modelling comparison study.

**Activation signals:** Default prediction, Z-Score models, distressed debt, credit scoring, corporate bankruptcy analysis

**Key principles:**

- **Z-Score model** — multivariate discriminant analysis using financial ratios (working capital/assets, retained earnings/assets, EBIT/assets, market equity/book debt, sales/assets). The foundational quantitative credit scoring model.
- **Distressed debt analysis** — recovery rates vary by seniority, industry, and economic cycle. LGD estimation must account for these factors.
- **Default rates by rating** — historical default and migration matrices provide the empirical foundation for PD estimation. Altman's datasets are the benchmark.
- **Credit cycles** — default rates are cyclical. Point-in-time vs through-the-cycle PD estimation is an architectural decision with regulatory implications.

---

## Darrell Duffie & Kenneth Singleton

**Source:** Darrell Duffie & Kenneth Singleton, *Credit Risk: Pricing, Measurement, and Management*, Princeton University Press (2003)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 4 | 5 | 3 | **Established** |

Evidence: Authority — Duffie holds endowed chair at Stanford; intensity framework foundational. Publication — Princeton University Press. Adoption — framework underpins virtually all CDS pricing.

**Work score — *Credit Risk: Pricing, Measurement, and Management*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 4 | 5 | 2 | 5 | **Established** |

Evidence: Depth — full mathematical derivation of intensity models. Influence — defining reference for reduced-form credit modelling.

**Activation signals:** Reduced-form credit models, credit spreads, default intensity, CVA/DVA, credit derivatives pricing

**Key principles:**

- **Reduced-form models** — default is modeled as a jump process with stochastic intensity. No attempt to model the firm's asset dynamics directly. More tractable than structural models for pricing.
- **Default intensity** — the hazard rate (instantaneous probability of default) can be calibrated from CDS spreads or bond spreads. This is the market-implied view of credit risk.
- **CVA as a derivative** — Credit Valuation Adjustment is the price of counterparty default risk. It is a derivative on the counterparty's credit quality and the exposure profile of the trade.
- **Wrong-way risk** — when exposure increases as the counterparty's credit quality deteriorates. Must be modeled explicitly; ignoring it systematically underestimates CVA.

---

## David Lando

**Source:** David Lando, *Credit Risk Modeling: Theory and Applications*, Princeton University Press (2004)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 4 | 5 | 4 | 4 | 3 | **Established** |

Evidence: Authority — recognised structural credit model authority; CBS professor. Publication — Princeton University Press.

**Work score — *Credit Risk Modeling*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 4 | 5 | 2 | 4 | **Established** |

Evidence: Depth — rigorous stochastic calculus treatment from first principles. Influence — standard PhD-level reading; cited in Basel papers on internal ratings.

**Activation signals:** Structural credit models, Merton model, credit migration, rating-based models

**Key principles:**

- **Merton structural model** — the firm's equity is a call option on its assets. Default occurs when assets fall below the debt barrier. Elegant but makes strong assumptions about asset observability.
- **First-passage models** — default can occur before maturity if assets hit a barrier (Black-Cox). More realistic than Merton for short-dated credit risk.
- **Rating transition matrices** — credit quality evolves as a Markov chain (or semi-Markov). Transition matrices are the foundation for multi-period credit portfolio models.
- **Structural vs reduced-form** — structural models have economic intuition but are hard to calibrate. Reduced-form models are easier to calibrate but lack structural interpretation. The choice depends on the use case.

---

## Gunter Löffler

**Source:** Gunter Löffler, *Anatomy of Risk Management*, Wiley (2003)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 3 | 3 | 4 | 3 | 3 | **Recognised** |

Evidence: Breadth — covers credit portfolio risk, PD/LGD/EAD estimation, capital allocation, and rating validation across practitioner and regulatory contexts.

**Work score — *Anatomy of Risk Management*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 4 | 3 | 2 | 3 | **Recognised** |

**Activation signals:** Rating systems, PD/LGD/EAD estimation, credit portfolio risk, economic capital

**Key principles:**

- **PD estimation** — point-in-time (current conditions) vs through-the-cycle (long-run average). Regulatory and economic capital models may require different approaches.
- **LGD drivers** — seniority, collateral type, industry, and economic conditions all affect recovery. LGD is not a fixed number — it must be modeled.
- **EAD for commitments** — undrawn credit lines are partially drawn before default (credit conversion factors). The drawn-at-default amount must be estimated.
- **Portfolio credit risk** — single-name PDs and LGDs are not enough. Correlation between defaults determines the tail of the portfolio loss distribution.

---

## Michael Ong

**Source:** Michael Ong, *Internal Credit Risk Models: Capital Allocation and Performance Measurement*, Risk Books (1999)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 3 | 3 | 4 | 3 | 2 | **Recognised** |

Evidence: Breadth — spans economic capital modelling, risk-adjusted returns, and enterprise-wide credit risk aggregation.

**Work score — *Internal Credit Risk Models*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 3 | 1 | 3 | **Recognised** |

Evidence: Specificity — tightly scoped to internal rating systems and economic capital.

**Activation signals:** Internal rating systems, credit scoring models, economic capital for credit risk, portfolio models

**Key principles:**

- **Internal rating systems** — calibration, validation, and discrimination testing (Gini coefficient, accuracy ratio, CAP curves). A rating system is only as good as its ability to rank-order risk.
- **Economic capital** — unexpected loss at a chosen confidence level. The difference between expected loss (provisions) and unexpected loss (capital) is fundamental.
- **CreditMetrics framework** — portfolio credit risk via migration simulation. Joint rating transitions generate the portfolio loss distribution.
- **RAROC** — risk-adjusted return on capital as the performance measure. Allocating capital to individual exposures enables risk-based pricing.

---

## Ashish Dev

**Source:** Ashish Dev (ed.), *Economic Capital: A Practitioner Guide*, Risk Books (2004)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 3 | 3 | 4 | 3 | 3 | **Recognised** |

Evidence: Breadth — covers structured credit, securitisation risk, and portfolio credit derivatives across trading and banking book contexts.

**Work score — *Economic Capital: A Practitioner Guide*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 3 | 2 | 3 | **Recognised** |

Evidence: Specificity — entirely scoped to economic capital modelling and IRB implementation.

**Activation signals:** IRB approaches, regulatory capital, stress testing for credit, Basel compliance

**Key principles:**

- **IRB Foundation vs Advanced** — Foundation IRB uses supervisory LGD and EAD; Advanced IRB uses internal estimates. The choice affects data requirements, validation burden, and capital outcomes.
- **Asset correlation** — the single systematic risk factor model underlying Basel IRB. Correlation assumptions drive the shape of the capital function.
- **Stress testing** — credit stress tests must shock PDs, LGDs, and correlations simultaneously. Stressing PD alone underestimates tail losses.
- **Concentration risk** — IRB capital assumes infinite granularity. Real portfolios have name and sector concentrations that require add-on capital.

---

## Regulatory & Standards References

### Basel Committee (BCBS) — Credit Risk Framework

**Sources:**
- *International convergence of capital measurement and capital standards* (Basel II, revised 2006)
- *Basel III: Finalising post-crisis reforms* (December 2017)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 5 | 5 | 5 | **Canonical** |

Evidence: Authority — sole global standard-setter for bank capital. Publication — formal BIS publications. Breadth — SA-CR, IRB, securitisation, CCR, CVA, large exposures. Adoption — implemented into law in 100+ jurisdictions. Currency — Basel III (2017) with ongoing implementation.

**Work score — *Basel II* (revised 2006):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 4 | 3 | 5 | **Established** |

Evidence: Specificity — prescriptive to formula level. Influence — every IRB implementation globally is built on this.

**Work score — *Basel III: Finalising Post-Crisis Reforms* (2017):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 4 | 5 | 5 | **Canonical** |

Evidence: Currency — operative global standard as of 2026. Influence — drives capital requirements for every internationally active bank.

**Activation signals:** Regulatory capital calculation, IRB approach, standardised approach for credit risk

**Key principles:**

- **Standardised Approach (SA-CR)** — risk weights based on external ratings or standardised categories. Simpler but less risk-sensitive.
- **IRB Approach** — risk weights derived from PD, LGD, EAD, and maturity. Requires regulatory approval and ongoing validation.
- **Output floor** — Basel III final reforms floor IRB capital at 72.5% of SA-CR capital. Limits the benefit of internal models.

### IFRS 9 / CECL — Expected Credit Loss

**Sources:**
- IASB, *IFRS 9 Financial Instruments* (2014)
- FASB, *ASC 326 (CECL)* (2016)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 4 | 5 | 5 | **Canonical** |

Evidence: Authority — IASB and FASB are authoritative accounting standard-setters. Adoption — mandatory in 140+ jurisdictions (IFRS) and all US GAAP entities (CECL). Currency — both are current operative standards.

**Work score — *IFRS 9 Financial Instruments*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 4 | 4 | 5 | **Canonical** |

Evidence: Specificity — three-stage ECL model in full operational detail. Influence — reshaped provisioning methodology across global banking.

**Work score — *ASC 326 (CECL)*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 3 | 4 | 5 | **Established** |

Evidence: Influence — caused $50-100bn provision increase across US banking on Day 1 adoption.

**Activation signals:** Loan loss provisioning, expected credit loss calculation, stage classification, lifetime PD

**Key principles:**

- **Three-stage model (IFRS 9)** — Stage 1 (12-month ECL), Stage 2 (lifetime ECL, performing), Stage 3 (lifetime ECL, impaired). Stage transfer criteria are a key design decision.
- **CECL (US)** — lifetime expected loss from day one. No staging. Simpler conceptually but front-loads provisions.
- **Forward-looking information** — both frameworks require incorporation of macroeconomic scenarios. Scenario weighting methodology is an architectural decision.

### Rating Agencies

**Sources:** Moody's, S&P, Fitch — published rating methodologies and annual default studies

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 4 | 5 | 5 | 5 | **Canonical** |

Evidence: Authority — NRSROs recognised by regulators globally; ratings embedded in SA-CR risk weights. Adoption — default studies are universal benchmark for PD calibration. Currency — annual publications; updated yearly.

**Work score — Annual Default Studies:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 4 | 5 | 5 | **Canonical** |

Evidence: Specificity — cumulative default rates by grade, sector, region, time horizon. Currency — published annually. Influence — universal benchmark for PD calibration validation.

**Work score — Rating Methodologies:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 4 | 3 | 5 | 4 | **Established** |

Evidence: Currency — updated on rolling basis. Influence — studied by issuers, investors, and internal rating system developers.

**Activation signals:** External ratings, benchmark calibration, transition matrices

**Key principles:**

- **Default studies** — annual publications providing empirical default rates and transition matrices by rating grade. The primary benchmark for PD calibration.
- **Rating methodologies** — sector-specific frameworks for assigning ratings. Useful for understanding what drives creditworthiness in specific industries.
