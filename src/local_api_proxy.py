# -*- coding: utf-8 -*-
"""
Antigravity 统一 API 代理 V5.0
===============================
路由层：Claude CLI → OpenRouter → Together AI → DeepSeek → NVIDIA
所有 Key 从 keys.json / .env 动态加载，不再硬编码。
"""

from pathlib import Path
from flask import Flask, request, jsonify
import requests
import json
import sys
import os
import logging

# ─── 日志配置（使用 logging 而非重定向 stdout）─────────────
_BASE_DIR = Path(__file__).resolve().parent
_LOG_FILE = _BASE_DIR / "local_api_runtime.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(str(_LOG_FILE), encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("LocalAPIProxy")

app = Flask(__name__)

_KEYS_FILE = _BASE_DIR / "keys.json"
_ARSENAL_FILE = _BASE_DIR / "arsenal.json"
_ENV_FILE = _BASE_DIR / ".env"
_LOTTERY_FILE = _BASE_DIR / "data" / "lottery_history.csv"

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
    if os.path.exists(_ARSENAL_FILE):
        with open(_ARSENAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def load_keys_json():
    """从 keys.json 读取 API Key"""
    if os.path.exists(_KEYS_FILE):
        with open(_KEYS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_env_vars():
    """从 .env 文件读取环境变量"""
    env_vars = {}
    if os.path.exists(_ENV_FILE):
        with open(_ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, val = line.split('=', 1)
                    env_vars[key.strip()] = val.strip()
    return env_vars


def get_openrouter_token():
    """获取 OpenRouter token（从 keys.json 或 .env）"""
    pool = get_keys_pool()
    if pool:
        return pool[0]
    keys = load_keys_json()
    if keys.get("openrouter"):
        return keys["openrouter"]
    env = load_env_vars()
    return env.get("OPENROUTER_API_KEY", "")


def get_together_key():
    """获取 Together AI key"""
    keys = load_keys_json()
    return keys.get("together", "") or os.environ.get("TOGETHER_API_KEY", "")


def get_deepseek_key():
    """获取 DeepSeek key"""
    keys = load_keys_json()
    return keys.get("deepseek", "") or os.environ.get("DEEPSEEK_API_KEY", "")


def get_nv_token():
    """获取 NVIDIA API token"""
    keys = load_keys_json()
    return keys.get("nvidia", "") or os.environ.get("NVIDIA_API_KEY", "")


def rotate_key(current_key):
    """从 arsenal 中移除失效 key"""
    pool = get_keys_pool()
    if current_key in pool:
        pool.remove(current_key)
        with open(_ARSENAL_FILE, "w", encoding="utf-8") as f:
            json.dump(pool, f, indent=4)


def get_lottery_context():
    try:
        if os.path.exists(_LOTTERY_FILE):
            with open(_LOTTERY_FILE, 'r', encoding='utf-8') as f:
                content = f.read().splitlines()
                recent = "\n".join(content[-20:])
                return f"\n[CRITICAL DATA: RECENT 20 PERIODS]\n{recent}\n"
    except Exception:
        pass
    return ""


# ─── Routes ────────────────────────────────────────────────

@app.route('/v1/models', methods=['GET'])
def list_models():
    models = [
        {"id": "anthropic/claude-3.5-sonnet", "object": "model", "created": 1677610602, "owned_by": "antigravity"},
        {"id": "meta-llama/Llama-3.3-70B-Instruct-Turbo", "object": "model", "created": 1677610602, "owned_by": "antigravity"},
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

    # 拦截高级模块请求
    if model in ["claude-xode-physical", "codex-logic-resolver"]:
        print(f"[EVOLUTION] Engaging Next-Gen Module: {model}")
        data["model"] = "meta-llama/Llama-3.3-70B-Instruct-Turbo"

    proxies = sniff_best_proxy()

    # 1. Claude CLI 隧道 (8090)
    if "claude" in model.lower():
        try:
            resp = requests.post("http://127.0.0.1:8090/v1/chat/completions", json=data, timeout=60)
            if resp.status_code == 200:
                return jsonify(resp.json())
        except Exception:
            pass

    # 2. OpenRouter (免费额度)
    or_token = get_openrouter_token()
    if or_token:
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {or_token}"},
                json=data, proxies=proxies, timeout=60
            )
            if resp.status_code == 200:
                return jsonify(resp.json())
            elif resp.status_code in [401, 429]:
                rotate_key(or_token)
        except Exception:
            pass

    # 3. Together AI
    together_key = get_together_key()
    if together_key:
        try:
            data["model"] = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
            resp = requests.post(
                "https://api.together.xyz/v1/chat/completions",
                headers={"Authorization": f"Bearer {together_key}"},
                json=data, proxies=proxies, timeout=60
            )
            if resp.status_code == 200:
                return jsonify(resp.json())
        except Exception:
            pass

    # 4. DeepSeek
    ds_key = get_deepseek_key()
    if ds_key:
        try:
            data["model"] = "deepseek-chat"
            resp = requests.post(
                "https://api.deepseek.com/chat/completions",
                headers={"Authorization": f"Bearer {ds_key}"},
                json=data, proxies=proxies, timeout=60
            )
            if resp.status_code == 200:
                return jsonify(resp.json())
        except Exception:
            pass

    # 5. NVIDIA
    nv_token = get_nv_token()
    if nv_token:
        try:
            data["model"] = "meta/llama-3.3-70b-instruct"
            resp = requests.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={"Authorization": "Bearer " + nv_token},
                json=data, proxies=proxies, timeout=60
            )
            return jsonify(resp.json())
        except Exception:
            pass

    return jsonify({"error": "All API providers offline"}), 500


if __name__ == '__main__':
    print("[Antigravity Hub] API Proxy V5.0 (Dynamic Key Loading)")
    try:
        app.run(host='127.0.0.1', port=12654, threaded=True, debug=False)
    except Exception:
        app.run(host='127.0.0.1', port=15999, threaded=True, debug=False)
