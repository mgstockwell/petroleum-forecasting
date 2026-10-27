# Oil & Fuels Market Outlook - Scenario Analysis
*As of 2026-10-27 | 2,000-path Monte Carlo, 180-day horizon*

**AAA national average retail prices (2026-10-27):** Regular **$4.266/gal**, diesel **$6.352/gal** ([AAA Gas Prices](https://gasprices.aaa.com/)). These are a snapshot from the last report run, not live prices. This model projects a *medium-term path* for the crude-to-pump price chain, not today's station price, so some gap is expected — but if the gap looks large, check the "Calibration inputs" line under Methodology first: the model is only as current as the last `calibrate.py` run.

## Executive Summary

Under current calibrated conditions, the model's base-case median retail gasoline price reaches **$4.49/gal** 180 days out (10th-90th percentile range $3.64-$5.65). Across the six stress scenarios modeled below, the most bullish case is **Combined Shock: Hormuz Closure + Saudi Cut**, which pushes the day-180 median to $6.10/gal (+35.9% vs. base), while **Iran Sanctions Lifted** offers the most relief, at $4.16/gal (-7.3% vs. base).

## Hormuz Traffic Monitor

[IMF PortWatch](https://portwatch.imf.org/pages/cb5856222a5b4105adc6ee7e880a1730), retrieved 2026-10-27. Seven-calendar-day window ending on the latest available observation: **2026-10-12 to 2026-10-18**; coverage **7/7 days**; latest observation **9 days old**.

Observed tanker transits: **0.57/day**; all vessel transits: **3.71/day** (arithmetic seven-day averages, including reported zeros).

> **Traffic data warning:** STALE: latest observation is 9 days old (warning threshold: more than 7 days). This is not traffic for the current trailing week.

**AIS-quality limitation:** GPS jamming, AIS spoofing, and vessels going dark can distort observed counts in either direction. A seven-day average smooths daily variation but cannot correct these biases. No spoofing correction or statistical confidence interval is claimed; independent traffic evidence is needed. Transit counts are not oil cargo volumes or a calibrated disruption-severity score. This monitor does not change the manually reviewed `disruption_severity.json` input or any simulation parameters.

## Scenario Summary Table (Gasoline)

| Scenario | Day 30 | Day 90 | Day 180 | Day 180 10th-90th pct. | vs. Base |
|---|---|---|---|---|---|
| Base Case | $4.43 | $4.36 | $4.49 | $3.64-$5.65 | - |
| Hormuz Closure | $5.91 | $5.84 | $5.86 | $4.43-$8.07 | +30.4% |
| Hormuz De-Risked | $4.31 | $4.19 | $4.34 | $3.53-$5.44 | -3.3% |
| Saudi Production -20% | $4.66 | $4.55 | $4.74 | $3.73-$6.03 | +5.6% |
| Iran Sanctions Lifted | $4.09 | $4.02 | $4.16 | $3.37-$5.26 | -7.3% |
| US Shale Surge | $4.28 | $4.18 | $4.30 | $3.51-$5.44 | -4.2% |
| Combined Shock: Hormuz Closure + Saudi Cut | $6.20 | $6.06 | $6.10 | $4.54-$8.58 | +35.9% |

## Scenario Summary Table (Diesel)

| Scenario | Day 30 | Day 60 | Day 90 | Day 180 |
|---|---|---|---|---|
| Base Case | $6.25 | $6.18 | $6.07 | $5.67 |
| Hormuz Closure | $7.71 | $7.71 | $7.58 | $7.04 |
| Hormuz De-Risked | $6.11 | $6.04 | $5.93 | $5.56 |
| Saudi Production -20% | $6.47 | $6.40 | $6.29 | $5.93 |
| Iran Sanctions Lifted | $5.92 | $5.87 | $5.76 | $5.37 |
| US Shale Surge | $6.09 | $6.03 | $5.92 | $5.52 |
| Combined Shock: Hormuz Closure + Saudi Cut | $8.00 | $7.96 | $7.80 | $7.29 |

## Scenario Detail

### Base Case

Current calibrated market conditions, including the manually-reviewed disruption_severity.json blend toward current chokepoint/freight conditions (see Methodology); no additional policy or geopolitical shock applied on top.

Day-180 median: **$4.49/gal** gasoline (base case), $5.67/gal diesel.

### Hormuz Closure

Strait of Hormuz effectively shut: roughly 55% of its normal throughput is assumed offline, chokepoint disruption frequency quadruples, and the war-risk shipping premium triples.

Day-180 median: **$5.86/gal** gasoline (+30.4% vs. base), $7.04/gal diesel.

### Hormuz De-Risked

Geopolitical tension around the strait fully unwinds: disruption frequency falls to a fifth of baseline and the war-risk premium halves, with no direct change to physical supply.

Day-180 median: **$4.34/gal** gasoline (-3.3% vs. base), $5.56/gal diesel.

### Saudi Production -20%

Saudi Arabia cuts output and spare capacity by 20%, e.g. an OPEC+ supply-discipline shock.

Day-180 median: **$4.74/gal** gasoline (+5.6% vs. base), $5.93/gal diesel.

### Iran Sanctions Lifted

Sanctions are lifted, letting Iranian output ramp toward a materially higher production ceiling.

Day-180 median: **$4.16/gal** gasoline (-7.3% vs. base), $5.37/gal diesel.

### US Shale Surge

US shale operators ramp drilling activity, lifting both current output and spare capacity.

Day-180 median: **$4.30/gal** gasoline (-4.2% vs. base), $5.52/gal diesel.

### Combined Shock: Hormuz Closure + Saudi Cut

A simultaneous Hormuz closure and 20% Saudi production cut - a tail-risk stack of the two largest supply-side scenarios.

Day-180 median: **$6.10/gal** gasoline (+35.9% vs. base), $7.29/gal diesel.

## Charts

![Gasoline scenario paths](scenario_gasoline_paths.png)

![Diesel scenario paths](scenario_diesel_paths.png)

![Day-180 scenario ranking](scenario_day180_ranking.png)

## Methodology

Each scenario re-runs the full 2,000-path stochastic simulation (`simulate.go`) with a modified set of inputs. Chokepoint scenarios (Hormuz closure/de-risking) adjust the model's existing disruption frequency and shipping-risk mechanics directly. Production scenarios additionally apply a first-order crude price shock: each 1% of global supply added or removed is assumed to move crude price 6% in the opposite direction (a simplifying short-run elasticity assumption, not a fitted econometric estimate), incorporated through a front-loaded exponential adjustment with a 7-day half-life: 50% after one week, 75% after two weeks, and about 95% by day 30, with no abrupt cutoff. The premium or discount persists while the scenario remains in force; no reopening or recovery date is assumed. The adjustment speed is an illustrative assumption, not a fitted retail pass-through estimate or a separate crude-to-pump lag. Charts share the base case's day-0 modeled retail price (not the AAA snapshot), with volatility scaled up in proportion to shock size so tail scenarios carry wider, not just higher or lower, confidence bands. This is a model output for illustrative what-if analysis, not investment advice.

**Reading the lines:** scenario lines are cross-path medians, not individual daily price trajectories. Individual paths contain random moves and jumps; medians are naturally smoother. No cosmetic noise is added to make the outlook look like a realized price path.

**Drift anchor:** the base case has no independent view on direction. Crude and both crack spreads are anchored to the CL/HO/RB forward curves, so the expected path is the market's own, and the simulation supplies the distribution around it. Scenario shocks shift that whole anchor path rather than replacing it. Futures are a risk-neutral expectation and not a forecast - in backwardation they will tend to read lower than a realized spot path - so treat the level as market-implied rather than predicted. Note also that the **median** sits below the **mean** at longer horizons because crude is lognormal: that gap is a property of the distribution, not a bearish view.

**Calibration inputs:** last calibrated on **2026-10-27** by `calibrate.py` from live NYMEX crude/gasoline/diesel futures (`yfinance`). If that date is stale, or reads "unknown" (no `date_calibrated` field), the base case below reflects old or placeholder inputs rather than today's market — re-run `python calibrate.py` before trusting the baseline.

**Current-conditions input:** the base case blends 40% of the way from calm-floor chokepoint/freight assumptions toward the Hormuz Closure scenario's values, per `disruption_severity.json` (reviewed 2026-09-30: EIA weekly retail diesel $5.97->$6.29->$6.53/gal over 3 weeks; Goldman Sachs/Morgan Stanley notes on distillate tightness, refinery crunch, and rerouted tanker freight amid Hormuz-related disruption). This is a manual, periodically-updated judgment call, not a live feed — re-review it as conditions change.
