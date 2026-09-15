# -*- coding: utf-8 -*-
"""
Antigravity Master Controller V3.0 — 7x24 全模式运算中枢
================================================================
统一调度所有计算模式:

  模式1: [CLOUD]   云端演进 — AI公式进化引擎 (6h周期)
  模式2: [SANDBOX] 沙箱实验 — 隔离策略实验室 (持续探索)
  模式3: [B2B]     后端桥接 — 分布式节点协同 (QwenPaw)
  模式4: [MCP]     多云管线 — GitHub/HF/Tencent 多平台
  模式5: [CORE]    核心预测 — 数据→检测→预测流水线 (数据更新时触发)

特性:
  - 开机自启动
  - 所有模式并行运行
  - 健康监控 + 自动恢复
  - 统一状态面板
"""
import json, os, sys, time, signal, threading, logging, subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

if sys.stdout.encoding and 'utf' not in sys.stdout.encoding.lower():
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding and 'utf' not in sys.stderr.encoding.lower():
    sys.stderr.reconfigure(encoding='utf-8')

_PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROJECT_ROOT))
_LOG_DIR = _PROJECT_ROOT / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(_LOG_DIR / "master_controller.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("MasterController")

# ================================================================
# CONFIG
# ================================================================

MASTER_STATE_FILE = _PROJECT_ROOT / "master_state.json"

COMPUTE_MODES = {
    "cloud": {
        "name": "Cloud Evolution",
        "icon": "[CLOUD]",
        "enabled": True,
        "interval_seconds": 6 * 3600,  # 每6小时
        "script": "cloud_daemon.py",
        "args": ["--run"],
        "description": "AI公式进化引擎 — 生成/变异/评估公式",
    },
    "sandbox": {
        "name": "Sandbox Lab",
        "icon": "[SANDBOX]",
        "enabled": True,
        "interval_seconds": 15 * 60,  # 每15分钟
        "script": None,  # 内联运行
        "args": [],
        "description": "隔离策略实验室 — 安全试验新策略",
    },
    "b2b": {
        "name": "B2B Bridge",
        "icon": "[B2B]",
        "enabled": True,
        "interval_seconds": 30 * 60,  # 每30分钟
        "script": "distributed_bridge.py",
        "args": ["--run-cycle"],
        "description": "分布式节点协同 — QwenPaw远程计算",
    },
    "mcp": {
        "name": "MCP Pipeline",
        "icon": "[MCP]",
        "enabled": True,
        "interval_seconds": 12 * 3600,  # 每12小时
        "script": None,  # 多平台内联
        "args": [],
        "description": "多云管线 — GitHub Actions + HF Space + Tencent",
    },
    "core": {
        "name": "Core Predictor",
        "icon": "[CORE]",
        "enabled": True,
        "interval_seconds": 1800,  # 每30分钟检查
        "script": "system_manager.py",
        "args": ["--predict"],
        "description": "核心预测引擎 — 数据采集→检测→预测",
    },
}


# ================================================================
# STATE MANAGEMENT
# ================================================================
class MasterState:
    def __init__(self):
        self.state = self._load()

    def _load(self) -> Dict:
        try:
            with open(MASTER_STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {
                "started_at": datetime.now().isoformat(),
                "uptime_seconds": 0,
                "last_health_check": None,
                "modes": {},
                "total_cycles": 0,
                "errors": [],
            }

    def save(self):
        self.state["uptime_seconds"] = (
            datetime.now() - datetime.fromisoformat(self.state["started_at"])
        ).total_seconds()
        with open(MASTER_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def record_cycle(self, mode: str, success: bool, elapsed: float, detail: str = ""):
        if mode not in self.state["modes"]:
            self.state["modes"][mode] = {"runs": 0, "successes": 0, "last_run": None, "last_elapsed": 0}
        m = self.state["modes"][mode]
        m["runs"] += 1
        if success:
            m["successes"] += 1
        m["last_run"] = datetime.now().isoformat()
        m["last_elapsed"] = round(elapsed, 1)
        self.state["total_cycles"] += 1
        self.save()

    def record_error(self, mode: str, error: str):
        self.state["errors"].append({
            "time": datetime.now().isoformat(),
            "mode": mode,
            "error": str(error)[:300],
        })
        self.state["errors"] = self.state["errors"][-20:]
        self.save()


# ================================================================
# SANDBOX ENGINE
# ================================================================
class SandboxEngine:
    """
    沙箱隔离策略实验室
    在不影响主系统的情况下:
      - 随机探索新策略组合
      - 快速回测验证
      - 发现潜力策略推送到主系统
    """
    def __init__(self):
        self.sandbox_dir = _PROJECT_ROOT / "sandbox"
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.sandbox_dir / "sandbox_state.json"
        self.state = self._load_state()

    def _load_state(self):
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"experiments": 0, "discoveries": [], "active_strategies": []}

    def run_experiment(self) -> Dict:
        """运行一轮沙箱实验"""
        import random, numpy as np
        from collections import Counter

        logger.info("  [SANDBOX] Starting experiment...")

        # 加载数据
        try:
            from data_layer import load_history
            draws = load_history()
            if not draws or len(draws) < 100:
                return {"success": False, "error": "Insufficient data"}
        except Exception as e:
            return {"success": False, "error": str(e)}

        # 随机策略组合实验
        strategies = []

        # 策略1: 纯热号加权
        freq = Counter()
        for d in draws[-100:]:
            for r in d.reds:
                freq[r] += 1
        hot_reds = sorted(freq.keys(), key=lambda x: freq[x], reverse=True)[:15]
        strategies.append({
            "name": "sandbox_hot_weighted",
            "reds": sorted(random.sample(hot_reds, 6)),
            "blue": max(freq, key=freq.get) % 16 + 1 if freq else random.randint(1, 16),
        })

        # 策略2: 冷热混合 + 区间平衡
        zones = [(1, 11), (12, 22), (23, 33)]
        mixed = []
        for lo, hi in zones:
            zone_nums = [n for n in range(lo, hi + 1)]
            mixed.append(random.choice(zone_nums))
        remaining = [n for n in range(1, 34) if n not in mixed]
        mixed.extend(random.sample(remaining, 3))
        strategies.append({
            "name": "sandbox_zone_balanced",
            "reds": sorted(mixed),
            "blue": random.randint(1, 16),
        })

        # 策略3: 随机种子探索
        strategies.append({
            "name": "sandbox_random_explore",
            "reds": sorted(random.sample(range(1, 34), 6)),
            "blue": random.randint(1, 16),
        })

        # 快速回测这些策略
        test_periods = min(30, len(draws) // 3)
        results = []
        for strat in strategies:
            hit_scores = []
            for i in range(test_periods):
                if len(draws) < i + 2:
                    break
                actual = draws[-(i + 1)]
                red_hits = len(set(strat["reds"]) & set(actual.reds))
                blue_hit = 1 if strat["blue"] == actual.blue else 0
                hit_scores.append(red_hits + blue_hit * 0.5)
            avg_hit = sum(hit_scores) / len(hit_scores) if hit_scores else 0
            results.append({"name": strat["name"], "avg_hits": round(avg_hit, 3), "reds": strat["reds"], "blue": strat["blue"]})

        # 保存实验结果
        experiment = {
            "id": self.state["experiments"] + 1,
            "timestamp": datetime.now().isoformat(),
            "results": sorted(results, key=lambda x: x["avg_hits"], reverse=True),
        }
        self.state["experiments"] += 1

        # 如果发现好策略（avg > 1.5），标记为发现
        for r in results:
            if r["avg_hits"] > 1.5:
                self.state["discoveries"].append({
                    "time": datetime.now().isoformat(),
                    "strategy": r["name"],
                    "score": r["avg_hits"],
                })

        # 保存沙箱快照
        exp_file = self.sandbox_dir / f"experiment_{experiment['id']:04d}.json"
        with open(exp_file, 'w', encoding='utf-8') as f:
            json.dump(experiment, f, ensure_ascii=False, indent=2)
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

        logger.info(f"  [SANDBOX] Experiment #{experiment['id']} done: {len(results)} strategies tested")
        return {"success": True, "experiment_id": experiment["id"], "best": results[0] if results else None}


# ================================================================
# B2B ENGINE
# ================================================================
class B2BEngine:
    """
    B2B 后端桥接引擎
    管理分布式节点通信: Claude -> QwenPaw -> 结果聚合
    """
    def __init__(self):
        self.dist_dir = _PROJECT_ROOT / "dist"
        self.tasks_dir = self.dist_dir / "tasks"
        self.results_dir = self.dist_dir / "results"
        for d in [self.dist_dir, self.tasks_dir, self.results_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def publish_tasks(self) -> Dict:
        """发布任务到分布式节点"""
        logger.info("  [B2B] Publishing distributed tasks...")
        tasks_published = 0

        try:
            from distributed_bridge import TaskPublisher
            pub = TaskPublisher()

            # 发布数据采集任务
            pub.publish("data_collection", {"source": "500.com"})
            tasks_published += 1

            # 发布非随机性检测任务
            pub.publish("nonrandomness_detection", {})
            tasks_published += 1

            # 发布回测任务（如果有新数据）
            pub.publish("backtest", {
                "lookback": 500,
                "top_k": 10,
                "description": "B2B auto backtest",
            })
            tasks_published += 1

        except Exception as e:
            logger.error(f"  [B2B] Task publish failed: {e}")
            return {"success": False, "error": str(e), "published": tasks_published}

        return {"success": True, "published": tasks_published}

    def poll_results(self) -> Dict:
        """轮询分布式节点结果"""
        results_collected = 0
        try:
            from distributed_bridge import ResultPoller
            poller = ResultPoller()
            all_results = poller.load_all_results()
            results_collected = len(all_results)
            for task_id, result in all_results.items():
                logger.info(f"  [B2B] Result received: {task_id} -> {result.get('status', 'unknown')}")
                poller.mark_processed(task_id)
        except Exception as e:
            logger.warning(f"  [B2B] Poll failed: {e}")

        return {"success": True, "collected": results_collected}

    def run_cycle(self) -> Dict:
        pub_result = self.publish_tasks()
        time.sleep(2)
        poll_result = self.poll_results()
        return {
            "success": pub_result["success"],
            "published": pub_result.get("published", 0),
            "collected": poll_result.get("collected", 0),
        }


# ================================================================
# MCP ENGINE
# ================================================================
class MCPEngine:
    """
    MCP 多云管线引擎
    管理多云端部署: GitHub Actions + HuggingFace Space + Tencent CVM
    """
    def __init__(self):
        self.state_file = _PROJECT_ROOT / "cloud_deploy_state.json"

    def run_cycle(self) -> Dict:
        logger.info("  [MCP] Running multi-cloud pipeline...")
        results = {}

        # 1. GitHub Actions 工作流更新
        try:
            github_dir = _PROJECT_ROOT / ".github" / "workflows"
            github_dir.mkdir(parents=True, exist_ok=True)

            wf_content = """name: Antigravity 24x7 Evolution
on:
  schedule:
    - cron: '0 */6 * * *'
    - cron: '30 3 * * *'
  workflow_dispatch:
permissions:
  contents: write
jobs:
  evolve:
    runs-on: ubuntu-latest
    timeout-minutes: 50
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install numpy pandas
      - run: python cloud_daemon.py --run
      - uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "auto: evolution cycle [skip ci]"
"""
            wf_path = github_dir / "evolution_24x7.yml"
            with open(wf_path, 'w', encoding='utf-8') as f:
                f.write(wf_content)
            results["github_actions"] = "workflow_updated"
        except Exception as e:
            results["github_actions"] = f"error: {e}"

        # 2. HuggingFace Space 同步
        try:
            hf_dir = _PROJECT_ROOT / "hf_space"
            if hf_dir.exists():
                results["hf_space"] = "present"
            else:
                results["hf_space"] = "not_configured"
        except Exception as e:
            results["hf_space"] = f"error: {e}"

        # 3. Tencent Cloud 检查
        try:
            from cloud_all_deployer import TencentCloudDeployer
            deployer = TencentCloudDeployer()
            if deployer.check_connectivity():
                status = deployer.get_status()
                results["tencent_cvm"] = status.get("daemon_running", False)
            else:
                results["tencent_cvm"] = "unreachable"
        except Exception as e:
            results["tencent_cvm"] = f"error: {e}"

        # 4. 本地 API 代理检查
        try:
            import requests
            r = requests.get("http://127.0.0.1:5000/health", timeout=3)
            results["api_proxy"] = "running" if r.status_code == 200 else "down"
        except:
            results["api_proxy"] = "down"

        logger.info(f"  [MCP] Pipeline complete: {json.dumps(results, ensure_ascii=False)}")
        return {"success": True, "platforms": results}


# ================================================================
# MASTER CONTROLLER
# ================================================================
class AntigravityMaster:
    """
    7x24 全模式主控制器
    """
    def __init__(self):
        self.state = MasterState()
        self.sandbox = SandboxEngine()
        self.b2b = B2BEngine()
        self.mcp = MCPEngine()
        self.running = True
        self.threads = {}
        self.last_runs = {}

    def find_python(self):
        venv = _PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
        return str(venv) if venv.exists() else sys.executable

    def run_script_mode(self, mode_name: str, mode_config: Dict):
        """运行脚本模式"""
        python = self.find_python()
        script = _PROJECT_ROOT / mode_config["script"]
        if not script.exists():
            logger.error(f"  {mode_config['icon']} Script not found: {mode_config['script']}")
            return False

        start = time.time()
        try:
            result = subprocess.run(
                [python, str(script)] + mode_config.get("args", []),
                cwd=str(_PROJECT_ROOT),
                timeout=1800,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            elapsed = time.time() - start
            ok = result.returncode == 0
            self.state.record_cycle(mode_name, ok, elapsed, result.stdout[-200:] if result.stdout else "")
            if ok:
                logger.info(f"  {mode_config['icon']} OK ({elapsed:.1f}s)")
            else:
                logger.error(f"  {mode_config['icon']} FAIL: {result.stderr[:200]}")
            return ok
        except subprocess.TimeoutExpired:
            self.state.record_cycle(mode_name, False, time.time() - start, "timeout")
            return False
        except Exception as e:
            self.state.record_cycle(mode_name, False, time.time() - start, str(e))
            return False

    def run_sandbox_mode(self):
        """运行沙箱模式"""
        start = time.time()
        try:
            result = self.sandbox.run_experiment()
            ok = result.get("success", False)
            self.state.record_cycle("sandbox", ok, time.time() - start)
            return ok
        except Exception as e:
            self.state.record_cycle("sandbox", False, time.time() - start, str(e))
            return False

    def run_b2b_mode(self):
        """运行B2B模式"""
        start = time.time()
        try:
            result = self.b2b.run_cycle()
            ok = result.get("success", False)
            self.state.record_cycle("b2b", ok, time.time() - start)
            return ok
        except Exception as e:
            self.state.record_cycle("b2b", False, time.time() - start, str(e))
            return False

    def run_mcp_mode(self):
        """运行MCP模式"""
        start = time.time()
        try:
            result = self.mcp.run_cycle()
            ok = result.get("success", False)
            self.state.record_cycle("mcp", ok, time.time() - start)
            return ok
        except Exception as e:
            self.state.record_cycle("mcp", False, time.time() - start, str(e))
            return False

    def run_mode(self, mode_name: str):
        """调度单个模式"""
        config = COMPUTE_MODES[mode_name]
        logger.info(f"\n{'='*60}")
        logger.info(f"  {config['icon']} {config['name']}: {config['description']}")
        logger.info(f"{'='*60}")

        if mode_name == "sandbox":
            return self.run_sandbox_mode()
        elif mode_name == "b2b":
            return self.run_b2b_mode()
        elif mode_name == "mcp":
            return self.run_mcp_mode()
        elif config.get("script"):
            return self.run_script_mode(mode_name, config)
        else:
            return False

    def mode_loop(self, mode_name: str):
        """模式循环线程"""
        config = COMPUTE_MODES[mode_name]
        interval = config["interval_seconds"]
        logger.info(f"[{mode_name}] Thread started, interval={interval}s")

        # 启动时立即运行一次
        self.run_mode(mode_name)

        while self.running:
            try:
                time.sleep(interval)
                if not self.running:
                    break
                self.run_mode(mode_name)
            except Exception as e:
                logger.error(f"[{mode_name}] Loop error: {e}")
                time.sleep(10)

    def start_all_modes(self):
        """启动所有模式的并行线程"""
        logger.info("\n" + "=" * 70)
        logger.info("    Antigravity Master Controller V3.0 — 7x24 Launch")
        logger.info("=" * 70)
        logger.info(f"  Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"  Project root: {_PROJECT_ROOT}")
        logger.info(f"  Modes: {len(COMPUTE_MODES)} enabled")

        for mode_name, config in COMPUTE_MODES.items():
            if not config["enabled"]:
                logger.info(f"  {config['icon']} SKIP (disabled)")
                continue
            logger.info(f"  {config['icon']} START: interval={config['interval_seconds']}s")

        logger.info("=" * 70)

        # 启动所有模式的并行线程
        for mode_name, config in COMPUTE_MODES.items():
            if not config["enabled"]:
                continue
            t = threading.Thread(
                target=self.mode_loop,
                args=(mode_name,),
                name=f"mode-{mode_name}",
                daemon=True,
            )
            t.start()
            self.threads[mode_name] = t
            time.sleep(1)  # 错峰启动

    def status_report(self):
        """打印状态报告"""
        health = {
            "uptime": datetime.now() - datetime.fromisoformat(self.state.state["started_at"]),
            "modes": {},
            "errors": len(self.state.state["errors"]),
        }
        for mode_name, mode_data in self.state.state.get("modes", {}).items():
            health["modes"][mode_name] = {
                "runs": mode_data.get("runs", 0),
                "success_rate": f"{mode_data.get('successes', 0)}/{mode_data.get('runs', 0)}",
                "last_run": mode_data.get("last_run", "never"),
            }

        report = json.dumps(health, ensure_ascii=False, indent=2, default=str)
        logger.info(f"\n[STATUS]\n{report}")
        return health

    def stop(self):
        """停止所有模式"""
        logger.info("\nShutting down all modes...")
        self.running = False
        for mode_name in self.threads:
            self.threads[mode_name].join(timeout=5)
        self.state.save()
        logger.info("Master Controller stopped.")


def main():
    master = AntigravityMaster()

    def signal_handler(sig, frame):
        master.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    master.start_all_modes()

    # 主线程: 每5分钟打印一次健康状态
    while master.running:
        try:
            time.sleep(300)
            master.status_report()
        except KeyboardInterrupt:
            master.stop()
            break


if __name__ == "__main__":
    main()