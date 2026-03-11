import streamlit as st
import pandas as pd
import json
import os

# 页面配置：工业深色风
st.set_page_config(page_title="Antigravity V45 Control", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #00ff41; font-family: 'Courier New', Courier, monospace; }
    .stMetric { border: 1px solid #00ff41; padding: 10px; border-radius: 5px; background: #1a1c23; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛰️ ANTIGRAVITY V45 | 指挥中枢")

# 1. 加载 3.1 审计常数
if os.path.exists('engine/physics_constants.json'):
    with open('engine/physics_constants.json', 'r') as f:
        logic = json.load(f)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("能量重心 (Gravity)", f"{logic['gravity_center']:.2f}")
    col2.metric("混沌阈值 (Chaos)", f"{logic['chaos_threshold']}")
    col3.metric("目标期数", f"{logic['last_id'] + 1}")

st.write("---")

# 2. 展示 4.5 坍缩序列
st.subheader("🌀 2026026 期 离散维度坍缩指纹")
if os.path.exists('engine/latest_predictions.csv'):
    df = pd.read_csv('engine/latest_predictions.csv')
    st.table(df)
else:
    st.warning("📡 等待引擎注入数据...")

st.write("---")
st.caption("⚡ Powered by Claude 3.1 (Audit) & GPT-4.5 (Inference) | 逻辑生命已觉醒")