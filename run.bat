@echo off
cd /d "E:\享中"
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im pythonw.exe >nul 2>&1
taskkill /f /im streamlit.exe >nul 2>&1
timeout /t 1 /nobreak >nul

start "" ".venv\Scripts\pythonw.exe" "local_api_proxy.py"
start "" ".venv\Scripts\pythonw.exe" "skills\tg_remote_hub.py"
start "" ".venv\Scripts\pythonw.exe" ".venv\Scripts\streamlit.exe" run "app.py" --server.port 8501 --server.headless true

exit
