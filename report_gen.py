import json
import os
from datetime import date

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf

from calibrate import _get_price_frame
import scenario_report as sr

PARAMS_FILE = "params_macro.json"
ANCHOR_FILE = "anchor_path.csv"
BACKTEST_DAYS = 180

# Mirrors simulate.go's tax/distribution constants - keep in sync if those change.
TAX_GAS = 0.57
DIST_GAS = 0.65
TAX_DIESEL = 0.65
DIST_DIESEL = 0.85

# Stress scenarios overlaid on the forecast charts as single plausible paths
# (see scenario_report.build_scenarios for the full set/ids). Colors are
# chosen to stay distinct in hue from both charts' percentile-band colors
# (blue/red) and from each other, rather than reused from scenario_report's
# PALETTE, which clusters several scenarios in the same orange/red family.
OVERLAY_SCENARIO_STYLES = {
    "hormuz_closure": {"color": "#9400d3", "linestyle": "--"},
    "saudi_cut": {"color": "#009e73", "linestyle": "-."},
}


def load_freight_assumptions():
    if not os.path.exists(PARAMS_FILE):
        return None
    with open(PARAMS_FILE) as f:
        params = json.load(f)
    return params.get("freight_0", 0.0), params.get("shipping_cost_0", 0.0)


def load_anchor():
    """Reads the deterministic anchor path the simulator was built around.

    Returns None when absent so the chart still renders from an older run's
    CSVs without it.
    """
    if not os.path.exists(ANCHOR_FILE):
        return None
    anchor = pd.read_csv(ANCHOR_FILE)
    return {
        "Gasoline": anchor["gas_retail"].to_numpy(),
        "Diesel": anchor["diesel_retail"].to_numpy(),
    }


def fetch_historical_implied_retail(days=BACKTEST_DAYS):
    """Reconstructs an approximate historical retail price from RBOB gasoline
    and heating-oil futures closes (which already price in crude + crack
    spread), holding today's freight/shipping assumptions constant since no
    historical freight series is available. Returns None on any failure -
    missing params, no internet, empty data - so the forecast chart can still
    render without the backtest overlay.

    Prices are pulled unadjusted (auto_adjust=False) to match calibrate.py.
    Back-adjusted futures settlements are shifted by the roll history, which
    would leave the overlay's last point offset from the forecast's first.
    """
    freight_shipping = load_freight_assumptions()
    if freight_shipping is None:
        print("Skipping historical backtest overlay: params_macro.json not found.")
        return None
    freight_0, shipping_cost_0 = freight_shipping
    try:
        raw = yf.download(["RB=F", "HO=F"], period=f"{days + 30}d", progress=False,
                          auto_adjust=False)
        if raw.empty:
            raise ValueError("no market data returned")
        data = _get_price_frame(raw).dropna()
        if data.empty:
            raise ValueError("no usable rows after cleaning")
        full_range = pd.date_range(end=data.index.max(), periods=days, freq="D")
        data = data.reindex(data.index.union(full_range)).sort_index().ffill().reindex(full_range)
        if data.isna().any().any():
            raise ValueError("insufficient history to cover the requested backtest window")
        freight_gal = freight_0 / 42.0
        shipping_gal = shipping_cost_0 / 42.0
        gas = (data["RB=F"] + freight_gal + shipping_gal + TAX_GAS + DIST_GAS).to_numpy()
        diesel = (data["HO=F"] + freight_gal + shipping_gal + TAX_DIESEL + DIST_DIESEL).to_numpy()
        return gas, diesel
    except Exception as exc:
        print(f"Skipping historical backtest overlay ({exc}).")
        return None


def pick_representative_path(df):
    """Picks one simulated path - not an average across paths - that best
    represents the scenario: the single trajectory closest (least-squares) to
    the cross-sectional median at every day. This keeps the real day-to-day
    jumps/vol of an actual simulated path intact, unlike the percentile bands
    or mean/median lines, which are aggregates across all paths.
    """
    median = df.median(axis=0)
    deviations = ((df - median) ** 2).sum(axis=1)
    return df.loc[deviations.idxmin()].to_numpy()


def build_overlay_scenario_paths():
    """Runs the Hormuz Closure and Saudi Production -20% stress scenarios
    once each and returns one plausible single-path trajectory per commodity
    per scenario, for overlaying on the forecast charts.

    Temporarily overwrites params_macro.json and the simulator's result/anchor
    CSVs (scenario_report.run_scenario's only interface), then restores
    whatever was on disk before this ran, so the rest of the pipeline still
    sees base-case output.
    """
    if not os.path.exists(sr.PARAMS_FILE):
        return {}, {}

    sr.ensure_simulator_built()
    base, original_params_text = sr.load_base_params()
    scenarios = {s["id"]: s for s in sr.build_scenarios(base)}

    cached_csvs = {}
    for source, targets in (
        (sr.GAS_CSV, (sr.GAS_CSV, sr.LEGACY_GAS_CSV)),
        (sr.DIESEL_CSV, (sr.DIESEL_CSV, sr.LEGACY_DIESEL_CSV)),
        (sr.ANCHOR_CSV, (sr.ANCHOR_CSV,)),
    ):
        if os.path.exists(source):
            with open(source) as f:
                cached_csvs[source] = (f.read(), targets)

    gas_paths, diesel_paths = {}, {}
    try:
        for scenario_id, style in OVERLAY_SCENARIO_STYLES.items():
            scenario = scenarios[scenario_id]
            print(f"Running overlay scenario: {scenario['label']}...")
            params = {**base, **scenario["overrides"]}
            # Scenario shocks ramp in via shock_pct/shock_ramp_days rather than
            # overriding s0, so this path starts where the chart's history,
            # anchor, and mean lines do and diverges from there.
            gas_df, diesel_df = sr.run_scenario(params)
            label = f"{scenario['label']} (plausible single path)"
            style_kwargs = (style["color"], style["linestyle"])
            gas_paths[label] = (pick_representative_path(gas_df), *style_kwargs)
            diesel_paths[label] = (pick_representative_path(diesel_df), *style_kwargs)
    finally:
        with open(sr.PARAMS_FILE, "w") as f:
            f.write(original_params_text)
        for content, targets in cached_csvs.values():
            for filename in targets:
                with open(filename, "w") as f:
                    f.write(content)

    return gas_paths, diesel_paths


def generate_chart(commodity, filename, color_base, historical, anchor, scenario_paths=None):
    print(f"Generating chart for {commodity}...")
    as_of = date.today().strftime("%Y-%m-%d")
    df = pd.read_csv(filename, header=None).astype(float)

    forward_days = np.arange(1, df.shape[1] + 1)
    p10 = df.quantile(0.10, axis=0)
    p25 = df.quantile(0.25, axis=0)
    p50 = df.quantile(0.50, axis=0)
    p75 = df.quantile(0.75, axis=0)
    p90 = df.quantile(0.90, axis=0)
    mean = df.mean(axis=0)

    fig, ax = plt.subplots(figsize=(12, 6.5))

    if historical is not None:
        hist_days = np.arange(-len(historical), 0)
        ax.plot(hist_days, historical, color="dimgray", linewidth=1.5,
                label=f"Historical implied retail (~{len(historical)}d, approx.)")
        ax.axvline(0, color="dimgray", linewidth=1, linestyle="--")

    ax.fill_between(forward_days, p10, p90, color=color_base, alpha=0.2,
                    label="10th-90th Percentile (Tail Risk)")
    ax.fill_between(forward_days, p25, p75, color=color_base, alpha=0.4,
                    label="25th-75th Percentile (Normal Range)")

    if anchor is not None:
        ax.plot(forward_days, anchor[:len(forward_days)], color="#1a6fb5", linewidth=2,
                linestyle=(0, (5, 2)), label="Market-implied anchor (forward curve)")

    for label, (path, color, linestyle) in (scenario_paths or {}).items():
        ax.plot(forward_days, path[:len(forward_days)], color=color, linewidth=1.5,
                alpha=0.9, linestyle=linestyle, label=label)

    # The mean tracks the curve anchor; the median sits below it because crude
    # is lognormal, so high volatility drags the median down even with no
    # bearish view. Both are shown so that gap is visible rather than implied.
    ax.plot(forward_days, mean, color="black", linewidth=2, label="Mean Forecast")
    ax.plot(forward_days, p50, color="black", linewidth=1.5, linestyle=":",
            label="Median Forecast")

    if historical is not None:
        title = f"{BACKTEST_DAYS}-Day Backtest + 180-Day Forecast: Retail {commodity}"
        xlabel = "Days (negative = historical, positive = forecast)"
    else:
        title = f"180-Day Stochastic Forecast: Retail {commodity}"
        xlabel = "Days Forward"
    ax.set_title(f"{title}\nAs of {as_of}")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Price (USD / Gallon)")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)

    out_file = f"{commodity.lower()}_forecast.png"
    fig.savefig(out_file, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out_file}")


if __name__ == "__main__":
    gas_file = "results_macro_gas.csv" if os.path.exists("results_macro_gas.csv") else "results_gas.csv"
    diesel_file = "results_macro_diesel.csv" if os.path.exists("results_macro_diesel.csv") else "results_diesel.csv"
    historical = fetch_historical_implied_retail()
    hist_gas, hist_diesel = historical if historical is not None else (None, None)
    anchors = load_anchor() or {}
    gas_scenario_paths, diesel_scenario_paths = build_overlay_scenario_paths()
    generate_chart("Gasoline", gas_file, "blue", hist_gas, anchors.get("Gasoline"), gas_scenario_paths)
    generate_chart("Diesel", diesel_file, "red", hist_diesel, anchors.get("Diesel"), diesel_scenario_paths)
