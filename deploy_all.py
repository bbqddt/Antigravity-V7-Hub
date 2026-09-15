# -*- coding: utf-8 -*-
"""
Antigravity 统一部署入口 — 一键部署到所有平台
=============================================

用法:
    python deploy_all.py --hf --e2b --cloud --agentscope --posit --kaggle --domcloud --vocon --endless --token-file tokens.json
    python deploy_all.py --hf --space user/Antigravity --e2b --generations 20
    python deploy_all.py --cloud --cloud-action sync

tokens.json 格式:
{
    "hf_token": "hf_xxx",
    "e2b_api_key": "e2b_xxx",
    "cloud_host": "10.xxx.xxx.xxx",
    "cloud_user": "admin",
    "cloud_pass": "xxx",
    "openrouter_key": "sk-or-xxx",
    "siliconflow_key": "sk-xxx",
    "cc_switch_key": "sk-xxx"
}
"""
import os
import sys
import json
import argparse
import subprocess
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent


def load_tokens(token_file: str) -> dict:
    """加载 Token 配置"""
    if not token_file:
        return {}
    
    path = Path(token_file)
    if not path.exists():
        print("[WARN] Token 文件不存在: " + token_file)
        return {}
    
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_cmd(cmd: list, cwd: Path = None) -> tuple:
    """运行命令并返回 (success, output)"""
    try:
        result = subprocess.run(
            cmd, cwd=cwd or _PROJECT_ROOT,
            capture_output=True, text=True, timeout=600
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "命令超时"
    except Exception as e:
        return False, str(e)


def deploy_hf(tokens: dict, space: str = None, quiet: bool = False) -> bool:
    """部署到 HF Spaces"""
    print("\n" + "=" * 60)
    print("[HF SPACES] 部署")
    print("=" * 60)
    
    token = tokens.get("hf_token") or os.environ.get("HF_TOKEN")
    if not token:
        print("[SKIP] HF_TOKEN 未提供")
        return False
    
    if not space:
        space = tokens.get("hf_space") or "username/Antigravity"
    
    cmd = [
        sys.executable, "hf_space/deploy_hf.py",
        "--space", space,
        "--token", token,
    ]
    if quiet:
        cmd.append("--quiet")
    
    success, output = run_cmd(cmd)
    print(output)
    return success


def deploy_e2b(tokens: dict, generations: int = 10, population: int = 20) -> bool:
    """部署到 E2B Sandbox"""
    print("\n" + "=" * 60)
    print("[E2B] 部署")
    print("=" * 60)
    
    api_key = tokens.get("e2b_api_key") or os.environ.get("E2B_API_KEY")
    if not api_key:
        print("[SKIP] E2B_API_KEY 未提供")
        return False
    
    cmd = [
        sys.executable, "deploy_e2b.py",
        "--api-key", api_key,
        "--generations", str(generations),
        "--population", str(population),
    ]
    
    success, output = run_cmd(cmd)
    print(output)
    return success


def deploy_cloud(tokens: dict, action: str = "deploy") -> bool:
    """部署到腾讯云"""
    print("\n" + "=" * 60)
    print("[CLOUD] 部署")
    print("=" * 60)
    
    required = ["cloud_host", "cloud_user", "cloud_pass"]
    if not all(k in tokens for k in required):
        print("[SKIP] 云端配置不完整 (需要 cloud_host, cloud_user, cloud_pass)")
        return False
    
    env = os.environ.copy()
    env.update({
        "CLOUD_HOST": tokens["cloud_host"],
        "CLOUD_USER": tokens["cloud_user"],
        "CLOUD_PASS": tokens["cloud_pass"],
        "CLOUD_PORT": str(tokens.get("cloud_port", 22)),
    })
    
    # 处理 deploy-monitor 动作（需要同步文件后执行部署脚本）
    if action == "deploy-monitor":
        print("[INFO] 部署监控面板 systemd 服务，先同步文件...")
        sync_cmd = [sys.executable, "cloud_quick_deploy.py", "--sync"]
        try:
            result = subprocess.run(sync_cmd, cwd=_PROJECT_ROOT, env=env, capture_output=True, text=True, timeout=300)
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
        except Exception as e:
            print(f"[WARN] 同步文件失败: {e}")
    
    cmd = [sys.executable, "cloud_quick_deploy.py", "--" + action]
    
    try:
        result = subprocess.run(
            cmd, cwd=_PROJECT_ROOT, env=env,
            capture_output=True, text=True, timeout=600
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return result.returncode == 0
    except Exception as e:
        print("[FAIL] 云端部署异常: " + str(e))
        return False


def deploy_agentscope(tokens: dict) -> bool:
    """部署到 AgentScope 平台"""
    print("\n" + "=" * 60)
    print("[AGENTSCOPE] 部署")
    print("=" * 60)
    
    cmd = [sys.executable, "deploy_agentscope.py"]
    if tokens.get("hf_token"):
        cmd.extend(["--hf-token", tokens["hf_token"]])
    if tokens.get("openrouter_key"):
        cmd.extend(["--openrouter-key", tokens["openrouter_key"]])
    
    success, output = run_cmd(cmd)
    print(output)
    return success


def deploy_posit(tokens: dict) -> bool:
    """部署到 Posit Cloud"""
    print("\n" + "=" * 60)
    print("[POSIT CLOUD] 部署")
    print("=" * 60)
    
    cmd = [sys.executable, "deploy_posit.py", "--create-project"]
    success, output = run_cmd(cmd)
    print(output)
    
    # 创建 Quarto 报告
    cmd2 = [sys.executable, "deploy_posit.py", "--create-quarto"]
    run_cmd(cmd2)
    
    return success


def deploy_kaggle(tokens: dict) -> bool:
    """部署到 Kaggle Notebooks"""
    print("\n" + "=" * 60)
    print("[KAGGLE] 部署")
    print("=" * 60)
    
    cmd = [sys.executable, "deploy_kaggle.py", "--create-notebook"]
    success, output = run_cmd(cmd)
    print(output)
    return success


def deploy_domcloud(tokens: dict) -> bool:
    """部署到 DOM Cloud"""
    print("\n" + "=" * 60)
    print("[DOM CLOUD] 部署")
    print("=" * 60)
    
    cmd = [sys.executable, "deploy_domcloud.py", "--create-config"]
    success, output = run_cmd(cmd)
    print(output)
    return success


def deploy_vocon(tokens: dict) -> bool:
    """部署到 vocon IT Cloud"""
    print("\n" + "=" * 60)
    print("[VOCON IT CLOUD] 部署")
    print("=" * 60)
    
    cmd = [sys.executable, "deploy_vocon.py", "--dockerfile", "--k8s", "--compose"]
    success, output = run_cmd(cmd)
    print(output)
    return success


def deploy_endless(tokens: dict) -> bool:
    """部署到 The Endless Web / 共享主机"""
    print("\n" + "=" * 60)
    print("[ENDLESS WEB] 部署")
    print("=" * 60)
    
    cmd = [sys.executable, "deploy_endless.py", "--wsgi", "--passenger", "--htaccess", "--guide"]
    success, output = run_cmd(cmd)
    print(output)
    return success


def main():
    parser = argparse.ArgumentParser(description="Antigravity 统一部署")
    parser.add_argument("--hf", action="store_true", help="部署到 HF Spaces")
    parser.add_argument("--e2b", action="store_true", help="部署到 E2B Sandbox")
    parser.add_argument("--cloud", action="store_true", help="部署到腾讯云")
    parser.add_argument("--agentscope", action="store_true", help="部署到 AgentScope 平台")
    parser.add_argument("--posit", action="store_true", help="部署到 Posit Cloud")
    parser.add_argument("--kaggle", action="store_true", help="部署到 Kaggle Notebooks")
    parser.add_argument("--domcloud", action="store_true", help="部署到 DOM Cloud")
    parser.add_argument("--vocon", action="store_true", help="部署到 vocon IT Cloud")
    parser.add_argument("--endless", action="store_true", help="部署到 The Endless Web / 共享主机")
    parser.add_argument("--all", action="store_true", help="部署到所有平台")
    parser.add_argument("--token-file", default="tokens.json", help="Token 配置文件")
    parser.add_argument("--space", help="HF Space ID (如 user/Antigravity)")
    parser.add_argument("--generations", type=int, default=10, help="E2B 进化代数")
    parser.add_argument("--population", type=int, default=20, help="E2B 种群大小")
    parser.add_argument("--cloud-action", default="deploy", help="云端操作: deploy/sync/status/start/stop/deploy-monitor")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    args = parser.parse_args()

    if not any([args.hf, args.e2b, args.cloud, args.agentscope, args.posit, args.kaggle, args.domcloud, args.vocon, args.endless, args.all]):
        parser.print_help()
        print("\n示例:")
        print("  python deploy_all.py --all --token-file tokens.json")
        print("  python deploy_all.py --hf --space user/Antigravity --e2b --generations 20")
        print("  python deploy_all.py --cloud --cloud-action sync")
        print("  python deploy_all.py --kaggle --domcloud --vocon --endless --token-file tokens.json")
        sys.exit(1)

    if args.all:
        args.hf = args.e2b = args.cloud = args.agentscope = args.posit = args.kaggle = args.domcloud = args.vocon = args.endless = True

    # 加载 Token
    tokens = load_tokens(args.token_file)
    
    # 环境变量覆盖
    for key in ["hf_token", "e2b_api_key", "cloud_host", "cloud_user", "cloud_pass", "hf_space", "openrouter_key", "siliconflow_key", "cc_switch_key"]:
        env_key = key.upper()
        if env_key in os.environ:
            tokens[key] = os.environ[env_key]

    results = {}
    
    if args.hf:
        results["hf"] = deploy_hf(tokens, args.space, args.quiet)
    
    if args.e2b:
        results["e2b"] = deploy_e2b(tokens, args.generations, args.population)
    
    if args.cloud:
        results["cloud"] = deploy_cloud(tokens, args.cloud_action)
    
    if args.agentscope:
        results["agentscope"] = deploy_agentscope(tokens)
    
    if args.posit:
        results["posit"] = deploy_posit(tokens)
    
    if args.kaggle:
        results["kaggle"] = deploy_kaggle(tokens)
    
    if args.domcloud:
        results["domcloud"] = deploy_domcloud(tokens)
    
    if args.vocon:
        results["vocon"] = deploy_vocon(tokens)
    
    if args.endless:
        results["endless"] = deploy_endless(tokens)

    # 汇总
    print("\n" + "=" * 60)
    print("[SUMMARY] 部署结果汇总")
    print("=" * 60)
    for platform, success in results.items():
        status = "[OK]" if success else "[FAIL]"
        print("  " + platform.upper() + ": " + status)
    
    all_ok = all(results.values()) if results else False
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()