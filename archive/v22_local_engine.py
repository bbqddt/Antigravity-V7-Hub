# -*- coding: utf-8 -*-
"""
V22 Local Engine — 离线统计分析引擎

修复：
1. 路径改为相对项目根目录
2. 自动搜索数据文件
"""
import pandas as pd
from collections import Counter
import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent


def local_analyze(csv_path=None):
    if csv_path is None:
        # 自动搜索数据文件
        candidates = [
            _PROJECT_ROOT / "data" / "lottery_history.csv",
            _PROJECT_ROOT / "data" / "ssq_history.csv",
            _PROJECT_ROOT / "data" / "ssq_history_full.csv",
        ]
        for c in candidates:
            if c.exists():
                csv_path = str(c)
                break
        if csv_path is None:
            print("❌ 警报：找不到数据文件！请先手动创建 lottery_history.csv")
            return

    print("📊 正在启动本地 ANTIGRAVITY 统计引擎...")
    df = pd.read_csv(csv_path)

    # 提取所有红球（兼容多种列名）
    red_col = '红球' if '红球' in df.columns else 'red'
    all_reds = []
    for balls in df[red_col]:
        if isinstance(balls, str):
            # 逗号分隔格式
            parts = [x.strip() for x in balls.split(',')]
            all_reds.extend(parts)
        elif isinstance(balls, list):
            all_reds.extend(str(balls).split())

    # 计算频率
    red_counts = Counter(all_reds)
    most_common = [num for num, count in red_counts.most_common(6)]

    blue_col = '蓝球' if '蓝球' in df.columns else 'blue'
    print(f"\n--- ⚡ 离线分析报告 ⚡ ---")
    print(f"🔹 已载入样本期数: {len(df)}")
    print(f"🔹 近期热点红球: {' '.join(most_common)}")
    if len(df) > 0 and blue_col in df.columns:
        print(f"🔹 建议关注蓝球: {df[blue_col].iloc[0]} (遗漏回补逻辑)")
    print("------------------------")


if __name__ == "__main__":
    local_analyze()
