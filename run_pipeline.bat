@echo off
setlocal
echo Starting Daily Petroleum Forecast Pipeline...

echo [1/5] Calibrating market parameters...
python calibrate.py
if errorlevel 1 goto :fail

echo [2/5] Building and running Go simulation...
go build simulate.go
if errorlevel 1 goto :fail
simulate.exe
if errorlevel 1 goto :fail

echo [3/5] Generating final charts...
python report_gen.py
if errorlevel 1 goto :fail

echo [4/5] Generating scenario what-if report...
python scenario_report.py
if errorlevel 1 goto :fail

echo [5/5] Publishing report and charts to GitHub...
git add oil_market_outlook.md gasoline_forecast.png diesel_forecast.png scenario_gasoline_paths.png scenario_diesel_paths.png scenario_day180_ranking.png
if errorlevel 1 goto :fail
git diff --cached --quiet
if not errorlevel 1 (
    echo No report changes to publish.
) else (
    git commit -m "Daily scenario report refresh"
    if errorlevel 1 goto :fail
    git push origin main
    if errorlevel 1 goto :fail
)

echo Pipeline complete.
exit /b 0

:fail
echo Pipeline failed with exit code %errorlevel%.
exit /b %errorlevel%
