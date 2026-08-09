"""
告警通知器模板 — alert_notifier.py

说明:
- 该模块提供发送 Telegram 和 Email 的最小工具函数。
- 出于安全性，API Key / 凭据请通过环境变量或 CI/Secrets 注入，不要直接写入代码。
- 在配置好凭据后，cloud_daemon 在捕获 ERROR/Exception 时可以调用这些函数发送告警。

使用示例:
from scripts.alert_notifier import send_telegram, send_email
send_telegram("演进守护出现错误: ...")
send_email("Antigravity 守护错误", "详细错误日志...")

请在部署前把 TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID 或 SMTP_* 环境变量填写到你的运行环境。
"""

import os
import requests
import smtplib
from email.message import EmailMessage
from pathlib import Path


def _load_dotenv() -> None:
    env_file = Path(__file__).resolve().parents[1] / '.env'
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


def send_telegram(message: str) -> bool:
    """使用 Telegram Bot 发送消息。
    需要环境变量: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[alert_notifier] Telegram 未配置（TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID）")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"[alert_notifier] 发送 Telegram 失败: {e}")
        return False


def send_email(subject: str, body: str) -> bool:
    """通过 SMTP 发送邮件。
    需要环境变量: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, ALERT_EMAIL_TO
    """
    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    to_addr = os.environ.get("ALERT_EMAIL_TO")

    if not all([host, user, password, to_addr]):
        print("[alert_notifier] Email 未配置（SMTP_* / ALERT_EMAIL_TO）")
        return False

    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=10) as s:
            s.starttls()
            s.login(user, password)
            s.send_message(msg)
        return True
    except Exception as e:
        print(f"[alert_notifier] 发送 Email 失败: {e}")
        return False


if __name__ == "__main__":
    print("[alert_notifier] 这是一个模板文件。请配置环境变量后在代码中调用 send_telegram/send_email。")
