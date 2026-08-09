"""
Antigravity 云端部署脚本 V1.0
=============================
目标: 在 GitHub Actions / Cloudflare Workers / Kaggle 上持续运行
支持: 自动数据抓取 -> 预测 -> TG 汇报 全流程

用法:
    python cloud_deploy.py --once      # 单次运行
    python cloud_deploy.py --daemon    # 守护模式 (每15分钟一轮)
"""

import json
import os
import subprocess
import sys
import time
import logging
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
SKILLS_DIR = BASE_DIR / "skills"

# Telegram 配置
TG_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")

# 代理配置
PROXY_URL = os.environ.get("PROXY_URL", "")

# 日志
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "cloud_deploy.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("CloudDeploy")


# ---------------------------------------------------------------------------
# 数据抓取 (云端版 - 不依赖浏览器)
# ---------------------------------------------------------------------------

def fetch_data_cloud():
    """云端数据抓取 - 纯 requests + BS4"""
    import requests
    from bs4 import BeautifulSoup

    url = "http://datachart.500.com/ssq/history/newinc/history.php?limit=5000&sort=0"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.select("tr.t_tr1")

        data = []
        for row in rows:
            tds = row.find_all("td")
            if len(tds) >= 8:
                period = tds[0].text.strip()
                if not period.isdigit():
                    continue
                reds = ",".join([tds[i].text.strip() for i in range(1, 7)])
                blue = tds[7].text.strip()
                date = tds[15].text.strip() if len(tds) > 15 else ""
                data.append([period, reds, blue, date])

        data.sort(key=lambda x: int(x[0]), reverse=True)

        # 写入 CSV
        csv_file = BASE_DIR / "data/lottery_history.csv"
        with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
            writer = __import__("csv").writer(f)
            writer.writerow(["period", "red", "blue", "date"])
            writer.writerows(data)

        logger.info(f"✅ 数据抓取成功: {len(data)} 期")
        return True
    except Exception as e:
        logger.error(f"❌ 数据抓取失败: {e}")
        return False


# ---------------------------------------------------------------------------
# 预测引擎 (云端版 - 无 GUI)
# ---------------------------------------------------------------------------

def run_prediction_cloud():
    """云端预测 - 使用增强版预测引擎"""
    # 尝试导入 enhanced_predictor
    enh_path = BASE_DIR / "enhanced_predictor.py"
    if enh_path.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(enh_path), "--groups", "5", "--mode", "normal"],
                cwd=str(BASE_DIR),
                timeout=120,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                # 读取结果
                pred_file = BASE_DIR / "latest_decision_enhanced.json"
                if pred_file.exists():
                    with open(pred_file, "r", encoding="utf-8") as f:
                        return json.load(f)
        except Exception as e:
            logger.warning(f"Enhanced predictor 失败: {e}")

    # 降级到 evolution_life
    evol_path = SKILLS_DIR / "evolution_life.py"
    if evol_path.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(evol_path)],
                cwd=str(BASE_DIR),
                timeout=180,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                # 读取 latest_decision.json
                dec_file = BASE_DIR / "latest_decision.json"
                if dec_file.exists():
                    with open(dec_file, "r", encoding="utf-8") as f:
                        return json.load(f)
        except Exception as e:
            logger.warning(f"Evolution life 失败: {e}")

    logger.error("所有预测引擎均失败")
    return None


# ---------------------------------------------------------------------------
# Telegram 汇报
# ---------------------------------------------------------------------------

def send_tg_message(text):
    """发送 Telegram 消息"""
    if not TG_TOKEN or not TG_CHAT_ID:
        logger.warning("TG 配置缺失，跳过消息发送")
        return False

    import requests

    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
    }

    try:
        kwargs = {"headers": {"Authorization": f"Bearer {TG_TOKEN}"}, "timeout": 30}
        if PROXY_URL:
            kwargs["proxies"] = {"http": PROXY_URL, "https": PROXY_URL}
        resp = requests.post(url, json=payload, **kwargs)
        if resp.status_code == 200:
            logger.info("✅ TG 消息发送成功")
            return True
        else:
            logger.error(f"❌ TG 发送失败: {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        logger.error(f"❌ TG 发送异常: {e}")
        return False


def format_prediction_report(decision):
    """格式化预测报告"""
    if not decision:
        return "❌ 推演失败: 未获取到结果"

    period = decision.get("period", decision.get("target_period", "未知"))
    engine = decision.get("engine", "未知")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 检查是否有 predictions 数组（增强版格式）
    if "predictions" in decision:
        lines = [f"💠 *Antigravity 增强版推演结果*", f"🎯 目标期号: `{period}`", f"⚙️ 引擎: `{engine}`", f"📅 {timestamp}", ""]
        for p in decision["predictions"]:
            reds = ", ".join([f"{r:02d}" for r in p["reds"]])
            blue = f"{p['blue']:02d}"
            lines.append(f"*第{p['group']}组* [{p['strategy']}]:")
            lines.append(f"  🔴 [{reds}]  🔵 `{blue}`")
            lines.append("")
        return "\n".join(lines)
    else:
        # 旧版格式
        reds = decision.get("red", [])
        blue = decision.get("blue", "")
        if isinstance(reds, list):
            red_str = ", ".join([f"{r:02d}" if isinstance(r, int) else str(r) for r in reds])
        else:
            red_str = str(reds)
        return (
            f"💠 *Antigravity 推演结果*\n"
            f"🎯 目标期号: `{period}`\n"
            f"🔴 红球: [{red_str}]\n"
            f"🔵 蓝球: `{blue}`\n"
            f"⚙️ 引擎: `{engine}`\n"
            f"📅 {timestamp}"
        )


def send_system_alert(text):
    """发送系统告警"""
    return send_tg_message(f"🚨 *Antigravity 系统告警*\n{text}")


# ---------------------------------------------------------------------------
# 系统健康检查
# ---------------------------------------------------------------------------

def health_check():
    """系统健康检查"""
    checks = {}

    # 数据文件
    csv_file = BASE_DIR / "data/lottery_history.csv"
    checks["数据文件"] = csv_file.exists()

    # 预测引擎
    checks["增强预测器"] = (BASE_DIR / "enhanced_predictor.py").exists()
    checks["Evolution Life"] = (SKILLS_DIR / "evolution_life.py").exists()
    checks["V8 Core"] = (BASE_DIR / "Antigravity_V8_Core.py").exists()

    # TG 配置
    checks["TG Token"] = bool(TG_TOKEN)
    checks["TG Chat ID"] = bool(TG_CHAT_ID)

    # 磁盘空间
    try:
        import shutil
        total, used, free = shutil.disk_usage(BASE_DIR.parent)
        free_gb = free / (1024 ** 3)
        checks["磁盘空间(GB)"] = free_gb > 1
    except:
        pass

    return checks


# ---------------------------------------------------------------------------
# 主循环
# ---------------------------------------------------------------------------

def run_once():
    """单次运行: 数据抓取 -> 预测 -> 汇报"""
    logger.info("🔄 [单次模式] 启动...")

    # 1. 数据抓取
    if not fetch_data_cloud():
        send_system_alert("数据抓取失败，终止流程")
        return False

    # 2. 预测
    decision = run_prediction_cloud()
    if not decision:
        send_system_alert("预测引擎全部失败")
        return False

    # 3. 汇报
    report = format_prediction_report(decision)
    send_tg_message(report)

    # 4. 健康检查
    health = health_check()
    failed = [k for k, v in health.items() if not v]
    if failed:
        send_system_alert(f"以下检查项失败: {', '.join(failed)}")

    logger.info("✅ [单次模式] 完成")
    return True


def run_daemon(interval_minutes=15):
    """守护模式"""
    logger.info(f"🔄 [守护模式] 启动，间隔: {interval_minutes} 分钟")
    send_tg_message("💠 *Antigravity 云端哨兵已上线*\n📡 运行模式: 守护\n🕐 启动时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    last_run = 0
    while True:
        try:
            now = time.time()
            if now - last_run >= interval_minutes * 60:
                run_once()
                last_run = now
        except KeyboardInterrupt:
            logger.info("收到中断信号，退出")
            send_tg_message("💠 *Antigravity 云端哨兵已下线*")
            break
        except Exception as e:
            logger.error(f"守护循环异常: {e}")
            send_system_alert(f"守护循环异常: {e}")
        time.sleep(60)  # 每分钟检查一次是否该运行


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Antigravity Cloud Deploy")
    parser.add_argument("--once", action="store_true", help="单次运行")
    parser.add_argument("--daemon", action="store_true", help="守护模式")
    parser.add_argument("--interval", type=int, default=15, help="守护模式间隔(分钟)")
    parser.add_argument("--health", action="store_true", help="仅健康检查")
    args = parser.parse_args()

    if args.health:
        health = health_check()
        for k, v in health.items():
            status = "✅" if v else "❌"
            logger.info(f"  {status} {k}")
        sys.exit(0 if all(health.values()) else 1)

    if args.once:
        run_once()
    elif args.daemon:
        run_daemon(args.interval)
    else:
        # 默认单次运行
        run_once()
