# install_task.ps1 — 注册 Windows 计划任务：登录(开机)时自动唤醒沙箱
# 普通用户或管理员运行均可；触发器用 AtLogOn，登录即触发，与 IDE 无关。
# 这样"电脑开机启动后"就会自动把 CloudStudio 沙箱拉起来。
$TaskName = "WakeCloudStudioSandbox"
$Script   = Join-Path $PSScriptRoot "wake_sandbox.ps1"

if (-not (Test-Path $Script)) {
  Write-Error "找不到 $Script，请先把 wake_sandbox.ps1 放在同一目录"
  exit 1
}

# 注意：wake_sandbox.ps1 需要环境变量 SANDBOX_URL。
# 请提前在「系统→高级→环境变量」里新增用户变量 SANDBOX_URL=你的沙箱地址，
# 这样计划任务（无交互桌面）也能读到它。
$Action   = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Script`""
$Trigger  = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -Hidden

Register-ScheduledTask -TaskName $TaskName -Action $Action `
  -Trigger $Trigger -Settings $Settings -Force | Out-Null

Write-Host "✅ 已注册计划任务 '$TaskName'：下次登录(开机)会自动唤醒沙箱"
Write-Host "   立即测试：  powershell -Command \"Start-ScheduledTask -TaskName '$TaskName'\""
Write-Host "   卸载：      powershell -File uninstall_task.ps1"
