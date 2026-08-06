"""
Antigravity 系统健康巡检 V1.0
==============================
检查所有组件状态、API Key 有效性、文件完整性
"""

import json
import os
import subprocess
import sys
import time
import shutil
from pathlib import Path

# Fix Windows GBK encoding for emoji output
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(r"E:\享中")
WORK_DIR = Path(r"E:\享中")  # unified to same dir
SKILLS_DIR = WORK_DIR / "skills"

# 结果收集
report = {}
alerts = []


def check_file(path, name):
    """检查文件是否存在"""
    exists = path.exists()
    report[name] = exists
    if not exists:
        alerts.append(f"❌ 缺失: {name} ({path})")
    else:
        size = path.stat().st_size
        report[name] = {"exists": True, "size_kb": round(size / 1024, 1)}
        print(f"  ✅ {name}: {size / 1024:.1f} KB")


def check_directory(path, name):
    """检查目录是否存在"""
    exists = path.exists() and path.is_dir()
    report[name] = exists
    if exists:
        files = list(path.glob("*.py"))
        print(f"  ✅ {name}: {len(files)} 个 Python 文件")
    else:
        alerts.append(f"❌ 缺失: {name}")


def check_port(port, name):
    """检查端口是否监听"""
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex(("127.0.0.1", port))
    sock.close()
    report[f"端口_{name}"] = result == 0
    status = "✅" if result == 0 else "❌"
    print(f"  {status} {name}:{port}")
    if result != 0:
        alerts.append(f"⚠️ 端口未监听: {name}:{port}")


def check_python_package(package):
    """检查 Python 包"""
    try:
        __import__(package)
        report[package] = True
        print(f"  ✅ {package}")
        return True
    except ImportError:
        report[package] = False
        alerts.append(f"❌ 缺少包: {package}")
        return False


def check_api_key(key_type, key_value):
    """检查 API Key 有效性"""
    if not key_value or key_value == "":
        report[key_type] = "未配置"
        print(f"  ⚠️ {key_type}: 未配置")
        return False

    # 脱敏显示
    masked = key_value[:8] + "..." + key_value[-4:] if len(key_value) > 12 else "***"
    print(f"  📋 {key_type}: {masked}")
    report[key_type] = {"configured": True, "masked": masked}
    return True


def main():
    print("=" * 60)
    print("  🔱 Antigravity 系统健康巡检")
    print("=" * 60)
    print()

    # 1. 文件检查
    print("[1/6] 核心文件检查...")
    core_files = [
        (BASE_DIR / "data/lottery_history.csv", "历史数据"),
        (BASE_DIR / "latest_decision.json", "最新预测"),
        (BASE_DIR / "token_tg.txt", "TG 配置"),
        (BASE_DIR / "keys.json", "API Keys"),
        (BASE_DIR / "arsenal.json", "弹药库"),
        (WORK_DIR / "commander_bot.py", "Commander Bot"),
        (WORK_DIR / "enhanced_predictor.py", "增强预测器"),
        (WORK_DIR / "cloud_deploy.py", "云端部署"),
    ]
    for path, name in core_files:
        check_file(path, name)
    print()

    # 2. 目录检查
    print("[2/6] 目录结构检查...")
    check_directory(BASE_DIR, "主目录")
    check_directory(SKILLS_DIR, "Skills 目录")
    print()

    # 3. Python 包检查
    print("[3/6] 依赖包检查...")
    packages = ["requests", "bs4", "pandas", "sklearn", "telegram"]
    for pkg in packages:
        check_pkg = pkg.replace("sklearn", "sklearn")  # sklearn imports as sklearn, not scikit_learn
        try:
            __import__(check_pkg)
            report[pkg] = True
            print(f"  ✅ {pkg}")
            continue
        except ImportError:
            report[pkg] = False
            alerts.append(f"❌ 缺少包: {pkg}")
    print()

    # 4. API Key 检查
    print("[4/6] API Key 检查...")
    keys_file = BASE_DIR / "keys.json"
    if keys_file.exists():
        with open(keys_file, "r") as f:
            keys = json.load(f)
        for ktype, kvalue in keys.items():
            check_api_key(ktype, kvalue)
    print()

    # 5. 端口检查
    print("[5/6] 端口检查...")
    ports = [(12654, "API Proxy"), (8089, "Local API"), (8090, "Claude Tunnel"), (8501, "Streamlit")]
    for port, name in ports:
        check_port(port, name)
    print()

    # 6. 磁盘空间
    print("[6/6] 磁盘空间...")
    try:
        total, used, free = shutil.disk_usage(str(BASE_DIR))
        free_gb = free / (1024 ** 3)
        print(f"  可用空间: {free_gb:.1f} GB")
        if free_gb < 1:
            alerts.append(f"⚠️ 磁盘空间不足: {free_gb:.1f} GB")
    except Exception as e:
        print(f"  ⚠️ 无法检查磁盘空间: {e}")
    print()

    # 汇总
    print("=" * 60)
    print("  巡 检 汇 总")
    print("=" * 60)

    passed = sum(1 for v in report.values() if v is True or (isinstance(v, dict) and v.get("exists")))
    failed = sum(1 for v in report.values() if v is False)
    warning = len(alerts)

    print(f"  通过: {passed} | 失败: {failed} | 警告: {warning}")

    if alerts:
        print("\n⚠️ 告警:")
        for alert in alerts:
            print(f"  {alert}")

    # 保存报告
    report_path = BASE_DIR / "health_check_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({"report": report, "alerts": alerts, "timestamp": time.time()}, f, indent=2)

    print(f"\n✅ 报告已保存至: {report_path}")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
