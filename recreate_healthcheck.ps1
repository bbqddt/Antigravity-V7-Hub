$BASE = 'E:\享中.worktrees\agents-invisible-pelican'
$PYTHON = "$BASE\.venv\Scripts\python.exe"

$action = New-ScheduledTaskAction -Execute $PYTHON -Argument "`"$BASE\health_check.py`"" -WorkingDirectory $BASE

$trigger1 = New-ScheduledTaskTrigger -AtStartup
$trigger2 = New-ScheduledTaskTrigger -Daily -At 00:00
$trigger2.RepetitionInterval = (New-TimeSpan -Hours 1)
$trigger2.RepetitionDuration = (New-TimeSpan -Days 365)

$triggers = @($trigger1, $trigger2)

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Days 365) -Compatibility Win8

$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Highest

Unregister-ScheduledTask -TaskName 'Antigravity_24x7_HealthCheck' -ErrorAction SilentlyContinue

Register-ScheduledTask -TaskName 'Antigravity_24x7_HealthCheck' -Action $action -Trigger $triggers -Settings $settings -Principal $principal -Description 'Antigravity 7x24 Health Check Hourly (Python)' -Force

Write-Host "[OK] HealthCheck task recreated"