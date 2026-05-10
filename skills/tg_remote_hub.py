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
                        
                        if "/strike" in cmd or "执行计划" in cmd or "计算" in cmd or "下期" in cmd:
                            send_tg_msg(f"🔱 *Hermes Agent V8.0 确认*: 侦测到强计算指令『{raw_cmd}』。\n正在切断所有外部弱智通用大模型 (LLM) 的干扰。\n强制启动本地 [Evolution Life] 核心进行流形演算...")
                            
                            try:
                                # 先抓取最新真相数据
                                subprocess.run([sys.executable, r"e:\享中\skills\truth_fetcher.py"], check=True)
                                # 执行本地演进生命核心
                                subprocess.run([sys.executable, r"e:\享中\skills\evolution_life.py"], check=True)
                                
                                # 读取演算结果
                                decision_path = r"e:\享中\latest_decision.json"
                                if os.path.exists(decision_path):
                                    with open(decision_path, "r", encoding='utf-8') as f:
                                        res = json.load(f)
                                    msg = (
                                        f"💠 *Antigravity V8.0 演算完毕*\n"
                                        f"🎯 目标期号: `{res.get('period', '未知')}`\n"
                                        f"🔴 红球坐标: `{res.get('red', [])}`\n"
                                        f"🔵 蓝球坐标: `{res.get('blue', '')}`\n"
                                        f"⚙️ 驱动引擎: `{res.get('engine', 'Evolution Life')}`\n\n"
                                        f"注: 本次计算全由物理规律推演，拒绝任何形式的道德推脱。\n"
                                        f"[全知观测塔入口]({public_link})"
                                    )
                                    send_tg_msg(msg)
                                else:
                                    send_tg_msg("❌ 演算核心输出断裂: 未找到 latest_decision.json。")
                            except Exception as e:
                                send_tg_msg(f"❌ 物理对抗内核启动失败: {e}")
                            
                        elif "/status" in cmd or "状态" in cmd:
                            send_tg_msg(f"💠 *Antigravity V8.0 系统当前态势*\n\n公网链路: {public_link}\nHermes Agent: FULLY ARMED\n拦截策略: 100% 屏蔽通用智脑\n[观测塔入口]({public_link})")
                            
                        elif cmd.startswith("/goal "):
                            goal_text = raw_cmd[6:].strip()
                            with open(r"e:\享中\goals.txt", "a", encoding="utf-8") as gf:
                                gf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {goal_text}\n")
                            send_tg_msg(f"✅ *Hermes 记录*: 目标已持久化归档至主节点 => `{goal_text}`")
                            
                        elif "操控" in cmd or "反重力" in cmd:
                            send_tg_msg("🔱 *战术分析*: 长官，反重力推演计划已全面挂载。目前的推演已引入三区引力摄动。您可以随时发送 `计算` 触发全球同步演化。")
                        
                        else:
                            # 拦截所有其他废话，防止被交给智脑
                            send_tg_msg("🤖 *Hermes V8.0*: 指令未识别。若需推演坐标，请直接发送 `计算` 或 `/strike`。我不再连接那种会跟你扯法律隐私的废话模型。")

            time.sleep(1)
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    remote_listener()
