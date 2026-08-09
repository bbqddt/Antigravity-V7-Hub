# -*- coding: utf-8 -*-
"""
Antigravity System Manager
One-click launch all core services
"""

import os
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

import time
import subprocess
import logging
import json
from pathlib import Path
from datetime import datetime

_PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = _PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "system_manager.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("SystemManager")


def find_python():
    venv_python = _PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def check_dependencies():
    python = find_python()
    required = ["requests", "beautifulsoup4", "pandas", "numpy"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            missing.append(pkg)
    if missing:
        logger.info(f"Installing missing deps: {', '.join(missing)}")
        for pkg in missing:
            subprocess.run([python, "-m", "pip", "install", pkg], check=False)
    return True


def run_script(script_name, args=None, timeout=120):
    python = find_python()
    script_path = _PROJECT_ROOT / script_name
    if not script_path.exists():
        logger.error(f"Script not found: {script_name}")
        return False, f"Not found: {script_name}"

    cmd = [python, str(script_path)]
    if args:
        cmd.extend(args)

    try:
        logger.info(f"Run: {script_name} {' '.join(args) if args else ''}")
        result = subprocess.run(
            cmd,
            cwd=str(_PROJECT_ROOT),
            timeout=timeout,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0:
            logger.info(f"[OK] {script_name}")
            return True, result.stdout[-500:] if result.stdout else ""
        else:
            logger.error(f"[FAIL] {script_name} code={result.returncode}")
            return False, result.stderr[-500:] if result.stderr else ""
    except subprocess.TimeoutExpired:
        logger.error(f"[TIMEOUT] {script_name}")
        return False, "Timeout"
    except Exception as e:
        logger.error(f"[ERROR] {script_name}: {e}")
        return False, str(e)


def full_pipeline():
    logger.info("=" * 60)
    logger.info("  Antigravity System Manager")
    logger.info("=" * 60)
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Step 0: Check deps
    logger.info("\n[0/6] Check dependencies...")
    check_dependencies()

    # Step 1: Data update
    logger.info("\n[1/6] Data update...")
    ok, output = run_script("data_updater_v2.py")
    if not ok:
        logger.warning(f"Data update failed: {output[:200]}")

    # Step 2: Non-randomness detection
    logger.info("\n[2/6] Non-randomness detection...")
    ok, output = run_script("nonrandomness_detector.py")
    if not ok:
        logger.warning(f"Non-randomness detection failed: {output[:200]}")

    # Step 3: Orchestrator prediction
    logger.info("\n[3/6] Orchestrator prediction...")
    ok, output = run_script("orchestrate.py", ["--top-k", "5"])
    if not ok:
        logger.warning(f"Orchestrator failed: {output[:200]}")

    # Step 4: Enhanced Predictor
    logger.info("\n[4/6] Enhanced Predictor...")
    ok, output = run_script("enhanced_predictor.py", ["--groups", "5"])
    if not ok:
        logger.warning(f"Enhanced Predictor failed: {output[:200]}")

    # Step 5: Evolved Predictor
    logger.info("\n[5/6] Evolved Predictor...")
    ok, output = run_script("evolved_predictor.py", ["--groups", "5"])
    if not ok:
        logger.warning(f"Evolved Predictor failed: {output[:200]}")

    # Step 6: V8 Core
    logger.info("\n[6/6] V8 Core...")
    ok, output = run_script("Antigravity_V8_Core.py", ["5"])
    if not ok:
        logger.warning(f"V8 Core failed: {output[:200]}")

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("  Pipeline complete")
    logger.info("=" * 60)

    show_latest_predictions()


def show_latest_predictions():
    files = [
        ("latest_prediction.json", "Orchestrator"),
        ("latest_decision_enhanced.json", "Enhanced"),
        ("latest_predictions_evolved.json", "Evolved"),
        ("latest_decision_v8.json", "V8 Core"),
    ]

    logger.info("\n[SUMMARY] Latest Predictions:")
    for fname, engine in files:
        fpath = _PROJECT_ROOT / fname
        if fpath.exists():
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    period = data.get("target_period", data.get("period", "?"))
                    logger.info(f"\n  [{engine}] Target Period: {period}")

                    groups = data.get("groups", data.get("predictions", []))
                    for i, g in enumerate(groups[:3], 1):
                        reds = g.get("red", g.get("reds", []))
                        blue = g.get("blue", "?")
                        if isinstance(reds, list):
                            red_str = ", ".join(f"{r:02d}" for r in reds)
                        else:
                            red_str = str(reds)
                        if isinstance(blue, int):
                            logger.info(f"    Group {i}: [{red_str}] + {blue:02d}")
                        else:
                            logger.info(f"    Group {i}: [{red_str}] + {blue}")
            except Exception as e:
                logger.warning(f"  [{engine}] Failed to read: {e}")


def start_daemon():
    logger.info("Starting daemon processes...")
    python = find_python()
    cloud_runner = _PROJECT_ROOT / "cloud_runner.py"
    if cloud_runner.exists():
        subprocess.Popen(
            [python, str(cloud_runner), "--daemon"],
            cwd=str(_PROJECT_ROOT),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
        )
        logger.info("[OK] Cloud Runner daemon started")

    commander = _PROJECT_ROOT / "commander_bot.py"
    token_file = _PROJECT_ROOT / "token_tg.txt"
    if commander.exists() and token_file.exists():
        try:
            with open(token_file, "r", encoding="utf-8") as f:
                token_data = json.load(f)
                if token_data.get("token"):
                    subprocess.Popen(
                        [python, str(commander)],
                        cwd=str(_PROJECT_ROOT),
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
                    )
                    logger.info("[OK] Commander Bot daemon started")
                else:
                    logger.warning("[SKIP] Commander Bot: Telegram Token not configured")
        except Exception:
            logger.warning("[SKIP] Commander Bot: token file invalid")
    else:
        logger.warning("[SKIP] Commander Bot: files missing")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Antigravity System Manager")
    parser.add_argument("--daemon", action="store_true", help="Start daemon processes")
    parser.add_argument("--once", action="store_true", help="Run full pipeline once")
    parser.add_argument("--predict", action="store_true", help="Run prediction only")
    args = parser.parse_args()

    if args.daemon:
        start_daemon()
    elif args.predict:
        run_script("orchestrate.py", ["--top-k", "5"])
    else:
        full_pipeline()


if __name__ == "__main__":
    main()