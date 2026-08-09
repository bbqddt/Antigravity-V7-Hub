$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonw = Join-Path $projectRoot '.venv\Scripts\pythonw.exe'
$cloudRunner = Join-Path $projectRoot 'cloud_runner.py'
$commanderBot = Join-Path $projectRoot 'commander_bot.py'

$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\Antigravity_CloudRunner.lnk")
$Shortcut.TargetPath = $pythonw
$Shortcut.Arguments = "`"$cloudRunner`" --daemon"
$Shortcut.WorkingDirectory = $projectRoot
$Shortcut.WindowStyle = 7
$Shortcut.Save()

$Shortcut2 = $WshShell.CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\Antigravity_CommanderBot.lnk")
$Shortcut2.TargetPath = $pythonw
$Shortcut2.Arguments = "`"$commanderBot`""
$Shortcut2.WorkingDirectory = $projectRoot
$Shortcut2.WindowStyle = 7
$Shortcut2.Save()
