"""
Antigravity Hermes Agent V8.3
使用 python-telegram-bot + httpx[socks] 彻底解决 SSL EOF 问题。
"""

import asyncio
import json
import os
import re
import subprocess
import sys
import ctypes
import time
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

log_file = open(r"E:\享中\tg_runtime.log", "a", encoding="utf-8")
sys.stdout = log_file
sys.stderr = log_file

TOKEN_FILE = r"E:\享中\token_tg.txt"
BASE_DIR = r"E:\享中"
VENV_PYTHON = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")
V8_CORE = os.path.join(BASE_DIR, "Antigravity_V8_Core.py")
DECISION_FILE = os.path.join(BASE_DIR, "latest_decision_v8.json")

# 候选代理: socks5h 优先（让代理解析 DNS）
PROXY_LIST = [
    "socks5://127.0.0.1:10808",
    "socks5://127.0.0.1:7890",
    "socks5://127.0.0.1:1080",
    "http://127.0.0.1:10808",
    "http://127.0.0.1:7890",
]


def load_config():
    with open(TOKEN_FILE, "r") as f:
        return json.load(f)


def trigger_local_alert(title, msg):
    ctypes.windll.user32.MessageBoxW(0, msg, title, 0x40000 | 0x00000040)


def sniff_proxy_sync():
    """同步嗅探：用 httpx 直接测试各代理，返回第一个可用的"""
    import httpx
    for proxy in PROXY_LIST:
        try:
            with httpx.Client(proxy=proxy, timeout=5, verify=False) as client:
                r = client.get("https://api.telegram.org")
                if r.status_code == 200:
                    print(f"[嗅探雷达] 可用通道: {proxy}", flush=True)
                    return proxy
        except Exception:
            pass
    # 尝试直连
    try:
        import httpx
        with httpx.Client(timeout=5) as client:
            r = client.get("https://api.telegram.org")
            if r.status_code == 200:
                print("[嗅探雷达] 直连成功", flush=True)
                return None  # None 表示不需要代理
    except Exception:
        pass
    print("[嗅探雷达] 所有通道不可用", flush=True)
    return "DEAD"


def run_v8_and_get_result(group_count):
    """同步运行 V8 核心，返回 (message_str, raw_str) 或 (None, error_str)"""
    try:
        subprocess.run(
            [VENV_PYTHON, V8_CORE, str(group_count)],
            cwd=BASE_DIR,
            timeout=120,
            check=True
        )
        if os.path.exists(DECISION_FILE):
            with open(DECISION_FILE, "r", encoding="utf-8") as f:
                res = json.load(f)
            period = res.get("target_period", "未知")
            groups = res.get("groups", [])
            engine = res.get("engine", "V8 Zero-T")

            msg = f"*Antigravity V8 演算完毕*\n目标期号: `{period}`\n\n"
            raw = f"【期号 {period}】演算完成！\n"
            for idx, g in enumerate(groups, 1):
                b = g["blue"]
                blue_str = f"{int(b):02d}" if str(b).isdigit() else str(b)
                msg += f"*第{idx}组*: [{g['red']}] | 蓝球 `{blue_str}`\n"
                raw += f"第{idx}组: 红 {g['red']} | 蓝 {blue_str}\n"
            msg += f"\n引擎: `{engine}`"
            return msg, raw
        else:
            return None, "演算完成但未找到 latest_decision_v8.json"
    except Exception as e:
        return None, f"V8 核心启动失败: {e}"


async def cmd_strike(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_cmd = update.message.text
    cmd = raw_cmd.lower()
    match = re.search(r"计算(\d+)组", cmd)
    group_count = int(match.group(1)) if match else 3

    await update.message.reply_text(
        f"*Hermes Agent V8.3 确认*: 收到 `{raw_cmd}`\n"
        f"正在启动 V8 物理引擎，目标组数：{group_count}...",
        parse_mode="Markdown"
    )

    loop = asyncio.get_event_loop()
    tg_msg, raw_msg = await loop.run_in_executor(None, run_v8_and_get_result, group_count)

    if tg_msg:
        await update.message.reply_text(tg_msg, parse_mode="Markdown")
    else:
        await update.message.reply_text(f"演算失败: {raw_msg}")
        trigger_local_alert("Antigravity 警报", raw_msg)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url_file = os.path.join(BASE_DIR, "tunnel_url.txt")
    public_url = open(url_file).read().strip() if os.path.exists(url_file) else "Tunnel-Offline"
    await update.message.reply_text(
        f"*Antigravity V8.3 系统态势*\n"
        f"Hermes Agent: ONLINE\n"
        f"公网链路: {public_url}\n"
        f"引擎: V8 Zero-T (物理张力版)",
        parse_mode="Markdown"
    )


async def msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if "/strike" in text or "执行" in text or "计算" in text:
        await cmd_strike(update, context)
    elif "/status" in text or "状态" in text:
        await cmd_status(update, context)
    else:
        await update.message.reply_text(
            "*Hermes V8*: 发送 `计算N组` 或 `/strike` 开始演算",
            parse_mode="Markdown"
        )


def main():
    config = load_config()
    token = config["token"]

    # 嗅探代理
    proxy_url = sniff_proxy_sync()
    if proxy_url == "DEAD":
        print("[警告] 无可用代理，尝试直连启动 Bot（可能失败）", flush=True)
        proxy_url = None  # 尝试直连

    print(f"[启动] 使用代理: {proxy_url}", flush=True)

    # 用 httpx 的 socks 代理构建 Request 对象
    if proxy_url:
        request = HTTPXRequest(proxy=proxy_url)
    else:
        request = HTTPXRequest()

    app = (
        Application.builder()
        .token(token)
        .request(request)
        .build()
    )

    app.add_handler(CommandHandler("strike", cmd_strike))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_handler))

    print("[Antigravity] Hermes Agent V8.3 正在启动 polling...", flush=True)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
