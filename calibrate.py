"""Calibrates the stochastic fuel-price model from live NYMEX data.

Three groups of inputs are produced:

1.  **Spot state** - today's crude price and crack spreads, plus a
    jump-filtered crude diffusion volatility.
2.  **Market-implied anchor paths** - the CL/HO/RB forward curves, converted
    into the deterministic path the market itself expects crude and the two
    crack spreads to follow over the forecast horizon. This is what gives the
    model a drift; without it the simulation has no view on direction at all.
3.  **Structural dynamics** - jump frequency/size, crack mean-reversion speed,
    crack volatility in dollar terms, and crack seasonality, all estimated
    from a long history because they are slow-moving properties of the market
    rather than today's state.
"""
import json
import os
from datetime import date, datetime

import numpy as np
import pandas as pd
import yfinance as yf

# Recent window used for the responsive spot volatility estimate.
SHORT_LOOKBACK_DAYS = 252
# Long window used for structural estimates (jumps, crack reversion,
# seasonality). These are properties of the market, not of today, so they want
# a stable multi-cycle sample rather than a responsive one.
LONG_LOOKBACK = "10y"
# Robust jump threshold, in MAD-scaled standard deviations of daily log
# returns. 4.0 isolates genuine shocks without absorbing ordinary vol.
JUMP_THRESHOLD_MADS = 4.0
# Number of consecutive contract months to probe for each forward curve.
CURVE_MONTHS = 10
# Futures month codes (NYMEX convention).
MONTH_CODES = {1: "F", 2: "G", 3: "H", 4: "J", 5: "K", 6: "M",
               7: "N", 8: "Q", 9: "U", 10: "V", 11: "X", 12: "Z"}
# Contracts closer than this to their delivery month are skipped: they are in
# or near expiry and their settlements get noisy/illiquid.
MIN_CURVE_DAYS = 5
TRADING_DAYS = 252.0

# Calm-condition defaults for the chokepoint/freight mechanics. These are
# structural properties of the model, not live-calibrated from data, and
# represent "no disruption happening right now".
CHOKEPOINT_CALM_FLOOR = {
    "freight_0": 2.50,
    "chokepoint_lambda": 1.5,
    "chokepoint_jump_mu": 5.0,
    # Disruption half-life of ~21 days, so a chokepoint event restricts
    # supply for weeks rather than for a single simulation step.
    "chokepoint_decay": 12.0,
    "hormuz_rate": 20.0,
    "bab_rate": 9.0,
    "shipping_cost_0": 0.15,
}
# Values these fields would take at disruption_severity=1.0 (equivalent to
# scenario_report.py's "Hormuz Closure" scenario). Only fields with a
# meaningful full-closure target are listed; the rest of
# CHOKEPOINT_CALM_FLOOR is left unblended.
CHOKEPOINT_FULL_CLOSURE_TARGETS = {
    "freight_0": CHOKEPOINT_CALM_FLOOR["freight_0"] * 3.0,
    "chokepoint_lambda": CHOKEPOINT_CALM_FLOOR["chokepoint_lambda"] * 4.0,
    "shipping_cost_0": CHOKEPOINT_CALM_FLOOR["shipping_cost_0"] * 3.0,
}
DISRUPTION_SEVERITY_FILE = "disruption_severity.json"


def load_disruption_severity():
    """Reads the manually-maintained current-conditions severity dial.

    Not pulled live - update disruption_severity.json by hand as conditions
    evolve, citing the source/date that justifies the value. Defaults to 0.0
    (today's calm-floor behavior) if the file is absent, so the pipeline
    still runs for anyone who hasn't set it up.
    """
    if not os.path.exists(DISRUPTION_SEVERITY_FILE):
        return {"severity": 0.0, "as_of": None, "source": None, "notes": None}
    with open(DISRUPTION_SEVERITY_FILE) as f:
        return json.load(f)


def blend_chokepoint_params(severity):
    """Linearly blends the calm-floor chokepoint params toward their
    full-closure equivalents by `severity` (0=calm, 1=full Hormuz Closure
    scenario severity), leaving unlisted fields at their calm-floor value.
    """
    severity = max(0.0, min(1.0, severity))
    blended = dict(CHOKEPOINT_CALM_FLOOR)
    for field, target in CHOKEPOINT_FULL_CLOSURE_TARGETS.items():
        calm = CHOKEPOINT_CALM_FLOOR[field]
        blended[field] = calm + severity * (target - calm)
    return blended


def _get_price_frame(raw_data):
    if isinstance(raw_data.columns, pd.MultiIndex):
        available_fields = raw_data.columns.get_level_values(0)
        price_column = "Adj Close" if "Adj Close" in available_fields else "Close"
        return raw_data.xs(price_column, axis=1, level=0)

    price_column = "Adj Close" if "Adj Close" in raw_data.columns else "Close"
    return raw_data[price_column]


def _clean_prices(frame):
    """Drops rows with missing or non-positive prices.

    April 2020 put WTI settlements below zero, which makes log returns
    undefined; those rows have to go before anything is estimated.
    """
    frame = frame.dropna()
    return frame[(frame > 0).all(axis=1)]


def fetch_history(period):
    raw = yf.download(["CL=F", "RB=F", "HO=F"], period=period,
                      progress=False, auto_adjust=False)
    if raw.empty:
        raise ValueError(f"No market data was returned for period {period}.")
    data = _clean_prices(_get_price_frame(raw))
    if data.empty:
        raise ValueError(f"No usable price rows for period {period}.")
    return data


def crack_spreads(prices):
    """Crack spreads in $/bbl. RB and HO quote in $/gal, so scale by 42."""
    return (
        (prices["RB=F"] * 42.0) - prices["CL=F"],
        (prices["HO=F"] * 42.0) - prices["CL=F"],
    )


def contract_symbols(root, today, months=CURVE_MONTHS):
    """Builds NYMEX contract tickers for the next `months` delivery months."""
    symbols = {}
    for offset in range(months):
        month_index = today.month - 1 + offset
        year = today.year + month_index // 12
        month = month_index % 12 + 1
        days_out = (date(year, month, 1) - today).days
        if days_out < MIN_CURVE_DAYS:
            continue
        symbols[f"{root}{MONTH_CODES[month]}{year % 100:02d}.NYM"] = days_out
    return symbols


def fetch_forward_curves(today):
    """Pulls the CL/HO/RB forward curves and returns the last settlement of
    each live contract, keyed by days from today to its delivery month.

    The delivery-month start date is used as the maturity proxy rather than the
    exact expiry, which is close enough for a 180-day anchor and avoids
    hard-coding an expiry calendar. Returns None if the curve cannot be built,
    so the caller can fall back to the mean-reversion model.
    """
    roots = ["CL", "HO", "RB"]
    wanted = {root: contract_symbols(root, today) for root in roots}
    all_symbols = [s for mapping in wanted.values() for s in mapping]
    raw = yf.download(all_symbols, period="10d", progress=False, auto_adjust=False)
    if raw.empty:
        return None
    prices = _get_price_frame(raw)
    if isinstance(prices, pd.Series):
        prices = prices.to_frame(all_symbols[0])

    settles = {}
    for symbol in prices.columns:
        series = prices[symbol].dropna()
        if not series.empty and series.iloc[-1] > 0:
            settles[symbol] = float(series.iloc[-1])

    curves = {}
    for root in roots:
        points = sorted(
            (days, settles[symbol])
            for symbol, days in wanted[root].items() if symbol in settles
        )
        if len(points) < 2:
            return None
        curves[root] = points

    # Keep only maturities quoted by all three products, so the implied crack
    # curves are computed from contemporaneous, same-maturity settlements.
    crude = dict(curves["CL"])
    diesel = dict(curves["HO"])
    gas = dict(curves["RB"])
    shared = sorted(set(crude) & set(diesel) & set(gas))
    if len(shared) < 2:
        return None

    return {
        "curve_crude": [[d, round(crude[d], 4)] for d in shared],
        "curve_crack_diesel": [[d, round(diesel[d] * 42.0 - crude[d], 4)] for d in shared],
        "curve_crack_gas": [[d, round(gas[d] * 42.0 - crude[d], 4)] for d in shared],
    }


def estimate_jumps(log_returns):
    """Splits crude log returns into a diffusion part and a jump part.

    Uses a MAD-based robust threshold so the estimate of "normal" volatility is
    not itself inflated by the shocks it is trying to detect. Returns the jump
    intensity (per year), mean jump size, jump dispersion, and the mask of
    non-jump observations.
    """
    centre = np.median(log_returns)
    mad_sigma = np.median(np.abs(log_returns - centre)) * 1.4826
    if mad_sigma <= 0:
        return 0.0, 0.0, 0.0, np.ones_like(log_returns, dtype=bool)

    is_jump = np.abs(log_returns - centre) > JUMP_THRESHOLD_MADS * mad_sigma
    years = len(log_returns) / TRADING_DAYS
    if not is_jump.any() or years <= 0:
        return 0.0, 0.0, 0.0, ~is_jump

    jumps = log_returns[is_jump]
    return (
        float(is_jump.sum() / years),
        float(jumps.mean()),
        float(jumps.std()),
        ~is_jump,
    )


def estimate_crack_dynamics(crack):
    """Fits an Ornstein-Uhlenbeck reversion plus an annual seasonal cycle.

    The reversion parameters come from an OLS fit of the daily change on the
    level; the seasonal amplitude and phase come from a sin/cos regression on
    the deviation from a centred one-year rolling mean, which strips out the
    slow level drift so only the within-year cycle is left.
    """
    values = crack.to_numpy()
    level, change = values[:-1], np.diff(values)
    design = np.vstack([np.ones_like(level), level]).T
    intercept, slope = np.linalg.lstsq(design, change, rcond=None)[0]

    if slope < 0:
        kappa = float(-slope * TRADING_DAYS)
        theta = float(-intercept / slope)
    else:  # no reversion detectable in-sample; fall back to the sample mean
        kappa, theta = 0.0, float(values.mean())

    sigma_bbl = float(change.std() * np.sqrt(TRADING_DAYS))

    seasonal = (crack - crack.rolling(365, center=True, min_periods=200).mean()).dropna()
    amplitude, phase = 0.0, 0.0
    if len(seasonal) > 365:
        omega = 2.0 * np.pi / 365.25
        day = seasonal.index.dayofyear.to_numpy().astype(float)
        design = np.vstack([np.ones_like(day), np.sin(omega * day), np.cos(omega * day)]).T
        _, sin_c, cos_c = np.linalg.lstsq(design, seasonal.to_numpy(), rcond=None)[0]
        amplitude = float(np.hypot(sin_c, cos_c))
        phase = float(np.arctan2(cos_c, sin_c))

    return {
        "kappa": round(kappa, 4),
        "theta": round(theta, 4),
        "sigma_bbl": round(sigma_bbl, 4),
        "seasonal_amp": round(amplitude, 4),
        "seasonal_phase": round(phase, 4),
    }


def calibrate_daily_parameters(lookback_days=SHORT_LOOKBACK_DAYS):
    print("Fetching NYMEX spot and history...")
    recent = fetch_history(f"{lookback_days}d")
    history = fetch_history(LONG_LOOKBACK)

    current_prices = recent.iloc[-1]
    crack_gas, crack_diesel = crack_spreads(recent)

    crude_log_returns = np.diff(np.log(history["CL=F"].to_numpy()))
    jump_lambda, jump_mu, jump_sigma, diffusion_mask = estimate_jumps(crude_log_returns)

    # Responsive diffusion vol from the recent window, with jump days removed
    # so the jump component is not counted twice in the simulation.
    recent_returns = np.log(recent["CL=F"] / recent["CL=F"].shift(1)).dropna()
    recent_centre = np.median(recent_returns)
    recent_mad = np.median(np.abs(recent_returns - recent_centre)) * 1.4826
    recent_diffusion = recent_returns[
        np.abs(recent_returns - recent_centre) <= JUMP_THRESHOLD_MADS * recent_mad
    ] if recent_mad > 0 else recent_returns
    sigma_crude = float(recent_diffusion.ewm(alpha=0.06).std().iloc[-1] * np.sqrt(TRADING_DAYS))

    history_gas_crack, history_diesel_crack = crack_spreads(history)
    gas_dynamics = estimate_crack_dynamics(history_gas_crack)
    diesel_dynamics = estimate_crack_dynamics(history_diesel_crack)

    print("Fetching forward curves...")
    today = date.today()
    curves = fetch_forward_curves(today)
    if curves is None:
        print("  WARNING: forward curves unavailable - the simulation will fall "
              "back to mean-reversion drift, which is a weaker anchor.")
        curves = {"curve_crude": [], "curve_crack_gas": [], "curve_crack_diesel": []}
    else:
        span = curves["curve_crude"][-1][0]
        print(f"  Built {len(curves['curve_crude'])}-point curves out to day {span}.")

    severity_info = load_disruption_severity()
    chokepoint_params = blend_chokepoint_params(severity_info["severity"])
    if severity_info["severity"] > 0:
        print(f"  Disruption severity {severity_info['severity']:.2f} "
              f"(as of {severity_info['as_of']}): {severity_info['source']}")

    sovereign_state = {
        "saudi_prod": 9.0,
        "saudi_cap": 12.0,
        "saudi_floor": 7.0,
        "saudi_response": 0.05,
        "russia_prod": 8.95,
        "russia_decay": 0.02,
        "venezuela_cap": 1.15,
        "iran_cap": 3.4,
        "iran_prod": 3.3,
        "iran_floor": 2.5,
        "iran_drift_rate": 0.0,
        "us_prod": 13.2,
        "us_cap": 13.8,
        "us_floor": 11.0,
        "us_response": 0.06,
        "other_prod": 67.25,
        "other_cap": 69.0,
        "other_response": 0.02,
    }

    params = {
        "s0": float(current_prices["CL=F"]),
        "sigma_crude": sigma_crude,
        "jump_lambda": round(jump_lambda, 4),
        "jump_mu": round(jump_mu, 6),
        "jump_sigma": round(jump_sigma, 6),
        "crack_gas_0": float(crack_gas.iloc[-1]),
        "crack_diesel_0": float(crack_diesel.iloc[-1]),
        "crack_gas_kappa": gas_dynamics["kappa"],
        "crack_gas_theta": gas_dynamics["theta"],
        "crack_diesel_kappa": diesel_dynamics["kappa"],
        "crack_diesel_theta": diesel_dynamics["theta"],
        # Crack volatility in $/bbl per year. The older sigma_crack_* fields
        # were log-return vols of the *product* futures and were never in the
        # right units to drive a spread, which is why they went unused.
        "sigma_crack_gas_bbl": gas_dynamics["sigma_bbl"],
        "sigma_crack_diesel_bbl": diesel_dynamics["sigma_bbl"],
        "crack_gas_seasonal_amp": gas_dynamics["seasonal_amp"],
        "crack_gas_seasonal_phase": gas_dynamics["seasonal_phase"],
        "crack_diesel_seasonal_amp": diesel_dynamics["seasonal_amp"],
        "crack_diesel_seasonal_phase": diesel_dynamics["seasonal_phase"],
        "day_of_year": int(datetime.now().timetuple().tm_yday),
        # 1.0 follows the forward curve in full; lower it to discount the
        # curve's drift (futures are a risk-neutral expectation, not a
        # real-world forecast - see the README).
        "curve_drift_weight": 1.0,
        # Freight/chokepoint fields are blended from CHOKEPOINT_CALM_FLOOR
        # toward CHOKEPOINT_FULL_CLOSURE_TARGETS by disruption_severity.json's
        # severity dial - see load_disruption_severity/blend_chokepoint_params.
        **chokepoint_params,
        "sims": 2000,
        # SPR thresholds are relative to the market-implied forward price, not
        # absolute dollars: "unusually expensive crude" is only meaningful
        # against what the market already expects.
        "spr_trigger_ratio": 1.25,
        "spr_floor_ratio": 0.75,
        "spr_max_draw_mbpd": 1.0,
        # Manual estimates of the actual SPR level/capacity (million barrels) -
        # not pulled live, update periodically from EIA/DOE reporting.
        "spr_level_mbbl": 405.0,
        "spr_capacity_mbbl": 714.0,
        "date_calibrated": today.strftime("%Y-%m-%d"),
        **sovereign_state,
        **curves,
    }

    with open("params_macro.json", "w") as f:
        json.dump(params, f, indent=4)

    with open("params.json", "w") as f:
        json.dump({key: params[key] for key in (
            "s0", "sigma_crude", "jump_lambda", "jump_mu", "jump_sigma",
            "crack_gas_0", "crack_diesel_0", "date_calibrated",
        )}, f, indent=4)

    print(f"Crude ${params['s0']:.2f}, sigma {sigma_crude:.3f}, "
          f"jumps {jump_lambda:.2f}/yr at {jump_mu:+.2%}")
    print(f"Cracks: gas ${params['crack_gas_0']:.2f}/bbl, "
          f"diesel ${params['crack_diesel_0']:.2f}/bbl")
    print("Macro parameters saved to params_macro.json")
    print("Legacy parameters saved to params.json")


if __name__ == "__main__":
    calibrate_daily_parameters()
