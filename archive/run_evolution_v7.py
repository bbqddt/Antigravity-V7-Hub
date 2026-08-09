# run_evolution_v7.py - Evolution Runner
import json
import os
import sys

# 路径配置 - 使用相对路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPT_FILE = os.path.join(SCRIPT_DIR, "v7_evolved_prompt.json")

def run_evolution():
    if not os.path.exists(PROMPT_FILE):
        print(f"Error: {PROMPT_FILE} not found.")
        return

    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    prompt = data["prompt"]
    target_period = data.get("target_period", "unknown")

    print(f">>> [Evolution v7] 启动 {target_period} 期全量推演...")
    print(f">>> [Basis] {data.get('evolution_basis', 'N/A')}")

    # 注意：OmniProxyClient 已从 test_proxy 移除（文件不存在）
    # 降级：直接使用本地预测引擎
    print("ℹ️ OmniProxyClient 已移除，使用本地预测引擎...")

    # 尝试使用 enhanced_predictor 作为替代
    enh_path = os.path.join(SCRIPT_DIR, "enhanced_predictor.py")
    if os.path.exists(enh_path):
        import subprocess
        result = subprocess.run(
            [sys.executable, enh_path, "--groups", "5", "--mode", "normal"],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            print("\n" + "=" * 60)
            print(f"  🏁 {target_period} 期决策输出 (基于增强预测器)")
            print("=" * 60)
            print(result.stdout[-1000:])
            archive_file = f"decision_{target_period}.txt"
            with open(archive_file, "w", encoding="utf-8") as f:
                f.write(result.stdout)
            print(f">>> 决策已归档至: {archive_file}")
        else:
            print(f"❌ 增强预测器失败: {result.stderr[:200]}")
    else:
        print("⚠️ enhanced_predictor.py 也不存在，无法执行推演。")

if __name__ == "__main__":
    run_evolution()
