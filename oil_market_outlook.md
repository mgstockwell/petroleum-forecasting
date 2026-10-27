# Oil & Fuels Market Outlook - Scenario Analysis
*As of 2026-10-27 | 2,000-path Monte Carlo, 180-day horizon*

**AAA national average retail prices (2026-10-27):** Regular **$4.266/gal**, diesel **$6.352/gal** ([AAA Gas Prices](https://gasprices.aaa.com/)). These are a snapshot from the last report run, not live prices. This model projects a *medium-term path* for the crude-to-pump price chain, not today's station price, so some gap is expected — but if the gap looks large, check the "Calibration inputs" line under Methodology first: the model is only as current as the last `calibrate.py` run.

## Executive Summary

Under current calibrated conditions, the model's base-case median retail gasoline price reaches **$4.35/gal** 180 days out (10th-90th percentile range $3.51-$5.51). Across the six stress scenarios modeled below, the most bullish case is **Combined Shock: Hormuz Closure + Saudi Cut**, which pushes the day-180 median to $5.91/gal (+35.9% vs. base), while **Iran Sanctions Lifted** offers the most relief, at $4.09/gal (-6.0% vs. base).

## Scenario Summary Table (Gasoline)

| Scenario | Day 30 | Day 90 | Day 180 | Day 180 10th-90th pct. | vs. Base |
|---|---|---|---|---|---|
| Base Case | $4.32 | $4.21 | $4.35 | $3.51-$5.51 | - |
| Hormuz Closure | $5.74 | $5.63 | $5.72 | $4.31-$7.97 | +31.5% |
| Hormuz De-Risked | $4.23 | $4.12 | $4.28 | $3.46-$5.30 | -1.6% |
| Saudi Production -20% | $4.57 | $4.47 | $4.56 | $3.65-$5.86 | +4.8% |
| Iran Sanctions Lifted | $4.05 | $3.92 | $4.09 | $3.35-$5.15 | -6.0% |
| US Shale Surge | $4.20 | $4.11 | $4.27 | $3.51-$5.35 | -1.8% |
| Combined Shock: Hormuz Closure + Saudi Cut | $5.99 | $5.85 | $5.91 | $4.37-$8.21 | +35.9% |

## Scenario Summary Table (Diesel)

| Scenario | Day 30 | Day 60 | Day 90 | Day 180 |
|---|---|---|---|---|
| Base Case | $6.08 | $5.98 | $5.84 | $5.46 |
| Hormuz Closure | $7.52 | $7.39 | $7.27 | $6.81 |
| Hormuz De-Risked | $5.99 | $5.85 | $5.74 | $5.35 |
| Saudi Production -20% | $6.33 | $6.19 | $6.10 | $5.69 |
| Iran Sanctions Lifted | $5.81 | $5.70 | $5.59 | $5.21 |
| US Shale Surge | $5.97 | $5.84 | $5.75 | $5.36 |
| Combined Shock: Hormuz Closure + Saudi Cut | $7.73 | $7.64 | $7.48 | $6.98 |

## Scenario Detail

### Base Case

Current calibrated market conditions, including the manually-reviewed disruption_severity.json blend toward current chokepoint/freight conditions (see Methodology); no additional policy or geopolitical shock applied on top.

Day-180 median: **$4.35/gal** gasoline (base case), $5.46/gal diesel.

### Hormuz Closure

Strait of Hormuz effectively shut: roughly 55% of its normal throughput is assumed offline, chokepoint disruption frequency quadruples, and the war-risk shipping premium triples.

Day-180 median: **$5.72/gal** gasoline (+31.5% vs. base), $6.81/gal diesel.

### Hormuz De-Risked

Geopolitical tension around the strait fully unwinds: disruption frequency falls to a fifth of baseline and the war-risk premium halves, with no direct change to physical supply.

Day-180 median: **$4.28/gal** gasoline (-1.6% vs. base), $5.35/gal diesel.

### Saudi Production -20%

Saudi Arabia cuts output and spare capacity by 20%, e.g. an OPEC+ supply-discipline shock.

Day-180 median: **$4.56/gal** gasoline (+4.8% vs. base), $5.69/gal diesel.

### Iran Sanctions Lifted

Sanctions are lifted, letting Iranian output ramp toward a materially higher production ceiling.

Day-180 median: **$4.09/gal** gasoline (-6.0% vs. base), $5.21/gal diesel.

### US Shale Surge

US shale operators ramp drilling activity, lifting both current output and spare capacity.

Day-180 median: **$4.27/gal** gasoline (-1.8% vs. base), $5.36/gal diesel.

### Combined Shock: Hormuz Closure + Saudi Cut

A simultaneous Hormuz closure and 20% Saudi production cut - a tail-risk stack of the two largest supply-side scenarios.

Day-180 median: **$5.91/gal** gasoline (+35.9% vs. base), $6.98/gal diesel.

## Charts

![Gasoline scenario paths](scenario_gasoline_paths.png)

![Diesel scenario paths](scenario_diesel_paths.png)

![Day-180 scenario ranking](scenario_day180_ranking.png)

## Methodology

Each scenario re-runs the full 2,000-path stochastic simulation (`simulate.go`) with a modified set of inputs. Chokepoint scenarios (Hormuz closure/de-risking) adjust the model's existing disruption frequency and shipping-risk mechanics directly. Production scenarios additionally apply a first-order crude price shock: each 1% of global supply added or removed is assumed to move crude price 6% in the opposite direction (a simplifying short-run elasticity assumption, not a fitted econometric estimate), incorporated through a front-loaded exponential adjustment with a 7-day half-life: 50% after one week, 75% after two weeks, and about 95% by day 30, with no abrupt cutoff. The premium or discount persists while the scenario remains in force; no reopening or recovery date is assumed. The adjustment speed is an illustrative assumption, not a fitted retail pass-through estimate or a separate crude-to-pump lag. Charts share the base case's day-0 modeled retail price (not the AAA snapshot), with volatility scaled up in proportion to shock size so tail scenarios carry wider, not just higher or lower, confidence bands. This is a model output for illustrative what-if analysis, not investment advice.

**Reading the lines:** scenario lines are cross-path medians, not individual daily price trajectories. Individual paths contain random moves and jumps; medians are naturally smoother. No cosmetic noise is added to make the outlook look like a realized price path.

**Drift anchor:** the base case has no independent view on direction. Crude and both crack spreads are anchored to the CL/HO/RB forward curves, so the expected path is the market's own, and the simulation supplies the distribution around it. Scenario shocks shift that whole anchor path rather than replacing it. Futures are a risk-neutral expectation and not a forecast - in backwardation they will tend to read lower than a realized spot path - so treat the level as market-implied rather than predicted. Note also that the **median** sits below the **mean** at longer horizons because crude is lognormal: that gap is a property of the distribution, not a bearish view.

**Calibration inputs:** last calibrated on **2026-10-21** by `calibrate.py` from live NYMEX crude/gasoline/diesel futures (`yfinance`). If that date is stale, or reads "unknown" (no `date_calibrated` field), the base case below reflects old or placeholder inputs rather than today's market — re-run `python calibrate.py` before trusting the baseline.

**Current-conditions input:** the base case blends 40% of the way from calm-floor chokepoint/freight assumptions toward the Hormuz Closure scenario's values, per `disruption_severity.json` (reviewed 2026-09-30: EIA weekly retail diesel $5.97->$6.29->$6.53/gal over 3 weeks; Goldman Sachs/Morgan Stanley notes on distillate tightness, refinery crunch, and rerouted tanker freight amid Hormuz-related disruption). This is a manual, periodically-updated judgment call, not a live feed — re-review it as conditions change.
