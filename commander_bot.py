"""
Antigravity Commander Bot V1.0
常驻 Telegram Bot 主控系统
基于 requests 同步实现（彻底绕过 httpx SSL 问题）

用法:
    python commander_bot.py          # 启动常驻 Bot
    python commander_bot.py --once   # 单次运行一轮

依赖:
    pip install requests beautifulsoup4 pandas
"""

import json
import os
import re
import subprocess
import sys
import time
import logging
from pathlib import Path

# Fix Windows GBK encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# 延迟导入 data_layer（避免启动时加载慢）
def get_latest_period(draws=None):
    from data_layer import get_latest_period as _glp
    if draws is None:
        from data_layer import load_history
        draws = load_history()
    return _glp(draws)

# Force absolute paths — use current script location
_BASE_DIR = Path(__file__).resolve().parent
_SKILLS_DIR = _BASE_DIR / "skills"
# Logging
_LOG_DIR = _BASE_DIR / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_LOG_FILE = _LOG_DIR / "commander_bot.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(_LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logging.raiseExceptions = False
logger = logging.getLogger("CommanderBot")

# ---------------------------------------------------------------------------
# Config Loading
# ---------------------------------------------------------------------------

def load_tg_config():
    """从 token_tg.txt 或环境变量加载 TG 配置"""
    # 优先使用环境变量
    if TG_TOKEN:
        token = TG_TOKEN
        chat_id = int(TG_CHAT_ID) if TG_CHAT_ID else 0
        return token, chat_id

    token_file = _BASE_DIR / "token_tg.txt"
    if token_file.exists():
        try:
            with open(token_file, "r") as f:
                data = json.load(f)
                return data.get("token", ""), data.get("chat_id", "")
        except (json.JSONDecodeError, IOError):
            pass
    return "", ""

def load_latest_decision():
    # 第一优先级: orchestrator 统一输出
    fpath = _BASE_DIR / "latest_prediction.json"
    if fpath.exists():
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "groups" in data or "predictions" in data:
                return data
    # 第二优先级: evolved 多组预测
    fpath = _BASE_DIR / "latest_predictions_evolved.json"
    if fpath.exists():
        with open(fpath, "r", encoding="utf-8") as f:
            return json.load(f)
    # 第三优先级: legacy 单组
    for fname in ["latest_decision_v8.json", "latest_decision.json"]:
        fpath = _BASE_DIR / fname
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f:
                return json.load(f)
    return None

def load_evolution_state():
    state_file = _BASE_DIR / "evolution_state.json"
    if state_file.exists():
        with open(state_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

# ---------------------------------------------------------------------------
# Telegram API (pure requests)
# ---------------------------------------------------------------------------

import requests

TG_BASE = "https://api.telegram.org"

def tg_api(method, data=None, timeout=30, proxy_url=None):
    """封装 Telegram Bot API 请求"""
    token = TOKEN  # Use module-level global
    url = "%s/bot%s/%s" % (TG_BASE, token, method)
    proxies = None
    if proxy_url and proxy_url != "DEAD":
        proxies = {"https": proxy_url, "http": proxy_url}
    try:
        r = requests.post(url, json=data, timeout=timeout, proxies=proxies)
        result = r.json()
        if isinstance(result, dict) and result.get("ok"):
            return result.get("result")
        else:
            logger.error("TG API %s failed: %s", method, result)
            return None
    except Exception as e:
        logger.error("TG API %s exception: %s", method, e)
        return None

def tg_send_message(chat_id, text, parse_mode="Markdown"):
    return tg_api("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }, proxy_url=PROXY)

# ---------------------------------------------------------------------------
# Proxy Sniffing
# ---------------------------------------------------------------------------

PROXY_LIST = [
    "http://127.0.0.1:10808",
    "socks5://127.0.0.1:10808",
    "http://127.0.0.1:7890",
    "socks5://127.0.0.1:7890",
    "socks5://127.0.0.1:1080",
]

def sniff_proxy():
    for proxy in PROXY_LIST:
        try:
            r = requests.get("https://api.telegram.org", proxies={"https": proxy}, timeout=5)
            if r.status_code == 200:
                logger.info("Proxy OK: %s", proxy)
                return proxy
        except Exception:
            pass
    try:
        r = requests.get("https://api.telegram.org", timeout=5)
        if r.status_code == 200:
            logger.info("Direct connection OK")
            return None
    except Exception:
        pass
    logger.warning("All connections dead")
    return "DEAD"

# ---------------------------------------------------------------------------
# Engine Dispatch
# ---------------------------------------------------------------------------

def _find_python():
    for base in [_PRIMARY, _WORK]:
        venv_py = base / ".venv" / "Scripts" / "python.exe"
        if venv_py.exists():
            return str(venv_py)
    return sys.executable

def run_evolution_life():
    evolver = _SKILLS_DIR / "evolution_life.py"
    if not evolver.exists():
        return None, "evolution_life.py not found"
    python = _find_python()
    try:
        result = subprocess.run([python, str(evolver)], cwd=str(_BASE_DIR), timeout=180, capture_output=True, text=True)
        if result.returncode == 0:
            return load_latest_decision(), result.stdout[-500:]
        return None, result.stderr[-500:]
    except subprocess.TimeoutExpired:
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

def run_evolved_predictor():
    pred_script = _BASE_DIR / "evolved_predictor.py"
    if not pred_script.exists():
        return None, "evolved_predictor.py not found"
    python = _find_python()
    try:
        result = subprocess.run([python, str(pred_script)], cwd=str(_BASE_DIR), timeout=120, capture_output=True, text=True)
        if result.returncode == 0:
            return load_latest_decision(), result.stdout[-500:]
        return None, result.stderr[-500:]
    except Exception as e:
        return None, str(e)

def run_v8_core(group_count=3):
    v8 = _BASE_DIR / "Antigravity_V8_Core.py"
    if not v8.exists():
        return None, "Antigravity_V8_Core.py not found"
    python = _find_python()
    try:
        result = subprocess.run([python, str(v8), str(group_count)], cwd=str(_BASE_DIR), timeout=300, capture_output=True, text=True)
        if result.returncode == 0:
            return load_latest_decision(), result.stdout[-500:]
        return None, result.stderr[-500:]
    except Exception as e:
        return None, str(e)

def run_data_fetch():
    fetcher = _BASE_DIR / "data_updater_v2.py"
    if not fetcher.exists():
        return None, "data_updater_v2.py not found"
    python = _find_python()
    try:
        result = subprocess.run([python, str(fetcher)], cwd=str(_BASE_DIR), timeout=120, capture_output=True, text=True)
        return result.returncode == 0, result.stdout[-500:]
    except Exception as e:
        return False, str(e)

def run_backtest():
    bt = _BASE_DIR / "backtest_and_evolve.py"
    if not bt.exists():
        return None, "backtest_and_evolve.py not found"
    python = _find_python()
    try:
        result = subprocess.run([python, str(bt)], cwd=str(_BASE_DIR), timeout=300, capture_output=True, text=True)
        return result.returncode == 0, result.stdout[-1000:]
    except Exception as e:
        return False, str(e)

def run_auto_pipeline():
    steps = []
    python = _find_python()
    fetcher = _SKILLS_DIR / "truth_fetcher.py"
    if fetcher.exists():
        try:
            r = subprocess.run([python, str(fetcher)], cwd=str(_BASE_DIR), timeout=120, capture_output=True, text=True)
            steps.append("数据抓取: %s" % ("OK" if r.returncode == 0 else "FAIL"))
        except Exception as e:
            steps.append("数据抓取: 异常 %s" % e)
    pred = _BASE_DIR / "evolved_predictor.py"
    if pred.exists():
        try:
            r = subprocess.run([python, str(pred)], cwd=str(_BASE_DIR), timeout=120, capture_output=True, text=True)
            steps.append("预测引擎: %s" % ("OK" if r.returncode == 0 else "FAIL"))
        except Exception as e:
            steps.append("预测引擎: 异常 %s" % e)
    else:
        evolver = _SKILLS_DIR / "evolution_life.py"
        if evolver.exists():
            try:
                r = subprocess.run([python, str(evolver)], cwd=str(_BASE_DIR), timeout=180, capture_output=True, text=True)
                steps.append("Evolution Life: %s" % ("OK" if r.returncode == 0 else "FAIL"))
            except Exception as e:
                steps.append("Evolution Life: 异常 %s" % e)
    return "; ".join(steps)

# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------

def generate_status_report():
    lines = ["*🔱 Antigravity 系统态势报告*"]
    lines.append("")
    csv_file = _BASE_DIR / "data/lottery_history.csv"
    if csv_file.exists():
        import pandas as pd
        df = pd.read_csv(csv_file)
        periods = pd.to_numeric(df.iloc[:, 0], errors="coerce").dropna()
        total = len(periods)
        lines.append("📊 历史数据: %d 期" % total)
        # 找最新一期 — 用 enhanced_predictor 的 load_data 清洗
        try:
            sys.path.insert(0, str(_BASE_DIR))
            from enhanced_predictor import load_data as clean_load
            clean_df = clean_load()
            if len(clean_df) > 0:
                latest = clean_df.iloc[0]
                lines.append("   最新期号: `%s` | 红球: [%s] | 蓝球: `%s`" % (
                    latest["period"], latest["red"], latest["blue"]))
        except Exception as e:
            lines.append("   (数据解析异常: %s)" % e)
    else:
        lines.append("❌ 历史数据文件缺失")

    decision = load_latest_decision()
    if decision:
        # Handle multi-group formats
        if "predictions" in decision:
            target = decision["target_period"]
            lines.append("🎯 最新预测: `%d` 期 (%d 组)" % (target, len(decision["predictions"])))
            for p in decision["predictions"]:
                g = p.get("group", "?")
                reds = ", ".join(["%02d" % r for r in p["reds"]])
                blue = "%02d" % p["blue"]
                strat = p.get("strategy", "")
                lines.append("   组%d [%s]: 🔴[%s] 🔵%s" % (g, strat, reds, blue))
        elif "groups" in decision:
            target = decision.get("target_period", "?")
            lines.append("🎯 最新预测: `%s` 期 (%d 组)" % (target, len(decision["groups"])))
            for i, g in enumerate(decision["groups"], 1):
                lines.append("   组%d: 🔴[%s] 🔵%02d (评分:%s)" % (i, g["red"], g["blue"], g.get("score", "?")))
        else:
            period = decision.get("period", decision.get("target_period", "未知"))
            reds = decision.get("red", [])
            blue = decision.get("blue", "")
            engine = decision.get("engine", "未知")
            if isinstance(reds, list):
                red_str = ", ".join(["%02d" % r if isinstance(r, int) else str(r) for r in reds])
            else:
                red_str = str(reds)
            lines.append("🎯 最新预测: `%s` 期" % period)
            lines.append("   🔴 红球: [%s]" % red_str)
            lines.append("   🔵 蓝球: `%s`" % blue)
            lines.append("   ⚙️ 引擎: `%s`" % engine)
    else:
        lines.append("⚠️ 暂无最新预测数据")

    engines = []
    for name, path in [
        ("Evolution Life", _SKILLS_DIR / "evolution_life.py"),
        ("Evolved Predictor", _BASE_DIR / "evolved_predictor.py"),
        ("V8 Core", _BASE_DIR / "Antigravity_V8_Core.py"),
        ("Backtest", _BASE_DIR / "backtest_and_evolve.py"),
    ]:
        if path.exists():
            engines.append("✅ %s" % name)
        else:
            engines.append("❌ %s" % name)
    lines.append("")
    lines.append("*引擎状态:*")
    lines.extend("   %s" % e for e in engines)
    lines.append("")
    lines.append("🕐 %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    return "\n".join(lines)

def generate_prediction_report(decision):
    if not decision:
        return "❌ 未获取到预测结果"

    # Format 1: latest_predictions_evolved.json
    if "predictions" in decision:
        lines = ["💠 *Antigravity 推演结果*", "🎯 目标期号: `%d`" % decision["target_period"]]
        for p in decision["predictions"]:
            g = p.get("group", "?")
            reds = ", ".join(["%02d" % r for r in p["reds"]])
            blue = "%02d" % p["blue"]
            strat = p.get("strategy", "")
            lines.append("组%d [%s]: 🔴[%s] 🔵%s" % (g, strat, reds, blue))
        lines.append("📅 %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
        return "\n".join(lines)

    # Format 2: latest_decision_v8.json
    if "groups" in decision:
        engine = decision.get("engine", "V8")
        target = decision.get("target_period", "?")
        lines = ["💠 *Antigravity V8 推演结果*", "🎯 目标期号: `%s`" % target, "⚙️ 引擎: `%s`" % engine]
        for i, g in enumerate(decision["groups"], 1):
            reds = g["red"]
            blue = "%02d" % g["blue"]
            score = g.get("score", "?")
            lines.append("组%d: 🔴[%s] 🔵%s (评分:%s)" % (i, reds, blue, score))
        lines.append("📅 %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
        return "\n".join(lines)

    # Format 3: latest_decision.json (single prediction)
    period = decision.get("period", decision.get("target_period", "未知"))
    reds = decision.get("red", [])
    blue = decision.get("blue", "")
    engine = decision.get("engine", "未知")
    if isinstance(reds, list):
        red_str = ", ".join(["%02d" % r if isinstance(r, int) else str(r) for r in reds])
    else:
        red_str = str(reds)
    return (
        "💠 *Antigravity 推演结果*\n"
        "🎯 目标期号: `%s`\n"
        "🔴 红球: [%s]\n"
        "🔵 蓝球: `%s`\n"
        "⚙️ 引擎: `%s`\n"
        "📅 %s"
        % (period, red_str, blue, engine, time.strftime("%Y-%m-%d %H:%M:%S"))
    )

# ---------------------------------------------------------------------------
# Command Dispatch
# ---------------------------------------------------------------------------

COMMAND_ACTIONS = {
    "/strike": "run_strike",
    "/status": "show_status",
    "/fetch": "run_fetch",
    "/backtest": "run_backtest",
    "/pipeline": "run_pipeline",
    "/help": "show_help",
    "/predict": "run_strike",
}

def show_help_text():
    return (
        "*🔱 Antigravity 指挥官 Bot*\n\n"
        "*可用指令:*\n"
        "• `/strike` 或 `/计算` — 执行推演\n"
        "• `/status` 或 `/状态` — 系统态势报告\n"
        "• `/fetch` 或 `/抓取` — 拉取最新数据\n"
        "• `/backtest` — 运行回测\n"
        "• `/pipeline` — 完整流水线（抓取+预测）\n"
        "• `/help` 或 `/命令` — 显示此帮助\n\n"
        "*自然语言:*\n"
        "发送任意包含「计算」「推演」「预测」的消息将触发推演\n"
        "发送任意包含「状态」「态势」的消息将显示系统状态"
    )

def execute_action(chat_id, action, text=""):
    """同步执行动作"""
    if action == "show_status":
        report = generate_status_report()
        tg_send_message(chat_id, report)
        return
    if action == "show_help":
        tg_send_message(chat_id, show_help_text())
        return
    if action == "run_fetch":
        tg_send_message(chat_id, "🔄 正在拉取最新开奖数据...")
        ok, output = run_data_fetch()
        if ok:
            tg_send_message(chat_id, "✅ 数据抓取成功!\n\n%s" % output[-300:])
        else:
            tg_send_message(chat_id, "❌ 数据抓取失败:\n%s" % output)
        return
    if action == "run_backtest":
        tg_send_message(chat_id, "🔄 正在运行回测...")
        ok, output = run_backtest()
        if ok:
            tg_send_message(chat_id, "✅ 回测完成!\n\n%s" % output[-500:])
        else:
            tg_send_message(chat_id, "❌ 回测失败:\n%s" % output)
        return
    if action == "run_pipeline":
        tg_send_message(chat_id, "🔄 正在运行完整流水线 (数据抓取 -> 预测)...")
        steps = run_auto_pipeline()
        tg_send_message(chat_id, "✅ 流水线完成:\n\n%s" % steps)
        decision = load_latest_decision()
        if decision:
            report = generate_prediction_report(decision)
            tg_send_message(chat_id, report)
        return
    if action == "run_strike":
        match = re.search(r"计算(\d+)组", text)
        group_count = int(match.group(1)) if match else 5
        tg_send_message(
            chat_id,
            "🔱 *Antigravity 指挥官确认*:\n正在启动推演引擎，目标组数：%d..." % group_count,
        )
        # 第一优先级: orchestrator.py (融合多引擎)
        orch_script = _BASE_DIR / "orchestrate.py"
        if orch_script.exists():
            python = _find_python()
            try:
                result = subprocess.run([python, str(orch_script), "--top-k", str(group_count)],
                                        cwd=str(_BASE_DIR), timeout=120, capture_output=True, text=True)
                if result.returncode == 0:
                    decision = load_latest_decision()
                    if decision:
                        tg_send_message(chat_id, generate_prediction_report(decision))
                        return
                tg_send_message(chat_id, "⚠️ Orchestrator 输出异常，降级到单引擎...")
            except Exception as e:
                tg_send_message(chat_id, f"⚠️ Orchestrator 异常: {e}，降级...")

        # 第二优先级: Enhanced Predictor
        try:
            sys.path.insert(0, str(_BASE_DIR))
            from enhanced_predictor import run_prediction
            run_prediction(num_groups=group_count, mode="normal")
            decision = load_latest_decision()
            if decision:
                tg_send_message(chat_id, generate_prediction_report(decision))
                return
        except Exception as e:
            tg_send_message(chat_id, f"⚠️ Enhanced Predictor 异常: {e}")

        # 第三优先级: Luckcast V15 (通过 enhanced_predictor 的子接口)
        try:
            from luckcast_antigravity_v1 import rank_candidates
            from data_layer import load_history
            draws = load_history()
            preds = rank_candidates(draws, n_candidates=1000, top_k=group_count)
            if preds:
                best = preds[0]
                legacy = {
                    "period": str(get_latest_period(draws) + 1),
                    "red": list(best[0]),
                    "blue": int(best[1]),
                    "engine": "Luckcast V15",
                    "scores": best[2],
                }
                with open(_BASE_DIR / "latest_decision.json", "w", encoding="utf-8") as f:
                    json.dump(legacy, f, ensure_ascii=False, indent=2)
                tg_send_message(chat_id, generate_prediction_report(legacy))
                return
        except Exception as e:
            tg_send_message(chat_id, f"⚠️ Luckcast V15 异常: {e}")

        # 第四优先级: Evolution Life
        decision, error = run_evolution_life()
        if decision:
            tg_send_message(chat_id, generate_prediction_report(decision))
            return

        tg_send_message(chat_id, "❌ 推演失败:\n所有引擎均不可用")

def dispatch_command(chat_id, text):
    text_lower = text.lower().strip()
    if text_lower in COMMAND_ACTIONS:
        execute_action(chat_id, COMMAND_ACTIONS[text_lower], text_lower)
        return
    for keyword, action in COMMAND_ACTIONS.items():
        if keyword.lower() in text_lower:
            execute_action(chat_id, action, text_lower)
            return
    if "计算" in text_lower or "推演" in text_lower or "预测" in text_lower:
        execute_action(chat_id, "run_strike", text_lower)
    elif "状态" in text_lower or "态势" in text_lower:
        execute_action(chat_id, "show_status", text_lower)
    else:
        tg_send_message(chat_id, "*Hermes*: 未识别指令。发送 /help 查看可用命令，或直接说「计算N组」开始推演")

# ---------------------------------------------------------------------------
# Main Loop (pure synchronous)
# ---------------------------------------------------------------------------

# Dynamic config loading
TG_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")
PROXY = None

# Global state
TOKEN = ""
CHAT_ID = ""

def main():
    global TOKEN, CHAT_ID, PROXY

    TOKEN, CHAT_ID = load_tg_config()
    if not TOKEN:
        logger.error("❌ 未配置 Telegram Token。请在 token_tg.txt 中填写。")
        return

    PROXY = sniff_proxy()
    if PROXY == "DEAD":
        logger.error("❌ 无可用代理且直连失败，无法连接 Telegram。")
        return

    logger.info("🔱 Antigravity Commander Bot 启动中...")

    welcome_msg = (
        "💠 *Antigravity Commander Bot V1.0 已上线*\n\n"
        "🎯 系统已接管，随时待命。\n"
        "📡 通信链路: %s\n"
        "🕐 启动时间: %s\n\n"
        "➡️ 发送 `/help` 查看可用指令。"
        % (("代理 " + PROXY) if PROXY else "直连", time.strftime("%Y-%m-%d %H:%M:%S"))
    )

    tg_send_message(CHAT_ID, welcome_msg)
    logger.info("✅ 欢迎消息已发送至 Telegram")

    logger.info("✅ Commander Bot 已上线！等待指令...")

    # Main polling loop
    last_update_id = 0
    while True:
        try:
            result = tg_api("getUpdates", {"offset": last_update_id + 1, "timeout": 5})
            if result:
                for update in result:
                    uid = update.get("update_id", 0)
                    if uid <= last_update_id:
                        continue
                    last_update_id = uid

                    if "message" in update:
                        msg = update["message"]
                        chat_id = msg.get("chat", {}).get("id", 0)
                        text = msg.get("text", "").strip()
                        if text:
                            logger.info("Received from %s: %s", chat_id, text[:50])
                            dispatch_command(chat_id, text)
        except KeyboardInterrupt:
            logger.info("❌ Interrupted, shutting down...")
            tg_send_message(CHAT_ID, "*Antigravity Commander Bot 已下线*")
            break
        except Exception as e:
            logger.error("Polling error: %s", e)
            time.sleep(2)

def run_once():
    """Single run: fetch -> predict -> report"""
    logger.info("[Single Mode] Starting...")
    ok, output = run_data_fetch()
    logger.info("Data fetch: %s", "OK" if ok else "FAIL")
    decision, error = run_evolution_life()
    if not decision:
        decision, error = run_evolved_predictor()
    if not decision:
        decision, error = run_v8_core()
    if decision:
        report = generate_prediction_report(decision)
        logger.info("Prediction OK: %s", report[:100])
    else:
        logger.error("Prediction failed: %s", error)
        report = "Failed: %s" % error
    token, chat_id = load_tg_config()
    if token and chat_id:
        url = "https://api.telegram.org/bot%s/sendMessage" % token
        payload = {"chat_id": chat_id, "text": report, "parse_mode": "Markdown"}
        try:
            r = requests.post(url, json=payload, timeout=30)
            if r.status_code == 200:
                logger.info("Report sent to Telegram")
            else:
                logger.error("TG send failed: %s %s", r.status_code, r.text[:200])
        except Exception as e:
            logger.warning("TG send failed: %s", e)

if __name__ == "__main__":
    if "--once" in sys.argv:
        run_once()
    else:
        main()
