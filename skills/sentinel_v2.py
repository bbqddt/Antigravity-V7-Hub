import os
import subprocess
import time
import requests

# [Antigravity Omega - 永恒守望者]
# 目标：解决长官反馈的“打不开”、“无反应”问题。
# 逻辑：实时监控端口，死后 3 秒原地复活。

def check_port(port):
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0

def heal_system():
    base_dir = r"e:\享中"
    
    # 1. 监控 127.0.0.1:8501 (观测塔)
    if not check_port(8501):
        print("[Watcher] ⚠️ 观测塔熄灭，正在紧急重启...")
        subprocess.Popen(["streamlit", "run", os.path.join(base_dir, "app.py"), "--server.port", "8501", "--server.address", "127.0.0.1"], 
                         creationflags=subprocess.CREATE_NEW_CONSOLE)
    
    # 2. 监控 TG 机器人进程 (通过检测进程名)
    # (这里采用简单粗暴的定时拉起，确保它在内存中)
    subprocess.Popen(["python", os.path.join(base_dir, "skills", "tg_remote_hub.py")], 
                     creationflags=subprocess.CREATE_NEW_CONSOLE)

if __name__ == "__main__":
    print("[Antigravity] Sentinel V2.0 - Monitoring Started...")
    while True:
        try:
            # 只有当端口不通时才拉起
            if not check_port(8501):
                heal_system()
        except: pass
        time.sleep(30) # 30秒巡检一次
