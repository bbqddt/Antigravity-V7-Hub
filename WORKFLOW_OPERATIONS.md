# Antigravity 系统运维工作流手册

> **版本**: 2026-08-08 v1.0  
> **适用环境**: 腾讯云 CVM (32核/123GB/Ubuntu 26.04) + 本地开发环境  
> **核心目标**: 7×24 小时自动化公式演化、研究、预测、监控全链路无人值守运行

---

## 1. 系统架构全景

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Antigravity 7×24 自动化系统                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │  数据层       │    │  演化层       │    │  预测层               │  │
│  │ data_layer.py│◄───│ formula_ev.. │    │ orchestrate.py       │  │
│  │ data_upd..v2 │    │ cloud_dae..  │    │ luckcast_v15         │  │
│  │ physical_sig │    │ research_dae │    │ enhanced_pred..      │  │
│  └──────┬───────┘    └──────┬───────┘    └──────────┬───────────┘  │
│         │                   │                        │              │
│         ▼                   ▼                        ▼              │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    监控与告警层 (monitor_dashboard.py:8080)     │  │
│  │  Metrics JSONL │ Health Logs │ Alerts │ WebSocket 实时推送      │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                   │                        │              │
│         ▼                   ▼                        ▼              │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    部署与运维层                                 │  │
│  │  cloud_quick_deploy.py │ deploy_all.py │ systemd 服务管理       │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 核心组件清单

| 组件 | 文件 | 角色 | 运行模式 | 关键依赖 |
|------|------|------|----------|----------|
| **数据采集** | `data_updater_v2.py` | 从 500.com 增量更新历史数据 | 定时/手动 | requests, bs4 |
| **数据层** | `data_layer.py` | 统一数据访问入口，多格式兼容 | 库调用 | pandas |
| **非随机性检测** | `nonrandomness_detector.py` | Hurst/游程/熵/频谱分析 | 编排调用 | numpy, scipy |
| **公式演化** | `formula_evolution.py` | 遗传算法优化预测公式 | 守护进程/手动 | 核心依赖 |
| **云端守护进程** | `cloud_daemon_24x7.py` | 7×24 演化调度、备份、健康检查 | systemd 服务 | 所有核心模块 |
| **研究守护进程** | `research_daemon_24x7.py` | 7×24 LLM 深度研究、建议应用 | systemd 服务 | llm_formula_loop |
| **统一编排** | `orchestrate.py` | 数据→检测→多引擎预测→融合 | 定时/手动 | 所有预测引擎 |
| **Luckcast V15** | `luckcast_antigravity_v1.py` | 学习型多维预测引擎 | 编排调用 | numpy |
| **Enhanced V2.0** | `enhanced_predictor.py` | 多策略加权集成预测 | 编排调用 | numpy, causal |
| **监控面板** | `monitor_dashboard.py` | FastAPI+Chart.js 实时监控 | systemd 服务 | fastapi, uvicorn |
| **云端部署** | `cloud_quick_deploy.py` | SSH/SFTP 一键部署、同步、管理 | 本地 CLI | paramiko |
| **统一部署** | `deploy_all.py` | 多平台部署统一入口 | 本地 CLI | 所有部署脚本 |

---

## 2. 标准化部署工作流

### 2.1 首次全量部署（云端裸机）

```bash
# 本地执行
cd /path/to/antigravity
python deploy_all.py --cloud --cloud-action deploy --token-file tokens.json
```

**自动执行步骤**：
1. ✅ SSH 连通性测试
2. ✅ 远程目录结构创建 (`/home/admin/antigravity/{data,logs,core,formula_lang,...}`)
3. ✅ 项目打包上传 (排除 .venv, __pycache__, .git, archive, models 等)
4. ✅ 远程 Python 虚拟环境创建 + 依赖安装 (pandas, numpy, scipy, sklearn, torch, fastapi, uvicorn, jinja2 等)
5. ✅ 数据文件同步 (CSV + 关键 JSON 状态文件)
6. ✅ **监控面板 systemd 服务注册** (`antigravity-monitor.service` → `/etc/systemd/system/`)
7. ✅ 云端守护进程启动 (`cloud_daemon_24x7.py` nohup 后台)
8. ✅ 研究守护进程启动 (`research_daemon_24x7.py` nohup 后台)
9. ✅ 监控面板服务启动 (`systemctl enable --now antigravity-monitor`)

### 2.2 增量同步部署（代码更新后）

```bash
# 仅同步代码变更
python cloud_quick_deploy.py --sync

# 或统一入口
python deploy_all.py --cloud --cloud-action sync
```

### 2.3 监控面板单独部署/重启

```bash
python cloud_quick_deploy.py --deploy-monitor
# 或
python deploy_all.py --cloud --cloud-action deploy-monitor
```

### 2.4 守护进程管理

```bash
# 状态查看
python cloud_quick_deploy.py --status

# 启动/停止/重启
python cloud_quick_deploy.py --start
python cloud_quick_deploy.py --stop
# 重启 = stop + start

# 查看日志
python cloud_quick_deploy.py --logs
```

---

## 3. 运维操作规范 (SOP)

### 3.1 systemd 服务管理

| 服务名 | 对应进程 | 端口 | 关键命令 |
|--------|----------|------|----------|
| `antigravity-monitor` | `monitor_dashboard.py` | 8080 | `systemctl status/restart/stop/start antigravity-monitor` |
| `antigravity-cloud-daemon` | `cloud_daemon_24x7.py` | — | 需创建服务文件 (见附录) |
| `antigravity-research-daemon` | `research_daemon_24x7.py` | — | 需创建服务文件 (见附录) |

**通用排查命令**：
```bash
# 查看服务状态
systemctl status antigravity-monitor --no-pager

# 实时日志
journalctl -u antigravity-monitor -f

# 最近 100 行
journalctl -u antigravity-monitor -n 100 --no-pager

# 启用开机自启
systemctl enable antigravity-monitor

# 禁用开机自启
systemctl disable antigravity-monitor
```

### 3.2 手动运行核心流程（调试/补跑）

```bash
# 1. 数据更新
python data_updater_v2.py

# 2. 非随机性检测
python nonrandomness_detector.py

# 3. 公式演化 (单轮)
python formula_evolution.py --run --generations 20 --population 30

# 4. 完整编排预测
python orchestrate.py --top-k 5

# 5. 单引擎预测
python luckcast_antigravity_v1.py
python enhanced_predictor.py --train

# 6. 监控面板前台运行 (调试)
python monitor_dashboard.py
```

### 3.3 数据备份与恢复

```bash
# 云端自动备份 (守护进程每 12 小时执行)
# 位置: /home/admin/antigravity/backups/YYYYMMDD_HHMMSS/

# 手动触发备份
ssh admin@10.139.54.143 "cd /home/admin/antigravity && python -c '
from cloud_daemon_24x7 import CloudDaemon
d = CloudDaemon()
d.backup_results()
'"

# 本地备份关键文件
tar -czf antigravity_backup_$(date +%Y%m%d).tar.gz \
  data/lottery_history.csv \
  *.json \
  logs/metrics_*.jsonl \
  logs/health_24x7.log
```

---

## 4. 每日开机必做工作清单 (Daily Startup Checklist)

> **执行时间**: 云端服务器重启后 / 每日首次登录时  
> **执行角色**: 运维工程师 / 自动化脚本  
> **预计耗时**: 3-5 分钟

### 4.1 服务健康检查 (必做)

| # | 检查项 | 命令 | 通过标准 | 异常处理 |
|---|--------|------|----------|----------|
| 1 | 监控面板服务 | `systemctl is-active antigravity-monitor` | `active` | `systemctl restart antigravity-monitor` |
| 2 | 监控面板 HTTP | `curl -sf http://localhost:8080/api/status` | 返回 JSON, `cloud_daemon: "running"` | 查看 `journalctl -u antigravity-monitor -n 50` |
| 3 | 云端守护进程 | `ps aux \| grep cloud_daemon_24x7 \| grep -v grep` | 1 个进程 | `python cloud_quick_deploy.py --start` |
| 4 | 研究守护进程 | `ps aux \| grep research_daemon_24x7 \| grep -v grep` | 1 个进程 | 手动启动 research_daemon |
| 5 | 磁盘空间 | `df -h /` | 可用 > 10 GB | 清理旧备份/日志 |
| 6 | 内存使用 | `free -h` | 可用 > 20 GB | 检查内存泄漏进程 |
| 7 | 数据文件存在 | `ls -la /home/admin/antigravity/data/lottery_history.csv` | 文件存在且 > 100KB | 运行 `python data_updater_v2.py` |
| 8 | 最新预测文件 | `cat /home/admin/antigravity/latest_prediction.json \| jq .target_period` | 目标期号 = 最新期号+1 | 运行 `python orchestrate.py` |

### 4.2 关键指标评测 (必做)

| 指标 | 获取方式 | 正常范围 | 告警阈值 | 记录位置 |
|------|----------|----------|----------|----------|
| **最佳评分** | `curl -s localhost:8080/api/status \| jq .last_score` | > 0.45 | < 0.35 | 监控面板 + 日志 |
| **完成轮数** | `curl -s localhost:8080/api/status \| jq .last_cycle` | 递增 | 24h 无增长 | 监控面板 |
| **运行时长** | `curl -s localhost:8080/api/status \| jq .uptime_hours` | 递增 | — | 监控面板 |
| **磁盘剩余** | `df -h / \| awk 'NR==2{print $4}'` | > 10 GB | < 5 GB | 监控面板告警 |
| **连续失败数** | 守护进程日志 | 0 | ≥ 3 | `cloud_daemon_*.log` |
| **beats_random** | `metrics_YYYYMMDD.jsonl` 最后一行 | true 偶尔出现 | 连续 7 天 false | 监控面板图表 |
| **预测命中率** | 回测脚本 / 人工核对 | 基线 1.09 | 连续 3 期 < 0.8 | 评测报告 |

### 4.3 日志轮转与清理 (周维护)

```bash
# 每周一执行
# 1. 清理 7 天前的备份
find /home/admin/antigravity/backups -type d -mtime +7 -exec rm -rf {} \;

# 2. 清理 30 天前的日志 (保留 metrics JSONL)
find /home/admin/antigravity/logs -name "*.log" -mtime +30 -delete

# 3. 压缩旧 metrics 文件
gzip /home/admin/antigravity/logs/metrics_$(date -d '7 days ago' +%Y%m%d).jsonl
```

---

## 5. 评测体系与质量门禁

### 5.1 核心评测指标定义

| 维度 | 指标 | 计算方法 | 目标值 | 说明 |
|------|------|----------|--------|------|
| **预测质量** | Best Score | 公式在历史数据上的综合评分 | > 0.50 | 越高越好，基线 1.09 随机期望 |
| **预测质量** | Beats Random Rate | `best_score > random_baseline` 的比例 | > 30% | 滚动 30 轮统计 |
| **预测质量** | Brier Score | 概率预测的校准度指标 | < 0.18 | 越低越好 |
| **系统稳定性** | Daemon Uptime | 守护进程连续运行时长 | > 99.5% | 扣除计划维护窗口 |
| **系统稳定性** | Cycle Success Rate | 演化周期成功完成率 | > 95% | 含自动恢复后成功 |
| **数据新鲜度** | Data Lag | 最新开奖期 - 本地最新期 | 0 期 | > 1 期触发告警 |
| **监控可用性** | Dashboard Availability | HTTP 200 响应率 | > 99.9% | 5 分钟探测间隔 |

### 5.2 自动化评测脚本 (每日自动运行)

```bash
# 位置: /home/admin/antigravity/scripts/daily_eval.sh
# 通过 systemd timer 每日 06:00 执行

#!/bin/bash
set -euo pipefail

LOG_FILE="/home/admin/antigravity/logs/daily_eval_$(date +%Y%m%d).log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== Daily Evaluation $(date) ==="

# 1. 系统状态
STATUS=$(curl -sf http://localhost:8080/api/status)
LAST_SCORE=$(echo "$STATUS" | jq -r .last_score)
LAST_CYCLE=$(echo "$STATUS" | jq -r .last_cycle)
UPTIME=$(echo "$STATUS" | jq -r .uptime_hours)

echo "Last Score: $LAST_SCORE"
echo "Last Cycle: $LAST_CYCLE"
echo "Uptime: ${UPTIME}h"

# 2. 告警检查
ALERTS=$(curl -sf http://localhost:8080/api/alerts)
CRITICAL=$(echo "$ALERTS" | jq '[.[] | select(.level=="critical")] | length')
if [ "$CRITICAL" -gt 0 ]; then
    echo "⚠️ CRITICAL ALERTS: $CRITICAL"
    echo "$ALERTS" | jq '.[] | select(.level=="critical")'
fi

# 3. 评分趋势 (最近 7 天)
METRICS=$(curl -sf "http://localhost:8080/api/metrics?days=7")
AVG_SCORE=$(echo "$METRICS" | jq '[.[] | .best_score] | add / length')
MIN_SCORE=$(echo "$METRICS" | jq '[.[] | .best_score] | min')
echo "7-day Avg Score: $AVG_SCORE"
echo "7-day Min Score: $MIN_SCORE"

# 4. 质量门禁
if (( $(echo "$LAST_SCORE < 0.35" | bc -l) )); then
    echo "❌ QUALITY GATE FAILED: last_score < 0.35"
    # 触发告警通知 (可接入 Telegram/钉钉/邮件)
fi

if (( $(echo "$AVG_SCORE < 0.40" | bc -l) )); then
    echo "⚠️ WARNING: 7-day avg score < 0.40"
fi

echo "=== Evaluation Complete ==="
```

### 5.3 回测验证流程 (每周)

```bash
# 每周日执行完整回测
python walkforward_backtest_v3.py --periods 50 --strategies all

# 关注指标:
# - 累计收益率 vs 基准
# - 最大回撤
# - 夏普比率
# - 命中率分布
```

---

## 6. 故障恢复手册 (Runbook)

### 6.1 常见故障分级

| 级别 | 现象 | 响应时限 | 处理方式 |
|------|------|----------|----------|
| **P0 紧急** | 监控面板不可访问、两个守护进程均停止 | 15 分钟 | 立即重启服务、检查资源、查看日志 |
| **P1 高** | 单守护进程停止、评分连续低于阈值 | 1 小时 | 重启进程、触发自动恢复、人工介入 |
| **P2 中** | 磁盘/内存告警、数据滞后 1 期 | 4 小时 | 清理空间、补跑数据更新 |
| **P3 低** | 单次预测失败、非核心依赖报错 | 24 小时 | 下次维护窗口修复 |

### 6.2 P0 级故障标准处理流程

```bash
# 1. 确认故障范围
systemctl status antigravity-monitor
ps aux | grep -E "(cloud_daemon|research_daemon)" | grep -v grep

# 2. 检查资源
df -h /; free -h; uptime

# 3. 查看关键日志 (最近 50 行)
journalctl -u antigravity-monitor -n 50 --no-pager
tail -50 /home/admin/antigravity/logs/cloud_daemon_$(date +%Y%m%d).log
tail -50 /home/admin/antigravity/logs/research_daemon_$(date +%Y%m%d).log

# 4. 尝试自动恢复 (守护进程内置)
# cloud_daemon 连续失败 3 次会自动触发 attempt_recovery()

# 5. 手动重启服务
systemctl restart antigravity-monitor
python cloud_quick_deploy.py --stop && python cloud_quick_deploy.py --start

# 6. 如果仍失败，完全重建
python cloud_quick_deploy.py --setup  # 重新部署 (慎用，会重装 venv)
```

### 6.3 数据损坏恢复

```bash
# 1. 从备份恢复数据文件
LATEST_BACKUP=$(ls -dt /home/admin/antigravity/backups/*/ | head -1)
cp "$LATEST_BACKUP/lottery_history.csv" /home/admin/antigravity/data/
cp "$LATEST_BACKUP/"*.json /home/admin/antigravity/

# 2. 重新运行数据校验
python -c "from data_layer import load_history; d=load_history(); print(f'Loaded {len(d)} draws')"

# 3. 重置守护进程状态
rm -f /home/admin/antigravity/logs/*.pid
systemctl restart antigravity-monitor
python cloud_quick_deploy.py --start
```

---

## 7. 附录：待创建的 systemd 服务文件

### 7.1 antigravity-cloud-daemon.service

```ini
[Unit]
Description=Antigravity Cloud Evolution Daemon 7x24
After=network.target antigravity-monitor.service
Wants=antigravity-monitor.service

[Service]
Type=simple
User=admin
WorkingDirectory=/home/admin/antigravity
ExecStart=/home/admin/antigravity/.venv/bin/python cloud_daemon_24x7.py
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1
# 资源限制 (可选)
# MemoryMax=8G
# CPUQuota=2000%

[Install]
WantedBy=multi-user.target
```

### 7.2 antigravity-research-daemon.service

```ini
[Unit]
Description=Antigravity Research Daemon 7x24
After=network.target antigravity-cloud-daemon.service
Wants=antigravity-cloud-daemon.service

[Service]
Type=simple
User=admin
WorkingDirectory=/home/admin/antigravity
ExecStart=/home/admin/antigravity/.venv/bin/python research_daemon_24x7.py
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

### 7.3 批量部署脚本 (deploy_daemons.sh)

```bash
#!/bin/bash
# 部署两个守护进程为 systemd 服务
set -euo pipefail

cd /home/admin/antigravity

# 创建服务文件
cat > antigravity-cloud-daemon.service <<'EOF'
[Unit]
Description=Antigravity Cloud Evolution Daemon 7x24
After=network.target

[Service]
Type=simple
User=admin
WorkingDirectory=/home/admin/antigravity
ExecStart=/home/admin/antigravity/.venv/bin/python cloud_daemon_24x7.py
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

cat > antigravity-research-daemon.service <<'EOF'
[Unit]
Description=Antigravity Research Daemon 7x24
After=network.target

[Service]
Type=simple
User=admin
WorkingDirectory=/home/admin/antigravity
ExecStart=/home/admin/antigravity/.venv/bin/python research_daemon_24x7.py
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# 安装并启动
sudo cp antigravity-*-daemon.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now antigravity-cloud-daemon antigravity-research-daemon

# 验证
systemctl status antigravity-cloud-daemon antigravity-research-daemon --no-pager
```

---

## 8. 版本历史

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| 1.0 | 2026-08-08 | 初版：全架构梳理、部署工作流、每日清单、评测体系、故障手册 | System |

---

> **文档维护原则**：  
> - 每次重大架构变更、新增组件、调整阈值时同步更新本文档  
> - 运维实操中发现的新故障模式、新恢复路径及时补录到 Runbook  
> - 评测指标随模型迭代调整，保持与业务目标对齐