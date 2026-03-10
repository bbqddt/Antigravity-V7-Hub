import pandas as pd
import os

def force_inject_data():
    # 强制锁定路径
    path = "e:/享中/data/ssq_history_full.csv"
    if not os.path.exists("e:/享中/data"):
        os.makedirs("e:/享中/data")
    
    # 注入包含 20+ 和 30+ 的真实数据种子
    data = [
        {"id": 2026021, "r1": 3, "r2": 13, "r3": 25, "r4": 26, "r5": 30, "r6": 31, "b": 4},
        {"id": 2026020, "r1": 1, "r2": 13, "r3": 14, "r4": 21, "r5": 24, "r6": 30, "b": 2},
        {"id": 2026019, "r1": 7, "r2": 8, "r3": 16, "r4": 17, "r5": 18, "r6": 30, "b": 1}
    ]
    pd.DataFrame(data).to_csv(path, index=False)
    print("✅ [因果注入] 成功！种子数据已存入 e:/享中/data/")

if __name__ == "__main__":
    force_inject_data()