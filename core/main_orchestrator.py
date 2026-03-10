# ==============================================================================
# 文件名: main_orchestrator.py
# 核心驱动: Antigravity 3.1 Pro (一键自动化调度)
# ==============================================================================

import subprocess
import os
import time

def run_pipeline():
    print("🚀 [Antigravity 3.1] 启动全自动反重力演进序列...")
    
    # 1. 自动同步最新因果数据
    print("\n📡 第一阶段：同步中彩网物理指纹...")
    subprocess.run(["python", "e:/享中/core/genesis_crawler.py"])
    
    # 2. 自动启动 AI 演进
    print("\n🧬 第二阶段：启动 PINN 物理信息神经网络演进...")
    subprocess.run(["python", "e:/享中/core/self_evolver.py"])
    
    print("\n✅ [序列完成] 建议号码已根据最新 23 年数据对齐。")

if __name__ == "__main__":
    run_pipeline()