# Antigravity_Launch.ps1
# Clean up existing processes safely
Get-Process -Name "python", "pythonw", "streamlit" -ErrorAction SilentlyContinue | Stop-Process -Force

Start-Sleep -Seconds 2

# Launch Sentinel and Streamlit in the background
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Definition
$venv_pythonw = "$SCRIPT_DIR\.venv\Scripts\pythonw.exe"
$streamlit_exe = "$SCRIPT_DIR\.venv\Scripts\streamlit.exe"

Start-Process -FilePath $venv_pythonw -ArgumentList "$SCRIPT_DIR\skills\sentinel_v2.py" -WindowStyle Hidden
Start-Process -FilePath $venv_pythonw -ArgumentList """$streamlit_exe"" run ""$SCRIPT_DIR\app.py"" --server.port 8501 --server.headless true" -WindowStyle Hidden
