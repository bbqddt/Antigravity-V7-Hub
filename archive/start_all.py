"""
Antigravity 一键启动脚本
=========================
启动所有核心服务:
  1. Commander Bot (Telegram 主控)
  2. API Proxy (12654 端口)
  3. Streamlit 观测塔 (8501 端口)
  4. Sentinel (守护进程)
"""

import os
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(r"E:\享中")
WORK_DIR = Path(r"E:\Antigravity_Work")

SERVICES = {}


def start_service(name, command, cwd=None, hidden=True):
    """启动服务"""
    flags = subprocess.CREATE_NO_WINDOW if hidden else 0
    process = subprocess.Popen(
        command,
        cwd=cwd or str(BASE_DIR),
        creationflags=flags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    SERVICES[name] = process
    print(f"  ✅ {name} 已启动 (PID: {process.pid})")
    return process


def stop_all():
    """停止所有服务"""
    print("\n🛑 正在停止所有服务...")
    for name, proc in SERVICES.items():
        try:
            proc.terminate()
            proc.wait(timeout=5)
            print(f"  ✅ {name} 已停止")
        except:
            proc.kill()
            print(f"  ⚠️ {name} 已强制终止")


def main():
    print("=" * 50)
    print("  🔱 Antigravity 一键启动")
    print("=" * 50)
    print()

    # 检查 Python 环境
    venv_py = BASE_DIR / ".venv" / "Scripts" / "python.exe"
    if venv_py.exists():
        python = str(venv_py)
        print(f"  🐍 使用虚拟环境: {python}")
    else:
        python = sys.executable
        print(f"  🐍 使用系统 Python: {python}")

    print()

    # 1. API Proxy
    print("[1/4] 启动 API Proxy...")
    api_proxy = WORK_DIR / "local_api_proxy.py"
    if api_proxy.exists():
        start_service("API Proxy", [python, str(api_proxy)], cwd=str(WORK_DIR))
    else:
        print("  ⚠️ local_api_proxy.py 不存在，跳过")
    time.sleep(1)

    # 2. Commander Bot
    print("[2/4] 启动 Commander Bot...")
    commander = WORK_DIR / "commander_bot.py"
    if commander.exists():
        # Bot 需要前台运行以接收信号
        start_service("Commander Bot", [python, str(commander)], cwd=str(WORK_DIR), hidden=True)
    else:
        print("  ⚠️ commander_bot.py 不存在，跳过")
    time.sleep(1)

    # 3. Streamlit 观测塔
    print("[3/4] 启动 Streamlit 观测塔...")
    streamlit_app = BASE_DIR / "app.py"
    if streamlit_app.exists():
        try:
            streamlit_exe = BASE_DIR / ".venv" / "Scripts" / "streamlit.exe"
            if streamlit_exe.exists():
                start_service(
                    "Streamlit",
                    [str(streamlit_exe), "run", str(streamlit_app), "--server.port", "8501", "--server.headless", "true"],
                )
            else:
                start_service(
                    "Streamlit",
                    [python, "-m", "streamlit", "run", str(streamlit_app), "--server.port", "8501"],
                )
        except Exception as e:
            print(f"  ⚠️ Streamlit 启动失败: {e}")
    else:
        print("  ⚠️ app.py 不存在，跳过")
    time.sleep(1)

    # 4. Sentinel (守护进程)
    print("[4/4] 启动 Sentinel 守护...")
    sentinel = WORK_DIR / "skills" / "sentinel_v2.py"
    if sentinel.exists():
        start_service("Sentinel", [python, str(sentinel)], cwd=str(WORK_DIR))
    else:
        print("  ⚠️ sentinel_v2.py 不存在，跳过")

    print()
    print("=" * 50)
    print("  🎉 所有服务已启动")
    print("=" * 50)
    print()
    print("  服务列表:")
    for name, proc in SERVICES.items():
        print(f"    {name}: PID {proc.pid}")
    print()
    print("  访问地址:")
    print("    Streamlit: http://localhost:8501")
    print("    API Proxy: http://localhost:12654")
    print()
    print("  按 Ctrl+C 停止所有服务")
    print()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n")
        stop_all()
        print("  ✅ 所有服务已停止")


if __name__ == "__main__":
    main()
