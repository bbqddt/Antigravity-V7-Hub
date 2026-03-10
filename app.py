import streamlit as st
import pandas as pd
import os

# 强制指向我们刚 push 上去的数据路径
DATA_PATH = 'data/ssq_history_full.csv'

if os.path.exists(DATA_PATH):
    df = pd.read_csv(DATA_PATH)
    st.success(f"🟢 因果基石已锁定：当前数据已进化至 {len(df)} 期")
else:
    st.error("🔴 物理断联：云端未检测到 3510 期数据，请检查 Git Push 状态")