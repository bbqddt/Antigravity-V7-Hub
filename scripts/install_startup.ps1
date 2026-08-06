$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\Antigravity_CloudRunner.lnk")
$Shortcut.TargetPath = "e:\享中\.venv\Scripts\pythonw.exe"
$Shortcut.Arguments = "e:\享中\cloud_runner.py --daemon"
$Shortcut.WorkingDirectory = "e:\享中"
$Shortcut.WindowStyle = 7
$Shortcut.Save()

$Shortcut2 = $WshShell.CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\Antigravity_CommanderBot.lnk")
$Shortcut2.TargetPath = "e:\享中\.venv\Scripts\pythonw.exe"
$Shortcut2.Arguments = "e:\享中\commander_bot.py"
$Shortcut2.WorkingDirectory = "e:\享中"
$Shortcut2.WindowStyle = 7
$Shortcut2.Save()
