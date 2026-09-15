Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' 清理旧残影
WshShell.Run "taskkill /f /im python.exe", 0, True
WshShell.Run "taskkill /f /im pythonw.exe", 0, True
WshShell.Run "taskkill /f /im streamlit.exe", 0, True

WScript.Sleep 2000

' 启动本地 API 隧道 (12654端口)
venvPython = scriptDir & "\.venv\Scripts\pythonw.exe"
WshShell.Run "cmd.exe /c """"" & venvPython & "" """ & scriptDir & "\local_api_proxy.py""""", 0, False

' 启动 Telegram 观测节点
WshShell.Run "cmd.exe /c """"" & venvPython & "" """ & scriptDir & "\skills\tg_remote_hub.py""""", 0, False

' 启动 Streamlit 可视化面板
streamlitExe = scriptDir & "\.venv\Scripts\streamlit.exe"
WshShell.Run "cmd.exe /c """"" & venvPython & "" """ & streamlitExe & "" run """ & scriptDir & "\app.py"" --server.port 8501 --server.headless true""""", 0, False
