# -*- coding: utf-8 -*-
"""
ETL History — 数据迁移/清洗工具

修复：
1. 不再硬编码 D:\\Antigravity_V7 路径
2. 支持多种输入格式
3. 手动数据补偿已移除（应使用 data_updater_v2.py 自动同步）
"""
import pandas as pd
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent


def migrate_autoresearch_data(source_path=None, target_path=None):
    """
    清洗并迁移双色球历史数据

    Args:
        source_path: 源数据文件路径（可选，默认自动搜索）
        target_path: 目标数据文件路径（可选，默认 data/ssq_history_full.csv）
    """
    if source_path is None:
        # 自动搜索源数据
        candidates = [
            _PROJECT_ROOT / "data" / "ssq_history_full.csv",
            _PROJECT_ROOT / "data" / "lottery_history.csv",
            _PROJECT_ROOT / "ssq_history_full.csv",
        ]
        for c in candidates:
            if c.exists():
                source_path = str(c)
                break
        if source_path is None:
            print("❌ 未找到源数据文件")
            return

    if target_path is None:
        target_path = str(_PROJECT_ROOT / "data" / "ssq_history_full.csv")

    print(f">>> [Data ETL] 正在清洗数据: {source_path}")

    try:
        df_raw = pd.read_csv(source_path)
        print(f"   原始行数: {len(df_raw)}")
        print(f"   列名: {list(df_raw.columns)}")

        # 尝试标准化为 period, red, blue, date 格式
        if 'period' in df_raw.columns:
            # 已经是标准格式
            df_clean = df_raw[['period', 'red', 'blue', 'date']].copy()
            df_clean.columns = ['period', 'red', 'blue', 'date']
        elif 'id' in df_raw.columns:
            # V7 flat 格式
            df_clean = pd.DataFrame()
            df_clean['id'] = pd.to_numeric(df_raw['id'], errors='coerce')
            for i in range(1, 7):
                col = f'r{i}' if f'r{i}' in df_raw.columns else df_raw.columns[i]
                df_clean[f'r{i}'] = pd.to_numeric(df_raw[col], errors='coerce')
            b_col = 'b' if 'b' in df_raw.columns else df_raw.columns[7]
            df_clean['b'] = pd.to_numeric(df_raw[b_col], errors='coerce')
            if 'date' in df_raw.columns:
                df_clean['date'] = df_raw['date']

            df_clean = df_clean.dropna(subset=['r1', 'b'])
            df_clean = df_clean.sort_values('id').reset_index(drop=True)
        else:
            print("❌ 无法识别的数据格式")
            return

        # 保存
        pd.DataFrame(df_clean).to_csv(target_path, index=False)
        print(f">>> [Data ETL] 清洗完成: {len(df_clean)} 条记录 -> {target_path}")

    except Exception as e:
        print(f"❌ ETL 失败: {e}")


if __name__ == "__main__":
    migrate_autoresearch_data()
