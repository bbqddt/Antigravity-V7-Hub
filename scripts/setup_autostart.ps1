# Antigravity 7x24 Auto-Start Setup
# Run as Administrator: powershell -ExecutionPolicy Bypass -File setup_autostart.ps1
$ErrorActionPreference = "Stop"
$BASE = "E:\享中"
$PYTHON = "$BASE\.venv\Scripts\pythonw.exe"
$MASTER = "$BASE\antigravity_master.py"
$LOG_DIR = "$BASE\logs"

# Ensure log directory exists
New-Item -ItemType Directory -Force -Path $LOG_DIR | Out-Null

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Antigravity 7x24 Auto-Start Setup"
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 1. Remove old shortcuts (they're unreliable)
$startupDir = [Environment]::GetFolderPath("Startup")
Get-ChildItem "$startupDir\Antigravity*" -ErrorAction SilentlyContinue | Remove-Item -Force

# 2. Create Scheduled Task for boot
$taskName = "Antigravity_7x24_Master"
$taskExists = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($taskExists) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "[OK] Removed old task" -ForegroundColor Yellow
}

$action = New-ScheduledTaskAction `
    -Execute $PYTHON `
    -Argument "`"$MASTER`"" `
    -WorkingDirectory $BASE

$trigger = New-ScheduledTaskTrigger -AtStartup

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Days 365) `
    -Compatibility Win8

$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Antigravity 7x24 Master Controller - Auto-start on boot" `
    -Force

Write-Host "[OK] Scheduled Task '$taskName' created" -ForegroundColor Green

# 3. Create a backup hourly trigger task
$taskNameHourly = "Antigravity_HealthCheck"
Get-ScheduledTask -TaskName $taskNameHourly -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false

$actionHealth = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c echo Health Check: %date% %time% >> `"$LOG_DIR\health_check.log`" 2>&1" `
    -WorkingDirectory $BASE

$triggerHealth1 = New-ScheduledTaskTrigger -AtStartup
$triggerHealth2 = New-ScheduledTaskTrigger -Once -At "00:00" -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 365)

Register-ScheduledTask `
    -TaskName $taskNameHourly `
    -Action $actionHealth `
    -Trigger $triggerHealth1, $triggerHealth2 `
    -Settings $settings `
    -Principal $principal `
    -Description "Antigravity Health Check" `
    -Force

Write-Host "[OK] Health Check task created" -ForegroundColor Green

# 4. Start the master controller now
Write-Host ""
Write-Host "Starting Antigravity Master Controller..." -ForegroundColor Cyan
Start-Process -FilePath $PYTHON -ArgumentList "`"$MASTER`"" -WorkingDirectory $BASE -WindowStyle Hidden

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  SETUP COMPLETE!" -ForegroundColor Green
Write-Host "  - Auto-start on boot: ENABLED"
Write-Host "  - 5 modes: CLOUD | SANDBOX | B2B | MCP | CORE"
Write-Host "  - Master running invisibly in background"
Write-Host "  - Logs: $LOG_DIR\master_controller.log"
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "To check status: get-content '$LOG_DIR\master_controller.log' -tail 20"
