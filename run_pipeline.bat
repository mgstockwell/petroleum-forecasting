@echo off
echo Starting Daily Petroleum Forecast Pipeline...

echo [1/3] Calibrating market parameters...
python calibrate.py

echo [2/3] Building and running Go simulation...
go build simulate.go
simulate.exe

echo [3/3] Generating final charts...
python report_gen.py

echo Pipeline complete.
pause
