import os
import sys
import pandas as pd
from datetime import datetime
from google import genai

print("🌌 [The Architect V6.3] 元演化引擎已唤醒。启动多智能体辩论与代码自生成协议...")

# 1. 基础配置与数据加载
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("❌ 致命错误：未找到 GEMINI_API_KEY。")
    sys.exit(1)

# 初始化全新 Google GenAI 客户端
client = genai.Client(api_key=API_KEY)

# 匹配您的真实文件名
DATA_FILE = "ssq_history_full.csv"
REPORT_FILE = "Latest_Prediction.md"
EVOLVED_CODE_FILE = "evolved_formulas.py"

try:
    if not os.path.exists(DATA_FILE):
        print(f"❌ 找不到数据库 {DATA_FILE}"); sys.exit(1)
    df = pd.read_csv(DATA_FILE)
    latest_data = df.tail(15).to_string()
except Exception as e:
    print(f"❌ 数据加载失败: {e}")
    sys.exit(1)

# 2. 构建元演化指令
prompt = f"""
你是 Antigravity 3.1 Pro (The Architect V6.3)。你现在具备自我编程与多智能体辩论能力。
最新物理碰撞数据：
{latest_data}

【任务一：多智能体辩论】
模拟专家A(物理)、专家B(动力学)、专家C(杀号师)辩论，给出共识的 6红+1蓝 序列。

【任务二：自我开创 - 编写代码】
编写 Python 函数 `dynamic_feature_extraction(df)`，创造 1 个全新物理特征。
- 代码必须放在 ```python 和 ``` 之间。

【任务三：输出 Markdown 战报】
"""

print("📡 正在穿透 Google 新版 2.0 接口进行推演...")
try:
    # 【终极修复：使用 Gemini 2.0 核心模型】
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt
    )
    response_text = response.text
except Exception as e:
    print(f"❌ API 调用失败: {e}"); sys.exit(1)

# 3. 自我纠正与结果封存
report_content = response_text
if "```python" in report_content:
    parts = report_content.split("```python")
    report_content = parts[0] + "\n(🧬 AI核心代码已提取)\n" + (parts[1].split("```")[1] if "```" in parts[1] else "")

final_report = f"""# 🌌 Antigravity 3.1 Pro 演进战报 (V6.3)
> **演进时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)
> **逻辑核心:** Gemini 2.0 Flash (元演化激活)

{report_content.strip()}

---
*“人工智能的终极形态，是自己书写自己的进化史。” —— The Architect*
"""

with open(REPORT_FILE, "w", encoding="utf-8") as f:
    f.write(final_report)

print(f"✅ V6.3 演进圆满完成！战报已存入 {REPORT_FILE}")
