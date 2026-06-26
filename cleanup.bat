@echo off
CHCP 65001 >nul
echo [OMNI BRAIN] Initiating Targeted Cellular Apoptosis (系统级新陈代谢)...

:: 1. 斩杀低级临时文件与错误断点
del /f /q "新建 文本文档.txt" 2>nul
del /f /q "新建 文本文档 (2).txt" 2>nul
del /f /q "🚀" 2>nul
del /f /q "同步" 2>nul
del /f /q "main*" 2>nul
del /f /q "*.log" 2>nul

:: 2. 清除刚刚修复系统留下的医疗废弃物
del /f /q "hermes_err.txt" 2>nul
del /f /q "hermes_out.txt" 2>nul
del /f /q "restart_hermes.bat" 2>nul

:: 3. 剥离冗余的编译缓存 (神经元排异物)
echo [OMNI BRAIN] Purging all neural __pycache__ traces...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
for /d /r d:\Antigravity_V7 %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"

echo [SUCCESS] Apoptosis Complete. The Leviathan is now absolutely sharp.

