@echo off
set GEMINI_API_KEY=AIzaSyAy6pJtckoIarMPlWi-oC97_h5302nkY94

cd /d "%~dp0"

start "" ".venv\Scripts\streamlit.exe" run "app.py" --server.port 8501 --server.headless true
start "" ".venv\Scripts\python.exe" "skills\sentinel_v2.py"
start "" ".venv\Scripts\python.exe" "v7_evolved_engine.py"
