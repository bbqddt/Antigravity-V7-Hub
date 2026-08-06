from pyngrok import ngrok
import os
import time
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent

def start_ngrok_warfare():
    print("[Antigravity] Ngrok Warfare - Initializing...")

    # 自动获取令牌
    token_path = _BASE_DIR / "ngrok_token.txt"
    if token_path.exists():
        with open(token_path, "r") as f:
            token = f.read().strip()
            # 兼容处理带 'ngrok config add-authtoken' 前缀的情况
            if 'authtoken' in token:
                token = token.split('authtoken ')[-1]
            ngrok.set_auth_token(token)
            print("OK: Token injected.")

    try:
        # 强制开启 8501 隧道
        public_url = ngrok.connect(8501).public_url
        print(f"Ngrok 隧道已合龙！全球入口: {public_url}")

        # 同步给 127 指挥塔
        decision_path = _BASE_DIR / "latest_decision.json"
        if decision_path.exists():
            import json
            with open(decision_path, "r", encoding='utf-8') as f:
                res = json.load(f)
                res['public_url_ngrok'] = public_url
            with open(decision_path, "w", encoding='utf-8') as f:
                json.dump(res, f, ensure_ascii=False, indent=4)
            print("状态已同步至 127 观测塔。")
        else:
            print("Warning: latest_decision.json not found, skipping sync.")
        
        # 保持运行
        while True:
            time.sleep(100)
    except Exception as e:
        print(f"❌ Ngrok 点火失败: {e}")

if __name__ == "__main__":
    start_ngrok_warfare()
