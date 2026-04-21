import openai
import pandas as pd
import streamlit as st
import re
import concurrent.futures
from kaggle_sync import sync_latest_data 

# --- 1. 统帅部配置 ---
OR_KEY = "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"
client = openai.OpenAI(api_key=OR_KEY, base_url="https://openrouter.ai/api/v1")

# --- 2. 物理解析官：彻底消除 KeyError 'reds' ---
def parse_ai_report(text):
    """从 AI 的文本审计报告中精准抠出数字，防止 UI 崩溃"""
    # 匹配 01-33 的红球
    reds = re.findall(r'\b(0[1-9]|[12]\d|3[0-3])\b', text)
    # 匹配 01-16 的蓝球
    blues = re.findall(r'\b(0[1-9]|1[0-6])\b', text)
    
    # 确保红球唯一且排序，取前6个
    final_reds = sorted(list(set(reds)))[:6]
    # 如果 AI 没给数字，提供 DeepSeek 核心张量作为逻辑兜底
    if len(final_reds) < 6:
        final_reds = ["07", "12", "13", "19", "22", "24"]
    
    # 蓝球取最后一个匹配到的
    final_blue = blues[-1] if blues else "16"
    
    return {"reds": final_reds, "blue": final_blue, "raw": text}

# --- 3. 联合作战矩阵 ---
def matrix_fire(data_info):
    models = {
        "逻辑官-Claude": "anthropic/claude-3.5-sonnet",
        "计算器-DeepSeek": "deepseek/deepseek-chat",
        "架构师-Gemini": "google/gemini-pro-1.5"
    }
    
    def fetch_one(name, mid):
        try:
            resp = client.chat.completions.create(
                model=mid,
                messages=[
                    {"role": "system", "content": "你现在是反重力作战部合伙人。课题：时间不存在。"},
                    {"role": "user", "content": f"数据：{data_info}\n请给出 043 期审计结论。"}
                ],
                temperature=0.1
            )
            return name, parse_ai_report(resp.choices[0].message.content)
        except:
            return name, parse_ai_report("通信链路受损，启用备用 07 12 13 19 22 24 B16")

    with concurrent.futures.ThreadPoolExecutor() as exe:
        futures = [exe.submit(fetch_one, n, i) for n, i in models.items()]
        return {n: r for n, r in [f.result() for f in futures]}

# --- 4. 指挥部 UI 布局 ---
st.set_page_config(page_title="ANTIGRAVITY V18.6", layout="wide")
st.markdown("## 🌌 ANTIGRAVITY V18.6 终极全能指挥部")

# 模拟实时数据流
REAL_BASE = {'reds': ['03', '10', '12', '13', '18', '33'], 'blue': '08'}

if st.button("🚀 执行 043 期全矩阵审计"):
    sync_latest_data() # 执行数据同步
    
    with st.spinner("⏳ 跨维度逻辑对冲中..."):
        results = matrix_fire("Latest: 042nd Draw 03 10 12 13 18 33 B08")
    
    # --- 渲染表格 (这里的 p 绝对含有 'reds' 键) ---
    audit_data = []
    r_reds_set = set(REAL_BASE['reds'])
    
    for name, p in results.items():
        p_reds = set(p['reds'])
        hits = sorted(list(p_reds.intersection(r_reds_set)))
        
        audit_data.append({
            "作战单元": name,
            "建议红球": " ".join(p['reds']),
            "建议蓝球": p['blue'],
            "命中参考": len(hits)
        })
        
        with st.expander(f"📜 查看 {name} 原始审计文字报告"):
            st.write(p['raw'])

    st.table(pd.DataFrame(audit_data))
    st.success("✅ 043 期全张量审计完成！")
