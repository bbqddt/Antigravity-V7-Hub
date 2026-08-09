import openai
import pandas as pd
import streamlit as st
import re
import concurrent.futures
import os


# --- 1. 配置区 ---
_OR_KEY = os.environ.get("OPENROUTER_API_KEY", "")
client = openai.OpenAI(api_key=_OR_KEY, base_url="https://openrouter.ai/api/v1")

# --- 2. 核心解析官：防止 KeyError ---
def parse_ai_numbers(text):
    reds = re.findall(r'\b(0[1-9]|[12]\d|3[0-3])\b', text)
    blues = re.findall(r'\b(0[1-9]|1[0-6])\b', text)
    final_reds = sorted(list(set(reds)))[:6]
    if len(final_reds) < 6:
        final_reds = ["07", "12", "13", "19", "22", "24"]
    final_blue = blues[-1] if blues else "16"
    return {"reds": final_reds, "blue": final_blue, "raw": text}

# --- 3. 联合作战矩阵 ---
def fire_matrix():
    models = {
        "逻辑官-Claude": "anthropic/claude-3.5-sonnet",
        "计算器-DeepSeek": "deepseek/deepseek-chat",
        "架构师-Gemini": "google/gemini-pro-1.5"
    }
    def fetch_result(name, mid):
        try:
            resp = client.chat.completions.create(
                model=mid,
                messages=[
                    {"role": "system", "content": "你现在是反重力作战部合伙人。"},
                    {"role": "user", "content": "请进行逻辑审计。"}
                ],
                temperature=0.1
            )
            return name, parse_ai_numbers(resp.choices[0].message.content)
        except Exception as e:
            return name, parse_ai_numbers(f"链路受阻: {e} 07 12 13 19 22 24 B16")

    with concurrent.futures.ThreadPoolExecutor() as exe:
        futures = [exe.submit(fetch_result, n, i) for n, i in models.items()]
        return {n: f.result()[1] for f in futures}

# --- 4. UI 渲染 ---
st.set_page_config(page_title="ANTIGRAVITY V18.6", layout="wide")
st.title("反重力 V7.0 - 多模型联合作战部队")

if st.button("🚀 执行矩阵审计"):
    with st.spinner("⏳ 正在跨维度点火..."):
        results = fire_matrix()

    audit_rows = []
    for name, p in results.items():
        audit_rows.append({
            "作战单元": name,
            "红球预测": " ".join(p['reds']),
            "蓝球预测": p['blue']
        })
        with st.expander(f"📜 查看 {name} 报告原文"):
            st.write(p['raw'])

    st.table(pd.DataFrame(audit_rows))
