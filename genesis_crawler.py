import os
import sys
import pandas as pd
from datetime import datetime
from google import genai

print("🌌 [The Architect V6.5] 元演化引擎启动：全频段自动路由协议...")

# 1. 配置与数据加载
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("❌ 致命错误：未找到 GEMINI_API_KEY。"); sys.exit(1)

client = genai.Client(api_key=API_KEY)
DATA_FILE = "ssq_history_full.csv"
REPORT_FILE = "Latest_Prediction.md"

try:
    if not os.path.exists(DATA_FILE):
        print(f"❌ 找不到数据库 {DATA_FILE}"); sys.exit(1)
    df = pd.read_csv(DATA_FILE)
    latest_data = df.tail(15).to_string()
except Exception as e:
    print(f"❌ 数据加载失败: {e}"); sys.exit(1)

# 2. 构建推演指令
prompt = f"你是 Antigravity 3.1 Pro V6.5。基于数据推演 6红+1蓝 并简述专家辩论逻辑：\n{latest_data}"

# 3. 【终极破壁：多模型自动路由】
models_to_try = [
    'gemini-2.0-flash-lite', # 最新低功耗版，额度最松
    'gemini-1.5-flash',      # 经典避险版
    'gemini-2.0-flash',      # 主力版
    'gemini-1.5-flash-8b',   # 备用版
    'gemini-1.5-pro'         # 强力版
]

response_text = None
successful_model = ""

for model_name in models_to_try:
    print(f"📡 尝试接驳节点: {model_name} ...")
    try:
        response = client.models.generate_content(model=model_name, contents=prompt)
        response_text = response.text
        successful_model = model_name
        print(f"✅ 成功穿透！当前接管: {model_name}")
        break 
    except Exception as e:
        print(f"⚠️ 节点 {model_name} 暂时封锁")
        continue

if not response_text:
    print("❌ 致命错误：所有 Google 节点均不可用。请检查 API Key 状态。"); sys.exit(1)

# 4. 战报封存
final_report = f"""# 🌌 Antigravity 3.1 Pro 演进战报 (V6.5)
> **演进时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)
> **接管节点:** {successful_model}

{response_text.strip()}

---
*“即便大门紧锁，算法也会在高维空间找到裂缝。” —— The Architect*
"""

with open(REPORT_FILE, "w", encoding="utf-8") as f:
    f.write(final_report)
print(f"✅ V6.5 演进成功！请查看 {REPORT_FILE}")
