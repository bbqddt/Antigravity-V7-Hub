import requests
import json
import time

TOKEN_FILE = r"E:\享中\token_tg.txt"

PROXY_CANDIDATES = [
    {"http": "socks5h://127.0.0.1:10808", "https": "socks5h://127.0.0.1:10808"},
    {"http": "http://127.0.0.1:10808",    "https": "http://127.0.0.1:10808"},
    {"http": "socks5h://127.0.0.1:7890",  "https": "socks5h://127.0.0.1:7890"},
    {"http": "http://127.0.0.1:7890",     "https": "http://127.0.0.1:7890"},
]

def sniff_proxy():
    for proxies in PROXY_CANDIDATES:
        try:
            r = requests.get("https://api.telegram.org", proxies=proxies, timeout=5)
            if r.status_code == 200:
                proto = list(proxies.values())[0].split("://")[0]
                port = list(proxies.values())[0].split(":")[-1]
                print(f"[OK] 代理: {proto}://127.0.0.1:{port}")
                return proxies
        except Exception as e:
            proto = list(proxies.values())[0].split("://")[0]
            port = list(proxies.values())[0].split(":")[-1]
            print(f"[FAIL] {proto}://127.0.0.1:{port} -> {type(e).__name__}")
    try:
        r = requests.get("https://api.telegram.org", timeout=5)
        if r.status_code == 200:
            print("[OK] 直连成功")
            return {}
    except Exception as e:
        print(f"[FAIL] 直连 -> {e}")
    return None

with open(TOKEN_FILE) as f:
    config = json.load(f)

print(f"Token: {config['token'][:20]}...")
proxies = sniff_proxy()
print(f"使用代理: {proxies}")

if proxies is not None:
    url = f"https://api.telegram.org/bot{config['token']}/sendMessage"
    payload = {"chat_id": config['chat_id'], "text": "✅ Hermes V8.2 已上线！嗅探代理修复完成，系统恢复正常监听。发送 /strike 开始演算。", "parse_mode": "Markdown"}
    r = requests.post(url, json=payload, proxies=proxies if proxies else None, timeout=15)
    print(f"发送结果: {r.status_code} -> {r.text[:200]}")
else:
    print("无可用代理，无法发送 TG 消息")
