import requests
import json
import os
import time
import subprocess
import sys

# [Antigravity V1000.0 Omega] Telegram Remote Hub
TOKEN_FILE = r"E:\享中\token_tg.txt"

# [Antigravity] 代理生命线配置
PROXIES = {"http": "http://127.0.0.1:10808", "https": "http://127.0.0.1:10808"}

def load_config():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    return None

def send_tg_msg(text):
    config = load_config()
    if not config: return
    url = f"https://api.telegram.org/bot{config['token']}/sendMessage"
    payload = {"chat_id": config['chat_id'], "text": text, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload, proxies=PROXIES, timeout=15)
    except: pass

def send_tg_photo(photo_path, caption):
    config = load_config()
    if not config: return
    url = f"https://api.telegram.org/bot{config['token']}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            payload = {"chat_id": config['chat_id'], "caption": caption, "parse_mode": "Markdown"}
            files = {"photo": photo}
            requests.post(url, data=payload, files=files, proxies=PROXIES, timeout=30)
    except: pass

def get_public_url():
    """多级寻址：优先读取人工配置，次选自动探测"""
    if os.path.exists("tunnel_url.txt"):
        with open("tunnel_url.txt", "r") as f:
            return f.read().strip()
    try:
        resp = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=2)
        return resp.json()['tunnels'][0]['public_url']
    except:
        return "Tunnel-Offline (Please send Ngrok URL to Bot)"

def remote_listener():
    """[Hermes-Omega] 远程指挥中枢"""
    config = load_config()
    if not config: return
    
    last_update_id = 0
    print("[Antigravity] Hermes Agent is now online. Waiting for instructions...")
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{config['token']}/getUpdates?offset={last_update_id + 1}&timeout=30"
            resp = requests.get(url, timeout=35).json()
            
            if resp.get("ok") and resp.get("result"):
                for update in resp["result"]:
                    last_update_id = update["update_id"]
                    if "message" in update and "text" in update["message"]:
                        raw_cmd = update["message"]["text"]
                        cmd = raw_cmd.lower()
                        
                        # --- 链路自愈逻辑：人工领路 (精准过滤) ---
                        if "http" in cmd and any(x in cmd for x in [".ngrok-free.app", ".ngrok.io", ".loca.lt"]):
                            if "dashboard.ngrok.com" in cmd:
                                send_tg_msg("⚠️ *Hermes 提示*: 这是管理后台链接。请发给我就那个黑窗口里显示的 `https://...ngrok-free.app` 地址。")
                                continue
                            
                            with open("tunnel_url.txt", "w") as f:
                                f.write(raw_cmd.strip())
                            send_tg_msg(f"🔱 *Hermes 报告*: 公网隧道已真实锚定！\n新入口: {raw_cmd.strip()}")
                            continue

                        public_link = get_public_url()
                        
                        if "/strike" in cmd or "执行计划" in cmd:
                            send_tg_msg(f"🔱 *Hermes Agent 确认*: 已接收长官指令『{raw_cmd}』。\n正在启动 OpenGCLow 物理对抗内核...")
                            subprocess.run([sys.executable, "-c", "from lib.orchestrator import orchestrator; orchestrator.execute_omega_strike('sk-or-fake-key', [])"])
                            send_tg_msg(f"✅ *计划已实施*！\n[点击进入全球观测台]({public_link})")
                            
                        elif "/status" in cmd or "状态" in cmd:
                            send_tg_msg(f"💠 *系统当前态势*\n\n公网链路: {public_link}\nHermes: ACTIVE\nOpenGCLow: STANDBY\n[观测塔入口]({public_link})")
                            
                        elif "操控" in cmd or "反重力" in cmd:
                            send_tg_msg("🔱 *战术分析*: 长官，反重力推演计划已全面挂载。目前的 045 期推演已引入三区引力摄动。您可以随时通过 `/strike` 触发全球同步演化。")

            time.sleep(1)
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    remote_listener()
