import time
import os
import sys
import logging
import subprocess
from core.hermes_agent import HermesAgent

# 确保路径正确
sys.path.append(os.path.abspath("."))

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
            subprocess.run(["python", "core/genesis_crawler.py"], check=True)
            
            # 2. 第二神格：算力演进 (Titan/Evolver)
            logger.info("🧬 第二阶段：执行本地逻辑演进 (Self-Evolver)...")
            subprocess.run(["python", "core/self_evolver.py"], check=True)
            
            # 3. 赫耳墨斯心脏跳动：置信度侦听与自主演进
            print("\n")
            if hermes.intelligence_pulse(confidence_threshold=0.92):
                # 如果检测到高置信度或逻辑衰退，触发深度代码重写
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
        # 在生产环境中建议保持潜伏状态
        sleep_time = 7200
        logger.info(f"💤 Hermes 代理进入潜伏期，倒计时 {sleep_time} 秒...")
        time.sleep(sleep_time)

if __name__ == "__main__":
    run_hermes_cycle()
