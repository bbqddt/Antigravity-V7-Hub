$ErrorActionPreference = "SilentlyContinue"

# Kill any existing processes to ensure clean start
Get-CimInstance Win32_Process -Filter "name='python.exe' OR name='pythonw.exe'" | Where-Object { $_.CommandLine -match "sentinel_v2.py|tg_remote_hub.py|cloud_hermes.py|app.py|local_api_proxy.py" } | Invoke-CimMethod -MethodName Terminate

# Start Sentinel V3 (Auto-Healing Armor)
Start-Process -FilePath "E:\享中\.venv\Scripts\python.exe" -ArgumentList "E:\享中\skills\sentinel_v2.py" -WindowStyle Hidden -RedirectStandardOutput "E:\享中\sentinel.log" -RedirectStandardError "E:\享中\sentinel_error.log"

# Start Observation Tower (app.py)
Start-Process -FilePath "E:\享中\.venv\Scripts\streamlit.exe" -ArgumentList "run E:\享中\app.py --server.port 8501 --server.headless true" -WindowStyle Hidden -RedirectStandardOutput "E:\享中\streamlit.log" -RedirectStandardError "E:\享中\streamlit_error.log"

# Note: sentinel_v2.py will automatically start tg_remote_hub.py and local_api_proxy.py
