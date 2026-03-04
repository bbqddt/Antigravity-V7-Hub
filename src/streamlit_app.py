import streamlit as st
import pandas as pd
import os

# --- 强制物理溯源逻辑 ---
def load_mcp_data():
    # 强制读取同目录下的物理档案
    file_path = "src/history_data.csv"
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return None

st.title("🛰️ V7 物理对齐中枢 (Core版)")

df = load_mcp_data()

if df is not None:
    # 这里的数据将严格等于您在 history_data.csv 里填写的 01,03,08...
    st.success(f"✅ 已连接 GitHub 物理库 | 最新期号: {df.iloc[0]['期号']}")
    
    st.subheader("📊 真实对照查询")
    search = st.text_input("输入期号 (如 2026023)")
    
    if search:
        res = df[df['期号'].astype(str) == search]
        st.table(res) # 这样出来的就是 01,03,08...
    else:
        st.dataframe(df, use_container_width=True)
else:
    st.error("🚨 找不到物理库文件！")
