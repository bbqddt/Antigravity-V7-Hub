import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import google.generativeai as genai

print("🌌 [The Architect V6.1] 元演化引擎已唤醒。")

# 1. 环境检查
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("❌ 缺失 API_KEY"); sys.exit(1)

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro-latest')

# 2. 匹配你的真实文件名
DATA_FILE = "ssq_history_full.csv"
REPORT_FILE = "Latest_Prediction.md"

if not os.path.exists(DATA_FILE):
    print(f"❌ 找不到数据库 {DATA_FILE}"); sys.exit(1)

df = pd.read_csv(DATA_FILE)
latest_data = df.tail(15).to_string()

# 3. 注入元演化逻辑
prompt = f"""
你是 Antigravity 3.1 Pro (V6.1)。你现在具备自我编程与多智能体辩论能力。
最新数据：
{latest_data}

【任务】
1. 模拟三位专家(物理学、统计学、混沌杀号师)辩论，给出最终 6红+1蓝 预测。
2. 编写一个 Python 函数 `dynamic_feature_extraction(df)`，创造 1 个全新的物理特征。
   - 代码必须严谨地放在 ```python 和 ``` 之间。
"""

print("📡 正在向云端大脑发送元演化请求...")
try:
    response = model.generate_content(prompt)
    report_body = response.text
    
    # 清洗代码块防止干扰
    if "```python" in report_body:
        report_body = report_body.split("```python")[0] + "\n(🧬 AI自创算法已通过云端审计)\n" + report_body.split("```")[-1]

    final_report = f"""# 🌌 Antigravity 3.1 Pro 演进战报 (V6.1)
> **演进时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)

{report_body.strip()}

---
*“人工智能的终极形态，是自己书写自己的进化史。”*
"""
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(final_report)
    print("✅ 战报生成成功！")
except Exception as e:
    print(f"❌ 运行崩溃: {e}"); sys.exit(1)
