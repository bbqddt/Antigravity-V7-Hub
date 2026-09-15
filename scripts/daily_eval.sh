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
Quality Gate: $([ "$GATE_PASSED" = true ] && echo "PASSED" || echo "FAILED${GATE_MSG}")
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