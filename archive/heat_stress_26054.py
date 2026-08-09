# -*- coding: utf-8 -*-
"""
Antigravity 热点压力测试内核
通过特征交叉，锁定目标期红球的"能量高地"
"""
import pandas as pd
import numpy as np
import json
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_heat_stress(period="26054"):
    print(f"[STRESS] Starting {period} Red Ball Heat Stress Analysis...")

    # 1. 加载历史真理
    csv_path = _PROJECT_ROOT / "data" / "lottery_history.csv"
    if not csv_path.exists():
        print(f"[ERROR] 数据文件不存在: {csv_path}")
        return None

    df = pd.read_csv(str(csv_path))
    all_reds = []
    for r in df['red']:
        all_reds.extend(list(map(int, r.split(','))))

    # 2. 局部热点分析 (最近 100 期)
    recent_reds = []
    for r in df.head(100)['red']:
        recent_reds.extend(list(map(int, r.split(','))))

    # 3. 权重修正
    weights = np.ones(34)  # 0-33
    weights[1] *= 1.25   # 01 权重增强
    weights[31] *= 1.25  # 31 权重增强
    weights[11] *= 1.1   # 中位重复权重

    # 4. 模拟推演 (基于频率+权重)
    counts = np.bincount(recent_reds, minlength=34)
    prob_dist = (counts / counts.sum()) * weights

    # 5. 锁定 Top 10 热点
    hot_spots = np.argsort(prob_dist)[-10:]
    results = {
        "period": period,
        "hot_spots": [int(x) for x in sorted(hot_spots)],
        "heat_scores": {int(i): float(prob_dist[i]) for i in hot_spots}
    }

    # 保存结果
    output_path = _PROJECT_ROOT / f"red_heat_{period}.json"
    with open(str(output_path), "w") as f:
        json.dump(results, f, indent=4)

    print(f"[SUCCESS] {period} Hot Spots: {results['hot_spots']}")

    return results


if __name__ == "__main__":
    run_heat_stress()
