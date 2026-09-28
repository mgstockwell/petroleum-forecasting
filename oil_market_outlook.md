# Oil & Fuels Market Outlook - Scenario Analysis
*As of 2026-09-28 | 2,000-path Monte Carlo, 180-day horizon*

**AAA national average retail prices (2026-09-28):** Regular **$4.477/gal**, diesel **$6.453/gal** ([AAA Gas Prices](https://gasprices.aaa.com/)). These are a snapshot from the last report run, not live prices. This model projects a *medium-term path* for the crude-to-pump price chain, not today's station price, so some gap is expected — but if the gap looks large, check the "Calibration inputs" line under Methodology first: the model is only as current as the last `calibrate.py` run.

## Executive Summary

Under current calibrated conditions, the model's base-case median retail gasoline price reaches **$4.16/gal** 180 days out (10th-90th percentile range $3.35-$5.31). Across the six stress scenarios modeled below, the most bullish case is **Combined Shock: Hormuz Closure + Saudi Cut**, which pushes the day-180 median to $5.58/gal (+34.1% vs. base), while **Iran Sanctions Lifted** offers the most relief, at $3.89/gal (-6.5% vs. base).

## Scenario Summary Table (Gasoline)

| Scenario | Day 30 | Day 90 | Day 180 | Day 180 10th-90th pct. | vs. Base |
|---|---|---|---|---|---|
| Base Case | $4.49 | $4.15 | $4.16 | $3.35-$5.31 | - |
| Hormuz Closure | $5.97 | $5.51 | $5.30 | $3.98-$7.55 | +27.4% |
| Hormuz De-Risked | $4.46 | $4.14 | $4.18 | $3.38-$5.23 | +0.5% |
| Saudi Production -20% | $4.72 | $4.36 | $4.34 | $3.42-$5.66 | +4.3% |
| Iran Sanctions Lifted | $4.18 | $3.86 | $3.89 | $3.15-$4.97 | -6.5% |
| US Shale Surge | $4.32 | $4.02 | $4.03 | $3.28-$5.18 | -3.1% |
| Combined Shock: Hormuz Closure + Saudi Cut | $6.22 | $5.77 | $5.58 | $4.07-$8.20 | +34.1% |

## Scenario Summary Table (Diesel, Day 180 median)

| Scenario | Day 180 Diesel |
|---|---|
| Base Case | $5.50 |
| Hormuz Closure | $6.59 |
| Hormuz De-Risked | $5.48 |
| Saudi Production -20% | $5.67 |
| Iran Sanctions Lifted | $5.20 |
| US Shale Surge | $5.33 |
| Combined Shock: Hormuz Closure + Saudi Cut | $6.91 |

## Scenario Detail

### Base Case

Current calibrated market conditions; no policy or geopolitical shock applied.

Day-180 median: **$4.16/gal** gasoline (base case), $5.50/gal diesel.

### Hormuz Closure

Strait of Hormuz effectively shut: roughly 55% of its normal throughput is assumed offline, chokepoint disruption frequency quadruples, and the war-risk shipping premium triples.

Day-180 median: **$5.30/gal** gasoline (+27.4% vs. base), $6.59/gal diesel.

### Hormuz De-Risked

Geopolitical tension around the strait fully unwinds: disruption frequency falls to a fifth of baseline and the war-risk premium halves, with no direct change to physical supply.

Day-180 median: **$4.18/gal** gasoline (+0.5% vs. base), $5.48/gal diesel.

### Saudi Production -20%

Saudi Arabia cuts output and spare capacity by 20%, e.g. an OPEC+ supply-discipline shock.

Day-180 median: **$4.34/gal** gasoline (+4.3% vs. base), $5.67/gal diesel.

### Iran Sanctions Lifted

Sanctions are lifted, letting Iranian output ramp toward a materially higher production ceiling.

Day-180 median: **$3.89/gal** gasoline (-6.5% vs. base), $5.20/gal diesel.

### US Shale Surge

US shale operators ramp drilling activity, lifting both current output and spare capacity.

Day-180 median: **$4.03/gal** gasoline (-3.1% vs. base), $5.33/gal diesel.

### Combined Shock: Hormuz Closure + Saudi Cut

A simultaneous Hormuz closure and 20% Saudi production cut - a tail-risk stack of the two largest supply-side scenarios.

Day-180 median: **$5.58/gal** gasoline (+34.1% vs. base), $6.91/gal diesel.

## Charts

![Gasoline scenario paths](scenario_gasoline_paths.png)

![Diesel scenario paths](scenario_diesel_paths.png)

![Day-180 scenario ranking](scenario_day180_ranking.png)

## Methodology

Each scenario re-runs the full 2,000-path stochastic simulation (`simulate.go`) with a modified set of inputs. Chokepoint scenarios (Hormuz closure/de-risking) adjust the model's existing disruption frequency and shipping-risk mechanics directly. Production scenarios additionally apply a first-order crude price shock: each 1% of global supply added or removed is assumed to move crude price 6% in the opposite direction (a simplifying short-run elasticity assumption, not a fitted econometric estimate), with volatility scaled up in proportion to shock size so tail scenarios carry wider, not just higher or lower, confidence bands. This is a model output for illustrative what-if analysis, not investment advice.

**Drift anchor:** the base case has no independent view on direction. Crude and both crack spreads are anchored to the CL/HO/RB forward curves, so the expected path is the market's own, and the simulation supplies the distribution around it. Scenario shocks shift that whole anchor path rather than replacing it. Futures are a risk-neutral expectation and not a forecast - in backwardation they will tend to read lower than a realized spot path - so treat the level as market-implied rather than predicted. Note also that the **median** sits below the **mean** at longer horizons because crude is lognormal: that gap is a property of the distribution, not a bearish view.

**Calibration inputs:** last calibrated on **2026-09-28** by `calibrate.py` from live NYMEX crude/gasoline/diesel futures (`yfinance`). If that date is stale, or reads "unknown" (no `date_calibrated` field), the base case below reflects old or placeholder inputs rather than today's market — re-run `python calibrate.py` before trusting the baseline.
