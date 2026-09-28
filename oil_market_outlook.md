# Oil & Fuels Market Outlook - Scenario Analysis
*As of 2026-09-28 | 2,000-path Monte Carlo, 180-day horizon*

**AAA national average retail prices (2026-09-28):** Regular **$4.477/gal**, diesel **$6.453/gal** ([AAA Gas Prices](https://gasprices.aaa.com/)). These are a snapshot from the last report run, not live prices. This model projects a *medium-term path* for the crude-to-pump price chain, not today's station price, so some gap is expected — but if the gap looks large, check the "Calibration inputs" line under Methodology first: the model is only as current as the last `calibrate.py` run.

## Executive Summary

Under current calibrated conditions, the model's base-case median retail gasoline price reaches **$4.30/gal** 180 days out (10th-90th percentile range $3.47-$5.39). Across the six stress scenarios modeled below, the most bullish case is **Combined Shock: Hormuz Closure + Saudi Cut**, which pushes the day-180 median to $5.54/gal (+28.8% vs. base), while **Iran Sanctions Lifted** offers the most relief, at $4.06/gal (-5.6% vs. base).

## Scenario Summary Table (Gasoline)

| Scenario | Day 30 | Day 90 | Day 180 | Day 180 10th-90th pct. | vs. Base |
|---|---|---|---|---|---|
| Base Case | $4.50 | $4.43 | $4.30 | $3.47-$5.39 | - |
| Hormuz Closure | $5.93 | $5.70 | $5.36 | $4.06-$7.37 | +24.5% |
| Hormuz De-Risked | $4.47 | $4.42 | $4.33 | $3.52-$5.22 | +0.6% |
| Saudi Production -20% | $4.69 | $4.60 | $4.48 | $3.55-$5.66 | +4.2% |
| Iran Sanctions Lifted | $4.19 | $4.16 | $4.06 | $3.28-$5.07 | -5.6% |
| US Shale Surge | $4.35 | $4.31 | $4.22 | $3.37-$5.24 | -1.9% |
| Combined Shock: Hormuz Closure + Saudi Cut | $6.19 | $5.97 | $5.54 | $4.14-$7.79 | +28.8% |

## Scenario Summary Table (Diesel, Day 180 median)

| Scenario | Day 180 Diesel |
|---|---|
| Base Case | $6.06 |
| Hormuz Closure | $7.06 |
| Hormuz De-Risked | $6.05 |
| Saudi Production -20% | $6.21 |
| Iran Sanctions Lifted | $5.83 |
| US Shale Surge | $5.94 |
| Combined Shock: Hormuz Closure + Saudi Cut | $7.29 |

## Scenario Detail

### Base Case

Current calibrated market conditions; no policy or geopolitical shock applied.

Day-180 median: **$4.30/gal** gasoline (base case), $6.06/gal diesel.

### Hormuz Closure

Strait of Hormuz effectively shut: roughly 55% of its normal throughput is assumed offline, chokepoint disruption frequency quadruples, and the war-risk shipping premium triples.

Day-180 median: **$5.36/gal** gasoline (+24.5% vs. base), $7.06/gal diesel.

### Hormuz De-Risked

Geopolitical tension around the strait fully unwinds: disruption frequency falls to a fifth of baseline and the war-risk premium halves, with no direct change to physical supply.

Day-180 median: **$4.33/gal** gasoline (+0.6% vs. base), $6.05/gal diesel.

### Saudi Production -20%

Saudi Arabia cuts output and spare capacity by 20%, e.g. an OPEC+ supply-discipline shock.

Day-180 median: **$4.48/gal** gasoline (+4.2% vs. base), $6.21/gal diesel.

### Iran Sanctions Lifted

Sanctions are lifted, letting Iranian output ramp toward a materially higher production ceiling.

Day-180 median: **$4.06/gal** gasoline (-5.6% vs. base), $5.83/gal diesel.

### US Shale Surge

US shale operators ramp drilling activity, lifting both current output and spare capacity.

Day-180 median: **$4.22/gal** gasoline (-1.9% vs. base), $5.94/gal diesel.

### Combined Shock: Hormuz Closure + Saudi Cut

A simultaneous Hormuz closure and 20% Saudi production cut - a tail-risk stack of the two largest supply-side scenarios.

Day-180 median: **$5.54/gal** gasoline (+28.8% vs. base), $7.29/gal diesel.

## Charts

![Gasoline scenario paths](scenario_gasoline_paths.png)

![Diesel scenario paths](scenario_diesel_paths.png)

![Day-180 scenario ranking](scenario_day180_ranking.png)

## Methodology

Each scenario re-runs the full 2,000-path stochastic simulation (`simulate.go`) with a modified set of inputs. Chokepoint scenarios (Hormuz closure/de-risking) adjust the model's existing disruption frequency and shipping-risk mechanics directly. Production scenarios additionally apply a first-order crude price shock: each 1% of global supply added or removed is assumed to move crude price 6% in the opposite direction (a simplifying short-run elasticity assumption, not a fitted econometric estimate), with volatility scaled up in proportion to shock size so tail scenarios carry wider, not just higher or lower, confidence bands. This is a model output for illustrative what-if analysis, not investment advice.

**Calibration inputs:** last calibrated on **2026-09-28** by `calibrate.py` from live NYMEX crude/gasoline/diesel futures (`yfinance`). If that date is stale, or reads "unknown" (no `date_calibrated` field), the base case below reflects old or placeholder inputs rather than today's market — re-run `python calibrate.py` before trusting the baseline.
