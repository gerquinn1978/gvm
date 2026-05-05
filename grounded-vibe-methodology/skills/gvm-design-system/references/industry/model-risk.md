---
domain_name: model_risk
activation_signals:
  - model_id
  - model_version
  - model_name
  - model_owner
  - validation_date
  - validation_status
  - tier
  - model_tier
  - challenger_model
  - performance_metric
  - backtest_result
  - inventory_id
strong_signals:
  - sr_11_7
  - ss1_23
  - mrm
---

# Industry Domain Specialists — Model Risk

> **Append-only file.** New experts discovered during projects should be added to this file, never removed. The file grows as domain understanding deepens across projects.

## Activation Signals

Activate this file for any application dealing with: model development, model validation, model inventory management, model governance, model performance monitoring, challenger model frameworks, model documentation, regulatory compliance for model risk (SR 11-7, SS1/23), ML/AI model governance, model explainability, or fairness and disparate impact analysis.

---

## Emanuel Derman

**Sources:**
- Emanuel Derman, *Models.Behaving.Badly: Why Confusing Illusion with Reality Can Lead to Disaster, on Wall Street and in Life*, Free Press (2011)
- Emanuel Derman & Michael Miller, *The Volatility Smile*, Wiley (2016)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 4 | 4 | 3 | **Established** |

Evidence: Authority — former Goldman Sachs head of quant strategies; Columbia professor; "models as analogies" framing is canonical. Publication — Free Press and Wiley.

**Work score — *Models.Behaving.Badly*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 3 | 4 | 3 | 5 | **Established** |

Evidence: Influence — widely cited as canonical framing of model risk philosophy; referenced in SR 11-7 era discourse.

**Work score — *The Volatility Smile*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 4 | 5 | 3 | 4 | **Established** |

Evidence: Specificity — focused on options pricing and implied volatility surfaces. Depth — graduate-level mathematical treatment of local vol, stochastic vol, jump-diffusion.

**Activation signals:** Model philosophy, model limitations, the distinction between models and theories, quantitative modeling ethics

**Key principles:**

- **Models are not theories** — theories describe reality; models are analogies that capture some features and ignore others. Treating a model as truth is the root cause of model risk.
- **The modeler's oath** — "I will remember that I didn't make the world, and it doesn't satisfy my equations." Humility about model limitations is not optional.
- **Know what you're ignoring** — every model simplifies. The dangerous simplifications are the ones the modeler doesn't know about. Document assumptions explicitly.
- **Volatility smile** — the smile is the market's way of telling you Black-Scholes is wrong. The pattern of implied volatilities across strikes encodes information about the true distribution of returns.

---

## Riccardo Rebonato

**Source:** Riccardo Rebonato, *Plight of the Fortune Tellers: Why We Need to Manage Financial Risk Differently*, Princeton University Press (2007)

*Riccardo Rebonato scored in market-risk.md. Classification: Established (avg 4.2).*

**Work score — *Plight of the Fortune Tellers*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 3 | 4 | 4 | 4 | **Established** |

Evidence: Depth — rigorous philosophical analysis of Bayesian reasoning and model uncertainty. Currency=4 (reconciled to market-risk.md): critique validated post-GFC; Basel shift to Expected Shortfall supports the argument; remains actively cited in model risk governance literature.

**Activation signals:** Critique of risk models, model uncertainty quantification, limits of backtesting, philosophical foundations of risk measurement

**Key principles:**

- **False precision** — risk models produce numbers with many decimal places but enormous uncertainty. Reporting VaR to the nearest dollar when the confidence interval spans millions is misleading.
- **Backtesting is necessary but not sufficient** — a model can pass backtests and still be structurally wrong. Backtesting validates the centre of the distribution, not the tails that matter.
- **Model uncertainty** — the range of plausible models for the same phenomenon can produce wildly different risk estimates. This model uncertainty should be quantified and reported.
- **Subjective judgment is unavoidable** — model selection, calibration choices, and parameter estimation all involve judgment. Making that judgment transparent is better than pretending it doesn't exist.

---

## Paul Wilmott

**Source:** Paul Wilmott, *Paul Wilmott on Quantitative Finance* (2nd ed.), Wiley (2006)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 5 | 5 | 3 | **Canonical** |

Evidence: Authority — DPhil Oxford; founded CQF programme and *Wilmott* magazine. Publication — 3-volume Wiley. Breadth — derivatives pricing, fixed income, credit, numerical methods, model risk. Adoption — standard reference; CQF built around it.

**Work score — *Paul Wilmott on Quantitative Finance* (2nd ed.):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 5 | 2 | 5 | **Established** |

Evidence: Specificity — 1,500+ pages of mathematical derivation. Depth — derives every major result from first principles. Influence — Wiley's top-selling quant finance title; CQF built around it.

**Activation signals:** Practical model building, model calibration, over-complexity dangers, financial engineering fundamentals

**Key principles:**

- **Simplicity over complexity** — a model you understand is better than one you don't. Over-parameterised models fit noise, not signal.
- **Calibration traps** — fitting too many parameters to market data creates the illusion of accuracy. Parsimonious models with fewer parameters are more robust.
- **Worst-case analysis** — when model uncertainty is high, compute the worst case across plausible models rather than relying on a single model's output.
- **The modeler must understand the mathematics** — using a model as a black box is a form of model risk. If you can't derive the model's sensitivities by hand, you don't understand it.

---

## Nassim Nicholas Taleb

**Sources:**
- Nassim Nicholas Taleb, *The Black Swan: The Impact of the Highly Improbable* (2nd ed.), Random House (2010)
- Nassim Nicholas Taleb, *Antifragile: Things That Gain from Disorder*, Random House (2012)
- Nassim Nicholas Taleb, *Statistical Consequences of Fat Tails*, STEM Academic Press (2020)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 5 | 5 | 4 | **Canonical** |

Evidence: Authority — former derivatives trader; NYU Distinguished Professor of Risk Engineering. Publication — 3+ million copies of *The Black Swan*. Breadth — probability theory, finance, philosophy, systems theory, policy. Adoption — "Black Swan" entered regulatory vocabulary; cited by IMF, Federal Reserve, BIS. Currency — *Statistical Consequences of Fat Tails* (2020).

**Work score — *The Black Swan* (2nd ed.):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 2 | 4 | 3 | 5 | **Established** |

Evidence: Influence — one of the most influential popular risk works in two decades; "Black Swan" is regulatory vocabulary.

**Work score — *Antifragile*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 2 | 3 | 3 | 4 | **Recognised** |

Evidence: Influence — fragility/antifragility framework adopted in risk management discourse and resilience thinking.

**Work score — *Statistical Consequences of Fat Tails*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 5 | 4 | 3 | **Established** |

Evidence: Specificity — directly addresses how fat tails invalidate standard inference. Depth — graduate-level probability theory with formal derivations. Currency — 2020.

**Activation signals:** Tail risk, model fragility, limits of prediction, fat-tailed distributions, anti-fragile system design

**Key principles:**

- **Black Swans** — high-impact, low-probability events that models systematically underestimate. The most important risks are the ones your model doesn't capture.
- **Fat tails invalidate standard statistics** — mean, variance, and correlation are unreliable under fat-tailed distributions. Most financial data is fat-tailed. Standard statistical tools give false confidence.
- **Fragility as a risk measure** — instead of predicting specific events, assess how fragile the system is to shocks. Fragile systems break under stress; antifragile systems benefit from it.
- **Skin in the game** — model builders should bear some consequence of model failure. Separation between modelers and risk-takers creates moral hazard.
- **Via negativa** — reducing fragility (removing what hurts) is more reliable than predicting what will help. Risk management should focus on eliminating ruin scenarios, not optimising returns.

---

## Christoph Molnar

**Source:** Christoph Molnar, *Interpretable Machine Learning: A Guide for Making Black Box Models Explainable* (2nd ed.), self-published online (2022), christophm.github.io/interpretable-ml-book/

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 4 | 3 | 3 | 4 | 5 | **Established** |

Evidence: Authority — ML interpretability researcher at Ludwig-Maximilians-Universität München; the most cited single-author reference in the ML interpretability field. Publication — self-published online (free); not a traditional academic or commercial press, which limits the score despite wide readership. Breadth — focused on ML interpretability specifically; narrower than general model risk but comprehensive within that domain. Adoption — standard reference in data science education and XAI courses; cited by Google and Microsoft Research. Currency — 2nd edition 2022, actively maintained; ML interpretability is a current and growing regulatory concern.

**Work score — *Interpretable Machine Learning* (2nd ed.):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 4 | 5 | 4 | **Canonical** |

Evidence: Specificity — covers SHAP, LIME, PDP, ALE, permutation feature importance, and counterfactual explanations, each with mathematical definition and worked examples. Depth — comprehensive treatment with mathematical foundations for each method. Currency — 2nd edition 2022, actively updated. Influence — most widely cited practical reference on ML interpretability; adopted as a primary text in XAI courses at major universities.

**Activation signals:** ML/AI model governance, model explainability, fairness and disparate impact analysis, interpretable model design, post-hoc explanation methods, SHAP/LIME implementation

**Key principles:**

- **Model-agnostic post-hoc explanation** — SHAP and LIME provide explanability for any black-box model without requiring access to model internals. This enables governance teams to challenge ML models regardless of implementation.
- **Feature importance must be computed, not assumed** — permutation importance measures the actual effect of each feature on prediction error; coefficient magnitude in regularised models is not a reliable proxy. SR 11-7 effective challenge requires computed evidence, not assertion.
- **Interpretability/accuracy trade-offs must be explicit** — the choice to use a high-accuracy black-box model over an interpretable model is a governance decision that must be documented. Regulators (SS1/23, SR 11-7) require that trade-offs be explicit and approved.
- **Counterfactual explanations support effective challenge** — "what would need to change for this model to produce a different output?" provides a concrete mechanism for validators to probe model boundaries, directly supporting SR 11-7's effective challenge requirement.

---

## Regulatory & Standards References

### Federal Reserve / OCC — SR 11-7

**Source:** Board of Governors of the Federal Reserve System / Office of the Comptroller of the Currency, *Supervisory Guidance on Model Risk Management* (SR Letter 11-7 / OCC Bulletin 2011-12), April 2011

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 5 | 5 | 3 | **Canonical** |

Evidence: Authority — joint issuance by Fed and OCC; compliance mandatory for all supervised institutions. Breadth — defines entire US MRM framework. Adoption — universally adopted; referenced by SS1/23, MAS, OSFI.

**Work score — *SR 11-7*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 4 | 3 | 5 | **Established** |

Evidence: Specificity — prescribes model definition, validation scope, governance, monitoring. Influence — the definitive MRM framework; every subsequent framework builds on it.

**Activation signals:** US model risk management framework, model inventory, model validation, model governance

**Key principles:**

*Independent validation and challenger model principles derived from SR 11-7 §§5-7.*

- **Definition of a model** — "a quantitative method, system, or approach that applies statistical, economic, financial, or mathematical theories, techniques, and assumptions to process input data into quantitative estimates." Broad definition — many things are models that people don't think of as models.
- **Three lines of defence** — model development (1st line), model validation (2nd line), internal audit (3rd line). Each has distinct responsibilities.
- **Effective challenge** — validation must provide "critical analysis by objective, informed parties who can identify model limitations and assumptions and produce appropriate changes." Rubber-stamp validation is a regulatory finding.
- **Model inventory** — all models must be inventoried, classified by risk tier, and subject to periodic validation. The inventory is itself auditable.
- **Ongoing monitoring** — models must be monitored between validations. Performance metrics, backtesting, and outcome analysis on a regular cycle.

### Bank of England / PRA — SS1/23

**Source:** Prudential Regulation Authority, *Model risk management principles for banks* (Supervisory Statement SS1/23), May 2023

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 5 | 4 | 5 | **Canonical** |

Evidence: Authority — PRA is UK's primary banking supervisor. Currency — 2023; most current major MRM statement; addresses AI/ML models. Adoption — mandatory for PRA-regulated firms.

**Work score — *SS1/23*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 4 | 5 | 4 | **Canonical** |

Evidence: Specificity — five named MRM principles with detailed sub-requirements. Currency — 2023; addresses AI/ML, third-party models, data quality.

**Activation signals:** UK model risk management framework, model risk appetite, MRM principles

**Key principles:**

- **Model risk appetite** — firms must define and quantify their appetite for model risk, not just manage it reactively.
- **Five principles** — model identification and classification, governance, model development and implementation, independent validation, model risk mitigants.
- **Extends SR 11-7** — UK framework builds on the US framework with additional expectations around data quality, model tiering, and board-level oversight.

### Basel Committee — BCBS 239

**Source:** Basel Committee on Banking Supervision, *Principles for effective risk data aggregation and risk reporting* (BCBS 239), January 2013

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 4 | 5 | 3 | **Established** |

Evidence: Authority — BCBS is global standard-setter. Adoption — mandatory for G-SIBs from 2016.

**Work score — *BCBS 239*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 4 | 3 | 3 | 5 | **Established** |

Evidence: Influence — foundational for risk data infrastructure globally; cited in ECB, PRA, and Fed communications.

**Activation signals:** Risk data infrastructure, data quality, risk reporting

**Key principles:**

- **Data accuracy and integrity** — risk data must be accurate, complete, and timely. Data quality is a model risk issue — garbage in, garbage out.
- **Aggregation capability** — firms must be able to aggregate risk data across the enterprise. Siloed data creates blind spots.
- **Timeliness** — risk reports must be produced quickly enough to be actionable, especially during stress events.
