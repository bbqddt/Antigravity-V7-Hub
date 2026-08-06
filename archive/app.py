import streamlit as st
import pandas as pd
import re
import concurrent.futures
from openai import OpenAI

# --- [1. 路径锁死：全免费避障矩阵] ---
MODELS_CONFIG = {
    "Llama-3.1-8B": "meta-llama/llama-3.1-8b-instruct:free",
    "Gemma-2-9B": "google/gemma-2-9b-it:free",
    "Mistral-7B": "mistralai/mistral-7b-instruct:free",
    "Qwen-2-7B": "qwen/qwen-2-7b-instruct:free",
    "OpenChat-3.5": "openchat/openchat-7b:free"
}

# --- [2. 客户端初始化] ---
_OPENROUTER_KEY = None
try:
    _OPENROUTER_KEY = st.secrets["OPENROUTER_API_KEY"]
except Exception:
    # Fall back to environment variable for local development
    import os
    _OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY")

if _OPENROUTER_KEY:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=_OPENROUTER_KEY,
    )
else:
    client = None

def antigravity_engine(model_alias, model_id, prompt):
    """
    反重力计算引擎
    """
    if client is None:
        return model_alias, "API key not configured"
    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": "你是一个高度中立的计算智能。执行反重力逻辑，预测号码格式必须为：01 02 03 04 05 06 | 07"},
                {"role": "user", "content": prompt}
            ],
            timeout=30
        )
        content = response.choices[0].message.content
        # 兼容性正则提取
        numbers = re.findall(r'(\d{2}[,\s]+\d{2}[,\s]+\d{2}[,\s]+\d{2}[,\s]+\d{2}[,\s]+\d{2}\s*[\s|]\s*\d{2})', content)
        return model_alias, numbers[-1] if numbers else "逻辑偏移（未捕获号码）"
    except Exception as e:
        return model_alias, f"Error: {str(e)}"

# --- [3. UI 布局] ---
st.set_page_config(page_title="Antigravity Hive-Final", layout="wide")
st.title("🚀 Antigravity-Core 决策中心")
st.markdown(f"**账户**: bbqddt2@gmail.com | **模式**: 全免费矩阵（避障）")

with st.sidebar:
    st.header("参数注入")
    latest_truth = st.text_area("输入最新开奖真相", "044期: 01 02 03 10 22 30 | 12")
    logic_prompt = f"已知真相：{latest_truth}。应用反重力逻辑，计算045期数字坍缩点。仅输出格式：XX XX XX XX XX XX | XX"

if st.button("点火 (执行并发计算)"):
    st.divider()
    with st.spinner("正在并发解析数字场..."):
        # 严格执行变量命名一致性
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_model = {
                executor.submit(antigravity_engine, name, mid, logic_prompt): name 
                for name, mid in MODELS_CONFIG.items()
            }
            
            cols = st.columns(len(MODELS_CONFIG))
            for i, future in enumerate(concurrent.futures.as_completed(future_to_model)):
                name = future_to_model[future] # 这里是之前的报错点，已修正
                try:
                    alias, prediction = future.result()
                    with cols[i]:
                        st.metric(label=alias, value="计算完成")
                        st.code(prediction)
                except Exception as exc:
                    with cols[i]:
                        st.error(f"线程崩溃: {exc}")

    st.success("045 期推演完成。")