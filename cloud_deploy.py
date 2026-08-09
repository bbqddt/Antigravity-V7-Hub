#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Antigravity 云端部署脚本 — 将项目部署到腾讯云 CVM
=================================================
本地运行此脚本，自动 SSH 连接到腾讯云并部署整个项目。

用法:
    python cloud_deploy.py --deploy          # 完整部署
    python cloud_deploy.py --sync-data       # 只同步数据文件
    python cloud_deploy.py --status          # 检查云端状态
    python cloud_deploy.py --logs            # 查看云端日志
    python cloud_deploy.py --stop            # 停止云端进程
    python cloud_deploy.py --restart         # 重启云端进程
"""
import subprocess
import sys
import os
import json
import time
import tarfile
from pathlib import Path
from datetime import datetime

# ─── 配置 ─────────────────────────────────────────────
CLOUD_HOST = "10.139.54.143"  # 腾讯云内网IP（或公网IP）
CLOUD_USER = "admin"
CLOUD_PASS = "5YK9LaJ6KOwFKmLLkPuO"
CLOUD_PORT = 22

PROJECT_ROOT = Path(__file__).resolve().parent
REMOTE_BASE = Path("/home/admin/antigravity")
REMOTE_VENV = REMOTE_BASE / ".venv"
REMOTE_DATA = REMOTE_BASE / "data"
REMOTE_LOGS = REMOTE_BASE / "logs"

# 需要排除的文件/目录
EXCLUDES = [
    ".venv", "__pycache__", "*.pyc", "*.pyo",
    "node_modules", ".git", "*.log",
    "archive", "models", "dist",
    "*.exe", "*.vbs", "*.bat", "*.ps1",
    ".env", "keys.json",
]


def ssh_cmd(cmd: str) -> subprocess.CompletedProcess:
    """通过 sshpass 执行远程命令"""
    full_cmd = (
        f'sshpass -p "{CLOUD_PASS}" ssh -o StrictHostKeyChecking=no '
        f'-p {CLOUD_PORT} {CLOUD_USER}@{CLOUD_HOST} "{cmd}"'
    )
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=60)
    return result


def run_local(cmd: str, **kwargs) -> subprocess.CompletedProcess:
    """在本地执行命令"""
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kwargs)


def check_cloud_connectivity() -> bool:
    """检查能否连接到云端"""
    result = ssh_cmd("echo 'connected' && hostname && uname -a")
    if result.returncode == 0 and "connected" in result.stdout:
        print(f"✅ 云端连接成功!")
        print(f"   主机名: {result.stdout.strip()}")
        return True
    else:
        print(f"❌ 无法连接到云端 ({CLOUD_HOST})")
        print(f"   错误: {result.stderr}")
        print(f"   提示: 请确认云端的 IP 地址、用户名和密码是否正确")
        return False


def create_tarball() -> Path:
    """将项目打包为 tar.gz（排除不需要传输的文件）"""
    archive_path = PROJECT_ROOT / "antigravity_deploy.tar.gz"
    print(f"📦 正在打包项目... ({archive_path})")

    def exclude_filter(tarinfo):
        name = tarinfo.name
        for exc in EXCLUDES:
            if exc.startswith("*"):
                if name.endswith(exc[1:]):
                    return None
            elif exc in name:
                return None
        return tarinfo

    with tarfile.open(archive_path, "w:gz") as tar:
        for item in PROJECT_ROOT.iterdir():
            if item.name == "antigravity_deploy.tar.gz":
                continue
            arcname = item.name
            if item.is_dir():
                tar.add(item, arcname=arcname, filter=exclude_filter)
            else:
                tar.add(item, arcname=arcname)

    size_mb = archive_path.stat().st_size / (1024 * 1024)
    print(f"✅ 打包完成: {size_mb:.1f} MB")
    return archive_path


def upload_file(local_path: Path):
    """上传文件到云端"""
    remote_dest = f"{CLOUD_USER}@{CLOUD_HOST}:{REMOTE_BASE}/{local_path.name}"
    cmd = f'scp -P {CLOUD_PORT} -o StrictHostKeyChecking=no "{local_path}" {remote_dest}'
    print(f"📤 上传: {local_path.name} ({local_path.stat().st_size / 1024 / 1024:.1f} MB)")
    result = run_local(cmd, timeout=300)
    if result.returncode != 0:
        print(f"   ❌ 上传失败: {result.stderr}")
    else:
        print(f"   ✅ 上传成功")


def deploy_venv():
    """在云端创建 Python 虚拟环境并安装依赖"""
    print("\n🐍 在云端创建 Python 虚拟环境...")

    # 安装系统依赖
    cmds = [
        "apt-get update -qq",
        "apt-get install -y -qq python3 python3-pip python3-venv gcc g++ libffi-dev libssl-dev 2>/dev/null",
        f"python3 -m venv {REMOTE_VENV}",
        f"source {REMOTE_VENV}/bin/activate && pip install --upgrade pip setuptools wheel -q",
    ]

    for cmd in cmds:
        result = ssh_cmd(cmd)
        if result.returncode != 0:
            print(f"   ⚠️ 警告: {result.stderr[:200]}")
        else:
            print(f"   ✅ {cmd[:60]}")

    # 安装 Python 依赖
    deps = [
        "pandas", "numpy", "scipy", "scikit-learn",
        "torch", "matplotlib", "seaborn",
        "beautifulsoup4", "requests", "httpx",
        "python-telegram-bot", "streamlit",
    ]
    print(f"\n📦 安装 Python 依赖 ({len(deps)} 个包)...")
    pip_cmd = f"source {REMOTE_VENV}/bin/activate && pip install {' '.join(deps)} 2>&1 | tail -5"
    result = ssh_cmd(pip_cmd)
    if result.returncode == 0:
        print(f"   ✅ 依赖安装完成")
    else:
        print(f"   ⚠️ 部分依赖安装可能有问题: {result.stderr[:200]}")


def setup_remote_structure():
    """在云端创建项目目录结构"""
    print("\n📁 创建云端目录结构...")
    dirs = [str(REMOTE_BASE), str(REMOTE_DATA), str(REMOTE_LOGS),
            str(REMOTE_BASE / "core"), str(REMOTE_BASE / "formula_lang"),
            str(REMOTE_BASE / "strategy_proposer"), str(REMOTE_BASE / "llm_innovation"),
            str(REMOTE_BASE / "skills"), str(REMOTE_BASE / "archive")]
    for d in dirs:
        ssh_cmd(f"mkdir -p {d}")
    print("   ✅ 目录结构创建完成")


def sync_data():
    """同步数据文件到云端"""
    print("\n📊 同步数据文件...")
    data_files = list((PROJECT_ROOT / "data").glob("*.csv"))
    for f in data_files:
        remote_dest = f"{CLOUD_USER}@{CLOUD_HOST}:{REMOTE_DATA}/{f.name}"
        cmd = f'scp -P {CLOUD_PORT} -o StrictHostKeyChecking=no "{f}" {remote_dest}'
        run_local(cmd)
        print(f"   ✅ {f.name}")

    # 同步其他关键 JSON 文件
    json_files = [
        "analysis_prior.json", "attribute_frequencies.json",
        "position_prior.json", "number_profiles.json",
        "learning_state.json", "enhanced_state.json",
        "evolution_state.json", "evolution_state_v2.json",
        "best_formula.json", "formula_candidates.json",
        "evolved_formulas.json", "evolved_formulas_v2.json",
        "signal_fusion.py",
    ]
    for jf in json_files:
        local = PROJECT_ROOT / jf
        if local.exists():
            remote_dest = f"{CLOUD_USER}@{CLOUD_HOST}:{REMOTE_BASE}/{jf}"
            cmd = f'scp -P {CLOUD_PORT} -o StrictHostKeyChecking=no "{local}" {remote_dest}'
            run_local(cmd)
            print(f"   ✅ {jf}")


def deploy_cloud_runner():
    """部署云端 Runner 脚本"""
    print("\n🚀 部署云端 Runner...")

    runner_script = f'''#!/bin/bash
# Antigravity Cloud Runner — 云端持续演算守护进程
# 部署于腾讯云 CVM (32核/123GB)

PROJECT_DIR="{REMOTE_BASE}"
VENV="{REMOTE_VENV}/bin/activate"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/cloud_runner_daemon.log"
PID_FILE="$LOG_DIR/cloud_runner.pid"

mkdir -p "$LOG_DIR"

cleanup() {{
    echo "[$(date)] 停止云端演算..."
    if [ -f "$PID_FILE" ]; then
        kill $(cat "$PID_FILE") 2>/dev/null
        rm -f "$PID_FILE"
    fi
}}

trap cleanup EXIT INT TERM

# 激活虚拟环境
source "$VENV"

# 进入项目目录
cd "$PROJECT_DIR"

echo "[$(date)] 云端演算守护进程启动 (PID: $$)"
echo "[$(date)] 主机: $(hostname)"
echo "[$(date)] CPU: $(nproc) 核"
echo "[$(date)] 内存: $(free -g | awk '{{print $2}}'G)"

# 持续运行：每30分钟一轮
while true; do
    echo "[$(date)] === 开始新一轮演算 ==="

    # 1. 数据采集
    python3 data_updater_v2.py 2>&1 | tee -a "$LOG_FILE"

    # 2. 预测引擎
    python3 orchestrate.py 2>&1 | tee -a "$LOG_FILE"

    # 3. 非随机性检测（每6小时一次）
    HOUR=$(date +%H)
    if [ "$HOUR" = "00" ] || [ "$HOUR" = "06" ] || [ "$HOUR" = "12" ] || [ "$HOUR" = "18" ]; then
        echo "[$(date)] 运行非随机性检测..."
        python3 nonrandomness_detector.py 2>&1 | tee -a "$LOG_FILE"
    fi

    # 4. 滚动回测（每天一次）
    DAY=$(date +%u)  # 1=Monday
    if [ "$DAY" = "7" ]; then  # Sunday
        echo "[$(date)] 运行滚动回测..."
        python3 walkforward_backtest_v2.py 2>&1 | tee -a "$LOG_FILE"
    fi

    echo "[$(date)] === 本轮演算完成 ==="
    echo "[$(date)] 等待30分钟..."
    sleep 1800
done
'''

    runner_path = REMOTE_BASE / "cloud_runner_daemon.sh"
    # 写入云端
    ssh_cmd(f"cat > {runner_path} << 'RUNNER_EOF'\n{runner_script}\nRUNNER_EOF")
    ssh_cmd(f"chmod +x {runner_path}")
    print(f"   ✅ 守护脚本已部署: {runner_path}")


def start_cloud_daemon():
    """在云端启动守护进程"""
    print("\n▶️  启动云端守护进程...")

    # 先杀掉旧的
    ssh_cmd("pkill -f 'cloud_runner_daemon.sh' 2>/dev/null || true")
    ssh_cmd(f"rm -f {REMOTE_BASE}/logs/cloud_runner.pid")

    # 用 nohup 启动
    ssh_cmd(
        f"nohup bash {REMOTE_BASE}/cloud_runner_daemon.sh "
        f"> {REMOTE_BASE}/logs/cloud_runner_stdout.log 2>&1 & "
        f"echo $! > {REMOTE_BASE}/logs/cloud_runner.pid"
    )

    time.sleep(3)

    # 检查进程
    result = ssh_cmd("ps aux | grep cloud_runner | grep -v grep")
    if result.returncode == 0 and result.stdout.strip():
        print("   ✅ 云端守护进程已启动!")
        print(f"   进程信息:\n{result.stdout}")
    else:
        print("   ⚠️ 守护进程可能未正常启动，请检查日志")


def cmd_deploy():
    """完整部署流程"""
    print("=" * 60)
    print("  Antigravity 云端部署工具 V1.0")
    print("  目标: 腾讯云 CVM (32核/123GB/Ubuntu 26.04)")
    print("=" * 60)

    # 1. 检查连通性
    if not check_cloud_connectivity():
        sys.exit(1)

    # 2. 创建目录结构
    setup_remote_structure()

    # 3. 打包项目
    archive = create_tarball()

    # 4. 上传到云端
    print(f"\n📤 上传项目到云端...")
    upload_file(archive)

    # 5. 在云端解压
    print(f"\n📂 在云端解压项目...")
    ssh_cmd(f"cd {REMOTE_BASE.parent} && tar xzf {archive.name}")
    print("   ✅ 解压完成")

    # 6. 删除压缩包
    ssh_cmd(f"rm -f {REMOTE_BASE.parent}/{archive.name}")

    # 7. 同步数据文件
    sync_data()

    # 8. 部署云端 Runner
    deploy_cloud_runner()

    # 9. 启动守护进程
    start_cloud_daemon()

    print("\n" + "=" * 60)
    print("  ✅ 部署完成!")
    print(f"  📍 云端项目: {REMOTE_BASE}")
    print(f"  📋 查看日志: python cloud_deploy.py --logs")
    print(f"  📊 检查状态: python cloud_deploy.py --status")
    print(f"  🛑 停止服务: python cloud_deploy.py --stop")
    print("=" * 60)


def cmd_status():
    """检查云端状态"""
    print("🔍 检查云端状态...")
    print()

    # 基本信息
    result = ssh_cmd("uname -a && hostname")
    if result.returncode == 0:
        print(f"📡 主机信息:\n{result.stdout}")

    # 进程
    result = ssh_cmd("ps aux | grep -E '(python|cloud_runner)' | grep -v grep")
    if result.returncode == 0 and result.stdout.strip():
        print(f"\n🔄 运行中的进程:\n{result.stdout}")
    else:
        print("\n❌ 没有运行中的 Antigravity 进程")

    # 磁盘
    result = ssh_cmd("df -h / && free -h")
    if result.returncode == 0:
        print(f"\n💾 磁盘和内存:\n{result.stdout}")

    # 最新日志
    result = ssh_cmd(f"tail -20 {REMOTE_BASE}/logs/cloud_runner.log 2>/dev/null || echo 'No log file found'")
    if result.returncode == 0:
        print(f"\n📋 最新日志:\n{result.stdout}")

    # 预测结果
    result = ssh_cmd(f"cat {REMOTE_BASE}/latest_prediction.json 2>/dev/null | python3 -m json.tool 2>/dev/null | head -20 || echo 'No prediction file'")
    if result.returncode == 0:
        print(f"\n🎯 最新预测:\n{result.stdout}")


def cmd_logs():
    """查看云端日志"""
    result = ssh_cmd(f"tail -50 {REMOTE_BASE}/logs/cloud_runner.log 2>/dev/null || echo 'No log file'")
    print(result.stdout)


def cmd_stop():
    """停止云端进程"""
    ssh_cmd("pkill -f 'cloud_runner_daemon.sh' 2>/dev/null && echo 'Stopped' || echo 'Not running'")
    ssh_cmd(f"rm -f {REMOTE_BASE}/logs/cloud_runner.pid")
    print("✅ 云端进程已停止")


def cmd_restart():
    """重启云端进程"""
    cmd_stop()
    time.sleep(2)
    start_cloud_daemon()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Antigravity 云端部署工具")
    parser.add_argument("--deploy", action="store_true", help="完整部署")
    parser.add_argument("--status", action="store_true", help="检查云端状态")
    parser.add_argument("--logs", action="store_true", help="查看云端日志")
    parser.add_argument("--stop", action="store_true", help="停止云端进程")
    parser.add_argument("--restart", action="store_true", help="重启云端进程")
    parser.add_argument("--host", default=CLOUD_HOST, help="云端主机地址")
    parser.add_argument("--user", default=CLOUD_USER, help="云端用户名")
    parser.add_argument("--pass", default=CLOUD_PASS, help="云端密码")
    parser.add_argument("--port", type=int, default=CLOUD_PORT, help="SSH端口")

    args = parser.parse_args()

    # 覆盖配置
    if args.host:
        global CLOUD_HOST
        CLOUD_HOST = args.host
    if args.user:
        CLOUD_USER = args.user
    if args.pass_:
        CLOUD_PASS = args.pass_
    CLOUD_PORT = args.port

    if args.deploy:
        cmd_deploy()
    elif args.status:
        cmd_status()
    elif args.logs:
        cmd_logs()
    elif args.stop:
        cmd_stop()
    elif args.restart:
        cmd_restart()
    else:
        parser.print_help()
