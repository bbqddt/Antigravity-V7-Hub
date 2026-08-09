@echo off
chcp 65001
cd /d "%~dp0"
start "" "%~dp0\.venv\Scripts\pythonw.exe" "%~dp0cloud_runner.py" --daemon
start "" "%~dp0\.venv\Scripts\pythonw.exe" "%~dp0commander_bot.py"
exit
