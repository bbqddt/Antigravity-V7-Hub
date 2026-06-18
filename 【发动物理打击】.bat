@echo off
chcp 65001 >nul
cd /d "E:\享中"
echo ========================================
echo        [Antigravity V8 脱网物理打击]
echo ========================================
echo 正在绕过所有网络封锁，直接强制启动本地 V8 核心...
".venv\Scripts\python.exe" "Local_Strike.py"
echo.
echo 执行完毕！(如果弹窗未自动关闭，请点击弹窗上的“确定”)
pause
