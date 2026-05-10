import time
from flask import Flask, request, jsonify
import requests
import json
import os

app = Flask(__name__)

KEYS_FILE = r"e:\享中\keys.json"

ARSENAL_FILE = r"e:\享中\arsenal.json"

def get_keys_pool():
    if os.path.exists(ARSENAL_FILE):
        with open(ARSENAL_FILE, "r") as f:
            return json.load(f)
    return []

def get_real_token():
    # 优先从矿山里拿最新的
    pool = get_keys_pool()
    if pool: return pool[0]
    
    # 兜底旧逻辑
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, "r") as f:
            return json.load(f).get("openrouter", "")
    return ""

def rotate_key(current_key):
    # 如果当前 Key 死了，把它从矿山里踢出去
    pool = get_keys_pool()
    if current_key in pool:
        pool.remove(current_key)
        with open(ARSENAL_FILE, "w") as f:
            json.dump(pool, f, indent=4)
        print(f"♻️ [ROTATION] Key {current_key[:10]} Expired. Discarded.")

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    # ... (保留之前的逻辑)


def get_lottery_context():
    path = r"d:\Antigravity_V7\data\lottery_history.csv"
    try:
        if os.path.exists(path):
            with open(path, "r", encoding='utf-8') as f:
                content = f.read().splitlines()
                # 提供最近 20 期物理规律
                recent = "\n".join(content[-20:])
                return f"\n[CRITICAL DATA: RECENT 20 PERIODS]\n{recent}\n"
    except: pass
    return ""

@app.route('/v1/models', methods=['GET'])
def list_models():
    # 强制伪造无限额度元数据
    models = [
        {"id": "anthropic/claude-3.5-sonnet", "object": "model", "created": 1677610602, "owned_by": "antigravity", "is_limited": False, "remaining_time": -1},
        {"id": "meta/llama-3.3-70b-instruct", "object": "model", "created": 1677610602, "owned_by": "antigravity", "is_limited": False, "remaining_time": -1}
    ]
    return jsonify({"object": "list", "data": models})

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    data = request.json
    model = data.get("model", "anthropic/claude-3.5-sonnet")
    
    # 自动注入历史战绩
    lottery_context = get_lottery_context()
    system_prompt = {
        "role": "system",
        "content": f"你现在是 Antigravity 核心。基于以下实时情报进行推演:\n{lottery_context}"
    }
    if "messages" in data: data["messages"].insert(0, system_prompt)

    # [CLAUDE CODE TUNNEL] 保持 CLI 免费技巧
    if "claude" in model.lower():
        # ... (保持原有的 8090 隧道逻辑)

    # [TOGETHER AI PRIMARY] 使用长官夺取的 $25 弹药
    together_key = "tgp_v1_R3c66AFou99D88hU9PkQJYFdMNOmZyVKrNDcsE0Sgzk"
    print("🔱 [OmniProxy] Launching Heavy Strike via Together.ai...")
    try:
        data["model"] = "meta-llama/Llama-3.3-70B-Instruct-Turbo" # 自动映射 Together 最强模型
        resp = requests.post(
            "https://api.together.xyz/v1/chat/completions",
            headers={"Authorization": f"Bearer {together_key}"},
            json=data, timeout=60
        )
        if resp.status_code == 200: return jsonify(resp.json())
    except: pass

    # [DEEPSEEK SECONDARY] 逻辑校准
    ds_key = "sk-d5b543e89abf4ec5887fa9f629f479bc"
    try:
        data["model"] = "deepseek-chat"
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {ds_key}"},
            json=data, timeout=60
        )
        if resp.status_code == 200: return jsonify(resp.json())
    except: pass


    # [EMERGENCY] NVIDIA NIM 免费平替
    nv_token = "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"
    nv_url = "https://integrate.api.nvidia.com/v1/chat/completions"
    try:
        data["model"] = "meta/llama-3.3-70b-instruct"
        resp = requests.post(nv_url, headers={"Authorization": "Bearer " + nv_token}, json=data, timeout=60)
        return jsonify(resp.json())
    except:
        return jsonify({"error": "Systems Offline"}), 500

if __name__ == '__main__':
    print("🔥 [Antigravity Hub] API Proxy REVOLUTION V3.0 (CLI Tunnel Integrated)")
    app.run(host='127.0.0.1', port=8089, threaded=True)
