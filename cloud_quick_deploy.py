#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Antigravity 云端一键部署脚本 (简化版)
=====================================
本地运行此脚本，通过 SCP 上传必要文件到腾讯云，然后通过 SSH 启动。

前提条件:
  - 已安装 sshpass (sudo apt install sshpass)
  - 已知腾讯云的公网IP

用法:
    python cloud_quick_deploy.py --setup          # 首次部署（上传全部文件）
    python cloud_quick_deploy.py --start          # 启动守护进程
    python cloud_quick_deploy.py --stop           # 停止守护进程
    python cloud_quick_deploy.py --status         # 查看状态
    python cloud_quick_deploy.py --logs           # 查看日志
"""
import subprocess
import sys
import os
import time
from pathlib import Path

# ─── 配置 ─────────────────────────────────────────────
# ⚠️ 请将以下 IP 改为你的腾讯云公网 IP
# 在 QwenPaw 终端运行: curl -s ifconfig.me  获取公网IP
CLOUD_HOST = os.environ.get("CLOUD_HOST", "YOUR_CLOUD_IP_HERE")
CLOUD_USER = os.environ.get("CLOUD_USER", "admin")
CLOUD_PASS = os.environ.get("CLOUD_PASS", "5YK9LaJ6KOwFKmLLkPuO")
CLOUD_PORT = os.environ.get("CLOUD_PORT", "22")

PROJECT_ROOT = Path(__file__).resolve().parent
REMOTE_BASE = f"/home/{CLOUD_USER}/antigravity"


def run(cmd, **kwargs):
    """执行本地命令"""
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kwargs)


def ssh(cmd):
    """SSH 到云端执行命令"""
    full = (
        f'sshpass -p "{CLOUD_PASS}" ssh -p {CLOUD_PORT} '
        f'-o StrictHostKeyChecking=no -o ConnectTimeout=10 '
        f'{CLOUD_USER}@{CLOUD_HOST} "{cmd}"'
    )
    return run(full)


def scp_upload(local_path, remote_path):
    """上传文件到云端"""
    cmd = (
        f'scp -P {CLOUD_PORT} -o StrictHostKeyChecking=no '
        f'-o ConnectTimeout=10 "{local_path}" "{remote_path}"'
    )
    return run(cmd)


def scp_upload_dir(local_dir, remote_base):
    """上传整个目录（排除 .venv, __pycache__, archive）"""
    patterns = [
        "--exclude=.venv", "--exclude=__pycache__", "--exclude=*.pyc",
        "--exclude=archive", "--exclude=models", "--exclude=dist",
        "--exclude=*.log", "--exclude=.git", "--exclude=*.exe",
        "--exclude=*.vbs", "--exclude=*.bat", "--exclude=*.ps1",
        "--exclude=.env", "--exclude=keys.json",
    ]
    cmd = (
        f'scp -P {CLOUD_PORT} -r ' + ' '.join(patterns) +
        f' "{local_dir}/" "{remote_base}/"'
    )
    result = run(cmd, timeout=600)
    return result.returncode == 0, result.stderr[:500]


def check_connection():
    """检查云端连接"""
    result = ssh("echo ok && hostname")
    if result.returncode == 0 and "ok" in result.stdout:
        print(f"✅ 云端连接成功: {result.stdout.strip()}")
        return True
    else:
        print(f"❌ 无法连接云端 ({CLOUD_HOST})")
        if "YOUR_CLOUD_IP_HERE" in CLOUD_HOST:
            print("   ⚠️ 请先设置 CLOUD_HOST 环境变量或修改脚本中的 IP:")
            print("   python cloud_quick_deploy.py --setup  (需要先设置IP)")
        else:
            print(f"   错误信息: {result.stderr[:200]}")
            print(f"   提示: 请确认腾讯云是否开机且网络可达")
        return False


def cmd_setup():
    """首次部署：上传文件 + 安装依赖"""
    print("=" * 60)
    print("  Antigravity 云端一键部署")
    print(f"  目标: {CLOUD_USER}@{CLOUD_HOST}")
    print("=" * 60)

    # 1. 检查连接
    if not check_connection():
        sys.exit(1)

    # 2. 创建远程目录
    print("\n📁 创建云端目录...")
    ssh(f"mkdir -p {REMOTE_BASE}/data {REMOTE_BASE}/logs {REMOTE_BASE}/core")

    # 3. 上传项目文件
    print("\n📤 上传项目文件...")
    success, error = scp_upload_dir(str(PROJECT_ROOT), REMOTE_BASE)
    if success:
        print("   ✅ 文件上传完成")
    else:
        print(f"   ⚠️ 上传可能有问题: {error}")

    # 4. 同步数据文件（确保最新）
    print("\n📊 同步数据文件...")
    for f in (PROJECT_ROOT / "data").glob("*.csv"):
        scp_upload(str(f), f"{REMOTE_BASE}/data/")
        print(f"   ✅ {f.name}")

    # 同步关键 JSON
    for f in ["analysis_prior.json", "learning_state.json", "enhanced_state.json",
              "evolution_state_v2.json", "best_formula.json", "signal_fusion.py"]:
        src = PROJECT_ROOT / f
        if src.exists():
            scp_upload(str(src), f"{REMOTE_BASE}/")
            print(f"   ✅ {f}")

    # 5. 安装 Python 依赖
    print("\n🐍 安装 Python 依赖...")
    setup_result = ssh(f"""
        cd {REMOTE_BASE} &&
        # 检查 Python3
        python3 --version &&
        # 创建虚拟环境
        python3 -m venv .venv &&
        # 升级 pip
        .venv/bin/pip install --upgrade pip setuptools wheel -q &&
        # 安装核心依赖
        .venv/bin/pip install pandas numpy scipy scikit-learn torch \\
            beautifulsoup4 requests httpx matplotlib seaborn -q 2>&1 | tail -5
    """)
    if setup_result.returncode == 0:
        print("   ✅ 依赖安装完成")
        print(setup_result.stdout[-200:])
    else:
        print(f"   ⚠️ 依赖安装输出:\n{setup_result.stdout[-500:]}")
        print(f"   错误: {setup_result.stderr[:200]}")

    # 6. 验证部署
    print("\n🔍 验证部署...")
    verify = ssh(f"""
        cd {REMOTE_BASE} &&
        echo '--- 文件列表 ---' &&
        ls -la *.py | head -20 &&
        echo '--- 数据文件 ---' &&
        ls -la data/ &&
        echo '--- Python 版本 ---' &&
        python3 --version &&
        echo '--- 核心依赖 ---' &&
        .venv/bin/python -c 'import pandas, numpy, scipy, sklearn; print(f"pandas={pandas.__version__}, numpy={numpy.__version__}")'
    """)
    print(verify.stdout)

    print("\n" + "=" * 60)
    print("  ✅ 部署完成!")
    print(f"  📍 云端路径: {REMOTE_BASE}")
    print(f"  ▶️  启动: python cloud_quick_deploy.py --start")
    print("=" * 60)


def cmd_start():
    """启动云端守护进程"""
    print("▶️  启动云端守护进程...")

    # 先杀旧进程
    ssh("pkill -f 'cloud_runner_v2.py' 2>/dev/null || true")
    time.sleep(1)

    # 启动
    result = ssh(f"""
        cd {REMOTE_BASE} &&
        nohup .venv/bin/python cloud_runner_v2.py --daemon > logs/cloud_runner_v2.log 2>&1 &
        echo $! > logs/cloud_runner.pid
        sleep 2 &&
        ps -p $(cat logs/cloud_runner.pid) &&
        echo '守护进程已启动'
    """)
    print(result.stdout)
    if result.returncode == 0:
        print("✅ 云端守护进程已启动!")
    else:
        print("⚠️ 启动可能有问题，请检查日志")


def cmd_stop():
    """停止云端守护进程"""
    print("🛑 停止云端守护进程...")
    pid_file = f"{REMOTE_BASE}/logs/cloud_runner.pid"
    ssh(f"kill $(cat {pid_file}) 2>/dev/null || pkill -f 'cloud_runner_v2.py' || echo '未运行'")
    print("✅ 已停止")


def cmd_status():
    """查看云端状态"""
    print("🔍 云端状态:")
    print()

    # 进程
    result = ssh(f"ps aux | grep cloud_runner | grep -v grep || echo '进程: 未运行'")
    print(f"📌 进程:\n{result.stdout}")

    # 系统资源
    result = ssh("echo 'CPU: ' && nproc && echo '内存: ' && free -h | head -2 && echo '负载: ' && cat /proc/loadavg")
    print(f"\n📌 系统资源:\n{result.stdout}")

    # 日志尾部
    result = ssh(f"tail -30 {REMOTE_BASE}/logs/cloud_runner_v2.log 2>/dev/null || echo '无日志'")
    print(f"\n📌 最新日志:\n{result.stdout}")

    # 预测结果
    result = ssh(f"cat {REMOTE_BASE}/latest_prediction.json 2>/dev/null | head -30 || echo '无预测结果'")
    print(f"\n📌 最新预测:\n{result.stdout}")


def cmd_logs():
    """查看云端日志"""
    result = ssh(f"tail -100 {REMOTE_BASE}/logs/cloud_runner_v2.log 2>/dev/null || echo '无日志'")
    print(result.stdout)


def cmd_sync():
    """增量同步（只上传变化的文件）"""
    print("🔄 增量同步...")
    success, error = scp_upload_dir(str(PROJECT_ROOT), REMOTE_BASE)
    if success:
        print("✅ 同步完成")
    else:
        print(f"⚠️ 同步可能有误: {error}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Antigravity 云端一键部署")
    parser.add_argument("--setup", action="store_true", help="首次部署（上传文件+安装依赖）")
    parser.add_argument("--start", action="store_true", help="启动守护进程")
    parser.add_argument("--stop", action="store_true", help="停止守护进程")
    parser.add_argument("--status", action="store_true", help="查看状态")
    parser.add_argument("--logs", action="store_true", help="查看日志")
    parser.add_argument("--sync", action="store_true", help="增量同步")
    args = parser.parse_args()

    if not any([args.setup, args.start, args.stop, args.status, args.logs, args.sync]):
        parser.print_help()
        sys.exit(1)

    if args.setup:
        cmd_setup()
    if args.start:
        cmd_start()
    if args.stop:
        cmd_stop()
    if args.status:
        cmd_status()
    if args.logs:
        cmd_logs()
    if args.sync:
        cmd_sync()
