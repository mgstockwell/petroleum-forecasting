# Oil & Fuels Market Outlook - Scenario Analysis
*As of 2026-09-28 | 2,000-path Monte Carlo, 180-day horizon*

**Compare against today's actual retail price:** [AAA National Average Gas Prices](https://gasprices.aaa.com/). This model projects a *medium-term path* for the crude-to-pump price chain, not today's station price, so some gap is expected — but if the gap looks large, check the "Calibration inputs" line under Methodology first: the model is only as current as the last `calibrate.py` run.

## Executive Summary

Under current calibrated conditions, the model's base-case median retail gasoline price reaches **$4.37/gal** 180 days out (10th-90th percentile range $3.52-$5.44). Across the six stress scenarios modeled below, the most bullish case is **Combined Shock: Hormuz Closure + Saudi Cut**, which pushes the day-180 median to $5.52/gal (+26.3% vs. base), while **Iran Sanctions Lifted** offers the most relief, at $4.07/gal (-6.9% vs. base).

## Scenario Summary Table (Gasoline)

| Scenario | Day 30 | Day 90 | Day 180 | Day 180 10th-90th pct. | vs. Base |
|---|---|---|---|---|---|
| Base Case | $4.51 | $4.46 | $4.37 | $3.52-$5.44 | - |
| Hormuz Closure | $5.96 | $5.81 | $5.41 | $4.07-$7.59 | +23.8% |
| Hormuz De-Risked | $4.50 | $4.41 | $4.29 | $3.51-$5.22 | -1.8% |
| Saudi Production -20% | $4.72 | $4.64 | $4.48 | $3.57-$5.68 | +2.5% |
| Iran Sanctions Lifted | $4.20 | $4.15 | $4.07 | $3.29-$5.11 | -6.9% |
| US Shale Surge | $4.36 | $4.29 | $4.19 | $3.37-$5.18 | -4.1% |
| Combined Shock: Hormuz Closure + Saudi Cut | $6.19 | $5.99 | $5.52 | $4.02-$7.86 | +26.3% |

## Scenario Summary Table (Diesel, Day 180 median)

| Scenario | Day 180 Diesel |
|---|---|
| Base Case | $6.05 |
| Hormuz Closure | $7.11 |
| Hormuz De-Risked | $6.03 |
| Saudi Production -20% | $6.19 |
| Iran Sanctions Lifted | $5.81 |
| US Shale Surge | $5.91 |
| Combined Shock: Hormuz Closure + Saudi Cut | $7.22 |

## Scenario Detail

### Base Case

Current calibrated market conditions; no policy or geopolitical shock applied.

Day-180 median: **$4.37/gal** gasoline (base case), $6.05/gal diesel.

### Hormuz Closure

Strait of Hormuz effectively shut: roughly 55% of its normal throughput is assumed offline, chokepoint disruption frequency quadruples, and the war-risk shipping premium triples.

Day-180 median: **$5.41/gal** gasoline (+23.8% vs. base), $7.11/gal diesel.

### Hormuz De-Risked

Geopolitical tension around the strait fully unwinds: disruption frequency falls to a fifth of baseline and the war-risk premium halves, with no direct change to physical supply.

Day-180 median: **$4.29/gal** gasoline (-1.8% vs. base), $6.03/gal diesel.

### Saudi Production -20%

Saudi Arabia cuts output and spare capacity by 20%, e.g. an OPEC+ supply-discipline shock.

Day-180 median: **$4.48/gal** gasoline (+2.5% vs. base), $6.19/gal diesel.

### Iran Sanctions Lifted

Sanctions are lifted, letting Iranian output ramp toward a materially higher production ceiling.

Day-180 median: **$4.07/gal** gasoline (-6.9% vs. base), $5.81/gal diesel.

### US Shale Surge

US shale operators ramp drilling activity, lifting both current output and spare capacity.

Day-180 median: **$4.19/gal** gasoline (-4.1% vs. base), $5.91/gal diesel.

### Combined Shock: Hormuz Closure + Saudi Cut

A simultaneous Hormuz closure and 20% Saudi production cut - a tail-risk stack of the two largest supply-side scenarios.

Day-180 median: **$5.52/gal** gasoline (+26.3% vs. base), $7.22/gal diesel.

## Charts

![Gasoline scenario paths](scenario_gasoline_paths.png)

![Diesel scenario paths](scenario_diesel_paths.png)

![Day-180 scenario ranking](scenario_day180_ranking.png)

## Methodology

Each scenario re-runs the full 2,000-path stochastic simulation (`simulate.go`) with a modified set of inputs. Chokepoint scenarios (Hormuz closure/de-risking) adjust the model's existing disruption frequency and shipping-risk mechanics directly. Production scenarios additionally apply a first-order crude price shock: each 1% of global supply added or removed is assumed to move crude price 6% in the opposite direction (a simplifying short-run elasticity assumption, not a fitted econometric estimate), with volatility scaled up in proportion to shock size so tail scenarios carry wider, not just higher or lower, confidence bands. This is a model output for illustrative what-if analysis, not investment advice.

**Calibration inputs:** last calibrated on **2026-09-28** by `calibrate.py` from live NYMEX crude/gasoline/diesel futures (`yfinance`). If that date is stale, or reads "unknown" (no `date_calibrated` field), the base case below reflects old or placeholder inputs rather than today's market — re-run `python calibrate.py` before trusting the baseline.
