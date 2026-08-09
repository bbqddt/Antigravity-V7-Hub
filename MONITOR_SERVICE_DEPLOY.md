# Antigravity 云端监控面板 systemd 服务部署指南

## 文件清单
- `antigravity-monitor.service` - systemd 服务单元文件
- `deploy_monitor_service.sh` - 一键部署脚本

## 云端部署步骤（服务器恢复后执行）

```bash
# 1. 登录云端
ssh admin@10.139.54.143

# 2. 进入项目目录
cd /home/admin/antigravity

# 3. 确保两个文件已同步上传（通过 cloud_quick_deploy.py --sync 或 scp）
# 如果未同步，先从本地上传：
# scp antigravity-monitor.service deploy_monitor_service.sh admin@10.139.54.143:/home/admin/antigravity/

# 4. 赋予执行权限并运行
chmod +x deploy_monitor_service.sh
bash deploy_monitor_service.sh
```

## 服务配置详情
- **服务名**：`antigravity-monitor`
- **运行用户**：`admin`
- **工作目录**：`/home/admin/antigravity`
- **启动命令**：`/home/admin/antigravity/.venv/bin/python monitor_dashboard.py`
- **端口**：`8080` (0.0.0.0)
- **自动重启**：`Restart=always`, `RestartSec=10`
- **日志**：`journalctl -u antigravity-monitor -f`

## 验证命令
```bash
# 检查服务状态
systemctl status antigravity-monitor

# 查看实时日志
journalctl -u antigravity-monitor -f

# 测试 HTTP 端点
curl http://localhost:8080/api/status
curl http://localhost:8080/

# 停止/重启/禁用服务
systemctl stop antigravity-monitor
systemctl restart antigravity-monitor
systemctl disable antigravity-monitor
```

## 故障排查
1. **服务启动失败**：检查 `journalctl -u antigravity-monitor -n 50`
2. **端口被占用**：`ss -tlnp | grep 8080` 或 `lsof -i :8080`
3. **虚拟环境路径错误**：确认 `/home/admin/antigravity/.venv/bin/python` 存在
4. **依赖缺失**：在虚拟环境中 `pip install fastapi uvicorn[standard] jinja2`

## 下一步建议
- 配置 Nginx 反向代理 + HTTPS（可选）
- 添加 Prometheus metrics 导出端点（`/metrics`）
- 集成到云端部署脚本 `cloud_quick_deploy.py` 中自动部署