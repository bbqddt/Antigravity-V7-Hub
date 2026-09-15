# -*- coding: utf-8 -*-
"""
Antigravity 多云端部署器 V1.0
================================
将项目打包上传到多个云平台，让多AI协同进化引擎7×24小时并行计算。

目标云平台:
1. 腾讯云 CVM (已有) — 32核/123GB，长期守护进程
2. GitHub Actions — 免费CI/CD，定时触发进化循环
3. 分布式桥接 (QwenPaw) — AgentScope远程节点

用法:
    python cloud_all_deployer.py --deploy-all      # 全平台部署
    python cloud_all_deployer.py --tencent         # 仅腾讯云
    python cloud_all_deployer.py --github          # 仅GitHub Actions
    python cloud_all_deployer.py --poll-results    # 轮询所有云端结果
    python cloud_all_deployer.py --status          # 查看各云状态
"""
import sys
import os
import json
import time
import hashlib
import tarfile
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, 'reconfigure') else None

_PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROJECT_ROOT))

LOG_DIR = _PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
DEPLOY_STATE_FILE = _PROJECT_ROOT / "cloud_deploy_state.json"


def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    try:
        with open(LOG_DIR / "cloud_deploy.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass


def load_deploy_state() -> Dict:
    if DEPLOY_STATE_FILE.exists():
        with open(DEPLOY_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"platforms": {}, "last_sync": None, "total_deployments": 0}


def save_deploy_state(state: Dict):
    state["last_sync"] = datetime.now().isoformat()
    with open(DEPLOY_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════════
# 1. 腾讯云 CVM 部署
# ═══════════════════════════════════════════════════════════

class TencentCloudDeployer:
    """腾讯云 CVM 部署 — SSH直连"""

    def __init__(self):
        self.host = os.environ.get("CLOUD_HOST", "YOUR_CLOUD_IP_HERE")
        self.user = os.environ.get("CLOUD_USER", "admin")
        self.password = os.environ.get("CLOUD_PASS", "5YK9LaJ6KOwFKmLLkPuO")
        self.port = int(os.environ.get("CLOUD_PORT", "22"))
        self.remote_base = f"/home/{self.user}/antigravity"
        self.connected = False

    def _ssh_cmd(self, cmd: str) -> subprocess.CompletedProcess:
        full_cmd = (
            f'sshpass -p "{self.password}" ssh -o StrictHostKeyChecking=no '
            f'-p {self.port} {self.user}@{self.host} "{cmd}"'
        )
        return subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=60)

    def check_connectivity(self) -> bool:
        result = self._ssh_cmd("echo connected && hostname")
        if result.returncode == 0 and "connected" in result.stdout:
            self.connected = True
            log(f"腾讯云连接成功: {result.stdout.strip()}")
            return True
        log(f"腾讯云连接失败: {result.stderr[:200]}", "WARN")
        return False

    def create_tarball(self) -> Path:
        archive_path = _PROJECT_ROOT / "multi_ai_evolution_deploy.tar.gz"
        log(f"打包项目到 {archive_path}...")

        exclude_names = [
            ".venv", "__pycache__", "*.pyc", "node_modules", ".git",
            "archive", "models", "dist", "*.exe", "*.vbs", "*.bat",
            "*.ps1", ".env", "keys.json", "antigravity_deploy.tar.gz",
            "cloud_runner.pid", "logs",
        ]

        def filter_fn(tarinfo):
            name = tarinfo.name
            for exc in exclude_names:
                if exc.startswith("*"):
                    if name.endswith(exc[1:]):
                        return None
                elif exc in name:
                    return None
            return tarinfo

        with tarfile.open(archive_path, "w:gz") as tar:
            for item in _PROJECT_ROOT.iterdir():
                if item.name == "multi_ai_evolution_deploy.tar.gz":
                    continue
                arcname = item.name
                if item.is_dir():
                    tar.add(item, arcname=arcname, filter=filter_fn)
                else:
                    tar.add(item, arcname=arcname)

        size_mb = archive_path.stat().st_size / (1024 * 1024)
        log(f"打包完成: {size_mb:.1f} MB")
        return archive_path

    def upload_and_extract(self, archive: Path):
        remote_dest = f"{self.user}@{self.host}:{self.remote_base}/{archive.name}"
        cmd = f'scp -P {self.port} -o StrictHostKeyChecking=no "{archive}" {remote_dest}'
        log(f"上传到腾讯云...")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            log(f"上传失败: {result.stderr[:200]}", "ERROR")
            return
        log("上传成功，解压中...")
        self._ssh_cmd(f"cd {self.remote_base.parent} && tar xzf {archive.name}")
        self._ssh_cmd(f"rm -f {self.remote_base.parent}/{archive.name}")
        log("解压完成")

    def deploy_evolution_daemon(self):
        """部署多AI进化守护脚本到腾讯云"""
        daemon_script = f'''#!/bin/bash
# Antigravity 多AI协同进化引擎 — 腾讯云守护脚本
cd "{self.remote_base}"
source .venv/bin/activate

LOG_FILE="$PWD/logs/evolution_daemon.log"
PID_FILE="$PWD/logs/evolution.pid"

mkdir -p "$PWD/logs"

cleanup() {{
    echo "[$(date)] 停止进化引擎..." >> "$LOG_FILE"
    if [ -f "$PID_FILE" ]; then
        kill $(cat "$PID_FILE") 2>/dev/null
        rm -f "$PID_FILE"
    fi
}}

trap cleanup EXIT INT TERM

echo "[$(date)] === 多AI协同进化引擎启动 ===" >> "$LOG_FILE"
echo "[$(date)] 主机: $(hostname) | CPU: $(nproc)核 | 内存: $(free -g | awk \\'{{print $2}}\\')G" >> "$LOG_FILE"

# 持续运行：每2小时跑一轮大规模进化
while true; do
    echo "[$(date)] === 开始进化周期 ===" >> "$LOG_FILE"

    # 数据采集
    python3 data_updater_v2.py >> "$LOG_FILE" 2>&1 || echo "数据更新失败" >> "$LOG_FILE"

    # 多AI协同进化
    python3 multi_ai_evolution_engine.py --generations 5 --candidates 10 >> "$LOG_FILE" 2>&1 || echo "进化失败" >> "$LOG_FILE"

    # 回测验证
    if [ -f "walkforward_backtest_v2.py" ]; then
        python3 walkforward_backtest_v2.py >> "$LOG_FILE" 2>&1 || true
    fi

    echo "[$(date)] === 本轮完成 ===" >> "$LOG_FILE"
    echo "[$(date)] 等待2小时..." >> "$LOG_FILE"
    sleep 7200
done
'''
        daemon_path = self.remote_base + "/evolution_daemon.sh"
        self._ssh_cmd(f"cat > {daemon_path} << 'DAEMON_EOF'\n{daemon_script}\nDAEMON_EOF")
        self._ssh_cmd(f"chmod +x {daemon_path}")
        log("进化守护脚本已部署")

    def start_daemon(self):
        """启动守护进程"""
        self._ssh_cmd("pkill -f 'evolution_daemon.sh' 2>/dev/null || true")
        self._ssh_cmd(
            f"nohup bash {self.remote_base}/evolution_daemon.sh "
            f"> {self.remote_base}/logs/evolution_stdout.log 2>&1 & "
            f"echo $! > {self.remote_base}/logs/evolution.pid"
        )
        time.sleep(3)
        result = self._ssh_cmd("ps aux | grep evolution_daemon | grep -v grep")
        if result.returncode == 0 and result.stdout.strip():
            log("腾讯云守护进程已启动!")
            return True
        log("守护进程可能未正常启动", "WARN")
        return False

    def poll_results(self) -> Dict:
        """拉取云端进化结果"""
        result = self._ssh_cmd(f"cat {self.remote_base}/evolution_state_v20.json 2>/dev/null | head -100")
        if result.returncode == 0:
            try:
                return json.loads(result.stdout)
            except:
                pass
        return {}

    def get_status(self) -> Dict:
        status = {"platform": "tencent_cvm", "host": self.host}
        result = self._ssh_cmd("ps aux | grep evolution | grep -v grep || true")
        status["daemon_running"] = bool(result.stdout.strip())
        result = self._ssh_cmd(f"ls -la {self.remote_base}/multi_ai_evolution_engine.py 2>/dev/null || echo not_found")
        status["engine_deployed"] = "not_found" not in result.stdout
        return status


# ═══════════════════════════════════════════════════════════
# 2. GitHub Actions 部署
# ═══════════════════════════════════════════════════════════

class GithubActionsDeployer:
    """GitHub Actions 定时部署 — 免费CI/CD"""

    def __init__(self):
        self.github_repo = os.environ.get("GITHUB_REPOSITORY", "")
        self.github_token = os.environ.get("GITHUB_TOKEN", "")
        self.deployed = False

    def check_prerequisites(self) -> bool:
        """检查GitHub环境"""
        if not self.github_repo:
            log("未检测到GITHUB_REPOSITORY环境变量", "WARN")
            log("GitHub Actions部署需要仓库环境，跳过", "WARN")
            return False
        if not self.github_token:
            log("未检测到GITHUB_TOKEN", "WARN")
            return False
        return True

    def create_workflow_file(self) -> Path:
        """创建GitHub Actions工作流文件"""
        workflows_dir = _PROJECT_ROOT / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)

        workflow_content = '''name: Multi-AI Evolution Engine

on:
  schedule:
    # 每天UTC 00:00运行（北京时间8:00）
    - cron: '0 0 * * *'
    # 每6小时运行一次大规模进化
    - cron: '0 */6 * * *'
  workflow_dispatch:  # 允许手动触发

permissions:
  contents: write

jobs:
  evolution:
    runs-on: ubuntu-latest
    timeout-minutes: 55

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install pandas numpy scipy scikit-learn torch beautifulsoup4 requests httpx matplotlib seaborn

      - name: Run evolution cycle
        env:
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
        run: |
          python multi_ai_evolution_engine.py --generations 3 --candidates 5 --export

      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: evolution-results
          path: |
            evolution_state_v20.json
            top_candidates_export.json
            logs/
          retention-days: 7

      - name: Commit results
        run: |
          git config user.name "Evolution Bot"
          git config user.email "bot@antigravity.local"
          git add evolution_state_v20.json top_candidates_export.json
          git commit -m "Auto-evolution: ${{ github.run_number }}" || echo "No changes"
          git push || echo "Push failed (fork?)"
'''
        workflow_file = workflows_dir / "multi_ai_evolution.yml"
        with open(workflow_file, "w", encoding="utf-8") as f:
            f.write(workflow_content)
        log(f"GitHub Actions工作流已创建: {workflow_file}")
        return workflow_file

    def create_secrets_instruction(self) -> str:
        """生成设置secrets的说明"""
        return """
GitHub Actions 需要配置以下Secrets才能调用云端AI模型:

1. 打开仓库 → Settings → Secrets and variables → Actions
2. 添加以下Secrets:
   - OPENROUTER_API_KEY: sk-or-v1-...
   - GEMINI_API_KEY: AIza...
   - DEEPSEEK_API_KEY: sk-...
   - DEEPRouter_API_KEY_1: sk-...

注意: GitHub Actions是Ubuntu环境，不支持Ollama本地模型。
云端模型通过API调用，不受影响。
"""

    def deploy(self) -> bool:
        if not self.check_prerequisites():
            log("GitHub Actions环境不可用，跳过自动部署")
            log("请手动将 .github/workflows/multi_ai_evolution.yml 推送到GitHub仓库")
            return False

        self.create_workflow_file()
        self.deployed = True
        log("GitHub Actions工作流已就绪，推送后生效")
        return True


# ═══════════════════════════════════════════════════════════
# 3. 分布式桥接 (QwenPaw / 其他节点)
# ═══════════════════════════════════════════════════════════

class DistributedDeployer:
    """分布式部署 — 向QwenPaw等远程节点发布进化任务"""

    def __init__(self):
        self.dist_dir = _PROJECT_ROOT / "dist"
        self.tasks_dir = self.dist_dir / "tasks"
        self.results_dir = self.dist_dir / "results"

    def setup(self):
        for d in [self.dist_dir, self.tasks_dir, self.results_dir,
                  self.dist_dir / "state" / "processed"]:
            d.mkdir(parents=True, exist_ok=True)
        log("分布式目录已初始化")

    def publish_evolution_task(self, generations: int = 5, candidates_per_ai: int = 10) -> Dict:
        """发布进化任务给远程节点"""
        task = {
            "task_id": hashlib.md5(f"evolution_{datetime.now().isoformat()}".encode()).hexdigest()[:12],
            "task_type": "multi_ai_evolution",
            "description": f"多AI协同进化: {generations}代 × {candidates_per_ai}候选",
            "module": "multi_ai_evolution_engine",
            "func": "quick_evolution",
            "params": {
                "generations": generations,
                "candidates_per_ai": candidates_per_ai,
            },
            "input_files": ["data/lottery_history.csv"],
            "output_files": [
                "evolution_state_v20.json",
                "top_candidates_export.json",
                "multi_ai_analysis.json",
            ],
            "estimated_time": 600,
            "created_at": datetime.now().isoformat(),
            "priority": "high",
            "status": "pending",
            "assigned_to": "distributed_nodes",
        }

        task_file = self.tasks_dir / f"{task['task_id']}.json"
        with open(task_file, "w", encoding="utf-8") as f:
            json.dump(task, f, ensure_ascii=False, indent=2)

        log(f"进化任务已发布: {task['task_id']}")
        return task

    def poll_results(self) -> Dict[str, Dict]:
        results = {}
        if self.results_dir.exists():
            for f in self.results_dir.glob("*.json"):
                try:
                    with open(f, "r", encoding="utf-8") as fh:
                        results[f.stem] = json.load(fh)
                except:
                    pass
        return results


# ═══════════════════════════════════════════════════════════
# 4. 多云端统一编排器
# ═══════════════════════════════════════════════════════════

class MultiCloudDeployer:
    """多云端统一部署器"""

    def __init__(self):
        self.tencent = TencentCloudDeployer()
        self.github = GithubActionsDeployer()
        self.distributed = DistributedDeployer()
        self.state = load_deploy_state()

    def deploy_all(self):
        """全平台部署"""
        log("=" * 60)
        log("  多云端部署 — 开始")
        log("=" * 60)

        # 1. 腾讯云
        log("\n--- 1/3 腾讯云 CVM ---")
        if self.tencent.check_connectivity():
            archive = self.tencent.create_tarball()
            self.tencent.upload_and_extract(archive)
            self.tencent.deploy_evolution_daemon()
            self.tencent.start_daemon()
            self.state["platforms"]["tencent"] = {"deployed": True, "timestamp": datetime.now().isoformat()}
            self.state["total_deployments"] += 1
            log("✅ 腾讯云部署完成")
        else:
            log("❌ 腾讯云连接失败，跳过", "ERROR")

        # 2. GitHub Actions
        log("\n--- 2/3 GitHub Actions ---")
        if self.github.deploy():
            self.state["platforms"]["github_actions"] = {"deployed": True, "timestamp": datetime.now().isoformat()}
            self.state["total_deployments"] += 1
            log("✅ GitHub Actions工作流已创建")
            log(self.github.create_secrets_instruction())
        else:
            log("⚠️ GitHub Actions环境不可用，需手动推送工作流文件", "WARN")

        # 3. 分布式
        log("\n--- 3/3 分布式节点 ---")
        self.distributed.setup()
        task = self.distributed.publish_evolution_task(generations=5, candidates_per_ai=10)
        self.state["platforms"]["distributed"] = {"deployed": True, "task_id": task["task_id"], "timestamp": datetime.now().isoformat()}
        self.state["total_deployments"] += 1
        log("✅ 分布式任务已发布")

        save_deploy_state(self.state)
        log(f"\n{'='*60}")
        log(f"  多云端部署完成! 总部署次数: {self.state['total_deployments']}")
        log(f"{'='*60}")

    def poll_all_results(self):
        """轮询所有云端的结果"""
        log("=" * 60)
        log("  轮询所有云端结果")
        log("=" * 60)

        results = {}

        # 腾讯云
        log("\n--- 腾讯云 ---")
        tencent_result = self.tencent.poll_results()
        if tencent_result:
            results["tencent"] = tencent_result
            log(f"  收到腾讯云结果: {len(tencent_result)} 字段")
        else:
            log("  腾讯云无新结果")

        # 分布式
        log("\n--- 分布式节点 ---")
        dist_results = self.distributed.poll_results()
        if dist_results:
            results["distributed"] = dist_results
            log(f"  收到 {len(dist_results)} 个分布式结果")
        else:
            log("  分布式无新结果")

        # 本地
        log("\n--- 本地 ---")
        local_state_file = _PROJECT_ROOT / "evolution_state_v20.json"
        if local_state_file.exists():
            with open(local_state_file, "r", encoding="utf-8") as f:
                local_result = json.load(f)
            results["local"] = local_result
            log(f"  本地有最新结果")
        else:
            log("  本地无结果")

        # 汇总报告
        log(f"\n{'='*60}")
        log(f"  汇总报告")
        log(f"{'='*60}")
        for platform, data in results.items():
            best = data.get("best_formula")
            if best:
                log(f"  [{platform}] 最佳公式: {best.get('name', '?')} (fitness={best.get('fitness_score', 0):.2f})")
            else:
                gen = data.get("total_generations", "?")
                pool = len(data.get("survival_pool", []))
                log(f"  [{platform}] 代数: {gen}, 存活池: {pool}")

        save_deploy_state({**self.state, "last_poll": datetime.now().isoformat(), "results_summary": results})
        return results

    def show_status(self):
        """显示多云端状态"""
        log("=" * 60)
        log("  多云端部署状态")
        log("=" * 60)

        for plat_name, plat_state in self.state.get("platforms", {}).items():
            deployed = plat_state.get("deployed", False)
            ts = plat_state.get("timestamp", "未知")
            status = "✅ 已部署" if deployed else "❌ 未部署"
            log(f"  {plat_name}: {status} (最后同步: {ts})")

        log(f"\n  总部署次数: {self.state.get('total_deployments', 0)}")
        log(f"  最后轮询: {self.state.get('last_poll', '从未')}")


# ═══════════════════════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Antigravity 多云端部署器")
    parser.add_argument("--deploy-all", action="store_true", help="全平台部署")
    parser.add_argument("--tencent", action="store_true", help="仅腾讯云")
    parser.add_argument("--github", action="store_true", help="仅GitHub Actions")
    parser.add_argument("--poll-results", action="store_true", help="轮询所有云端结果")
    parser.add_argument("--status", action="store_true", help="查看各云状态")
    args = parser.parse_args()

    deployer = MultiCloudDeployer()

    if args.deploy_all:
        deployer.deploy_all()
    elif args.tencent:
        deployer.tencent.check_connectivity()
        archive = deployer.tencent.create_tarball()
        deployer.tencent.upload_and_extract(archive)
        deployer.tencent.deploy_evolution_daemon()
        deployer.tencent.start_daemon()
    elif args.github:
        deployer.github.deploy()
    elif args.poll_results:
        deployer.poll_all_results()
    elif args.status:
        deployer.show_status()
    else:
        # 默认：全平台部署
        deployer.deploy_all()
