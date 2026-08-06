#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Antigravity 云端信息收集脚本
============================
在腾讯云 VM 上运行此脚本，收集系统信息和网络配置。

将此文件发送给 QwenPaw，让它在云端运行:
  python cloud_info.py
"""
import socket
import subprocess
import json
from pathlib import Path
from datetime import datetime

def run(cmd):
    """执行命令并返回输出"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout.strip()
    except Exception as e:
        return str(e)

def main():
    info = {
        "collected_at": datetime.now().isoformat(),
        "hostname": run("hostname"),
        "os": run("cat /etc/os-release | grep PRETTY_NAME"),
        "kernel": run("uname -r"),
        "cpu": {
            "model": run("lscpu | grep 'Model name'"),
            "cores": run("nproc"),
            "threads": run("lscpu | grep '^Thread(s) per core:'"),
        },
        "memory": {
            "total_gb": run("free -g | awk '/Mem:/{print $2}'"),
            "available_gb": run("free -g | awk '/Mem:/{print $7}'"),
        },
        "disk": {
            "total_gb": run("df -h / | awk 'NR==2{print $2}'"),
            "used_gb": run("df -h / | awk 'NR==2{print $3}'"),
            "avail_gb": run("df -h / | awk 'NR==2{print $4}'"),
        },
        "network": {
            "interfaces": run("ip addr show 2>/dev/null || ifconfig 2>/dev/null || echo 'no network tools'"),
            "internal_ip": run("hostname -I 2>/dev/null || echo 'unknown'"),
            "public_ip": run("curl -s ifconfig.me 2>/dev/null || echo 'unknown'"),
            "dns": run("cat /etc/resolv.conf 2>/dev/null || echo 'unknown'"),
        },
        "python": {
            "version": run("python3 --version 2>&1"),
            "path": run("which python3"),
            "pip_packages": run("pip3 list 2>/dev/null | head -30"),
        },
        "processes": {
            "python_procs": run("ps aux | grep python | grep -v grep || echo 'none'"),
        },
        "uptime": run("uptime"),
        "load_avg": run("cat /proc/loadavg"),
    }

    print("=" * 60)
    print("  腾讯云 CVM 系统信息")
    print("=" * 60)
    print()

    for key, val in info.items():
        if isinstance(val, dict):
            print(f"📌 {key}:")
            for k, v in val.items():
                print(f"   {k}: {v}")
        else:
            display = val[:200] if len(str(val)) > 200 else val
            print(f"📌 {key}: {display}")
        print()

    # 保存为 JSON
    output_file = Path("cloud_info.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)
    print(f"📄 详细信息已保存到: {output_file}")


if __name__ == "__main__":
    main()
