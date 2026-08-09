# 本地一键拉起 Antigravity（无沙箱模式）
# 启动：cloud_daemon_24x7.py（演化守护） + monitor_dashboard.py（:8080 面板，含 /api/health）
# 用法：
#   powershell -ExecutionPolicy Bypass -File start_local.ps1
# 或放入 Windows 启动文件夹 / 由 .vscode/tasks.json（folderOpen）调用。

$ErrorActionPreference = 'Continue'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$logs = Join-Path $projectRoot "logs"
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

$py = Join-Path $projectRoot ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $py)) {
    Write-Error "未找到 venv 解释器：$py `n请先在本仓库执行创建虚拟环境并安装依赖。"
    exit 1
}

$jobs = @(
    @{ name = "cloud_daemon_24x7"; script = "cloud_daemon_24x7.py" },
    @{ name = "monitor_dashboard"; script = "monitor_dashboard.py" }
)

foreach ($j in $jobs) {
    $script = Join-Path $projectRoot $j.script
    if (Test-Path $script) {
        $out = Join-Path $logs ($j.name + ".out.log")
        $err = Join-Path $logs ($j.name + ".err.log")
        Start-Process -FilePath $py -ArgumentList $script `
            -WindowStyle Hidden -WorkingDirectory $projectRoot `
            -RedirectStandardOutput $out -RedirectStandardError $err
        Write-Host "✅ 已启动 $($j.name)  -> 日志见 logs\$($j.name).*.log"
    }
    else {
        Write-Warning "❌ 缺失 $script（跳过）"
    }
}

Write-Host ""
Write-Host "本地服务已拉起："
Write-Host "  - 演化守护 cloud_daemon_24x7.py"
Write-Host "  - 监控面板 monitor_dashboard.py  ->  http://localhost:8080  (健康检查 /api/health)"
Write-Host ""
Write-Host "如需公网访问（替代已失效的 CloudStudio 预览地址），另开一个终端跑："
Write-Host "  .\cloudflared.exe tunnel --url http://localhost:8080"
Write-Host "  它会返回一个 *.trycloudflare.com 的公网地址。"
