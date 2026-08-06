#!/bin/bash
# Antigravity 云端初始化脚本
# ==========================
# 在腾讯云 VM 上运行此脚本，完成项目初始化
#
# 运行方式:
#   1. 将此脚本复制到云端: scp init_cloud.sh admin@YOUR_IP:/tmp/
#   2. 在云端运行: bash /tmp/init_cloud.sh
#
# 或者让 QwenPaw 在终端中执行:
#   wget -qO- https://...  (如果可访问)
#   或直接粘贴脚本内容到终端运行

set -e

echo "============================================================"
echo "  Antigravity 云端初始化 — 腾讯云 CVM"
echo "============================================================"

# ─── 配置 ─────────────────────────────────────────────
PROJECT_DIR="$HOME/antigravity"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo ""
echo "[$DATE] 系统信息:"
echo "  主机: $(hostname)"
echo "  CPU: $(nproc) 核"
echo "  内存: $(free -g | awk '/Mem:/{print $2}')G"
echo "  磁盘: $(df -h / | awk 'NR==2{print $4}') 可用"
echo "  负载: $(cat /proc/loadavg)"

# ─── 1. 创建项目目录 ──────────────────────────────────
echo ""
echo "[$DATE] 1/5 创建项目目录..."
mkdir -p "$PROJECT_DIR"/{data,logs,core,formula_lang,strategy_proposer,llm_innovation,skills,archive}
cd "$PROJECT_DIR"
echo "  ✅ 目录创建: $PROJECT_DIR"

# ─── 2. 安装 Python 依赖 ──────────────────────────────
echo ""
echo "[$DATE] 2/5 安装 Python 环境..."

# 检查 Python3
if ! command -v python3 &>/dev/null; then
    echo "  安装 Python3..."
    apt-get update -qq
    apt-get install -y -qq python3 python3-venv gcc g++ libffi-dev libssl-dev 2>/dev/null
fi

# 创建虚拟环境
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "  创建虚拟环境..."
    python3 -m venv "$PROJECT_DIR/.venv"
fi

# 升级 pip
echo "  升级 pip..."
"$PROJECT_DIR/.venv/bin/pip" install --upgrade pip setuptools wheel -q 2>/dev/null || true

# 安装核心依赖
echo "  安装核心依赖..."
"$PROJECT_DIR/.venv/bin/pip" install \
    pandas numpy scipy scikit-learn \
    beautifulsoup4 requests httpx \
    matplotlib seaborn \
    -q 2>&1 | tail -3 || true

echo "  ✅ Python 环境就绪"
"$PROJECT_DIR/.venv/bin/python" --version

# ─── 3. 安装 sshpass (用于从云端回连本地或下载文件) ───
echo ""
echo "[$DATE] 3/5 安装工具..."
apt-get install -y -qq sshpass wget curl 2>/dev/null || true
echo "  ✅ 工具安装完成"

# ─── 4. 创建云端 Runner 脚本 ──────────────────────────
echo ""
echo "[$DATE] 4/5 创建云端 Runner..."

cat > "$PROJECT_DIR/run.sh" << 'RUNEOF'
#!/bin/bash
# Antigravity 云端 Runner
cd "$(dirname "$0")"
source .venv/bin/activate

echo "[$(date)] 启动 Antigravity 云端 Runner..."
echo "[$(date)] 主机: $(hostname) | CPU: $(nproc)核 | 内存: $(free -g | awk '/Mem:/{print $2}')G"

if [ "$1" = "--daemon" ]; then
    # 守护模式：持续运行
    while true; do
        echo "[$(date)] === 新周期 ==="

        # 数据采集
        python3 data_updater_v2.py 2>&1 || echo "数据采集失败"

        # 预测
        python3 orchestrate.py 2>&1 || echo "预测失败"

        # 非随机性检测（每6小时）
        HOUR=$(date +%H)
        [ $((10#$HOUR % 6)) -eq 0 ] && python3 nonrandomness_detector.py 2>&1 || true

        # 等待30分钟
        echo "[$(date)] 等待30分钟..."
        sleep 1800
    done
else
    # 单轮模式
    python3 data_updater_v2.py 2>&1
    python3 orchestrate.py 2>&1
fi
RUNEOF

chmod +x "$PROJECT_DIR/run.sh"
echo "  ✅ Runner 脚本: $PROJECT_DIR/run.sh"

# ─── 5. 创建 systemd 服务（可选，开机自启）────────────
echo ""
echo "[$DATE] 5/5 创建 systemd 服务..."

cat > /etc/systemd/system/antigravity.service << SVCEOF
[Unit]
Description=Antigravity SSQ Prediction System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/.venv/bin/python $PROJECT_DIR/cloud_runner_v2.py --daemon
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal
Environment="PATH=$PROJECT_DIR/.venv/bin:/usr/bin:/usr/local/bin"

[Install]
WantedBy=multi-user.target
SVCEOF

# 也创建 run.sh 方式的 service（更轻量）
cat > /etc/systemd/system/antigravity-run.service << SVCEOF2
[Unit]
Description=Antigravity SSQ Cloud Runner
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/run.sh
Restart=always
RestartSec=30
StandardOutput=append:$PROJECT_DIR/logs/service.log
StandardError=append:$PROJECT_DIR/logs/service.log

[Install]
WantedBy=multi-user.target
SVCEOF2

echo "  ✅ systemd 服务已创建"
echo "     启用: sudo systemctl enable antigravity-run"
echo "     启动: sudo systemctl start antigravity-run"
echo "     状态: sudo systemctl status antigravity-run"
echo "     日志: journalctl -u antigravity-run -f"

# ─── 完成 ─────────────────────────────────────────────
echo ""
echo "============================================================"
echo "  ✅ 云端初始化完成!"
echo "============================================================"
echo ""
echo "  项目目录: $PROJECT_DIR"
echo ""
echo "  下一步:"
echo "  1. 将项目文件上传到此目录 (SCP)"
echo "  2. 启动守护进程:"
echo "     sudo systemctl start antigravity-run"
echo "  3. 查看状态:"
echo "     sudo systemctl status antigravity-run"
echo "  4. 或直接运行:"
echo "     cd $PROJECT_DIR && bash run.sh  (前台)"
echo "     nohup bash run.sh --daemon &    (后台)"
echo ""
echo "  文件上传命令 (从本地):"
echo "     scp -r E:/享中/* admin@$CLOUD_IP:$PROJECT_DIR/"
echo ""
echo "============================================================"
