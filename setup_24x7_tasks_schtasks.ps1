# Antigravity 7x24 守护进程计划任务 - 使用 schtasks.exe
# 以管理员运行: powershell -ExecutionPolicy Bypass -File setup_24x7_tasks_schtasks.ps1

$ErrorActionPreference = "Stop"
$BASE = "E:\享中.worktrees\agents-invisible-pelican"
$PYTHON = "$BASE\.venv\Scripts\python.exe"
$LOG_DIR = "$BASE\logs"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Antigravity 7x24 Daemon Tasks Setup (schtasks)"
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 删除旧任务
schtasks /Delete /TN "Antigravity_CloudDaemon_24x7" /F 2>$null
schtasks /Delete /TN "Antigravity_CloudDaemon_24x7_DailyRestart" /F 2>$null
schtasks /Delete /TN "Antigravity_ResearchDaemon_24x7" /F 2>$null
schtasks /Delete /TN "Antigravity_ResearchDaemon_24x7_DailyRestart" /F 2>$null
schtasks /Delete /TN "Antigravity_24x7_HealthCheck" /F 2>$null

# Cloud Daemon - 开机启动
$cmdCloudBoot = "`"$PYTHON`" `"$BASE\cloud_daemon_24x7.py`""
schtasks /Create /TN "Antigravity_CloudDaemon_24x7" /TR $cmdCloudBoot /SC ONSTART /RU SYSTEM /RL HIGHEST /F
Write-Host "[OK] Antigravity_CloudDaemon_24x7 (ONSTART)" -ForegroundColor Green

# Cloud Daemon - 每日 03:00 重启
schtasks /Create /TN "Antigravity_CloudDaemon_24x7_DailyRestart" /TR $cmdCloudBoot /SC DAILY /ST 03:00 /RU SYSTEM /RL HIGHEST /F
Write-Host "[OK] Antigravity_CloudDaemon_24x7_DailyRestart (DAILY 03:00)" -ForegroundColor Green

# Research Daemon - 开机启动
$cmdResearchBoot = "`"$PYTHON`" `"$BASE\research_daemon_24x7.py`""
schtasks /Create /TN "Antigravity_ResearchDaemon_24x7" /TR $cmdResearchBoot /SC ONSTART /RU SYSTEM /RL HIGHEST /F
Write-Host "[OK] Antigravity_ResearchDaemon_24x7 (ONSTART)" -ForegroundColor Green

# Research Daemon - 每日 03:00 重启
schtasks /Create /TN "Antigravity_ResearchDaemon_24x7_DailyRestart" /TR $cmdResearchBoot /SC DAILY /ST 03:00 /RU SYSTEM /RL HIGHEST /F
Write-Host "[OK] Antigravity_ResearchDaemon_24x7_DailyRestart (DAILY 03:00)" -ForegroundColor Green

# Health Check - 每小时 (简化命令避免 261 字符限制)
$healthScript = @"
`$log = "`$env:BASE\logs\health_24x7.log`"
`$cloud = (tasklist /FI "IMAGENAME eq python.exe" /FO CSV 2>$null | findstr /I cloud_daemon_24x7)
`$research = (tasklist /FI "IMAGENAME eq python.exe" /FO CSV 2>$null | findstr /I research_daemon_24x7)
"`[HEALTH] `(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') CloudDaemon=`$(if(`$cloud){'RUNNING'}else{'STOPPED'}) ResearchDaemon=`$(if(`$research){'RUNNING'}else{'STOPPED'})" | Out-File -Append -Encoding utf8 `$log
"@
$healthScriptPath = "$BASE\scripts\health_check_24x7.ps1"
$healthScript | Out-File -Encoding utf8 $healthScriptPath

$cmdHealth = "powershell -ExecutionPolicy Bypass -File `"$healthScriptPath`""
schtasks /Create /TN "Antigravity_24x7_HealthCheck" /TR $cmdHealth /SC HOURLY /ST 00:00 /RU SYSTEM /RL HIGHEST /F
Write-Host "[OK] Antigravity_24x7_HealthCheck (HOURLY)" -ForegroundColor Green

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  SETUP COMPLETE!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Verify: schtasks /Query /TN 'Antigravity_*' /FO LIST /V"
Write-Host "Start now: schtasks /Run /TN 'Antigravity_CloudDaemon_24x7'"
Write-Host "Logs: $LOG_DIR\cloud_daemon_*.log, $LOG_DIR\research_daemon_*.log"