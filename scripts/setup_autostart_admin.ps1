$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runScript = Join-Path $projectRoot 'run_cloud_daemon.bat'
$logFile = Join-Path $projectRoot 'logs\setup_autostart_admin.log'

New-Item -Path $logFile -ItemType File -Force | Out-Null
function Log($message) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $message"
    Add-Content -Path $logFile -Value $line
    Write-Output $line
}

$identity = [Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
$admin = $identity.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    Log "当前不是管理员，尝试以管理员身份重启脚本"
    $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    Start-Process powershell.exe -Verb RunAs -ArgumentList $arguments -Wait
    exit $LASTEXITCODE
}

Log "开始注册 Antigravity 自动启动计划任务"

try {
    if (-not (Test-Path $runScript)) {
        throw "找不到启动脚本: $runScript"
    }

    $action = New-ScheduledTaskAction -Execute $runScript -WorkingDirectory $projectRoot
    $triggerLogon = New-ScheduledTaskTrigger -AtLogOn
    $triggerPeriodic = New-ScheduledTaskTrigger -Daily -At 00:00 -RepetitionInterval (New-TimeSpan -Hours 6) -RepetitionDuration (New-TimeSpan -Days 1)

    $taskName1 = 'Antigravity CloudDaemon AtLogon'
    $taskName2 = 'Antigravity CloudDaemon Every6Hours'

    foreach ($taskName in @($taskName1, $taskName2)) {
        $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        if ($existing) {
            Unregister-ScheduledTask -TaskName $taskName -Confirm:$false | Out-Null
            Log "已更新现有计划任务: $taskName"
        }
    }

    Register-ScheduledTask -TaskName $taskName1 -Action $action -Trigger $triggerLogon -RunLevel Highest -Force | Out-Null
    Log "已注册计划任务: $taskName1"

    Register-ScheduledTask -TaskName $taskName2 -Action $action -Trigger $triggerPeriodic -RunLevel Highest -Force | Out-Null
    Log "已注册计划任务: $taskName2"

    Log "计划任务注册完成。"
} catch {
    Log "计划任务注册失败: $($_.Exception.Message)"
    throw
}
