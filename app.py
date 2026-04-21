import openai
import pandas as pd
import time
import os
import streamlit as st
import concurrent.futures
from kaggle_sync import sync_latest_data  # 保留你的同步功能

# --- 1. 配置区：升级为 OpenRouter 统帅 Key ---
OR_KEY = "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"
client = openai.OpenAI(
    api_key=OR_KEY,
    base_url="https://openrouter.ai/api/v1"
)

# --- 2. 核心：多模型联合作战矩阵 ---
def matrix_audit_logic(data_info):
    # 定义参谋部成员
    models = {
        "逻辑官-Claude 3.5": "anthropic/claude-3-5-sonnet",
        "概率计算器-DeepSeek": "deepseek/deepseek-chat",
        "架构师-Gemini Pro": "google/gemini-pro-1.5"
    }

    def fetch_prediction(name, m_id):
        try:
            resp = client.chat.completions.create(
                model=m_id,
                messages=[
                    {"role": "system", "content": f"你现在是反重力作战部队的{name}。核心课题：时间并不存在。"},
                    {"role": "user", "content": f"基于最新数据：\n{data_info}\n推演 043 期。"}
                ],
                temperature=0.1
            )
            return name, resp.choices[0].message.content
        except Exception as e:
            return name, f"❌ 链路波动: {str(e)}"

    # 真正的并发点火：5个通道同时开启
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(fetch_prediction, n, i) for n, i in models.items()]
        return {n: r for n, r in [f.result() for f in futures]}

# --- 3. 主推演函数：逻辑重构 ---
def run_low_pressure_audit():
    st.write(">>> 🚀 正在锁定 043 期时空坐标，多模型矩阵点火中...")
    
    try:
        # --- 数据补给逻辑 (保留原版) ---
        remote_path = sync_latest_data()
        target_path = remote_path if remote_path and os.path.exists(remote_path) else "lottery_history.csv"
        
        if os.path.exists(target_path):
            st.success(f"✅ 数据链路已锁定: {target_path}")
            df = pd.read_csv(target_path).tail(15) # 稍微增加点深度
            data_info = df.to_string()
        else:
            st.error("❌ 找不到历史数据文件！")
            return

        # --- 并发审计 (核心升级) ---
        start_time = time.time()
        with st.spinner("⏳ 正在跨维度征询所有模型意见 (不再死等 70s)..."):
            all_results = matrix_audit_logic(data_info)
        
        # --- 结果展示区 (UI 升级) ---
        st.balloons() 
        st.markdown("## 🔥 043 期多模型对冲审计报告")
        
        # 将结果并排展示或折叠展示
        for name, res in all_results.items():
            with st.expander(f"📊 点击查看 【{name}】 的深度推演"):
                st.write(res)
        
        # 结果存入本地 (保留原版习惯)
        with open("latest_predictions.csv", "w", encoding="utf-8") as f:
            f.write(f"period,audit_results\n2026043,\"{str(all_results)[:500]}\"")

        st.success(f"✅ 矩阵推演完成！总耗时: {int(time.time() - start_time)}s")

    except Exception as e:
        st.error(f"❌ 统帅部反馈异常: {e}")

# --- 4. Streamlit UI 入口 ---
if __name__ == "__main__":
    st.set_page_config(page_title="反重力·时空审计中心", layout="wide")
    st.title("🛸 反重力 V7.0 - 多模型联合作战部队")
    
    if st.button("🚀 执行 043 期多模型矩阵推演"):
        run_low_pressure_audit()
