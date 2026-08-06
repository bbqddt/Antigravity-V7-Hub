@echo off
chcp 65001 >nul
echo [Antigravity 战略重构] 启动极简内核...

echo 1. 清理旧残影...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im pythonw.exe >nul 2>&1
taskkill /f /im streamlit.exe >nul 2>&1
timeout /t 1 /nobreak >nul

echo 2. 启动本地 API 隧道 (12654端口)...
start "" ".venv\Scripts\pythonw.exe" "local_api_proxy.py"

echo 3. 启动 Telegram 观测节点...
start "" ".venv\Scripts\pythonw.exe" "skills\tg_remote_hub.py"

echo 4. 启动 Streamlit 可视化面板...
start "" ".venv\Scripts\pythonw.exe" ".venv\Scripts\streamlit.exe" run "app.py" --server.port 8501 --server.headless true

echo [系统已点燃] 后台静默运行中。若需关闭，请重新双击此脚本或关闭电脑。
timeout /t 3 >nul
exit