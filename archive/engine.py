# -*- coding: utf-8 -*-
"""
engine.py - Antigravity Force Sync Module
强制同步：对齐最新开奖数据并生成预测
"""
import os
import json
import random
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def force_sync():
    """
    强制同步：对齐最新开奖数据并生成预测
    从 data/lottery_history.csv 读取最新开奖，生成下一期预测
    """
    csv_path = os.path.join(BASE_DIR, "data", "lottery_history.csv")

    # 读取最新一期真实开奖
    if os.path.exists(csv_path):
        import pandas as pd
        df = pd.read_csv(csv_path)
        last_row = df.iloc[-1]
        latest_period = int(last_row.get('period', 0))
        latest_reds = [int(x.strip()) for x in str(last_row.get('red', '')).split(',')]
        latest_blue = int(last_row.get('blue', 0))
        print(f"✅ 已对齐最新开奖 #{latest_period}: {sorted(latest_reds)} + {latest_blue:02d}")
    else:
        latest_period = 26069
        latest_reds = [12, 14, 16, 17, 18, 32]
        latest_blue = 8
        print(f"⚠️ 未找到数据文件，使用默认值")

    # 生成下一期预测
    next_period = latest_period + 1
    predictions = []
    for _ in range(5):
        predictions.append({
            "agent": "Engine Core",
            "reds": sorted(random.sample(range(1, 34), 6)),
            "blue": random.randint(1, 16),
            "status": "Calculated"
        })

    # 封装全量情报包
    payload = {
        "metadata": {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "next_target": str(next_period),
            "engine_log": "V18.5_FORCE_ALIGNED"
        },
        "real_draw": {
            "period": str(latest_period),
            "reds": latest_reds,
            "blue": latest_blue
        },
        "predictions": predictions
    }

    output_path = os.path.join(BASE_DIR, "latest_decision.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=4)
    print(f"✅ 情报库已物理重置！下期目标: #{next_period}")


if __name__ == "__main__":
    force_sync()
