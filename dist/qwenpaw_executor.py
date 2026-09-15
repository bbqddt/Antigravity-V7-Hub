
# QwenPaw Executor — 复制到 QwenPaw 的 Python 环境中运行
# 作用：读取 dist/tasks/ 中的任务，执行，写入 dist/results/

import json
import sys
import os
import importlib
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
TASKS_DIR = DIST_DIR / "tasks"
RESULTS_DIR = DIST_DIR / "results"
STATE_DIR = DIST_DIR / "state"

def execute_task(task_file):
    """执行单个任务"""
    with open(task_file, "r", encoding="utf-8") as f:
        task = json.load(f)

    task_id = task["task_id"]
    task_type = task["task_type"]

    # 标记为运行中
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / f"{task_id}.running").touch()

    print(f"[QwenPaw] 开始执行任务: {task_id} ({task_type})")

    try:
        # 根据任务类型执行
        if task_type == "data_collection":
            from data_updater_v2 import main as updater_main
            updater_main()

        elif task_type == "nonrandomness_detection":
            from nonrandomness_detector import run_detection
            run_detection()

        elif task_type == "backtest":
            from walkforward_backtest_v2 import run as backtest_run
            backtest_run()

        elif task_type == "formula_evolution":
            from autonomous_evolution_v2 import AutonomousEvolutionV2
            evo = AutonomousEvolutionV2(max_cycles=task.get("params", {}).get("cycles", 1))
            evo.run()

        elif task_type == "custom_script":
            # 执行自定义脚本
            script = task.get("custom_script", "")
            local_vars = {}
            exec(script, {}, local_vars)

        # 标记完成
        result = {
            "task_id": task_id,
            "task_type": task_type,
            "status": "success",
            "completed_at": datetime.now().isoformat(),
            "output_files": task.get("output_files", []),
            "message": f"任务 {task_id} 执行成功",
        }

    except Exception as e:
        result = {
            "task_id": task_id,
            "task_type": task_type,
            "status": "error",
            "completed_at": datetime.now().isoformat(),
            "error": str(e),
            "message": f"任务 {task_id} 执行失败: {e}",
        }
        print(f"[QwenPaw] 任务失败: {e}")

    finally:
        # 写入结果
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        result_file = RESULTS_DIR / f"{task_id}.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # 移除运行标记
        running_file = STATE_DIR / f"{task_id}.running"
        if running_file.exists():
            running_file.unlink()

    print(f"[QwenPaw] 任务完成: {task_id} → {result_file}")
    return result


def run_loop():
    """循环执行模式：定期检查新任务"""
    print("[QwenPaw] 分布式执行器已启动，等待任务...")
    while True:
        if TASKS_DIR.exists():
            task_files = sorted(TASKS_DIR.glob("*.json"))
            for tf in task_files:
                # 检查是否正在被其他实例处理
                task_id = tf.stem
                running = (STATE_DIR / f"{task_id}.running").exists()
                if not running:
                    execute_task(tf)
        import time
        time.sleep(10)  # 每10秒检查一次


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true", help="循环模式")
    parser.add_argument("--once", type=str, help="执行单个任务文件")
    args = parser.parse_args()

    if args.loop:
        run_loop()
    elif args.once:
        execute_task(Path(args.once))
    else:
        # 默认：执行所有待处理任务
        if TASKS_DIR.exists():
            for tf in sorted(TASKS_DIR.glob("*.json")):
                execute_task(tf)
