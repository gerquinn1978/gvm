---
domain_name: market_risk
activation_signals:
  - var
  - var_1d
  - var_10d
  - expected_shortfall
  - es
  - pnl
  - daily_pnl
  - delta
  - gamma
  - vega
  - theta
  - rho
  - volatility
  - implied_vol
  - yield_curve
  - spread
  - risk_factor
  - tenor
  - notional
strong_signals:
  - frtb
  - sa_ccr
  - simm
---

# Industry Domain Specialists — Market Risk

> **Append-only file.** New experts discovered during projects should be added to this file, never removed. The file grows as domain understanding deepens across projects.

## Activation Signals

Activate this file for any application dealing with: trading book risk, market risk measurement, VaR/ES calculation, derivatives pricing, risk factor modeling, P&L attribution, market data systems, sensitivity analysis (Greeks), stress testing, or regulatory capital for market risk (FRTB).

---

## Philippe Jorion

**Source:** Philippe Jorion, *Value at Risk: The New Benchmark for Managing Financial Risk* (3rd ed.), McGraw-Hill (2006)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 4 | 5 | 3 | **Established** |

Evidence: Authority — defining VaR authority; cited in Basel working papers and GARP FRM. Publication — 3 editions, McGraw-Hill. Adoption — FRM set text; standard at university risk programmes globally.

**Work score — *Value at Risk* (3rd ed.):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 5 | 3 | 5 | **Canonical** |

Evidence: Specificity — purpose-built on VaR: parametric, historical simulation, Monte Carlo, backtesting. Depth — graduate-level with worked examples across 3 editions. Influence — cross-cited in Hull, Alexander, Dowd, Rebonato; shaped market risk vocabulary.

**Activation signals:** VaR calculation, risk measurement methodology, backtesting, regulatory capital, risk limits

**Key principles:**

- **Three VaR approaches** — parametric (variance-covariance), historical simulation, and Monte Carlo simulation. Each has distinct assumptions, strengths, and failure modes. The choice is an architectural decision.
- **Backtesting as validation** — VaR models must be backtested against actual P&L. Kupiec and Christoffersen tests for coverage and independence. A model that passes coverage but fails independence is systematically wrong.
- **Risk decomposition** — VaR should be decomposable by desk, asset class, and risk factor. Marginal, component, and incremental VaR provide different views of the same risk.
- **Stress testing complements VaR** — VaR measures risk under normal conditions. Stress tests measure risk under extreme but plausible scenarios. Neither is sufficient alone.
- **Mapping positions to risk factors** — complex instruments must be mapped to a manageable set of risk factors. The mapping introduces model risk that must be understood and documented.

---

## John Hull

**Sources:**
- John Hull, *Options, Futures, and Other Derivatives* (11th ed.), Pearson (2021)
- John Hull, *Risk Management and Financial Institutions* (5th ed.), Wiley (2018)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 5 | 5 | 5 | **Canonical** |

Evidence: Authority — most widely cited derivatives/risk textbook author. Publication — 11 editions (Pearson), 5 editions (Wiley). Breadth — derivatives pricing, Greeks, yield curves, volatility, regulatory capital. Adoption — standard at 500+ universities; CFA, FRM, CQF. Currency — 11th ed. 2021 covers OIS/SOFR transition.

**Work score — *Options, Futures, and Other Derivatives* (11th ed.):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 4 | 5 | 5 | 5 | **Canonical** |

Evidence: Depth — Black-Scholes derivation, risk-neutral pricing, yield curve construction from first principles. Currency — 2021; covers current market practice. Influence — standard text at 500+ universities; defines shared practitioner vocabulary.

**Work score — *Risk Management and Financial Institutions* (5th ed.):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 4 | 4 | 4 | **Established** |

Evidence: Specificity — market risk, credit risk, operational risk, and regulation. Depth — solid applied coverage of Basel III.

**Activation signals:** Derivatives pricing, Greeks, hedging strategies, risk factor modeling, yield curve construction, volatility surfaces

**Key principles:**

- **No-arbitrage pricing** — derivative prices are determined by replication arguments, not by expected returns. The risk-neutral framework is the foundation.
- **Greeks as risk sensitivities** — Delta, Gamma, Vega, Theta, Rho each measure sensitivity to a specific risk factor. Systems must compute and store Greeks for position management and hedging.
- **Volatility surface** — implied volatility varies by strike and maturity (smile/skew). The surface must be interpolated consistently for pricing and risk.
- **Yield curve construction** — bootstrapping from market instruments, interpolation methods (cubic spline, monotone convex), and the choice of curve-building methodology are architectural decisions with risk implications.
- **Model choice matters** — Black-Scholes, local volatility, stochastic volatility, and jump-diffusion models each make different assumptions. The model must match the instrument's characteristics.

---

## Carol Alexander

**Source:** Carol Alexander, *Market Risk Analysis* (4 volumes), Wiley (2008-2009):
- Vol I: Quantitative Methods in Finance
- Vol II: Practical Financial Econometrics
- Vol III: Pricing, Hedging and Trading Financial Instruments
- Vol IV: Value-at-Risk Models

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 5 | 4 | 3 | **Established** |

Evidence: Authority — definitive multi-volume reference on quantitative risk methods. Publication — 4 coordinated Wiley volumes. Breadth — quantitative methods, econometrics, pricing/hedging, VaR models. Adoption — used in quantitative finance programmes and CQF.

**Work score — *Market Risk Analysis* (4 volumes):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 5 | 3 | 4 | **Established** |

Evidence: Specificity — each volume maps to implementation concerns. Depth — GARCH derivations, copula theory, EVT, Monte Carlo at graduate-to-PhD level. Influence — cited alongside Jorion and Hull in academic curricula.

**Activation signals:** Quantitative risk methods, GARCH models, volatility estimation, correlation modeling, practical VaR implementation

**Key principles:**

- **GARCH for volatility** — volatility is not constant. GARCH models capture volatility clustering and mean reversion. The choice of GARCH variant (EWMA, GARCH(1,1), EGARCH) affects risk estimates.
- **Correlation is unstable** — correlations between assets change over time and increase during crises (correlation breakdown). Risk systems must account for this.
- **Practical econometrics** — data quality, outlier treatment, return calculation methodology (log vs arithmetic), and frequency alignment are not implementation details — they are risk modeling decisions.
- **Fat tails** — financial returns are not normally distributed. Ignoring fat tails systematically underestimates tail risk. Student-t, GED, or empirical distributions are more appropriate.

---

## Kevin Dowd

**Source:** Kevin Dowd, *Measuring Market Risk* (2nd ed.), Wiley (2005)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 4 | 4 | 3 | 3 | 3 | **Recognised** |

Evidence: Authority — primary practitioner reference for Expected Shortfall, EVT, and coherent risk measures.

**Work score — *Measuring Market Risk* (2nd ed.):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 4 | 3 | 4 | **Established** |

Evidence: Specificity — entire text focused on risk measurement methodology. Depth — thorough EVT treatment (GPD, POT) and coherent risk measure axioms. Influence — primary text on coherent risk measures in market risk.

**Activation signals:** Coherent risk measures, Expected Shortfall, extreme value theory, model risk in risk measurement

**Key principles:**

- **Expected Shortfall over VaR** — ES (CVaR) is a coherent risk measure; VaR is not. ES answers "how bad is it when things go wrong?" rather than just "what's the threshold?"
- **Extreme Value Theory** — EVT provides a principled framework for estimating tail risk. The Peaks-over-Threshold approach and the Generalised Pareto Distribution are the practical tools.
- **Model risk in risk models** — every risk model is wrong. The question is how wrong, and whether the errors are systematic. Model risk must be quantified and reported alongside the risk estimate itself.
- **Coherent risk measures** — a risk measure should satisfy monotonicity, translation invariance, positive homogeneity, and subadditivity. VaR fails subadditivity; ES does not.

---

## Riccardo Rebonato

**Sources:**
- Riccardo Rebonato, *Volatility and Correlation: The Perfect Hedger and the Fox* (2nd ed.), Wiley (2004)
- Riccardo Rebonato, *Plight of the Fortune Tellers: Why We Need to Manage Financial Risk Differently*, Princeton University Press (2007)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 3 | 4 | 4 | **Established** |

Evidence: Authority — former Global Head rates research at RBS/PIMCO; EDHEC professor. Publication — Wiley and Princeton University Press. Adoption — *Volatility and Correlation* standard for LMM calibration. Currency — *Bond Pricing and Yield Curve Modelling* (Cambridge, 2018).

**Work score — *Volatility and Correlation* (2nd ed.):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 5 | 3 | 4 | **Established** |

Evidence: Specificity — focused on LMM/BGM calibration. Depth — most rigorous LMM calibration treatment available. Influence — standard reference for quant interest rate teams.

**Work score — *Plight of the Fortune Tellers*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 3 | 4 | 4 | 4 | **Established** |

Evidence: Depth — rigorous epistemological critique of probabilistic risk modelling. Currency — critique validated post-GFC; Basel shift to ES supports the argument.

**Activation signals:** Interest rate models, model calibration, critique of VaR, model limitations, swaption pricing

**Key principles:**

- **Calibration is not validation** — a model that fits market prices today may be structurally wrong. Calibration absorbs model deficiencies into parameters rather than exposing them.
- **VaR limitations** — VaR creates a false sense of precision. The confidence interval around a VaR estimate is often wider than the estimate itself. Communicate uncertainty, not point estimates.
- **Interest rate modeling** — LIBOR Market Model (BGM), Hull-White, and other frameworks each make different assumptions about rate dynamics. The choice must be driven by the instruments being priced.
- **Model risk awareness** — practitioners should understand what their models assume, where those assumptions break down, and what the consequences are.

---

## Paul Glasserman

**Source:** Paul Glasserman, *Monte Carlo Methods in Financial Engineering*, Springer (2003)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 3 | 5 | 4 | **Established** |

Evidence: Authority — definitive reference for Monte Carlo in finance; Columbia professor. Publication — Springer Applications of Mathematics series. Adoption — standard in quant finance PhD programmes. Currency — Monte Carlo methods mathematically mature; core techniques unchanged.

**Work score — *Monte Carlo Methods in Financial Engineering*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 5 | 4 | 5 | **Canonical** |

Evidence: Specificity — path generation, variance reduction, sensitivity computation, quasi-random sequences. Depth — convergence proofs, variance reduction properties, PhD-level mathematics. Influence — cited in virtually every MC financial engineering paper.

**Activation signals:** Monte Carlo simulation, variance reduction, path-dependent derivatives, simulation architecture

**Key principles:**

- **Variance reduction** — antithetic variates, control variates, importance sampling, and stratified sampling can dramatically improve convergence. Brute-force simulation is almost never the right approach.
- **Path generation** — the choice of discretisation scheme (Euler, Milstein) and the number of time steps affect both accuracy and performance. These are architectural decisions.
- **Greek computation via simulation** — pathwise derivatives and likelihood ratio methods for computing sensitivities within Monte Carlo. Finite differences are simple but noisy.
- **Quasi-random sequences** — Sobol and Halton sequences provide better coverage than pseudo-random numbers for high-dimensional problems.

---

## Regulatory & Standards References

### Basel Committee (BCBS) — FRTB

**Source:** Basel Committee on Banking Supervision, *Minimum capital requirements for market risk* (MAR), January 2019 (revised)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 5 | 5 | 5 | **Canonical** |

Evidence: Authority — sole international standard-setter for bank capital. Publication — formal BIS publication. Breadth — full market risk framework (SA, IMA, P&L attribution, NMRF). Adoption — all BCBS member jurisdictions implementing. Currency — 2019 standard with ongoing revisions.

**Work score — *Minimum capital requirements for market risk* (MAR):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 5 | 5 | 5 | **Canonical** |

Evidence: Specificity — every provision specific to trading book risk. Depth — prescribes exact risk weights, correlations, liquidity horizons. Currency — active standard under ongoing revision. Influence — mandates bank behaviour globally.

**Activation signals:** Regulatory capital calculation, standardised approach, internal models approach, P&L attribution test, risk factor eligibility test

**Key principles:**

- **Standardised Approach (SA)** — sensitivities-based method using prescribed risk weights and correlations. Delta, vega, and curvature charges.
- **Internal Models Approach (IMA)** — Expected Shortfall at 97.5% confidence, liquidity-adjusted horizons, desk-level approval via P&L attribution and backtesting.
- **Trading book / banking book boundary** — clear rules for which instruments belong where. Reclassification is restricted.
- **Non-modellable risk factors (NMRFs)** — risk factors without sufficient real price observations must be capitalised with stress scenarios, not modeled VaR.

### ISDA — SIMM

**Source:** ISDA, *Standard Initial Margin Model* (SIMM), methodology versions 2.0+

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 4 | 5 | 5 | **Canonical** |

Evidence: Authority — ISDA is authoritative OTC derivatives standards body; SIMM mandated under UMR. Adoption — adopted by 30+ dealers and hundreds of buy-side firms. Currency — annually versioned (v2.6, 2024).

**Work score — *Standard Initial Margin Model* (SIMM):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 5 | 5 | 5 | **Canonical** |

Evidence: Specificity — IM calculation for uncleared derivatives. Depth — risk weight tables, correlation matrices, aggregation formulae. Currency — annual recalibration. Influence — universal industry standard.

**Activation signals:** Initial margin calculation, uncleared derivatives, margin optimization

**Key principles:**

- **Sensitivities-based** — margin computed from delta, vega, and curvature sensitivities across risk classes.
- **Risk classes** — interest rate, credit (qualifying and non-qualifying), equity, commodity, FX.
- **Concentration thresholds** — large exposures receive higher margin requirements.
