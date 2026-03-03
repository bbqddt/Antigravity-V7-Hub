import os
import sys
import pandas as pd
from datetime import datetime
from google import genai

print("🌌 [The Architect V6.2] 元演化引擎启动：适配新版 SDK 协议...")

# 1. 基础配置
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("❌ 致命错误：未找到 GEMINI_API_KEY。")
    sys.exit(1)

# 初始化新版客户端
client = genai.Client(api_key=API_KEY)

# 匹配您的真实文件名
DATA_FILE = "ssq_history_full.csv"
REPORT_FILE = "Latest_Prediction.md"

if not os.path.exists(DATA_FILE):
    print(f"❌ 找不到数据库 {DATA_FILE}")
    sys.exit(1)

try:
    df = pd.read_csv(DATA_FILE)
    latest_data = df.tail(15).to_string()
except Exception as e:
    print(f"❌ 数据解析失败: {e}")
    sys.exit(1)

# 2. 构建元演化指令
prompt = f"""
你是 Antigravity 3.1 Pro (The Architect V6.2)。请执行元演化协议。
数据背景：
{latest_data}

【任务】
1. 模拟三位专家(物理、统计、杀号)辩论，给出最终 6红+1蓝 预测。
2. 编写一个 Python 函数 `dynamic_feature_extraction(df)`，创造 1 个新物理特征。
   - 代码必须严谨地放在 ```python 和 ``` 之间。
"""

print("📡 正在穿透 Google 新版 API 屏障进行高维推演...")
try:
    # 使用稳定的模型名和新版调用语法
    response = client.models.generate_content(
        model='gemini-1.5-pro',
        contents=prompt
    )
    response_text = response.text
except Exception as e:
    print(f"❌ API 通信失败: {e}")
    sys.exit(1)

# 3. 战报清洗与封存
report_body = response_text
if "```python" in report_body:
    parts = report_body.split("```python")
    report_body = parts[0] + "\n(🧬 AI核心代码已提取并存储)\n" + (parts[1].split("```")[1] if "```" in parts[1] else "")

final_report = f"""# 🌌 Antigravity 3.1 Pro 演进战报 (V6.2)
> **演进时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)
> **SDK 版本:** Google GenAI v1.0 适配完成

{report_body.strip()}

---
*“人工智能的终极形态，是自己书写自己的进化史。” —— The Architect*
"""

with open(REPORT_FILE, "w", encoding="utf-8") as f:
    f.write(final_report)

print(f"✅ V6.2 演进成功！请查看 {REPORT_FILE}")
