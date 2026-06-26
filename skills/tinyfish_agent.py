import requests
import json
import sys
import io

# 强制设置控制台输出为 UTF-8 (解决 Windows 乱码和 Emoji 报错)
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# [Antigravity Omega] TinyFish 自动化抓取引擎
TINYFISH_API_KEY = "sk-tinyfish-kdX0yLVAlO18NN_qM40OPQq-4MYCxcKp"

def run_tinyfish_mission(url, goal):
    print(f"🐟 [TinyFish Agent] 开始深潜...")
    print(f"🔗 目标坐标: {url}")
    print(f"🎯 战术目标: {goal}")
    
    endpoint = "https://agent.tinyfish.ai/v1/automation/run-sse"
    headers = {
        "X-API-Key": TINYFISH_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "url": url,
        "goal": goal
    }
    
    try:
        # 使用流式请求
        with requests.post(endpoint, headers=headers, json=payload, stream=True, timeout=120) as response:
            if response.status_code != 200:
                print(f"❌ [TinyFish Agent] 潜入失败! 状态码: {response.status_code}")
                print(response.text)
                return None
                
            print(f"🌊 [TinyFish Agent] 链接建立，正在接收自动化行动流...")
            final_result = ""
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("data: "):
                        # TinyFish 的 SSE 数据包
                        data_content = decoded_line[6:]
                        if data_content == "[DONE]":
                            break
                        try:
                            json_data = json.loads(data_content)
                            # 解析并展示过程或结果
                            if "text" in json_data:
                                sys.stdout.write(json_data["text"])
                                sys.stdout.flush()
                                final_result += json_data["text"]
                        except:
                            pass
            print("\n✅ [TinyFish Agent] 任务完成！")
            return final_result
            
    except Exception as e:
        print(f"❌ [TinyFish Agent] 通讯断裂: {e}")
        return None

if __name__ == "__main__":
    # 测试执行 (如需带参数执行可扩写 argparse)
    test_url = "https://news.ycombinator.com/jobs"
    test_goal = "Extract the first 3 job postings. Return as JSON array with keys: title, url."
    run_tinyfish_mission(test_url, test_goal)
