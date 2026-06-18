Set WshShell = CreateObject("WScript.Shell")
strDesktop = WshShell.SpecialFolders("Desktop")
Set oShellLink = WshShell.CreateShortcut(strDesktop & "\【发动物理打击】.lnk")
oShellLink.TargetPath = "E:\享中\【发动物理打击】.bat"
oShellLink.WorkingDirectory = "E:\享中"
oShellLink.IconLocation = "cmd.exe"
oShellLink.Description = "脱网启动 V8 引擎"
oShellLink.Save
