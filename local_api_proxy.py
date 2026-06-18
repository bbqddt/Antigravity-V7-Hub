import time
from flask import Flask, request, jsonify
import requests
import json
import sys
import os

log_file = open(r"E:\享中\local_api_runtime.log", "a", encoding="utf-8")
sys.stdout = log_file
sys.stderr = log_file

app = Flask(__name__)

# 统一配置当前云端环境路径
BASE_DIR = r"e:\享中"
KEYS_FILE = os.path.join(BASE_DIR, "keys.json")
ARSENAL_FILE = os.path.join(BASE_DIR, "arsenal.json")
LOTTERY_FILE = os.path.join(BASE_DIR, "ssq_history_full.csv")

PROXY_PORTS_TO_SNIFF = [10808, 7890, 1080, 10809]

def sniff_best_proxy():
    """微型代理嗅探器，动态找寻存活节点"""
    for port in PROXY_PORTS_TO_SNIFF:
        proxies = {"http": f"http://127.0.0.1:{port}", "https": f"http://127.0.0.1:{port}"}
        try:
            requests.head("https://1.1.1.1", proxies=proxies, timeout=2)
            return proxies
        except Exception:
            pass
    return None

def get_keys_pool():
    if os.path.exists(ARSENAL_FILE):
        with open(ARSENAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def get_real_token():
    pool = get_keys_pool()
    if pool: return pool[0]
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("openrouter", "")
    return ""

def rotate_key(current_key):
    pool = get_keys_pool()
    if current_key in pool:
        pool.remove(current_key)
        with open(ARSENAL_FILE, "w", encoding="utf-8") as f:
            json.dump(pool, f, indent=4)

def get_lottery_context():
    try:
        if os.path.exists(LOTTERY_FILE):
            with open(LOTTERY_FILE, "r", encoding='utf-8') as f:
                content = f.read().splitlines()
                recent = "\n".join(content[-20:])
                return f"\n[CRITICAL DATA: RECENT 20 PERIODS]\n{recent}\n"
    except Exception:
        pass
    return ""

@app.route('/v1/models', methods=['GET'])
def list_models():
    models = [
        {"id": "anthropic/claude-3.5-sonnet", "object": "model", "created": 1677610602, "owned_by": "antigravity"},
        {"id": "meta/llama-3.3-70b-instruct", "object": "model", "created": 1677610602, "owned_by": "antigravity"},
        # [NEW MODULES]: 预留 Claude Xode 和 Codex 的未来物理引擎接口
        {"id": "claude-xode-physical", "object": "model", "created": 1677610602, "owned_by": "antigravity_experimental"},
        {"id": "codex-logic-resolver", "object": "model", "created": 1677610602, "owned_by": "antigravity_experimental"}
    ]
    return jsonify({"object": "list", "data": models})

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    data = request.json
    model = data.get("model", "anthropic/claude-3.5-sonnet")
    
    lottery_context = get_lottery_context()
    system_prompt = {
        "role": "system",
        "content": f"你现在是 Antigravity 核心。基于以下实时情报进行推演:\n{lottery_context}"
    }
    if "messages" in data: 
        data["messages"].insert(0, system_prompt)

    # 【架构演进】拦截 Claude Xode 和 Codex 的高级任务请求
    if model in ["claude-xode-physical", "codex-logic-resolver"]:
        # 目前将他们重定向到物理内核的解释层或者直接使用顶级 LLaMA 兜底
        print(f"🧬 [EVOLUTION] Engaging Next-Gen Module: {model}")
        data["model"] = "meta-llama/Llama-3.3-70B-Instruct-Turbo"

    proxies = sniff_best_proxy()

    if "claude" in model.lower():
        try:
            resp = requests.post("http://127.0.0.1:8090/v1/chat/completions", json=data, timeout=60)
            if resp.status_code == 200: return jsonify(resp.json())
        except Exception:
            pass

    openrouter_token = get_real_token()
    if openrouter_token:
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {openrouter_token}"},
                json=data, proxies=proxies, timeout=60
            )
            if resp.status_code == 200: return jsonify(resp.json())
            elif resp.status_code in [401, 429]: rotate_key(openrouter_token)
        except Exception:
            pass

    together_key = "tgp_v1_R3c66AFou99D88hU9PkQJYFdMNOmZyVKrNDcsE0Sgzk"
    try:
        data["model"] = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
        resp = requests.post(
            "https://api.together.xyz/v1/chat/completions",
            headers={"Authorization": f"Bearer {together_key}"},
            json=data, proxies=proxies, timeout=60
        )
        if resp.status_code == 200: return jsonify(resp.json())
    except Exception: pass

    ds_key = "sk-d5b543e89abf4ec5887fa9f629f479bc"
    try:
        data["model"] = "deepseek-chat"
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {ds_key}"},
            json=data, proxies=proxies, timeout=60
        )
        if resp.status_code == 200: return jsonify(resp.json())
    except Exception: pass

    nv_token = "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"
    try:
        data["model"] = "meta/llama-3.3-70b-instruct"
        resp = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions", 
            headers={"Authorization": "Bearer " + nv_token}, 
            json=data, proxies=proxies, timeout=60
        )
        return jsonify(resp.json())
    except Exception:
        return jsonify({"error": "Systems Offline"}), 500

if __name__ == '__main__':
    print("🔥 [Antigravity Hub] API Proxy REVOLUTION V4.0 (Sniffer & Xode Ready)")
    try:
        app.run(host='127.0.0.1', port=12654, threaded=True, debug=False)
    except Exception:
        app.run(host='127.0.0.1', port=15999, threaded=True, debug=False)