# -*- coding: utf-8 -*-
"""
Antigravity Auto Pipeline — 奖惩结算 + 组件归档

修复：
1. 所有硬编码路径改为相对路径
2. 使用 pathlib.Path 统一管理
3. 归档目录可配置
"""
import os
import json
import time
import glob
import shutil
from pathlib import Path
from datetime import datetime

import pandas as pd

# ─── 相对路径 ─────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent
DATA_FILE = _PROJECT_ROOT / "data" / "lottery_history.csv"
STATE_FILE = _PROJECT_ROOT / "evolution_state.json"
PRED_FILE = _PROJECT_ROOT / "latest_predictions_evolved.json"
ARCHIVE_DIR = _PROJECT_ROOT / "_archive"


def apply_reward_punishment():
    print(">>> 启动奖惩结算协议...")
    if not PRED_FILE.exists() or not STATE_FILE.exists():
        print("未找到上一期预测文件或状态文件，跳过结算。")
        return

    with open(PRED_FILE, 'r', encoding='utf-8') as f:
        preds = json.load(f)
    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        state = json.load(f)

    target_period = preds.get("target_period")
    df = pd.read_csv(str(DATA_FILE))
    actual_row = df[df["period"] == target_period]

    if actual_row.empty:
        print(f"数据尚未更新至 {target_period} 期，无法结算。")
        return

    if state.get("last_period_evaluated") >= target_period:
        print(f"第 {target_period} 期已结算过，跳过。")
        return

    # 提取真实结果
    actual_reds = set([int(x) for x in str(actual_row.iloc[0]["red"]).split(",")])
    actual_blue = int(actual_row.iloc[0]["blue"])

    print(f"[{target_period} 期] 真实开奖: 红 {sorted(actual_reds)} | 蓝 {actual_blue}")

    # 计分与奖惩
    for group in preds.get("predictions", []):
        strat = group["strategy"]
        pred_reds = set(group["reds"])
        pred_blue = group["blue"]

        red_hits = len(pred_reds & actual_reds)
        blue_hit = 1 if pred_blue == actual_blue else 0

        reward = (red_hits * 0.1) + (blue_hit * 0.3)
        if red_hits == 0 and not blue_hit:
            reward = -0.1  # 惩罚

        if strat in state["strategies"]:
            state["strategies"][strat]["weight"] += reward
            state["strategies"][strat]["total_hits"] += red_hits
            state["strategies"][strat]["usage_count"] += 1

            # 保底权重
            state["strategies"][strat]["weight"] = max(0.1, state["strategies"][strat]["weight"])
            print(f"策略 [{strat}] -> 命中红 {red_hits} 蓝 {blue_hit} | 权重变动: {reward:+.2f} -> 当前权重: {state['strategies'][strat]['weight']:.2f}")

    state["last_period_evaluated"] = target_period
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def punish_dead_components():
    print("\n>>> 启动组件监工 (Component Punisher)...")
    # 扫描目录下所有的 py 文件
    py_files = glob.glob(str(_PROJECT_ROOT / "*.py"))
    active_core_files = [
        "evolved_predictor.py", "auto_pipeline.py", "engine.py",
        "manual_sync.py", "mcp_harvester.py",
        "enhanced_predictor.py", "omni_strike_v8.py",
        "commander_bot.py", "local_api_proxy.py",
        "cloud_deploy.py", "backtest_and_evolve.py",
    ]

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archived = []

    for filepath in py_files:
        filename = os.path.basename(filepath)
        if filename not in active_core_files:
            # 判断文件最后修改时间，超过 30 天未修改则视为光吃饭不干活
            mtime = os.path.getmtime(filepath)
            days_inactive = (time.time() - mtime) / (24 * 3600)
            if days_inactive > 30:
                archived.append((filename, days_inactive))

    if archived:
        print("发现以下低效僵尸组件，执行归档隔离:")
        for fname, days in archived:
            src = _PROJECT_ROOT / fname
            dst = ARCHIVE_DIR / (fname + "." + time.strftime("%Y%m%d"))
            try:
                shutil.move(str(src), str(dst))
                print(f" [归档] {fname} -> _archive/ (连续 {days:.0f} 天未活跃)")
            except OSError:
                pass
    else:
        print("所有核心组件均处于活跃状态。")


if __name__ == "__main__":
    apply_reward_punishment()
    punish_dead_components()
    print("\n流水线执行完毕。下一步请运行 evolved_predictor.py 生成最新预测。")
