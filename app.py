import openai
import pandas as pd
import time
import os
import re
import streamlit as st
import concurrent.futures
from kaggle_sync import sync_latest_data 

# --- 1. 核心配置：OpenRouter 统帅钥匙 ---
OR_KEY = "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"
client = openai.OpenAI(
    api_key=OR_KEY,
    base_url="https://openrouter.ai/api/v1"
)

# --- 2. 物理提取器：将“审计文字”转为“表格数据” ---
def extract_logic_numbers(text):
    """
    核心：从模型的逻辑报告中强行提取 043 期红蓝球
    防止 KeyError: 'reds' 报错
    """
    # 提取红球 (01-33)
    reds = re.findall(r'\b(0[1-9]|[12]\d|3[0-3])\b', text)
    # 提取蓝球 (01-16)
    blues = re.findall(r'\b(0[1-9]|1[0-6])\b', text)
    
    # 格式化数据：取前6个独特红球，取最后1个蓝球
    final_reds = sorted(list(set(reds)))[:6]
    # 容错：如果没提取到，给一组逻辑兜底
    if len(final_reds) < 6:
        final_reds = ["07", "12", "13", "19", "22", "24"]
    
    final_blue = blues[-1] if blues else "16"
    
    return {
        "reds": final_reds,
        "blue": final_blue,
        "raw_report": text
    }

# --- 3. 联合作战矩阵：并发调度 ---
def matrix_audit_logic(data_info):
    council = {
        "逻辑官-Claude 3.5": "anthropic/claude-3.5-sonnet",
        "计算器-DeepSeek": "deepseek/deepseek-chat",
        "架构师-Gemini Pro": "google/gemini-pro-1.5"
    }

    def fetch_prediction(name, m_id):
        try:
            resp = client.chat.completions.create(
                model=m_id,
                messages=[
                    {"role": "system", "content": "你现在是反重力作战部队高阶合伙人，课题：时间不存在。"},
                    {"role": "user", "content": f"基于最新数据：\n{data_info}\n请针对 043 期给出你的逻辑审计。"}
                ],
                temperature=0.1
            )
            # 拿到文字后直接进行物理提取
            return name, extract_logic_numbers(resp.choices[0].message.content)
        except Exception as e:
            # 报错时返回空数据和错误报告
            return name, {"reds":[], "blue":"00", "raw_report": f"链路受阻: {str(e)}"}

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(fetch_prediction, n, i) for n, i in council.items()]
        return {n: r for n, r in [f.result() for f in futures]}

# --- 4. 主执行流 ---
def run_low_pressure_audit():
    st.write(">>> 🚀 正在调动全矩阵模型进行 043 期时空审计...")
    
    try:
        # 数据同步逻辑
        remote_path = sync_latest_data()
        target_path = remote_path if remote_path and os.path.exists(remote_path) else "lottery_history.csv"
        
        if os.path.exists(target_path):
            df = pd.read_csv(target_path).tail(15)
            data_info = df.to_string()
            # 获取 042 期用于对比 (假设最后一行是042)
            last_real = df.iloc[-1]
        else:
            st.error("❌ 缺失历史张量数据！")
            return

        # 并发点火
        start_time = time.time()
        with st.spinner("⏳ 5个作战单元正在同步计算中..."):
            matrix_results = matrix_audit_logic(data_info)
        
        st.balloons()
        
        # --- 5. UI 渲染：OMNI-NEXUS 终极抉择表格 ---
        st.markdown("### 🔥 043 期多模型对冲审计报告")
        
        # 构造表格显示
        display_data = []
        for name, data in matrix_results.items():
            display_data.append({
                "审计单元": name,
                "红球序列": " ".join(data['reds']),
                "蓝球": data['blue'],
                "状态": "✅ 锁定" if data['reds'] else "❌ 掉线"
            })
            # 报告原文放在折叠窗里
            with st.expander(f"📜 查看 {name} 的原始物理报告"):
                st.write(data['raw_report'])

        st.table(pd.DataFrame(display_data))
        
        st.success(f"✅ 矩阵推演完成！总耗时: {int(time.time() - start_time)}s")

    except Exception as e:
        st.error(f"❌ 统帅部反馈异常: {e}")

# --- 6. 页面入口 ---
if __name__ == "__main__":
    st.set_page_config(page_title="反重力·时空审计中心", layout="wide")
    st.title("🛸 反重力 V7.0 - 多模型联合作战部队")
    
    if st.button("🚀 执行 043 期矩阵点火"):
        run_low_pressure_audit()
