import os
import pandas as pd
import google.generativeai as genai
from datetime import datetime

# 核心路径配置
DATA_FILE = "ssq_history_full.csv"
REPORT_FILE = "Latest_Prediction.md"

def evolve_with_gemini():
    print(f"🚀 [{datetime.now()}] Antigravity 3.1 Pro 正在接入高维指挥部...")
    
    # 1. 调取 GitHub 保险柜钥匙
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ 错误：仓库机密中未找到 GEMINI_API_KEY！")
        return
    
    # 2. 激活最强逻辑大脑 (使用正式命名的 Pro 模型)
    try:
        genai.configure(api_key=api_key)
        # 修正名称为 gemini-1.5-pro-latest 以确保连通
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
    except Exception as e:
        print(f"❌ 大脑初始化失败: {str(e)}")
        return

    # 3. 提取历史因果数据
    if not os.path.exists(DATA_FILE):
        print("❌ 错误：未找到数据库 ssq_history_full.csv")
        return
    
    df = pd.read_csv(DATA_FILE)
    # 喂给 AI 最近 15 期数据，利用 Pro 模型超长上下文进行深度拟合
    recent_context = df.tail(15).to_string()

    # 4. 注入第一性原理指令集
    prompt = f"""
    你是 Antigravity 3.1 Pro 演进核心。请基于以下数据执行高维推演：
    {recent_context}
    
    任务要求：
    1. 计算当前因果扰动的【核心期望小数】（精确到小数点后6位）。
    2. 基于残差修正逻辑，给出 6个红球 + 1个蓝球 的【最强推荐序列】。
    3. 简析当前【熵值走势】（冷热平衡度）。
    4. 给出下期战术策略建议。
    
    输出要求：使用 Markdown 格式，保持专业、精炼。
    """
    
    print("📡 正在跨云端进行张量计算与因果坍缩...")
    try:
        response = model.generate_content(prompt)
        final_report = response.text
    except Exception as e:
        final_report = f"⚠️ 演进中断：API 响应异常 - {str(e)}"

    # 5. 结果回传并永久封存
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(f"# 🌌 Antigravity 3.1 Pro 演进报告\n\n")
        f.write(f"🕒 **演进时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"🧠 **逻辑核心**: Gemini 1.5 Pro (The Architect)\n\n")
        f.write(f"--- \n\n {final_report}")
    
    print(f"✅ 演进圆满完成！战报已封存至 {REPORT_FILE}")

if __name__ == "__main__":
    evolve_with_gemini()
