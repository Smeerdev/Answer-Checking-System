@echo off
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    py -m venv venv
)
echo Installing dependencies...
venv\Scripts\pip.exe install -r requirements.txt -q
echo Starting app...
venv\Scripts\python.exe app.py
