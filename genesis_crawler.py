import os
import sys
import pandas as pd
from datetime import datetime
from google import genai

print("🌌 [The Architect V6.7] 反重力元演化协议：全维度算力穿透启动...")

# 1. 密钥池注入 (多账号冗余)
keys = [os.environ.get("GEMINI_API_KEY"), os.environ.get("GEMINI_API_KEY_2")]
keys = [k for k in keys if k] # 过滤空值

if not keys:
    print("❌ 致命错误：未检测到任何 API Key。"); sys.exit(1)

DATA_FILE = "ssq_history_full.csv"
REPORT_FILE = "Latest_Prediction.md"

# 2. 数据加载
if not os.path.exists(DATA_FILE):
    print(f"❌ 找不到数据库 {DATA_FILE}"); sys.exit(1)
df = pd.read_csv(DATA_FILE)
latest_data = df.tail(15).to_string()

# 3. 反重力演化指令
prompt = f"""
你是 Antigravity 3.1 Pro V6.7。执行高维推演任务：
1. 分析数据碰撞：{latest_data}
2. 模拟三位专家(统计、动力学、杀号)进行元演化辩论。
3. 给出 6红+1蓝 预测并详述杀号逻辑。
"""

# 4. 全模型路由 + 多 Key 轮询
models = ['gemini-2.0-flash-lite', 'gemini-1.5-flash', 'gemini-2.0-flash', 'gemini-1.5-pro']
response_text = None
active_model = ""

for key in keys:
    if response_text: break
    client = genai.Client(api_key=key)
    for m in models:
        print(f"📡 尝试接驳节点: {m} (Key: {key[:8]}...)")
        try:
            res = client.models.generate_content(model=m, contents=prompt)
            response_text = res.text
            active_model = m
            print(f"✅ 穿透成功！由 {m} 接管推演。")
            break
        except Exception as e:
            print(f"⚠️ 节点拒绝: {str(e)[:50]}...")
            continue

if not response_text:
    print("❌ 所有 Key 及所有模型均已封锁。请等待额度重置。"); sys.exit(1)

# 5. 战报封存
final_report = f"""# 🌌 Antigravity 3.1 Pro 演进战报 (V6.7)
> **演进时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)
> **逻辑核心:** {active_model} (Google AI Studio)

{response_text.strip()}

---
*“即便引力束缚了身体，算法也能在云端自由演化。” —— The Architect*
"""

with open(REPORT_FILE, "w", encoding="utf-8") as f: f.write(final_report)
print(f"✅ V6.7 演进成功！请查看 {REPORT_FILE}")
