# Antigravity_Launch.ps1
# Clean up existing processes safely
Get-Process -Name "python", "pythonw", "streamlit" -ErrorAction SilentlyContinue | Stop-Process -Force

Start-Sleep -Seconds 2

# Launch Sentinel and Streamlit in the background
$venv_pythonw = "E:\享中\.venv\Scripts\pythonw.exe"
$streamlit_exe = "E:\享中\.venv\Scripts\streamlit.exe"

Start-Process -FilePath $venv_pythonw -ArgumentList "E:\享中\skills\sentinel_v2.py" -WindowStyle Hidden
Start-Process -FilePath $venv_pythonw -ArgumentList """$streamlit_exe"" run ""E:\享中\app.py"" --server.port 8501 --server.headless true" -WindowStyle Hidden
