#!/usr/bin/env bash
# deploy_sandbox.sh —— 一键在沙箱落地 supervisord 全栈
# 用法：在沙箱 Web Terminal / SSH 里直接跑：
#   bash deploy_sandbox.sh

set -euo pipefail

WORKDIR="/workspace"
cd "$WORKDIR"

echo "🚀 沙箱全栈部署开始..."

# 1. 安装 supervisord
echo "▶ 安装 supervisord..."
pip install -q supervisor

# 2. 写入 supervisord.conf（已在本地生成，这里直接用本地文件，若远程需 scp）
if [[ ! -f supervisord.conf ]]; then
    echo "❌ 缺少 supervisord.conf，请先 scp 推送或 git pull"
    exit 1
fi

# 3. 日志目录
mkdir -p logs

# 4. 启动 supervisord
echo "▶ 启动 supervisord..."
supervisord -c supervisord.conf

# 5. 等待进程拉起
sleep 3

# 6. 状态检查
echo "▶ 状态检查..."
supervisorctl -c supervisord.conf status

# 6. 健康检查
echo "▶ 健康检查..."
for port in 8080 9001; do
    if nc -zv -w 3 localhost "$port" 2>/dev/null; then
        echo "✅ localhost:$port 可达"
    else
        echo "❌ localhost:$port 不可达"
    fi
done

echo "🎉 沙箱全栈部署完成！"
echo "查看状态: supervisorctl -c supervisord.conf status"
echo "查看日志: tail -f logs/*.log"
echo "Web UI: http://<沙箱公网IP>:9001 (admin/yourpass)"