# -*- coding: utf-8 -*-
"""
Antigravity 一键启动器 — 确保只运行一个orchestrator + 一个evolution daemon
在 Windows 启动项中调用此脚本
用法: python _launcher.py
"""
import sys
import os
import time
import subprocess
import psutil
from pathlib import Path

PROJECT_ROOT = Path(r"D:\cdx\antigravity_cloud")
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

def is_daemon_running(script_name):
    """检查守护进程是否已运行（只算python进程）"""
    for proc in psutil.process_iter(['pid', 'cmdline', 'exe']):
        try:
            exe = proc.info.get('exe', '') or ''
            if 'python' not in exe.lower():
                continue
            cmdline = ' '.join(proc.info['cmdline'] or [])
            # Must be the actual script, not a wrapper or our check
            if script_name in cmdline and '--daemon' in cmdline:
                # Exclude this launcher script itself
                if '_launcher' in cmdline:
                    continue
                return proc.info['pid']
        except:
            pass
    return None

def start_daemon(script, args, log_file):
    """启动守护进程"""
    pid = is_daemon_running(script)
    if pid:
        print(f"[{script}] 已运行 PID={pid}，跳过")
        return pid

    log_path = LOG_DIR / log_file
    python = sys.executable
    cmd = [python, str(PROJECT_ROOT / script)] + args
    print(f"[{script}] 启动中...")

    proc = subprocess.Popen(
        cmd,
        cwd=str(PROJECT_ROOT),
        stdout=open(log_path, "a", encoding="utf-8"),
        stderr=subprocess.STDOUT,
    )
    print(f"[{script}] 已启动 PID={proc.pid}")
    return proc.pid

def main():
    print(f"Antigravity Launcher {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # 0. 启动Ray本地集群(如果没运行)
    import subprocess as _sp
    ray_result = _sp.run(['ray', 'status'], capture_output=True, text=True, encoding='utf-8', errors='replace')
    if 'ERROR' in ray_result.stdout or ray_result.returncode != 0:
        print("[Ray] 启动本地集群...")
        import os as _os
        _ray_tmp = str(PROJECT_ROOT / "logs" / ".ray")
        _os.makedirs(_ray_tmp, exist_ok=True)
        _sp.Popen(['ray', 'start', '--head', '--num-cpus=6', '--port=6379',
                    f'--temp-dir={_ray_tmp}'],
                  cwd=str(PROJECT_ROOT), stdout=open(LOG_DIR / 'ray.log', 'a'),
                  stderr=subprocess.STDOUT)
        time.sleep(5)
        print("[Ray] 已启动")
    else:
        print("[Ray] 已运行")

    # 1. 启动orchestrator
    start_daemon("cloud_orchestrator.py",
                 ["--daemon", "--interval", "15", "--tasks", "30", "--workers", "6"],
                 "orchestrator_daemon.log")

    # 2. 启动evolution daemon
    start_daemon("continuous_evolution_daemon_v4.py",
                 ["--daemon", "--interval", "30"],
                 "evolution_daemon.log")

    # 3. 生成最新预测（如果缺失或过期）
    pred_path = PROJECT_ROOT / "latest_prediction.json"
    import json
    from datetime import datetime
    need_prediction = True
    if pred_path.exists():
        with open(pred_path, encoding='utf-8') as f:
            pred = json.load(f)
        try:
            from data_layer import load_history
            draws = load_history()
            if pred.get('target_period') and draws[-1].period <= pred['target_period']:
                need_prediction = False
        except:
            pass

    if need_prediction:
        print("[Prediction] 生成最新预测...")
        subprocess.run([sys.executable, str(PROJECT_ROOT / "orchestrate.py")],
                       cwd=str(PROJECT_ROOT), capture_output=True)
        print("[Prediction] 完成")

    # 4. 运行健康检查
    print("[HealthCheck] 运行检查...")
    subprocess.run([sys.executable, str(PROJECT_ROOT / "health_check.py")],
                   cwd=str(PROJECT_ROOT), capture_output=True)
    print("[HealthCheck] 完成")

    print("启动器完成")

if __name__ == "__main__":
    main()
