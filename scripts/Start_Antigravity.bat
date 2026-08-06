@echo off
chcp 65001
cd /d e:\享中
start "" "e:\享中\.venv\Scripts\pythonw.exe" "e:\享中\cloud_runner.py" --daemon
start "" "e:\享中\.venv\Scripts\pythonw.exe" "e:\享中\commander_bot.py"
exit
