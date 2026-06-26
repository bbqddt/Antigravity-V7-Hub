Set WshShell = CreateObject("WScript.Shell")

' Kill old instances first
WshShell.Run "taskkill /f /im python.exe", 0, True
WshShell.Run "taskkill /f /im pythonw.exe", 0, True
WshShell.Run "taskkill /f /im streamlit.exe", 0, True

' Wait for cleanup
WScript.Sleep 2000

' Start Sentinel (which auto-spawns tg_remote_hub + local_api_proxy)
WshShell.Run "cmd.exe /c """"E:\享中\.venv\Scripts\pythonw.exe"" ""E:\享中\skills\sentinel_v2.py""""", 0, False

' Start Observation Tower
WshShell.Run "cmd.exe /c """"E:\享中\.venv\Scripts\pythonw.exe"" ""E:\享中\.venv\Scripts\streamlit.exe"" run ""E:\享中\app.py"" --server.port 8501 --server.headless true""""", 0, False
