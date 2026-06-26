import subprocess
import time
import os
import sys

# [Antigravity] Hermes Watchdog - 永生看门狗
# 任务：确保 cloud_hermes.py 永不熄灭

SCRIPT_PATH = r"e:\享中\skills\cloud_hermes.py"
VENV_PYTHON = r"e:\享中\.venv\Scripts\python.exe"

def is_hermes_running():
    try:
        output = subprocess.check_output('tasklist /FI "IMAGENAME eq python.exe" /V', shell=True).decode('gbk')
        return "cloud_hermes.py" in output
    except:
        return False

def revive():
    print(f"[{time.strftime('%H:%M:%S')}] 🚨 侦测到哨兵生命体征消失！正在执行强制复活...")
    # 物理级静默：使用 pythonw 且 严禁创建新窗口
    PYTHONW = VENV_PYTHON.replace("python.exe", "pythonw.exe")
    try:
        subprocess.Popen([PYTHONW, SCRIPT_PATH], creationflags=subprocess.CREATE_NO_WINDOW)
        print("✅ 复活指令已下达（全静默模式）。")
    except Exception as e:
        print(f"❌ 复活失败: {e}")


if __name__ == "__main__":
    print("🔱 Antigravity Watchdog 已就位。监控目标: Cloud Hermes")
    while True:
        if not is_hermes_running():
            revive()
        time.sleep(30)
