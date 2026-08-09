@echo off
cd /d "%~dp0"
start "" ".venv\Scripts\python.exe" "cloud_runner.py" --daemon
start "" ".venv\Scripts\python.exe" "commander_bot.py"
