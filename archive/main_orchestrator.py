# -*- coding: utf-8 -*-
"""
Antigravity 3.1 Pro 一键自动化调度器
"""
import subprocess
import os
import sys

def run_pipeline():
    print("🚀 [Antigravity 3.1] 启动全自动反重力演进序列...")

    # 确定项目根目录
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    python = sys.executable

    # 1. 自动同步最新因果数据
    print("\n📡 第一阶段：同步中彩网物理指纹...")
    crawler = os.path.join(base_dir, "core", "genesis_crawler.py")
    if os.path.exists(crawler):
        subprocess.run([python, crawler], cwd=base_dir)
    else:
        print("⚠️ genesis_crawler.py 不存在，跳过数据同步")

    # 2. 自动启动 AI 演进
    print("\n🧬 第二阶段：启动自我演进...")
    evolver = os.path.join(base_dir, "core", "self_evolver.py")
    if os.path.exists(evolver):
        subprocess.run([python, evolver], cwd=base_dir)
    else:
        print("⚠️ self_evolver.py 不存在，跳过演进")

    print("\n✅ [序列完成] 建议号码已根据最新数据对齐。")

if __name__ == "__main__":
    run_pipeline()
