#!/bin/bash
# Antigravity CloudStudio E2B 7x24守护进程启动脚本
# 在CloudStudio E2B沙箱终端中粘贴运行

cd ~

# 1. 克隆/同步项目
if [ ! -d ~/antigravity_cloud ]; then
    git clone https://github.com/bbqddt/Antigravity.git ~/antigravity_cloud
fi
cd ~/antigravity_cloud
git pull

# 2. 安装依赖
pip install pandas numpy scipy scikit-learn requests -q 2>/dev/null || \
pip3 install pandas numpy scipy scikit-learn requests -q 2>/dev/null

# 3. 确保数据文件存在
mkdir -p data
if [ ! -f data/lottery_history.csv ]; then
    echo "警告: 缺少数据文件 data/lottery_history.csv"
    echo "请从本地复制 data/lottery_history.csv 到 ~/antigravity_cloud/data/"
fi

# 4. 启动守护进程
echo "============================================"
echo "  Antigravity 7x24守护进程启动"
echo "  $(date)"
echo "============================================"

nohup python3 cloud_orchestrator.py --daemon --interval 5 --tasks 30 --workers 2 \
    >> logs/daemon.log 2>&1 &

echo $! > logs/daemon.pid
echo "守护进程已启动 (PID: $(cat logs/daemon.pid))"
echo "查看日志: tail -f logs/daemon.log"
echo "查看状态: cat logs/daemon.pid && ps aux | grep orchestrator"
