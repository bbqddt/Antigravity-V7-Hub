import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Antigravity V12.8 - 指挥部", layout="wide")

DATA_PATH = 'data/ssq_history_full.csv'

st.title("🌀 Antigravity 四位一体中枢 - 2026026 专项")

if os.path.exists(DATA_PATH):
    df = pd.read_csv(DATA_PATH)
    total = len(df)
    st.success(f"🟢 因果基石已锁定：{total} 期 (最新数据已进化)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔥 红球热度分布 (Top 10)")
        # 统计最近 100 期的频率
        recent_reds = df.iloc[-100:][['r1','r2','r3','r4','r5','r6']].values.flatten()
        red_counts = pd.Series(recent_reds).value_counts().head(10)
        st.bar_chart(red_counts)

    with col2:
        st.subheader("🎯 2026026 逻辑演化建议")
        last_blue = df.iloc[-1]['blue']
        st.info(f"上期蓝球：{last_blue} | 判定：11 强排斥")
        st.write("逻辑位移：10, 05, 16")
        st.warning("一区（01-11）目前处于能量真空，警惕断区！")

else:
    st.error("🔴 物理断联：请检查 data/ 目录下的 CSV 文件是否已推送。")