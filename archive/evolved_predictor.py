# -*- coding: utf-8 -*-
"""
Antigravity 自我演进预测器 (Evolved Predictor)
基于动态权重策略池的多模式预测引擎
"""
import pandas as pd
import random
from collections import Counter
import os
import json
from pathlib import Path

# ─── 相对路径 ─────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent
DATA_FILE = _PROJECT_ROOT / "data" / "lottery_history.csv"
STATE_FILE = _PROJECT_ROOT / "evolution_state.json"
PRED_OUTPUT = _PROJECT_ROOT / "latest_predictions_evolved.json"

def generate_prediction(hot_reds, cold_reds, hot_blues, cold_blues, strategy="balanced"):
    pool = list(range(1, 34))
    if strategy == "hot_core" and hot_reds:
        base = random.sample(hot_reds, min(len(hot_reds), 3))
        available_cold = [x for x in cold_reds if x not in base]
        supplement = random.sample(available_cold, min(len(available_cold), 3)) if available_cold else []
        reds = sorted(set(base + supplement))
    elif strategy == "cold_strike" and cold_reds:
        base = random.sample(cold_reds, min(len(cold_reds), 4))
        available_hot = [x for x in hot_reds if x not in base]
        supplement = random.sample(available_hot, min(len(available_hot), 2)) if available_hot else []
        reds = sorted(set(base + supplement))
    else:
        sample_hot = random.sample(hot_reds, min(len(hot_reds), 3)) if hot_reds else []
        sample_cold = random.sample(cold_reds, min(len(cold_reds), 3)) if cold_reds else []
        reds = sorted(set(sample_hot + sample_cold))

    while len(reds) < 6:
        extra = random.choice([x for x in pool if x not in reds])
        reds.append(extra)
        reds = sorted(set(reds))
        
    blue = random.choice(cold_blues) if cold_blues else random.randint(1, 16)
    return reds[:6], blue

def load_weights():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
            return state.get("strategies", {}), state.get("last_period_evaluated", 0)
    return {
        "hot_core": {"weight": 1.0},
        "cold_strike": {"weight": 1.0},
        "balanced": {"weight": 1.0}
    }, 0

def select_strategies(weights_dict, total_groups=5):
    # Filter out dead strategies (weight <= 0.1)
    active = {k: max(0.1, v["weight"]) for k, v in weights_dict.items()}
    names = list(active.keys())
    w = list(active.values())
    
    selected = random.choices(names, weights=w, k=total_groups)
    return selected

def main():
    print(">>> [Evolved Predictor] 加载动态权重池...")
    weights, _ = load_weights()
    print("当前策略权重:", {k: round(v['weight'], 2) for k, v in weights.items()})
    
    df = pd.read_csv(str(DATA_FILE))
    latest_period = df['period'].max()
    target_period = latest_period + 1
    
    all_reds = []
    all_blues = []
    for _, row in df.head(30).iterrows():
        reds = [int(x) for x in str(row["red"]).split(",")]
        all_reds.extend(reds)
        all_blues.append(int(row["blue"]))
        
    red_freq = Counter(all_reds)
    blue_freq = Counter(all_blues)
    
    hot_reds = [k for k, v in red_freq.most_common(10)]
    cold_reds = [i for i in range(1, 34) if red_freq.get(i, 0) <= 1]
    hot_blues = [k for k, v in blue_freq.most_common(5)]
    cold_blues = [i for i in range(1, 17) if blue_freq.get(i, 0) <= 1]
    
    chosen_strats = select_strategies(weights, 5)
    
    print(f"\n=========================================")
    print(f"      Antigravity 自我演进系统 - 第 {target_period} 期")
    print(f"=========================================\n")
    
    results = []
    for i, strat in enumerate(chosen_strats, 1):
        reds, blue = generate_prediction(hot_reds, cold_reds, hot_blues, cold_blues, strategy=strat)
        red_str = ", ".join([f"{x:02d}" for x in reds])
        blue_str = f"{blue:02d}"
        print(f"组别 {i} [{strat}]:\n -> 红球: [{red_str}] | 蓝球: {blue_str}\n")
        results.append({
            "group": i,
            "strategy": strat,
            "reds": reds,
            "blue": blue
        })
        
    output_data = {
        "target_period": int(target_period),
        "predictions": results
    }
    with open(str(PRED_OUTPUT), 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"预测已保存至: {PRED_OUTPUT}")

if __name__ == "__main__":
    main()
