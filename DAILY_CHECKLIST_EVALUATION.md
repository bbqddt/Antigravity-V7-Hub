# Antigravity 每日开机必做工作清单与评测指标

> **执行频率**: 每日首次登录云端 / 服务器重启后  
> **执行时间**: ~5 分钟  
> **记录位置**: `logs/daily_checklist_YYYYMMDD.log` (建议人工记录或脚本自动生成)

---

## 📋 每日开机必做清单 (Daily Startup Checklist)

### Phase 1: 基础设施健康检查 (必须通过，否则阻塞后续)

| # | 检查项 | 命令 | ✅ 通过标准 | ❌ 失败处理 | 记录值 |
|---|--------|------|-------------|-------------|--------|
| 1.1 | **监控面板 systemd 服务** | `systemctl is-active antigravity-monitor` | `active` | `systemctl restart antigravity-monitor` | [ ] |
| 1.2 | **监控面板 HTTP API** | `curl -sf http://localhost:8080/api/status \| jq .` | 返回完整 JSON，含 `cloud_daemon: "running"` | `journalctl -u antigravity-monitor -n 50` | [ ] |
| 1.3 | **监控面板 Web UI** | `curl -sf http://localhost:8080/ \| head -5` | 返回 HTML，含 "Antigravity 7x24 监控面板" | 同上 | [ ] |
| 1.4 | **云端演化守护进程** | `ps aux \| grep cloud_daemon_24x7 \| grep -v grep` | 存在 1 个进程，PID 稳定 | `python cloud_quick_deploy.py --start` | [ ] |
| 1.5 | **研究守护进程** | `ps aux \| grep research_daemon_24x7 \| grep -v grep` | 存在 1 个进程，PID 稳定 | 手动启动 `python research_daemon_24x7.py &` | [ ] |
| 1.6 | **磁盘可用空间** | `df -h / \| awk 'NR==2{print $4}'` | > 10 GB | 清理 `/home/admin/antigravity/backups/` 旧目录 | ___ GB |
| 1.7 | **内存可用量** | `free -h \| awk 'NR==2{print $7}'` | > 20 GB | 检查内存泄漏，必要时重启守护进程 | ___ GB |
| 1.8 | **数据文件完整性** | `wc -l /home/admin/antigravity/data/lottery_history.csv` | 行数 > 2000 (含表头)，文件 > 100KB | `python data_updater_v2.py` | ___ 行 |
| 1.9 | **最新预测文件** | `cat /home/admin/antigravity/latest_prediction.json \| jq .target_period` | 目标期号 = 最新开奖期号 + 1 | `python orchestrate.py --top-k 5` | 第 ___ 期 |

> **Phase 1 全绿方可进入 Phase 2** ⚠️

---

### Phase 2: 核心指标采集与判读 (量化记录)

| # | 指标 | 获取命令 | 🟢 正常区间 | 🟡 预警区间 | 🔴 危险区间 | 今日数值 | 备注 |
|---|------|----------|-------------|-------------|-------------|----------|------|
| 2.1 | **最佳评分** | `curl -s localhost:8080/api/status \| jq .last_score` | ≥ 0.45 | 0.35~0.45 | < 0.35 | | |
| 2.2 | **完成演化轮数** | `curl -s localhost:8080/api/status \| jq .last_cycle` | 递增，≥ 昨天 | 24h 无增长 | 48h 无增长 | | |
| 2.3 | **系统运行时长** | `curl -s localhost:8080/api/status \| jq .uptime_hours` | 递增 | — | 重启后 < 1h | | |
| 2.4 | **磁盘剩余** | `df -h / \| awk 'NR==2{print $4}'` | > 20 GB | 10~20 GB | < 10 GB | | |
| 2.5 | **beats_random** | `tail -1 logs/metrics_$(date +%Y%m%d).jsonl \| jq .beats_random` | 偶尔 true | 连续 3 天 false | 连续 7 天 false | | |
| 2.6 | **Brier Score** | `tail -1 logs/metrics_$(date +%Y%m%d).jsonl \| jq .brier_score` | < 0.18 | 0.18~0.22 | > 0.22 | | 近似键名 |
| 2.7 | **连续失败计数** | `grep -c "连续失败" logs/cloud_daemon_$(date +%Y%m%d).log` | 0 | 1~2 | ≥ 3 (触发自动恢复) | | |
| 2.8 | **健康检查通过率** | `grep -c "健康检查通过" logs/cloud_daemon_$(date +%Y%m%d).log` | ≥ 40 次/天 | 20~40 | < 20 | | 30分钟/次 |
| 2.9 | **预测引擎可用数** | `curl -s localhost:8080/api/status \| jq .health_entries` | ≥ 2 | 1 | 0 | | Luckcast + Enhanced |

---

### Phase 3: 质量门禁决策 (Quality Gate)

根据 Phase 2 采集的指标，作出今日运维决策：

| 决策类型 | 触发条件 | 动作 | 责任人 | 记录 |
|----------|----------|------|--------|------|
| **✅ 正常放行** | 所有指标 🟢 | 无需干预，常规巡检 | 运维 | [ ] |
| **⚠️ 关注观察** | 任一指标 🟡，无 🔴 | 记录、加大巡检频次至 2h/次 | 运维 | [ ] |
| **🔴 需介入** | 任一指标 🔴 | 立即按 Runbook 处理，升级通知 | 运维+开发 | [ ] |
| **🚨 紧急熔断** | 两个守护进程均停止、或监控面板不可达 > 10min | 执行 P0 故障流程，必要时重建部署 | 运维+开发 | [ ] |

---

## 📊 评测指标体系 (Evaluation Metrics Framework)

### 核心预测质量指标 (每日自动采集，周报聚合)

| 一级指标 | 二级指标 | 计算口径 | 目标值 | 采集频率 | 数据源 |
|----------|----------|----------|--------|----------|--------|
| **准确性** | Best Score (最佳评分) | 公式在历史校对中的综合得分 | > 0.50 | 每轮演化 | `metrics_*.jsonl` |
| **准确性** | Beats Random Rate | `best_score > 1.09` 的轮次占比 (滚动 30 轮) | > 30% | 每日 | `metrics_*.jsonl` |
| **校准度** | Brier Score | 概率预测的均方误差 | < 0.18 | 每日 | `metrics_*.jsonl` |
| **稳定性** | Score Volatility | 最近 30 轮 best_score 标准差 | < 0.05 | 每周 | `metrics_*.jsonl` |
| **趋势** | Score Trend | 最近 10 轮线性回归斜率 | > 0 (上升) | 每周 | `metrics_*.jsonl` |

### 系统工程指标 (每日自动采集)

| 一级指标 | 二级指标 | 计算口径 | 目标值 | 采集频率 | 数据源 |
|----------|----------|----------|--------|----------|--------|
| **可用性** | Daemon Uptime | 守护进程存活时间 / 总时间 | > 99.5% | 每日 | systemd + 健康日志 |
| **可用性** | Dashboard Availability | HTTP 200 响应率 (5min 探测) | > 99.9% | 每日 | 监控面板 / 外部监控 |
| **可靠性** | Cycle Success Rate | 成功完成演化轮次 / 触发轮次 | > 95% | 每日 | `cloud_daemon_*.log` |
| **可靠性** | Auto Recovery Rate | 自动恢复成功次数 / 触发恢复次数 | > 80% | 每周 | `cloud_daemon_*.log` |
| **时效性** | Data Freshness | 最新开奖期 - 本地最新期 | 0 期 | 每日 | `latest_prediction.json` |
| **资源** | Disk Usage Trend | 日均磁盘增长量 | < 500 MB/天 | 每周 | `df -h` 历史 |
| **资源** | Memory Leak Check | 守护进程 RSS 增长趋势 | 稳定/微增 | 每周 | `ps aux` 采样 |

### 业务价值指标 (周/月人工评测)

| 指标 | 计算方式 | 目标 | 评测周期 | 备注 |
|------|----------|------|----------|------|
| **回测命中率** | 最近 50 期 Top-5 预测中奖统计 | 红球 ≥ 3 个命中率 > 15% | 每周 | 需对接开奖结果 |
| **回测收益率** | 模拟投注 ROI (含奖金扣税) | > 0 (盈亏平衡为基线) | 每月 | 需真实开奖数据 |
| **策略多样性** | 不同引擎/策略贡献的唯一预测占比 | > 40% | 每月 | 避免模式崩塌 |
| **创新率** | LLM 研究产生的新原语/策略被采纳率 | > 10% | 每月 | 研究守护进程产出 |

---

## 🤖 自动化采集脚本 (部署建议)

### 部署为 systemd timer (每日 06:00 执行)

**文件**: `/etc/systemd/system/antigravity-daily-eval.service`
```ini
[Unit]
Description=Antigravity Daily Evaluation
After=network.target

[Service]
Type=oneshot
User=admin
WorkingDirectory=/home/admin/antigravity
ExecStart=/home/admin/antigravity/scripts/daily_eval.sh
StandardOutput=journal
StandardError=journal
```

**文件**: `/etc/systemd/system/antigravity-daily-eval.timer`
```ini
[Unit]
Description=Run daily evaluation at 06:00

[Timer]
OnCalendar=*-*-* 06:00:00
Persistent=true
RandomizedDelaySec=15m

[Install]
WantedBy=timers.target
```

**启用**: `sudo systemctl enable --now antigravity-daily-eval.timer`

### 核心采集脚本: `scripts/daily_eval.sh`

```bash
#!/bin/bash
# /home/admin/antigravity/scripts/daily_eval.sh
# 每日自动评测采集 - 由 systemd timer 触发

set -euo pipefail

DATE=$(date +%Y%m%d)
LOG_DIR="/home/admin/antigravity/logs"
OUT_FILE="${LOG_DIR}/daily_eval_${DATE}.json"
TMP_DIR=$(mktemp -d)

cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

echo "=== Daily Evaluation ${DATE} Started ===" | tee -a "${LOG_DIR}/daily_eval.log"

# 1. 拉取监控面板数据
STATUS=$(curl -sf http://localhost:8080/api/status 2>/dev/null || echo '{}')
METRICS=$(curl -sf "http://localhost:8080/api/metrics?days=7" 2>/dev/null || echo '[]')
ALERTS=$(curl -sf http://localhost:8080/api/alerts 2>/dev/null || echo '[]')
HEALTH=$(curl -sf http://localhost:8080/api/health 2>/dev/null || echo '[]')

# 2. 系统资源
DISK_FREE=$(df -h / | awk 'NR==2{print $4}' | sed 's/G//')
MEM_FREE=$(free -g | awk 'NR==2{print $7}')
UPTIME_HOURS=$(uptime | grep -oP 'up \K[^,]+' | head -1)

# 3. 守护进程状态
CLOUD_PID=$(pgrep -f cloud_daemon_24x7 | head -1)
RESEARCH_PID=$(pgrep -f research_daemon_24x7 | head -1)

# 4. 最新 metrics 解析
LATEST_METRIC=$(echo "$METRICS" | jq 'if length>0 then .[-1] else {} end')
LAST_SCORE=$(echo "$LATEST_METRIC" | jq -r '.best_score // 0')
LAST_CYCLE=$(echo "$LATEST_METRIC" | jq -r '.cycle // 0')
BEATS_RANDOM=$(echo "$LATEST_METRIC" | jq -r '.beats_random // false')
BRIER=$(echo "$LATEST_METRIC" | jq -r '.brier_score // 0')

# 5. 7天聚合
AVG_SCORE=$(echo "$METRICS" | jq '[.[] | .best_score] | if length>0 then add/length else 0 end')
MIN_SCORE=$(echo "$METRICS" | jq '[.[] | .best_score] | if length>0 then min else 0 end')
MAX_SCORE=$(echo "$METRICS" | jq '[.[] | .best_score] | if length>0 then max else 0 end')

# 6. 告警统计
CRITICAL_ALERTS=$(echo "$ALERTS" | jq '[.[] | select(.level=="critical")] | length')
WARNING_ALERTS=$(echo "$ALERTS" | jq '[.[] | select(.level=="warning")] | length')

# 7. 构建输出 JSON
cat > "$OUT_FILE" <<EOF
{
  "date": "${DATE}",
  "timestamp": "$(date -Iseconds)",
  "system": {
    "disk_free_gb": ${DISK_FREE},
    "mem_free_gb": ${MEM_FREE},
    "uptime": "${UPTIME_HOURS}",
    "cloud_daemon_pid": ${CLOUD_PID:-null},
    "research_daemon_pid": ${RESEARCH_PID:-null}
  },
  "prediction_quality": {
    "last_score": ${LAST_SCORE},
    "last_cycle": ${LAST_CYCLE},
    "beats_random": ${BEATS_RANDOM},
    "brier_score": ${BRIER},
    "7day_avg_score": ${AVG_SCORE},
    "7day_min_score": ${MIN_SCORE},
    "7day_max_score": ${MAX_SCORE}
  },
  "alerts": {
    "critical": ${CRITICAL_ALERTS},
    "warning": ${WARNING_ALERTS},
    "details": ${ALERTS}
  },
  "health_checks": ${HEALTH}
}
EOF

# 8. 质量门禁检查
GATE_PASSED=true
GATE_MSG=""

if (( $(echo "$LAST_SCORE < 0.35" | bc -l 2>/dev/null || echo 0) )); then
    GATE_PASSED=false
    GATE_MSG="${GATE_MSG} | last_score < 0.35"
fi

if (( $(echo "$AVG_SCORE < 0.40" | bc -l 2>/dev/null || echo 0) )); then
    GATE_PASSED=false
    GATE_MSG="${GATE_MSG} | 7day_avg < 0.40"
fi

if [ "$CRITICAL_ALERTS" -gt 0 ]; then
    GATE_PASSED=false
    GATE_MSG="${GATE_MSG} | ${CRITICAL_ALERTS} critical alerts"
fi

if [ -z "$CLOUD_PID" ] || [ -z "$RESEARCH_PID" ]; then
    GATE_PASSED=false
    GATE_MSG="${GATE_MSG} | daemon(s) missing"
fi

# 9. 输出摘要
cat <<EOF | tee -a "${LOG_DIR}/daily_eval.log"

=== Daily Evaluation Summary ${DATE} ===
Quality Gate: $([ "$GATE_PASSED" = true ] && echo "✅ PASSED" || echo "❌ FAILED${GATE_MSG}")
Last Score: ${LAST_SCORE} | 7d Avg: ${AVG_SCORE} | 7d Min: ${MIN_SCORE}
Last Cycle: ${LAST_CYCLE} | Beats Random: ${BEATS_RANDOM}
Cloud Daemon: $([ -n "$CLOUD_PID" ] && echo "RUNNING ($CLOUD_PID)" || echo "STOPPED")
Research Daemon: $([ -n "$RESEARCH_PID" ] && echo "RUNNING ($RESEARCH_PID)" || echo "STOPPED")
Critical Alerts: ${CRITICAL_ALERTS} | Warning: ${WARNING_ALERTS}
Disk Free: ${DISK_FREE}GB | Mem Free: ${MEM_FREE}GB
Detail JSON: ${OUT_FILE}
==============================

EOF

# 10. 如果门禁失败，写入告警日志 (可对接外部通知)
if [ "$GATE_PASSED" = false ]; then
    echo "[ALERT] Quality gate failed: ${GATE_MSG}" | tee -a "${LOG_DIR}/daily_eval.log"
    # 这里可接入: curl -X POST "webhook_url" -d "{\"text\":\"Antigravity质量门禁失败: ${GATE_MSG}\"}"
fi

echo "=== Daily Evaluation ${DATE} Completed ===" | tee -a "${LOG_DIR}/daily_eval.log"
```

---

## 📝 使用模板 (人工记录版)

### 每日开机检查记录表

| 日期 | 执行人 | Phase 1 全绿? | 关键指标异常 | 质量门禁 | 处理动作 | 备注 |
|------|--------|---------------|--------------|----------|----------|------|
| 2026-08-08 | | ☐ 是 ☐ 否 | | ☐ 通过 ☐ 关注 ☐ 介入 ☐ 熔断 | | |
| 2026-08-09 | | ☐ 是 ☐ 否 | | ☐ 通过 ☐ 关注 ☐ 介入 ☐ 熔断 | | |
| 2026-08-10 | | ☐ 是 ☐ 否 | | ☐ 通过 ☐ 关注 ☐ 介入 ☐ 熔断 | | |

### 关键指标趋势记录 (周维度)

| 周起止 | 平均Best Score | Beats Random率 | 完成轮数 | 平均Brier | 守护进程可用性 | 告警次数 | 质量门禁通过率 |
|--------|----------------|----------------|----------|-----------|----------------|----------|----------------|
| 8.4-8.10 | | | | | | | |
| 8.11-8.17 | | | | | | | |

---

## 🔗 关联文档

- **总体工作流**: `WORKFLOW_OPERATIONS.md` (部署、运维、故障恢复全流程)
- **监控面板 API**: `monitor_dashboard.py` (端口 8080, `/api/status`, `/api/metrics`, `/api/alerts`, `/api/health`)
- **守护进程配置**: `cloud_daemon_24x7.py`, `research_daemon_24x7.py` (演化间隔 6h, 研究间隔 12h, 健康检查 30min)
- **部署脚本**: `cloud_quick_deploy.py`, `deploy_all.py` (支持 `--deploy-monitor`, `--cloud-action deploy-monitor`)

---

> **维护提示**:  
> - 每日检查建议固化为 `scripts/daily_eval.sh` + systemd timer 自动化  
> - 质量门禁阈值随模型迭代调整，建议每月复盘一次  
> - 所有原始指标保留在 `logs/daily_eval_YYYYMMDD.json` 供历史回溯