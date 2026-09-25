# Oil & Fuels Market Outlook - Scenario Analysis
*As of 2026-09-25 | 2,000-path Monte Carlo, 180-day horizon*

**AAA national average retail prices (2026-09-25):** Regular **$4.492/gal**, diesel **$6.502/gal** ([AAA Gas Prices](https://gasprices.aaa.com/)). These are a snapshot from the last report run, not live prices. This model projects a *medium-term path* for the crude-to-pump price chain, not today's station price, so some gap is expected — but if the gap looks large, check the "Calibration inputs" line under Methodology first: the model is only as current as the last `calibrate.py` run.

## Executive Summary

Under current calibrated conditions, the model's base-case median retail gasoline price reaches **$4.30/gal** 180 days out (10th-90th percentile range $3.47-$5.36). Across the six stress scenarios modeled below, the most bullish case is **Combined Shock: Hormuz Closure + Saudi Cut**, which pushes the day-180 median to $5.43/gal (+26.3% vs. base), while **Iran Sanctions Lifted** offers the most relief, at $4.05/gal (-5.8% vs. base).

## Scenario Summary Table (Gasoline)

| Scenario | Day 30 | Day 90 | Day 180 | Day 180 10th-90th pct. | vs. Base |
|---|---|---|---|---|---|
| Base Case | $4.47 | $4.42 | $4.30 | $3.47-$5.36 | - |
| Hormuz Closure | $5.85 | $5.65 | $5.27 | $3.92-$7.27 | +22.6% |
| Hormuz De-Risked | $4.46 | $4.40 | $4.31 | $3.54-$5.20 | +0.3% |
| Saudi Production -20% | $4.68 | $4.59 | $4.46 | $3.53-$5.61 | +3.6% |
| Iran Sanctions Lifted | $4.18 | $4.14 | $4.05 | $3.25-$5.13 | -5.8% |
| US Shale Surge | $4.33 | $4.30 | $4.19 | $3.40-$5.23 | -2.6% |
| Combined Shock: Hormuz Closure + Saudi Cut | $6.10 | $5.91 | $5.43 | $4.07-$7.77 | +26.3% |

## Scenario Summary Table (Diesel, Day 180 median)

| Scenario | Day 180 Diesel |
|---|---|
| Base Case | $6.00 |
| Hormuz Closure | $6.98 |
| Hormuz De-Risked | $6.01 |
| Saudi Production -20% | $6.17 |
| Iran Sanctions Lifted | $5.76 |
| US Shale Surge | $5.92 |
| Combined Shock: Hormuz Closure + Saudi Cut | $7.17 |

## Scenario Detail

### Base Case

Current calibrated market conditions; no policy or geopolitical shock applied.

Day-180 median: **$4.30/gal** gasoline (base case), $6.00/gal diesel.

### Hormuz Closure

Strait of Hormuz effectively shut: roughly 55% of its normal throughput is assumed offline, chokepoint disruption frequency quadruples, and the war-risk shipping premium triples.

Day-180 median: **$5.27/gal** gasoline (+22.6% vs. base), $6.98/gal diesel.

### Hormuz De-Risked

Geopolitical tension around the strait fully unwinds: disruption frequency falls to a fifth of baseline and the war-risk premium halves, with no direct change to physical supply.

Day-180 median: **$4.31/gal** gasoline (+0.3% vs. base), $6.01/gal diesel.

### Saudi Production -20%

Saudi Arabia cuts output and spare capacity by 20%, e.g. an OPEC+ supply-discipline shock.

Day-180 median: **$4.46/gal** gasoline (+3.6% vs. base), $6.17/gal diesel.

### Iran Sanctions Lifted

Sanctions are lifted, letting Iranian output ramp toward a materially higher production ceiling.

Day-180 median: **$4.05/gal** gasoline (-5.8% vs. base), $5.76/gal diesel.

### US Shale Surge

US shale operators ramp drilling activity, lifting both current output and spare capacity.

Day-180 median: **$4.19/gal** gasoline (-2.6% vs. base), $5.92/gal diesel.

### Combined Shock: Hormuz Closure + Saudi Cut

A simultaneous Hormuz closure and 20% Saudi production cut - a tail-risk stack of the two largest supply-side scenarios.

Day-180 median: **$5.43/gal** gasoline (+26.3% vs. base), $7.17/gal diesel.

## Charts

![Gasoline scenario paths](scenario_gasoline_paths.png)

![Diesel scenario paths](scenario_diesel_paths.png)

![Day-180 scenario ranking](scenario_day180_ranking.png)

## Methodology

Each scenario re-runs the full 2,000-path stochastic simulation (`simulate.go`) with a modified set of inputs. Chokepoint scenarios (Hormuz closure/de-risking) adjust the model's existing disruption frequency and shipping-risk mechanics directly. Production scenarios additionally apply a first-order crude price shock: each 1% of global supply added or removed is assumed to move crude price 6% in the opposite direction (a simplifying short-run elasticity assumption, not a fitted econometric estimate), with volatility scaled up in proportion to shock size so tail scenarios carry wider, not just higher or lower, confidence bands. This is a model output for illustrative what-if analysis, not investment advice.

**Calibration inputs:** last calibrated on **2026-09-25** by `calibrate.py` from live NYMEX crude/gasoline/diesel futures (`yfinance`). If that date is stale, or reads "unknown" (no `date_calibrated` field), the base case below reflects old or placeholder inputs rather than today's market — re-run `python calibrate.py` before trusting the baseline.
