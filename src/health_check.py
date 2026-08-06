#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Antigravity 系统健康检查 — 每小时运行
集成到 Windows 任务计划程序中
"""
import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))

PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

def log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"[{ts}] {msg}", flush=True)
    with open(LOG_DIR / "health_check.log", "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")

def check_daemons():
    """检查守护进程是否运行，未运行则重启"""
    import psutil
    needed = [
        ("cloud_orchestrator.py", "cloud_orchestrator.py --daemon --interval 15 --tasks 30 --workers 6"),
        ("continuous_evolution_daemon", "continuous_evolution_daemon_v4.py --daemon --interval 30"),
    ]
    for name, cmd in needed:
        running = False
        for proc in psutil.process_iter(['pid', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if name in cmdline:
                    running = True
                    break
            except:
                pass
        if not running:
            log(f"Restarting {name}...")
            python = sys.executable
            args = cmd.split()
            subprocess.Popen(
                [python] + args,
                cwd=str(PROJECT_ROOT),
                stdout=open(LOG_DIR / f"{name}.log", "a", encoding="utf-8"),
                stderr=subprocess.STDOUT,
            )
        else:
            log(f"{name}: OK")

def check_data_freshness():
    """检查数据是否过期"""
    from data_layer import load_history
    draws = load_history()
    latest = draws[-1]
    today = datetime.now().date()
    # Draw object has 'period' not 'date' — parse from period or use CSV
    try:
        # Try to get date from CSV directly
        import csv
        csv_path = PROJECT_ROOT / "data" / "lottery_history.csv"
        with open(csv_path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        latest_row = max(rows, key=lambda r: int(r.get('period', 0)))
        last_date_str = latest_row.get('date', '')
        if last_date_str:
            ld = datetime.strptime(last_date_str, '%Y-%m-%d').date()
            days_ago = (today - ld).days
            if days_ago > 3:
                log(f"WARNING: Data is {days_ago} days old! Latest: #{latest.period}")
                subprocess.Popen([sys.executable, "data_updater_v2.py"], cwd=str(PROJECT_ROOT))
            else:
                log(f"Data fresh: {days_ago} days old, #{latest.period}")
        else:
            log(f"Data: #{latest.period} (no date info)")
    except Exception as e:
        log(f"Data check error: {e}")

def check_prediction_current():
    """检查最新预测是否覆盖下一期"""
    pred_path = PROJECT_ROOT / "latest_prediction.json"
    if pred_path.exists():
        with open(pred_path, encoding="utf-8") as f:
            pred = json.load(f)
        target = pred.get("target_period")
        data_periods = pred.get("data_periods", 0)
        from data_layer import load_history
        draws = load_history()
        latest = draws[-1].period
        if target and latest > target:
            log(f"Prediction behind: target={target}, latest_data={latest}. Running orchestrate.py...")
            subprocess.Popen([sys.executable, "orchestrate.py"], cwd=str(PROJECT_ROOT))
        else:
            log(f"Prediction current: target={target}, latest_data={latest}")
    else:
        log("WARNING: No latest_prediction.json found")
        subprocess.Popen([sys.executable, "orchestrate.py"], cwd=str(PROJECT_ROOT))

if __name__ == "__main__":
    log("=== Health Check ===")
    check_daemons()
    check_data_freshness()
    check_prediction_current()
    log("=== Check Complete ===")
