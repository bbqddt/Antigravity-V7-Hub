import os
import pandas as pd
import numpy as np
from pathlib import Path

# 计算逻辑重心偏离分析
CENTROID = np.array([8.57, 8.57, 8.57])

def analyze_deviation(csv_path=None):
    """自动检测数据路径并分析重心偏离"""
    _ROOT = Path(__file__).resolve().parent
    if csv_path is None:
        # 自动搜索数据文件
        candidates = [
            _ROOT / "data" / "ssq_history.csv",
            _ROOT / "data" / "ssq_history_full.csv",
            _ROOT / "data" / "lottery_history.csv",
        ]
        for c in candidates:
            if c.exists():
                csv_path = str(c)
                break
        if csv_path is None:
            print("❌ 未找到数据文件，请提供路径")
            return

    print(f"📊 正在分析: {csv_path}")
    df = pd.read_csv(csv_path)

    # 获取最新一期
    last_row = df.iloc[-1]

    # 计算最新一期的空间坐标
    def get_coords(row):
        z = row.iloc[-1]
        x = row.iloc[-7:-4].mean()
        y = row.iloc[-4:-1].mean()
        return np.array([x, y, z])

    current_pos = get_coords(last_row)
    offset = CENTROID - current_pos

    print(f"\n[偏离值分析] 当前期偏离重心: {offset}")
    print("-" * 40)

    if np.linalg.norm(offset) > 2:
        print("结论：当前逻辑场处于不平衡态，下一期号码极大概率会向重心的反方向补全。")
    else:
        print("结论：当前逻辑场处于平衡态，下一期可能出现常规波动。")

    # 建议目标坐标
    suggested_pos = CENTROID + offset * 0.5
    print(f"\n[建议目标坐标]: {suggested_pos}")

if __name__ == "__main__":
    analyze_deviation()
