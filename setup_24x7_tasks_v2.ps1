# Antigravity 7x24 守护进程计划任务 - 参照 setup_autostart.ps1 方式
# 以管理员运行: powershell -ExecutionPolicy Bypass -File setup_24x7_tasks_v2.ps1

$ErrorActionPreference = "Stop"
$BASE = Split-Path -Parent $MyInvocation.MyCommand.Definition
$PYTHON = "$BASE\.venv\Scripts\python.exe"
$LOG_DIR = "$BASE\logs"

New-Item -ItemType Directory -Force -Path $LOG_DIR | Out-Null

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Antigravity 7x24 Daemon Tasks Setup v2"
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 5 `
    -RestartInterval (New-TimeSpan -Minutes 2) `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Days 365) `
    -Compatibility Win8

$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Highest

# --- Cloud Daemon ---
$taskCloud = "Antigravity_CloudDaemon_24x7"
Get-ScheduledTask -TaskName $taskCloud -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false -ErrorAction SilentlyContinue

$actionCloud = New-ScheduledTaskAction `
    -Execute $PYTHON `
    -Argument "`"$BASE\cloud_daemon_24x7.py`"" `
    -WorkingDirectory $BASE

$triggerCloudBoot = New-ScheduledTaskTrigger -AtStartup
$triggerCloudDaily = New-ScheduledTaskTrigger -Daily -At 3am

Register-ScheduledTask `
    -TaskName $taskCloud `
    -Action $actionCloud `
    -Trigger $triggerCloudBoot, $triggerCloudDaily `
    -Settings $settings `
    -Principal $principal `
    -Description "Antigravity Cloud Daemon 7x24 - Formula Evolution" `
    -Force

Write-Host "[OK] Task '$taskCloud' created (Boot + Daily 03:00)" -ForegroundColor Green

# --- Research Daemon ---
$taskResearch = "Antigravity_ResearchDaemon_24x7"
Get-ScheduledTask -TaskName $taskResearch -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false -ErrorAction SilentlyContinue

$actionResearch = New-ScheduledTaskAction `
    -Execute $PYTHON `
    -Argument "`"$BASE\research_daemon_24x7.py`"" `
    -WorkingDirectory $BASE

$triggerResearchBoot = New-ScheduledTaskTrigger -AtStartup
$triggerResearchDaily = New-ScheduledTaskTrigger -Daily -At 3am

Register-ScheduledTask `
    -TaskName $taskResearch `
    -Action $actionResearch `
    -Trigger $triggerResearchBoot, $triggerResearchDaily `
    -Settings $settings `
    -Principal $principal `
    -Description "Antigravity Research Daemon 7x24 - LLM Research & Optimization" `
    -Force

Write-Host "[OK] Task '$taskResearch' created (Boot + Daily 03:00)" -ForegroundColor Green

# --- Health Check ---
$taskHealth = "Antigravity_24x7_HealthCheck"
Get-ScheduledTask -TaskName $taskHealth -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false -ErrorAction SilentlyContinue

$actionHealth = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -Command `"& { `$log = '$LOG_DIR\health_24x7.log'; `$cloud = (tasklist /FI 'IMAGENAME eq python.exe' /FO CSV 2>`$null | findstr /I cloud_daemon_24x7); `$research = (tasklist /FI 'IMAGENAME eq python.exe' /FO CSV 2>`$null | findstr /I research_daemon_24x7); '[HEALTH] ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' CloudDaemon=' + (if(`$cloud){'RUNNING'}else{'STOPPED'}) + ' ResearchDaemon=' + (if(`$research){'RUNNING'}else{'STOPPED'}) | Out-File -Append -Encoding utf8 `$log }`"" `
    -WorkingDirectory $BASE

$triggerHealthBoot = New-ScheduledTaskTrigger -AtStartup
$triggerHealthHourly = New-ScheduledTaskTrigger -Once -At "00:00" -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 365)

Register-ScheduledTask `
    -TaskName $taskHealth `
    -Action $actionHealth `
    -Trigger $triggerHealthBoot, $triggerHealthHourly `
    -Settings $settings `
    -Principal $principal `
    -Description "Antigravity 7x24 Health Check Hourly" `
    -Force

Write-Host "[OK] Task '$taskHealth' created (Boot + Hourly)" -ForegroundColor Green

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  SETUP COMPLETE!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Verify: Get-ScheduledTask -TaskName Antigravity_*"
Write-Host "Start now: Start-ScheduledTask -TaskName Antigravity_CloudDaemon_24x7"
Write-Host "Logs: $LOG_DIR\cloud_daemon_*.log, $LOG_DIR\research_daemon_*.log"