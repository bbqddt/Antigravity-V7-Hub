#!/usr/bin/env bash
# install_docker.sh —— 一键安装 Docker + 启用开机自启（Linux）
# 用法：curl -fsSL https://get.docker.com | sh && sudo systemctl enable --now docker
# 或在 Windows/Mac 上安装 Docker Desktop 并勾选 "Start Docker Desktop when you log in"

set -euo pipefail

echo "🐳 安装 Docker Engine..."

# 1. 安装 Docker Engine（Linux）
if command -v apt-get >/dev/null 2>&1; then
    # Ubuntu/Debian
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl gnupg lsb-release
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/$(. /etc/os-release && echo "$ID")/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$(. /etc/os-release && echo "$ID") $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
elif command -v yum >/dev/null 2>&1; then
    # CentOS/RHEL/Fedora
    sudo yum install -y yum-utils
    sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
elif command -v dnf >/dev/null 2>&1; then
    # Fedora
    sudo dnf -y install dnf-plugins-core
    sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
    sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
else
    echo "❌ 不支持的发行版，请手动安装 Docker"
    exit 1
fi

# 2. 启用并启动 Docker 服务（开机自启）
sudo systemctl enable --now docker

# 3. 将当前用户加入 docker 组（免 sudo）
sudo usermod -aG docker "$USER"

# 4. 验证
docker version
docker compose version

echo "✅ Docker 安装完成，已设置开机自启"
echo "⚠️ 请重新登录或重启机器使 docker 组生效"
echo "👉 部署项目: docker compose up -d"