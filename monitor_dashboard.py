#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Antigravity 7x24 监控面板
==========================
FastAPI + Chart.js 单页应用，实时展示演化指标、健康状态、告警
端口: 8080
"""
import os
import json
import glob
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = PROJECT_ROOT / "logs"

app = FastAPI(title="Antigravity 7x24 Monitor", version="1.0.0")

# ─── 工具函数 ────────────────────────────────────────────

def read_metrics_files(days: int = 7) -> List[Dict[str, Any]]:
    """读取最近 N 天的 metrics JSONL 文件"""
    metrics = []
    cutoff = datetime.now() - timedelta(days=days)
    for f in sorted(LOG_DIR.glob("metrics_*.jsonl")):
        try:
            file_date = datetime.strptime(f.stem.split("_")[1], "%Y%m%d")
            if file_date < cutoff:
                continue
            with open(f, encoding='utf-8') as fp:
                for line in fp:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        m = json.loads(line)
                        # 过滤未来数据
                        ts = datetime.fromisoformat(m["timestamp"])
                        if ts > datetime.now() + timedelta(minutes=5):
                            continue
                        metrics.append(m)
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass
    return sorted(metrics, key=lambda x: x["timestamp"])

def read_health_log() -> List[Dict[str, Any]]:
    """读取健康检查日志"""
    health_file = LOG_DIR / "health_24x7.log"
    if not health_file.exists():
        return []
    entries = []
    with open(health_file, encoding='utf-8') as f:
        for line in f:
            if "[HEALTH]" in line:
                try:
                    parts = line.strip().split(" ", 3)
                    timestamp = f"{parts[1]} {parts[2]}"
                    rest = parts[3] if len(parts) > 3 else ""
                    # 解析 CloudDaemon=RUNNING ResearchDaemon=STOPPED
                    status = {}
                    for item in rest.split():
                        if "=" in item:
                            k, v = item.split("=", 1)
                            status[k] = v
                    entries.append({"timestamp": timestamp, **status})
                except Exception:
                    pass
    return entries[-100:]  # 最近 100 条

def _pid_running(pid: int) -> bool:
    """跨平台判断 PID 是否存活：优先 psutil，缺失则回退到系统调用（无需第三方依赖）。"""
    try:
        import psutil
        return psutil.Process(pid).is_running()
    except ImportError:
        pass  # psutil 未安装，走下方回退
    except Exception:
        return False
    import sys
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_INFORMATION = 0x0400
            handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
            if not handle:
                return False
            exit_code = wintypes.DWORD()
            kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
            kernel32.CloseHandle(handle)
            return exit_code.value == 259  # STILL_ACTIVE
        except Exception:
            return False
    else:
        try:
            import os
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False
        except Exception:
            return False

def check_process_alive(name: str) -> bool:
    """检查进程是否存活（通过 PID 文件 + 系统调用精确判断，psutil 可选）"""
    import tempfile
    pid_file = Path(tempfile.gettempdir()) / f"antigravity-{name}.pid"
    if not pid_file.exists():
        return False
    try:
        with open(pid_file) as f:
            pid = int(f.read().strip())
    except (ValueError, FileNotFoundError):
        return False
    return _pid_running(pid)

def compute_alerts(metrics: List[Dict]) -> List[Dict[str, Any]]:
    """计算告警"""
    alerts = []
    if not metrics:
        return [{"level": "warning", "message": "暂无指标数据", "time": datetime.now().isoformat()}]
    
    latest = metrics[-1]
    
    # 1. 磁盘空间
    if latest.get("disk_free_gb", 999) < 5:
        alerts.append({"level": "critical", "message": f"磁盘空间不足: {latest['disk_free_gb']:.1f}GB", "time": latest["timestamp"]})
    elif latest.get("disk_free_gb", 999) < 10:
        alerts.append({"level": "warning", "message": f"磁盘空间预警: {latest['disk_free_gb']:.1f}GB", "time": latest["timestamp"]})
    
    # 2. 连续 3 轮 beats_random=False (best_score < baseline)
    # baseline 随机约 1.09 hits，这里用 score < 0.4 近似
    recent = metrics[-3:] if len(metrics) >= 3 else metrics
    if all(m.get("best_score", 1) < 0.4 for m in recent):
        alerts.append({"level": "critical", "message": "连续 3 轮评分低于基线 (疑似退化)", "time": latest["timestamp"]})
    
    # 3. 评分连续下降 (最近 5 轮单调递减)
    if len(metrics) >= 5:
        scores = [m.get("best_score", 0) for m in metrics[-5:]]
        if all(scores[i] > scores[i+1] for i in range(len(scores)-1)):
            alerts.append({"level": "warning", "message": "评分连续 5 轮下降", "time": latest["timestamp"]})
    
    # 4. 进程存活
    cloud_alive = check_process_alive("cloud_daemon_24x7")
    research_alive = check_process_alive("research_daemon_24x7")
    if not cloud_alive:
        alerts.append({"level": "critical", "message": "CloudDaemon 进程未运行", "time": datetime.now().isoformat()})
    if not research_alive:
        alerts.append({"level": "critical", "message": "ResearchDaemon 进程未运行", "time": datetime.now().isoformat()})
    
    if not alerts:
        alerts.append({"level": "ok", "message": "系统运行正常", "time": latest["timestamp"]})
    
    return alerts

# ─── API 路由 ────────────────────────────────────────────

@app.get("/api/metrics")
def api_metrics(days: int = 7):
    metrics = read_metrics_files(days)
    return JSONResponse(metrics)

@app.get("/api/health")
def api_health():
    """实时健康状态：直接读 PID 文件 + psutil 判断真实存活（不再读陈旧的 health_24x7.log）"""
    cloud_alive = check_process_alive("cloud_daemon_24x7")
    research_alive = check_process_alive("research_daemon_24x7")
    return JSONResponse([{
        "timestamp": datetime.now().isoformat(),
        "CloudDaemon": "RUNNING" if cloud_alive else "STOPPED",
        "ResearchDaemon": "RUNNING" if research_alive else "STOPPED",
    }])

@app.get("/api/health-history")
def api_health_history():
    """历史健康检查日志（保留 read_health_log 供历史查看）"""
    return JSONResponse(read_health_log())

@app.get("/api/alerts")
def api_alerts():
    metrics = read_metrics_files(7)
    alerts = compute_alerts(metrics)
    return JSONResponse(alerts)

@app.get("/api/status")
def api_status():
    metrics = read_metrics_files(1)
    cloud_alive = check_process_alive("cloud_daemon_24x7")
    research_alive = check_process_alive("research_daemon_24x7")
    return JSONResponse({
        "cloud_daemon": "running" if cloud_alive else "stopped",
        "research_daemon": "running" if research_alive else "stopped",
        "last_cycle": metrics[-1]["cycle"] if metrics else 0,
        "last_score": metrics[-1]["best_score"] if metrics else 0,
        "last_update": metrics[-1]["timestamp"] if metrics else None,
        "health_entries": 1 if cloud_alive or research_alive else 0,
        "uptime_hours": metrics[-1].get("uptime_hours", 0) if metrics else 0,
        "last_health_check": datetime.now().isoformat(),
    })

# ─── WebSocket 实时推送 ──────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []
    
    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)
    
    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)
    
    async def broadcast(self, data: dict):
        for ws in self.active[:]:
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(ws)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # 保持连接
    except WebSocketDisconnect:
        manager.disconnect(ws)

async def push_loop():
    """后台任务：每 30 秒推送最新状态"""
    import asyncio
    while True:
        await asyncio.sleep(30)
        metrics = read_metrics_files(1)
        health = read_health_log()
        alerts = compute_alerts(read_metrics_files(7))
        status = {
            "metrics_latest": metrics[-1] if metrics else None,
            "health_latest": health[-1] if health else None,
            "alerts": alerts,
            "timestamp": datetime.now().isoformat()
        }
        await manager.broadcast(status)

@app.on_event("startup")
async def startup_event():
    import asyncio
    asyncio.create_task(push_loop())

# ─── 前端页面 ────────────────────────────────────────────

INDEX_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Antigravity 7x24 监控面板</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'JetBrains Mono', monospace; background: #0d1117; color: #e6edf3; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; }
        .metric-value { font-size: 2rem; font-weight: 600; }
        .metric-label { font-size: 0.875rem; color: #8b949e; }
        .alert-critical { border-left: 4px solid #f85149; background: rgba(248,81,73,0.1); }
        .alert-warning { border-left: 4px solid #d29922; background: rgba(210,153,34,0.1); }
        .alert-ok { border-left: 4px solid #3fb950; background: rgba(63,185,80,0.1); }
        .status-running { color: #3fb950; }
        .status-stopped { color: #f85149; }
        canvas { max-height: 300px; }
        .tooltip { background: #161b22 !important; border: 1px solid #30363d !important; color: #e6edf3 !important; }
    </style>
</head>
<body class="min-h-screen p-4 md:p-8">
    <div class="max-w-7xl mx-auto space-y-6">
        <!-- Header -->
        <header class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
                <h1 class="text-2xl font-bold">Antigravity 7x24 监控面板</h1>
                <p class="text-sm text-gray-400">公式演化 · LLM 研究 · 自动化运行</p>
            </div>
            <div class="flex items-center gap-4 text-sm">
                <span id="conn-status" class="px-2 py-1 rounded bg-gray-800">连接中...</span>
                <span id="last-update" class="text-gray-400"></span>
            </div>
        </header>

        <!-- Status Cards -->
        <section class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4" id="status-cards">
            <!-- JS 渲染 -->
        </section>

        <!-- Alerts -->
        <section class="card p-4">
            <h2 class="text-lg font-semibold mb-3 flex items-center gap-2">⚠ 告警与状态</h2>
            <div id="alerts" class="space-y-2"></div>
        </section>

        <!-- Charts -->
        <section class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div class="card p-4">
                <h3 class="font-semibold mb-3">📈 最佳评分趋势</h3>
                <canvas id="scoreChart"></canvas>
            </div>
            <div class="card p-4">
                <h3 class="font-semibold mb-3">⏱️ 单轮耗时 & 磁盘空间</h3>
                <canvas id="perfChart"></canvas>
            </div>
        </section>

        <!-- Health Log -->
        <section class="card p-4">
            <h3 class="font-semibold mb-3">🏥 健康检查历史 (最近 50 条)</h3>
            <div class="overflow-x-auto">
                <table class="w-full text-sm" id="health-table">
                    <thead class="text-gray-400">
                        <tr><th class="text-left pb-2">时间</th><th class="text-left pb-2">CloudDaemon</th><th class="text-left pb-2">ResearchDaemon</th></tr>
                    </thead>
                    <tbody id="health-body"></tbody>
                </table>
            </div>
        </section>
    </div>

    <script>
        // ─── 状态管理 ─────────────────────────────────────
        let scoreChart, perfChart;
        let ws = null;

        // ─── 初始化 ───────────────────────────────────────
        async function init() {
            await Promise.all([loadStatus(), loadAlerts(), loadCharts(), loadHealth()]);
            connectWS();
            setInterval(() => Promise.all([loadStatus(), loadAlerts()]), 30000);
            setInterval(() => Promise.all([loadCharts(), loadHealth()]), 60000);
        }

        // ─── WebSocket ────────────────────────────────────
        function connectWS() {
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${location.host}/ws`);
            ws.onopen = () => setConnStatus('connected');
            ws.onclose = () => { setConnStatus('disconnected'); setTimeout(connectWS, 5000); };
            ws.onmessage = (e) => {
                const data = JSON.parse(e.data);
                updateStatusCards(data.metrics_latest);
                updateAlerts(data.alerts);
                updateChartsIncremental(data.metrics_latest);
                updateHealthTable(data.health_latest ? [data.health_latest] : []);
                document.getElementById('last-update').textContent = `更新: ${new Date().toLocaleTimeString()}`;
            };
        }

        function setConnStatus(state) {
            const el = document.getElementById('conn-status');
            el.textContent = state === 'connected' ? '🟢 已连接' : '🔴 断开重连...';
            el.className = 'px-2 py-1 rounded text-xs ' + (state === 'connected' ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400');
        }

        // ─── API 请求 ─────────────────────────────────────
        async function fetchAPI(path) {
            const res = await fetch(path);
            return res.json();
        }

        async function loadStatus() {
            const data = await fetchAPI('/api/status');
            updateStatusCards(data);
        }

        async function loadAlerts() {
            const data = await fetchAPI('/api/alerts');
            updateAlerts(data);
        }

        async function loadCharts() {
            const data = await fetchAPI('/api/metrics?days=7');
            renderCharts(data);
        }

        async function loadHealth() {
            const data = await fetchAPI('/api/health');
            renderHealthTable(data);
        }

        // ─── 渲染函数 ─────────────────────────────────────
        function updateStatusCards(data) {
            const container = document.getElementById('status-cards');
            const cloud = data.cloud_daemon || 'unknown';
            const research = data.research_daemon || 'unknown';
            const cycle = data.last_cycle || 0;
            const score = data.last_score || 0;
            const uptime = data.uptime_hours || 0;
            
            container.innerHTML = `
                <div class="card p-4">
                    <div class="metric-label">CloudDaemon</div>
                    <div class="metric-value status-${cloud}">${cloud === 'running' ? '🟢 运行中' : '🔴 已停止'}</div>
                </div>
                <div class="card p-4">
                    <div class="metric-label">ResearchDaemon</div>
                    <div class="metric-value status-${research}">${research === 'running' ? '🟢 运行中' : '🔴 已停止'}</div>
                </div>
                <div class="card p-4">
                    <div class="metric-label">完成轮数</div>
                    <div class="metric-value">${cycle}</div>
                </div>
                <div class="card p-4">
                    <div class="metric-label">最佳评分</div>
                    <div class="metric-value">${score.toFixed(4)}</div>
                </div>
                <div class="card p-4 md:col-span-2">
                    <div class="metric-label">运行时长</div>
                    <div class="metric-value">${uptime.toFixed(1)} 小时</div>
                </div>
                <div class="card p-4 md:col-span-2">
                    <div class="metric-label">最后更新</div>
                    <div class="metric-value text-base">${data.last_update ? new Date(data.last_update).toLocaleString() : '暂无'}</div>
                </div>
            `;
        }

        function updateAlerts(alerts) {
            const container = document.getElementById('alerts');
            if (!alerts.length) {
                container.innerHTML = '<div class="text-gray-400 text-sm">无告警</div>';
                return;
            }
            container.innerHTML = alerts.map(a => `
                <div class="p-3 rounded alert-${a.level} flex items-center gap-3">
                    <span class="text-lg">${a.level === 'critical' ? '🔴' : a.level === 'warning' ? '🟡' : '🟢'}</span>
                    <span class="flex-1">${a.message}</span>
                    <span class="text-xs text-gray-400">${a.time ? new Date(a.time).toLocaleString() : ''}</span>
                </div>
            `).join('');
        }

        function renderCharts(metrics) {
            if (!metrics.length) return;
            
            const labels = metrics.map(m => new Date(m.timestamp).toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'}));
            const scores = metrics.map(m => m.best_score);
            const elapsed = metrics.map(m => m.elapsed_seconds);
            const disk = metrics.map(m => m.disk_free_gb);
            
            // Score Chart
            const ctx1 = document.getElementById('scoreChart').getContext('2d');
            if (scoreChart) scoreChart.destroy();
            scoreChart = new Chart(ctx1, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: '最佳评分',
                        data: scores,
                        borderColor: '#58a6ff',
                        backgroundColor: 'rgba(88,166,255,0.1)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 3,
                        pointHoverRadius: 5
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: false, grid: { color: '#30363d' }, ticks: { color: '#8b949e' } },
                        x: { grid: { display: false }, ticks: { color: '#8b949e', maxTicksLimit: 10 } }
                    }
                }
            });
            
            // Perf Chart (dual axis)
            const ctx2 = document.getElementById('perfChart').getContext('2d');
            if (perfChart) perfChart.destroy();
            perfChart = new Chart(ctx2, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: '耗时 (秒)',
                            data: elapsed,
                            borderColor: '#d29922',
                            backgroundColor: 'rgba(210,153,34,0.1)',
                            fill: false,
                            tension: 0.3,
                            yAxisID: 'y',
                            pointRadius: 2
                        },
                        {
                            label: '磁盘 (GB)',
                            data: disk,
                            borderColor: '#3fb950',
                            backgroundColor: 'rgba(63,185,80,0.1)',
                            fill: false,
                            tension: 0.3,
                            yAxisID: 'y1',
                            pointRadius: 2
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: '#8b949e' } } },
                    scales: {
                        y: { type: 'linear', position: 'left', grid: { color: '#30363d' }, ticks: { color: '#8b949e' } },
                        y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, ticks: { color: '#8b949e' } },
                        x: { grid: { display: false }, ticks: { color: '#8b949e', maxTicksLimit: 10 } }
                    }
                }
            });
        }

        function updateChartsIncremental(metric) {
            if (!metric || !scoreChart || !perfChart) return;
            const label = new Date(metric.timestamp).toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'});
            
            // 保留最近 50 点
            const maxPoints = 50;
            if (scoreChart.data.labels.length >= maxPoints) {
                scoreChart.data.labels.shift();
                scoreChart.data.datasets[0].data.shift();
                perfChart.data.labels.shift();
                perfChart.data.datasets[0].data.shift();
                perfChart.data.datasets[1].data.shift();
            }
            
            scoreChart.data.labels.push(label);
            scoreChart.data.datasets[0].data.push(metric.best_score);
            scoreChart.update('none');
            
            perfChart.data.labels.push(label);
            perfChart.data.datasets[0].data.push(metric.elapsed_seconds);
            perfChart.data.datasets[1].data.push(metric.disk_free_gb);
            perfChart.update('none');
        }

        function renderHealthTable(data) {
            const tbody = document.getElementById('health-body');
            tbody.innerHTML = data.slice(-50).reverse().map(h => `
                <tr class="border-t border-gray-800">
                    <td class="py-1 text-gray-400">${h.timestamp || ''}</td>
                    <td class="py-1 ${h.CloudDaemon === 'RUNNING' ? 'text-green-400' : 'text-red-400'}">${h.CloudDaemon || '?'}</td>
                    <td class="py-1 ${h.ResearchDaemon === 'RUNNING' ? 'text-green-400' : 'text-red-400'}">${h.ResearchDaemon || '?'}</td>
                </tr>
            `).join('');
        }

        function updateHealthTable(newEntries) {
            if (!newEntries.length) return;
            const tbody = document.getElementById('health-body');
            newEntries.slice(-10).forEach(h => {
                const row = document.createElement('tr');
                row.className = 'border-t border-gray-800';
                row.innerHTML = `
                    <td class="py-1 text-gray-400">${h.timestamp || ''}</td>
                    <td class="py-1 ${h.CloudDaemon === 'RUNNING' ? 'text-green-400' : 'text-red-400'}">${h.CloudDaemon || '?'}</td>
                    <td class="py-1 ${h.ResearchDaemon === 'RUNNING' ? 'text-green-400' : 'text-red-400'}">${h.ResearchDaemon || '?'}</td>
                `;
                tbody.prepend(row);
            });
            // 限制 50 行
            while (tbody.children.length > 50) tbody.lastChild.remove();
        }

        // ─── 启动 ────────────────────────────────────────
        init();
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def index():
    return INDEX_HTML

# ─── 入口 ────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Antigravity 7x24 Monitor Dashboard")
    parser.add_argument("--daemon", action="store_true", help="作为守护进程运行（systemd 兼容）")
    args = parser.parse_args()
    
    LOG_DIR.mkdir(exist_ok=True)
    print("[INFO] Starting Antigravity Monitor Dashboard on http://0.0.0.0:8080")
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")