import time
import subprocess
import os
import sys

# [Antigravity Sentinel] 永恒哨兵 - 确保系统 24/7 自动运行
def start_services():
    base_dir = r"e:\享中"
    
    # 1. 启动远程中枢 (TG 监听)
    print("[Sentinel] Launching Hermes Hub...")
    subprocess.Popen([sys.executable, "-u", os.path.join(base_dir, "skills", "tg_remote_hub.py")], 
                     creationflags=subprocess.CREATE_NEW_CONSOLE)
    
    # 2. 启动战略观测塔 (Streamlit)
    print("[Sentinel] Launching Strategic Tower...")
    subprocess.Popen(["streamlit", "run", os.path.join(base_dir, "app.py"), "--server.port", "8501"], 
                     creationflags=subprocess.CREATE_NEW_CONSOLE)

if __name__ == "__main__":
    print("[Antigravity] Sentinel Initializing...")
    # 杀掉残留
    try:
        os.system("taskkill /F /IM python.exe /T")
    except: pass
    time.sleep(2)
    start_services()
    print("[Antigravity] All systems online. Sentinel is now guarding the logic.")
