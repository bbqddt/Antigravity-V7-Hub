import os
import sys
import subprocess
import json
import time


# 使用当前目录而非硬编码路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_BIN = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")
STREAMLIT_BIN = os.path.join(BASE_DIR, ".venv", "Scripts", "streamlit.exe")

TARGETS = []

# 1. Local API Proxy
proxy_path = os.path.join(BASE_DIR, "local_api_proxy.py")
if os.path.exists(proxy_path):
    TARGETS.append([PYTHON_BIN, proxy_path])

# 2. Streamlit Dashboard
if os.path.exists(STREAMLIT_BIN):
    TARGETS.append([STREAMLIT_BIN, "run", os.path.join(BASE_DIR, "app.py"),
                    "--server.port", "8501", "--server.headless", "true"])

print("[Antigravity Ignition] Engaging Startup Sequence...")

processes = []
for idx, cmd in enumerate(TARGETS, 1):
    print(f"[{idx}/{len(TARGETS)}] Spawning: {os.path.basename(cmd[1]) if len(cmd) > 1 else 'App'}")
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
