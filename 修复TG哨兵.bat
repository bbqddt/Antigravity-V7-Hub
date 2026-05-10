@echo off
title [ANTIGRAVITY] TG 哨兵一键重启
color 0c
echo ======================================================
echo           ANTIGRAVITY OMEGA | TG 哨兵修复程序
echo ======================================================
echo [SYSTEM] 正在肃清旧进程...
taskkill /f /im python.exe /fi "WINDOWTITLE eq [Antigravity]*" >nul 2>&1
powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match 'cloud_hermes.py' } | Stop-Process -Force"

echo [SYSTEM] 正在重新注入 Venv 环境...
cd /d "e:\享中"
start /min "" "e:\享中\.venv\Scripts\python.exe" "e:\享中\skills\cloud_hermes.py"

echo [SUCCESS] TG 哨兵已在后台重新上线!
echo [TIP] 请前往 Telegram 发送 /strike 测试。
timeout /t 3
exit
