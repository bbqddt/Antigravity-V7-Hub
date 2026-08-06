# -*- coding: utf-8 -*-
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import time
import logging
from pathlib import Path
from datetime import datetime

_PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROJECT_ROOT))

LOG_DIR = _PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "cloud_runner.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("CloudRunner")

def run_single_cycle():
    logger.info("--- Start single cycle ---")
    try:
        from system_manager import full_pipeline
        full_pipeline()
        logger.info("--- Cycle complete ---")
    except Exception as e:
        logger.error(f"Cycle failed: {e}")

def run_daemon(interval_minutes=60):
    logger.info(f"Starting daemon mode, interval={interval_minutes}min")
    cycle = 0
    while True:
        cycle += 1
        logger.info(f"=== Cycle {cycle} ===")
        try:
            run_single_cycle()
        except Exception as e:
            logger.error(f"Cycle {cycle} error: {e}")
        logger.info(f"Waiting {interval_minutes}min until next cycle...")
        time.sleep(interval_minutes * 60)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--once", action="store_true", help="Run once")
    parser.add_argument("--interval", type=int, default=60, help="Daemon interval in minutes")
    args = parser.parse_args()

    try:
        import requests
        import bs4
    except ImportError:
        logger.error("Missing dependencies: pip install requests beautifulsoup4")
        sys.exit(1)

    if args.daemon:
        run_daemon(args.interval)
    else:
        run_single_cycle()