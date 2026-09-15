# -*- coding: utf-8 -*-
"""
Antigravity 分布式协作协议 V1.0
================================
让 QwenPaw (AgentScope) 成为你的远程计算节点。

架构:
  Claude (我)     = 大脑/指挥官 — 架构设计、公式开发、策略决策
  QwenPaw         = 手臂/工人 — 批量计算、定时执行、数据搬运

通信方式: 共享文件 (dist/*)

用法:
    python distributed_bridge.py --setup       # 初始化分布式目录
    python distributed_bridge.py --publish     # 发布任务给 QwenPaw
    python distributed_bridge.py --poll          # 轮询 QwenPaw 的结果
    python distributed_bridge.py --run-cycle   # 发布+轮询一条龙
"""
import json
import sys
import os
import time
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# Fix Windows GBK
sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, 'reconfigure') else None

_PROJECT_ROOT = Path(__file__).resolve().parent
_DIST_DIR = _PROJECT_ROOT / "dist"
_TASKS_DIR = _DIST_DIR / "tasks"
_RESULTS_DIR = _DIST_DIR / "results"
_STATE_DIR = _DIST_DIR / "state"

# 日志
LOG_DIR = _PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "distributed_bridge.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("DistributedBridge")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 任务定义
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TASK_TYPES = {
    "data_collection": {
        "description": "数据采集 — 从500.com抓取最新开奖",
        "module": "data_updater_v2",
        "func": "main",
        "input_files": [],
        "output_files": ["data/lottery_history.csv"],
        "estimated_time": 30,
    },
    "nonrandomness_detection": {
        "description": "非随机性检测 — 22项统计检验",
        "module": "nonrandomness_detector",
        "func": "run_detection",
        "input_files": ["data/lottery_history.csv"],
        "output_files": ["nonrandomness_results.json", "analysis_prior.json"],
        "estimated_time": 120,
    },
    "backtest": {
        "description": "滚动回测 — 前向滚动验证",
        "module": "walkforward_backtest_v2",
        "func": "run",
        "input_files": ["data/lottery_history.csv"],
        "output_files": ["walkforward_results_v2.json", "walkforward_report_v2.md"],
        "estimated_time": 300,
    },
    "formula_evolution": {
        "description": "公式进化 — 生成+变异+评估新公式",
        "module": "autonomous_evolution_v2",
        "func": "AutonomousEvolutionV2.run",
        "input_files": ["data/lottery_history.csv"],
        "output_files": ["evolved_formulas_v2.json", "evolution_state_v2.json"],
        "estimated_time": 600,
    },
    "custom_script": {
        "description": "自定义脚本 — 用户指定的任意Python任务",
        "module": None,  # 需要指定 script_path
        "func": None,
        "input_files": [],
        "output_files": [],
        "estimated_time": 60,
    },
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 任务发布器 (Claude → QwenPaw)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TaskPublisher:
    """把任务打包成 JSON，写入 dist/tasks/ 目录"""

    def __init__(self):
        _TASKS_DIR.mkdir(parents=True, exist_ok=True)
        _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        _STATE_DIR.mkdir(parents=True, exist_ok=True)

    def publish(self, task_type: str, params: Optional[Dict] = None,
                custom_script: Optional[str] = None) -> Dict:
        """
        发布一个任务给 QwenPaw。

        Args:
            task_type: 任务类型 (data_collection, backtest, etc.)
            params: 任务的额外参数
            custom_script: 如果是 custom_script 类型，提供 Python 代码

        Returns:
            任务描述字典
        """
        if task_type not in TASK_TYPES:
            raise ValueError(f"未知任务类型: {task_type}。可用: {list(TASK_TYPES.keys())}")

        task_def = TASK_TYPES[task_type].copy()

        # 生成唯一任务ID
        task_id = hashlib.md5(
            f"{task_type}_{datetime.now().isoformat()}_{hash(time.time())}".encode()
        ).hexdigest()[:12]

        task = {
            "task_id": task_id,
            "task_type": task_type,
            "description": task_def["description"],
            "module": task_def["module"],
            "func": task_def["func"],
            "params": params or {},
            "custom_script": custom_script,
            "input_files": task_def["input_files"],
            "output_files": task_def["output_files"],
            "estimated_time": task_def["estimated_time"],
            "created_at": datetime.now().isoformat(),
            "priority": params.get("priority", "normal"),
            "status": "pending",
            "assigned_to": "qwenpaw",  # 明确分配给 QwenPaw
        }

        # 写入任务文件
        task_file = _TASKS_DIR / f"{task_id}.json"
        with open(task_file, "w", encoding="utf-8") as f:
            json.dump(task, f, ensure_ascii=False, indent=2)

        logger.info(f"任务已发布: {task_id} ({task_type}) → {task_def['description']}")
        logger.info(f"  任务文件: {task_file}")
        return task

    def publish_full_cycle(self) -> List[Dict]:
        """发布一个完整的调度周期任务给 QwenPaw"""
        tasks = []
        steps = [
            ("data_collection", {}),
            ("nonrandomness_detection", {}),
            ("backtest", {}),
        ]
        for task_type, params in steps:
            task = self.publish(task_type, params)
            tasks.append(task)

        logger.info(f"已发布 {len(tasks)} 个任务给 QwenPaw（完整调度周期）")
        return tasks

    def publish_batch_backtest(self, n_rounds: int = 100) -> Dict:
        """发布一个批量回测任务（可以多次运行不同参数）"""
        return self.publish("backtest", {
            "n_rounds": n_rounds,
            "description": f"批量回测 {n_rounds} 轮",
        })


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 结果轮询器 (QwenPaw → Claude)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ResultPoller:
    """从 dist/results/ 读取 QwenPaw 的执行结果"""

    def __init__(self):
        _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        _STATE_DIR.mkdir(parents=True, exist_ok=True)

    def list_pending_results(self) -> List[str]:
        """列出所有待处理的结果文件"""
        if not _RESULTS_DIR.exists():
            return []
        return sorted([f.stem for f in _RESULTS_DIR.glob("*.json")])

    def load_result(self, task_id: str) -> Optional[Dict]:
        """加载指定任务ID的结果"""
        result_file = _RESULTS_DIR / f"{task_id}.json"
        if not result_file.exists():
            return None
        with open(result_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_all_results(self) -> Dict[str, Dict]:
        """加载所有结果"""
        results = {}
        for task_id in self.list_pending_results():
            result = self.load_result(task_id)
            if result:
                results[task_id] = result
        return results

    def mark_processed(self, task_id: str):
        """标记结果为已处理（移动到 state/processed/）"""
        src = _RESULTS_DIR / f"{task_id}.json"
        dst = _STATE_DIR / "processed" / f"{task_id}.json"
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            src.rename(dst)
            logger.info(f"结果已归档: {task_id}")

    def get_task_status(self, task_id: str) -> str:
        """检查任务状态"""
        # 先查结果
        if self.load_result(task_id):
            return "completed"
        # 再查正在执行
        state_file = _STATE_DIR / f"{task_id}.running"
        if state_file.exists():
            return "running"
        # 查是否已发布
        task_file = _TASKS_DIR / f"{task_id}.json"
        if task_file.exists():
            return "pending"
        return "unknown"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# QwenPaw 端脚本生成器
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_qwenpaw_executor() -> str:
    """
    生成 QwenPaw 端需要运行的 executor 脚本。
    QwenPaw 看到这个脚本后，可以自动执行 dist/tasks/ 中的任务。

    把这段代码发给 QwenPaw，让它保存在自己的环境中运行。
    """
    return '''
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
'''


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI 入口
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_setup():
    """初始化分布式目录结构"""
    for d in [_DIST_DIR, _TASKS_DIR, _RESULTS_DIR, _STATE_DIR,
              _STATE_DIR / "processed", _STATE_DIR / "inbox"]:
        d.mkdir(parents=True, exist_ok=True)

    # 生成 QwenPaw executor 脚本
    executor_path = _DIST_DIR / "qwenpaw_executor.py"
    executor_code = generate_qwenpaw_executor()
    with open(executor_path, "w", encoding="utf-8") as f:
        f.write(executor_code)

    logger.info(f"分布式目录已初始化: {_DIST_DIR}")
    logger.info(f"QwenPaw Executor 脚本: {executor_path}")
    logger.info(f"\n下一步：把 {executor_path} 的内容发给 QwenPaw，让它在自己的环境中运行")

    return executor_path


def cmd_publish(task_type: str = None, full_cycle: bool = False):
    """发布任务"""
    publisher = TaskPublisher()
    if full_cycle or task_type == "full_cycle":
        tasks = publisher.publish_full_cycle()
        logger.info(f"已发布 {len(tasks)} 个任务")
    elif task_type:
        task = publisher.publish(task_type)
        logger.info(f"已发布 1 个任务")
    else:
        logger.info("发布完整调度周期的所有任务...")
        tasks = publisher.publish_full_cycle()
        logger.info(f"已发布 {len(tasks)} 个任务")


def cmd_poll():
    """轮询结果"""
    poller = ResultPoller()
    results = poller.load_all_results()
    if not results:
        logger.info("没有待处理的结果")
        return

    logger.info(f"发现 {len(results)} 个结果:")
    for tid, result in results.items():
        status = result.get("status", "?")
        msg = result.get("message", "")
        logger.info(f"  [{tid}] {status} — {msg}")


def cmd_run_cycle():
    """发布 + 轮询一条龙"""
    publisher = TaskPublisher()
    poller = ResultPoller()

    # 发布
    tasks = publisher.publish_full_cycle()
    task_ids = [t["task_id"] for t in tasks]
    logger.info(f"已发布 {len(tasks)} 个任务，开始轮询...")

    # 等待结果（最多等 10 分钟）
    max_wait = 600
    start = time.time()
    while time.time() - start < max_wait:
        results = poller.load_all_results()
        if len(results) >= len(tasks):
            logger.info("所有结果已收到！")
            for tid, result in results.items():
                logger.info(f"  [{tid}] {result.get('status')} — {result.get('message', '')}")
            return
        time.sleep(10)
        logger.info(f"等待结果... ({len(results)}/{len(tasks)})")

    logger.warning("等待超时，部分结果可能还未到达")


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Antigravity 分布式协作桥接器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python distributed_bridge.py --setup                          # 初始化
  python distributed_bridge.py --publish --type backtest        # 发布回测任务
  python distributed_bridge.py --publish --full-cycle           # 发布完整周期
  python distributed_bridge.py --poll                           # 轮询结果
  python distributed_bridge.py --run-cycle                      # 发布+轮询
        """,
    )

    parser.add_argument("--setup", action="store_true", help="初始化分布式目录")
    parser.add_argument("--publish", action="store_true", help="发布任务")
    parser.add_argument("--poll", action="store_true", help="轮询结果")
    parser.add_argument("--run-cycle", action="store_true", help="发布+轮询一条龙")
    parser.add_argument("--full-cycle", action="store_true", help="发布完整调度周期")
    parser.add_argument("--type", choices=list(TASK_TYPES.keys()), default=None,
                        help="任务类型")

    args = parser.parse_args()

    if not any([args.setup, args.publish, args.poll, args.run_cycle]):
        # 默认行为：显示帮助
        parser.print_help()
        return

    if args.setup:
        cmd_setup()

    if args.publish:
        cmd_publish(args.type, args.full_cycle)

    if args.poll:
        cmd_poll()

    if args.run_cycle:
        cmd_run_cycle()


if __name__ == "__main__":
    main()
