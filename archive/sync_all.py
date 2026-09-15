"""
Antigravity 双向同步脚本 — 享中 <-> Antigravity_Work
双向同步，确保两个目录保持一致。
"""
import os
import shutil
import json
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = str(_PROJECT_ROOT / 'Antigravity_Work')
Xiang_DIR = str(_PROJECT_ROOT)

# 必须同步的核心文件
CORE_FILES = [
    "commander_bot.py",
    "enhanced_predictor.py",
    "health_check.py",
    "start_all.py",
    "cloud_deploy.py",
    "latest_decision.json",
    "latest_decision_v8.json",
    "latest_predictions_evolved.json",
    "evolution_state.json",
    "run_prediction.py",
    "SYSTEM_STATUS.json",
    "token_tg.txt",
]

# 数据目录
DATA_FILES = [
    "data/lottery_history.csv",
    "data/lottery_history.csv",
]

def sync_file(src_dir, dst_dir, filename):
    """单向同步文件"""
    src = os.path.join(src_dir, filename)
    dst = os.path.join(dst_dir, filename)
    if os.path.exists(src):
        dst_parent = os.path.dirname(dst)
        if dst_parent and not os.path.exists(dst_parent):
            os.makedirs(dst_parent, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"  OK {filename}")
        return True
    return False

def sync_both_directions():
    print("=" * 50)
    print("  Antigravity 双向同步开始")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    synced_count = 0

    # Work -> 享中
    print("\n[OUT] Antigravity_Work -> 享中:")
    for f in CORE_FILES + DATA_FILES:
        if sync_file(WORK_DIR, Xiang_DIR, f):
            synced_count += 1

    # 享中 -> Work (反向同步)
    print("\n[IN] 享中 -> Antigravity_Work:")
    for f in CORE_FILES + DATA_FILES:
        if sync_file(Xiang_DIR, WORK_DIR, f):
            synced_count += 1

    print(f"\n{'=' * 50}")
    print(f"  Sync complete: {synced_count} files")
    print(f"{'=' * 50}")

if __name__ == "__main__":
    sync_both_directions()
