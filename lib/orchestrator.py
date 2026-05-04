import os
import json
import subprocess
import time
import sys

# 强制 UTF-8 环境
os.environ["PYTHONIOENCODING"] = "utf-8"

class Orchestrator:
    """
    Antigravity Orchestrator V1.2 - 强力解码版
    """
    def __init__(self):
        self.workspace = r"e:\享中"
        self.scripts = {
            "fetcher": os.path.join(self.workspace, "skills", "truth_fetcher.py"),
            "chaos": os.path.join(self.workspace, "lib", "chaos_engine.py"),
            "evolver": os.path.join(self.workspace, "skills", "evolution_life.py")
        }

    def run_step(self, name, path):
        print(f"\n[ORCHESTRATOR] >>> Starting: {name}")
        try:
            # 显式指定编码为 utf-8，解决 subprocess 在 Windows 下的解码问题
            result = subprocess.run(
                ["python", path], 
                capture_output=True, 
                text=True, 
                check=True, 
                encoding='utf-8' 
            )
            print(result.stdout)
            return True
        except Exception as e:
            print(f"[ERROR] {name} failed: {e}")
            return False

    def pulse(self):
        print("--- Antigravity Lifeform: System Pulse Start ---")
        
        self.run_step("Perception", self.scripts["fetcher"])
        self.run_step("Chaos", self.scripts["chaos"])
        self.run_step("Evolution", self.scripts["evolver"])
        
        decision_path = os.path.join(self.workspace, "latest_decision.json")
        if os.path.exists(decision_path):
            with open(decision_path, "r", encoding='utf-8') as f:
                res = json.load(f)
            print("\n" + "#"*40)
            print(f"PULSE COMPLETE: Period {res['period']}")
            print(f"RED:  {res['red']}")
            print(f"BLUE: {res['blue']}")
            print(f"ENG:  {res['engine']}")
            print("#"*40)

if __name__ == "__main__":
    # 设置系统输出流
    if sys.stdout.encoding != 'utf-8':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    brain = Orchestrator()
    brain.pulse()
