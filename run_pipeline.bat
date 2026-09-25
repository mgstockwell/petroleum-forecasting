@echo off
setlocal
echo Starting Daily Petroleum Forecast Pipeline...

echo [1/4] Calibrating market parameters...
python calibrate.py
if errorlevel 1 goto :fail

echo [2/4] Building and running Go simulation...
go build simulate.go
if errorlevel 1 goto :fail
simulate.exe
if errorlevel 1 goto :fail

echo [3/4] Generating final charts...
python report_gen.py
if errorlevel 1 goto :fail

echo [4/4] Generating scenario what-if report...
python scenario_report.py
if errorlevel 1 goto :fail

echo Pipeline complete.
exit /b 0

:fail
echo Pipeline failed with exit code %errorlevel%.
exit /b %errorlevel%
