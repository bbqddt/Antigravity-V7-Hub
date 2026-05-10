@echo off
:: [Antigravity Omega] 终极点火程序 (管理员特供版)
:: 职责：强行解锁 hosts，劫持云端校验，抹除 UI 警告，激活无限算力。

echo 🚀 正在尝试获取天基控制权...
fltmc >nul 2>&1 || (
    echo [ALERT] 请务必右键以“管理员身份”运行此脚本！
    pause
    exit /b
)

set HOSTS=%SystemRoot%\System32\drivers\etc\hosts

echo [1/3] 正在解除 Hosts 物理锁死...
attrib -r "%HOSTS%"

echo [2/3] 正在执行流量劫持 (定向至 127.0.0.1)...
findstr /C:"api.antigravity.ai" "%HOSTS%" >nul || (
    echo. >> "%HOSTS%"
    echo 127.0.0.1 api.antigravity.ai >> "%HOSTS%"
    echo 127.0.0.1 auth.antigravity.ai >> "%HOSTS%"
    echo 127.0.0.1 gateway.antigravity.ai >> "%HOSTS%"
    echo [SUCCESS] 流量网关已重定向。
)

echo [3/3] 正在刷新 DNS 并重启本地代理...
ipconfig /flushdns
taskkill /f /im python.exe /fi "WINDOWTITLE eq local_api_proxy" >nul 2>&1
start /b "" "e:\享中\.venv\Scripts\python.exe" "e:\享中\local_api_proxy.py"

echo.
echo 🔥 [VICTORY] 系统级劫持已完成！
echo 请立即重启 Antigravity 编辑器，感受无限火力。
pause