import pandas as pd
import numpy as np
import os

# 指向你的实际数据路径
FILE_PATH = 'data/ssq_history.csv'

def run_zero_t_analysis(csv_path=None):
    """Project Zero-T: 静态逻辑重心分析"""
    if csv_path is None:
        # 自动搜索
        candidates = [
            'data/ssq_history.csv',
            'data/ssq_history_full.csv',
            'data/lottery_history.csv',
        ]
        for c in candidates:
            if os.path.exists(c):
                csv_path = c
                break
        if csv_path is None:
            print(f"错误：没找到 {csv_path}，请检查 data 文件夹。")
            return

    print(f"📊 正在分析: {csv_path}")
    df = pd.read_csv(csv_path)

    # 彻底打乱数据顺序，抹除线性时间干扰
    df_shuffled = df.sample(frac=1).reset_index(drop=True)

    # 动态检测列数，防止越界
    total_cols = df_shuffled.shape[1]
    print(f"\n[检测] 你的数据共有 {total_cols} 列")

    # 尝试提取坐标：假设最后一列是蓝球，倒数第2-7列是红球
    coords = pd.DataFrame()
    try:
        # Z轴设定为最后一列（通常是蓝球）
        coords['Z'] = df_shuffled.iloc[:, -1]

        # X轴为红球前段（倒数第7到第5列）
        coords['X'] = df_shuffled.iloc[:, -7:-4].mean(axis=1)

        # Y轴为红球后段（倒数第4到第2列）
        coords['Y'] = df_shuffled.iloc[:, -4:-1].mean(axis=1)

        print("\n" + "=" * 40)
        print("   Project Zero-T: 静态逻辑重心分析")
        print("=" * 40)
        print(f"分析样本总量: {len(df)} 期")

        # 计算静态重心
        centroid = coords.mean()
        print(f"\n当前逻辑重心 (Static Centroid):")
        print(f"X (红球前段轴): {centroid['X']:.4f}")
        print(f"Y (红球后段轴): {centroid['Y']:.4f}")
        print(f"Z (蓝球平衡轴): {centroid['Z']:.4f}")
        print("-" * 40)

        # 计算熵值
        entropy = coords.std().mean()
        print(f"场域稳定熵值: {entropy:.4f}")
        print("=" * 40)
        print("只要这组数稳定，'未来'就是可计算的逻辑占位。")

    except Exception as e:
        print(f"分析失败：{e}")
        print("请检查 CSV 内容是否包含足够的号码列。")

if __name__ == "__main__":
    run_zero_t_analysis()
