import os
import sys
import pandas as pd
from datetime import datetime
from google import genai

print("🌌 [The Architect V6.4] 元演化引擎启动：切换至 1.5-Flash 算力避险协议...")

# 1. 基础配置
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("❌ 致命错误：未找到 GEMINI_API_KEY。")
    sys.exit(1)

# 初始化新版客户端
client = genai.Client(api_key=API_KEY)

# 自动适配您仓库中的文件名
DATA_FILE = "ssq_history_full.csv"
REPORT_FILE = "Latest_Prediction.md"

if not os.path.exists(DATA_FILE):
    print(f"❌ 找不到数据库 {DATA_FILE}")
    sys.exit(1)

try:
    df = pd.read_csv(DATA_FILE)
    # 取最后15期数据作为推演背景
    latest_data = df.tail(15).to_string()
except Exception as e:
    print(f"❌ 数据加载失败: {e}")
    sys.exit(1)

# 2. 构建推演指令
prompt = f"""
你是 Antigravity 3.1 Pro (The Architect V6.4)。
这是最新的双色球数据快照：
{latest_data}

【任务】
1. 模拟三位专家(物理学、统计学、混沌杀号师)辩论。
2. 给出共识后的下一期 6红+1蓝 预测序列。
3. 简述推演逻辑。
"""

print("📡 正在接驳 Gemini 1.5 Flash 算力突围版...")
try:
    # 使用免费额度最慷慨且稳定的模型避开 404/429 错误
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=prompt
    )
    report_body = response.text
    
    final_report = f"""# 🌌 Antigravity 3.1 Pro 演进战报 (V6.4)
> **演进时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)
> **避险模式:** Gemini 1.5 Flash (算力突围版)

{report_body.strip()}

---
*“人工智能的终极形态，是自己书写自己的进化史。” —— The Architect*
"""
    
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(final_report)
    print("✅ V6.4 演进成功！战报已生成。")
except Exception as e:
    print(f"❌ API 通信崩溃: {e}")
    sys.exit(1)
