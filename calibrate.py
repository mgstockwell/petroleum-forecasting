import json
from datetime import datetime

import numpy as np
import pandas as pd
import yfinance as yf


def _get_price_frame(raw_data):
    if isinstance(raw_data.columns, pd.MultiIndex):
        available_fields = raw_data.columns.get_level_values(0)
        price_column = "Adj Close" if "Adj Close" in available_fields else "Close"
        return raw_data.xs(price_column, axis=1, level=0)

    price_column = "Adj Close" if "Adj Close" in raw_data.columns else "Close"
    return raw_data[price_column]


def calibrate_daily_parameters(lookback_days=252):
    print("Fetching NYMEX data...")
    tickers = ["CL=F", "RB=F", "HO=F"]
    raw_data = yf.download(tickers, period=f"{lookback_days}d")
    if raw_data.empty:
        raise ValueError("No market data was returned for calibration.")

    data = _get_price_frame(raw_data)
    returns = np.log(data / data.shift(1)).dropna()
    if returns.empty:
        raise ValueError("No return observations were available for calibration.")

    volatilities = returns.ewm(alpha=0.06).std().iloc[-1] * np.sqrt(252)

    current_prices = data.iloc[-1]
    crack_gas = (current_prices["RB=F"] * 42.0) - current_prices["CL=F"]
    crack_diesel = (current_prices["HO=F"] * 42.0) - current_prices["CL=F"]

    sovereign_state = {
        "saudi_prod": 9.0,
        "saudi_cap": 12.0,
        "russia_prod": 8.95,
        "russia_decay": 0.02,
        "venezuela_cap": 1.15,
        "iran_cap": 3.4,
    }

    base_freight_bbl = 2.50

    params = {
        "s0": float(current_prices["CL=F"]),
        "sigma_crude": float(volatilities["CL=F"]),
        "jump_lambda": float(0.0),
        "jump_mu": float(0.15),
        "crack_gas_0": float(crack_gas),
        "crack_diesel_0": float(crack_diesel),
        "sigma_crack_gas": float(volatilities["RB=F"]),
        "sigma_crack_diesel": float(volatilities["HO=F"]),
        "day_of_year": int(datetime.now().timetuple().tm_yday),
        "freight_0": float(base_freight_bbl),
        "chokepoint_lambda": 1.5,
        "chokepoint_jump_mu": 5.0,
        "spr_trigger_price": 95.00,
        "spr_floor_price": 70.00,
        "spr_max_draw_mbpd": 1.0,
        "date_calibrated": datetime.now().strftime("%Y-%m-%d"),
        **sovereign_state,
    }

    with open("params_macro.json", "w") as f:
        json.dump(params, f, indent=4)

    with open("params.json", "w") as f:
        json.dump({
            "s0": params["s0"],
            "sigma_crude": params["sigma_crude"],
            "jump_lambda": params["jump_lambda"],
            "jump_mu": params["jump_mu"],
            "crack_gas_0": params["crack_gas_0"],
            "crack_diesel_0": params["crack_diesel_0"],
            "sigma_crack_gas": params["sigma_crack_gas"],
            "sigma_crack_diesel": params["sigma_crack_diesel"],
            "date_calibrated": params["date_calibrated"],
        }, f, indent=4)

    print("Macro parameters saved to params_macro.json")
    print("Legacy parameters saved to params.json")


if __name__ == "__main__":
    calibrate_daily_parameters()
