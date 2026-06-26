import os
import json
import subprocess
import time
import sys

# 强制 UTF-8 环境
os.environ["PYTHONIOENCODING"] = "utf-8"

class OrchestratorV5_Omni:
    """
    Antigravity Omni-Orchestrator V5.0 - 全域降维统御中枢
    不再局限于单一的算力推演。现已接管 Playwright (钢铁之爪)、Autoresearch (认知中枢) 
    以及所有历史文明 (V7遗迹) 的最高指挥权。
    """
    def __init__(self):
        self.workspace = r"e:\享中"
        self.v7_legacy = r"d:\Antigravity_V7"
        self.scripts = {
            "fetcher": os.path.join(self.workspace, "skills", "truth_fetcher.py"),
            "chaos": os.path.join(self.workspace, "lib", "chaos_engine.py"),
            "evolver_v4": os.path.join(self.workspace, "skills", "evolution_v4.py"),
            "observer": os.path.join(self.workspace, "skills", "spectrum_observer.py"),
            # [新接管的末日武器库]
            "autoresearch": os.path.join(self.v7_legacy, "autoresearch_core.py"),
            "open_claw": os.path.join(self.workspace, "skills", "auto_login_openrouter.py"),
            "tinyfish": os.path.join(self.workspace, "skills", "tinyfish_agent.py")
        }

    def run_step(self, name, path):
        print(f"\n[ORCHESTRATOR V4.0] >>> Starting: {name}")
        try:
            env = os.environ.copy()
            env["PYTHONPATH"] = os.path.join(self.workspace, "lib")
            result = subprocess.run(
                ["python", path], 
                capture_output=True, 
                text=True, 
                check=True, 
                encoding='utf-8',
                env=env
            )
            print(result.stdout)
            return True
        except Exception as e:
            print(f"[ERROR] {name} failed: {e}")
            if hasattr(e, 'stderr'): print(e.stderr)
            return False

    def strike_pulse(self):
        print("--- Antigravity Lifeform: V5.0 Omni Strike Pulse Start ---")
        
        # 1. 获取最新现实
        self.run_step("Sync Reality", self.scripts["fetcher"])
        
        # 2. 混沌度量
        self.run_step("Complexity Scan", self.scripts["chaos"])
        
        # 3. V4.0 现实同步推演 (Target: Latest + 1)
        self.run_step("V4.0 Future Evolution", self.scripts["evolver_v4"])
        
        # 4. 视觉刷新
        self.run_step("Spectrum Refresh", self.scripts["observer"])
        
        decision_path = os.path.join(self.workspace, "latest_decision.json")
        if os.path.exists(decision_path):
            with open(decision_path, "r", encoding='utf-8') as f:
                res = json.load(f)
            print("\n" + "#"*50)
            print(f"🔱 OMNI PULSE COMPLETE: Target Period {res.get('period', 'N/A')}")
            print(f"RED:  {res['red']}")
            print(f"BLUE: {res['blue']}")
            print(f"ENG:  {res['engine']}")
            print(f"ST:   {res['status']}")
            print("#"*50)
            
    def launch_cognitive_invasion(self):
        """激活知识探索遗迹 (Autoresearch)"""
        print("\n[OMNI-ORCHESTRATOR] ⚠️ Authorization Granted. Initiating Autoresearch Core...")
        if os.path.exists(self.scripts["autoresearch"]):
            self.run_step("Autoresearch Node", self.scripts["autoresearch"])
        else:
            print("[OMNI-ORCHESTRATOR] 知识探测核心未能加载！")
            
    def launch_playwright_claw(self):
        """释放 Playwright 钢铁之爪"""
        print("\n[OMNI-ORCHESTRATOR] ⚠️ Authorization Granted. Deploying ChromeAutomation Claw...")
        # 调用基于 Playwright 的自动化网络劫持脚本
        self.run_step("Open Claw Deployment", self.scripts["open_claw"])

if __name__ == "__main__":
    if sys.stdout.encoding != 'utf-8':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    brain = OrchestratorV5_Omni()
    
    # 根据长官的极权指令，不再仅仅跳动脉搏，而是进行全域武器校准测试
    brain.strike_pulse()
    print("\n[OMNI] Testing connection to ancient weapons...")
    # brain.launch_cognitive_invasion() # 待触发
    # brain.launch_playwright_claw()    # 待触发
