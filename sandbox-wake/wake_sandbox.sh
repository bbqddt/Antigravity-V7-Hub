#!/usr/bin/env bash
#
# wake_sandbox.sh — 策略 A：从沙箱「外面」唤醒 CloudStudio 沙箱
# ⚠️ 必须在本地机器 / IDE 侧运行，绝不要放进沙箱里（沙箱睡着时它自己跑不了）。
#
# 用法（三种都行，已内置默认沙箱地址，可直接 ./wake_sandbox.sh）:
#   ./wake_sandbox.sh                                                       # 使用内置默认地址
#   ./wake_sandbox.sh "https://webview.e2b.gz2.sandbox.cloudstudio.club"
#   SANDBOX_URL="https://webview.e2b.gz2.sandbox.cloudstudio.club" ./wake_sandbox.sh
#
# 原理:
#   1) 向沙箱 webview 地址发一个请求 → CloudStudio 代理检测到休眠，拉起空间
#   2) supervisord 已配好，自动把 3000 服务带起来
#   3) 轮询 <BASE>/health 直到返回 200，说明可以打开 webview 用了
#
set -u

# ---------- 可配置项 ----------
DEFAULT_URL="https://webview.e2b.gz2.sandbox.cloudstudio.club"   # 你的 CloudStudio 沙箱 webview 地址
BASE_URL="${1:-${SANDBOX_URL:-$DEFAULT_URL}}"
HEALTH_PATH="/health"     # 你的 3000 服务暴露的健康检查端点
MAX_WAIT=120              # 最多等待秒数
POLL_INTERVAL=5           # 轮询间隔秒数
# --------------------------------

if [[ -z "$BASE_URL" ]]; then
  echo "❌ 未提供沙箱地址。" >&2
  echo "   用法: SANDBOX_URL='https://你的沙箱地址' $0" >&2
  exit 2
fi

# 去掉末尾斜杠
BASE_URL="${BASE_URL%/}"
HEALTH_URL="${BASE_URL}${HEALTH_PATH}"

need_cmd() { command -v "$1" >/dev/null 2>&1 || { echo "❌ 需要 '$1' 但未找到（Windows 请用 Git Bash / WSL）" >&2; exit 3; }; }
need_cmd curl

echo "🔔 正在向沙箱发请求以触发唤醒: $BASE_URL"
curl -sS -m 10 -o /dev/null -w "   wake HTTP %{http_code}\n" "$BASE_URL" \
  || echo "   (唤醒请求可能超时/非200，继续轮询 health 状态)"

echo "⏳ 等待 3000 服务就绪 (最多 ${MAX_WAIT}s)..."
elapsed=0
while (( elapsed < MAX_WAIT )); do
  code=$(curl -sS -m 10 -o /dev/null -w "%{http_code}" "$HEALTH_URL" 2>/dev/null)
  if [[ "$code" == "200" ]]; then
    echo "✅ 服务已就绪: $HEALTH_URL (HTTP 200)，耗时 ${elapsed}s"
    echo "   现在可以打开 webview 了。"
    exit 0
  fi
  echo "   ... health=$code，等待中 (${elapsed}s/${MAX_WAIT}s)"
  sleep "$POLL_INTERVAL"
  elapsed=$((elapsed + POLL_INTERVAL))
done

echo "⚠️ 等待超时，服务未在 ${MAX_WAIT}s 内就绪。请检查:" >&2
echo "   - 沙箱地址是否正确（CloudStudio 预览/访问地址）" >&2
echo "   - 3000 服务是否暴露了 $HEALTH_PATH 端点" >&2
echo "   - CloudStudio 代理是否确实通过该地址唤醒空间" >&2
exit 1
