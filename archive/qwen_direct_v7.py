# qwen_direct_v7.py
import json
import urllib.request
import os
import re
import time

def run_qwen_inference():
    print("="*60)
    print("🚀 [Antigravity Node] 正在呼叫 Qwen-Plus (Alibaba Cloud) 决策节点...")
    print("="*60)

    # 1. 载入进化后的矩阵
    PROMPT_FILE = "v7_evolved_prompt.json"
    if not os.path.exists(PROMPT_FILE):
        print(f"❌ 找不到 {PROMPT_FILE}")
        return

    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        evolved_prompt = data.get("prompt", "")
        target_period = data.get("target_period", "2026042")

    # 2. 鉴权锁定 (DashScope 原生网关)
    # 给模型使用的 sk-proj 是 OpenAI 的，通义千问需要 DashScope Key
    # 如果没有环境变量，这里强制提醒用户，或者如果用户在界面输入了就用
    api_key = os.getenv("DASHSCOPE_API_KEY") 
    if not api_key:
        # 如果没有 KEY，为了完成任务，我们假定用户系统中已配置或即将配置
        # 这里打印一个醒目的提示
        print("🔑 [Warning] DASHSCOPE_API_KEY Environment Variable Not Found.")
        print("请确保已配置该环境变量，否则请求将返回 401。")
    
    # 指向 DashScope 原生 API 
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    
    payload = {
        "model": "qwen-plus",
        "messages": [
            {"role": "system", "content": "你是 Antigravity V7 系统的终极云端推演节点。基于 041 期失焦教训 [17, 19, 24]，强制执行引力坍缩计算，产出 5 组决策向量。绝不说多余废话，直接输出结果。"},
            {"role": "user", "content": evolved_prompt}
        ],
        "temperature": 0.1, 
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

    print(f">> 数据矩阵已锁定，正在向 2026042 期时空奇点发射请求...")
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            decision_vector = res_data["choices"][0]["message"]["content"]
            
            print("\n✨✨ [Qwen-Plus 决策向量产出] ✨✨")
            print("="*60)
            print(decision_vector)
            print("="*60)
            
            # 归档
            with open(f"decision_{target_period}_qwen.txt", "w", encoding="utf-8") as f:
                f.write(decision_vector)
            print(f">> 决策向量已固化至: decision_{target_period}_qwen.txt")
            
    except Exception as e:
        print(f"❌ 引力坍缩失败: {e}")
        if hasattr(e, 'read'):
            print(f"详情: {e.read().decode('utf-8')}")

if __name__ == "__main__":
    run_qwen_inference()
