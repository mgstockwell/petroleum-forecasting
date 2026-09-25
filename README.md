# petroleum-forecasting

Production petroleum stochastic forecast pipeline. The project calibrates a
price model from recent NYMEX futures data, runs parallel Monte Carlo
simulations, and generates forecast charts for retail gasoline and diesel.

## Files

- `calibrate.py` downloads crude, gasoline, and diesel futures data with
  `yfinance`, estimates volatility and crack spread levels, and writes the
  model inputs to `params.json` and `params_macro.json`.
- `simulate.go` reads those calibrations and simulates 10,000 180-day fuel paths.
  It now includes sovereign production behavior, SPR intervention logic,
  chokepoint freight risk, and seasonal refinery margin effects.
- `report_gen.py` reads the simulation CSVs and creates percentile-band charts:
  `gasoline_forecast.png` and `diesel_forecast.png` with the date stamped in the
  title.
- `run_pipeline.bat` runs calibration, builds and runs the Go simulation, and
  generates both charts. It stops if any step fails.
- `.gitignore` excludes generated data outputs, the local virtual environment,
  and copied workspace artifacts.

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

## Model Logic: How the Variables Interact

This project is no longer a single jump-diffusion crude model. It is a coupled
system of stochastic equations that separates raw commodity pricing from the
real-world constraints that affect retail fuel costs.

### 1. Crude price component (`s0`, `sigma_crude`, `jump_lambda`, `jump_mu`)

- `s0`: the current crude price baseline.
- `sigma_crude`: the volatility of crude returns used in the stochastic price
  driver.
- `jump_lambda`: the expected frequency of large unexpected crude shocks.
- `jump_mu`: the average magnitude of those shocks.

These variables create the underlying crude oil path. In plain English, they
answer: "How expensive is crude today, how quickly can it move, and how often
should we expect surprise jumps?"

### 2. Sovereign production and supply dynamics (`saudi_prod`, `saudi_cap`,
`russia_prod`, `russia_decay`, `venezuela_cap`, `iran_cap`)

The model treats supply as a constrained system instead of a perfect infinite
supply assumption.

- `saudi_prod`: the baseline Saudi production level.
- `saudi_cap`: maximum Saudi spare capacity; Saudi Arabia acts like a balancing
  producer and can dampen price spikes when it brings more volume online.
- `russia_prod`: current Russian output baseline.
- `russia_decay`: negative drift representing aging wells, sanctions exposure,
  and infrastructure decline.
- `venezuela_cap`: an export ceiling for Venezuela.
- `iran_cap`: a cap for Iranian supply.

These variables determine how much oil is physically available to the market.
The model assumes that the main producers are not interchangeable: Saudi output
acts like a stabilizer, while Russia is assumed to decline over time and
sanctioned producers remain volume-constrained.

### 3. Seasonality and refining yields (`day_of_year`, `crack_gas_0`,
`crack_diesel_0`, `sigma_crack_gas`, `sigma_crack_diesel`)

Gasoline and diesel do not move in a vacuum; their values depend on seasonal
refining yields and blending rules.

- `day_of_year`: the current day of the year, which drives the seasonal phase.
- `crack_gas_0`: the initial gasoline crack spread baseline.
- `crack_diesel_0`: the initial diesel crack spread baseline.
- `sigma_crack_gas`: volatility of gasoline crack spread movements.
- `sigma_crack_diesel`: volatility of diesel crack spread movements.

Refining margins are not static. Summer gasoline demand and RVP blending rules
can create stronger gasoline cracks, while winter diesel and heating demand can
shift diesel cracks. In the Go model, this is represented as a sinusoidal
seasonal component layered onto the baseline crack spread.

### 4. Freight and maritime chokepoint risk (`freight_0`,
`chokepoint_lambda`, `chokepoint_jump_mu`)

The model separates shipping cost from the commodity itself because the freight
bill is driven by geopolitical risk rather than crude value alone.

- `freight_0`: the baseline tanker freight cost in dollars per barrel.
- `chokepoint_lambda`: the rate at which conflict-driven shipping disruptions are
  expected.
- `chokepoint_jump_mu`: the average extra freight cost added when shipping risk
  spikes.

A war risk premium or disruption around the Strait of Hormuz or Bab
el-Mandeb can cause a sharp jump in freight costs even if crude itself does not
move dramatically. This matters because higher freight can raise delivered retail
prices even when the crude component is stable.

### 5. SPR intervention logic (`spr_trigger_price`, `spr_floor_price`,
`spr_max_draw_mbpd`)

The Strategic Petroleum Reserve is modeled as a policy lever rather than an
abstract damping term.

- `spr_trigger_price`: the crude price threshold at which the U.S. may release
  reserves.
- `spr_floor_price`: the lower price floor below which the U.S. may restock.
- `spr_max_draw_mbpd`: the maximum release rate, in million barrels per day.

When crude prices spike above a trigger threshold, the model can simulate SPR
release and add supply back to the market. When prices fall below a floor,
restocking can become a mild drain on supply.

### 6. Interaction between variables

The model works by coupling the drivers like this:

1. Crude price is driven by stochastic volatility and jump risk.
2. Sovereign production determines physical supply availability and whether the
   market is tight or loose.
3. Freight and chokepoint risk change delivery costs and add market stress.
4. Seasonal crack spreads modify refinery margins and therefore retail fuel
   prices.
5. SPR intervention acts as a policy shock that dampens or amplifies the crude
   price path depending on the price regime.

The final pump price is not just the commodity price. It is the crude price path,
plus refining margin, plus freight, plus taxes and distribution costs:

`P_t = (S_t + C_t + F_t) / 42 + D_t + T_t`

That is why a forecast can show lower fuel prices even when local gasoline at the
pump feels expensive today: the forecast is modeling the medium-term path of the
whole chain, not just the immediate station price you see in the moment.

## Outputs

After a successful run, the repository contains:

- `params.json`: legacy market calibration inputs
- `params_macro.json`: sovereign supply, SPR, freight, crack, and seasonal inputs
- `results_gas.csv`: one simulated gasoline path per row
- `results_diesel.csv`: one simulated diesel path per row
- `results_macro_gas.csv`: macro-factor gasoline simulations
- `results_macro_diesel.csv`: macro-factor diesel simulations
- `gasoline_forecast.png`: chart for the gasoline path with the as-of date
- `diesel_forecast.png`: chart for the diesel path with the as-of date

### Diesel Forecast

![Diesel forecast prediction](diesel_forecast.png)

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
