@echo off
cd /d e:\享中
start "" ".venv\Scripts\python.exe" "cloud_runner.py" --daemon
start "" ".venv\Scripts\python.exe" "commander_bot.py"
