$scriptPath = Join-Path $PSScriptRoot 'scripts\setup_autostart_admin.ps1'
if (-not (Test-Path $scriptPath)) {
    throw "找不到脚本: $scriptPath"
}

& $scriptPath
exit $LASTEXITCODE
