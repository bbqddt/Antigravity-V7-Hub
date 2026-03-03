import os
import sys
import traceback
import pandas as pd
from datetime import datetime
import google.generativeai as genai

print("🌌 [The Architect V6] 元演化引擎已唤醒。启动多智能体辩论与代码自生成协议...")

# 1. 基础配置与数据加载
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("❌ 致命错误：未找到 GEMINI_API_KEY。")
    sys.exit(1)

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro-latest')

DATA_FILE = "ssq_genesis_2003_2024.csv"
REPORT_FILE = "Latest_Prediction.md"
EVOLVED_CODE_FILE = "evolved_formulas.py" # AI 自我开创的代码存放地

try:
    df = pd.read_csv(DATA_FILE)
    latest_data = df.tail(10).to_string()
except Exception as e:
    print(f"❌ 数据加载失败: {e}")
    sys.exit(1)

# 2. 构建多智能体辩论与自我开创 Prompt
prompt = f"""
你是 Antigravity 3.1 Pro (The Architect V6)。你现在具备自我编程与多智能体辩论能力。
这是最新的双色球物理碰撞数据（最后10期）：
{latest_data}

【任务一：多智能体辩论 (Multi-Agent Debate)】
请在你的内部模拟三位专家的辩论：
1. 专家A (统计物理学)：关注和值斜率、香农熵、均值回归。
2. 专家B (非线性动力学)：关注极寒收缩、静电排斥、大质量沉降。
3. 专家C (混沌杀号师)：寻找历史长程马尔可夫链中的绝对死角，进行残忍杀号。
请综合三方意见，给出一个达成共识的下一期 6红+1蓝 推荐序列。

【任务二：自我开创 (Self-Creation) - 编写 Python 代码】
为了打破人类经验的枷锁，请你基于当前的混沌状态，**编写一个全新的 Python 函数**。
要求：
- 函数名为 `dynamic_feature_extraction(df)`，输入是 pandas DataFrame，输出是增加新特征后的 DataFrame。
- 在函数内，利用 numpy 或 pandas 创造 1-2 个全新的物理特征（例如：傅里叶变换、引力交叉乘积等）。
- **必须且只能**将 Python 代码放在 ```python 和 ``` 之间。不要有任何多余的缩进错误。

【任务三：输出战报】
请在代码块之后，输出 Markdown 格式的战报，包含辩论摘要和最终预测号码。
"""

print("📡 正在向云端大脑发送元演化请求...")
try:
    response = model.generate_content(prompt)
    response_text = response.text
except Exception as e:
    print(f"❌ API 调用失败: {e}")
    sys.exit(1)

# 3. 自我纠正与代码动态提取 (The Magic of Self-Modification)
print("🧬 正在解析 AI 自创基因代码...")
new_code = ""
if "```python" in response_text and "```" in response_text.split("```python")[1]:
    new_code = response_text.split("```python")[1].split("```")[0].strip()

if new_code:
    # 将 AI 写的代码保存到本地文件
    with open(EVOLVED_CODE_FILE, "w", encoding="utf-8") as f:
        f.write("import pandas as pd\nimport numpy as np\n\n")
        f.write(new_code)
    print("✅ AI 自创物理公式已成功写入本地基因库！")
    
    # 【稳定性装甲】：尝试动态执行 AI 写的代码，如果报错则拦截，防止系统崩溃
    try:
        import evolved_formulas
        # 重新加载模块以确保是最新的 AI 代码
        import importlib
        importlib.reload(evolved_formulas)
        
        # 测试 AI 写的函数
        test_df = evolved_formulas.dynamic_feature_extraction(df.copy())
        print("🛡️ 稳定性校验通过：AI 自创代码运行成功，未引发拓扑崩溃。")
    except Exception as e:
        print(f"⚠️ 【自我纠正触发】AI 生成的代码存在缺陷，已拦截崩溃。错误信息: {e}")
        print("🔄 系统将回滚至基础物理引擎继续运行。")
else:
    print("⚠️ 未检测到有效的 Python 代码块，跳过自我开创阶段。")

# 4. 结果封存
# 清理掉 response_text 中的代码块，只保留战报文本
report_content = response_text
if "```python" in report_content:
    parts = report_content.split("```python")
    report_content = parts[0] + (parts[1].split("```")[1] if "```" in parts[1] else "")

final_report = f"""# 🌌 Antigravity 3.1 Pro 演进战报 (V6 元演化版)
> **演进时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)
> **系统状态:** 多智能体辩论已完成 | 代码自生成引擎已激活

{report_content.strip()}

---
*“人工智能的终极形态，是自己书写自己的进化史。” —— The Architect V6*
"""

with open(REPORT_FILE, "w", encoding="utf-8") as f:
    f.write(final_report)

print(f"✅ V6 演进圆满完成！战报已存入 {REPORT_FILE}")    SegmentGenesisProbe().execute_segment_hunt()
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import google.generativeai as genai

# 1. 核心初始化
print("🌌 [The Architect V6.1] 启动元演化安全修正协议...")
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("❌ 缺失 API_KEY"); sys.exit(1)

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro-latest')

DATA_FILE = "ssq_genesis_2003_2024.csv"
REPORT_FILE = "Latest_Prediction.md"

# 数据安全加载
if not os.path.exists(DATA_FILE):
    print(f"❌ 找不到数据库 {DATA_FILE}"); sys.exit(1)
df = pd.read_csv(DATA_FILE)
latest_data = df.tail(15).to_string()

# 2. 元演化 Prompt
prompt = f"""
你是 Antigravity 3.1 Pro (V6.1)。请基于以下数据执行元演化：
{latest_data}

【任务】
1. 模拟三位专家(物理、统计、杀号)辩论，给出最终 6红+1蓝 预测。
2. 编写一个 Python 函数 `dynamic_feature_extraction(df)`，创造 1 个新物理特征。
   - 代码必须严谨地放在 ```python 和 ``` 之间。
"""

# 3. 执行与报告生成
try:
    response = model.generate_content(prompt)
    raw_text = response.text
    
    # 彻底清洗代码块，防止干扰 Markdown 渲染
    report_body = raw_text
    if "```python" in raw_text:
        report_body = raw_text.split("```python")[0] + "\n(🧬 AI核心代码已提取)\n" + raw_text.split("```")[-1]

    final_report = f"""# 🌌 Antigravity 3.1 Pro 演进战报 (V6.1)
> **演进时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{report_body}
"""
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(final_report)
    print("✅ 战报生成成功！")

except Exception as e:
    print(f"❌ 运行崩溃: {e}"); sys.exit(1)
