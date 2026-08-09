# ==========================================
# Antigravity V18: NemoClaw 级智能体架构
# ==========================================
import streamlit as st
import pandas as pd
import requests
import json
import random
import re
import collections
import os
import time

# --- [1. 初始化 NemoClaw 级作用域与缓存] ---
# 彻底废除局部 nonlocal Binding 陷阱，改用 st.session_state 缓存
if "audit_log_buf" not in st.session_state:
    st.session_state.audit_log_buf = []

# --- [2. NemoClaw 资源库Skill库] ---
# 核心凭据：您的新 KEY
API_KEY = os.environ.get("GEMINI_API_KEY", "")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

# 物理隧道：死锁 Netch 的 2801 (SOCKS5h)
PROXIES = {
    "http": "socks5h://127.0.0.1:2801",
    "https": "socks5h://127.0.0.1:2801"
}

# --- [3. Agent/Workflow 定义] ---
class NemoClawCore:
    def __init__(self):
        self.data_path = r"D:\Antigravity_V7\data\lottery_history.csv"
        self.output_path = r"D:\Antigravity_V7\latest_predictions.csv"
    
    # [Agent Skill]: 本地冷热号物理推演
    def local_physical_audit(self):
        st.session_state.audit_log_buf.append("🟢 [Audit Agent]: 激活 Skill_LocalPhysics 推演...")
        if not os.path.exists(self.data_path): return []
        
        df = pd.read_csv(self.data_path).tail(50)
        # 频率统计核心逻辑
        all_reds = []
        for i in range(1, 7): all_reds.extend(df.iloc[:, i].tolist())
        hot_reds = [num for num, _ in collections.Counter(all_reds).most_common(12)]
        
        selected_reds = sorted(random.sample(hot_reds, 6))
        blue = df.iloc[:, 7].value_counts().idxmax()
        line = f"{' '.join([f'{x:02d}' for x in selected_reds])} | {blue:02d}"
        return [line]

    # [Workflow]: 网络穿透审计
    def workflow_online_audit(self):
        st.session_state.audit_log_buf.append(f"🟢 [Audit Workflow]: 通过 2801 隧道尝试 LLM 注入...")
        if not os.path.exists(self.data_path): return None

        df = pd.read_csv(self.data_path).tail(10)
        payload = {"contents": [{"parts":[{"text": f"推演 033 期：\n{df.to_string()}"}]}]}
        
        try:
            # 执行 Skill_Request: 通过 2801 代理发送 POST
            res = requests.post(URL, json=payload, proxies=PROXIES, timeout=30)
            
            # 捕获 429 封锁 IP 或 KEY 无效错误
            if res.status_code == 429:
                st.session_state.audit_log_buf.append("💥 [Status]: 隧道 2801 出口 IP 被封锁 (429)！")
                st.session_state.audit_log_buf.append("👉 [Connect Agent]: 准备Skill_Connect_Switch，切换 v2rayN 节点...")
                return None # 标记在线失败

            res.raise_for_status()
            candidates = res.json().get("candidates", [])
            if candidates:
                # 强大的正则解析 Skill，清洗结果
                final_text = candidates[0]["content"]["parts"][0]["text"]
                return re.findall(r"(\d{2}\s+\d{2}\s+\d{2}\s+\d{2}\s+\d{2}\s+\d{2})\s*\|\s*(\d{2})", final_text)
        except Exception as e:
            st.session_state.audit_log_buf.append(f"❌ [Error]: 网络层握手失败：{e}")
        return None

    # [Workflow]: 战术转进与合龙
    def final_closeout(self, results):
        if not results: return
        
        formatted = [" ; ".join([f"{r} | {b}" for r, b in results])]
        # 写入 CSV 的 Skill
        try:
            with open(self.output_path, "w", encoding="utf-8") as f:
                f.write("period,audit_results\n")
                f.write(f"2026033,\"{formatted[0]}\"")
            st.session_state.audit_log_buf.append("✨✨✨ [目标达成] 033 期数据已通过本地/在线机制强制合龙！")
        except Exception as e:            st.session_state.audit_log_buf.append(f'Error: {e}')
