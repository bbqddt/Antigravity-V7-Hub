# uninstall_task.ps1 — 卸载开机自启的计划任务
$TaskName = "WakeCloudStudioSandbox"
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
  Write-Host "✅ 已卸载计划任务 '$TaskName'"
} else {
  Write-Host "ℹ️ 计划任务 '$TaskName' 不存在，无需卸载"
}
