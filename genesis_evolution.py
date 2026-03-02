import os
import pandas as pd
import google.generativeai as genai
from datetime import datetime

# 配置路径
DATA_FILE = "ssq_history_full.csv"
REPORT_FILE = "Latest_Prediction.md"

def evolve_with_gemini():
    print(f"🚀 [{datetime.now()}] 正在同步 Google AI 高维大脑...")
    
    # 1. 获取保险柜钥匙
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ 错误：仓库保险柜中未找到 GEMINI_API_KEY！")
        return
    
    # 2. 激活大脑
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    # 3. 准备数据快照
    if not os.path.exists(DATA_FILE):
        print("❌ 错误：未找到数据库文件！")
        return
    
    df = pd.read_csv(DATA_FILE)
    recent_data = df.tail(10).to_string()

    # 4. 发起演进推演
    prompt = f"""
    你现在是反重力 3.1 Pro 演进核心。
    基于以下最新数据流，运用非线性动力学进行残差修正，给出下一期的推演结论：
    {recent_data}
    
    请按以下格式输出：
    1. 核心期望值（精确到小数点后6位）
    2. 推荐序列（6+1）
    3. 简短的战术逻辑分析
    """
    
    try:
        response = model.generate_content(prompt)
        ai_logic = response.text
    except Exception as e:
        ai_logic = f"大脑连接异常: {str(e)}"

    # 5. 封存报告
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(f"# 🌌 Antigravity 3.1 Pro 演进报告\n\n")
        f.write(f"🕒 **演进时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"--- \n\n {ai_logic}")
    
    print(f"✅ 演进成功，战报已存入 {REPORT_FILE}")

if __name__ == "__main__":
    evolve_with_gemini()
