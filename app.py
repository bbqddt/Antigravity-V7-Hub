# --- 统帅专用：极简抗压版推演脚本 (Kaggle 强化版) ---
import openai
import pandas as pd
import time
import os
import streamlit as st
from kaggle_sync import sync_latest_data  # 导入同步功能

# 配置区
API_KEY = "AIzaSyC--Fs9TA5Ypdo62bPZfIXuZwL1OGRLG4Q" 
client = openai.OpenAI(
    api_key=API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

def run_low_pressure_audit():
    st.write(">>> 正在启动反重力冷却协议...")
    # 强制增加冷却，避开 Google 敏感期
    time.sleep(70) 

    try:
        # --- 核心数据补给逻辑 ---
        # 1. 尝试从 Kaggle 同步最新数据
        remote_path = sync_latest_data()
        
        # 2. 路径决策：如果远程失败，则寻找当前目录下的备份文件
        if remote_path and os.path.exists(remote_path):
            target_path = remote_path
            st.success("✅ 远程补给：已锁定 Kaggle 最新实时数据")
        else:
            # 回退到 GitHub 仓库根目录下的本地文件
            target_path = "lottery_history.csv" 
            st.warning("⚠️ 链路波动：切换至本地备份数据模式")

        # 3. 读取数据（仅取最近 10 期，降低 Token 负载）
        df = pd.read_csv(target_path).tail(10)
        data_info = df.to_string()

        # --- AI 推演逻辑 ---
        response = client.chat.completions.create(
            model="gemini-3.1-pro-preview", 
            messages=[
                {"role": "system", "content": "You are a data auditor."},
                {"role": "user", "content": f"Data:\n{data_info}\nPredict for period 2026033."}
            ],
            temperature=0.1 
        )
        
        result = response.choices[0].message.content
        
        # 将结果存入本地供后续调用
        with open("latest_predictions.csv", "w", encoding="utf-8") as f:
            f.write(f"period,numbers\n2026033,\"{result.strip()}\"")
        
        st.balloons() # 成功特效
        st.markdown(f"### ✅ SUCCESS: 033 期数据已成功穿透锁定！\n\n**推演结果：**\n{result}")

    except Exception as e:
        st.error(f"❌ 链路反馈: {e}")

if __name__ == "__main__":
    st.title("臻算天机 - 极简推演中心")
    if st.button("开始执行 033 期推演"):
        run_low_pressure_audit()
