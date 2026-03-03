```python
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

DATA_FILE = "ssq_genesis_2003_2024.csv"
REPORT_FILE = "Latest_Prediction.md"
EVOLVED_CODE_FILE = "evolved_formulas.py"

try:
    df = pd.read_csv(DATA_FILE)
    latest_data = df.tail(10).to_string()
except Exception as e:
    print(f"❌ 数据加载失败: {e}")
    sys.exit(1)
