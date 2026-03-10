import pandas as pd
import os

# 1. 强行锁定路径
csv_path = 'data/ssq_history_full.csv'

if not os.path.exists(csv_path):
    print(f"🔴 物理层错误：找不到文件 {csv_path}")
else:
    df = pd.read_csv(csv_path)
    # 2. 锁定 10 和 11 的因果位移
    target_range = df.tail(100)
    
    # 找到最后一次出现的索引
    last_11 = df[df.iloc[:, -1] == 11].index.max()
    last_10 = df[df.iloc[:, -1] == 10].index.max()
    
    current_idx = len(df)
    
    print("-" * 30)
    print(f"📊 ANTIGRAVITY 核心审计 (数据至 {current_idx} 期)")
    print(f"🔹 蓝球 11 当前遗漏: {current_idx - last_11} 期")
    print(f"🔹 蓝球 10 当前遗漏: {current_idx - last_10} 期")
    print(f"🔹 场强判研: {'11 处于高频释放场' if (current_idx - last_11) < (current_idx - last_10) else '10 处于坍缩边缘'}")
    print("-" * 30)