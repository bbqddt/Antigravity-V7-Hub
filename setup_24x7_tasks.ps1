# Antigravity 7x24 守护进程计划任务设置
# 以管理员运行: powershell -ExecutionPolicy Bypass -File setup_24x7_tasks.ps1

$ErrorActionPreference = "Stop"
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Definition
$BASE = $SCRIPT_DIR
$PYTHON = "$BASE\.venv\Scripts\python.exe"
$LOG_DIR = "$BASE\logs"

# 确保日志目录存在
New-Item -ItemType Directory -Force -Path $LOG_DIR | Out-Null

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Antigravity 7x24 Daemon Tasks Setup"
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 通用设置
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

# 触发器
$triggerBoot = New-ScheduledTaskTrigger -AtStartup
$triggerDaily = New-ScheduledTaskTrigger -Daily -At 3am
$triggers = @($triggerBoot, $triggerDaily)

Write-Host "[DEBUG] Trigger count: $($triggers.Count)" -ForegroundColor Yellow
$triggers | ForEach-Object { Write-Host "[DEBUG] Trigger: $_" -ForegroundColor Yellow }

# --- Cloud Daemon (公式演化) ---
$taskCloud = "Antigravity_CloudDaemon_24x7"
Get-ScheduledTask -TaskName $taskCloud -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false -ErrorAction SilentlyContinue

$actionCloud = New-ScheduledTaskAction `
    -Execute $PYTHON `
    -Argument "`"$BASE\cloud_daemon_24x7.py`"" `
    -WorkingDirectory $BASE

Register-ScheduledTask `
    -TaskName $taskCloud `
    -Action $actionCloud `
    -Trigger $triggers `
    -Settings $settings `
    -Principal $principal `
    -Description "Antigravity Cloud Daemon 7x24 - Formula Evolution" `
    -Force

Write-Host "[OK] Task '$taskCloud' created" -ForegroundColor Green

# --- Research Daemon (LLM 研究) ---
$taskResearch = "Antigravity_ResearchDaemon_24x7"
Get-ScheduledTask -TaskName $taskResearch -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false -ErrorAction SilentlyContinue

$actionResearch = New-ScheduledTaskAction `
    -Execute $PYTHON `
    -Argument "`"$BASE\research_daemon_24x7.py`"" `
    -WorkingDirectory $BASE

Register-ScheduledTask `
    -TaskName $taskResearch `
    -Action $actionResearch `
    -Trigger $triggers `
    -Settings $settings `
    -Principal $principal `
    -Description "Antigravity Research Daemon 7x24 - LLM Research & Optimization" `
    -Force

Write-Host "[OK] Task '$taskResearch' created" -ForegroundColor Green

# --- Health Check (每小时心跳) ---
$taskHealth = "Antigravity_24x7_HealthCheck"
Get-ScheduledTask -TaskName $taskHealth -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false -ErrorAction SilentlyContinue

$actionHealth = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c echo [HEALTH] %date% %time% CloudDaemon=$(tasklist /FI \"IMAGENAME eq python.exe\" /FO CSV 2^>nul ^| findstr /I cloud_daemon_24x7 ^|^| echo STOPPED) ResearchDaemon=$(tasklist /FI \"IMAGENAME eq python.exe\" /FO CSV 2^>nul ^| findstr /I research_daemon_24x7 ^|^| echo STOPPED) >> `"$LOG_DIR\health_24x7.log`" 2^>^&1" `
    -WorkingDirectory $BASE

$triggerHealth = New-ScheduledTaskTrigger -Daily -At 00:00
$triggerHealth.RepetitionInterval = (New-TimeSpan -Hours 1)
$triggerHealth.RepetitionDuration = (New-TimeSpan -Days 365)

Register-ScheduledTask `
    -TaskName $taskHealth `
    -Action $actionHealth `
    -Trigger $triggerHealth `
    -Settings $settings `
    -Principal $principal `
    -Description "Antigravity 7x24 Health Check Hourly" `
    -Force

Write-Host "[OK] Health Check task created" -ForegroundColor Green

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  SETUP COMPLETE!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Created tasks:"
Write-Host "  - $taskCloud (boot + daily 03:00 restart)"
Write-Host "  - $taskResearch (boot + daily 03:00 restart)"
Write-Host "  - $taskHealth (hourly heartbeat)"
Write-Host ""
Write-Host "To verify: Get-ScheduledTask -TaskName Antigravity_*"
Write-Host "To start now: Start-ScheduledTask -TaskName Antigravity_CloudDaemon_24x7"
Write-Host "Logs: $LOG_DIR\cloud_daemon_*.log, $LOG_DIR\research_daemon_*.log"