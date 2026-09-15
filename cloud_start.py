# -*- coding: utf-8 -*-
"""
Antigravity 云端守护进程 — Windows 启动脚本
============================================

用法:
    python cloud_start.py              # 后台守护模式
    python cloud_start.py --once       # 单轮运行
    python cloud_start.py --status     # 查看状态
    python cloud_start.py --task prediction  # 运行单个任务
"""
import sys
import os
import time
import subprocess
import signal
import json
from pathlib import Path
from datetime import datetime

_PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROJECT_ROOT))

# 日志
LOG_DIR = _PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
PID_FILE = _PROJECT_ROOT / "cloud_runner.pid"
LOG_FILE = LOG_DIR / "cloud_start.log"


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass


def is_running():
    """检查是否已有守护进程在运行"""
    if PID_FILE.exists():
        with open(PID_FILE, "r") as f:
            try:
                pid = int(f.read().strip())
                # 检查进程是否存在
                try:
                    os.kill(pid, 0)
                    return pid
                except OSError:
                    # 进程不存在，清理旧PID
                    PID_FILE.unlink()
                    return None
            except ValueError:
                PID_FILE.unlink()
                return None
    return None


def start_daemon():
    """启动守护进程"""
    existing = is_running()
    if existing:
        log(f"守护进程已在运行 (PID={existing})")
        return

    log("启动云端守护进程...")

    # 启动 cloud_runner_v2.py 的守护模式
    runner_script = _PROJECT_ROOT / "cloud_runner_v2.py"
    if not runner_script.exists():
        log(f"错误: 找不到 {runner_script}")
        return

    # 设置环境变量
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    # 启动子进程
    process = subprocess.Popen(
        [sys.executable, str(runner_script), "--daemon", "--interval", "30"],
        cwd=str(_PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        startupinfo=None,
    )

    # 保存PID
    with open(PID_FILE, "w") as f:
        f.write(str(process.pid))

    log(f"守护进程已启动 (PID={process.pid})")
    log(f"日志: {LOG_FILE}")

    # 启动日志监控线程
    monitor_thread = subprocess.Popen(
        [sys.executable, "-c", f"""
import time, sys
from pathlib import Path
log_file = Path(r'{LOG_FILE}')
with open(log_file, 'r', encoding='utf-8') as f:
    f.seek(0, 2)  # 跳到末尾
    while True:
        line = f.readline()
        if line:
            sys.stdout.write(line)
            sys.stdout.flush()
        else:
            time.sleep(2)
        if not Path(r'{PID_FILE}').exists():
            break
"""],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    log(f"日志监控已启动 (PID={monitor_thread.pid})")


def stop_daemon():
    """停止守护进程"""
    pid = is_running()
    if not pid:
        log("没有运行的守护进程")
        return

    log(f"停止守护进程 (PID={pid})...")
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(3)
        # 如果还在运行，强制终止
        try:
            os.kill(pid, 0)
            os.kill(pid, signal.SIGKILL)
        except:
            pass
    except OSError:
        pass

    PID_FILE.unlink(missing_ok=True)
    log("守护进程已停止")


def show_status():
    """显示守护进程状态"""
    pid = is_running()

    print("\n" + "=" * 60)
    print("  Antigravity 云端守护进程状态")
    print("=" * 60)

    if pid:
        print(f"\n  状态: 运行中 (PID={pid})")
    else:
        print(f"\n  状态: 未运行")

    # 显示最近日志
    if LOG_FILE.exists():
        print(f"\n  最近日志:")
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-10:]:
                    print(f"    {line.strip()}")
        except:
            pass

    # 显示守护进程状态
    state_file = _PROJECT_ROOT / "cloud_runner_state.json"
    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            print(f"\n  历史统计:")
            print(f"    总运行周期: {state.get('total_cycles', 0)}")
            print(f"    上次运行: {state.get('last_run', '从未')}")
        except:
            pass

    print("=" * 60)


def run_once():
    """运行单轮预测"""
    log("运行单轮预测...")
    from orchestrate import run_full_pipeline
    result = run_full_pipeline(top_k=5)
    target = result.get("target_period", "?")
    log(f"预测完成: 目标 #{target}")
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Antigravity 云端守护进程启动器")
    parser.add_argument("--start", action="store_true", help="启动守护进程")
    parser.add_argument("--stop", action="store_true", help="停止守护进程")
    parser.add_argument("--status", action="store_true", help="显示状态")
    parser.add_argument("--once", action="store_true", help="运行单轮预测")
    args = parser.parse_args()

    if args.stop:
        stop_daemon()
    elif args.status:
        show_status()
    elif args.once:
        run_once()
    elif args.start:
        start_daemon()
    else:
        # 默认：启动守护进程
        start_daemon()
