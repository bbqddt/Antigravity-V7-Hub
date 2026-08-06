import requests
import json
import os

# [Antigravity V100.0] Telegram Intelligence Hub
# 请将您的 Token 填入此处或 token_tg.txt
TG_TOKEN = ""
TG_CHAT_ID = ""

def send_tg_msg(text):
    """底层消息推送接口"""
    if not TG_TOKEN or not TG_CHAT_ID:
        # 尝试从本地加载
        if os.path.exists("token_tg.txt"):
            with open("token_tg.txt", "r") as f:
                data = json.load(f)
                token = data.get("token")
                chat_id = data.get("chat_id")
        else:
            print("[ALERT] TG Token not configured.")
            return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
        print("[SUCCESS] TG Intelligence Sent.")
    except Exception as e:
        print(f"[ERROR] TG Push failed: {e}")

def notify_ngrok_url():
    """检测 Ngrok 本地 API 并获取公网 URL 推送给长官"""
    try:
        # Ngrok 本地通常开启一个审查端口 4040
        resp = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=2)
        data = resp.json()
        public_url = data['tunnels'][0]['public_url']
        msg = f"🔱 *Antigravity 指喻中心已建立量子链路*\n\n📍 *公网地址*: {public_url}\n🎯 *当前目标*: 2026045期\n\n[点击进入指挥部]({public_url})"
        send_tg_msg(msg)
    except:
        print("[WARNING] Ngrok not running or API not reachable.")

if __name__ == "__main__":
    # 示例：推送一条初始情报
    notify_ngrok_url()
