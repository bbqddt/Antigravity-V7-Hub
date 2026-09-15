Set WshShell = CreateObject("WScript.Shell")
projectRoot = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = projectRoot
WshShell.Run Chr(34) & projectRoot & "\.venv\Scripts\pythonw.exe" & Chr(34) & " " & Chr(34) & projectRoot & "\cloud_runner.py --daemon" & Chr(34), 0, False
WshShell.Run Chr(34) & projectRoot & "\.venv\Scripts\pythonw.exe" & Chr(34) & " " & Chr(34) & projectRoot & "\commander_bot.py" & Chr(34), 0, False
