@echo off
chcp 65001 >nul
title Antigravity Local Proxy Server
echo 正在进入核心代码区...
cd /d C:\Users\Administrator\free-claude-code

echo.
echo [核心任务] 🚀 正在激活本地隧道以绕过额度限制...
echo [状态] 强启补丁已就位。
echo.

uv run python server.py

pause