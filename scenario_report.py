"""Generates a Bloomberg-style scenario / what-if outlook from the Go simulator.

Runs the existing Monte Carlo model (simulate.exe) once per scenario, each
scenario being the calibrated base case plus a set of parameter overrides
representing a specific geopolitical or production event. Writes three PNG
charts and a markdown report (oil_market_outlook.md).

Run after calibrate.py, e.g.:
    python calibrate.py
    python scenario_report.py
"""
import json
import os
import subprocess
from datetime import date

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

PARAMS_FILE = "params_macro.json"
SIM_BINARY = "simulate.exe"
GAS_CSV = "results_macro_gas.csv"
DIESEL_CSV = "results_macro_diesel.csv"
LEGACY_GAS_CSV = "results_gas.csv"
LEGACY_DIESEL_CSV = "results_diesel.csv"

# Short-run oil demand elasticity rule of thumb: oil demand barely responds to
# price in the short run, so each 1% of global supply added or removed is
# assumed to move crude price about 6% in the opposite direction. This is a
# simplifying assumption for illustrative "what-if" sizing, not a fitted
# elasticity - see the Methodology section of the generated report.
ELASTICITY_MULTIPLIER = 6.0

# Fixed-order categorical palette (validated for colorblind-safe adjacent
# contrast); slot order must not be re-cycled across scenarios.
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7"]

INK = "#0b0b0b"
SECONDARY_INK = "#52514e"
MUTED_INK = "#898781"
SURFACE = "#fcfcfb"
GRID = "#e1e0d9"

# Mirrors simulate.go's DefaultSims fallback, used only for the report's
# path-count caption when "sims" is absent from params_macro.json.
DEFAULT_SIMS = 2000

AAA_GAS_PRICES_URL = "https://gasprices.aaa.com/"


def fetch_aaa_prices():
    response = requests.get(AAA_GAS_PRICES_URL, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for table in soup.select("table"):
        headers = [cell.get_text(" ", strip=True) for cell in table.select("thead th")]
        if "Regular" not in headers or "Diesel" not in headers:
            continue
        for row in table.select("tbody tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.select("td")]
            if cells and cells[0] == "Current Avg.":
                return {
                    fuel: float(cells[headers.index(fuel)].replace("$", ""))
                    for fuel in ("Regular", "Diesel")
                }
    raise ValueError("AAA current national regular/diesel prices not found")


def load_base_params():
    if not os.path.exists(PARAMS_FILE):
        raise SystemExit(f"{PARAMS_FILE} not found. Run `python calibrate.py` first.")
    with open(PARAMS_FILE) as f:
        text = f.read()
    return json.loads(text), text


def build_scenarios(base):
    global_supply = (
        base["saudi_prod"] + base["russia_prod"] + base["iran_prod"]
        + base["us_prod"] + base["other_prod"]
    )

    def price_shock(supply_delta_mbpd):
        return -(supply_delta_mbpd / global_supply) * ELASTICITY_MULTIPLIER

    def shocked(supply_delta_mbpd, extra_overrides):
        shock = price_shock(supply_delta_mbpd)
        overrides = {
            "s0": base["s0"] * (1 + shock),
            "sigma_crude": base["sigma_crude"] * (1 + 0.5 * abs(shock)),
        }
        overrides.update(extra_overrides)
        return overrides, shock

    saudi_cut_delta = -0.20 * base["saudi_prod"]
    iran_lifted_delta = base["iran_prod"] * 0.7
    us_surge_delta = base["us_prod"] * 0.08
    hormuz_closure_delta = -0.55 * base["hormuz_rate"]
    worst_case_delta = hormuz_closure_delta + saudi_cut_delta

    hormuz_closure_overrides, hormuz_closure_shock = shocked(hormuz_closure_delta, {
        "chokepoint_lambda": base["chokepoint_lambda"] * 4.0,
        "shipping_cost_0": base["shipping_cost_0"] * 3.0,
    })
    saudi_cut_overrides, saudi_cut_shock = shocked(saudi_cut_delta, {
        "saudi_prod": base["saudi_prod"] * 0.8,
        "saudi_cap": base["saudi_cap"] * 0.8,
    })
    iran_lifted_overrides, iran_lifted_shock = shocked(iran_lifted_delta, {
        "iran_prod": base["iran_prod"] * 1.7,
        "iran_cap": base["iran_cap"] * 1.8,
    })
    us_surge_overrides, us_surge_shock = shocked(us_surge_delta, {
        "us_prod": base["us_prod"] * 1.08,
        "us_cap": base["us_cap"] * 1.15,
    })
    worst_case_overrides, worst_case_shock = shocked(worst_case_delta, {
        "chokepoint_lambda": base["chokepoint_lambda"] * 4.0,
        "shipping_cost_0": base["shipping_cost_0"] * 3.0,
        "saudi_prod": base["saudi_prod"] * 0.8,
        "saudi_cap": base["saudi_cap"] * 0.8,
    })

    return [
        {
            "id": "base",
            "label": "Base Case",
            "summary": "Current calibrated market conditions; no policy or geopolitical shock applied.",
            "overrides": {},
            "supply_shock_pct": 0.0,
        },
        {
            "id": "hormuz_closure",
            "label": "Hormuz Closure",
            "summary": (
                "Strait of Hormuz effectively shut: roughly 55% of its normal "
                "throughput is assumed offline, chokepoint disruption frequency "
                "quadruples, and the war-risk shipping premium triples."
            ),
            "overrides": hormuz_closure_overrides,
            "supply_shock_pct": hormuz_closure_shock,
        },
        {
            "id": "hormuz_reopened",
            "label": "Hormuz De-Risked",
            "summary": (
                "Geopolitical tension around the strait fully unwinds: disruption "
                "frequency falls to a fifth of baseline and the war-risk premium "
                "halves, with no direct change to physical supply."
            ),
            "overrides": {
                "chokepoint_lambda": base["chokepoint_lambda"] * 0.2,
                "shipping_cost_0": base["shipping_cost_0"] * 0.5,
                "sigma_crude": base["sigma_crude"] * 0.85,
            },
            "supply_shock_pct": 0.0,
        },
        {
            "id": "saudi_cut",
            "label": "Saudi Production -20%",
            "summary": (
                "Saudi Arabia cuts output and spare capacity by 20%, e.g. an "
                "OPEC+ supply-discipline shock."
            ),
            "overrides": saudi_cut_overrides,
            "supply_shock_pct": saudi_cut_shock,
        },
        {
            "id": "iran_lifted",
            "label": "Iran Sanctions Lifted",
            "summary": (
                "Sanctions are lifted, letting Iranian output ramp toward a "
                "materially higher production ceiling."
            ),
            "overrides": iran_lifted_overrides,
            "supply_shock_pct": iran_lifted_shock,
        },
        {
            "id": "us_shale_surge",
            "label": "US Shale Surge",
            "summary": (
                "US shale operators ramp drilling activity, lifting both current "
                "output and spare capacity."
            ),
            "overrides": us_surge_overrides,
            "supply_shock_pct": us_surge_shock,
        },
        {
            "id": "worst_case",
            "label": "Combined Shock: Hormuz Closure + Saudi Cut",
            "summary": (
                "A simultaneous Hormuz closure and 20% Saudi production cut - a "
                "tail-risk stack of the two largest supply-side scenarios."
            ),
            "overrides": worst_case_overrides,
            "supply_shock_pct": worst_case_shock,
        },
    ]


def ensure_simulator_built():
    if not os.path.exists(SIM_BINARY):
        print("Building simulate.exe...")
        subprocess.run(["go", "build", "-o", SIM_BINARY, "simulate.go"], check=True)


def run_scenario(params):
    with open(PARAMS_FILE, "w") as f:
        json.dump(params, f, indent=4)
    result = subprocess.run([f"./{SIM_BINARY}"], capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"simulate.exe failed:\n{result.stdout}\n{result.stderr}")
    gas = pd.read_csv(GAS_CSV, header=None).astype(float)
    diesel = pd.read_csv(DIESEL_CSV, header=None).astype(float)
    return gas, diesel


def percentile_bands(df):
    return {
        "p10": df.quantile(0.10, axis=0).to_numpy(),
        "p25": df.quantile(0.25, axis=0).to_numpy(),
        "p50": df.quantile(0.50, axis=0).to_numpy(),
        "p75": df.quantile(0.75, axis=0).to_numpy(),
        "p90": df.quantile(0.90, axis=0).to_numpy(),
    }


def plot_scenario_paths(scenarios, bands_by_id, commodity, out_file):
    days = np.arange(1, len(bands_by_id["base"]["p50"]) + 1)
    fig, ax = plt.subplots(figsize=(12, 6.5), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)

    base_bands = bands_by_id["base"]
    ax.fill_between(days, base_bands["p10"], base_bands["p90"], color=PALETTE[0],
                     alpha=0.15, linewidth=0, label="Base Case 10th-90th pct.")
    ax.fill_between(days, base_bands["p25"], base_bands["p75"], color=PALETTE[0],
                     alpha=0.28, linewidth=0, label="Base Case 25th-75th pct.")

    for i, scenario in enumerate(scenarios):
        bands = bands_by_id[scenario["id"]]
        color = PALETTE[i % len(PALETTE)]
        ax.plot(days, bands["p50"], color=color, linewidth=2, label=scenario["label"])

    ax.set_title(f"180-Day Scenario Outlook: Retail {commodity}", color=INK,
                 fontsize=14, fontweight="bold", loc="left")
    ax.set_xlabel("Days Forward", color=SECONDARY_INK)
    ax.set_ylabel("Price (USD / Gallon)", color=SECONDARY_INK)
    ax.tick_params(colors=MUTED_INK)
    ax.grid(True, color=GRID, linewidth=0.8)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=8, framealpha=0.9,
              borderaxespad=0)
    fig.savefig(out_file, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    print(f"Saved {out_file}")


def plot_day180_ranking(scenarios, summary_rows, out_file):
    labels = [row["label"] for row in summary_rows]
    values = [row["gas_day180_p50"] for row in summary_rows]
    order = np.argsort(values)
    labels = [labels[i] for i in order]
    values = [values[i] for i in order]
    colors = [PALETTE[scenarios_index(scenarios, summary_rows[i]["id"])] for i in order]

    fig, ax = plt.subplots(figsize=(10, 5.5), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    bars = ax.barh(labels, values, color=colors, height=0.55)
    base_value = next(r["gas_day180_p50"] for r in summary_rows if r["id"] == "base")
    ax.axvline(base_value, color=MUTED_INK, linewidth=1, linestyle="--")

    for bar, value in zip(bars, values):
        ax.text(bar.get_width() + 0.02, bar.get_y() + bar.get_height() / 2,
                 f"${value:.2f}", va="center", color=INK, fontsize=9)

    ax.set_title("Day-180 Median Gasoline Price by Scenario", color=INK,
                 fontsize=14, fontweight="bold", loc="left")
    ax.set_xlabel("Price (USD / Gallon)", color=SECONDARY_INK)
    ax.tick_params(colors=MUTED_INK)
    ax.grid(True, axis="x", color=GRID, linewidth=0.8)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    fig.savefig(out_file, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    print(f"Saved {out_file}")


def scenarios_index(scenarios, scenario_id):
    return next(i for i, s in enumerate(scenarios) if s["id"] == scenario_id)


def build_summary_rows(scenarios, gas_bands_by_id, diesel_bands_by_id):
    rows = []
    for scenario in scenarios:
        gb = gas_bands_by_id[scenario["id"]]
        db = diesel_bands_by_id[scenario["id"]]
        rows.append({
            "id": scenario["id"],
            "label": scenario["label"],
            "summary": scenario["summary"],
            "supply_shock_pct": scenario["supply_shock_pct"],
            "gas_day30_p50": gb["p50"][29],
            "gas_day90_p50": gb["p50"][89],
            "gas_day180_p50": gb["p50"][179],
            "gas_day180_p10": gb["p10"][179],
            "gas_day180_p90": gb["p90"][179],
            "diesel_day180_p50": db["p50"][179],
        })
    return rows


def render_report(scenarios, summary_rows, as_of, base, aaa_prices):
    sims = base.get("sims") or DEFAULT_SIMS
    calibrated_date = base.get("date_calibrated") or "unknown"
    base_row = next(r for r in summary_rows if r["id"] == "base")
    non_base = [r for r in summary_rows if r["id"] != "base"]
    most_bullish = max(non_base, key=lambda r: r["gas_day180_p50"])
    most_bearish = min(non_base, key=lambda r: r["gas_day180_p50"])

    def delta_pct(row):
        return (row["gas_day180_p50"] / base_row["gas_day180_p50"] - 1) * 100

    lines = []
    lines.append(f"# Oil & Fuels Market Outlook - Scenario Analysis")
    lines.append(f"*As of {as_of} | {sims:,}-path Monte Carlo, 180-day horizon*\n")
    lines.append(
        f"**AAA national average retail prices ({as_of}):** "
        f"Regular **${aaa_prices['Regular']:.3f}/gal**, "
        f"diesel **${aaa_prices['Diesel']:.3f}/gal** "
        f"([AAA Gas Prices]({AAA_GAS_PRICES_URL})). These are a snapshot from "
        f"the last report run, not live prices. This model "
        f"projects a *medium-term path* for the crude-to-pump price chain, not "
        f"today's station price, so some gap is expected — but if the gap looks "
        f"large, check the \"Calibration inputs\" line under Methodology first: "
        f"the model is only as current as the last `calibrate.py` run.\n"
    )

    lines.append("## Executive Summary\n")
    lines.append(
        f"Under current calibrated conditions, the model's base-case median "
        f"retail gasoline price reaches **${base_row['gas_day180_p50']:.2f}/gal** "
        f"180 days out (10th-90th percentile range "
        f"${base_row['gas_day180_p10']:.2f}-${base_row['gas_day180_p90']:.2f}). "
        f"Across the six stress scenarios modeled below, the most bullish case "
        f"is **{most_bullish['label']}**, which pushes the day-180 median to "
        f"${most_bullish['gas_day180_p50']:.2f}/gal ({delta_pct(most_bullish):+.1f}% "
        f"vs. base), while **{most_bearish['label']}** offers the most relief, at "
        f"${most_bearish['gas_day180_p50']:.2f}/gal ({delta_pct(most_bearish):+.1f}% "
        f"vs. base).\n"
    )

    lines.append("## Scenario Summary Table (Gasoline)\n")
    lines.append("| Scenario | Day 30 | Day 90 | Day 180 | Day 180 10th-90th pct. | vs. Base |")
    lines.append("|---|---|---|---|---|---|")
    for row in summary_rows:
        vs_base = "-" if row["id"] == "base" else f"{delta_pct(row):+.1f}%"
        lines.append(
            f"| {row['label']} | ${row['gas_day30_p50']:.2f} | ${row['gas_day90_p50']:.2f} "
            f"| ${row['gas_day180_p50']:.2f} | ${row['gas_day180_p10']:.2f}-${row['gas_day180_p90']:.2f} "
            f"| {vs_base} |"
        )
    lines.append("")

    lines.append("## Scenario Summary Table (Diesel, Day 180 median)\n")
    lines.append("| Scenario | Day 180 Diesel |")
    lines.append("|---|---|")
    for row in summary_rows:
        lines.append(f"| {row['label']} | ${row['diesel_day180_p50']:.2f} |")
    lines.append("")

    lines.append("## Scenario Detail\n")
    for scenario, row in zip(scenarios, summary_rows):
        vs_base = "base case" if scenario["id"] == "base" else f"{delta_pct(row):+.1f}% vs. base"
        lines.append(f"### {scenario['label']}\n")
        lines.append(f"{scenario['summary']}\n")
        lines.append(
            f"Day-180 median: **${row['gas_day180_p50']:.2f}/gal** gasoline "
            f"({vs_base}), ${row['diesel_day180_p50']:.2f}/gal diesel.\n"
        )

    lines.append("## Charts\n")
    lines.append("![Gasoline scenario paths](scenario_gasoline_paths.png)\n")
    lines.append("![Diesel scenario paths](scenario_diesel_paths.png)\n")
    lines.append("![Day-180 scenario ranking](scenario_day180_ranking.png)\n")

    lines.append("## Methodology\n")
    lines.append(
        f"Each scenario re-runs the full {sims:,}-path stochastic simulation "
        "(`simulate.go`) with a modified set of inputs. Chokepoint scenarios "
        "(Hormuz closure/de-risking) adjust the model's existing disruption "
        "frequency and shipping-risk mechanics directly. Production scenarios "
        "additionally apply a first-order crude price shock: each 1% of "
        f"global supply added or removed is assumed to move crude price "
        f"{ELASTICITY_MULTIPLIER:.0f}% in the opposite direction (a simplifying "
        "short-run elasticity assumption, not a fitted econometric estimate), "
        "with volatility scaled up in proportion to shock size so tail scenarios "
        "carry wider, not just higher or lower, confidence bands. This is a "
        "model output for illustrative what-if analysis, not investment advice.\n"
    )
    lines.append(
        f"**Calibration inputs:** last calibrated on **{calibrated_date}** by "
        "`calibrate.py` from live NYMEX crude/gasoline/diesel futures "
        "(`yfinance`). If that date is stale, or reads \"unknown\" (no "
        "`date_calibrated` field), the base case below reflects old or "
        "placeholder inputs rather than today's market — re-run "
        "`python calibrate.py` before trusting the baseline.\n"
    )

    with open("oil_market_outlook.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("Saved oil_market_outlook.md")


def main():
    ensure_simulator_built()
    base, original_text = load_base_params()
    aaa_prices = fetch_aaa_prices()
    scenarios = build_scenarios(base)

    gas_bands_by_id = {}
    diesel_bands_by_id = {}
    cached_base_csvs = {}

    for scenario in scenarios:
        print(f"Running scenario: {scenario['label']}...")
        params = {**base, **scenario["overrides"]}
        gas_df, diesel_df = run_scenario(params)
        gas_bands_by_id[scenario["id"]] = percentile_bands(gas_df)
        diesel_bands_by_id[scenario["id"]] = percentile_bands(diesel_df)
        if scenario["id"] == "base":
            with open(GAS_CSV) as f:
                cached_base_csvs[GAS_CSV] = f.read()
            with open(DIESEL_CSV) as f:
                cached_base_csvs[DIESEL_CSV] = f.read()

    # Restore params_macro.json and the standard result CSVs to the true base
    # case so the rest of the pipeline (report_gen.py, run_pipeline.bat) is
    # left in a normal, non-scenario state.
    with open(PARAMS_FILE, "w") as f:
        f.write(original_text)
    for filename in (GAS_CSV, LEGACY_GAS_CSV):
        with open(filename, "w") as f:
            f.write(cached_base_csvs[GAS_CSV])
    for filename in (DIESEL_CSV, LEGACY_DIESEL_CSV):
        with open(filename, "w") as f:
            f.write(cached_base_csvs[DIESEL_CSV])

    as_of = date.today().strftime("%Y-%m-%d")
    plot_scenario_paths(scenarios, gas_bands_by_id, "Gasoline", "scenario_gasoline_paths.png")
    plot_scenario_paths(scenarios, diesel_bands_by_id, "Diesel", "scenario_diesel_paths.png")
    summary_rows = build_summary_rows(scenarios, gas_bands_by_id, diesel_bands_by_id)
    plot_day180_ranking(scenarios, summary_rows, "scenario_day180_ranking.png")
    render_report(scenarios, summary_rows, as_of, base, aaa_prices)


if __name__ == "__main__":
    main()
