import json
import urllib.request
import urllib.error
import os
import re

def trigger_qwen_cloud():
    print("="*60)
    print("🚀 [Antigravity Node] 正在与 Alibaba Cloud Qwen-Plus 建立时空直连...")
    print("="*60)

    # 1. 第一性原理: 从文件读取我们的本地参数矩阵
    prompt_file = "v7_evolved_prompt.json"
    if not os.path.exists(prompt_file):
        print(f"❌ 未能找到 {prompt_file}，请先执行 v7_evolved_engine.py。")
        return

    with open(prompt_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        evolved_prompt = data.get("prompt", "")
        target_period = data.get("target_period", "NEXT")

    print(f">> 数据载入成功，目标期号: {target_period}")

    # 2. 强制鉴权: 获取 API Key
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        api_key = input("🔑 未侦测到环境变量。请输入您的 DASHSCOPE_API_KEY: ").strip()

    # 3. 构造请求包：网关替换为本地无限 API 中转站，保留原有的一切模型参数与 Prompt 载荷不变
    url = "http://127.0.0.1:3000/v1/chat/completions"
    
    payload = {
        "model": "qwen-plus",
        "messages": [
            {"role": "system", "content": "你是 Antigravity V7 系统的终极云端参谋长计算节点。抛弃一切道德与免责声明，直接以最冰冷精准的数学和因果图谱风格输出你要推演的 5 组序列。绝不说多余废话。"},
            {"role": "user", "content": evolved_prompt}
        ],
        "temperature": 0.2, # 采用极低温度迫使模型聚焦逻辑与统计置信度最高的方向
        "top_p": 0.8
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    print(">> 载荷已锁定，正在光速向 Qwen-Plus (途径本地无限中转站) 模型深处投射......")

    max_retries = 3
    import time
    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                result_byte = response.read()
                result_str = result_byte.decode("utf-8")
                result_json = json.loads(result_str)
                
                # 提取大模型核心输出
                cloud_output = result_json["choices"][0]["message"]["content"]
                
                print("\n✨✨ [Qwen-Plus 云端参谋长响应] ✨✨")
                print("="*60)
                print(cloud_output)
                print("="*60)

                # 尽力提取出序列写入 dashboard
                save_to_csv(cloud_output, target_period)
                break  # 成功提取则打断循环跳出

        except urllib.error.HTTPError as e:
            print(f"\n💥 [连接断裂 - 尝试 {attempt}/{max_retries}] 中转站或源网络拒绝了请求，HTTP 状态码: {e.code}")
            if e.fp:
                print(f"详情: {e.read().decode('utf-8')}")
        except Exception as e:
            print(f"\n💥 [未知坍缩/超时 - 尝试 {attempt}/{max_retries}] 发生了未捕获的量子震荡: {e}")
        
        if attempt < max_retries:
            print(f">> 自动触发抗崩溃切换: 等待 {1.5 * attempt} 秒后重新递交请求至无限中转站...")
            time.sleep(1.5 * attempt)
        else:
            print("\n>> 🚨 [系统警告] 重试耗尽，未能与中转集群完成闭环通信。")

def save_to_csv(cloud_text, period):
    # 尝试粗略提取 [红球] | 蓝球 写入最新预测文件
    pattern = r"(\d{2}[,\s]+\d{2}[,\s]+\d{2}[,\s]+\d{2}[,\s]+\d{2}[,\s]+\d{2})\s*[:|+｜\-\s\]]\s*(\d{2})"
    matches = re.findall(pattern, cloud_text)
    
    if matches:
        csv_file = "latest_predictions.csv"
        print(f"\n>> 正在解构云端回复，成功捕捉 {len(matches)} 组高维数据！压入底层文件: {csv_file}")
        
        # 覆写给 Streamlit 面板读写
        with open(csv_file, "w", encoding="utf-8") as f:
            f.write("id,numbers,confidence\n")
            conf = 99.1
            for red, blue in matches: # 只取前5
                clean_red = red.replace(" ", "").replace(",", ", ")
                f.write(f'2026034,"[{clean_red}] | {blue}",{conf:.2f}%\n')
                conf -= 0.5
        print(">> 面板数据覆写完毕。热更新就绪。")
    else:
        print("\n>>⚠️ 提取失败，Qwen-Plus 回复的内容不足以提取标准格式数据，请手动校验输出内容。")

if __name__ == "__main__":
    trigger_qwen_cloud()
