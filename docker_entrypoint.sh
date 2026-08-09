#!/bin/bash
set -e

# 初始化数据目录
mkdir -p /app/data /app/logs

# 启动监控面板 (后台)
cd /app
python monitor_dashboard.py &
MONITOR_PID=$!

# 启动演化守护进程 (前台，作为容器主进程)
exec python cloud_daemon_24x7.py