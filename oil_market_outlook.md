# Oil & Fuels Market Outlook - Scenario Analysis
*As of 2026-09-30 | 2,000-path Monte Carlo, 180-day horizon*

**AAA national average retail prices (2026-09-30):** Regular **$4.434/gal**, diesel **$6.414/gal** ([AAA Gas Prices](https://gasprices.aaa.com/)). These are a snapshot from the last report run, not live prices. This model projects a *medium-term path* for the crude-to-pump price chain, not today's station price, so some gap is expected — but if the gap looks large, check the "Calibration inputs" line under Methodology first: the model is only as current as the last `calibrate.py` run.

## Executive Summary

Under current calibrated conditions, the model's base-case median retail gasoline price reaches **$4.33/gal** 180 days out (10th-90th percentile range $3.52-$5.42). Across the six stress scenarios modeled below, the most bullish case is **Combined Shock: Hormuz Closure + Saudi Cut**, which pushes the day-180 median to $5.71/gal (+31.9% vs. base), while **Iran Sanctions Lifted** offers the most relief, at $4.09/gal (-5.5% vs. base).

## Scenario Summary Table (Gasoline)

| Scenario | Day 30 | Day 90 | Day 180 | Day 180 10th-90th pct. | vs. Base |
|---|---|---|---|---|---|
| Base Case | $4.62 | $4.30 | $4.33 | $3.52-$5.42 | - |
| Hormuz Closure | $6.11 | $5.66 | $5.59 | $4.24-$7.84 | +29.2% |
| Hormuz De-Risked | $4.51 | $4.16 | $4.17 | $3.38-$5.22 | -3.7% |
| Saudi Production -20% | $4.87 | $4.50 | $4.52 | $3.60-$5.77 | +4.4% |
| Iran Sanctions Lifted | $4.34 | $4.01 | $4.09 | $3.29-$5.13 | -5.5% |
| US Shale Surge | $4.50 | $4.15 | $4.19 | $3.42-$5.24 | -3.2% |
| Combined Shock: Hormuz Closure + Saudi Cut | $6.35 | $5.87 | $5.71 | $4.18-$8.31 | +31.9% |

## Scenario Summary Table (Diesel)

| Scenario | Day 30 | Day 60 | Day 90 | Day 180 |
|---|---|---|---|---|
| Base Case | $6.34 | $6.18 | $6.04 | $5.57 |
| Hormuz Closure | $7.82 | $7.61 | $7.39 | $6.88 |
| Hormuz De-Risked | $6.23 | $6.06 | $5.90 | $5.41 |
| Saudi Production -20% | $6.58 | $6.41 | $6.27 | $5.78 |
| Iran Sanctions Lifted | $6.06 | $5.88 | $5.77 | $5.35 |
| US Shale Surge | $6.22 | $6.03 | $5.92 | $5.47 |
| Combined Shock: Hormuz Closure + Saudi Cut | $8.04 | $7.87 | $7.65 | $7.01 |

## Scenario Detail

### Base Case

Current calibrated market conditions, including the manually-reviewed disruption_severity.json blend toward current chokepoint/freight conditions (see Methodology); no additional policy or geopolitical shock applied on top.

Day-180 median: **$4.33/gal** gasoline (base case), $5.57/gal diesel.

### Hormuz Closure

Strait of Hormuz effectively shut: roughly 55% of its normal throughput is assumed offline, chokepoint disruption frequency quadruples, and the war-risk shipping premium triples.

Day-180 median: **$5.59/gal** gasoline (+29.2% vs. base), $6.88/gal diesel.

### Hormuz De-Risked

Geopolitical tension around the strait fully unwinds: disruption frequency falls to a fifth of baseline and the war-risk premium halves, with no direct change to physical supply.

Day-180 median: **$4.17/gal** gasoline (-3.7% vs. base), $5.41/gal diesel.

### Saudi Production -20%

Saudi Arabia cuts output and spare capacity by 20%, e.g. an OPEC+ supply-discipline shock.

Day-180 median: **$4.52/gal** gasoline (+4.4% vs. base), $5.78/gal diesel.

### Iran Sanctions Lifted

Sanctions are lifted, letting Iranian output ramp toward a materially higher production ceiling.

Day-180 median: **$4.09/gal** gasoline (-5.5% vs. base), $5.35/gal diesel.

### US Shale Surge

US shale operators ramp drilling activity, lifting both current output and spare capacity.

Day-180 median: **$4.19/gal** gasoline (-3.2% vs. base), $5.47/gal diesel.

### Combined Shock: Hormuz Closure + Saudi Cut

A simultaneous Hormuz closure and 20% Saudi production cut - a tail-risk stack of the two largest supply-side scenarios.

Day-180 median: **$5.71/gal** gasoline (+31.9% vs. base), $7.01/gal diesel.

## Charts

![Gasoline scenario paths](scenario_gasoline_paths.png)

![Diesel scenario paths](scenario_diesel_paths.png)

![Day-180 scenario ranking](scenario_day180_ranking.png)

## Methodology

Each scenario re-runs the full 2,000-path stochastic simulation (`simulate.go`) with a modified set of inputs. Chokepoint scenarios (Hormuz closure/de-risking) adjust the model's existing disruption frequency and shipping-risk mechanics directly. Production scenarios additionally apply a first-order crude price shock: each 1% of global supply added or removed is assumed to move crude price 6% in the opposite direction (a simplifying short-run elasticity assumption, not a fitted econometric estimate), with volatility scaled up in proportion to shock size so tail scenarios carry wider, not just higher or lower, confidence bands. This is a model output for illustrative what-if analysis, not investment advice.

**Drift anchor:** the base case has no independent view on direction. Crude and both crack spreads are anchored to the CL/HO/RB forward curves, so the expected path is the market's own, and the simulation supplies the distribution around it. Scenario shocks shift that whole anchor path rather than replacing it. Futures are a risk-neutral expectation and not a forecast - in backwardation they will tend to read lower than a realized spot path - so treat the level as market-implied rather than predicted. Note also that the **median** sits below the **mean** at longer horizons because crude is lognormal: that gap is a property of the distribution, not a bearish view.

**Calibration inputs:** last calibrated on **2026-09-30** by `calibrate.py` from live NYMEX crude/gasoline/diesel futures (`yfinance`). If that date is stale, or reads "unknown" (no `date_calibrated` field), the base case below reflects old or placeholder inputs rather than today's market — re-run `python calibrate.py` before trusting the baseline.

**Current-conditions input:** the base case blends 40% of the way from calm-floor chokepoint/freight assumptions toward the Hormuz Closure scenario's values, per `disruption_severity.json` (reviewed 2026-09-30: EIA weekly retail diesel $5.97->$6.29->$6.53/gal over 3 weeks; Goldman Sachs/Morgan Stanley notes on distillate tightness, refinery crunch, and rerouted tanker freight amid Hormuz-related disruption). This is a manual, periodically-updated judgment call, not a live feed — re-review it as conditions change.
