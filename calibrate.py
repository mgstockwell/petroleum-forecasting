import json
from datetime import datetime

import numpy as np
import yfinance as yf


def calibrate_daily_parameters(lookback_days=252):
    print("Fetching NYMEX data...")
    tickers = ["CL=F", "RB=F", "HO=F"]
    raw_data = yf.download(tickers, period=f"{lookback_days}d")
    price_column = "Adj Close" if "Adj Close" in raw_data else "Close"
    data = raw_data[price_column]

    returns = np.log(data / data.shift(1)).dropna()
    if returns.empty:
        raise ValueError("No return observations were available for calibration.")
    volatilities = returns.ewm(alpha=0.06).std().iloc[-1] * np.sqrt(252)

    z_scores = (returns["CL=F"] - returns["CL=F"].mean()) / returns["CL=F"].std()
    jumps = returns["CL=F"][abs(z_scores) > 2.0]

    jump_lambda = len(jumps) * 252 / len(returns)
    jump_mu = jumps.mean() if len(jumps) > 0 else 0.15

    current_prices = data.iloc[-1]
    crack_gas_current = (current_prices["RB=F"] * 42) - current_prices["CL=F"]
    crack_diesel_current = (current_prices["HO=F"] * 42) - current_prices["CL=F"]

    params = {
        "s0": float(current_prices["CL=F"]),
        "sigma_crude": float(volatilities["CL=F"]),
        "jump_lambda": float(jump_lambda),
        "jump_mu": float(jump_mu),
        "crack_gas_0": float(crack_gas_current),
        "crack_diesel_0": float(crack_diesel_current),
        "sigma_crack_gas": float(volatilities["RB=F"]),
        "sigma_crack_diesel": float(volatilities["HO=F"]),
        "date_calibrated": datetime.now().strftime("%Y-%m-%d"),
    }

    with open("params.json", "w") as f:
        json.dump(params, f, indent=4)
    print("Parameters saved to params.json")


if __name__ == "__main__":
    calibrate_daily_parameters()
