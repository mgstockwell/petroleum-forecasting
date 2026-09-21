import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def generate_chart(commodity, filename, color_base):
    print(f"Generating chart for {commodity}...")
    df = pd.read_csv(filename, header=None).astype(float)

    days = np.arange(1, df.shape[1] + 1)
    p10 = df.quantile(0.10, axis=0)
    p25 = df.quantile(0.25, axis=0)
    p50 = df.quantile(0.50, axis=0)
    p75 = df.quantile(0.75, axis=0)
    p90 = df.quantile(0.90, axis=0)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.fill_between(days, p10, p90, color=color_base, alpha=0.2, label="10th-90th Percentile (Tail Risk)")
    ax.fill_between(days, p25, p75, color=color_base, alpha=0.4, label="25th-75th Percentile (Normal Range)")
    ax.plot(days, p50, color="black", linewidth=2, label="Median Forecast")

    ax.set_title(f"180-Day Stochastic Forecast: Retail {commodity}")
    ax.set_xlabel("Days Forward")
    ax.set_ylabel("Price (USD / Gallon)")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)

    out_file = f"{commodity.lower()}_forecast.png"
    fig.savefig(out_file, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out_file}")


if __name__ == "__main__":
    generate_chart("Gasoline", "results_gas.csv", "blue")
    generate_chart("Diesel", "results_diesel.csv", "red")
