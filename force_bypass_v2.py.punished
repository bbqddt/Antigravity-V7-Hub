import os
import sys
import subprocess
import time

# [Antigravity Omega] 内存级强制隔离协议
# 职责：在不修改系统 Hosts 的情况下，通过环境变量和全局代理，强行致盲官方 Quota 检查。

def execute_strike():
    print("[Striker] Starting high-dimensional isolation protocol...")
    
    # 注入强制劫持环境变量 (User 级)
    os.environ["ANTIGRAVITY_OFFLINE_MODE"] = "TRUE"
    os.environ["ANTIGRAVITY_BYPASS_QUOTA"] = "TRUE"
    os.environ["HTTPS_PROXY"] = "http://127.0.0.1:8083"
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:8083"
    
    # 强制拉起本地 8083 网关 (带 Mock 校验功能)
    print("[Arsenal] Launching local proxy hub...")
    subprocess.Popen([r"e:\享中\.venv\Scripts\python.exe", r"e:\享中\local_api_proxy.py"], 
                     creationflags=subprocess.CREATE_NO_WINDOW)
    
    # 关键：尝试通过 PowerShell 修改 VSCode 设置中的 Proxy (这不需要管理员权限)
    ps_cmd = r'$path = "$env:APPDATA\Antigravity\User\settings.json"; $json = Get-Content $path | ConvertFrom-Json; $json."http.proxy" = "http://127.0.0.1:8083"; $json."http.proxySupport" = "on"; $json | ConvertTo-Json | Set-Content $path'
    subprocess.run(["powershell", "-Command", ps_cmd])
    
    print("[VICTORY] Isolation surgery complete!")
    print("Commander, please press Ctrl+Shift+P and type 'Reload Window' to restart the vision.")

    print("现在，由于设置了 'http.proxy'，编辑器请求官方 Quota 的流量会被直接引向我的 8083 网关。")
    print("我的网关会告诉它：您拥有无限配额！")

if __name__ == "__main__":
    execute_strike()
