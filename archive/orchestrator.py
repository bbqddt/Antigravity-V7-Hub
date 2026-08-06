# -*- coding: utf-8 -*-
"""
Antigravity Omni-Orchestrator V5.0 - 全域降维统御中枢
不再局限于单一的算力推演。整合所有核心模块。
"""
import os
import json
import subprocess
import time
import sys

# 强制 UTF-8 环境
os.environ["PYTHONIOENCODING"] = "utf-8"

class OrchestratorV5_Omni:
    """
    Antigravity Omni-Orchestrator V5.0
    整合 Playwright、Autoresearch、Evolution 等所有模块
    """
    def __init__(self):
        self.workspace = os.path.dirname(os.path.abspath(__file__))
        self.scripts = {
            "fetcher": os.path.join(self.workspace, "skills", "truth_fetcher.py"),
            "chaos": os.path.join(self.workspace, "chaos_engine.py"),
            "evolver_v4": os.path.join(self.workspace, "evolution_v4.py"),
            "observer": os.path.join(self.workspace, "skills", "spectrum_observer.py"),
            "autoresearch": os.path.join(self.workspace, "autoresearch_core.py"),
            "open_claw": os.path.join(self.workspace, "skills", "auto_login_openrouter.py"),
            "tinyfish": os.path.join(self.workspace, "skills", "tinyfish_agent.py"),
        }

    def run_step(self, name, path):
        print(f"\n[ORCHESTRATOR V5.0] >>> Starting: {name}")
        if not os.path.exists(path):
            print(f"[SKIP] {name}: 文件不存在 {path}")
            return False
        try:
            result = subprocess.run(
                [sys.executable, path],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.stdout:
                print(result.stdout[-500:])  # 限制输出长度
            if result.returncode != 0 and result.stderr:
                print(f"[WARN] {name} stderr: {result.stderr[-200:]}")
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print(f"[TIMEOUT] {name} 超时 (120s)")
            return False
        except Exception as e:
            print(f"[ERROR] {name} failed: {e}")
            return False

    def strike_pulse(self):
        print("--- Antigravity Lifeform: V5.0 Omni Strike Pulse Start ---")

        # 1. 获取最新现实
        self.run_step("Sync Reality", self.scripts["fetcher"])

        # 2. 混沌度量 (如果 chaos_engine.py 存在)
        if os.path.exists(self.scripts["chaos"]):
            self.run_step("Complexity Scan", self.scripts["chaos"])
        else:
            print("[SKIP] Complexity Scan: chaos_engine.py 不存在")

        # 3. V4.0 现实同步推演
        self.run_step("V4.0 Future Evolution", self.scripts["evolver_v4"])

        # 4. 视觉刷新
        self.run_step("Spectrum Refresh", self.scripts["observer"])

        decision_path = os.path.join(self.workspace, "latest_decision.json")
        if os.path.exists(decision_path):
            with open(decision_path, "r", encoding='utf-8') as f:
                res = json.load(f)
            print("\n" + "#" * 50)
            print(f"🔱 OMNI PULSE COMPLETE: Target Period {res.get('period', 'N/A')}")
            print(f"RED:  {res.get('red', 'N/A')}")
            print(f"BLUE: {res.get('blue', 'N/A')}")
            print(f"ENG:  {res.get('engine', 'N/A')}")
            print(f"ST:   {res.get('status', 'N/A')}")
            print("#" * 50)

    def launch_cognitive_invasion(self):
        """激活 Autoresearch 核心"""
        print("\n[OMNI-ORCHESTRATOR] ⚠️ Authorization Granted. Initiating Autoresearch Core...")
        self.run_step("Autoresearch Node", self.scripts["autoresearch"])

    def launch_playwright_claw(self):
        """释放 Playwright 钢铁之爪"""
        print("\n[OMNI-ORCHESTRATOR] ⚠️ Authorization Granted. Deploying ChromeAutomation Claw...")
        self.run_step("Open Claw Deployment", self.scripts["open_claw"])


if __name__ == "__main__":
    brain = OrchestratorV5_Omni()
    brain.strike_pulse()
    print("\n[OMNI] Testing connection to ancient weapons...")
    # brain.launch_cognitive_invasion()  # 待触发
    # brain.launch_playwright_claw()     # 待触发
