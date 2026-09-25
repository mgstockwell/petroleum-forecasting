# Oil & Fuels Market Outlook - Scenario Analysis
*As of 2026-09-25 | 2,000-path Monte Carlo, 180-day horizon*

**Compare against today's actual retail price:** [AAA National Average Gas Prices](https://gasprices.aaa.com/). This model projects a *medium-term path* for the crude-to-pump price chain, not today's station price, so some gap is expected — but if the gap looks large, check the "Calibration inputs" line under Methodology first: the model is only as current as the last `calibrate.py` run.

## Executive Summary

Under current calibrated conditions, the model's base-case median retail gasoline price reaches **$3.50/gal** 180 days out (10th-90th percentile range $2.80-$4.28). Across the six stress scenarios modeled below, the most bullish case is **Combined Shock: Hormuz Closure + Saudi Cut**, which pushes the day-180 median to $4.74/gal (+35.4% vs. base), while **Iran Sanctions Lifted** offers the most relief, at $3.26/gal (-6.9% vs. base).

## Scenario Summary Table (Gasoline)

| Scenario | Day 30 | Day 90 | Day 180 | Day 180 10th-90th pct. | vs. Base |
|---|---|---|---|---|---|
| Base Case | $3.55 | $3.54 | $3.50 | $2.80-$4.28 | - |
| Hormuz Closure | $4.72 | $4.69 | $4.62 | $3.54-$6.17 | +32.0% |
| Hormuz De-Risked | $3.55 | $3.53 | $3.50 | $2.84-$4.20 | +0.0% |
| Saudi Production -20% | $3.74 | $3.71 | $3.67 | $2.93-$4.51 | +4.9% |
| Iran Sanctions Lifted | $3.31 | $3.30 | $3.26 | $2.61-$4.02 | -6.9% |
| US Shale Surge | $3.44 | $3.43 | $3.40 | $2.71-$4.15 | -2.9% |
| Combined Shock: Hormuz Closure + Saudi Cut | $4.91 | $4.86 | $4.74 | $3.60-$6.32 | +35.4% |

## Scenario Summary Table (Diesel, Day 180 median)

| Scenario | Day 180 Diesel |
|---|---|
| Base Case | $3.95 |
| Hormuz Closure | $5.06 |
| Hormuz De-Risked | $3.94 |
| Saudi Production -20% | $4.11 |
| Iran Sanctions Lifted | $3.70 |
| US Shale Surge | $3.84 |
| Combined Shock: Hormuz Closure + Saudi Cut | $5.18 |

## Scenario Detail

### Base Case

Current calibrated market conditions; no policy or geopolitical shock applied.

Day-180 median: **$3.50/gal** gasoline (base case), $3.95/gal diesel.

### Hormuz Closure

Strait of Hormuz effectively shut: roughly 55% of its normal throughput is assumed offline, chokepoint disruption frequency quadruples, and the war-risk shipping premium triples.

Day-180 median: **$4.62/gal** gasoline (+32.0% vs. base), $5.06/gal diesel.

### Hormuz De-Risked

Geopolitical tension around the strait fully unwinds: disruption frequency falls to a fifth of baseline and the war-risk premium halves, with no direct change to physical supply.

Day-180 median: **$3.50/gal** gasoline (+0.0% vs. base), $3.94/gal diesel.

### Saudi Production -20%

Saudi Arabia cuts output and spare capacity by 20%, e.g. an OPEC+ supply-discipline shock.

Day-180 median: **$3.67/gal** gasoline (+4.9% vs. base), $4.11/gal diesel.

### Iran Sanctions Lifted

Sanctions are lifted, letting Iranian output ramp toward a materially higher production ceiling.

Day-180 median: **$3.26/gal** gasoline (-6.9% vs. base), $3.70/gal diesel.

### US Shale Surge

US shale operators ramp drilling activity, lifting both current output and spare capacity.

Day-180 median: **$3.40/gal** gasoline (-2.9% vs. base), $3.84/gal diesel.

### Combined Shock: Hormuz Closure + Saudi Cut

A simultaneous Hormuz closure and 20% Saudi production cut - a tail-risk stack of the two largest supply-side scenarios.

Day-180 median: **$4.74/gal** gasoline (+35.4% vs. base), $5.18/gal diesel.

## Charts

![Gasoline scenario paths](scenario_gasoline_paths.png)

![Diesel scenario paths](scenario_diesel_paths.png)

![Day-180 scenario ranking](scenario_day180_ranking.png)

## Methodology

Each scenario re-runs the full 2,000-path stochastic simulation (`simulate.go`) with a modified set of inputs. Chokepoint scenarios (Hormuz closure/de-risking) adjust the model's existing disruption frequency and shipping-risk mechanics directly. Production scenarios additionally apply a first-order crude price shock: each 1% of global supply added or removed is assumed to move crude price 6% in the opposite direction (a simplifying short-run elasticity assumption, not a fitted econometric estimate), with volatility scaled up in proportion to shock size so tail scenarios carry wider, not just higher or lower, confidence bands. This is a model output for illustrative what-if analysis, not investment advice.

**Calibration inputs:** last calibrated on **unknown** by `calibrate.py` from live NYMEX crude/gasoline/diesel futures (`yfinance`). If that date is stale, or reads "unknown" (no `date_calibrated` field), the base case below reflects old or placeholder inputs rather than today's market — re-run `python calibrate.py` before trusting the baseline.
