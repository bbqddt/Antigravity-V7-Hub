# cloudflared 快速暴露本地/CVM 服务

## 1. 安装 cloudflared
# Linux/macOS
curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared && chmod +x cloudflared && sudo mv cloudflared /usr/local/bin/
# Windows (PowerShell)
# iwr -useb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe -o cloudflared.exe

## 2. 登录 Cloudflare（仅首次）
cloudflared tunnel login
# 浏览器打开授权页面，选域名/账号

## 3. 创建隧道（仅首次）
cloudflared tunnel create antigravity
# 记录返回的 Tunnel ID

## 4. 配置隧道路由
# 编辑 ~/.cloudflared/config.yml
tunnel: <TUNNEL_ID>
credentials-file: /home/user/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: antigravity.yourdomain.com
    service: http://localhost:8080
  - service: http_status:404

## 5. 路由 DNS（仅需一次）
cloudflared tunnel route dns antigravity antigravity.yourdomain.com

## 6. 运行隧道（前台/后台）
# 前台测试
cloudflared tunnel run antigravity
# 后台常驻（systemd / supervisord / nohup）
nohup cloudflared tunnel run antigravity > cloudflared.log 2>&1 &

## 7. 验证
curl https://antigravity.yourdomain.com/api/health
# 或直接用 trycloudflare 临时域名（无需域名/DNS）
cloudflared tunnel --url http://localhost:8080
# 返回类似 https://xxx.trycloudflare.com

---
# Windows 后台常驻（PowerShell 管理员）
# 1. 安装 cloudflared 为服务
cloudflared service install
# 2. 创建配置文件 C:\Users\<user>\.cloudflared\config.yml
# 3. 启动服务
cloudflared service start