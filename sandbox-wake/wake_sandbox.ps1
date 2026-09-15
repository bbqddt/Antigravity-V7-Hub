# wake_sandbox.ps1 — 策略 A（Windows 任务计划 / 原生 PowerShell 版）
# ⚠️ 同样必须在本机运行，不要放进沙箱。
#
# 用法:
#   $env:SANDBOX_URL = "https://你的沙箱地址"
#   .\wake_sandbox.ps1
#   或
#   .\wake_sandbox.ps1 -SandboxUrl "https://你的沙箱地址"
#
param(
  [string]$SandboxUrl = $env:SANDBOX_URL
)

$DefaultUrl   = "https://webview.e2b.gz2.sandbox.cloudstudio.club"   # 你的 CloudStudio 沙箱 webview 地址
if (-not $SandboxUrl) { $SandboxUrl = $DefaultUrl }

$HealthPath   = "/health"   # 你的 3000 服务暴露的健康检查端点
$MaxWait      = 120         # 最多等待秒数
$PollInterval = 5           # 轮询间隔秒数

if (-not $SandboxUrl) {
  Write-Error "未提供沙箱地址。用法: .\wake_sandbox.ps1 -SandboxUrl 'https://你的沙箱地址'"
  exit 2
}

$Base      = $SandboxUrl.TrimEnd('/')
$HealthUrl = $Base + $HealthPath

Write-Host "🔔 触发唤醒: $Base"
try {
  Invoke-WebRequest -Uri $Base -TimeoutSec 10 -UseBasicParsing -ErrorAction SilentlyContinue | Out-Null
} catch {
  Write-Host "   (唤醒请求异常，继续轮询)"
}

Write-Host "⏳ 等待 3000 服务就绪 (最多 ${MaxWait}s)..."
$elapsed = 0
while ($elapsed -lt $MaxWait) {
  try {
    $resp = Invoke-WebRequest -Uri $HealthUrl -TimeoutSec 10 -UseBasicParsing
    if ($resp.StatusCode -eq 200) {
      Write-Host "✅ 服务已就绪: $HealthUrl (HTTP 200)，耗时 ${elapsed}s"
      Write-Host "   现在可以打开 webview 了。"
      exit 0
    }
  } catch { }
  Write-Host "   ... 等待中 (${elapsed}s/${MaxWait}s)"
  Start-Sleep -Seconds $PollInterval
  $elapsed += $PollInterval
}

Write-Error "⚠️ 等待超时，服务未就绪。检查地址 / /health 端点 / 代理唤醒逻辑。"
exit 1
