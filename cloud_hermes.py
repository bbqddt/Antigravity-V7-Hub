# -*- coding: utf-8 -*-
"""
Antigravity Cloud Hermes V8.0 - Root Level Edition
运行于 GitHub Actions 的 24/7 守护进程
安全改进：所有敏感配置从环境变量/文件加载，不硬编码
"""

import requests
import json
import os
import time
import subprocess
import sys

# ─── 动态配置 ─────────────────────────────────────────────
base_dir = os.path.dirname(os.path.abspath(__file__))
TG_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")


def get_tg_token():
    """从环境变量或 token_tg.txt 加载 Telegram Token"""
    if TG_TOKEN:
        return TG_TOKEN
    token_file = os.path.join(base_dir, "token_tg.txt")
    if os.path.exists(token_file):
        try:
            with open(token_file, "r") as f:
                data = json.load(f)
                return data.get("token", "")
        except (json.JSONDecodeError, IOError):
            pass
    return ""


def get_chat_id():
    """从环境变量或 token_tg.txt 加载 Chat ID"""
    if TG_CHAT_ID:
        return int(TG_CHAT_ID)
    token_file = os.path.join(base_dir, "token_tg.txt")
    if os.path.exists(token_file):
        try:
            with open(token_file, "r") as f:
                data = json.load(f)
                return int(data.get("chat_id", 0))
        except (json.JSONDecodeError, ValueError, IOError):
            pass
    return 0


def send_tg_msg(text, chat_id=None):
    """发送 Telegram 消息"""
    token = get_tg_token()
    if not token:
        print("[WARN] TG Token 未配置，跳过消息发送")
        return False
    if chat_id is None:
        chat_id = get_chat_id()
    if not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=15)
        return True
    except Exception:
        return False


def clear_webhook():
    """清除旧的 webhook 绑定"""
    token = get_tg_token()
    if not token:
        return
    print("[Cloud Hermes] 正在斩断旧的 Cloudflare 羁绊 (删除 Webhook)...")
    try:
        requests.get(f"https://api.telegram.org/bot{token}/deleteWebhook")
    except Exception:
        pass


def run_evolution():
    """触发流形演算：真相抓取 + 演进推演"""
    print("[Cloud Hermes] 触发流形演算...")
    try:
        evolver_path = os.path.join(base_dir, "skills", "evolution_life.py")
        subprocess.run([sys.executable, evolver_path], check=False)

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


def remote_listener():
    """Telegram 长轮询主循环"""
    clear_webhook()
    last_update_id = 0
    print("[Antigravity] Cloud Hermes Agent V8.0 现已在云端上线！等待指令...")

    # 设定脚本最大运行时间 (5 小时 50 分钟)，让 Github Actions Cron 重启它
    start_time = time.time()
    max_duration = 5 * 3600 + 50 * 60

    while time.time() - start_time < max_duration:
        try:
            token = get_tg_token()
            if not token:
                time.sleep(5)
                continue

            url = f"https://api.telegram.org/bot{token}/getUpdates?offset={last_update_id + 1}&timeout=30"
            resp = requests.get(url, timeout=35).json()

            if resp.get("ok") and resp.get("result"):
                for update in resp["result"]:
                    last_update_id = update["update_id"]
                    if "message" in update and "text" in update["message"]:
                        raw_cmd = update["message"]["text"]
                        cmd = raw_cmd.lower()
                        chat_id = update["message"]["chat"]["id"]

                        if "/strike" in cmd or "执行计划" in cmd or "计算" in cmd or "下期" in cmd:
                            send_tg_msg(
                                f"🔱 *云端 Hermes V8.0 确认*: 侦测到强计算指令『{raw_cmd}』。\n正在拉起 Github Actions 算力集群执行物理级推演...",
                                chat_id
                            )
                            res_msg = run_evolution()
                            send_tg_msg(res_msg, chat_id)

                        elif "/status" in cmd or "状态" in cmd:
                            send_tg_msg(
                                f"💠 *Antigravity 云端态势*\n节点: Github Actions Runner (Ubuntu)\nHermes Agent: 7*24 离岸巡航中\n拦截策略: 物理断绝通用 LLM 污染",
                                chat_id
                            )

                        else:
                            send_tg_msg(
                                "🤖 *Cloud Hermes V8.0*: 指令未识别。云端集群仅接受 `计算` 或 `/strike` 进行高维推演。",
                                chat_id
                            )
            time.sleep(1)
        except Exception as e:
            time.sleep(5)


if __name__ == "__main__":
    remote_listener()
