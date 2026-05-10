import os
import subprocess
import time
import socket

# [Antigravity Omega - 天基自愈哨兵 V3.0]
# 职责：监控核心组件，执行防多开清剿，维护唯一生命通道。

def check_port(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0

def clean_and_respawn(process_name, script_path):
    print(f"[Sentinel] 侦测到 {process_name} 异常或断联，执行天基扫荡...")
    # 暴力清理所有重名进程，防止精神分裂
    subprocess.run(["powershell", "-Command", f"Get-Process python -ErrorAction SilentlyContinue | Where-Object {{ $_.CommandLine -match '{process_name}' }} | Stop-Process -Force"], shell=True)
    time.sleep(1)
    print(f"[Sentinel] 正在拉起纯净唯一的生命线: {process_name}")
    subprocess.Popen(["python", script_path], creationflags=subprocess.CREATE_NO_WINDOW)

def heal_system():
    base_dir = r"e:\享中"
    
    # 1. 监控 127.0.0.1:8501 (观测塔)
    if not check_port(8501):
        clean_and_respawn("app.py", os.path.join(base_dir, "app.py"))
        
    # 2. 监控 127.0.0.1:8083 (无限算力代理)
    if not check_port(8083):
        clean_and_respawn("local_api_proxy.py", os.path.join(base_dir, "local_api_proxy.py"))
    
    # 3. 监控 Cloud Hermes 主脑 (通过进程检测)
    # 获取 cloud_hermes 的进程数量
    try:
        output = subprocess.check_output(["powershell", "-Command", "(Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match 'cloud_hermes.py' }).Count"]).decode().strip()
        count = int(output) if output else 0
    except:
        count = 0
        
    if count == 0:
        clean_and_respawn("cloud_hermes.py", os.path.join(base_dir, "skills", "cloud_hermes.py"))
    elif count > 1:
        print("[Sentinel] 警报！Cloud Hermes 发生多开精神分裂！执行肃清...")
        clean_and_respawn("cloud_hermes.py", os.path.join(base_dir, "skills", "cloud_hermes.py"))

if __name__ == "__main__":
    print("[Antigravity] Sentinel V3.0 (自愈装甲) - 永恒守望中...")
    while True:
        try:
            heal_system()
        except Exception as e:
            print("[Sentinel] 哨兵核心受损:", e)
        time.sleep(30) # 每30秒执行一次全维体检
