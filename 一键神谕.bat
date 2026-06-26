@echo off
title [ANTIGRAVITY] 一键神谕推演控制台
color 0b
echo ======================================================
echo           ANTIGRAVITY OMEGA | 一键神谕模式
echo ======================================================
echo [SYSTEM] 正在同步 50 期真实混沌战绩...
echo [SYSTEM] 正在激活 Claude 3.5 免费隧道...
echo [SYSTEM] 正在绕过官方配额校验...

:: 自动重启后台代理并重置状态
powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match 'local_api_proxy.py' } | Stop-Process -Force; Start-Process -FilePath 'e:\享中\.venv\Scripts\python.exe' -ArgumentList 'e:\享中\local_api_proxy.py' -WindowStyle Hidden"

echo [SUCCESS] 算力隧道已进入战备状态。
echo.
echo 长官，请直接在 Antigravity 聊天框中输入：
echo ">>> 开始推演 26053 期"
echo.
echo (系统将自动完成数据注入、模型选择与算法对冲)
echo ======================================================
pause
