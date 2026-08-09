# -*- coding: utf-8 -*-
"""
hermes_agent.py - Antigravity Core Auditor
Hermes 审计逻辑：强制对比真实物理坐标
"""
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def audit_data(predictions, truth_source=None):
    """
    Hermes 审计逻辑：强制对比真实物理坐标
    Args:
        predictions: 预测数据列表，每项包含 reds 和 blue
        truth_source: 真实数据CSV路径（默认自动检测）
    """
    if truth_source is None:
        truth_source = os.path.join(BASE_DIR, "data", "lottery_history.csv")

    if not os.path.exists(truth_source):
        print(f"[Hermes] 警告：未发现历史数据库 {truth_source}")
        return None

    import pandas as pd
    df = pd.read_csv(truth_source)
    if df.empty:
        print("[Hermes] 警告：数据源为空")
        return None

    # 获取最新一期真实数据
    last_row = df.iloc[-1]
    red_str = last_row.get('red', '')
    actual_reds = [int(x.strip()) for x in str(red_str).split(',')] if red_str else []
    actual_blue = last_row.get('blue', 0)

    print(f"[Hermes] 正在执行物理对齐校验...")
    print(f"[Hermes] 真实开奖: 红 {actual_reds} | 蓝 {actual_blue}")

    if predictions:
        for pred in predictions:
            pred_reds = set(pred.get('reds', []))
            pred_blue = pred.get('blue')
            hit_reds = pred_reds & set(actual_reds)
            hit_blue = (pred_blue == actual_blue)
            print(f"[Hermes] 预测: {sorted(pred_reds)} + {pred_blue} | 红球命中: {len(hit_reds)}, 蓝球{'OK' if hit_blue else 'MISS'}")

    return True


if __name__ == "__main__":
    audit_data([])
