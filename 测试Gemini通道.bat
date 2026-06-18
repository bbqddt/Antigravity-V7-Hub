@echo off
CHCP 65001
title Antigravity Gemini Channel Tester

echo 📂 [1/2] Setting Environment...
set GEMINI_API_KEY=AIzaSyBtJNrzX8q2RoDhQzCgUZAffoSRp3SCaus

echo 🚀 [2/2] Triggering Python Bridge...
:: 换用标准呼叫方式，配合全路径，哪怕找不到也会报错而不会直接闪退
"E:\享中\.venv\Scripts\python.exe" "E:\享中\bridge_config.py" --model gemini

echo.
echo 💾 Mission Finished.
pause