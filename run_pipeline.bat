@echo off
setlocal
echo Starting Daily Petroleum Forecast Pipeline...

echo [1/3] Calibrating market parameters...
python calibrate.py
if errorlevel 1 goto :fail

echo [2/3] Building and running Go simulation...
go build simulate.go
if errorlevel 1 goto :fail
simulate.exe
if errorlevel 1 goto :fail

echo [3/3] Generating final charts...
python report_gen.py
if errorlevel 1 goto :fail

echo Pipeline complete.
pause
exit /b 0

:fail
echo Pipeline failed with exit code %errorlevel%.
exit /b %errorlevel%
