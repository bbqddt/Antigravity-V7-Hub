@echo off
chcp 65001 >nul
set BASE=E:\享中
set VENV=%BASE%\.venv\Scripts\python.exe
set LOG=%BASE%\logs\auto_schedule.log

echo === [%date% %time%] Antigravity Auto Schedule Start === >> "%LOG%"

echo [%time%] [1/3] Running full pipeline... >> "%LOG%"
"%VENV%" "%BASE%\system_manager.py" --once >> "%LOG%" 2>&1

echo [%time%] [2/3] Non-randomness detection... >> "%LOG%"
"%VENV%" "%BASE%\nonrandomness_detector.py" >> "%LOG%" 2>&1

echo [%time%] [3/3] Done. >> "%LOG%"
echo === [%date% %time%] Antigravity Auto Schedule Complete === >> "%LOG%"