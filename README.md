# petroleum-forecasting

Production petroleum stochastic forecast pipeline. The project calibrates a
price model from recent NYMEX futures data, runs parallel Monte Carlo
simulations, and generates forecast charts for retail gasoline and diesel.

## Files

- `calibrate.py` downloads daily crude oil (`CL=F`), gasoline (`RB=F`), and
  heating oil (`HO=F`) futures data with `yfinance`. It estimates volatility,
  crude jump behavior, and crack spreads, then writes the current model inputs
  to `params.json`.
- `simulate.go` reads `params.json` and runs 10,000 parallel 180-day price
  paths. It writes the simulated retail prices to `results_gas.csv` and
  `results_diesel.csv`.
- `report_gen.py` reads the simulation CSVs and creates percentile-band charts:
  `gasoline_forecast.png` and `diesel_forecast.png`.
- `run_pipeline.bat` runs calibration, builds and runs the Go simulation, and
  generates both charts. It stops if any step fails.
- `root/` contains the Go workspace/module cache used by the local
  environment. It is not required as an application entry point.

## Requirements

- Windows (the included deployment script is a batch file)
- Python 3.10 or newer
- Go 1.20 or newer
- Internet access when calibration runs, so `yfinance` can fetch NYMEX data

Install the Python dependencies in a virtual environment:

```powershell
py -3 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
python -m pip install numpy pandas matplotlib yfinance
```

If PowerShell blocks activation, run the commands from Command Prompt instead:

```bat
py -3 -m venv .venv
.venv\\Scripts\\activate.bat
python -m pip install --upgrade pip
python -m pip install numpy pandas matplotlib yfinance
```

## Run Locally

Run the batch file from the repository directory so all input and output files
are resolved in the expected location:

```bat
run_pipeline.bat
```

Or run the stages individually:

```bat
python calibrate.py
go build simulate.go
simulate.exe
python report_gen.py
```

The default model uses 252 days of calibration data, a 180-day forecast
horizon, and 10,000 simulation paths. Calibration must run before simulation
because `simulate.go` requires the generated `params.json` file.

## Understanding the Crack Spread

A crack spread is the difference between the price of crude oil and the value
of the refined products produced from it, mainly gasoline and diesel. In
practical terms, it measures refinery margin: a refinery buys crude, refines it,
then sells gasoline and diesel to the market. If the refined product prices do
not rise enough to offset crude costs and processing costs, refinery margins
compress and the crack spread narrows.

The model in this project captures that relationship by calibrating:

- crude price volatility,
- jump risk (sudden large price moves),
- the current gasoline crack spread,
- the current diesel crack spread,
- and the volatility of each spread.

That matters because a forecast can say fuel prices are likely to decline even
when consumers are seeing high prices today. This is not a contradiction. The
model is forecasting the likely path of future prices and spreads over the next
180 days, not making a prediction that current retail pain disappears
immediately. A short-term market environment may still feel expensive because of
near-term supply shocks, demand seasonality, or local station pricing, while the
medium-term model can still show the most likely path leaning lower.

In other words, the model is not saying "no one is right." It is saying that,
under the current assumptions, the combined crude + refining margin + product
spread relationship points to a likely softer medium-term path for retail fuel
prices, with a still-present risk of sharp upside shocks.

## Outputs

After a successful run, the repository contains:

- `params.json`: calibrated inputs and the calibration date
- `results_gas.csv`: one simulated gasoline path per row
- `results_diesel.csv`: one simulated diesel path per row
- `gasoline_forecast.png`: 10th-90th, 25th-75th, and median gasoline forecast
- `diesel_forecast.png`: 10th-90th, 25th-75th, and median diesel forecast

These generated files are ignored by Git. Keep them locally or publish them to
the reporting location used by your operations process.

## Deployment

1. Install Python, Go, and the Python dependencies on the target Windows
   machine.
2. Copy or clone this repository to a stable folder, such as
   `C:\\Apps\\petroleum-forecasting`.
3. Open a terminal in that folder, activate the virtual environment, and run
   `run_pipeline.bat` once to verify network access and permissions.
4. To run it automatically, create a Windows Task Scheduler task with:
   - **Program:** the full path to `run_pipeline.bat`
   - **Start in:** the repository folder
   - **Trigger:** the desired daily schedule, preferably after the market data
     is available
   - **Settings:** enable running whether or not a user is logged on, and save
     the task output or configure a failure notification

The task account must have write access to the repository folder. Because the
batch file calls `python` and `go`, those commands must be on that account's
`PATH`; alternatively, update the batch file to use absolute paths to the
virtual-environment Python executable and the Go installation.

This repository does not currently expose an HTTP service or container image.
For server deployment, use the same scheduled batch workflow on a Windows
worker, or add a service wrapper that invokes `run_pipeline.bat` and publishes
the generated PNG and CSV files.

## Troubleshooting

- **`No return observations were available for calibration.`** Check the
  internet connection and confirm Yahoo Finance returned data for the three
  futures tickers.
- **`failed to open params.json`** Run `python calibrate.py` from the project
  directory before starting the simulation.
- **Missing Python module** Activate `.venv` and install the dependencies
  listed above.
- **Task Scheduler cannot find files** Set the task's **Start in** directory to
  the repository folder; relative paths are used throughout the pipeline.
