# install_service.ps1 - Install Antigravity daemons as Windows services via nssm.
# Effects: auto-start on boot + auto-restart on crash (PID-level self-heal) + log rotation.
# Idempotent: re-running removes old services first.
#
# Usage (run as Administrator):
#   powershell -ExecutionPolicy Bypass -File install_service.ps1
# Uninstall:
#   powershell -ExecutionPolicy Bypass -File install_service.ps1 -Uninstall

param([switch]$Uninstall)

$ErrorActionPreference = 'Continue'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$nssm        = Join-Path $projectRoot "nssm\nssm-2.24\win64\nssm.exe"
$python      = Join-Path $projectRoot ".venv\Scripts\python.exe"
$logs        = Join-Path $projectRoot "logs"
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

if (-not (Test-Path $nssm))   { Write-Error "Missing nssm: $nssm"; exit 1 }
if (-not (Test-Path $python)) { Write-Error "Missing venv: $python"; exit 1 }

$daemons = @(
    @{
        name    = "antigravity-monitor"
        script  = "monitor_dashboard.py"
        display = "Antigravity 7x24 Monitor Dashboard (:8080)"
        desc    = "FastAPI dashboard, persistent on :8080, exposes /api/health"
        depend  = ""
    },
    @{
        name    = "antigravity-cloud-daemon"
        script  = "cloud_daemon_24x7.py"
        display = "Antigravity Cloud Evolution Daemon 7x24"
        desc    = "7x24 auto-evolution daemon (chained compute + state persistence)"
        depend  = "antigravity-monitor"
    }
)

foreach ($d in $daemons) {
    $svc = $d.name
    Write-Host "--- $svc ---"
    & $nssm stop $svc confirm *>$null
    & $nssm remove $svc confirm *>$null

    if ($Uninstall) { Write-Host "removed $svc"; continue }

    $scriptPath = Join-Path $projectRoot $d.script
    if (-not (Test-Path $scriptPath)) { Write-Warning "Missing $scriptPath, skip"; continue }

    & $nssm install $svc $python $d.script 2>&1
    & $nssm set $svc AppDirectory $projectRoot 2>&1
    & $nssm set $svc DisplayName $d.display 2>&1
    & $nssm set $svc Description $d.desc 2>&1

    $out = Join-Path $logs ($svc + ".out.log")
    $err = Join-Path $logs ($svc + ".err.log")
    & $nssm set $svc AppStdout $out 2>&1
    & $nssm set $svc AppStderr $err 2>&1
    & $nssm set $svc AppRotateFiles 1 2>&1
    & $nssm set $svc AppRotateBytes 10485760 2>&1
    & $nssm set $svc AppRotateSeconds 86400 2>&1

    & $nssm set $svc Start SERVICE_AUTO_START 2>&1
    & $nssm set $svc AppExit Default Restart 2>&1
    & $nssm set $svc AppRestartDelay 10000 2>&1

    if ($d.depend -ne "") { & $nssm set $svc DependOnService $d.depend 2>&1 }

    Write-Host "installed $svc (DisplayName: $($d.display))"
}

if (-not $Uninstall) {
    Write-Host ""
    Write-Host "Next: Start-Service antigravity-monitor ; Start-Service antigravity-cloud-daemon"
}
