# -*- coding: utf-8 -*-
"""
Antigravity 云端守护进程 V2.0 (腾讯云 CVM 专用)
=================================================
利用 32核/123GB 资源进行大规模并行计算。

调度计划:
  每30分钟: 数据采集 + 预测引擎
  每6小时:  非随机性检测
  每天:      滚动回测
  每周:      公式进化

用法:
    python cloud_runner_v2.py --daemon    # 守护模式（默认）
    python cloud_runner_v2.py --once       # 单轮运行
    python cloud_runner_v2.py --backtest   # 仅回测
    python cloud_runner_v2.py --evolve     # 仅进化
    python cloud_runner_v2.py --status     # 显示状态
"""
import sys
import os
import time
import logging
import json
import signal
import traceback
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Fix encoding
sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, 'reconfigure') else None

_PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROJECT_ROOT))

# ─── 日志 ─────────────────────────────────────────────
LOG_DIR = _PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("CloudRunnerV2")
logger.setLevel(logging.INFO)

# 文件处理器
fh = logging.FileHandler(LOG_DIR / "cloud_runner_v2.log", encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(fh)

# 控制台处理器
sh = logging.StreamHandler(sys.stdout)
sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(sh)

# ─── 状态管理 ──────────────────────────────────────────
STATE_FILE = _PROJECT_ROOT / "cloud_runner_state.json"


def load_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"runs": [], "last_run": None, "total_cycles": 0, "errors": []}


def save_state(state: Dict[str, Any]):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def record_run(task: str, status: str, elapsed: float, error: str = None):
    state = load_state()
    entry = {
        "time": datetime.now().isoformat(),
        "task": task,
        "status": status,
        "elapsed_seconds": round(elapsed, 2),
    }
    if error:
        entry["error"] = error
    state["runs"].append(entry)
    # 只保留最近100条记录
    if len(state["runs"]) > 100:
        state["runs"] = state["runs"][-100:]
    state["last_run"] = entry["time"]
    state["total_cycles"] = state.get("total_cycles", 0) + 1
    if status == "error":
        state.setdefault("errors", []).append(error)
        if len(state["errors"]) > 50:
            state["errors"] = state["errors"][-50:]
    save_state(state)


# ─── 单轮任务执行器 ─────────────────────────────────────

def run_data_collection() -> bool:
    """数据采集"""
    logger.info("  [1/4] 数据采集...")
    try:
        from data_updater_v2 import main as updater_main
        updater_main()
        logger.info("  ✅ 数据采集完成")
        return True
    except Exception as e:
        logger.warning(f"  ⚠️ 数据采集失败: {e}")
        return False


def run_prediction() -> bool:
    """预测引擎"""
    logger.info("  [2/4] 预测引擎...")
    try:
        from orchestrate import run_full_pipeline
        result = run_full_pipeline(top_k=5)
        target = result.get("target_period", "?")
        logger.info(f"  ✅ 预测完成: 目标 #{target}")
        return True
    except Exception as e:
        logger.warning(f"  ⚠️ 预测引擎失败: {e}")
        return False


def run_nonrandomness() -> bool:
    """非随机性检测"""
    logger.info("  [3/4] 非随机性检测...")
    try:
        from nonrandomness_detector import run_detection
        run_detection()
        logger.info("  ✅ 非随机性检测完成")
        return True
    except Exception as e:
        logger.warning(f"  ⚠️ 非随机性检测失败: {e}")
        return False


def run_backtest() -> bool:
    """滚动回测"""
    logger.info("  [4/4] 滚动回测...")
    try:
        from walkforward_backtest_v2 import run as backtest_run
        backtest_run()
        logger.info("  ✅ 滚动回测完成")
        return True
    except Exception as e:
        logger.warning(f"  ⚠️ 滚动回测失败: {e}")
        return False


def run_full_cycle():
    """运行完整调度周期"""
    logger.info("=" * 60)
    logger.info("  云端守护进程 V2.0 — 完整调度周期")
    logger.info(f"  主机: {os.popen('hostname').read().strip()}")
    logger.info(f"  CPU: {os.popen('nproc').read().strip()} 核 | "
                f"内存: {os.popen(\"free -g | awk '/Mem:/{print $2}'\").read().strip()}G")
    logger.info("=" * 60)

    start = time.time()
    results = {}

    # 数据采集
    results["data_collection"] = run_data_collection()

    # 预测引擎（依赖数据）
    if results["data_collection"]:
        results["prediction"] = run_prediction()
    else:
        results["prediction"] = False
        logger.warning("  跳过预测引擎（数据未更新）")

    elapsed = time.time() - start
    logger.info(f"\n  📊 周期完成: {elapsed:.1f}s | "
                f"成功: {sum(1 for v in results.values() if v)}/{len(results)}")

    record_run("full_cycle", "ok" if all(results.values()) else "partial", elapsed)

    return results


def run_single_task(task_name: str) -> bool:
    """运行单个任务"""
    logger.info(f"运行单个任务: {task_name}")
    start = time.time()
    try:
        if task_name == "data_collection":
            result = run_data_collection()
        elif task_name == "prediction":
            result = run_prediction()
        elif task_name == "nonrandomness":
            result = run_nonrandomness()
        elif task_name == "backtest":
            result = run_backtest()
        else:
            logger.error(f"未知任务: {task_name}")
            return False
        elapsed = time.time() - start
        record_run(task_name, "ok" if result else "error", elapsed)
        return result
    except Exception as e:
        elapsed = time.time() - start
        record_run(task_name, "error", elapsed, str(e))
        raise


def show_status():
    """显示云端状态"""
    state = load_state()
    print("\n" + "=" * 60)
    print("  Antigravity 云端守护进程状态")
    print("=" * 60)
    print(f"\n  总运行周期: {state.get('total_cycles', 0)}")
    print(f"  上次运行: {state.get('last_run', '从未')}")

    if state.get("runs"):
        print(f"\n  最近5次运行:")
        for run in state["runs"][-5:]:
            status_icon = "✅" if run["status"] == "ok" else "❌"
            print(f"    {status_icon} [{run['time']}] {run['task']} "
                  f"({run['elapsed_seconds']}s)")

    if state.get("errors"):
        print(f"\n  最近错误:")
        for err in state["errors"][-3:]:
            print(f"    ⚠️ {err[:100]}")

    # 系统信息
    print(f"\n  系统信息:")
    print(f"    主机: {os.popen('hostname').read().strip()}")
    print(f"    CPU: {os.popen('nproc').read().strip()} 核")
    print(f"    内存: {os.popen('free -g | awk \'/Mem:/{{print $2}}\'').read().strip()}G")
    print(f"    负载: {os.popen('cat /proc/loadavg').read().strip()}")

    # 最新预测
    pred_file = _PROJECT_ROOT / "latest_prediction.json"
    if pred_file.exists():
        with open(pred_file, "r", encoding="utf-8") as f:
            pred = json.load(f)
        target = pred.get("target_period", "?")
        fusion = pred.get("fusion", [])
        if fusion:
            best = fusion[0]
            reds = ", ".join(f"{r:02d}" for r in best.get("reds", []))
            blue = f"{best.get('blue', 0):02d}"
            print(f"\n  最新预测 (#{target}):")
            print(f"    🔴[{reds}] 🔵{blue}")
            print(f"    跨引擎支持: {best.get('cross_engine_support', '?')}")
    print("=" * 60)


# ─── 守护模式 ──────────────────────────────────────────

class CloudRunnerDaemon:
    """云端守护进程调度器"""

    def __init__(self, interval_minutes: int = 30):
        self.interval = interval_minutes
        self.running = True
        self.cycle_count = 0

        # 信号处理
        def signal_handler(sig, frame):
            logger.info("收到停止信号，优雅退出...")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def should_run_nonrandomness(self) -> bool:
        """判断是否应该运行非随机性检测（每6小时）"""
        hour = datetime.now().hour
        return hour % 6 == 0

    def should_run_backtest(self) -> bool:
        """判断是否应该运行回测（每天周日）"""
        return datetime.now().weekday() == 6  # Sunday

    def run_loop(self):
        """主循环"""
        logger.info("=" * 60)
        logger.info("  云端守护进程 V2.0 — 守护模式启动")
        logger.info(f"  调度间隔: {self.interval} 分钟")
        logger.info(f"  主机: {os.popen('hostname').read().strip()}")
        logger.info(f"  资源: {os.popen('nproc').read().strip()}核 / "
                    f"{os.popen('free -g | awk \'/Mem:/{{print $2}}\'').read().strip()}G")
        logger.info("=" * 60)

        while self.running:
            self.cycle_count += 1
            logger.info(f"\n>>> 第 {self.cycle_count} 轮 <<<")

            # 标准周期：数据 + 预测
            run_full_cycle()

            # 特殊周期：非随机性检测
            if self.should_run_nonrandomness():
                logger.info("\n  📅 运行非随机性检测...")
                run_nonrandomness()

            # 特殊周期：回测
            if self.should_run_backtest():
                logger.info("\n  📅 运行滚动回测...")
                run_backtest()

            # 等待下一轮
            logger.info(f"\n  💤 等待 {self.interval} 分钟...")
            for _ in range(self.interval * 60):
                if not self.running:
                    break
                time.sleep(1)

        # 优雅退出
        state = load_state()
        state["stopped_at"] = datetime.now().isoformat()
        save_state(state)
        logger.info(f"\n守护进程退出，共运行 {self.cycle_count} 轮")


# ─── CLI ──────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Antigravity 云端守护进程 V2.0")
    parser.add_argument("--daemon", action="store_true", help="守护模式（持续运行）")
    parser.add_argument("--once", action="store_true", help="单轮运行")
    parser.add_argument("--task", type=str, help="运行单个任务 (data_collection/prediction/nonrandomness/backtest)")
    parser.add_argument("--status", action="store_true", help="显示状态")
    parser.add_argument("--interval", type=int, default=30, help="守护模式间隔(分钟)")

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.task:
        run_single_task(args.task)
    elif args.daemon:
        daemon = CloudRunnerDaemon(interval_minutes=args.interval)
        daemon.run_loop()
    elif args.once:
        run_full_cycle()
    else:
        # 默认：守护模式
        daemon = CloudRunnerDaemon(interval_minutes=args.interval)
        daemon.run_loop()
