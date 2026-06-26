import time
import subprocess
import os
import sys

# [Antigravity] Infinite Truth Sentry - 无限真相哨兵
# 任务：24/7 不间断抓取，一旦发现开奖更新，立即触发全球演化。

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FETCHER_PATH = os.path.join(BASE_DIR, "skills", "truth_fetcher.py")
EVOLVER_PATH = os.path.join(BASE_DIR, "skills", "evolution_life.py")
PYTHON_EXE = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")

def strike_and_sync():
    print(f"[{time.strftime('%H:%M:%S')}] 🔱 启动全维打击序列 (26054 对齐)...")
    try:
        # 1. 真相抓取
        subprocess.run([PYTHON_EXE, FETCHER_PATH], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        # 2. 算力套利 (Puter 白嫖)
        BRIDGE_PATH = os.path.join(BASE_DIR, "skills", "puter_bridge.py")
        subprocess.run([PYTHON_EXE, BRIDGE_PATH], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        # 3. 本地演化 (融合对冲)
        subprocess.run([PYTHON_EXE, EVOLVER_PATH], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        print("✅ [OMEGA CLOCK] 26054 全闭环同步完成。")
    except Exception as e:
        print(f"❌ 打击序列中断: {e}")


if __name__ == "__main__":
    print("🔱 Antigravity 无限真相哨兵已点火。监控频率: 15分钟/次")
    while True:
        strike_and_sync()
        # 模拟心跳
        with open(os.path.join(BASE_DIR, "sentry_heartbeat.txt"), "w") as f:
            f.write(str(time.time()))
        time.sleep(900) # 15分钟巡检一次
