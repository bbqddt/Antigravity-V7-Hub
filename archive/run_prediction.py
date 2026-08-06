import pandas as pd
import random
from collections import Counter
import os

DATA_FILE = r"E:\享中\data/lottery_history.csv"

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

def main():
    print(">>> 正在启动极速推演核心...")
    df = pd.read_csv(DATA_FILE)
    
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
    
    strategies = [
        ("hot_core", "[Hot] 热号骨架+冷号回补"),
        ("hot_core", "[Hot] 热号骨架+冷号回补(变体)"),
        ("balanced", "[Bal] 热冷均衡策略"),
        ("cold_strike", "[Cold] 冷号反击策略"),
        ("balanced", "[Free] 自由覆盖组合"),
    ]
    
    print(f"\n=========================================")
    print(f"      Antigravity 最终防线推演结果 (5组)")
    print(f"=========================================\n")
    
    for i, (strat, desc) in enumerate(strategies, 1):
        reds, blue = generate_prediction(hot_reds, cold_reds, hot_blues, cold_blues, strategy=strat)
        red_str = ", ".join([f"{x:02d}" for x in reds])
        blue_str = f"{blue:02d}"
        print(f"组别 {i} [{desc}]:\n -> 红球: [{red_str}] | 蓝球: {blue_str}\n")

if __name__ == "__main__":
    main()
