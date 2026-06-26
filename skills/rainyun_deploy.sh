#!/bin/bash
# 🔱 Antigravity Omega - Rainyun 云端一键部署脚本

echo "🚀 [1/5] 正在初始化雨云战场..."
sudo apt update && sudo apt install -y python3-pip git screen

echo "📦 [2/5] 正在拉取 Omega 核心依赖..."
pip3 install streamlit requests beautifulsoup4 qrcode pillow pyyaml openai

echo "📂 [3/5] 正在创建工作区..."
mkdir -p ~/antigravity/lib ~/antigravity/skills
# (此处将由首席顾问通过后续指令同步核心代码)

echo "📡 [4/5] 正在配置端口映射 (8501)..."
# 注意：请确保在雨云后台开启 8501 端口入站规则

echo "🔥 [5/5] 正在后台点火..."
screen -dmS omega streamlit run ~/antigravity/app.py --server.port 8501 --server.address 0.0.0.0

echo "✅ 报告长官：云端观测站已部署完成！"
echo "🔗 请通过: http://您的服务器IP:8501 访问。"
