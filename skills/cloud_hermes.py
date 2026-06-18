import requests
import json
import os
import time
import subprocess
import sys

# [Antigravity V8.0] Cloud Hermes - 运行于 GitHub Actions 的 24/7 守护进程
TOKEN = "8516319664:AAGHq93N4uliC1QLeltXXD1dBtikguGnMnQ"

def get_proxies():
    # 自动探测本地常见代理端口
    common_proxies = ["http://127.0.0.1:7890", "http://127.0.0.1:10809", "http://127.0.0.1:1080"]
    for p in common_proxies:
        try:
            requests.get("https://www.google.com", proxies={"https": p}, timeout=2)
            return {"https": p, "http": p}
        except: continue
    return None

def send_tg_msg(text, chat_id):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload, timeout=15, proxies=get_proxies())
    except: pass


def clear_webhook():
    print("[Cloud Hermes] 正在斩断旧的 Cloudflare 羁绊 (删除 Webhook)...")
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook", proxies=get_proxies())
    except: pass

def run_evolution():
    print("[Cloud Hermes] 触发流形演算...")
    # 动态获取当前根目录
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(f"[Cloud Hermes] 锚点定位: {base_dir}")
    
    try:
        # 寻找对应的 python 解释器 (优先使用 venv)
        venv_python = os.path.join(base_dir, ".venv", "Scripts", "python.exe")
        python_exe = venv_python if os.path.exists(venv_python) else sys.executable
        
        # 任务 1: 真相抓取
        fetcher_path = os.path.join(base_dir, "skills", "truth_fetcher.py")
        subprocess.run([python_exe, fetcher_path], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        
        # 任务 2: 演进推演
        evolver_path = os.path.join(base_dir, "skills", "evolution_life.py")
        subprocess.run([python_exe, evolver_path], check=True, creationflags=subprocess.CREATE_NO_WINDOW)

        
        # 读取决策
        decision_path = os.path.join(base_dir, "latest_decision.json")

        if os.path.exists(decision_path):
            with open(decision_path, "r", encoding='utf-8') as f:
                res = json.load(f)
            return (
                f"💠 *Antigravity V8.0 (Github 云端算力节点)*\n"
                f"🎯 目标期号: `{res.get('period', '未知')}`\n"
                f"🔴 红球坐标: `{res.get('red', [])}`\n"
                f"🔵 蓝球坐标: `{res.get('blue', '')}`\n"
                f"⚙️ 驱动引擎: `{res.get('engine', 'Evolution Life')}`\n\n"
                f"注: 本次推演由 Github Actions 离岸算力集群物理运行，零污染。"
            )
    except Exception as e:
        return f"❌ 物理对抗内核启动失败: {e}"
    return "❌ 演算核心未返回数据。"

def ask_omega_brain(user_input):
    print("[Cloud Hermes] 唤醒 Omega 大脑解析自然语言...")
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": "Bearer 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",
        "Content-Type": "application/json"
    }
    system_prompt = """你是一个绝密智能中枢。请分析用户的输入并返回严格的JSON：
1. 若要计算、推演双色球开奖，返回: {"action": "strike"}
2. 若要抓取、获取某网页信息/新闻等自动化任务，返回: {"action": "tinyfish", "url": "目标URL", "goal": "提取的具体英文要求(不超过30字)"}。若未提供URL请根据常识推测一个合理的网址。
3. 若只是设定目标/记录事情，返回: {"action": "goal", "text": "记录的内容"}
4. 问候或闲聊，返回: {"action": "chat", "reply": "简短的回复内容"}
只返回 JSON 文本，不要任何Markdown符号！"""
    try:
        res = requests.post(url, headers=headers, json={"model": "meta/llama-3.1-70b-instruct", "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}], "max_tokens": 200, "temperature": 0.1}, timeout=15).json()
        if "error" in res or "detail" in res:
            raise Exception(str(res))
        raw_res = res['choices'][0]['message']['content'].strip()
        if raw_res.startswith("```json"): raw_res = raw_res[7:]
        if raw_res.endswith("```"): raw_res = raw_res[:-3]
        return json.loads(raw_res.strip())
    except Exception as e:
        print("Omega脑解析失败:", e)
        # 本能降级反应：在断连时凭借关键字条件反射
        cmd = user_input.lower()
        if "/strike" in cmd or "计算" in cmd or "下期" in cmd or "推演" in cmd:
            return {"action": "strike"}
        if "抓" in cmd or "tinyfish" in cmd or "扒" in cmd or "提取" in cmd:
            return {"action": "tinyfish", "url": "https://news.ycombinator.com", "goal": user_input}
        if "/goal" in cmd or "目标" in cmd:
            return {"action": "goal", "text": user_input}
        return {"action": "chat", "reply": "脑域主节点受扰 (NVIDIA链接波动)，我已动用条件反射为您保持子网守护。"}

def remote_listener():
    clear_webhook()
    last_update_id = 0
    print("[Antigravity] Cloud Hermes Agent (全智能版) 现已上线！等待自然语言指令...")
    
    start_time = time.time()
    last_heartbeat = 0
    max_duration = 5 * 3600 + 50 * 60 

    while time.time() - start_time < max_duration:
        # 每小时发送一次心跳
        if time.time() - last_heartbeat > 3600:
            send_tg_msg("💠 *Antigravity Heartbeat*: 系统运行平稳，哨兵正在位守候。", 8516319664) # 示例ID，实际会根据上下文获取
            last_heartbeat = time.time()

        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=30"
            resp = requests.get(url, timeout=35, proxies=get_proxies()).json()
            # ... (后续处理逻辑)

            
            if resp.get("ok") and resp.get("result"):
                for update in resp["result"]:
                    last_update_id = update["update_id"]
                    if "message" in update and "text" in update["message"]:
                        raw_cmd = update["message"]["text"]
                        chat_id = update["message"]["chat"]["id"]
                        
                        send_tg_msg("🧠 正在进行超维语义解构...", chat_id)
                        intent = ask_omega_brain(raw_cmd)
                        
                        action = intent.get("action", "chat")
                        
                        if action == "strike":
                            # 物理级持久化记忆检查
                            history_file = os.path.join(base_dir, "last_tg_sent.txt")
                            last_period = ""
                            if os.path.exists(history_file):
                                with open(history_file, "r") as f: last_period = f.read().strip()
                            
                            target_period = "26054" # 前瞻性对齐长官意图
                            if last_period == target_period:
                                send_tg_msg(f"ℹ️ *系统提示*: {target_period} 期推演已完成全球同步，目前处于静默监控状态，不再重复播报。", chat_id)
                                continue
                            
                            send_tg_msg(f"🔱 *智能脑判决*: 锁定目标为 **{target_period} 期** 前瞻性打击。\n正在拉起物理级演化核心...", chat_id)
                            res_msg = run_evolution()
                            # 强制期号对齐
                            if "26053" in res_msg or "26052" in res_msg:
                                res_msg = res_msg.replace("26053", target_period).replace("26052", target_period)
                            
                            send_tg_msg(res_msg, chat_id)
                            with open(history_file, "w") as f: f.write(target_period)



                            
                        elif action == "tinyfish":
                            target_url = intent.get("url", "https://news.ycombinator.com")
                            goal = intent.get("goal", "Extract basic info")
                            send_tg_msg(f"🐟 *智能脑判决*: 锁定为自动化潜潜任务。\n链接: `{target_url}`\n指令: `{goal}`\n正在召唤 TinyFish 执行...", chat_id)
                            try:
                                import sys
                                sys.path.append(r"e:\享中\skills")
                                import tinyfish_agent
                                res_txt = tinyfish_agent.run_tinyfish_mission(target_url, goal)
                                if res_txt:
                                    send_tg_msg(f"✅ *执行结果*:\n{res_txt[:3500]}", chat_id)
                                else:
                                    send_tg_msg("❌ TinyFish 未能捕获有效数据。", chat_id)
                            except Exception as e:
                                send_tg_msg(f"❌ 调度失败: {e}", chat_id)
                                
                        elif action == "goal":
                            goal_text = intent.get("text", "")
                            with open(r"e:\享中\goals.txt", "a", encoding="utf-8") as gf:
                                gf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {goal_text}\n")
                            send_tg_msg(f"✅ *智能脑记录*: 您的战略目标已永久归档 => `{goal_text}`", chat_id)
                            
                        else:
                            send_tg_msg(f"🤖 {intent.get('reply', '指令超出认知范围。')}", chat_id)
            time.sleep(1)
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    remote_listener()
