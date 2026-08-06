Set WshShell = CreateObject("WScript.Shell")

' 清理旧残影
WshShell.Run "taskkill /f /im python.exe", 0, True
WshShell.Run "taskkill /f /im pythonw.exe", 0, True
WshShell.Run "taskkill /f /im streamlit.exe", 0, True

WScript.Sleep 2000

' 启动本地 API 隧道 (12654端口)
WshShell.Run "cmd.exe /c """"E:\享中\.venv\Scripts\pythonw.exe"" ""E:\享中\local_api_proxy.py""""", 0, False

' 启动 Telegram 观测节点
WshShell.Run "cmd.exe /c """"E:\享中\.venv\Scripts\pythonw.exe"" ""E:\享中\skills\tg_remote_hub.py""""", 0, False

' 启动 Streamlit 可视化面板
WshShell.Run "cmd.exe /c """"E:\享中\.venv\Scripts\pythonw.exe"" ""E:\享中\.venv\Scripts\streamlit.exe"" run ""E:\享中\app.py"" --server.port 8501 --server.headless true""""", 0, False
