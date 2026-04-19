import pandas as pd

def migrate_autoresearch_data():
    source_path = r"D:\Antigravity_V7\data\ssq_history_full.csv"
    target_path = r"E:\享中\ssq_history_full.csv"
    
    print(">>> [Data ETL] 正在清洗并摄取 Autoresearch 的全量物理基石...")
    df_raw = pd.read_csv(source_path)
    
    col_id = df_raw.columns[0]
    col_date = df_raw.columns[15]
    
    df_clean = pd.DataFrame()
    # 转换为数值，遇到 "双色球开奖" 这种就变 NaN
    numeric_ids = pd.to_numeric(df_raw[col_id], errors='coerce')
    valid_idx = numeric_ids.dropna().index
    
    # 提取纯净数据
    df_valid = df_raw.loc[valid_idx].copy()
    numeric_ids = numeric_ids.loc[valid_idx]
    
    def fix_id(x):
        s = str(int(x))
        if len(s) == 5: return int("20" + s)
        elif len(s) == 6 and s.startswith("0"): return int("20" + s) # 03001 -> 2003001
        elif len(s) == 7: return int(s)
        return int(s)
        
    df_clean['id'] = numeric_ids.apply(fix_id)
    df_clean['r1'] = pd.to_numeric(df_valid[df_raw.columns[1]], errors='coerce').astype(pd.Int64Dtype())
    df_clean['r2'] = pd.to_numeric(df_valid[df_raw.columns[2]], errors='coerce').astype(pd.Int64Dtype())
    df_clean['r3'] = pd.to_numeric(df_valid[df_raw.columns[3]], errors='coerce').astype(pd.Int64Dtype())
    df_clean['r4'] = pd.to_numeric(df_valid[df_raw.columns[4]], errors='coerce').astype(pd.Int64Dtype())
    df_clean['r5'] = pd.to_numeric(df_valid[df_raw.columns[5]], errors='coerce').astype(pd.Int64Dtype())
    df_clean['r6'] = pd.to_numeric(df_valid[df_raw.columns[6]], errors='coerce').astype(pd.Int64Dtype())
    df_clean['b'] = pd.to_numeric(df_valid[df_raw.columns[7]], errors='coerce').astype(pd.Int64Dtype())
    df_clean['date'] = df_valid[col_date]
    
    df_clean = df_clean.dropna(subset=['r1', 'b'])
    
    # 手动补偿刚才我用 MCP 抓取的 040 期
    df_clean.loc[len(df_clean)] = [int(2026040), 3, 4, 14, 22, 23, 33, 4, '2026-04-12']
    
    df_clean = df_clean.sort_values('id').reset_index(drop=True)
    df_clean.to_csv(target_path, index=False)
    print(f">>> [Data ETL] 成功清洗 {len(df_clean)} 条全量记录，最新至 {df_clean.iloc[-1]['id']} 期，已注入矩阵！")

if __name__ == "__main__":
    migrate_autoresearch_data()
