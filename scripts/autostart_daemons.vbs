Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "e:\享中"
WshShell.Run "e:\享中\.venv\Scripts\pythonw.exe cloud_runner.py --daemon", 0, False
WshShell.Run "e:\享中\.venv\Scripts\pythonw.exe commander_bot.py", 0, False
