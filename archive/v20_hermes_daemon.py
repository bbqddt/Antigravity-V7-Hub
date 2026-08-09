# -*- coding: utf-8 -*-
"""
Antigravity V20.0 赫耳墨斯守护进程
核心循环：数据抓取 → 算力演进 → 置信度侦听 → 云端合龙
"""
import time
import os
import sys
import logging
import subprocess

# 确保核心路径已挂载
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from core.hermes_agent import HermesAgent
except ImportError:
    # 如果 core/ 下有 __init__.py 但无法导入，尝试直接导入
    sys.path.insert(0, os.path.join(BASE_DIR, "core"))
    from hermes_agent import HermesAgent

logging.basicConfig(
    level=logging.INFO,
    format='[DAEMON-V20] %(asctime)s - %(levelname)s: %(message)s'
)
logger = logging.getLogger("MainDaemon")


def run_hermes_cycle():
    """V20.0 核心循环：由赫耳墨斯主导的四大神格协同"""
    hermes = HermesAgent()

    while True:
        logger.info("=== 启动新一轮 V20.0 全维演进循环 ===")

        try:
            # 1. 第一神格：因果抓取 (Crawler)
            logger.info("📡 第一阶段：赫耳墨斯下发指令，启动 Genesis Crawler...")
            crawler_path = os.path.join(BASE_DIR, "core", "genesis_crawler.py")
            if os.path.exists(crawler_path):
                subprocess.run([sys.executable, crawler_path], cwd=BASE_DIR, check=False)
            else:
                logger.warning("⚠️ genesis_crawler.py 不存在，跳过数据抓取")

            # 2. 第二神格：算力演进 (Titan/Evolver)
            logger.info("🧬 第二阶段：执行本地逻辑演进 (Self-Evolver)...")
            evolver_path = os.path.join(BASE_DIR, "core", "self_evolver.py")
            if os.path.exists(evolver_path):
                subprocess.run([sys.executable, evolver_path], cwd=BASE_DIR, check=False)
            else:
                logger.warning("⚠️ self_evolver.py 不存在，跳过演进")

            # 3. 赫耳墨斯心脏跳动：置信度侦听与自主演进
            print("\n")
            if hermes.intelligence_pulse(confidence_threshold=0.92):
                logger.warning("🚨 [Hermes Insight] 检测到关键突破或逻辑偏离，触发自主演进...")
                hermes.trigger_autonomous_evolution()
            else:
                logger.info("📡 系统逻辑保持稳定，当前无需外部重写。")

            # 4. 第三神格：合龙与镜像 (Hermes Sync)
            logger.info("📡 第三阶段：执行全维合龙 (Cloud Sync)...")
            hermes.shuttle_sync()

            logger.info("✅ 循环成功结束。系统进入静默监测态。")

        except Exception as e:
            logger.error(f"❌ 循环中发生物理阻断: {e}")
            logger.error("正在尝试自愈并在 60 秒后重试...")
            time.sleep(60)
            continue

        # 设定循环间隔：默认 2 小时 (7200 秒)
        sleep_time = 7200
        logger.info(f"💤 Hermes 代理进入潜伏期，倒计时 {sleep_time} 秒...")
        time.sleep(sleep_time)


if __name__ == "__main__":
    run_hermes_cycle()
