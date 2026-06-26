Set WshShell = CreateObject("WScript.Shell")
strStartup = WshShell.SpecialFolders("Startup")
Set oShellLink = WshShell.CreateShortcut(strStartup & "\Antigravity_Omega.lnk")
oShellLink.TargetPath = "E:\享中\Start_Antigravity.bat"
oShellLink.WindowStyle = 7
oShellLink.Description = "Antigravity Global Launcher"
oShellLink.WorkingDirectory = "E:\享中"
oShellLink.Save
