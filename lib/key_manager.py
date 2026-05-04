import json
import os

# [Antigravity Omega] 多维云端秘钥仓
KEYS_FILE = r"e:\享中\keys.json"

def init_keys():
    default_keys = {
        "openrouter": "",
        "github": "",
        "huggingface": "",
        "local_ollama": "http://localhost:11434"
    }
    
    # 尝试继承旧 token
    if os.path.exists(r"e:\享中\token.txt"):
        with open(r"e:\享中\token.txt", "r") as f:
            default_keys["openrouter"] = f.read().strip()
            
    if not os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, "w") as f:
            json.dump(default_keys, f, indent=4)
    return default_keys

def get_key(provider):
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, "r") as f:
            return json.load(f).get(provider, "")
    return ""

init_keys()
