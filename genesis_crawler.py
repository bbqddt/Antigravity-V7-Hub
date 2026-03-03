import os
import sys
import pandas as pd
from datetime import datetime
from google import genai
from openai import OpenAI # 阿里云兼容 OpenAI 协议

print("🌌 [The Architect V6.8] 三线算力引擎启动：Google 1/2 + 阿里云协议...")

# 1. 密钥池注入
g_keys = [os.environ.get("GEMINI_API_KEY"), os.environ.get("GEMINI_API_KEY_2")]
g_keys = [k for k in g_keys if k]
ali_key = os.environ.get("ALIBABA_API_KEY")

DATA_FILE = "ssq_history_full.csv" # 确保对齐您的仓库文件名
REPORT_FILE = "Latest_Prediction.md"

if not os.path.exists(DATA_FILE):
    print(f"❌ 找不到数据库 {DATA_FILE}"); sys.exit(1)

try:
    df = pd.read_csv(DATA_FILE)
    latest_data = df.tail(15).to_string()
except Exception as e:
    print(f"❌ 数据加载失败: {e}"); sys.exit(1)

prompt = f"你是 Antigravity 3.1 Pro V6.8。推演 6红+1蓝 并详述专家辩论逻辑：\n{latest_data}"
response_text = None
active_cloud = ""

# 2. 第一、二阶段：尝试 Google 阵列 (自动切换 Key)
for i, key in enumerate(g_keys):
    if response_text: break
    try:
        client = genai.Client(api_key=key)
        # 尝试两个最稳定的模型
        for m in ['gemini-2.0-flash-lite', 'gemini-1.5-flash']:
            print(f"📡 尝试 Google 节点: {m} (Key-{i+1})...")
            try:
                res = client.models.generate_content(model=m, contents=prompt)
                response_text = res.text
                active_cloud = f"Google-Key-{i+1} ({m})"
                break
            except: continue
    except: continue

# 3. 第三阶段：阿里云引擎 (当 Google 彻底封锁时触发)
if not response_text and ali_key:
    print("⚠️ Google 阵列全线封锁！正在呼叫阿里云算力...")
    try:
        # 阿里云百炼兼容模式配置
        client = OpenAI(api_key=ali_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
        completion = client.chat.completions.create(
            model="qwen-plus", # 阿里云通义千问主力模型
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = completion.choices[0].message.content
        active_cloud = "Alibaba Cloud (Qwen-Plus)"
    except Exception as e:
        print(f"❌ 阿里云接驳失败: {e}")

if not response_text:
    print("❌ 致命错误：三线算力均告急！请检查所有 API Key 有效性。"); sys.exit(1)

# 4. 战报生成与封存
final_report = f"""# 🌌 Antigravity 3.1 Pro 演进战报 (V6.8)
> **演进时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)
> **接管云端:** {active_cloud}

{response_text.strip()}

---
*“即便引力束缚了身体，算法也能在多云端自由演化。” —— The Architect*
"""

with open(REPORT_FILE, "w", encoding="utf-8") as f:
    f.write(final_report)

print(f"✅ V6.8 演进圆满完成！由 {active_cloud} 强力驱动。")
