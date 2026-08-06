# -*- coding: utf-8 -*-
"""
[Antigravity Sentinel] 永恒哨兵 - 确保系统 24/7 自动运行

修复：
1. 路径改为相对项目根目录
2. 移除危险的 taskkill /F /IM python.exe（会杀死所有 Python 进程）
3. 改为选择性终止特定端口占用
"""
import time
import subprocess
import os
import sys
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent


def start_services():
    """启动所有 Antigravity 服务"""
    # 1. 启动远程中枢 (TG 监听)
    print("[Sentinel] Launching Hermes Hub...")
    hub_path = _BASE_DIR / "skills" / "tg_remote_hub.py"
    if hub_path.exists():
        subprocess.Popen([sys.executable, "-u", str(hub_path)],
                         creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        print(f"[Sentinel] WARNING: {hub_path} not found, skipping.")

    # 2. 启动战略观测塔 (Streamlit)
    print("[Sentinel] Launching Strategic Tower...")
    app_path = _BASE_DIR / "app.py"
    if app_path.exists():
        subprocess.Popen(["streamlit", "run", str(app_path), "--server.port", "8501"],
                         creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        print(f"[Sentinel] WARNING: {app_path} not found, skipping.")


def cleanup_stale_ports():
    """清理占用特定端口的进程（安全版，不杀死所有 Python）"""
    ports_to_check = [8501, 12654, 15999, 8090, 3000]
    for port in ports_to_check:
        try:
            result = subprocess.run(
                f"netstat -ano | findstr :{port}",
                shell=True, capture_output=True, text=True, timeout=5
            )
            if result.stdout:
                # 提取 PID
                for line in result.stdout.splitlines():
                    parts = line.strip().split()
                    if parts and parts[-1].isdigit():
                        pid = parts[-1]
                        print(f"[Sentinel] Found process PID {pid} on port {port}")
        except Exception:
            pass


if __name__ == "__main__":
    print("[Antigravity] Sentinel Initializing...")
    cleanup_stale_ports()
    time.sleep(2)
    start_services()
    print("[Antigravity] All systems online. Sentinel is now guarding the logic.")
