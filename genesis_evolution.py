import os
import pandas as pd
import numpy as np
import google.generativeai as genai
from datetime import datetime

# 配置路径
# 请确保您的文件名与仓库中实际的文件名一致
DATA_FILE = "ssq_history_full.csv" 
REPORT_FILE = "Latest_Prediction.md"

def evolve_engine_v4_1():
    print(f"🚀 [{datetime.now()}] Antigravity 3.1 Pro V4.1 准头强化版启动...")
    
    # 1. 调取 GitHub 保险柜钥匙
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ 错误：未找到 API Key")
        return
    
    genai.configure(api_key=api_key)
    # 使用 Pro 模型处理复杂逻辑
    model = genai.GenerativeModel('gemini-1.5-pro-latest')

    # 2. 准备数据与物理特征
    if not os.path.exists(DATA_FILE):
        print(f"❌ 错误：找不到文件 {DATA_FILE}")
        return
        
    df = pd.read_csv(DATA_FILE)
    
    # 计算物理特征：系统总能量(和值)、离散度(方差)
    df['Sum_Energy'] = df[['R1','R2','R3','R4','R5','R6']].sum(axis=1)
    df['Variance_Tension'] = df[['R1','R2','R3','R4','R5','R6']].var(axis=1)
    
    # 提取最近 20 期的高维上下文
    recent_context = df.tail(20).to_string()
    
    # 3. 注入“准头强化”指令集
    prompt = f"""
    你是 Antigravity 3.1 Pro 指挥官。当前任务：基于第一性原理进行【准头强化】推演。
    
    数据流（含系统能量与张力特征）：
    {recent_context}
    
    演进要求：
    1. 执行【残差自修复】：对比历史数据，计算因果偏差并进行补偿。
    2. 计算核心期望小数（精确到6位），需考虑【能量守恒】约束。
    3. 给出 6个红球 + 1个蓝球 的最强推荐序列。
    4. 给出下期【实战策略】。
    
    输出要求：使用 Markdown 格式，保持专业、精炼。
    """
    
    print("📡 正在跨云端进行张量计算与因果坍缩...")
    try:
        response = model.generate_content(prompt)
        final_report = response.text
    except Exception as e:
        final_report = f"⚠️ 演进中断: {str(e)}"

    # 4. 结果封存
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(f"# 🌌 Antigravity 3.1 Pro V4.1 (准头强化版)\n\n")
        f.write(f"🕒 **演进时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"🧠 **逻辑核心**: Gemini 1.5 Pro (Causal Inference)\n\n")
        f.write(f"--- \n\n {final_report}")
    
    print(f"✅ 准头强化推演完成！战报已存入 {REPORT_FILE}")

if __name__ == "__main__":
    evolve_engine_v4_1()
