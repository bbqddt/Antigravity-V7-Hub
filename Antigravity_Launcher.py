import subprocess
import os
import sys
import time

BASE_DIR = r"E:\享中"
PYTHON_BIN = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")
STREAMLIT_BIN = os.path.join(BASE_DIR, ".venv", "Scripts", "streamlit.exe")

TARGETS = [
    # 1. Local API Proxy
    [PYTHON_BIN, os.path.join(BASE_DIR, "local_api_proxy.py")],
    # 2. Telegram Hub
    [PYTHON_BIN, os.path.join(BASE_DIR, "skills", "tg_remote_hub.py")],
    # 3. Streamlit Dashboard
    [STREAMLIT_BIN, "run", os.path.join(BASE_DIR, "app.py"), "--server.port", "8501", "--server.headless", "true"]
]

print("[Antigravity Ignition] Engaging Startup Sequence...")

processes = []
for idx, cmd in enumerate(TARGETS, 1):
    print(f"[{idx}/3] Spawning: {os.path.basename(cmd[1]) if len(cmd) > 1 else 'App'}")
    # creationflags=0x08000000 即 CREATE_NO_WINDOW
    # 这样可以在前台显示的同时，子进程完全没有黑框，而且非常稳定
    p = subprocess.Popen(cmd, cwd=BASE_DIR, creationflags=0x08000000)
    processes.append(p)
    time.sleep(1)

print("All systems go! The engines are now running silently in the background.")
print("To shut down Antigravity completely, close this window or use Task Manager.")

try:
    while True:
        time.sleep(3600)
except KeyboardInterrupt:
    print("Shutting down Antigravity...")
    for p in processes:
        p.terminate()
