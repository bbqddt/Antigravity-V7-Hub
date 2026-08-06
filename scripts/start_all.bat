@echo off
chcp 65001
echo ==========================================
echo   Antigravity 系统一键启动
echo ==========================================
echo.

cd /d e:\享中

REM 检查 Python
if not exist ".venv\Scripts\python.exe" (
    echo [错误] 未找到虚拟环境 Python
    pause
    exit /b 1
)

echo [1/3] 执行完整流水线...
.venv\Scripts\python.exe system_manager.py --once

echo.
echo [2/3] 启动守护进程...
.venv\Scripts\python.exe system_manager.py --daemon

echo.
echo [3/3] 系统状态检查...
.venv\Scripts\python.exe -c "import json; from pathlib import Path; f=Path('latest_prediction.json'); print('预测文件存在' if f.exists() else '无预测文件')"

echo.
echo ==========================================
echo   启动完成！查看 logs\ 目录获取详细日志
echo ==========================================
pause
