@echo off
chcp 65001 >nul
REM 进入项目根目录
cd /d "%~dp0"

REM 确保日志目录存在
if not exist "%~dp0logs" mkdir "%~dp0logs"

REM 使用仓库内 .venv 运行 metrics_exporter.py
SET VENV_PY=%~dp0.venv\Scripts\python.exe
IF NOT EXIST "%VENV_PY%" (
    ECHO [run_metrics_exporter] 未找到 .venv Python: %VENV_PY% >> "%~dp0logs\run_metrics_exporter.log" 2>&1
    EXIT /B 1
)

REM 后台启动监控导出器，并将输出写入日志
start "Antigravity Metrics Exporter" /min cmd /c ""%VENV_PY%" "%~dp0scripts\metrics_exporter.py" --host 0.0.0.0 --port 9119 >> "%~dp0logs\run_metrics_exporter.log" 2>&1"
EXIT /B 0
