@echo off
chcp 65001 >nul
REM 进入项目根目录
cd /d "%~dp0"
REM 确保日志目录存在
if not exist "%~dp0logs" mkdir "%~dp0logs"

REM 使用仓库内 .venv 运行 cloud_daemon.py（你已选择使用 .venv）
SET VENV_PY=%~dp0.venv\Scripts\python.exe
IF NOT EXIST "%VENV_PY%" (
    ECHO [run_cloud_daemon] 未找到 .venv Python: %VENV_PY% >> "%~dp0logs\run_cloud_daemon.log" 2>&1
    EXIT /B 1
)

REM 启动一次守护进程的单次执行（会把 stdout/stderr 追加到 wrapper 日志）
"%VENV_PY%" "%~dp0cloud_daemon.py" --run >> "%~dp0logs\run_cloud_daemon.log" 2>&1
EXIT /B %ERRORLEVEL%
