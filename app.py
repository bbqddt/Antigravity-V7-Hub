import openai
import pandas as pd
import streamlit as st
import re
import concurrent.futures

# --- 1. 统帅部配置 ---
OR_KEY = "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"
client = openai.OpenAI(
    api_key=OR_KEY, 
    base_url="https://openrouter.ai/api/v1"
)

# --- 2. 核心解析官：从文字报告中提取红蓝球 ---
def parse_ai_numbers(text):
    """
    物理提取器：确保 UI 永远能读到 'reds' 键，彻底终结 KeyError
    """
    # 提取红球 (01-33)
    reds = re.findall(r'\b(0[1-9]|[12]\d|3[0-3])\b', text)
    # 提取蓝球 (01-16)
    blues = re.findall(r'\b(0[1-9]|1[0-6])\b', text)
    
    # 格式化：去重、排序、取前6
    final_reds = sorted(list(set(reds)))[:6]
    # 兜底：如果 AI 没吐数字，使用 DeepSeek 的核心张量
    if len(final_reds) < 6:
        final_reds = ["07", "12", "13", "19", "22", "24"]
    
    final_blue = blues[-1] if blues else "16"
    return {"reds": final_reds, "blue": final_blue, "raw": text}

# --- 3. 联合作战矩阵：并发执行逻辑 ---
def fire_matrix():
    models = {
        "逻辑官-Claude 3.5": "anthropic/claude-3.5-sonnet",
        "计算器-DeepSeek": "deepseek/deepseek-chat",
        "架构师-Gemini Pro": "google/gemini-pro-1.5"
    }

    def fetch_result(name, mid):
        try:
            resp = client.chat.completions.create(
                model=mid,
                messages=[
                    {"role": "system", "content": "你现在是反重力作战部合伙人，课题：时间不存在。"},
                    {"role": "user", "content": "请对 043 期进行逻辑审计并给出号码。"}
                ],
                temperature=0.1
            )
            # 返回元组，确保结果可追踪
            return (name, parse_ai_numbers(resp.choices[0].message.content))
        except Exception as e:
            return (name, parse_ai_numbers(f"链路波动: {e} 07 12 13 19 22 24 B16"))

    with concurrent.futures.ThreadPoolExecutor() as exe:
        # 45行修正点：使用列表推导式配合元组解包
        futures = [exe.submit(fetch_result, n, i) for n, i in models.items()]
        # 修正逻辑：不再直接引用未定义的 n，而是从结果元组中取值
        return {f.result()[0]: f.result()[1] for f in futures}

# --- 4. UI 渲染：指挥部主界面 ---
st.set_page_config(page_title="ANTIGRAVITY V7.0", layout="wide")
st.title("🛸 反重力 V7.0 - 多模型联合作战部队")

# 模拟复盘基准
REAL_BASE = {'reds': ['03', '10', '12', '13', '18', '33'], 'blue': '08'}

if st.button("🚀 执行 043 期全矩阵多模型审计"):
    with st.spinner("⏳ 正在跨维度征询所有单元意见..."):
        # 点火执行
        results = fire_matrix()
    
    #
